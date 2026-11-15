"""The local web server: the status page and a small JSON API. Nothing here calls the outside world;
the browser only ever talks to this process."""
import asyncio
import contextlib
import math
import re
import resource
import sys
import time
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import config, db, satinfo, translate
from . import news as news_window
from .collector import Collector
from .ais import stream as ais_stream
from .feeds import Fetcher, _readsb_aircraft, adsbfi_area
from .lookup import api as lookup_api

STATIC = Path(__file__).parent / "static"
collector = Collector()


def _process() -> dict:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    peak = ru.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)   # macOS reports bytes, Linux kilobytes
    return {"peak_memory_mb": round(peak, 1), "cpu_seconds": round(ru.ru_utime + ru.ru_stime, 2)}


def _ships_world_state(f):
    """The live ship stream is not a timed fetch; describe it from the stream itself."""
    a = ais_stream.status()
    f.update(items=a["ships"], fetched=a["last_message"], data_time=a["last_message"], tried=a["last_message"], error=None, note=None)
    if not a["key"]:
        f.update(state="waiting", note="not set up: register a free key at aisstream.io and put it in data/aisstream-key.txt")
    elif a["state"] == "failing":
        f.update(state="failing", error=a["error"])
    elif a["state"] == "connecting" or not a["last_message"]:
        f.update(state="waiting", note="connecting to aisstream.io")
    else:
        f.update(state="ok" if time.time() - a["last_message"] < 120 else "late",
                 note=f"{a['ships']:,} ships heard in the last 30 minutes; {a['messages']:,} messages since the stream opened")
    return f


async def status(request):
    s = collector.status()
    s["feeds"] = [_ships_world_state(f) if f["name"] == "ships_world" else f for f in s["feeds"]]
    s["process"] = _process()
    s["home"] = {"lat": config.HOME_LAT, "lon": config.HOME_LON}
    return JSONResponse(s, headers={"Cache-Control": "no-store"})


async def data(request):
    st = collector.states.get(request.path_params["name"])
    if not st:
        return JSONResponse({"error": "no such feed"}, status_code=404)
    now = time.time()
    payload = st.payload
    if request.path_params["name"] == "ships":
        # Finland's feed (stored) plus the worldwide stream (in memory only, merged here); the newer report wins
        merged = {s["mmsi"]: {**s, "source": "Digitraffic"} for s in (payload or {}).get("ships", [])}
        for s in ais_stream.ships():
            if s["mmsi"] not in merged or s["time"] > merged[s["mmsi"]]["time"]:
                merged[s["mmsi"]] = s
        payload = {"ships": list(merged.values()), "world": ais_stream.status()}
    return JSONResponse({**st.public(now), "now": now, "payload": payload}, headers={"Cache-Control": "no-store"})


async def route(request):
    """Where a flight is scheduled from and to, by callsign, from adsbdb.com (crowd-sourced, can be wrong).
    Asked only when someone opens an aircraft, and remembered for a day."""
    callsign = request.path_params["callsign"].upper()
    if not re.fullmatch(r"[A-Z0-9]{3,8}", callsign):
        return JSONResponse({"error": "not a callsign"}, status_code=400)
    key = "route2:" + callsign
    hit = await asyncio.to_thread(db.lookup_get, key, 86400)
    if not hit:
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get(f"https://api.adsbdb.com/v0/callsign/{callsign}")
            fr = r.json().get("response", {}).get("flightroute") if r.status_code == 200 else None
            body = None
            if isinstance(fr, dict):
                port = lambda a: {"iata": a.get("iata_code"), "name": a.get("name"), "city": a.get("municipality"), "country": a.get("country_name"),
                                  "lat": a.get("latitude"), "lon": a.get("longitude")}
                body = {"airline": (fr.get("airline") or {}).get("name"), "origin": port(fr["origin"]), "destination": port(fr["destination"])}
            elif r.status_code not in (200, 404):
                return JSONResponse({"error": f"adsbdb answered {r.status_code}"}, status_code=502)
            hit = {"fetched": time.time(), "body": body}
            await asyncio.to_thread(db.lookup_put, key, hit["fetched"], body)
        except httpx.HTTPError as e:
            return JSONResponse({"error": f"adsbdb could not be reached ({type(e).__name__})"}, status_code=502)
    fits, why = None, ""
    q = request.query_params
    if hit["body"] and "lat" in q and "lon" in q:
        try:
            fits, why = route_fits(hit["body"], float(q["lat"]), float(q["lon"]), float(q["track"]) if q.get("track") else None)
        except ValueError:
            pass
    return JSONResponse({"callsign": callsign, "route": hit["body"], "fits": fits, "why": why, "fetched": hit["fetched"], "now": time.time()})


def _km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = math.radians
    h = math.sin(r(b_lat - a_lat) / 2) ** 2 + math.cos(r(a_lat)) * math.cos(r(b_lat)) * math.sin(r(b_lon - a_lon) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def _bearing(a_lat, a_lon, b_lat, b_lon) -> float:
    r = math.radians
    y = math.sin(r(b_lon - a_lon)) * math.cos(r(b_lat))
    x = math.cos(r(a_lat)) * math.sin(r(b_lat)) - math.sin(r(a_lat)) * math.cos(r(b_lat)) * math.cos(r(b_lon - a_lon))
    return math.degrees(math.atan2(y, x)) % 360


def route_fits(route: dict, lat: float, lon: float, track: float | None) -> tuple[bool, str]:
    """Does an aircraft at this position, on this heading, plausibly belong to this route? adsbdb's routes are
    crowd-sourced per callsign and are sometimes plain wrong. Two simple tests on the numbers we have:
    the detour via the aircraft must be small, and the aircraft must be heading roughly towards the destination."""
    o, d = route["origin"], route["destination"]
    if None in (o.get("lat"), o.get("lon"), d.get("lat"), d.get("lon")):
        return False, "the airports have no coordinates"
    direct = _km(o["lat"], o["lon"], d["lat"], d["lon"])
    to_go = _km(lat, lon, d["lat"], d["lon"])
    via = _km(o["lat"], o["lon"], lat, lon) + to_go
    if via > direct * 1.25 + 150:
        return False, "the aircraft is far off the line between those airports"
    if track is not None and to_go > 120:
        off = abs((_bearing(lat, lon, d["lat"], d["lon"]) - track + 180) % 360 - 180)
        if off > 100:
            return False, "the aircraft is heading away from that destination"
    return True, ""


_tracks: dict[str, tuple[float, dict]] = {}


async def track(request):
    """The path an aircraft has really flown on its current flight, from OpenSky's track service; if that
    fails, the positions this server received for it in the last 3 hours."""
    hex_ = request.path_params["hex"].lower()
    if not re.fullmatch(r"[0-9a-f]{6}", hex_):
        return JSONResponse({"error": "not a transponder address"}, status_code=400)
    now = time.time()
    hit = _tracks.get(hex_)
    if not hit or now - hit[0] > 60:
        body = None
        try:
            async with httpx.AsyncClient(timeout=12, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get(f"https://opensky-network.org/api/tracks/all?icao24={hex_}&time=0")
            if r.status_code == 200:
                d = r.json()
                body = {"source": "OpenSky Network", "points": [[p[0], p[2], p[1]] for p in d.get("path") or [] if p[1] is not None and p[2] is not None],
                        "start": d.get("startTime"), "note": None}
            elif r.status_code == 429:
                body = {"source": None, "points": [], "note": "OpenSky's free daily allowance is used up"}
            elif r.status_code == 404:
                body = {"source": None, "points": [], "note": "OpenSky has no path for this aircraft"}
            else:
                body = {"source": None, "points": [], "note": f"OpenSky answered {r.status_code}"}
        except httpx.HTTPError as e:
            body = {"source": None, "points": [], "note": f"OpenSky could not be reached ({type(e).__name__})"}
        for k in [k for k, v in _tracks.items() if now - v[0] > 600]:
            del _tracks[k]
        hit = _tracks[hex_] = (now, body)
    body = dict(hit[1])
    ours = collector.trails.get(hex_, [])
    if not body["points"] and ours:
        body.update(source="positions this server received in the last 3 hours", points=ours)
    return JSONResponse({"hex": hex_, **body, "fetched": hit[0], "now": now}, headers={"Cache-Control": "no-store"})


async def photo(request):
    """A photo of this very aircraft from planespotters.net. Their rules: identify yourself, credit the
    photographer, link back to their page, and keep the answer no longer than a day."""
    hex_ = request.path_params["hex"].lower()
    if not re.fullmatch(r"[0-9a-f]{6}", hex_):
        return JSONResponse({"error": "not a transponder address"}, status_code=400)
    who = config.contact()
    if not who:
        return JSONResponse({"photo": None, "off": True})
    key = "photo:" + hex_
    hit = await asyncio.to_thread(db.lookup_get, key, 86400)
    if not hit:
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": f"WorldWatch/0.1 (personal non-commercial dashboard; {who})"}) as c:
                r = await c.get(f"https://api.planespotters.net/pub/photos/hex/{hex_}")
            if r.status_code != 200:
                return JSONResponse({"photo": None, "error": f"planespotters.net answered {r.status_code}"})
            ph = (r.json().get("photos") or [None])[0]
            body = ph and {"src": (ph.get("thumbnail_large") or ph["thumbnail"])["src"], "link": ph["link"], "photographer": ph["photographer"]}
            hit = {"fetched": time.time(), "body": body}
            await asyncio.to_thread(db.lookup_put, key, hit["fetched"], body)
        except httpx.HTTPError as e:
            return JSONResponse({"photo": None, "error": f"planespotters.net could not be reached ({type(e).__name__})"})
    return JSONResponse({"photo": hit["body"]})


async def news_place(request):
    """Every article of one news place over the last six hours, headlines in other languages machine-translated
    now (and remembered), so a card shows the full picture without sending everything with the map."""
    name = request.query_params.get("p", "")
    arts = news_window.place_articles(name)
    todo: dict[str, list[dict]] = {}
    for a in arts:
        if a["lang"] != "eng":
            todo.setdefault(a["lang"], []).append(a)
    failed = 0
    if todo:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": config.USER_AGENT}) as c:
            f = Fetcher(c)
            for lang, group in todo.items():
                english, bad = await translate.to_english(f, [a["title"] for a in group], news_window.GOOGLE.get(lang, "auto"))
                failed += bad
                for a in group:
                    if english.get(a["title"], a["title"]) != a["title"]:
                        a["title_original"], a["title"], a["translated"] = a["title"], english[a["title"]], True
    return JSONResponse({"place": name, "articles": arts, "untranslated": failed, "languages": news_window.NAMES})


_ucs = {"at": 0, "data": {}}


async def satellite(request):
    """What one satellite is: the UCS row (purpose, operator, users) and Wikidata's entry (picture, description,
    kind, operator, manufacturer), by catalogue number. Wikidata is asked when a card opens and remembered 30 days."""
    try:
        norad = int(request.path_params["norad"])
    except ValueError:
        return JSONResponse({"error": "not a catalogue number"}, status_code=400)
    if time.time() - _ucs["at"] > 3600:
        _ucs.update(at=time.time(), data=await asyncio.to_thread(satinfo.load))
    key, wd = f"satwd:{norad}", None
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        wd = hit["body"]
    else:
        q = f"""SELECT ?s ?sLabel ?sDescription ?img ?typeLabel ?useLabel ?opLabel ?makerLabel ?article WHERE {{
          ?s wdt:P377 "{norad}". OPTIONAL {{ ?s wdt:P18 ?img }} OPTIONAL {{ ?s wdt:P31 ?type }} OPTIONAL {{ ?s wdt:P366 ?use }}
          OPTIONAL {{ ?s wdt:P137 ?op }} OPTIONAL {{ ?s wdt:P176 ?maker }}
          OPTIONAL {{ ?article schema:about ?s; schema:isPartOf <https://en.wikipedia.org/> }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }} LIMIT 40"""
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT, "Accept": "application/sparql-results+json"}) as c:
                r = await c.get("https://query.wikidata.org/sparql", params={"query": q})
            if r.status_code == 200:
                rows = r.json()["results"]["bindings"]
                v = lambda x, k: x.get(k, {}).get("value")
                if rows:
                    main = rows[0]["s"]["value"]
                    rows = [x for x in rows if x["s"]["value"] == main] or rows   # the ISS number also names its modules
                    wd = {"qid": main.rsplit("/", 1)[1], "name": v(rows[0], "sLabel"), "description": v(rows[0], "sDescription"),
                          "image": next((v(x, "img") for x in rows if v(x, "img")), None),
                          "kinds": sorted({v(x, "typeLabel") for x in rows if v(x, "typeLabel")} - {"artificial satellite of the Earth", "satellite"}),
                          "uses": sorted({v(x, "useLabel") for x in rows if v(x, "useLabel")}),
                          "operators": sorted({v(x, "opLabel") for x in rows if v(x, "opLabel")}),
                          "makers": sorted({v(x, "makerLabel") for x in rows if v(x, "makerLabel")}),
                          "wikipedia": next((v(x, "article") for x in rows if v(x, "article")), None)}
                else:
                    wd = {}
                await asyncio.to_thread(db.lookup_put, key, time.time(), wd)
        except (httpx.HTTPError, ValueError, KeyError):
            wd = None
    return JSONResponse({"norad": norad, "ucs": _ucs["data"].get(norad), "wikidata": wd,
                         "ucs_kind": satinfo.code(_ucs["data"][norad]) if norad in _ucs["data"] else None})


async def ship_about(request):
    """A ship's picture and description from Wikidata: by IMO number (P458) or MMSI (P587), and for warships, which
    rarely have an IMO number, by name. Remembered 30 days."""
    q = request.query_params
    imo, mmsi, name, mil = (q.get("imo") or "").strip(), (q.get("mmsi") or "").strip(), (q.get("name") or "").strip(), q.get("mil") == "1"
    key = f"ship:{imo}:{mmsi}:{name.lower() if mil else ''}"
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        return JSONResponse(hit["body"])
    fields = """OPTIONAL { ?s wdt:P18 ?img } OPTIONAL { ?s wdt:P31 ?type } OPTIONAL { ?s wdt:P137 ?op } OPTIONAL { ?s wdt:P8047 ?flag }
      OPTIONAL { ?s wdt:P729 ?since } OPTIONAL { ?article schema:about ?s; schema:isPartOf <https://en.wikipedia.org/> }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }"""
    body, by = {}, None
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT, "Accept": "application/sparql-results+json"}) as c:
        async def sparql(where):
            r = await c.get("https://query.wikidata.org/sparql", params={"query": f"SELECT ?s ?sLabel ?sDescription ?img ?typeLabel ?opLabel ?flagLabel ?since ?article WHERE {{ {where} {fields} }} LIMIT 20"})
            return r.json()["results"]["bindings"] if r.status_code == 200 else []
        try:
            rows = []
            if re.fullmatch(r"\d{7}", imo):
                rows, by = await sparql(f'?s wdt:P458 "{imo}".'), "imo"
            if not rows and re.fullmatch(r"\d{9}", mmsi):
                rows, by = await sparql(f'?s wdt:P587 "{mmsi}".'), "mmsi"
            if not rows and mil and len(name) >= 4:
                r = await c.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities", "search": name.title(), "language": "en", "type": "item", "limit": 7, "format": "json"})
                hits = [h["id"] for h in r.json().get("search", []) if re.search(r"ship|frigate|destroyer|corvette|carrier|submarine|cruiser|vessel|patrol|boat|navy", h.get("description", ""), re.I)]
                if hits:
                    rows, by = await sparql(f"VALUES ?s {{ wd:{hits[0]} }}"), "name"
        except (httpx.HTTPError, ValueError, KeyError):
            return JSONResponse({"error": "Wikidata could not be reached"})
        if rows:
            v = lambda x, k: x.get(k, {}).get("value")
            body = {"qid": v(rows[0], "s").rsplit("/", 1)[1], "name": v(rows[0], "sLabel"), "description": v(rows[0], "sDescription"),
                    "image": next((v(x, "img") for x in rows if v(x, "img")), None),
                    "kinds": sorted({v(x, "typeLabel") for x in rows if v(x, "typeLabel")})[:4],
                    "operator": next((v(x, "opLabel") for x in rows if v(x, "opLabel")), None),
                    "country": next((v(x, "flagLabel") for x in rows if v(x, "flagLabel")), None),
                    "built": (next((v(x, "since") for x in rows if v(x, "since")), None) or "")[:4] or None,
                    "wikipedia": next((v(x, "article") for x in rows if v(x, "article")), None), "by": by}
        # Wikimedia Commons files ships under "Category:IMO <number>", which covers far more ships than Wikidata
        if not body.get("image") and re.fullmatch(r"\d{7}", imo):
            try:
                api = "https://commons.wikimedia.org/w/api.php"
                cat = f"Category:IMO {imo}"
                for _ in range(2):                                 # the IMO category often holds one category per ship name
                    r = await c.get(api, params={"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": "file|subcat", "cmlimit": 10, "format": "json"})
                    members = r.json().get("query", {}).get("categorymembers", []) if r.status_code == 200 else []
                    files = [m["title"] for m in members if m["title"].startswith("File:")]
                    if files:
                        r = await c.get(api, params={"action": "query", "titles": files[0], "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 640, "format": "json"})
                        page = next(iter(r.json()["query"]["pages"].values()))
                        info = (page.get("imageinfo") or [{}])[0]
                        body.update(image=info.get("thumburl") or info.get("url"), commons=info.get("descriptionurl"), by=body.get("by") or "imo")
                        break
                    subs = [m["title"] for m in members if m["title"].startswith("Category:")]
                    if not subs:
                        break
                    cat = subs[0]
            except (httpx.HTTPError, ValueError, KeyError, StopIteration):
                pass
    await asyncio.to_thread(db.lookup_put, key, time.time(), body)
    return JSONResponse(body)


async def imagery_date(request):
    """When the sharp picture (Esri World Imagery) under a point was taken, from Esri's own metadata. Cached a week
    per ~1 km square, since the pictures change a few times a year at most."""
    try:
        lat, lon, z = float(request.query_params["lat"]), float(request.query_params["lon"]), int(request.query_params.get("z", 14))
    except (KeyError, ValueError):
        return JSONResponse({"error": "lat and lon are needed"}, status_code=400)
    key = f"esri-date:{lat:.2f},{lon:.2f}"
    hit = await asyncio.to_thread(db.lookup_get, key, 7 * 86400)
    if not hit:
        d = 0.01
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get("https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/identify", params={
                    "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "sr": 4326, "layers": "all", "tolerance": 1,
                    "mapExtent": f"{lon - d},{lat - d},{lon + d},{lat + d}", "imageDisplay": "400,400,96", "returnGeometry": "false", "f": "json"})
            res = r.json().get("results", [])
        except (httpx.HTTPError, ValueError):
            return JSONResponse({"date": None, "error": "Esri could not be reached"})
        best = None
        for x in res:                      # the sharpest picture that has a date
            a = x.get("attributes", {})
            dt = a.get("DATE (YYYYMMDD)") or ""
            if re.fullmatch(r"\d{8}", dt):
                res_m = float(a.get("RESOLUTION (M)") or 99)
                if not best or res_m < best["res"]:
                    best = {"date": f"{dt[:4]}-{dt[4:6]}-{dt[6:]}", "res": res_m, "sensor": a.get("DESCRIPTION"), "source": a.get("SOURCE")}
        hit = {"fetched": time.time(), "body": best or {}}
        await asyncio.to_thread(db.lookup_put, key, hit["fetched"], hit["body"])
    return JSONResponse(hit["body"] or {"date": None})


async def news_image(request):
    """An outlet's preview picture, fetched by this server so the outlet never sees the browser. Only pictures
    named in the current news data are fetched; this is not an open proxy."""
    url = request.query_params.get("u", "")
    if url not in news_window.images():
        return Response(status_code=404)
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={"User-Agent": config.USER_AGENT}) as c:
            async with c.stream("GET", url) as r:
                kind = r.headers.get("content-type", "")
                if r.status_code != 200 or not kind.startswith("image/"):
                    return Response(status_code=502)
                body = b""
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > 3_000_000:
                        return Response(status_code=502)
    except httpx.HTTPError:
        return Response(status_code=502)
    return Response(body, media_type=kind.split(";")[0], headers={"Cache-Control": "private, max-age=86400"})


_area = {"at": 0.0, "key": None, "body": None}


async def area(request):
    """Live aircraft for the part of the map someone is looking at, from adsb.fi, fetched only on request.
    Answers are reused for 8 seconds, so several open pages cannot multiply the requests."""
    try:
        lat, lon = float(request.query_params["lat"]), float(request.query_params["lon"])
        radius = max(10, min(250, int(float(request.query_params.get("r", 100)))))
    except (KeyError, ValueError):
        return JSONResponse({"error": "lat, lon and r are needed"}, status_code=400)
    if not (-90 <= lat <= 90):
        return JSONResponse({"error": "lat out of range"}, status_code=400)
    lon = (lon + 180) % 360 - 180
    key, now = (round(lat, 1), round(lon, 1), radius), time.time()
    st = collector.states["aircraft_view"]
    if _area["key"] != key or now - _area["at"] > 8:
        started, t0 = now, time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": config.USER_AGENT}) as c:
                d, nbytes = await adsbfi_area(c, lat, lon, radius)
            ac = _readsb_aircraft(d)
            collector._remember(ac, d["now"] / 1000)
            _area.update(at=time.time(), key=key, body={"aircraft": ac, "data_time": d["now"] / 1000, "fetched": time.time(), "lat": lat, "lon": lon, "radius_nm": radius})
            st.tried = st.fetched = started; st.error = None; st.ok_count += 1; st.items = len(ac); st.data_time = d["now"] / 1000
            st.last_ms = int((time.perf_counter() - t0) * 1000); st.last_bytes = nbytes; st.total_bytes += nbytes
            st.note = f"the {radius} nautical miles around {lat:.1f}, {lon:.1f}; fetched only while someone is zoomed in"
        except Exception as e:
            st.tried = started; st.fail_count += 1
            st.error = f"adsb.fi: {type(e).__name__}" + (f" {e.response.status_code}" if isinstance(e, httpx.HTTPStatusError) else "")
            return JSONResponse({"error": st.error, "now": time.time()}, status_code=502)
    return JSONResponse({**_area["body"], "now": time.time()}, headers={"Cache-Control": "no-store"})


async def trail(request):
    hex_ = request.path_params["hex"].lower()
    return JSONResponse({"hex": hex_, "points": collector.trails.get(hex_, []), "now": time.time()}, headers={"Cache-Control": "no-store"})


# Browsers, Safari above all, keep script files and reuse them without asking, and then mix old and new
# files after an update (which once left the map blank). So every start of the server gets its own address
# for the files: the pages point at /s/<start time>/..., and an old copy can never be picked up again.
VERSION = format(int(time.time()), "x")


class Forever(StaticFiles):
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return r


def page(name):
    async def serve(request):
        html = (STATIC / name).read_text().replace("/static/", f"/s/{VERSION}/")
        return HTMLResponse(html, headers={"Cache-Control": "no-store"})
    return serve


@contextlib.asynccontextmanager
async def lifespan(app):
    await collector.start()
    ais_stream.start()
    yield
    await ais_stream.stop()
    await collector.stop()


app = Starlette(lifespan=lifespan, middleware=[Middleware(GZipMiddleware, minimum_size=2000)], routes=[
    Route("/", page("index.html")),
    Route("/feeds", page("feeds.html")),
    Route("/lookup", page("lookup.html")),
    *lookup_api.routes,
    Route("/api/status", status),
    Route("/api/data/{name}", data),
    Route("/api/route/{callsign}", route),
    Route("/api/trail/{hex}", trail),
    Route("/api/track/{hex}", track),
    Route("/api/photo/{hex}", photo),
    Route("/api/news/place", news_place),
    Route("/api/news/image", news_image),
    Route("/api/satellite/{norad}", satellite),
    Route("/api/imagery/date", imagery_date),
    Route("/api/ship/about", ship_about),
    Route("/api/aircraft/area", area),
    Mount(f"/s/{VERSION}", Forever(directory=STATIC)),
    Mount("/static", StaticFiles(directory=STATIC)),
])
