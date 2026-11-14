"""The local web server: the status page and a small JSON API. Nothing here calls the outside world;
the browser only ever talks to this process."""
import asyncio
import contextlib
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
    key = "route:" + callsign
    hit = await asyncio.to_thread(db.lookup_get, key, 86400)
    if not hit:
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get(f"https://api.adsbdb.com/v0/callsign/{callsign}")
            fr = r.json().get("response", {}).get("flightroute") if r.status_code == 200 else None
            body = None
            if isinstance(fr, dict):
                port = lambda a: {"iata": a.get("iata_code"), "name": a.get("name"), "city": a.get("municipality"), "country": a.get("country_name")}
                body = {"airline": (fr.get("airline") or {}).get("name"), "origin": port(fr["origin"]), "destination": port(fr["destination"])}
            elif r.status_code not in (200, 404):
                return JSONResponse({"error": f"adsbdb answered {r.status_code}"}, status_code=502)
            hit = {"fetched": time.time(), "body": body}
            await asyncio.to_thread(db.lookup_put, key, hit["fetched"], body)
        except httpx.HTTPError as e:
            return JSONResponse({"error": f"adsbdb could not be reached ({type(e).__name__})"}, status_code=502)
    return JSONResponse({"callsign": callsign, "route": hit["body"], "fetched": hit["fetched"], "now": time.time()})


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
    Mount("/static", StaticFiles(directory=STATIC)),
])
