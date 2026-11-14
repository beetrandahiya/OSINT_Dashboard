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
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import config, db
from .collector import Collector
from .feeds import _readsb_aircraft, adsbfi_area

STATIC = Path(__file__).parent / "static"
collector = Collector()


def _process() -> dict:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    peak = ru.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)   # macOS reports bytes, Linux kilobytes
    return {"peak_memory_mb": round(peak, 1), "cpu_seconds": round(ru.ru_utime + ru.ru_stime, 2)}


async def status(request):
    s = collector.status()
    s["process"] = _process()
    return JSONResponse(s, headers={"Cache-Control": "no-store"})


async def data(request):
    st = collector.states.get(request.path_params["name"])
    if not st:
        return JSONResponse({"error": "no such feed"}, status_code=404)
    now = time.time()
    return JSONResponse({**st.public(now), "now": now, "payload": st.payload}, headers={"Cache-Control": "no-store"})


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


def page(name):
    async def serve(request):
        return FileResponse(STATIC / name, headers={"Cache-Control": "no-cache"})
    return serve


@contextlib.asynccontextmanager
async def lifespan(app):
    await collector.start()
    yield
    await collector.stop()


app = Starlette(lifespan=lifespan, middleware=[Middleware(GZipMiddleware, minimum_size=2000)], routes=[
    Route("/", page("index.html")),
    Route("/feeds", page("feeds.html")),
    Route("/api/status", status),
    Route("/api/data/{name}", data),
    Route("/api/route/{callsign}", route),
    Route("/api/trail/{hex}", trail),
    Route("/api/track/{hex}", track),
    Route("/api/photo/{hex}", photo),
    Route("/api/aircraft/area", area),
    Mount("/static", StaticFiles(directory=STATIC)),
])
