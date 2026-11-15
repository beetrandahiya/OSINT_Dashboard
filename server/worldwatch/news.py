"""News places over the last six hours, from GDELT's 15-minute GKG files (English, and the translated series).

GDELT publishes one file per 15-minute slot. The map used to show only the newest file, which left most of the
world (India in particular, ~40 articles per file) almost empty. Now every file of the last six hours is kept,
reduced to the few fields we show, and the places are counted over all of them.

What each article keeps: the place it is pinned to (the first city-level place GDELT found in it), the outlet,
headline, link, language, the outlet's own preview picture (GKG column V2.1SHARINGIMAGE) and the time GDELT
published the file. Nothing is scored. The count per place is the number of distinct outlets.
"""
import asyncio
import calendar
import html
import io
import json
import re
import time
import zipfile
from email.utils import parsedate_to_datetime

from . import config

CACHE = config.DATA / "gdelt"     # each slot's reduced rows, written once, so a restart does not refill six hours


def cache_load(name: str, stamp: str):
    f = CACHE / f"{name}-{stamp}.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return None


def cache_save(name: str, stamp: str, value) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CACHE / f".{name}-{stamp}.tmp"
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    tmp.replace(CACHE / f"{name}-{stamp}.json")


def cache_prune(name: str, oldest: str) -> None:
    for f in CACHE.glob(f"{name}-*.json"):
        if f.stem.rsplit("-", 1)[1] < oldest:
            f.unlink(missing_ok=True)

WINDOW = 6 * 3600
SLOT = 900
_TITLE = re.compile(r"<PAGE_TITLE>(.*?)</PAGE_TITLE>")
_LANG = re.compile(r"srclc:(\w+)")

# GDELT gives ISO 639-2 codes; Google Translate wants 639-1. Unknown ones are sent as "auto".
GOOGLE = {"deu": "de", "hin": "hi", "fra": "fr", "spa": "es", "ita": "it", "rus": "ru", "zho": "zh-CN", "tur": "tr",
          "ukr": "uk", "ell": "el", "ron": "ro", "vie": "vi", "kor": "ko", "por": "pt", "pol": "pl", "ind": "id",
          "jpn": "ja", "ara": "ar", "srp": "sr", "guj": "gu", "tel": "te", "tam": "ta", "mar": "mr", "ben": "bn",
          "urd": "ur", "pan": "pa", "kan": "kn", "mal": "ml", "nld": "nl", "swe": "sv", "dan": "da", "nor": "no",
          "fin": "fi", "ces": "cs", "slk": "sk", "hun": "hu", "bul": "bg", "hrv": "hr", "slv": "sl", "bos": "bs",
          "lit": "lt", "lav": "lv", "est": "et", "heb": "iw", "fas": "fa", "tha": "th", "msa": "ms", "tgl": "tl",
          "swa": "sw", "aze": "az", "kat": "ka", "hye": "hy", "kaz": "kk", "uzb": "uz", "sqi": "sq", "mkd": "mk",
          "bel": "be", "cat": "ca", "glg": "gl", "eus": "eu", "isl": "is", "nep": "ne", "sin": "si", "khm": "km",
          "mya": "my", "amh": "am", "som": "so", "afr": "af", "mon": "mn", "pus": "ps", "lao": "lo"}
NAMES = {"eng": "English", "deu": "German", "hin": "Hindi", "fra": "French", "spa": "Spanish", "ita": "Italian",
         "rus": "Russian", "zho": "Chinese", "tur": "Turkish", "ukr": "Ukrainian", "ell": "Greek", "ron": "Romanian",
         "vie": "Vietnamese", "kor": "Korean", "por": "Portuguese", "pol": "Polish", "ind": "Indonesian",
         "jpn": "Japanese", "ara": "Arabic", "srp": "Serbian", "guj": "Gujarati", "tel": "Telugu", "tam": "Tamil",
         "mar": "Marathi", "ben": "Bengali", "urd": "Urdu", "pan": "Punjabi", "kan": "Kannada", "mal": "Malayalam",
         "nld": "Dutch", "swe": "Swedish", "fas": "Persian", "heb": "Hebrew", "tha": "Thai", "ces": "Czech",
         "hun": "Hungarian", "bul": "Bulgarian", "hrv": "Croatian", "fin": "Finnish", "dan": "Danish", "nor": "Norwegian",
         "slk": "Slovak", "msa": "Malay", "nep": "Nepali", "sin": "Sinhala", "aze": "Azerbaijani", "kat": "Georgian"}


def parse(raw_zip: bytes, translated: bool) -> list[tuple]:
    """One GKG file -> compact rows (place, lat, lon, outlet, title, url, lang, image).
    Only articles with a headline and a city-level place: country- and state-level mentions are pinned by GDELT
    to a centroid, which would put a story in the middle of a country it may only mention."""
    z = zipfile.ZipFile(io.BytesIO(raw_zip))
    rows = []
    # read line by line: a translated file is ~30 MB of text, and holding it whole doubled the server's peak memory
    for line in io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8", errors="replace"):
        r = line.split("\t")
        if len(r) < 27:
            continue
        lang = "eng"
        if translated:
            m = _LANG.search(r[25])
            lang = m.group(1) if m else "?"
        best = None
        for part in r[10].split(";"):
            p = part.split("#")
            if len(p) >= 9 and p[0] in ("3", "4") and p[5] and p[6]:
                try:
                    cand = (int(p[8]), p[1], float(p[5]), float(p[6]))
                except ValueError:
                    continue
                if best is None or cand < best:
                    best = cand
        m = _TITLE.search(r[26])
        if not best or not m or not m.group(1).strip():
            continue
        img = r[18].strip() if r[18].startswith("https://") else None
        persons = r[11][:400] if len(r) > 11 else ""          # V1Persons: the people GDELT found named in the article
        rows.append((best[1], best[2], best[3], r[3], html.unescape(m.group(1)).strip()[:300], r[4], lang, img, persons))
    return rows


class Window:
    """The files of the last six hours of one GDELT series."""

    def __init__(self, name: str, suffix: str, listing: str, translated: bool, per_run: int):
        self.name, self.suffix, self.listing, self.translated, self.per_run = name, suffix, listing, translated, per_run
        self.files: dict[str, tuple[float, list[tuple]]] = {}   # slot stamp -> (published, rows)
        self.missing: dict[str, float] = {}                      # slot stamp -> when it last answered 404

    async def refresh(self, f) -> tuple[int, int, int]:
        """Fetch the newest slots we do not hold yet, newest first, a few per run.
        Returns (files fetched now, files held, slots in the window).
        GDELT lists a file before it can be downloaded and some slots stay missing for a while, so a 404 is
        normal: the slot is tried again ten minutes later."""
        text = (await f.get(self.listing)).text
        url = next(line.split()[2] for line in text.splitlines() if line.endswith(self.suffix))
        newest = calendar.timegm(time.strptime(url.rsplit("/", 1)[1][:14], "%Y%m%d%H%M%S"))
        now, got = time.time(), 0
        slots = [time.strftime("%Y%m%d%H%M%S", time.gmtime(newest - i * SLOT)) for i in range(WINDOW // SLOT + 1)]
        for stamp in slots:
            if got >= self.per_run:
                break
            if stamp in self.files or now - self.missing.get(stamp, 0) < 600:
                continue
            hit = cache_load(self.name, stamp)
            if hit:
                self.files[stamp] = (hit[0], [tuple(x) for x in hit[1]])
                continue
            r = await f.client.get(f"https://data.gdeltproject.org/gdeltv2/{stamp}{self.suffix}")
            f.wire_bytes += r.num_bytes_downloaded
            if r.status_code == 404:
                self.missing[stamp] = now
                continue
            r.raise_for_status()
            published = parsedate_to_datetime(r.headers["last-modified"]).timestamp()
            self.files[stamp] = (published, await asyncio.to_thread(parse, r.content, self.translated))
            await asyncio.to_thread(cache_save, self.name, stamp, self.files[stamp])
            self.missing.pop(stamp, None)
            got += 1
        # keep six hours of slots counted back from the newest listed one
        oldest = time.strftime("%Y%m%d%H%M%S", time.gmtime(newest - WINDOW))
        for stamp in [s for s in self.files if s < oldest]:
            del self.files[stamp]
        for stamp in [s for s in self.missing if s < oldest]:
            del self.missing[stamp]
        await asyncio.to_thread(cache_prune, self.name, oldest)
        held = len(self.files)
        expected = len([s for s in slots if s >= oldest])
        return got, held, expected

    def articles(self):
        for published, rows in self.files.values():
            for row in rows:
                yield published, row

    def newest(self) -> float | None:
        return max((p for p, _ in self.files.values()), default=None)

    def oldest(self) -> float | None:
        return min((p for p, _ in self.files.values()), default=None)


english = Window("gkg", ".gkg.csv.zip", "https://data.gdeltproject.org/gdeltv2/lastupdate.txt", False, per_run=6)
translated = Window("gkgtr", ".translation.gkg.csv.zip", "https://data.gdeltproject.org/gdeltv2/lastupdate-translation.txt", True, per_run=3)
PER_PLACE = 8          # articles per place sent with the map data; a card asks for the rest


def places(win: Window) -> list[dict]:
    """Count distinct outlets per place over the window; keep each outlet's newest article."""
    by: dict[str, dict] = {}
    for published, row in win.articles():
        place, lat, lon, outlet, title, url, lang, img = row[:8]
        c = by.setdefault(place, {"place": place, "lat": lat, "lon": lon, "outlets": {}, "last": 0})
        old = c["outlets"].get(outlet)
        if not old or published > old["time"]:
            c["outlets"][outlet] = {"outlet": outlet, "title": title, "url": url, "lang": lang, "image": img, "time": published}
        c["last"] = max(c["last"], published)
    out = []
    for c in by.values():
        arts = sorted(c["outlets"].values(), key=lambda a: (-(a["image"] is not None), -a["time"]))
        out.append({"place": c["place"], "lat": c["lat"], "lon": c["lon"], "outlets": len(arts), "last": c["last"],
                    "articles": arts[:PER_PLACE]})
    out.sort(key=lambda c: -c["outlets"])
    return out


def place_articles(name: str) -> list[dict]:
    """Every article of one place in both windows, newest first, one per outlet."""
    seen = {}
    for win in (english, translated):
        for published, row in win.articles():
            place, lat, lon, outlet, title, url, lang, img = row[:8]
            if place == name and (outlet not in seen or published > seen[outlet]["time"]):
                seen[outlet] = {"outlet": outlet, "title": title, "url": url, "lang": lang, "image": img, "time": published}
    return sorted(seen.values(), key=lambda a: -a["time"])


_imgs = {"key": None, "set": set()}


def images() -> set[str]:
    """Every picture the news windows hold: the only addresses the picture proxy will fetch."""
    key = (tuple(english.files), tuple(translated.files))
    if key != _imgs["key"]:
        _imgs.update(key=key, set={row[7] for win in (english, translated) for _, row in win.articles() if row[7]})
    return _imgs["set"]


def _norm(name: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFKD", name.lower())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).replace("-", " ").split())


_ALIAS = {"people's republic of china": "china", "united states of america": "united states", "russian federation": "russia",
          "state of palestine": "palestine", "republic of the congo": "congo", "kingdom of the netherlands": "netherlands",
          "czech republic": "czechia", "ivory coast": "cote d'ivoire", "east timor": "timor-leste"}


def _abroad(place: str, country: str) -> bool:
    """True when the place GDELT gives is in another country than the leader's (compared by name)."""
    here = _norm(place.split(",")[-1]) if place else ""
    home = _norm(_ALIAS.get(country.lower(), country))
    if here in ("palestine", "gaza strip", "west bank") and home == "palestine":
        return False
    return bool(here) and here not in home and home not in here


def _headline(t: str) -> str:
    t = re.sub(r"\s+[-|–]\s+[^-|–]{2,40}$", "", t.lower())       # drop " - Outlet name" endings
    return re.sub(r"\W+", " ", t).strip()


def leaders_today(leaders: list[dict]) -> list[dict]:
    """For each leader: the places that articles naming them were pinned to in the last six hours, counted by
    distinct outlets. A place is the first city an article mentions, which is usually its dateline. This says where
    the news reported them, not where they are."""
    names = {}
    for l in leaders:
        n = _norm(l["name"])
        if len(n.split()) >= 2:                     # single names (some monarchs) would match too much
            names.setdefault(n, []).append(l)
    hits: dict[str, dict] = {}
    for win in (english, translated):
        for published, row in win.articles():
            if len(row) < 9 or not row[8]:
                continue
            raw = [p for p in row[8].split(";") if p]
            if len(raw) > 12:                       # "today in history" and round-ups name dozens of people: no place to learn
                continue
            persons = {_norm(p) for p in raw}
            for n in persons & names.keys():
                for l in names[n]:
                    h = hits.setdefault(l["qid"], {"leader": l, "places": {}, "articles": {}})
                    pl = h["places"].setdefault(row[0], {"place": row[0], "lat": row[1], "lon": row[2], "outlets": set(), "heads": set(), "last": 0})
                    pl["outlets"].add(row[3])
                    pl["heads"].add(_headline(row[4]))
                    pl["last"] = max(pl["last"], published)
                    old = h["articles"].get(row[3])
                    if not old or published > old["time"]:
                        h["articles"][row[3]] = {"outlet": row[3], "title": row[4], "url": row[5], "lang": row[6], "image": row[7],
                                                 "place": row[0], "time": published}
    out = []
    for h in hits.values():
        # One agency story reprinted by twenty papers is one report: places rank by distinct headlines first, and the
        # leading place needs at least two different headlines from two outlets.
        places = sorted(({**p, "outlets": len(p["outlets"]), "headlines": len(p["heads"])} for p in h["places"].values()),
                        key=lambda p: (-p["headlines"], -p["outlets"]))
        for p in places:
            del p["heads"]
        if places[0]["headlines"] < 2 or places[0]["outlets"] < 2:
            continue
        arts = sorted(h["articles"].values(), key=lambda a: (a["place"] != places[0]["place"], -(a["image"] is not None), -a["time"]))
        l = h["leader"]
        out.append({"abroad": _abroad(places[0]["place"], l["country"]), "qid": l["qid"], "name": l["name"], "role": l["role"], "country": l["country"], "home": [l["lon"], l["lat"]],
                    "place": places[0], "places": places[:6], "outlets": len(h["articles"]), "articles": arts[:10]})
    out.sort(key=lambda x: -x["outlets"])
    return out
