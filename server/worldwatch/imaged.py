"""Which civil imaging satellites actually captured a place: the public catalogues of Sentinel-1 (radar, ASF),
Sentinel-2 (optical, Copernicus Data Space STAC) and Landsat 8/9 (optical, USGS LandsatLook STAC). No keys.

Each capture comes with its outline, time, cloud cover (optical) and the catalogue's own preview picture. These are
real acquisitions, unlike the spy-satellite passes, which only say a satellite could have looked."""
import asyncio
import re
import time

import httpx

from . import config

ASF = "https://api.daac.asf.alaska.edu/services/search/param"
CDSE = "https://stac.dataspace.copernicus.eu/v1/search"
USGS = "https://landsatlook.usgs.gov/stac-server/search"
PICTURE_HOSTS = ("datapool.asf.alaska.edu", "datahub.creodias.eu", "landsatlook.usgs.gov")
_seen: dict[str, float] = {}       # preview addresses we handed out (the proxy serves only those)
_cache: dict[str, tuple[float, dict]] = {}


def _iso(t: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()


def _remember(u: str | None) -> str | None:
    if u:
        _seen[u] = time.time()
        if len(_seen) > 5000:
            for k, v in sorted(_seen.items(), key=lambda kv: kv[1])[:2500]:
                _seen.pop(k, None)
    return u


def allowed(u: str) -> bool:
    host = re.sub(r"^https?://([^/]+).*", r"\1", u or "")
    return host in PICTURE_HOSTS and u in _seen


async def _sentinel1(c: httpx.AsyncClient, lat: float, lon: float, start: str) -> list[dict]:
    r = await c.get(ASF, params={"intersectsWith": f"POINT({lon} {lat})", "platform": "Sentinel-1", "processingLevel": "GRD_HD,GRD_MD,GRD_MS,GRD_FD",
                                 "start": start, "output": "geojson", "maxResults": 60})
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        p = f["properties"]
        out.append({"sat": p.get("platform"), "kind": "radar", "time": _iso(p["startTime"]), "geometry": f.get("geometry"),
                    "mode": p.get("beamModeType"), "direction": (p.get("flightDirection") or "").lower(), "track": p.get("pathNumber"),
                    "resolution": "10-20 m" if p.get("beamModeType") in ("IW", "SM") else "40 m", "polarisation": p.get("polarization"),
                    "preview": _remember((p.get("browse") or [None])[0]), "id": p.get("sceneName"),
                    "page": f"https://search.asf.alaska.edu/#/?searchType=List%20Search&searchList={p.get('sceneName')}"})
    return out


async def _stac(c: httpx.AsyncClient, url: str, coll: str, lat: float, lon: float, start: str, end: str, label: str, res: str) -> list[dict]:
    r = await c.post(url, json={"collections": [coll], "intersects": {"type": "Point", "coordinates": [lon, lat]},
                                "datetime": f"{start}/{end}", "limit": 60})
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        p, a = f["properties"], f.get("assets", {})
        prev = (a.get("thumbnail") or a.get("reduced_resolution_browse") or {}).get("href")
        sat = re.sub(r"^sentinel-(\w+)$", lambda m: "Sentinel-" + m.group(1).upper(), p.get("platform") or label).replace("LANDSAT_", "Landsat ")
        out.append({"sat": sat, "kind": "optical",
                    "time": _iso(p["datetime"]), "geometry": f.get("geometry"), "cloud": p.get("eo:cloud_cover"), "resolution": res,
                    "sun": p.get("view:sun_elevation"), "preview": _remember(prev), "id": f.get("id"),
                    "page": (f"https://browser.dataspace.copernicus.eu/?zoom=10&lat={lat}&lng={lon}" if "copernicus" in url
                             else f"https://landsatlook.usgs.gov/explore?sat=LANDSAT&lat={lat}&lng={lon}&z=9")})
    return out


async def search(lat: float, lon: float, days: int = 30) -> dict:
    key = f"{round(lat, 2)}:{round(lon, 2)}:{days}"
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start, end = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": config.USER_AGENT}) as c:
        jobs = {"Sentinel-1 (ASF)": _sentinel1(c, lat, lon, start),
                "Sentinel-2 (Copernicus)": _stac(c, CDSE, "sentinel-2-l2a", lat, lon, start, end, "Sentinel-2", "10 m"),
                "Landsat 8/9 (USGS)": _stac(c, USGS, "landsat-c2l2-sr", lat, lon, start, end, "Landsat", "30 m")}
        got = await asyncio.gather(*jobs.values(), return_exceptions=True)
    caps, failed = [], []
    for name, res in zip(jobs, got):
        if isinstance(res, Exception):
            failed.append(f"{name}: {type(res).__name__}")
        else:
            caps += res
    # one scene can be listed twice (two processing levels or tiles of the same pass): keep one per satellite and minute
    seen, uniq = set(), []
    for x in sorted(caps, key=lambda x: -x["time"]):
        k = (x["sat"], int(x["time"] // 60))
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    body = {"lat": lat, "lon": lon, "days": days, "captures": uniq, "failed": failed, "asked": time.time()}
    if not failed:
        _cache[key] = (time.time(), body)
        if len(_cache) > 300:
            _cache.clear()
    return body
