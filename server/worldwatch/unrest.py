"""Protests and clashes over the last 24 hours, from GDELT's Events 2.0 files.

GDELT's software reads news articles and codes "who did what to whom, where" with the CAMEO scheme. That is
machine coding of news, not verified events, and it is noisy. What we do to keep it honest:
- only the event an article leads with (IsRootEvent = 1), not everything it mentions in passing;
- only places at city level (ActionGeo types 3 and 4); country or state level would be a centroid;
- only CAMEO root codes 14 (protest), 18 (assault), 19 (fight) and 20 (unconventional mass violence);
- sports pages dropped by their address ("attack" and "fight" in match reports are the classic false alarm);
- events of the same kind at the same place on the same day are one group, so one story coded five ways counts once;
- outlets are counted from GDELT's Mentions files: every distinct outlet that wrote about any event of the group,
  including articles published after the event was first coded. Groups seen by one outlet only are kept but hidden
  by default on the map.
Headlines and pictures come from the GKG news windows (news.py) when the same article is there.
"""
import asyncio
import calendar
import io
import json
import re
import time
import zipfile
from urllib.parse import urlparse

from . import config
from . import news as news_window

WINDOW = 24 * 3600
SLOT = 900
ROOTS = {"14", "18", "19", "20"}
# Showbiz pages: GDELT codes film plots and celebrity news as fighting ("Javed Akhtar spotted at Mumbai airport" came
# out as small-arms fighting in Mumbai).
SHOWBIZ = re.compile(r"/(entertainment|bollywood|hollywood|tollywood|kollywood|celebrit(y|ies)|showbiz|gossip|movies?|movie-reviews?|films?|"
                     r"tv|television|tv-shows?|web-series|ott|music|lifestyle|arts?-and-culture|culture|style|fashion|books?|horoscopes?)(/|-|$)", re.I)
SPORT = re.compile(r"/(sports?|football|soccer|cricket|rugby|nfl|nba|nhl|mlb|tennis|golf|boxing|ufc|mma|wwe|f1|formula-?1|motorsports?|esports|athletics|olympics|basketball|baseball|hockey)(/|-|$)", re.I)

# CAMEO codes in plain words (CAMEO manual 1.1b3). Category first, then the specific action.
CATEGORY = {"141": "protest", "142": "protest", "143": "protest", "144": "protest", "140": "protest", "145": "riot",
            "18": "attack", "19": "clash", "20": "mass violence"}
ACTION = {
    "140": "protest", "141": "demonstration or rally", "1411": "demonstration for leadership change", "1412": "demonstration for policy change",
    "1413": "demonstration for rights", "1414": "demonstration for change in institutions", "142": "hunger strike",
    "143": "strike or boycott", "1431": "strike or boycott for leadership change", "1432": "strike or boycott for policy change",
    "1433": "strike or boycott for rights", "1434": "strike or boycott for change in institutions",
    "144": "blockade or obstruction", "1441": "blockade for leadership change", "1442": "blockade for policy change",
    "1443": "blockade for rights", "1444": "blockade for change in institutions",
    "145": "violent protest or riot", "1451": "riot for leadership change", "1452": "riot for policy change",
    "1453": "riot for rights", "1454": "riot for change in institutions",
    "180": "unconventional violence", "181": "abduction or hijacking", "182": "physical assault", "1821": "sexual assault",
    "1822": "torture", "1823": "killing by physical assault", "183": "bombing", "1831": "suicide bombing",
    "1832": "vehicle bombing", "1833": "roadside bombing", "1834": "location bombing", "184": "use of human shields",
    "185": "attempted assassination", "186": "assassination",
    "190": "use of conventional military force", "191": "blockade or restricted movement", "192": "occupation of territory",
    "193": "fighting with small arms", "194": "fighting with artillery and tanks", "195": "aerial weapons (air strike, drone)",
    "1951": "precision-guided aerial munitions", "1952": "remotely piloted aerial munitions", "196": "ceasefire violation",
    "200": "unconventional mass violence", "201": "mass expulsion", "202": "mass killings", "203": "ethnic cleansing",
    "204": "weapons of mass destruction", "2041": "chemical, biological or radiological weapons", "2042": "nuclear weapons",
}


# Which GKG theme flag (news.theme_flags: 1 violence, 2 protest) an article must carry to support a category.
THEME_FIT = {"protest": 2, "riot": 3, "attack": 1, "clash": 1, "mass violence": 1}


def category(code: str) -> str:
    return CATEGORY.get(code[:3]) or CATEGORY.get(code[:2]) or "other"


def _rows(raw_zip: bytes):
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    for line in io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8", errors="replace"):
        yield line.rstrip("\n").split("\t")


ARMED = {"MIL", "REB", "INS", "UAF", "SEP", "SPY"}     # CAMEO actor types: military, rebels, insurgents, unidentified armed force, separatists, intelligence


def plausible(code: str, types: set, c1: str, c2: str, known: str | None) -> bool:
    """CAMEO's general codes catch figures of speech ("the opposition attacked the cabinet", "a port sues to seize a
    tanker"). For armed actions we therefore ask for an armed actor (by its CAMEO type or a known group code) or two
    different countries facing each other. Protests and the specific violent codes (bombing, assassination,
    small-arms fighting, air strikes and so on) are kept as coded."""
    if code.startswith("14"):
        return True
    armed = bool(types & ARMED) or bool(known)
    interstate = bool(c1 and c2 and c1 != c2)
    if code in ("190", "192", "191", "180", "200"):          # the vague ones
        return armed or (interstate and code != "192")
    if code.startswith(("182", "181")):                      # assault, abduction: also everyday crime; police count
        return armed or bool(types & {"COP", "CRM"}) or interstate
    return True


def parse_events(raw_zip: bytes) -> list[dict]:
    out = []
    for r in _rows(raw_zip):
        if len(r) < 61 or r[28] not in ROOTS or r[25] != "1" or r[51] not in ("3", "4") or not r[56] or not r[57]:
            continue
        url = r[60]
        if SPORT.search(urlparse(url).path) or SHOWBIZ.search(urlparse(url).path):
            continue
        types = {t for t in (r[12], r[13], r[14], r[22], r[23], r[24]) if t}
        if not plausible(r[26], types, r[7], r[17], r[8] or r[18] or None):
            continue
        try:
            lat, lon = float(r[56]), float(r[57])
        except ValueError:
            continue
        out.append({"id": int(r[0]), "code": r[26], "cat": category(r[26]), "place": r[52], "country": r[53],
                    "lat": lat, "lon": lon, "fid": r[58], "added": r[59], "url": url,
                    "a1": r[6].title() or None, "a2": r[16].title() or None, "sources": int(r[32] or 0),
                    "types": sorted(types),
                    "c1": r[7], "c2": r[17], "known": r[8] or r[18] or None})
    return out


def parse_mentions(raw_zip: bytes, wanted: set[int]) -> list[tuple]:
    out = []
    for r in _rows(raw_zip):
        if len(r) < 6:
            continue
        try:
            eid = int(r[0])
        except ValueError:
            continue
        if eid in wanted and r[3] == "1":                   # type 1 = web article
            if not SPORT.search(urlparse(r[5]).path) and not SHOWBIZ.search(urlparse(r[5]).path):
                out.append((eid, r[4], r[5], r[2], int(r[11] or 0) if len(r) > 11 else 0))   # event, outlet, address, time, confidence
    return out


class Unrest:
    def __init__(self):
        self.events: dict[str, list[dict]] = {}       # slot -> events coded in that slot (filtered)
        self.mentions: dict[str, list[tuple]] = {}    # slot -> mentions of our events found in that slot
        self.missing: dict[tuple, float] = {}         # (kind, slot) -> last 404
        # headline, language and picture of each event article, kept once seen in the 6-hour news window: events stay on
        # the map 24 hours, so without this the card lost its headline and picture after 6 (saved across restarts)
        self.heads_seen: dict[str, list] = self._load_heads()

    HEADS_FILE = config.DATA / "unrest-heads.json"

    def _load_heads(self) -> dict:
        try:
            d = json.loads(self.HEADS_FILE.read_text())
            cut = time.time() - 30 * 3600
            return {u: v for u, v in d.items() if v[-1] > cut}
        except (OSError, ValueError):
            return {}

    def save_heads(self) -> None:
        cut = time.time() - 30 * 3600
        self.heads_seen = {u: v for u, v in self.heads_seen.items() if v[-1] > cut}
        try:
            tmp = self.HEADS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.heads_seen))
            tmp.replace(self.HEADS_FILE)
        except OSError:
            pass

    def _wanted(self) -> set[int]:
        return {e["id"] for evs in self.events.values() for e in evs}

    async def refresh(self, f) -> tuple[int, int, int]:
        text = (await f.get("https://data.gdeltproject.org/gdeltv2/lastupdate.txt")).text
        url = next(line.split()[2] for line in text.splitlines() if line.endswith(".export.CSV.zip"))
        newest = calendar.timegm(time.strptime(url.rsplit("/", 1)[1][:14], "%Y%m%d%H%M%S"))
        slots = [time.strftime("%Y%m%d%H%M%S", time.gmtime(newest - i * SLOT)) for i in range(WINDOW // SLOT)]
        now, budget = time.time(), 16

        async def grab(kind, stamp):
            r = await f.client.get(f"https://data.gdeltproject.org/gdeltv2/{stamp}.{kind}.CSV.zip")
            f.wire_bytes += r.num_bytes_downloaded
            if r.status_code == 404:
                self.missing[(kind, stamp)] = now
                return None
            r.raise_for_status()
            return r.content

        # Events first (tiny files), all of the window, so that mentions can be matched to them.
        for stamp in slots:
            if budget <= 0:
                break
            if stamp in self.events or now - self.missing.get(("export", stamp), 0) < 600:
                continue
            hit = news_window.cache_load("events", stamp)
            if hit is not None:
                self.events[stamp] = hit
                continue
            raw = await grab("export", stamp)
            budget -= 1
            if raw is not None:
                self.events[stamp] = await asyncio.to_thread(parse_events, raw)
                await asyncio.to_thread(news_window.cache_save, "events", stamp, self.events[stamp])
        events_done = all(s in self.events or ("export", s) in self.missing for s in slots)
        if events_done:
            wanted = self._wanted()
            for stamp in slots:
                if budget <= 0:
                    break
                if stamp in self.mentions or now - self.missing.get(("mentions", stamp), 0) < 600:
                    continue
                hit = news_window.cache_load("mentions", stamp)
                if hit is not None:
                    self.mentions[stamp] = [tuple(x) for x in hit]
                    continue
                raw = await grab("mentions", stamp)
                budget -= 1
                if raw is not None:
                    self.mentions[stamp] = await asyncio.to_thread(parse_mentions, raw, wanted)
                    await asyncio.to_thread(news_window.cache_save, "mentions", stamp, self.mentions[stamp])
        oldest = slots[-1]
        for d in (self.events, self.mentions):
            for s in [s for s in d if s < oldest]:
                del d[s]
        for k in [k for k in self.missing if k[1] < oldest]:
            del self.missing[k]
        for name in ("events", "mentions"):
            await asyncio.to_thread(news_window.cache_prune, name, oldest)
        return len(self.events), len(self.mentions), len(slots)

    def groups(self) -> list[dict]:
        """One group per place, kind and day (UTC), with every outlet that covered any of its events."""
        heads = {}
        for win in (news_window.english, news_window.translated):
            for _, row in win.articles():
                heads[row[5]] = row                           # address -> (place, lat, lon, outlet, title, url, lang, image)
        by_event, groups = {}, {}
        for evs in self.events.values():
            for e in evs:
                if SHOWBIZ.search(urlparse(e["url"]).path):   # slots cached before this filter existed
                    continue
                key = (e["fid"] or f'{e["lat"]:.2f},{e["lon"]:.2f}', e["cat"], e["added"][:8])
                g = groups.get(key)
                if not g:
                    g = groups[key] = {"id": "|".join(key), "place": e["place"], "country": e["country"], "lat": e["lat"],
                                       "lon": e["lon"], "cat": e["cat"], "day": e["added"][:8], "codes": {}, "actors": {},
                                       "events": 0, "first": e["added"], "last": e["added"], "articles": {}}
                g["events"] += 1
                g["codes"][e["code"]] = g["codes"].get(e["code"], 0) + 1
                for a in (e["a1"], e["a2"]):
                    if a:
                        g["actors"][a] = g["actors"].get(a, 0) + 1
                g["first"], g["last"] = min(g["first"], e["added"]), max(g["last"], e["added"])
                g["articles"].setdefault(e["url"], {"url": e["url"], "outlet": urlparse(e["url"]).netloc.removeprefix("www."), "time": e["added"]})
                by_event[e["id"]] = g
        for ms in self.mentions.values():
            for eid, outlet, url, when, conf in ms:
                g = by_event.get(eid)
                if g and url not in g["articles"]:
                    g["articles"][url] = {"url": url, "outlet": outlet.removeprefix("www."), "time": when}
                    g["last"] = max(g["last"], when)
        out = []
        self.dropped_by_theme = 0
        for g in groups.values():
            arts = list(g["articles"].values())
            known = fits = 0
            want = THEME_FIT.get(g["cat"], 1)
            for a in arts:
                h = heads.get(a["url"])
                if h:
                    self.heads_seen[a["url"]] = [h[4], h[6], h[7], h[10] if len(h) > 10 else None, time.time()]
                elif a["url"] in self.heads_seen:             # out of the 6-hour news window, but we saw it earlier
                    t, lang, img, flags, _ = self.heads_seen[a["url"]]
                    a.update(title=t, lang=lang, image=img)
                    if flags is not None:
                        known += 1
                        fits += bool(flags & want)
                if h:
                    a.update(title=h[4], lang=h[6], image=h[7])
                    if len(h) > 10:                           # rows cached before the theme flags existed have none
                        known += 1
                        fits += bool(h[10] & want)
            if known and not fits:
                # every article whose themes GDELT gave us is about something else: the coding is wrong, not the news
                self.dropped_by_theme += 1
                continue
            outlets = {a["outlet"] for a in arts}
            arts.sort(key=lambda a: (-("title" in a), -(a.get("image") is not None), a["time"]))
            one = {}
            for a in arts:                                    # one article per outlet
                one.setdefault(a["outlet"], a)
            code = max(g["codes"], key=g["codes"].get)
            out.append({**{k: g[k] for k in ("id", "place", "country", "lat", "lon", "cat", "day", "events")},
                        "first": _t(g["first"]), "last": _t(g["last"]), "outlets": len(outlets),
                        "action": ACTION.get(code, ACTION.get(code[:3], "")), "codes": g["codes"],
                        "actions": {ACTION.get(c, ACTION.get(c[:3], c)): n for c, n in g["codes"].items()},
                        "actors": sorted(g["actors"], key=g["actors"].get, reverse=True)[:4],
                        "articles": [{**a, "time": _t(a["time"])} for a in list(one.values())[:25]],   # epoch seconds, clamped
                        "themes_checked": known})
        out.sort(key=lambda g: -g["outlets"])
        return out


def _t(stamp: str) -> float:
    """GDELT's DATEADDED and mention times are the 15-minute slot labels, which can be ahead of the clock (see the
    lesson on file names in CLAUDE.md). They are used to order and group, never shown as later than now."""
    return min(calendar.timegm(time.strptime(stamp[:14], "%Y%m%d%H%M%S")), time.time())


window = Unrest()
