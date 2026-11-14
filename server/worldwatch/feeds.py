"""The feeds: where each layer's data comes from, how often we ask, and how we read the answer.

Rules every feed follows:
- Only what the source returned is stored. Nothing is estimated, filled in or carried forward silently.
- `data_time` is the source's own timestamp for its data. If a source gives none, it stays None and
  the screen says so; our fetch time is recorded separately and is never passed off as data time.
- Intervals respect each source's published limits (noted per feed).
"""
import asyncio
import calendar
import html
import io
import json
import re
import time
import zipfile
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any, Awaitable, Callable

import httpx

from . import config


@dataclass
class Result:
    items: int
    payload: Any
    data_time: float | None = None   # the source's own timestamp, unix seconds
    data_label: str | None = None    # shown instead of a clock time when the source dates data differently
    note: str | None = None


class Fetcher:
    """One fetch attempt: counts the bytes that really crossed the network."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.wire_bytes = 0
        self.clock_diffs: list[float] = []   # server clock minus ours, from each answer's Date header

    async def get(self, url: str, **kw) -> httpx.Response:
        t0 = time.time()
        r = await self.client.get(url, **kw)
        self.wire_bytes += r.num_bytes_downloaded
        try:
            server = parsedate_to_datetime(r.headers["date"]).timestamp()
            self.clock_diffs.append(server - (t0 + time.time()) / 2)
        except Exception:
            pass
        r.raise_for_status()
        return r


@dataclass
class Feed:
    name: str
    layer: str
    source: str
    home: str                      # the source's website, for credit and for checking by hand
    interval: int                  # seconds between fetches
    fetch: Callable[["Feed", Fetcher], Awaitable[Result]]
    stale_after: int | None = None  # data older than this (by the source's own time) is flagged late
    min_retry: int = 20            # shortest wait after a failure
    limit_note: str = ""
    memo: dict = field(default_factory=dict)   # the feed's own scratch space between fetches


def _iso(s: str) -> float:
    """'2026-11-14T09:45:00Z' or without the Z -> unix seconds (UTC)."""
    s = s.strip().replace("Z", "")
    base, _, frac = s.partition(".")
    t = calendar.timegm(time.strptime(base[:19], "%Y-%m-%dT%H:%M:%S"))
    return t + (float("0." + frac) if frac.isdigit() else 0.0)


def _readsb_aircraft(d: dict) -> list[dict]:
    """adsb.fi and adsb.lol share the readsb JSON format."""
    out = []
    for a in d.get("ac") or d.get("aircraft") or []:
        if a.get("lat") is None or a.get("lon") is None:
            continue
        flags = a.get("dbFlags") or 0
        out.append({
            "hex": a.get("hex"), "flight": (a.get("flight") or "").strip() or None,
            "reg": a.get("r"), "type": a.get("t"), "category": a.get("category"),
            "lat": a["lat"], "lon": a["lon"], "alt_ft": a.get("alt_baro"), "gs_kt": a.get("gs"),
            "track": a.get("track"), "squawk": a.get("squawk"),
            "seen_pos_s": a.get("seen_pos"),          # seconds since the last position, per the source
            "military": bool(flags & 1), "pia": bool(flags & 4), "ladd": bool(flags & 8),
        })
    return out


async def aircraft_near(feed: Feed, f: Fetcher) -> Result:
    url = f"https://opendata.adsb.fi/api/v3/lat/{config.HOME_LAT}/lon/{config.HOME_LON}/dist/{config.HOME_RADIUS_NM}"
    d = (await f.get(url)).json()
    ac = _readsb_aircraft(d)
    return Result(len(ac), {"aircraft": ac}, data_time=d["now"] / 1000)


async def aircraft_military(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://api.adsb.lol/v2/mil")).json()
    ac = _readsb_aircraft(d)
    return Result(len(ac), {"aircraft": ac}, data_time=d["now"] / 1000)


async def aircraft_world(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://opensky-network.org/api/states/all")).json()
    ac = [{"hex": s[0], "flight": (s[1] or "").strip() or None, "lon": s[5], "lat": s[6],
           "alt_m": s[7], "on_ground": s[8], "gs_ms": s[9], "track": s[10], "last_contact": s[4]}
          for s in d.get("states") or [] if s[5] is not None and s[6] is not None]
    return Result(len(ac), {"aircraft": ac}, data_time=float(d["time"]))


async def satellites(feed: Feed, f: Fetcher) -> Result:
    recs = (await f.get("https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=json")).json()
    newest = max(_iso(r["EPOCH"]) for r in recs)
    return Result(len(recs), {"omm": recs}, data_time=newest, note="data time is the newest orbit epoch")


async def launches(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=20&mode=normal")).json()
    out = []
    for r in d["results"]:
        pad = r.get("pad") or {}
        out.append({
            "id": r["id"], "name": r["name"], "net": r["net"], "status": (r.get("status") or {}).get("name"),
            "provider": (r.get("launch_service_provider") or {}).get("name"),
            "pad": pad.get("name"), "site": (pad.get("location") or {}).get("name"),
            "lat": pad.get("latitude"), "lon": pad.get("longitude"),
            "updated": r.get("last_updated"), "image": (r.get("image") or {}).get("thumbnail_url"),
        })
    upd = [_iso(x["updated"]) for x in out if x["updated"]]
    return Result(len(out), {"launches": out}, data_time=max(upd) if upd else None, note="data time is the newest edit to a launch entry")


_TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>")


def _gdelt_clusters(raw_zip: bytes) -> tuple[int, list[dict]]:
    """Group one 15-minute GDELT file by the first city-level place each article mentions.
    The count per place is the number of distinct outlets, nothing more."""
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    places: dict[str, dict] = {}
    articles = 0
    for line in text.split("\n"):
        r = line.split("\t")
        if len(r) < 27:
            continue
        articles += 1
        locs = []
        for part in r[10].split(";"):
            p = part.split("#")
            # types 3 and 4 are US and world cities; country- and state-level mentions are skipped
            # because GDELT pins them to a centroid, which would put stories in the wrong spot.
            if len(p) >= 9 and p[0] in ("3", "4") and p[5] and p[6]:
                try:
                    locs.append((int(p[8]), p[1], float(p[5]), float(p[6])))
                except ValueError:
                    pass
        m = _TITLE.search(r[26])
        if not locs or not m:
            continue
        _, name, lat, lon = min(locs)
        c = places.setdefault(name, {"place": name, "lat": lat, "lon": lon, "outlets": {}, })
        c["outlets"].setdefault(r[3], {"outlet": r[3], "title": html.unescape(m.group(1)), "url": r[4]})
    out = [{"place": c["place"], "lat": c["lat"], "lon": c["lon"], "outlets": len(c["outlets"]),
            "articles": list(c["outlets"].values())[:12]} for c in places.values()]
    out.sort(key=lambda c: -c["outlets"])
    return articles, out


async def news(feed: Feed, f: Fetcher) -> Result:
    r = await f.get("https://data.gdeltproject.org/gdeltv2/lastupdate.txt")
    listing = r.text
    # GDELT names each file after a 15-minute slot, and that name can be minutes ahead of the real
    # clock. The honest data time is when GDELT published the listing, so that is what we use.
    published = parsedate_to_datetime(r.headers["last-modified"]).timestamp()
    url = next(line.split()[2] for line in listing.splitlines() if line.endswith(".gkg.csv.zip"))
    stamp = url.rsplit("/", 1)[1][:14]
    if feed.memo.get("stamp") != stamp:
        raw = (await f.get(url.replace("http://", "https://"))).content
        articles, clusters = await asyncio.to_thread(_gdelt_clusters, raw)
        feed.memo.update(stamp=stamp, payload={"file": stamp, "articles": articles, "places": clusters}, n=len(clusters))
        note = f"new 15-minute file, {articles} articles"
    else:
        note = "no new file yet"
    feed.memo["payload"]["published"] = published
    return Result(feed.memo["n"], feed.memo["payload"], data_time=published, note=f"{note} (file {stamp}); data time is when GDELT published it")


async def quakes(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson")).json()
    out = [{"id": q["id"], "mag": q["properties"]["mag"], "place": q["properties"]["place"],
            "time": q["properties"]["time"] / 1000, "updated": q["properties"]["updated"] / 1000,
            "url": q["properties"]["url"], "lon": q["geometry"]["coordinates"][0],
            "lat": q["geometry"]["coordinates"][1], "depth_km": q["geometry"]["coordinates"][2]}
           for q in d["features"]]
    return Result(len(out), {"quakes": out}, data_time=d["metadata"]["generated"] / 1000)


async def outages(feed: Feed, f: Fetcher) -> Result:
    now = int(time.time())
    d = (await f.get(f"https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?from={now - 86400}&until={now}&limit=200")).json()
    out = [{"where": e["location_name"], "location": e["location"], "start": e["start"], "duration_s": e["duration"],
            "signal": e["datasource"], "score": e["score"]} for e in d.get("data") or []]
    return Result(len(out), {"events": out}, note="IODA gives no timestamp for the data set as a whole")


YAHOO = {"^GSPC": "S&P 500", "^GDAXI": "DAX", "^N225": "Nikkei 225", "^NSEI": "Nifty 50",
         "BZ=F": "Brent crude", "GC=F": "Gold", "EURUSD=X": "EUR/USD"}


async def markets(feed: Feed, f: Fetcher) -> Result:
    quotes, errors = [], []
    for sym, name in YAHOO.items():
        try:
            r = await f.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym.replace('^', '%5E')}?interval=1d&range=1d")
            m = r.json()["chart"]["result"][0]["meta"]
            quotes.append({"symbol": sym, "name": name, "price": m["regularMarketPrice"], "previous_close": m.get("chartPreviousClose"),
                           "currency": m.get("currency"), "time": m["regularMarketTime"], "exchange": m.get("fullExchangeName")})
        except Exception as e:  # one bad symbol must not hide the others; it is reported, not skipped silently
            errors.append(f"{sym}: {type(e).__name__}")
        await asyncio.sleep(0.3)
    if not quotes:
        raise RuntimeError("no symbol answered: " + "; ".join(errors))
    return Result(len(quotes), {"quotes": quotes, "missing": errors}, data_time=float(max(q["time"] for q in quotes)),
                  note=("missing " + ", ".join(errors)) if errors else "data time is the newest quote; each quote keeps its own")


async def crypto(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur&include_last_updated_at=true&include_24hr_change=true")).json()
    b = d["bitcoin"]
    return Result(1, {"bitcoin": b}, data_time=float(b["last_updated_at"]))


async def fx(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD,GBP,INR,CHF,JPY")).json()
    return Result(len(d["rates"]), d, data_label=f"reference rates of {d['date']}", note="the ECB publishes once per working day")


H = 3600
FEEDS = [
    Feed("aircraft_near", "Aircraft near Munich", "adsb.fi", "https://adsb.fi", 10, aircraft_near, stale_after=60,
         limit_note="limit 1 request per second; personal use"),
    Feed("aircraft_military", "Military aircraft", "adsb.lol", "https://adsb.lol", 300, aircraft_military, stale_after=900,
         limit_note="500 requests per day without a key"),
    Feed("aircraft_world", "Aircraft worldwide", "OpenSky Network", "https://opensky-network.org", 900, aircraft_world, stale_after=2700,
         limit_note="anonymous: about 100 world snapshots per day"),
    Feed("satellites", "Satellites and ISS", "CelesTrak", "https://celestrak.org", 2 * H, satellites, stale_after=3 * 86400, min_retry=1800,
         limit_note="data changes every 2 hours; asking sooner risks a block"),
    Feed("launches", "Rocket launches", "Launch Library 2", "https://thespacedevs.com", 900, launches,
         limit_note="15 requests per hour"),
    Feed("news", "News places", "GDELT", "https://www.gdeltproject.org", 120, news, stale_after=2400,
         limit_note="one new file every 15 minutes"),
    Feed("quakes", "Earthquakes", "USGS", "https://earthquake.usgs.gov", 60, quakes, stale_after=600,
         limit_note="feed regenerates every minute"),
    Feed("outages", "Internet outages", "IODA, Georgia Tech", "https://ioda.inetintel.cc.gatech.edu", 300, outages,
         limit_note="no published limit"),
    Feed("markets", "Markets", "Yahoo Finance (unofficial)", "https://finance.yahoo.com", 300, markets,
         limit_note="unofficial endpoint, delayed quotes, can break without notice"),
    Feed("crypto", "Bitcoin", "CoinGecko", "https://www.coingecko.com", 120, crypto, stale_after=900,
         limit_note="keyless public endpoint"),
    Feed("fx", "Exchange rates", "ECB via Frankfurter", "https://frankfurter.dev", H, fx,
         limit_note="daily reference rates, not live"),
]
