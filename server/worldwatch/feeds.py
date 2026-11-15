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
from pathlib import Path
from email.utils import parsedate_to_datetime
from typing import Any, Awaitable, Callable

import httpx

from . import config, translate
from . import news as news_window
from . import unrest as unrest_window
from . import navwarn
from . import airspace


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
    fetch: Callable[["Feed", Fetcher], Awaitable[Result]] | None   # None: fetched on request, not on a timer
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
            "nac_p": a.get("nac_p"), "nic": a.get("nic"),   # the aircraft's own statement of how exact its position is
        })
    return out


_adsbfi_lock, _adsbfi_last = asyncio.Lock(), 0.0


async def adsbfi_area(client: httpx.AsyncClient, lat: float, lon: float, radius_nm: int) -> tuple[dict, int]:
    """One adsb.fi request for a circle on the map. adsb.fi allows one request per second, so every caller
    goes through this gate, which keeps at least 1.2 seconds between requests."""
    global _adsbfi_last
    async with _adsbfi_lock:
        wait = 1.2 - (time.monotonic() - _adsbfi_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await client.get(f"https://opendata.adsb.fi/api/v3/lat/{lat:.4f}/lon/{lon:.4f}/dist/{radius_nm}")
        finally:
            _adsbfi_last = time.monotonic()
    r.raise_for_status()
    return r.json(), r.num_bytes_downloaded


async def aircraft_near(feed: Feed, f: Fetcher) -> Result:
    d, n = await adsbfi_area(f.client, config.HOME_LAT, config.HOME_LON, config.HOME_RADIUS_NM)
    f.wire_bytes += n
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


SAT_GROUPS = {"visual": "the brightest", "stations": "space stations", "gps-ops": "GPS", "galileo": "Galileo", "geo": "geostationary"}


async def satellites(feed: Feed, f: Fetcher) -> Result:
    """Orbit data for a few families of satellites from CelesTrak, so that low, medium and geostationary orbits
    are all on the map. One request per family, spaced out; a family that fails keeps its last good data."""
    have, problems = feed.memo.setdefault("groups", {}), []
    for i, group in enumerate(SAT_GROUPS):
        if i:
            await asyncio.sleep(2.5)
        try:
            have[group] = (await f.get(f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=json")).json()
        except Exception as e:
            problems.append(f"{SAT_GROUPS[group]} ({type(e).__name__})")
    if not have:
        raise RuntimeError("CelesTrak answered for none of the satellite families: " + ", ".join(problems))
    seen, recs = set(), []
    for group, rows in have.items():
        for r in rows:
            if r["NORAD_CAT_ID"] not in seen:
                seen.add(r["NORAD_CAT_ID"])
                recs.append(r)
    newest = max(_iso(r["EPOCH"]) for r in recs)
    return Result(len(recs), {"omm": recs, "families": {g: len(v) for g, v in have.items()}}, data_time=newest,
                  note="data time is the newest orbit epoch" + (f"; not refreshed this time: {', '.join(problems)}" if problems else ""))


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


async def news(feed: Feed, f: Fetcher) -> Result:
    """English news places over the last six hours (see news.py)."""
    got, held, expected = await news_window.english.refresh(f)
    payload = {"places": news_window.places(news_window.english), "newest": news_window.english.newest(),
               "oldest": news_window.english.oldest(), "files": held, "window_h": news_window.WINDOW // 3600}
    n = sum(len(r) for _, r in news_window.english.files.values())
    return Result(len(payload["places"]), payload, data_time=payload["newest"],
                  note=f"{n:,} articles in {held} of {expected} files of the last 6 hours"
                       + (" (still filling: a few older files per fetch)" if held < expected - 2 else "")
                       + "; data time is when GDELT published the newest file")


async def news_translated(feed: Feed, f: Fetcher) -> Result:
    """News in every other language GDELT translates, over the last six hours. The headline leading each place
    with two or more outlets is machine-translated to English now; the rest when a card is opened."""
    got, held, expected = await news_window.translated.refresh(f)
    places = news_window.places(news_window.translated)
    lead: dict[str, list[dict]] = {}
    for p in places:
        if p["outlets"] >= 3:          # only the places the list shows; the rest are translated when a card opens
            a = p["articles"][0]
            lead.setdefault(a["lang"], []).append(a)
    failed = 0
    for lang, arts in lead.items():
        english, bad = await translate.to_english(f, [a["title"] for a in arts], news_window.GOOGLE.get(lang, "auto"))
        failed += bad
        for a in arts:
            if english.get(a["title"], a["title"]) != a["title"]:
                a["title_original"], a["title"], a["translated"] = a["title"], english[a["title"]], True
    payload = {"places": places, "newest": news_window.translated.newest(), "oldest": news_window.translated.oldest(),
               "files": held, "window_h": news_window.WINDOW // 3600, "languages": news_window.NAMES}
    n = sum(len(r) for _, r in news_window.translated.files.values())
    return Result(len(places), payload, data_time=payload["newest"],
                  note=f"{n:,} articles in {held} of {expected} files of the last 6 hours, all languages GDELT translates"
                       + (" (still filling)" if held < expected - 2 else "")
                       + (f"; {failed} headlines could not be translated and stay in their language" if failed else "")
                       + (f" (Google asked us to slow down; translation pauses {int(translate.blocked() // 60)} more minutes)" if translate.blocked() else "")
                       + "; GDELT releases these about an hour late")


async def unrest(feed: Feed, f: Fetcher) -> Result:
    """Protests and clashes over the last 24 hours from GDELT's event coding (see unrest.py)."""
    ev, men, slots = await unrest_window.window.refresh(f)
    groups = unrest_window.window.groups()
    newest = max((g["last"] for g in groups), default=None)
    filling = ev < slots - 4 or men < slots - 4
    return Result(len(groups), {"groups": groups, "files": ev, "mention_files": men, "slots": slots, "window_h": 24}, data_time=newest,
                  note=f"{sum(g['outlets'] >= 2 for g in groups)} groups reported by two or more outlets, {sum(g['outlets'] < 2 for g in groups)} by one; "
                       f"{ev} of {slots} event files and {men} mention files of the last 24 hours"
                       + (" (still filling)" if filling else "") + "; machine-coded from news reports, not verified")


async def navwarn_feed(feed: Feed, f: Fetcher) -> Result:
    """Navigational warnings that report activity (firings, launches, exercises, threats); see navwarn.py.
    Two official sources; if one fails the other is still shown and the note names the one that failed."""
    out, problems, used = [], [], []
    try:
        r = await f.get("https://msi.nga.mil/api/publications/broadcast-warn", params={"output": "json", "status": "active"})
        out += navwarn.parse_nga(r.json())
        used.append("NGA")
    except Exception as e:
        problems.append(f"NGA (US, worldwide) failed: {type(e).__name__} {str(e)[:80]}")
    try:
        r = await f.get("https://msi.admiralty.co.uk/RadioNavigationalWarnings")
        out += navwarn.parse_ukho(r.text)
        used.append("UKHO")
    except Exception as e:
        problems.append(f"UKHO (UK) failed: {type(e).__name__} {str(e)[:80]}")
    if not used:
        raise RuntimeError("; ".join(problems))
    drawn = sum(1 for w in out if w["geoms"])
    return Result(len(out), {"warnings": out, "sources": used, "problems": problems}, data_time=None,
                  data_label="warnings in force when fetched",
                  note=f"{len(out)} activity warnings in force from {' and '.join(used)} ({drawn} with positions)"
                       + ("; " + "; ".join(problems) if problems else "") + "; lights, buoys and other routine notices left out")


async def airspace_feed(feed: Feed, f: Fetcher) -> Result:
    """Conflict-zone warnings (EASA, FAA) on flight regions, and US temporary flight restrictions; see airspace.py."""
    m, problems = feed.memo, []
    if time.time() - m.get("fir_at", 0) > 7 * 86400 or "fir" not in m:
        m["fir"] = (await f.get(airspace.VATSPY)).json()
        m["fir_at"] = time.time()
    zones = []
    try:
        czibs = airspace.parse_czib_list((await f.get("https://www.easa.europa.eu/en/domains/air-operations/czibs")).text)
        pages = m.setdefault("czib_pages", {})
        for c in czibs:
            if c["number"] not in pages:                       # a revision gets a new number, so a page is read once
                await asyncio.sleep(1)
                pages[c["number"]] = airspace.parse_czib_page((await f.get(c["link"])).text)
            zones.append({"id": "EASA:" + c["number"], "source": "EASA", **c, **pages[c["number"]]})
    except Exception as e:
        problems.append(f"EASA bulletins failed: {type(e).__name__} {str(e)[:80]}")
    try:
        for c in airspace.parse_faa((await f.get("https://www.faa.gov/air_traffic/publications/us_restrictions")).text):
            zones.append({"id": "FAA:" + c["country"], "source": "FAA", "title": c["country"], **c,
                          "link": "https://www.faa.gov/air_traffic/publications/us_restrictions"})
    except Exception as e:
        problems.append(f"FAA list failed: {type(e).__name__} {str(e)[:80]}")
    shapes = airspace.fir_shapes(m["fir"], {c for z in zones for c in z["firs"]})
    for z in zones:
        z["shapes"] = {c: shapes[c] for c in z["firs"] if c in shapes}
        z["unmapped"] = [c for c in z["firs"] if c not in shapes]
    tfrs, cache = [], m.setdefault("tfr", {})
    try:
        listing = (await f.get("https://tfr.faa.gov/tfrapi/exportTfrList")).json()
        for t in listing[:120]:
            nid = t.get("notam_id", "")
            if nid not in cache:
                r = await f.client.get("https://tfr.faa.gov/download/detail_" + nid.replace("/", "_") + ".xml")
                f.wire_bytes += r.num_bytes_downloaded
                cache[nid] = airspace.parse_tfr_xml(r.content.decode("utf-8-sig", "replace")) if r.status_code == 200 else None
            if cache[nid]:
                tfrs.append({"id": "TFR:" + nid, "notam": nid, "type": t.get("type"), "where": t.get("description"), **cache[nid]})
        for k in [k for k in cache if k not in {t.get("notam_id") for t in listing}]:
            del cache[k]
    except Exception as e:
        problems.append(f"US TFRs failed: {type(e).__name__} {str(e)[:80]}")
    if not zones and not tfrs:
        raise RuntimeError("; ".join(problems) or "nothing came back")
    return Result(len(zones) + len(tfrs), {"zones": zones, "tfrs": tfrs, "problems": problems}, data_label="in force when fetched",
                  note=f"{sum(z['source'] == 'EASA' for z in zones)} EASA bulletins, {sum(z['source'] == 'FAA' for z in zones)} FAA country entries, {len(tfrs)} US restrictions"
                       + ("; " + "; ".join(problems) if problems else ""))


async def quakes(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson")).json()
    out = [{"id": q["id"], "mag": q["properties"]["mag"], "place": q["properties"]["place"],
            "time": q["properties"]["time"] / 1000, "updated": q["properties"]["updated"] / 1000,
            "url": q["properties"]["url"], "lon": q["geometry"]["coordinates"][0],
            "lat": q["geometry"]["coordinates"][1], "depth_km": q["geometry"]["coordinates"][2]}
           for q in d["features"]]
    return Result(len(out), {"quakes": out}, data_time=d["metadata"]["generated"] / 1000)


_COUNTRIES = json.loads((Path(__file__).parent / "countries.json").read_text())   # ISO code -> [lon, lat, name]


async def outages(feed: Feed, f: Fetcher) -> Result:
    """Country-level outage signals of the last 24 hours. IODA also reports single networks; those are
    far too many and too local for a world view, so only whole countries are asked for."""
    now = int(time.time())
    d = (await f.get(f"https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events?from={now - 86400}&until={now}&limit=200&entityType=country")).json()
    out = []
    for e in d.get("data") or []:
        code = e["location"].split("/")[-1]
        place = _COUNTRIES.get(code)
        out.append({"id": f"{code}-{e['start']}-{e['datasource']}", "code": code, "where": e["location_name"],
                    "start": e["start"], "duration_s": e["duration"], "signal": e["datasource"], "score": e["score"],
                    # a country has no single point: the marker sits at the country's geographic centre
                    "lon": place[0] if place else None, "lat": place[1] if place else None})
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


GDACS_TYPES = {"TC": "Tropical cyclone", "FL": "Flood", "VO": "Volcano", "DR": "Drought", "WF": "Wildfire"}


async def gdacs(feed: Feed, f: Fetcher) -> Result:
    """Alerts from GDACS, the UN and EU disaster alert system. Orange and red alerts (the serious ones) are kept
    for a week after their end date, green ones for cyclones, floods and volcanoes for three days. Green
    wildfire alerts are left out (about a hundred at any time). Earthquakes are left out too: USGS has them."""
    now, out, seen = time.time(), [], set()
    day = lambda back: time.strftime("%Y-%m-%d", time.gmtime(now - back * 86400))
    for levels, types, since, keep_days in (("orange;red", "TC;FL;VO;DR;WF", day(45), 7), ("green", "TC;FL;VO", day(14), 3)):
        d = (await f.get(f"https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist={types}&alertlevel={levels}&fromdate={since}")).json()
        for x in d.get("features") or []:
            p, g = x["properties"], x.get("geometry") or {}
            key = (p["eventtype"], p["eventid"])
            if p["eventtype"] not in GDACS_TYPES or g.get("type") != "Point" or key in seen:
                continue
            end = _iso(p["todate"])
            if end < now - keep_days * 86400:
                continue
            seen.add(key)
            sev = p.get("severitydata") or {}
            out.append({"id": f"gdacs-{p['eventtype']}-{p['eventid']}", "kind": GDACS_TYPES[p["eventtype"]], "code": p["eventtype"],
                        "level": p["alertlevel"], "name": p.get("eventname") or p["name"], "title": p["name"], "countries": p.get("country"),
                        "from": _iso(p["fromdate"]), "to": end, "modified": _iso(p["datemodified"]), "severity": sev.get("severitytext"),
                        "url": (p.get("url") or {}).get("report"), "lon": g["coordinates"][0], "lat": g["coordinates"][1], "source": "GDACS"})
        await asyncio.sleep(0.5)
    newest = max((e["modified"] for e in out), default=None)
    return Result(len(out), {"events": out}, data_time=newest, note="data time is the newest edit to an alert")


EONET_KINDS = {"wildfires": ("Wildfire", "WF"), "volcanoes": ("Volcano", "VO"), "severeStorms": ("Storm", "TC"), "seaLakeIce": ("Iceberg", "IC"),
               "floods": ("Flood", "FL"), "landslides": ("Landslide", "LS"), "dustHaze": ("Dust or haze", "DH")}


async def eonet(feed: Feed, f: Fetcher) -> Result:
    """Open natural events tracked by NASA's Earth Observatory (EONET), each at its latest reported position."""
    d = (await f.get("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=14")).json()
    out = []
    for e in d.get("events") or []:
        cat = (e.get("categories") or [{}])[0].get("id")
        pts = [g for g in e.get("geometry") or [] if g.get("type") == "Point"]
        if cat not in EONET_KINDS or not pts:
            continue
        last = pts[-1]
        mag = f"{last['magnitudeValue']:g} {last['magnitudeUnit']}" if last.get("magnitudeValue") is not None else None
        out.append({"id": "eonet-" + e["id"], "kind": EONET_KINDS[cat][0], "code": EONET_KINDS[cat][1], "level": None, "name": e["title"], "title": e["title"],
                    "countries": None, "from": _iso(pts[0]["date"]), "to": None, "modified": _iso(last["date"]), "severity": mag,
                    "url": (e.get("sources") or [{}])[0].get("url"), "lon": last["coordinates"][0], "lat": last["coordinates"][1], "source": "NASA EONET",
                    "track": [g["coordinates"] for g in pts] if len(pts) > 1 else None})
    newest = max((e["modified"] for e in out), default=None)
    return Result(len(out), {"events": out}, data_time=newest, note="data time is the newest position report of an event")


async def radar(feed: Feed, f: Fetcher) -> Result:
    """Which rain radar picture is the newest. The pictures themselves are map tiles the browser loads from RainViewer."""
    d = (await f.get("https://api.rainviewer.com/public/weather-maps.json")).json()
    frames = d["radar"]["past"]
    last = frames[-1]
    return Result(len(frames), {"host": d["host"], "path": last["path"], "time": last["time"]}, data_time=float(last["time"]))


async def space_weather(feed: Feed, f: Fetcher) -> Result:
    """NOAA's planetary K index (how disturbed Earth's magnetic field is, 0 to 9) and the aurora forecast grid,
    cut down to the cells where NOAA gives aurora a 10 % chance or more."""
    kp = (await f.get("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")).json()
    rows = [r for r in kp if isinstance(r, dict)] or [dict(zip(kp[0], r)) for r in kp[1:]]     # NOAA has used both shapes
    last = rows[-1]
    a = (await f.get("https://services.swpc.noaa.gov/json/ovation_aurora_latest.json")).json()
    cells = [[lon, lat, p] for lon, lat, p in a["coordinates"] if p >= 3]     # lon 0..359, lat -90..90, percent
    obs = _iso(a["Observation Time"])
    return Result(len(cells), {"kp": float(last["Kp"]), "kp_time": _iso(last["time_tag"]), "kp_history": [[_iso(r["time_tag"]), float(r["Kp"])] for r in rows[-16:]],
                               "aurora": cells, "aurora_observed": obs, "aurora_valid": _iso(a["Forecast Time"])},
                  data_time=obs, note="data time is the aurora observation; the K index is a 3-hour value")


async def cables(feed: Feed, f: Fetcher) -> Result:
    d = (await f.get("https://www.submarinecablemap.com/api/v3/cable/cable-geo.json")).json()
    feats = [{"type": "Feature", "geometry": x["geometry"], "properties": {"id": "cable:" + x["properties"]["id"], "name": x["properties"]["name"]}}
             for x in d["features"] if x.get("geometry")]
    return Result(len({x["properties"]["id"] for x in feats}), {"type": "FeatureCollection", "features": feats},
                  note="a map that changes rarely; the source gives no timestamp")


async def gps_interference(feed: Feed, f: Fetcher) -> Result:
    """GPSJAM's daily map: for each hexagon of the world, how many aircraft passing through reported good and
    how many reported poor navigation accuracy. We keep GPSJAM's own two bands: more than 10 % poor (high)
    and 2 to 10 % poor (some). Hexagons with fewer than 5 aircraft that day are left out as too thin to judge."""
    import csv
    import h3
    manifest = (await f.get("https://gpsjam.org/data/manifest.csv")).text.strip().splitlines()
    day = manifest[-1].split(",")[0]
    if feed.memo.get("day") != day:
        text = (await f.get(f"https://gpsjam.org/data/{day}-h3_4.csv")).text

        def build():
            feats = []
            for row in csv.DictReader(io.StringIO(text)):
                good, bad = int(row["count_good_aircraft"]), int(row["count_bad_aircraft"])
                total = good + bad
                if total < 5 or bad / total <= 0.02:
                    continue
                ring = [[lon, lat] for lat, lon in h3.cell_to_boundary(row["hex"])]
                lons = [p[0] for p in ring]
                if max(lons) - min(lons) > 180:          # a hexagon across the date line: keep it on one side
                    ring = [[lon + 360 if lon < 0 else lon, lat] for lon, lat in ring]
                ring.append(ring[0])
                feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                              "properties": {"id": "gps:" + row["hex"], "good": good, "bad": bad, "level": "high" if bad / total > 0.10 else "some"}})
            return feats

        feats = await asyncio.to_thread(build)
        feed.memo.update(day=day, payload={"day": day, "type": "FeatureCollection", "features": feats}, n=len(feats))
    end_of_day = calendar.timegm(time.strptime(day, "%Y-%m-%d")) + 86400
    return Result(feed.memo["n"], feed.memo["payload"], data_time=float(end_of_day), data_label=f"the whole day of {day} (UTC)",
                  note="one map per day, published the day after")


async def munich_weather(feed: Feed, f: Fetcher) -> Result:
    """Current weather and official warnings for Munich from the German Weather Service (DWD), through Bright Sky."""
    w = (await f.get(f"https://api.brightsky.dev/current_weather?lat={config.HOME_LAT}&lon={config.HOME_LON}")).json()
    a = (await f.get(f"https://api.brightsky.dev/alerts?lat={config.HOME_LAT}&lon={config.HOME_LON}")).json()
    cur, station = w["weather"], (w.get("sources") or [{}])[0]
    alerts = [{"id": x["id"], "event": x.get("event_en"), "headline": x.get("headline_en") or x.get("headline_de"),
               "description": x.get("description_en") or x.get("description_de"), "severity": x.get("severity"),
               "onset": _iso(x["onset"][:19]) if x.get("onset") else None, "expires": _iso(x["expires"][:19]) if x.get("expires") else None}
              for x in a.get("alerts") or []]
    return Result(len(alerts), {"now": {k: cur.get(k) for k in ("temperature", "condition", "icon", "wind_speed_10", "wind_direction_10", "wind_gust_speed_10",
                                                                 "relative_humidity", "pressure_msl", "cloud_cover", "precipitation_60", "visibility")},
                               "observed": _iso(cur["timestamp"][:19]), "station": station.get("station_name"), "alerts": alerts},
                  data_time=_iso(cur["timestamp"][:19]), note="items = official warnings in force or announced")


_TAG = re.compile(r"<[^>]+>")


async def mvg(feed: Feed, f: Fetcher) -> Result:
    """Disruption messages for Munich's U-Bahn, S-Bahn, tram and bus, from the feed behind mvg.de. That feed
    is not an official public service, so it can change or vanish without notice."""
    d = (await f.get("https://www.mvg.de/api/bgw-pt/v3/messages")).json()
    now, out = time.time() * 1000, []
    for m in d:
        start, end = float(m.get("validFrom") or 0), float(m.get("validTo") or 0)
        if not (start <= now and (not end or now <= end)):
            continue
        lines = list(dict.fromkeys(x["label"] for x in m.get("lines") or [] if x.get("label")))
        out.append({"id": str(m.get("publication")) + ":" + (m.get("title") or "")[:40], "title": m.get("title"), "kind": m.get("type"),
                    "text": html.unescape(_TAG.sub(" ", m.get("description") or "")).strip()[:600],
                    "lines": lines, "transport": sorted({x.get("transportType") for x in m.get("lines") or [] if x.get("transportType")}),
                    "from": start / 1000, "to": end / 1000 if end else None, "published": float(m.get("publication") or 0) / 1000})
    rail = {"SBAHN", "UBAHN", "TRAM"}
    out.sort(key=lambda m: (m["kind"] != "INCIDENT", not (rail & set(m["transport"])), -m["published"]))
    incidents = sum(1 for m in out if m["kind"] == "INCIDENT")
    # The first screenful gets an English headline by machine translation; the German stays beside it.
    english, _ = await translate.to_english(f, [m["title"] for m in out[:30] if m["title"]], "de")
    for m in out[:30]:
        if english.get(m["title"], m["title"]) != m["title"]:
            m["title_original"], m["title"] = m["title"], english[m["title"]]
    newest = max((m["published"] for m in out), default=None)
    return Result(incidents, {"messages": out, "incidents": incidents}, data_time=newest,
                  note=f"{incidents} incidents and {len(out) - incidents} planned changes in force; data time is the newest message")


async def fires(feed: Feed, f: Fetcher) -> Result:
    """Fire detections of the last 24 hours from NASA's FIRMS (the MODIS instruments on the Terra and Aqua
    satellites, about 1 km resolution). Each row is one hot pixel a satellite saw as it passed over."""
    import csv
    r = await f.get("https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv")
    published = parsedate_to_datetime(r.headers["last-modified"]).timestamp()
    pts = []
    for row in csv.DictReader(io.StringIO(r.text)):
        try:
            t = calendar.timegm(time.strptime(row["acq_date"] + row["acq_time"].zfill(4), "%Y-%m-%d%H%M"))
            pts.append([round(float(row["longitude"]), 4), round(float(row["latitude"]), 4), round(float(row["frp"]), 1),
                        int(row["confidence"]), t, row["satellite"], row["daynight"]])
        except (ValueError, KeyError):
            continue
    return Result(len(pts), {"points": pts, "published": published, "fields": ["lon", "lat", "power_mw", "confidence", "time", "satellite", "daynight"]},
                  data_time=published, note="data time is when NASA last rebuilt the file")


SHIP_TYPES = {30: "Fishing vessel", 31: "Tug", 32: "Tug", 33: "Dredger", 35: "Military vessel", 36: "Sailing vessel", 37: "Pleasure craft",
              50: "Pilot vessel", 51: "Search and rescue vessel", 52: "Tug", 53: "Port tender", 55: "Law enforcement vessel", 58: "Medical transport"}


def _ship_type(code) -> str | None:
    if code is None:
        return None
    if code in SHIP_TYPES:
        return SHIP_TYPES[code]
    return {4: "High-speed craft", 6: "Passenger ship", 7: "Cargo ship", 8: "Tanker"}.get(code // 10)


async def ships(feed: Feed, f: Fetcher) -> Result:
    """Ships in and around Finnish waters and the northern Baltic, from Finland's open maritime data service
    (Digitraffic). It is the one free ship feed that needs no key; world coverage needs an aisstream.io key."""
    hdr = {"Digitraffic-User": "WorldWatch/personal"}
    now = time.time()
    if now - feed.memo.get("names_at", 0) > 6 * 3600:        # names, types and destinations change rarely
        v = (await f.get("https://meri.digitraffic.fi/api/ais/v1/vessels", headers=hdr)).json()
        feed.memo.update(names={x["mmsi"]: x for x in v}, names_at=now)
    d = (await f.get("https://meri.digitraffic.fi/api/ais/v1/locations", headers=hdr)).json()
    names, out = feed.memo["names"], []
    for x in d["features"]:
        p, at = x["properties"], x["properties"]["timestampExternal"] / 1000
        if now - at > 1800:                                    # a position older than half an hour says little about now
            continue
        n = names.get(p["mmsi"], {})
        out.append({"mmsi": p["mmsi"], "lon": x["geometry"]["coordinates"][0], "lat": x["geometry"]["coordinates"][1],
                    "speed_kn": p.get("sog"), "course": p.get("cog") if (p.get("cog") or 0) < 360 else None,
                    "heading": p.get("heading") if (p.get("heading") or 511) < 360 else None, "status": p.get("navStat"), "time": at,
                    "name": (n.get("name") or "").strip() or None, "kind": _ship_type(n.get("shipType")), "callsign": n.get("callSign"),
                    "destination": (n.get("destination") or "").strip() or None, "imo": n.get("imo") or None, "draught_m": (n.get("draught") or 0) / 10 or None})
    newest = max((s["time"] for s in out), default=None)
    return Result(len(out), {"ships": out}, data_time=newest, note="data time is the newest position; positions older than 30 minutes are dropped")


H = 3600
FEEDS = [
    Feed("aircraft_near", "Aircraft near Munich", "adsb.fi", "https://adsb.fi", 20, aircraft_near, stale_after=90,
         limit_note="limit 1 request per second, shared with the area you are looking at"),
    Feed("aircraft_view", "Aircraft where you are looking", "adsb.fi", "https://adsb.fi", 10, None,
         limit_note="fetched on request, at most every 8 seconds, only while a page is zoomed in"),
    Feed("aircraft_military", "Military aircraft", "adsb.lol", "https://adsb.lol", 300, aircraft_military, stale_after=900,
         limit_note="500 requests per day without a key"),
    Feed("aircraft_world", "Aircraft worldwide", "OpenSky Network", "https://opensky-network.org", 1200, aircraft_world, stale_after=3600,
         limit_note="every 20 minutes: the free daily allowance is shared with flight-path lookups"),
    Feed("satellites", "Satellites and ISS", "CelesTrak", "https://celestrak.org", 2 * H, satellites, stale_after=3 * 86400, min_retry=1800,
         limit_note="data changes every 2 hours; asking sooner risks a block"),
    Feed("launches", "Rocket launches", "Launch Library 2", "https://thespacedevs.com", 900, launches,
         limit_note="15 requests per hour"),
    Feed("news", "News places", "GDELT", "https://www.gdeltproject.org", 120, news, stale_after=3600,
         limit_note="one new file every 15 minutes; kept 6 hours"),
    Feed("news_translated", "News in other languages", "GDELT", "https://www.gdeltproject.org", 300, news_translated, stale_after=3 * H,
         limit_note="one 8 MB file every 15 minutes, released about an hour late; kept 6 hours"),
    Feed("unrest", "Protests and clashes", "GDELT events", "https://www.gdeltproject.org", 120, unrest, stale_after=3600,
         limit_note="one small events file and one mentions file every 15 minutes; kept 24 hours"),
    Feed("navwarn", "Navy warnings at sea", "NGA and UKHO", "https://msi.nga.mil/NavWarnings", 1800, navwarn_feed, stale_after=6 * H,
         limit_note="official warning lists; asked every 30 minutes"),
    Feed("airspace", "Airspace warnings and closures", "EASA, FAA", "https://www.easa.europa.eu/en/domains/air-operations/czibs", 3600, airspace_feed,
         stale_after=12 * H, min_retry=600, limit_note="official lists, asked hourly; flight-region outlines from VATSpy (community, CC BY-SA)"),
    Feed("quakes", "Earthquakes", "USGS", "https://earthquake.usgs.gov", 60, quakes, stale_after=600,
         limit_note="feed regenerates every minute"),
    Feed("gdacs", "Disaster alerts", "GDACS (UN and EU)", "https://www.gdacs.org", 600, gdacs,
         limit_note="no published limit"),
    Feed("eonet", "Natural events", "NASA EONET", "https://eonet.gsfc.nasa.gov", 1800, eonet,
         limit_note="no published limit"),
    Feed("radar", "Rain radar", "RainViewer", "https://www.rainviewer.com", 300, radar, stale_after=1800,
         limit_note="a new picture every 10 minutes"),
    Feed("space_weather", "Space weather and aurora", "NOAA SWPC", "https://www.swpc.noaa.gov", 600, space_weather, stale_after=3 * H,
         limit_note="aurora forecast updates about every 5 minutes"),
    Feed("cables", "Undersea cables", "TeleGeography", "https://www.submarinecablemap.com", 7 * 86400, cables, min_retry=600,
         limit_note="fetched once a week; licence CC BY-NC-SA, private use only"),
    Feed("gps", "GPS interference", "GPSJAM", "https://gpsjam.org", 6 * H, gps_interference, min_retry=600,
         limit_note="one file per day; worked out by GPSJAM from aircraft reports"),
    Feed("munich_weather", "Munich weather and warnings", "DWD via Bright Sky", "https://brightsky.dev", 600, munich_weather, stale_after=2 * H,
         limit_note="no published limit"),
    Feed("mvg", "Munich transport disruptions", "MVG (unofficial feed)", "https://www.mvg.de", 300, mvg,
         limit_note="the feed behind mvg.de; not an official service, can break"),
    Feed("fires", "Fire detections", "NASA FIRMS", "https://firms.modaps.eosdis.nasa.gov", 1800, fires, stale_after=6 * H,
         limit_note="NASA rebuilds the 24-hour file several times an hour"),
    Feed("ships_world", "Ships worldwide", "aisstream.io", "https://aisstream.io", 60, None,
         limit_note="live stream from volunteer receivers; needs a free key in data/aisstream-key.txt"),
    Feed("ships", "Ships (northern Baltic)", "Digitraffic, Finland", "https://www.digitraffic.fi/en/marine-traffic/", 60, ships, stale_after=900,
         limit_note="open data, no key; Finnish coverage area only"),
    Feed("outages", "Internet outages", "IODA, Georgia Tech", "https://ioda.inetintel.cc.gatech.edu", 300, outages,
         limit_note="no published limit; country-level signals only"),
    Feed("markets", "Markets", "Yahoo Finance (unofficial)", "https://finance.yahoo.com", 300, markets,
         limit_note="unofficial endpoint, delayed quotes, can break without notice"),
    Feed("crypto", "Bitcoin", "CoinGecko", "https://www.coingecko.com", 120, crypto, stale_after=900,
         limit_note="keyless public endpoint"),
    Feed("fx", "Exchange rates", "ECB via Frankfurter", "https://frankfurter.dev", H, fx,
         limit_note="daily reference rates, not live"),
]
