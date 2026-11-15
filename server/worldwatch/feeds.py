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
from . import satinfo
from . import flags
from . import maxar
from . import usni
from . import geo, travel, courts


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
    owners = feed.memo.setdefault("owners", {})
    if time.time() - feed.memo.get("owners_at", 0) > 86400:
        for group in SAT_GROUPS:
            await asyncio.sleep(2.5)
            try:
                for x in (await f.get("https://celestrak.org/satcat/records.php", params={"GROUP": group, "FORMAT": "json"})).json():
                    owners[x["NORAD_CAT_ID"]] = x.get("OWNER")
            except Exception:
                pass
        feed.memo["owners_at"] = time.time()
    seen, recs = set(), []
    for group, rows in have.items():
        for r in rows:
            if r["NORAD_CAT_ID"] not in seen:
                seen.add(r["NORAD_CAT_ID"])
                recs.append(r)
    newest = max(_iso(r["EPOCH"]) for r in recs)
    for r in recs:
        if owners.get(r["NORAD_CAT_ID"]):
            r["OWNER"] = owners[r["NORAD_CAT_ID"]]
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
            "orbit": ((r.get("mission") or {}).get("orbit") or {}).get("name"),
            "mission": ((r.get("mission") or {}).get("description") or "")[:600] or None,
            "window": [r.get("window_start"), r.get("window_end")],
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
                       + (" (still filling)" if filling else "")
                       + f"; {unrest_window.window.dropped_by_theme} groups left out because their articles' GDELT themes are about something else"
                       + "; machine-coded from news reports, not verified")


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
    if time.time() - m.get("fir_at", 0) > 7 * 86400 or "fir_raw" not in m:
        # kept compressed (~0.5 MB): parsed, the 2.3 MB file took tens of MB of memory for the whole week
        import zlib
        m["fir_raw"] = zlib.compress((await f.get(airspace.VATSPY)).content, 6)
        m["fir_at"] = time.time()
        m.pop("fir_shapes", None)
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
    want = frozenset(c for z in zones for c in z["firs"])
    if m.get("fir_shapes", (None,))[0] != want:            # parse the boundaries only when the set of regions changes
        import zlib
        m["fir_shapes"] = (want, await asyncio.to_thread(_in_child, airspace.fir_shapes_raw, m["fir_raw"], set(want)))
    shapes = m["fir_shapes"][1]
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


_VIP_CATS = {"Doomsday", "Governments", "Dictator Alert", "Don't you know who I am?", "Radiohead", "Royal Aircraft"}
_VIP_WORDS = re.compile(r"head of state|president|prime minister|royal flight|air force one|potus|executive transport|\bvip\b|\bking\b|emir|sultan|royal family|chancellor", re.I)
_VIP_MIL = {"Toy Soldiers", "USAF", "United States Marine Corps", "United States Navy", "Other Navies", "GAF", "RAF", "Other Air Forces", "Army Air Corps"}
_VIP_STRONG = re.compile(r"head of state|president|prime minister|royal flight|air force one|potus|\bking\b|emir|sultan|royal family|chancellor|government", re.I)
_VIP_NOT = {"Coastguard", "Aerial Firefighter", "Dogs with Jobs", "Flying Doctors", "Police Forces", "Historic"}


async def vip_aircraft(feed: Feed, f: Fetcher) -> Result:
    """Government, head-of-state and VIP aircraft by transponder address, from plane-alert-db (volunteer-kept,
    ODbL). Only the list; their positions come from the aircraft feeds we already have."""
    import csv
    text = (await f.get("https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/plane-alert-db.csv")).text
    out = {}
    for x in csv.DictReader(io.StringIO(text)):
        tags = " ".join(x.get(k) or "" for k in ("$Tag 1", "$#Tag 2", "$#Tag 3", "$Operator"))
        cat = x.get("Category") or ""
        if re.search(r"Doomsday|Nightwatch|Looking Glass", tags) and not re.search(r"Trainer|Atmospheric", tags):
            cat = "Doomsday"                     # airborne nuclear command posts (E-4B, E-6B, Il-86/Il-76 VKP, Tu-214SR)
        military = cat in _VIP_MIL
        if cat in _VIP_CATS or (cat not in _VIP_NOT and (_VIP_STRONG if military else _VIP_WORDS).search(tags)):
            hex_ = (x.get("$ICAO") or "").strip().lower()
            if re.fullmatch(r"[0-9a-f]{6}", hex_):
                out[hex_] = {"reg": x.get("$Registration") or None, "operator": x.get("$Operator") or None, "type": x.get("$Type") or None,
                             "category": cat, "tags": [t for t in (x.get("$Tag 1"), x.get("$#Tag 2"), x.get("$#Tag 3")) if t], "link": x.get("$#Link") or None}
    return Result(len(out), {"aircraft": out}, data_label="list as of this fetch",
                  note=f"{len(out)} government, head-of-state and VIP aircraft out of the list's {text.count(chr(10)) - 1:,}")


def _in_child(fn, *args):
    """Run a heavy one-off parse in a short-lived child process: Python keeps memory it has used, so a 25 MB parse
    in the server would stay in the server for good. In a child, the memory goes back when it exits."""
    import concurrent.futures
    import multiprocessing
    with concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn")) as pool:
        return pool.submit(fn, *args).result(timeout=300)


async def sat_catalog(feed: Feed, f: Fetcher) -> Result:
    """What each satellite does (UCS Satellite Database). The full rows are kept on disk for satellite cards;
    the map gets one word per satellite."""
    raw = (await f.get(satinfo.UCS_URL)).content
    compact, n, spies = await asyncio.to_thread(_in_child, satinfo.parse_save_compact, raw)
    return Result(n, {"purpose": compact}, data_label="UCS database, last updated May 2023",
                  note=f"{n:,} satellites with a stated purpose; {spies} are military imaging, radar, signals or early-warning")


async def recon_sats(feed: Feed, f: Fetcher) -> Result:
    """Orbits of military imaging and signals satellites: public ones from CelesTrak, classified US ones as
    tracked by amateur observers (McCants' classfd.tle)."""
    ucs = satinfo.load()
    if not ucs:                                    # first start: the purpose list decides which orbits to keep
        raw = (await f.get(satinfo.UCS_URL)).content
        await asyncio.to_thread(_in_child, satinfo.parse_save_compact, raw)
        ucs = satinfo.load()
    want = {k for k, v in ucs.items() if satinfo.spy(v)}
    had_ucs = bool(ucs)
    del ucs
    omm, problems, sources = [], [], {}
    try:
        import csv
        text = (await f.get("https://celestrak.org/NORAD/elements/gp.php", params={"GROUP": "active", "FORMAT": "csv"})).text
        rows = [satinfo.omm_from_csv_row(r) for r in csv.DictReader(io.StringIO(text)) if r.get("NORAD_CAT_ID", "").isdigit() and int(r["NORAD_CAT_ID"]) in want]
        for o in rows:
            o["SOURCE"] = "CelesTrak"
        omm += rows
        sources["CelesTrak"] = len(rows)
    except Exception as e:
        # The full active list is large; when it fails, ask for the main military families by name instead.
        got = 0
        for name in ("YAOGAN", "COSMOS", "USA", "GAOFEN", "OFEQ", "SAR-LUPE", "CSO", "RISAT", "IGS", "HELIOS", "TJS", "SJ-", "GEOEYE"):
            await asyncio.sleep(2.5)
            try:
                r = await f.client.get("https://celestrak.org/NORAD/elements/gp.php", params={"NAME": name, "FORMAT": "json"})
                f.wire_bytes += r.num_bytes_downloaded
                rows = [dict(o, SOURCE="CelesTrak") for o in r.json() if o["NORAD_CAT_ID"] in want] if r.status_code == 200 else []
            except (httpx.HTTPError, ValueError):
                continue
            have = {o["NORAD_CAT_ID"] for o in omm}
            rows = [o for o in rows if o["NORAD_CAT_ID"] not in have]
            omm += rows
            got += len(rows)
        sources["CelesTrak"] = got
        problems.append(f"CelesTrak's full active list failed ({type(e).__name__}); asked by family name instead")
    try:
        amateur = await asyncio.to_thread(satinfo.parse_mccants, (await f.get(satinfo.MCCANTS_URL)).content)
        have = {o["NORAD_CAT_ID"] for o in omm}
        amateur = [dict(o, SOURCE="amateur observers") for o in amateur if o["NORAD_CAT_ID"] not in have]
        omm += amateur
        sources["amateur observers"] = len(amateur)
    except Exception as e:
        problems.append(f"amateur list failed ({type(e).__name__})")
    if not omm:
        raise RuntimeError("; ".join(problems) or "no orbits")
    return Result(len(omm), {"omm": omm, "sources": sources}, data_time=max(_iso(o["EPOCH"]) for o in omm),
                  note=", ".join(f"{n} from {k}" for k, n in sources.items()) + ("; " + "; ".join(problems) if problems else "")
                       + ("" if had_ucs else "; the UCS purpose list has not been loaded yet, so only amateur-tracked classified satellites are here"))


async def flag_tables(feed: Feed, f: Fetcher) -> Result:
    """The official country allocations behind the flags: aircraft address blocks (ICAO Annex 10, via tar1090), ship
    MMSI country digits (ITU, via Wikidata), and CelesTrak's satellite owner codes."""
    problems, out = [], {}
    try:
        out["icao"] = flags.parse_icao((await f.get("https://raw.githubusercontent.com/wiedehopf/tar1090/master/html/flags.js")).text)
    except Exception as e:
        problems.append(f"aircraft table ({type(e).__name__})")
    try:
        q = "SELECT ?mid ?c ?cLabel ?iso WHERE { ?c wdt:P2979 ?mid. OPTIONAL { ?c wdt:P297 ?iso } SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } }"
        r = await f.get("https://query.wikidata.org/sparql", params={"query": q}, headers={"Accept": "application/sparql-results+json"})
        out["mid"] = flags.parse_mid(r.json()["results"]["bindings"])
    except Exception as e:
        problems.append(f"ship table ({type(e).__name__})")
    try:
        out["owners"] = flags.parse_owner_codes((await f.get("https://celestrak.org/satcat/sources.php")).text)
    except Exception as e:
        problems.append(f"satellite owner codes ({type(e).__name__})")
    old = feed.memo.get("last") or {}
    for k in ("icao", "mid", "owners"):                        # a table that failed this time keeps its last good copy
        if k not in out and k in old:
            out[k] = old[k]
    if not out:
        raise RuntimeError("; ".join(problems))
    feed.memo["last"] = out
    return Result(sum(len(v) for v in out.values()), out, data_label="allocation tables",
                  note=f"{len(out.get('icao', []))} aircraft address blocks, {len(out.get('mid', {}))} ship flag codes, {len(out.get('owners', {}))} satellite owner codes"
                       + ("; not refreshed: " + ", ".join(problems) if problems else ""))


async def maxar_events(feed: Feed, f: Fetcher) -> Result:
    """The disasters Maxar has released free imagery for: name, area and dates of each event (see maxar.py)."""
    cat = (await f.get(maxar.BASE + "catalog.json")).json()
    kids = [l["href"] for l in cat.get("links", []) if l.get("rel") == "child"]
    have = feed.memo.setdefault("events", {})
    for href in kids:
        eid = href.strip("./").split("/")[0]
        if eid in have:
            continue
        await asyncio.sleep(0.3)
        try:
            c = (await f.get(maxar.BASE + eid + "/collection.json")).json()
        except Exception:
            continue
        ext = c.get("extent", {})
        box = (ext.get("spatial", {}).get("bbox") or [[None] * 4])[0]
        when = (ext.get("temporal", {}).get("interval") or [[None, None]])[0]
        have[eid] = {"id": eid, "title": c.get("title") or maxar.quiet_title(eid), "bbox": box, "start": when[0], "end": when[1],
                     "acquisitions": sum(1 for l in c.get("links", []) if l.get("rel") == "child")}
    events = sorted(have.values(), key=lambda e: e["end"] or "", reverse=True)
    return Result(len(events), {"events": events}, data_time=_iso(events[0]["end"].replace(" ", "T")) if events and events[0]["end"] else None,
                  note=f"{len(events)} events with free sharp imagery; newest pictures {events[0]['end'][:10] if events and events[0]['end'] else 'unknown'}")


async def usni_fleet(feed: Feed, f: Fetcher) -> Result:
    """US carriers and amphibious assault ships by region or port, from USNI News' weekly Fleet Tracker (see usni.py)."""
    r = await f.get(usni.FEED, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"})
    d = await asyncio.to_thread(usni.parse, r.text)
    placed = sum(1 for s in d["ships"] if s["lat"] is not None)
    return Result(len(d["ships"]), d, data_time=d["published"],
                  note=f"{d['title']}: {len(d['ships'])} carriers and amphibious assault ships, {placed} placed by region or port (approximate)")


_EMS = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/"
_EMS_COG = "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/"


def _wkt_rings(w: str | None) -> list:
    """Polygon rings from WKT (POLYGON / MULTIPOLYGON), outer rings only, thinned to at most 200 points each."""
    if not w:
        return []
    rings = []
    for body in re.findall(r"\(\(([^()]+)\)", w):
        pts = [[round(float(a), 5), round(float(b), 5)] for a, b in (p.split()[:2] for p in body.split(",") if p.strip())]
        if len(pts) >= 3:
            rings.append(pts[::max(1, len(pts) // 200)] + [pts[0]])
    return rings


async def ems(feed: Feed, f: Fetcher) -> Result:
    """Copernicus Emergency Management Service, rapid mapping: maps of current disasters made from fresh satellite
    pictures (often 0.3-1.5 m), with counts of affected buildings and land. Activations of the last 120 days."""
    lst = (await f.get(_EMS + "public-activations-info/", params={"limit": 40})).json().get("results", [])
    cut = time.time() - 120 * 86400
    keep, memo = [], feed.memo.setdefault("detail", {})
    for a in lst:
        t = _iso(a.get("eventTime") or a.get("activationTime") or "")
        if t and t < cut:
            continue
        code = a["code"]
        old = memo.get(code)
        if not old or (not a.get("closed") and time.time() - old[0] > 6 * 3600) or old[1].get("lastUpdate") != a.get("lastUpdate"):
            await asyncio.sleep(0.5)
            try:
                d = (await f.get(_EMS + "public-activations/", params={"code": code})).json()
                d = d["results"][0] if "results" in d else d
            except Exception:
                continue
            aois = []
            for ao in d.get("aois", []):
                prods = []
                for pr in ao.get("products", []):
                    cogs = [_EMS_COG + l["name"] for l in pr.get("layers", []) if l.get("format") == "cog" and "ORTHO" in l["name"]]
                    imgs = [{"sensor": i.get("sensorName"), "time": i.get("acquisitionTime"), "res": i.get("resolutionClass"), "file": i.get("fileName")}
                            for i in pr.get("images", [])]
                    built = {k: v for k, v in ((pr.get("stats") or {}).get("Built-up") or {}).items() if isinstance(v, dict)}
                    prods.append({"type": pr.get("type"), "monitoring": pr.get("monitoringNumber"), "images": imgs, "cogs": cogs,
                                  "built": built, "delivered": ((pr.get("version") or {}).get("deliveryTime") or "")[:16],
                                  "download": pr.get("downloadPath")})
                aois.append({"name": ao.get("name"), "number": ao.get("number"), "rings": _wkt_rings(ao.get("extent")), "products": prods})
            m = re.search(r"POINT \(([-\d.]+) ([-\d.]+)\)", d.get("centroid") or "")
            memo[code] = (time.time(), {"code": code, "name": d.get("name"), "category": d.get("category"), "countries": d.get("countries"),
                                        "eventTime": d.get("eventTime"), "activationTime": d.get("activationTime"), "closed": d.get("closed"),
                                        "lastUpdate": a.get("lastUpdate"), "lon": float(m.group(1)) if m else None, "lat": float(m.group(2)) if m else None,
                                        "rings": _wkt_rings(d.get("extent")), "aois": aois, "report": d.get("reportLink"), "gdacs": d.get("gdacsId")})
        keep.append(memo[code][1])
    with_pics = sum(1 for k in keep if any(p["cogs"] for ao in k["aois"] for p in ao["products"]))
    newest = max((_iso(k["eventTime"]) for k in keep if k.get("eventTime")), default=None)
    return Result(len(keep), {"activations": keep}, data_time=newest,
                  note=f"{len(keep)} activations in the last 120 days, {with_pics} with satellite pictures we can show")


# Regions where GPS jamming and spoofing are commonly reported; each is a 250-mile circle asked from adsb.fi.
JAM_REGIONS = {"Baltic and Kaliningrad": (55.5, 20.5), "Gulf of Finland": (60.0, 27.5), "Belarus and Ukraine border": (52.0, 30.5),
               "Black Sea": (44.0, 34.0), "Caucasus": (41.5, 45.0), "Eastern Mediterranean": (34.5, 33.5), "Israel and Lebanon": (32.5, 35.3),
               "Iraq and Syria": (34.5, 41.5), "Persian Gulf": (26.5, 52.0), "Red Sea": (20.0, 39.0), "Libya": (31.5, 16.0),
               "Northern Norway and Kola": (69.0, 29.0), "India and Pakistan border": (31.0, 73.5), "Myanmar": (21.0, 96.0), "Korean peninsula": (38.0, 127.0)}


async def gps_live(feed: Feed, f: Fetcher) -> Result:
    """GPS interference in the last hour, worked out by us from live aircraft in those regions, the way GPSJAM does
    it for a whole day: per hexagon, the share of aircraft whose broadcast position accuracy is poor (NACp below 8,
    i.e. worse than 93 m). Only the sampled regions are covered. A derived picture, not a measurement of jammers."""
    import h3
    seen = feed.memo.setdefault("seen", {})          # (hex cell, aircraft) -> [time, bad]
    asked, failed = 0, []
    for name, (lat, lon) in JAM_REGIONS.items():
        try:
            d, n = await adsbfi_area(f.client, lat, lon, 250)
            f.wire_bytes += n
            asked += 1
        except Exception:
            failed.append(name)
            continue
        now = time.time()
        for a in _readsb_aircraft(d):
            if a["nac_p"] is None or a["alt_ft"] in (None, "ground"):
                continue
            cell = h3.latlng_to_cell(a["lat"], a["lon"], 4)
            seen[(cell, a["hex"])] = [now, a["nac_p"] < 8]
    cut = time.time() - 3600
    for k in [k for k, v in seen.items() if v[0] < cut]:
        del seen[k]
    cells: dict[str, list] = {}
    for (cell, _), (t, bad) in seen.items():
        c = cells.setdefault(cell, [0, 0])
        c[1 if bad else 0] += 1
    feats = []
    for cell, (good, bad) in cells.items():
        total = good + bad
        if total < 3 or bad / total <= 0.02:
            continue
        ring = [[lon, lat] for lat, lon in h3.cell_to_boundary(cell)]
        ring.append(ring[0])
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"id": "gpsl:" + cell, "good": good, "bad": bad, "level": "high" if bad / total > 0.10 else "some"}})
    if not asked:
        raise RuntimeError("adsb.fi answered for none of the regions")
    return Result(len(feats), {"type": "FeatureCollection", "features": feats, "regions": {k: list(v) for k, v in JAM_REGIONS.items()}, "window_h": 1},
                  data_time=time.time(), note=f"{len(feats)} hexagons with interference in the last hour, from {asked} of {len(JAM_REGIONS)} sampled regions"
                  + (f"; not answered: {', '.join(failed)}" if failed else ""))
async def courts_icc(feed: Feed, f: Fetcher) -> Result:
    """The International Criminal Court's case list and situation pages, for person dossiers (see courts.py).
    Case list pages 1.5 s apart, then situation pages 20 s apart (the site's bot shield refuses bursts), once a day."""
    ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"}
    cases, sits, failed = [], [], []
    for page in range(8):
        got = courts.parse_cases((await f.get(courts.ICC + "/cases", params={"page": page}, headers=ua, follow_redirects=True)).text)
        if not got:
            break
        cases += got
        await asyncio.sleep(1.5)
    kept = courts.load_situations()                # last good copy of each page, used when the site refuses one today
    for slug in courts.SITUATIONS:
        for attempt in (0, 1):                 # the site's bot shield blocks bursts for a while: one retry after a pause
            try:
                r = await f.get(f"{courts.ICC}/{slug}", headers=ua, follow_redirects=True)
                if courts.is_challenge(r.text):
                    raise RuntimeError("bot-protection page")
                sits.append({**courts.parse_situation(r.text), "url": str(r.url), "read": time.time(), "slug": slug})
                break
            except Exception as e:
                if attempt:
                    old = kept.get(slug)
                    if old:
                        sits.append(old)
                    failed.append(f"{slug} ({e.response.status_code if isinstance(e, httpx.HTTPStatusError) else str(e) or type(e).__name__}"
                                  + (f", kept the copy from {time.strftime('%Y-%m-%d', time.gmtime(old['read']))})" if old else ")"))
                else:
                    await asyncio.sleep(90)
        await asyncio.sleep(20)
    courts.save_situations({s["slug"]: s for s in sits if s.get("slug")} | {k: v for k, v in kept.items() if k not in {s.get("slug") for s in sits}})
    if not cases:
        raise RuntimeError("the ICC case list came back empty (page layout changed?)")
    return Result(len(cases), {"cases": cases, "situations": sits}, data_time=time.time(), data_label="read",
                  note=f"{len(cases)} defendants, {len(sits)} situation pages" + (f"; failed: {', '.join(failed)}" if failed else ""))


async def travel_advice(feed: Feed, f: Fetcher) -> Result:
    """Official travel advice per country from the US State Department and the German Foreign Office (see travel.py).
    If one office fails, the other is still kept and the note names the one that failed."""
    await geo.ensure(f.client)
    out, problems = {"us": {}, "de": {}}, []
    try:
        out["us"] = travel.parse_us((await f.get(travel.US_URL)).text)
    except Exception as e:
        problems.append(f"US State Department failed: {type(e).__name__}")
    try:
        out["de"] = travel.parse_de((await f.get(travel.DE_URL)).json())
    except Exception as e:
        problems.append(f"German Foreign Office failed: {type(e).__name__}")
    if not out["us"] and not out["de"]:
        raise RuntimeError("; ".join(problems) or "nothing came back")
    out["problems"] = problems
    return Result(len(out["us"]) + len(out["de"]), out, data_label="advice in force when fetched",
                  note=f"{len(out['us'])} countries with a US advisory, {len(out['de'])} with German advice"
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
    Feed("vip_aircraft", "Government and VIP aircraft list", "plane-alert-db (ODbL)", "https://github.com/sdr-enthusiasts/plane-alert-db", 7 * 86400,
         vip_aircraft, min_retry=1800, limit_note="a volunteer-kept list, fetched weekly; positions come from the aircraft feeds"),
    Feed("sat_catalog", "What satellites do", "UCS Satellite Database", "https://www.ucs.org/resources/satellite-database", 7 * 86400, sat_catalog,
         min_retry=1800, limit_note="one 1.5 MB spreadsheet, fetched weekly; last updated by UCS in May 2023"),
    Feed("recon_sats", "Spy satellites", "CelesTrak, amateur observers", "https://www.mmccants.org/tles/", 12 * H, recon_sats,
         stale_after=3 * 86400, min_retry=1800, limit_note="twice a day; classified orbits come from amateur sightings"),
    Feed("flags", "Country tables for flags", "ICAO (via tar1090), ITU (via Wikidata), CelesTrak", "https://celestrak.org/satcat/sources.php", 7 * 86400,
         flag_tables, min_retry=1800, limit_note="three small tables, weekly"),
    Feed("maxar_events", "Disaster imagery (Maxar Open Data)", "Maxar Open Data (CC BY-NC 4.0)", "https://www.maxar.com/open-data", 86400, maxar_events,
         min_retry=1800, limit_note="the list of events, daily; pictures are fetched only when you open one"),
    Feed("usni_fleet", "US carriers (USNI Fleet Tracker)", "USNI News", "https://news.usni.org/category/fleet-tracker", 6 * H, usni_fleet,
         stale_after=10 * 86400, min_retry=1800, limit_note="a weekly article, read through its RSS feed"),
    Feed("ems", "Disaster maps and pictures (Copernicus EMS)", "Copernicus Emergency Management Service", "https://rapidmapping.emergency.copernicus.eu", 3600, ems,
         stale_after=2 * 86400, min_retry=600, limit_note="hourly; each activation's details are read once and again when it changes"),
    Feed("gps_live", "GPS interference, last hour (derived)", "adsb.fi, worked out by World Watch", "https://adsb.fi", 600, gps_live,
         stale_after=3600, limit_note="15 regions, one request each every 10 minutes, spaced 1.2 s (adsb.fi allows one a second)"),
    Feed("courts_icc", "International Criminal Court cases", "International Criminal Court", "https://www.icc-cpi.int/cases",
         24 * H, courts_icc, min_retry=3600, limit_note="about 25 pages once a day; used by person dossiers"),
    Feed("travel_advice", "Travel advice per country", "US State Department, German Foreign Office", "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html",
         6 * H, travel_advice, min_retry=1800, limit_note="two official lists, asked every 6 hours; shown in country dossiers"),
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
