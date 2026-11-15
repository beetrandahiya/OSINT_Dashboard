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

from . import config, db, maxar, patterns, satinfo, translate
from . import dossier
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


def _wm_headers(sparql=False) -> dict:
    """Wikimedia asks automated clients to say who they are; with a contact address set, it is included."""
    who = config.contact()
    h = {"User-Agent": f"WorldWatch/0.1 (personal non-commercial dashboard{'; ' + who if who else ''})"}
    if sparql:
        h["Accept"] = "application/sparql-results+json"
    return h


def _commons(url_or_name: str | None) -> str | None:
    if not url_or_name:
        return None
    return url_or_name.replace("http://", "https://") + ("&" if "?" in url_or_name else "?") + "width=640"


async def satellite(request):
    """What one satellite is: the UCS row (purpose, operator, users) and Wikidata's entry (picture, description,
    kind, operator, maker), by catalogue number. When the satellite has no picture of its own, the picture of its
    type (Wikidata's class) or of its family (by name, e.g. Starlink) is used, and labelled as such."""
    try:
        norad = int(request.path_params["norad"])
    except ValueError:
        return JSONResponse({"error": "not a catalogue number"}, status_code=400)
    name = (request.query_params.get("name") or "").strip()
    ucs_row = await asyncio.to_thread(lambda: satinfo.load().get(norad))   # read per request: holding all 7,551 rows cost ~10 MB
    key, wd, problem = f"satwd3:{norad}", None, None
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        wd = hit["body"]
    else:
        q = f"""SELECT ?s ?sLabel ?sDescription ?img ?typeLabel ?typeImg ?opLabel ?makerLabel ?article WHERE {{
          ?s wdt:P377 "{norad}". OPTIONAL {{ ?s wdt:P18 ?img }} OPTIONAL {{ ?s wdt:P31 ?type. OPTIONAL {{ ?type wdt:P18 ?typeImg }} }}
          OPTIONAL {{ ?s wdt:P137 ?op }} OPTIONAL {{ ?s wdt:P176 ?maker }}
          OPTIONAL {{ ?article schema:about ?s; schema:isPartOf <https://en.wikipedia.org/> }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }} LIMIT 60"""
        try:
            async with httpx.AsyncClient(timeout=25, headers=_wm_headers(True)) as c:
                try:
                    r = await c.get("https://query.wikidata.org/sparql", params={"query": q})
                    rows = r.json()["results"]["bindings"] if r.status_code == 200 else []
                    if r.status_code != 200:
                        problem = f"Wikidata answered {r.status_code}"
                except (httpx.HTTPError, ValueError, KeyError) as e:
                    rows, problem = [], f"Wikidata could not be asked ({type(e).__name__})"
                v = lambda x, k: x.get(k, {}).get("value")
                wd = {}
                if rows:
                    main = rows[0]["s"]["value"]
                    rows = [x for x in rows if x["s"]["value"] == main] or rows   # the ISS number also names its modules
                    own = next((v(x, "img") for x in rows if v(x, "img")), None)
                    typ = next(((v(x, "typeImg"), v(x, "typeLabel")) for x in rows if v(x, "typeImg")), (None, None))
                    wd = {"qid": main.rsplit("/", 1)[1], "name": v(rows[0], "sLabel"), "description": v(rows[0], "sDescription"),
                          "image": _commons(own or typ[0]), "image_of": "this satellite" if own else (f"its type, {typ[1]}" if typ[0] else None),
                          "kinds": sorted({v(x, "typeLabel") for x in rows if v(x, "typeLabel")} - {"artificial satellite of the Earth", "satellite"}),
                          "operators": sorted({v(x, "opLabel") for x in rows if v(x, "opLabel")}),
                          "makers": sorted({v(x, "makerLabel") for x in rows if v(x, "makerLabel")}),
                          "wikipedia": next((v(x, "article") for x in rows if v(x, "article")), None)}
                # no picture yet: try the family by name (STARLINK-1234 -> Starlink, YAOGAN-30 01 -> Yaogan)
                family = re.split(r"[-\s(]|\d", name.strip(), maxsplit=1)[0].strip().title() if name else ""
                if not wd.get("image") and len(family) >= 3 and family.upper() not in ("USA", "OBJECT", "SL", "CZ"):
                    r = await c.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities", "search": family, "language": "en",
                                                                                 "type": "item", "limit": 6, "format": "json"})
                    fam = next((h for h in r.json().get("search", []) if re.search(r"satellite|constellation|spacecraft|space", h.get("description", ""), re.I)), None)
                    if fam:
                        r = await c.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": fam["id"], "props": "claims", "format": "json"})
                        claim = (r.json()["entities"][fam["id"]].get("claims", {}).get("P18") or [{}])[0]
                        file = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                        if file:
                            wd.update(image=_commons("https://commons.wikimedia.org/wiki/Special:FilePath/" + file.replace(" ", "_")),
                                      image_of=f"the {fam.get('label', family)} family, not this satellite", family_qid=fam["id"])
                # still nothing: NASA's image library (free, mostly public domain), accepted only when the picture's
                # title names this satellite or its family
                if not wd.get("image") and name:
                    for q in dict.fromkeys([re.sub(r"\s*\(.*\)", "", name).strip(), family]):
                        if not q or len(q) < 3:
                            continue
                        r = await c.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "image"})
                        key_q = re.sub(r"[\s_-]+", " ", q.lower())
                        hit = next((i for i in (r.json().get("collection", {}).get("items") or [])[:25]
                                    if key_q in re.sub(r"[\s_-]+", " ", (i.get("data") or [{}])[0].get("title", "").lower())), None)
                        if hit:
                            d0 = hit["data"][0]
                            wd.update(image=next((l["href"] for l in hit.get("links", []) if l.get("render") == "image"), None),
                                      image_of=f"NASA's picture \"{d0.get('title')}\" ({(d0.get('date_created') or '')[:4]})",
                                      image_link="https://images.nasa.gov/details/" + d0.get("nasa_id", ""))
                            break
            if not problem:                                  # remember only complete answers
                await asyncio.to_thread(db.lookup_put, key, time.time(), wd)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            problem = (problem or "") + f"; a picture source could not be asked ({type(e).__name__})"
    return JSONResponse({"norad": norad, "ucs": ucs_row, "wikidata": wd, "problem": problem if not (wd or {}).get("image") else None,
                         "ucs_kind": satinfo.code(ucs_row) if ucs_row else None})


async def ship_trail(request):
    """The positions the worldwide ship stream heard from one ship since this server started (up to 30 points)."""
    try:
        mmsi = int(request.path_params["mmsi"])
    except ValueError:
        return JSONResponse({"error": "not an MMSI"}, status_code=400)
    return JSONResponse({"mmsi": mmsi, "points": ais_stream.trail(mmsi), "since": ais_stream.t0})


async def ship_about(request):
    """A ship's picture and description from Wikidata: by IMO number (P458) or MMSI (P587), and for warships, which
    rarely have an IMO number, by name. Remembered 30 days."""
    q = request.query_params
    imo, mmsi, name, mil = (q.get("imo") or "").strip(), (q.get("mmsi") or "").strip(), (q.get("name") or "").strip(), q.get("mil") == "1"
    key = f"ship2:{imo}:{mmsi}:{name.lower()}"
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        return JSONResponse(hit["body"])
    fields = """OPTIONAL { ?s wdt:P18 ?img } OPTIONAL { ?s wdt:P31 ?type } OPTIONAL { ?s wdt:P137 ?op } OPTIONAL { ?s wdt:P8047 ?flag }
      OPTIONAL { ?s wdt:P729 ?since } OPTIONAL { ?article schema:about ?s; schema:isPartOf <https://en.wikipedia.org/> }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }"""
    body, by = {}, None
    async with httpx.AsyncClient(timeout=20, headers=_wm_headers(True)) as c:
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
                return JSONResponse({**body, "error": "Wikimedia Commons could not be asked"})   # not remembered: try again next time
        # last: a Wikimedia Commons file whose title carries the ship's name (warships are often filed by name)
        if not body.get("image") and len(name) >= 4:
            try:
                q = name.title() + (" ship" if not mil else "")
                r = await c.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "list": "search", "srnamespace": 6,
                                                                                   "srsearch": q, "srlimit": 8, "format": "json"})
                low = name.lower()
                file = next((h["title"] for h in r.json().get("query", {}).get("search", []) if low in h["title"].lower()), None)
                if file:
                    r = await c.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "titles": file, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 640, "format": "json"})
                    info = (next(iter(r.json()["query"]["pages"].values())).get("imageinfo") or [{}])[0]
                    body.update(image=info.get("thumburl") or info.get("url"), commons=info.get("descriptionurl"), by=body.get("by") or "name")
            except (httpx.HTTPError, ValueError, KeyError, StopIteration):
                return JSONResponse({**body, "error": "Wikimedia Commons could not be asked"})
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


_mx_meta: dict[str, tuple[float, dict]] = {}


async def _mx_json(c, url):
    key = "maxar:" + url
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        return hit["body"]
    r = await c.get(url)
    r.raise_for_status()
    body = r.json()
    await asyncio.to_thread(db.lookup_put, key, time.time(), body)
    return body


async def maxar_acq(request):
    """The acquisitions (one satellite pass each) of one Maxar event: where, when, how many picture files."""
    eid = request.query_params.get("event", "")
    if not re.fullmatch(r"[\w.-]+", eid):
        return JSONResponse({"error": "no such event"}, status_code=400)
    base = maxar.BASE + eid + "/"
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT}) as c:
        try:
            col = await _mx_json(c, base + "collection.json")
            out, gate = [], asyncio.Semaphore(6)
            async def one(href):
                async with gate:
                    a = await _mx_json(c, base + href.lstrip("./"))
                ext = a.get("extent", {})
                return {"id": a.get("id"), "href": href.lstrip("./"), "bbox": (ext.get("spatial", {}).get("bbox") or [[None] * 4])[0],
                        "when": ((ext.get("temporal", {}).get("interval") or [[None]])[0][0] or "")[:16], "items": sum(1 for l in a.get("links", []) if l.get("rel") == "item")}
            out = await asyncio.gather(*(one(l["href"]) for l in col.get("links", []) if l.get("rel") == "child"))
        except (httpx.HTTPError, ValueError) as e:
            return JSONResponse({"error": f"Maxar's catalogue could not be read ({type(e).__name__})"}, status_code=502)
    return JSONResponse({"event": eid, "acquisitions": sorted(out, key=lambda a: a["when"], reverse=True)})


async def maxar_items(request):
    """The picture files of one acquisition: each with its area, time, satellite and file address."""
    eid, href = request.query_params.get("event", ""), request.query_params.get("acq", "")
    if not re.fullmatch(r"[\w.-]+", eid) or not re.fullmatch(r"[\w./-]+\.json", href) or ".." in href.replace("../", ""):
        return JSONResponse({"error": "bad request"}, status_code=400)
    acq_url = maxar.BASE + eid + "/" + href
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT}) as c:
        try:
            acq = await _mx_json(c, acq_url)
            gate = asyncio.Semaphore(8)
            async def one(link):
                url = str(httpx.URL(acq_url).join(link))
                async with gate:
                    it = await _mx_json(c, url)
                vis = (it.get("assets", {}).get("visual") or {}).get("href")
                pr = it.get("properties", {})
                return {"id": it.get("id"), "bbox": it.get("bbox"), "when": (pr.get("datetime") or "")[:16], "platform": pr.get("platform"),
                        "gsd": pr.get("gsd"), "cloud": pr.get("eo:cloud_cover"), "visual": str(httpx.URL(url).join(vis)) if vis else None}
            items = await asyncio.gather(*(one(l["href"]) for l in acq.get("links", []) if l.get("rel") == "item"))
        except (httpx.HTTPError, ValueError) as e:
            return JSONResponse({"error": f"Maxar's catalogue could not be read ({type(e).__name__})"}, status_code=502)
    return JSONResponse({"items": [i for i in items if i["visual"]]})


async def _mx_read(u: str) -> dict:
    hit = _mx_meta.get(u)
    if hit and time.time() - hit[0] < 6 * 3600:
        return hit[1]
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT}) as c:
        for size in (65536, 262144):
            r = await c.get(u, headers={"Range": f"bytes=0-{size - 1}"})
            r.raise_for_status()
            try:
                meta = await asyncio.to_thread(maxar.parse_tiff, r.content)
                break
            except ValueError as e:
                if "beyond" not in str(e) or size == 262144:
                    raise
    if len(_mx_meta) > 300:
        for k, _ in sorted(_mx_meta.items(), key=lambda kv: kv[1][0])[:100]:
            del _mx_meta[k]
    _mx_meta[u] = (time.time(), meta)
    return meta


async def maxar_meta(request):
    u = request.query_params.get("u", "")
    if not maxar.ALLOWED.match(u):
        return JSONResponse({"error": "not a Maxar Open Data file"}, status_code=400)
    try:
        return JSONResponse(maxar.public(await _mx_read(u)), headers={"Cache-Control": "private, max-age=86400"})
    except (httpx.HTTPError, ValueError) as e:
        return JSONResponse({"error": f"could not read the file ({e})"[:160]}, status_code=502)


async def maxar_tile(request):
    """One 512-pixel piece of a Maxar picture, as a JPEG, cut straight out of the file."""
    q = request.query_params
    u = q.get("u", "")
    if not maxar.ALLOWED.match(u):
        return Response(status_code=400)
    try:
        meta = await _mx_read(u)
        off, n, lv = maxar.piece(meta, int(q["l"]), int(q["x"]), int(q["y"]))
        if not n:
            return Response(status_code=204)
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT}) as c:
            r = await c.get(u, headers={"Range": f"bytes={off}-{off + n - 1}"})
        r.raise_for_status()
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return Response(status_code=502)
    if lv["comp"] == 8:
        try:
            body = await asyncio.to_thread(maxar.png_from_deflate, lv, r.content)
        except Exception:
            return Response(status_code=502)
        return Response(body, media_type="image/png", headers={"Cache-Control": "private, max-age=2592000"})
    return Response(maxar.jpeg(lv["tables"], r.content), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=2592000"})


_eum_times: dict[str, tuple[float, str | None]] = {}


async def eumetsat_time(request):
    """The newest image time of an EUMETSAT layer, so every map tile asks for the same moment (tiles fetched a minute
    apart otherwise show different pictures, which looked like lightning moving when zooming)."""
    layer = request.query_params.get("layer", "mtg_fd:li_afa")
    if not re.fullmatch(r"[a-z_]+:[a-z0-9_]+", layer):
        return JSONResponse({"error": "bad layer"}, status_code=400)
    hit = _eum_times.get(layer)
    if not hit or time.time() - hit[0] > 60:
        t = hit[1] if hit else None
        ns, name = layer.split(":")
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get(f"https://view.eumetsat.int/geoserver/{ns}/{name}/ows", params={"service": "WMS", "version": "1.3.0", "request": "GetCapabilities"})
            m = re.search(r'<Dimension name="time" default="([^"]+)"', r.text)
            t = m.group(1) if m else t
        except httpx.HTTPError:
            pass
        hit = _eum_times[layer] = (time.time(), t)
    return JSONResponse({"time": hit[1]})


async def news_image(request):
    """An outlet's preview picture, fetched by this server so the outlet never sees the browser. Only pictures
    named in the current news data are fetched; this is not an open proxy."""
    url = request.query_params.get("u", "")
    fleet = (collector.states.get("usni_fleet") and collector.states["usni_fleet"].payload) or {}
    if url not in news_window.images() and url != fleet.get("graphic"):
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


async def flight_patterns(request):
    """Orbiting military aircraft and tankers in the air, worked out from the positions we received (patterns.py)."""
    st = collector.states.get("aircraft_military")
    mil = (st.payload or {}).get("aircraft", []) if st else []
    vst = collector.states.get("vip_aircraft")
    vip = (vst.payload or {}).get("aircraft", {}) if vst else {}
    body = await asyncio.to_thread(patterns.analyse, collector.trails, mil, time.time(), vip)
    body["fetched"] = st.fetched if st else None
    return JSONResponse(body, headers={"Cache-Control": "no-store"})


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
    from .lookup import store as lookup_store
    hit = lookup_store.cache_get("leaders", 30 * 86400)          # who to keep in the news rows, before the news feeds start
    if hit:
        news_window.set_watch(l["name"] for l in hit["body"])
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
    *dossier.make_routes(collector),
    Route("/api/status", status),
    Route("/api/data/{name}", data),
    Route("/api/route/{callsign}", route),
    Route("/api/trail/{hex}", trail),
    Route("/api/aircraft/patterns", flight_patterns),
    Route("/api/track/{hex}", track),
    Route("/api/photo/{hex}", photo),
    Route("/api/news/place", news_place),
    Route("/api/news/image", news_image),
    Route("/api/satellite/{norad}", satellite),
    Route("/api/imagery/date", imagery_date),
    Route("/api/eumetsat/time", eumetsat_time),
    Route("/api/ship/about", ship_about),
    Route("/api/ship/trail/{mmsi}", ship_trail),
    Route("/api/maxar/acquisitions", maxar_acq),
    Route("/api/maxar/items", maxar_items),
    Route("/api/maxar/meta", maxar_meta),
    Route("/api/maxar/tile", maxar_tile),
    Route("/api/aircraft/area", area),
    Mount(f"/s/{VERSION}", Forever(directory=STATIC)),
    Mount("/static", StaticFiles(directory=STATIC)),
])
