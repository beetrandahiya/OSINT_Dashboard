"""The local web server: the status page and a small JSON API. Nothing here calls the outside world;
the browser only ever talks to this process."""
import contextlib
import resource
import sys
import time
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

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


async def index(request):
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@contextlib.asynccontextmanager
async def lifespan(app):
    await collector.start()
    yield
    await collector.stop()


app = Starlette(lifespan=lifespan, routes=[
    Route("/", index),
    Route("/api/status", status),
    Route("/api/data/{name}", data),
    Mount("/static", StaticFiles(directory=STATIC)),
])
