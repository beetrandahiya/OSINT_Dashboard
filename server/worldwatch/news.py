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
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime

from . import config, helper, wire

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


# GKG's themes (V1Themes) say what an article is about. Two flags are kept per article so the protests-and-clashes
# layer can drop events whose articles are about something else (a celebrity at an airport coded as "fighting with
# small arms"). Generic themes (WB_2433_CONFLICT_AND_VIOLENCE, ARREST, POLICE) do not count: they are on most crime
# and politics stories.
_VIOLENT = re.compile(r"(?:^|;)(KILL|ARMEDCONFLICT|MILITARY|WOUND|TERROR|REBELLION|SEIGE|KIDNAP|BLOCKADE|ACT_FORCEPOSTURE|"
                      r"CRISISLEX_T03_DEAD|CRISISLEX_T02_INJURED|TAX_WEAPONS\w*|TAX_TERROR_GROUP\w*|MIL_\w+|"
                      r"TAX_FNCACT_(?:TROOPS|SOLDIERS|MILITANTS|GUNMEN|INSURGENTS|REBELS|ATTACKER\w*|MILITIA\w*)|SUICIDE_ATTACK|ASSASSINATION|WMD)(?=;|$)")
_PROTEST = re.compile(r"(?:^|;)(PROTEST|UNREST_\w+|STRIKE|DEMONSTRATION\w*|RALLY|BOYCOTT|RIOT\w*|CIVIL_DISOBEDIENCE|"
                      r"POLITICAL_TURMOIL|BLOCKADE|REBELLION|TAX_FNCACT_PROTEST\w*|TAX_FNCACT_DEMONSTRATORS|TAX_FNCACT_STRIKERS)(?=;|$)")


def theme_flags(themes: str) -> int:
    """1 = about violence, 2 = about protest (either or both)."""
    return (1 if _VIOLENT.search(themes) else 0) | (2 if _PROTEST.search(themes) else 0)


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
        best, cities = None, []
        for part in r[10].split(";"):
            p = part.split("#")
            if len(p) >= 9 and p[0] in ("3", "4") and p[5] and p[6]:
                try:
                    cand = (int(p[8]), p[1], float(p[5]), float(p[6]))
                except ValueError:
                    continue
                cities.append(cand)
                if best is None or cand < best:
                    best = cand
        m = _TITLE.search(r[26])
        if not best or not m or not m.group(1).strip():
            continue
        img = r[18].strip() if r[18].startswith("https://") else None
        # V2EnhancedPersons ("name,offset;"): who is named and where in the text, so a person can be matched to the
        # city mentioned nearest to them rather than to the article's first city
        persons = r[12][:600] if len(r) > 12 else ""
        if WATCH and persons and not any(n in WATCH for n, _ in person_mentions(persons)):
            persons = ""                    # nobody we follow is named: drop the names, which would cost ~40 MB over 6 hours
        near = tuple((c[0], c[1], c[2], c[3]) for c in sorted(set(cities))[:8]) if persons else ()
        rows.append((best[1], best[2], best[3], r[3], html.unescape(m.group(1)).strip()[:300], r[4], lang, img, persons, near, theme_flags(r[7])))
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
            raw = r.content
            del r
            # parsed in the helper process (helper.py): a translated file is ~30 MB of text, and what parsing it
            # touches would otherwise stay in the server
            self.files[stamp] = (published, await helper.run(parse_following, raw, self.translated, frozenset(WATCH)))
            del raw
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
PER_PLACE = 3          # articles per place sent with the map data (list row and first look); a card asks for the rest


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


WATCH: set[str] = set()          # normalised names of the people we follow (heads of state and government)


def set_watch(names) -> None:
    """Which people's names to keep in the news rows (see parse); called when the leaders list is loaded."""
    WATCH.clear()
    WATCH.update(_norm(n) for n in names if n)


def parse_following(raw_zip: bytes, translated: bool, watch: frozenset) -> list[tuple]:
    """`parse` for the helper process, which has its own (empty) WATCH: the server's list comes along."""
    WATCH.clear()
    WATCH.update(watch)
    return parse(raw_zip, translated)


def _norm(name: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFKD", name.lower())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).replace("-", " ").split())


def person_mentions(persons: str) -> list[tuple[str, int]]:
    """A row's person field as (normalised name, character offset or -1). It holds V2EnhancedPersons ("name,offset;");
    old cache files hold V1Persons (names without offsets). Every reader must strip the offset: comparing the raw entry
    ("donald trump,1234") with a name never matches."""
    out = []
    for p in persons.split(";"):
        if not p:
            continue
        name, _, off = p.rpartition(",")
        if not name or not off.isdigit():
            name, off = p, ""
        out.append((_norm(name), int(off) if off else -1))
    return out


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


_TRAVEL_BEFORE = r"(?:in|to|at|arrives?(?: in| at)?|arrived(?: in| at)?|lands?(?: in)?|landed(?: in)?|visits?|visited|visiting|reaches|reached|heads? to|flies to|flew to)"
_TRAVEL_AFTER = r"(?:visit|trip|talks|summit|meeting|meet|tour|stopover|arrival)"


def _travel_headlines(titles: list[str], name: str, place: str) -> int:
    """How many headlines name the person (surname) and say they are at the place."""
    parts = _norm(name).split()
    city = _norm(place.split(",")[0])
    if not city or not parts:
        return 0
    # family name last (Modi) or first (Xi Jinping): either, as a whole word
    who = re.compile(r"\b(" + "|".join(re.escape(x) for x in {parts[-1], parts[0]} if len(x) >= 2) + r")\b")
    before = re.compile(rf"\b{_TRAVEL_BEFORE}\s+(?:the\s+)?{re.escape(city)}\b")
    after = re.compile(rf"\b{re.escape(city)}(?:'s)?\s+{_TRAVEL_AFTER}")
    n = 0
    for t in titles:
        t = _norm(t)
        if who.search(t) and (before.search(t) or after.search(t)):
            n += 1
    return n


def leaders_today(leaders: list[dict]) -> list[dict]:
    """See _leaders_today; kept until the windows or the leaders list change (asked by every tab and every dossier).
    Callers get the kept list: they must not change it."""
    key = (_files_key(), tuple(l.get("qid") or l.get("name") for l in leaders), frozenset(WATCH))
    return _today_memo.get(key, lambda: _leaders_today(leaders))


def _leaders_today(leaders: list[dict]) -> list[dict]:
    """For each leader: the places the news put them in the last six hours, counted by distinct outlets. For each
    article naming a leader, the place is the city mentioned nearest to their name in the text (GDELT gives the
    character position of every name and place); without positions, the article's first city. This says where the
    news reported them, not where they are."""
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
            mentions: dict[str, list[int]] = {}
            for name, off in person_mentions(row[8]):
                mentions.setdefault(name, []).append(off)
            if len(mentions) > 12:                  # "today in history" and round-ups name dozens of people: no place to learn
                continue
            cities = row[9] if len(row) > 9 else []
            for n in mentions.keys() & names.keys():
                # the city mentioned nearest to the person's name; the article's first city when offsets are missing
                offs = [o for o in mentions[n] if o >= 0]
                if cities and offs:
                    c = min(cities, key=lambda c: min(abs(c[0] - o) for o in offs))
                    where = (c[1], c[2], c[3])
                else:
                    where = (row[0], row[1], row[2])
                for l in names[n]:
                    h = hits.setdefault(l["qid"], {"leader": l, "places": {}, "articles": {}})
                    pl = h["places"].setdefault(where[0], {"place": where[0], "lat": where[1], "lon": where[2], "outlets": set(), "heads": set(), "last": 0, "titles": []})
                    pl["outlets"].add(row[3])
                    if _headline(row[4]) not in pl["heads"] and len(pl["titles"]) < 30:
                        pl["titles"].append(row[4])
                    pl["heads"].add(_headline(row[4]))
                    pl["last"] = max(pl["last"], published)
                    old = h["articles"].get(row[3])
                    if not old or published > old["time"]:
                        h["articles"][row[3]] = {"outlet": row[3], "title": row[4], "url": row[5], "lang": row[6], "image": row[7],
                                                 "place": where[0], "time": published}
    out = []
    for h in hits.values():
        # One agency story reprinted by twenty papers is one report: places rank by distinct headlines first, and the
        # leading place needs at least two different headlines from two outlets.
        places = sorted(({**p, "outlets": len(p["outlets"]), "headlines": len(p["heads"])} for p in h["places"].values()),
                        key=lambda p: (-p["headlines"], -p["outlets"]))
        l = h["leader"]
        # A place abroad needs headlines that put them there: being mentioned near a city is not being in it ("Zelensky
        # says Moscow ..." had put him in Moscow). At least two different headlines must name the leader and say "in /
        # to / arrives in / visits <city>" or "<city> visit / talks / summit". Places at home keep the plain rule.
        best = None
        for p in places:
            if p["headlines"] < 2 or p["outlets"] < 2:
                break                                    # sorted: nothing further down qualifies either
            if not _abroad(p["place"], l["country"]):
                best = p
                break
            if _travel_headlines(p["titles"], l["name"], p["place"]) >= 2:
                best = p
                break
        for p in places:
            del p["heads"]
            p.pop("titles", None)
        if not best:
            continue
        arts = sorted(h["articles"].values(), key=lambda a: (a["place"] != best["place"], -(a["image"] is not None), -a["time"]))
        out.append({"abroad": _abroad(best["place"], l["country"]), "qid": l["qid"], "name": l["name"], "role": l["role"], "country": l["country"], "home": [l["lon"], l["lat"]],
                    "place": best, "places": [best] + [p for p in places if p is not best][:5], "outlets": len(h["articles"]), "articles": arts[:10]})
    out.sort(key=lambda x: -x["outlets"])
    return out


_SKIP_SPIKE = re.compile(r"/(sports?|football|soccer|cricket|rugby|nfl|nba|nhl|mlb|tennis|golf|boxing|ufc|mma|f1|motorsports?|basketball|baseball|hockey|"
                         r"entertainment|bollywood|hollywood|celebrit(y|ies)|showbiz|gossip|movies?|films?|tv|music|lifestyle|horoscopes?)(/|-|$)", re.I)


_SPLIT = re.compile(r"[\s,.;:!?'\"“”‘’«»()\[\]{}|/\\–—\-_#@&+*=<>%$0-9]+")
_STOP = set("""about above after again against also among amid amidst another around away back been before being below between
both cannot could does doing down during each even every from further have having here into just like live latest make many more
most much must near news next only other over said says should since some such than that their them then there these they this
those three through today under until update updates very video watch were what when where which while will with without would
your year years week first last over amid hours watch photos read full story report reports breaking says said""".split())


def _story(arts: list[dict], place: str):
    """The story the newest headlines share, if any: the distinctive word (or pair of words) found in the most
    headlines from different outlets. Words of the place's own name and common words do not count."""
    own = {w for w in _SPLIT.split(place.lower()) if w}
    docs = []
    for a in arts:
        words = {w for w in _SPLIT.split((a["title"] or "").lower()) if len(w) >= 4 and w not in _STOP and w not in own}
        docs.append((a, words))
    df = {}
    for _, ws in docs:
        for w in ws:
            df[w] = df.get(w, 0) + 1
    best = None
    for w1, n1 in sorted(df.items(), key=lambda kv: -kv[1])[:12]:
        if n1 < 4:
            break
        with1 = [d for d in docs if w1 in d[1]]
        pair = {}
        for _, ws in with1:
            for w in ws - {w1}:
                pair[w] = pair.get(w, 0) + 1
        w2, n2 = max(pair.items(), key=lambda kv: kv[1], default=(None, 0))
        group, words = (([d for d in with1 if w2 in d[1]], [w1, w2]) if n2 >= 4 else (with1, [w1]))
        outlets = {d[0]["outlet"] for d in group}
        if len(outlets) >= 4 and (best is None or len(outlets) > best[2]):
            best = ([d[0] for d in group], words, len(outlets))
    return best


def _files_key():
    """Changes exactly when a window gains or drops a slot (a slot's rows never change once held)."""
    return tuple(english.files), tuple(translated.files)


_spikes_memo, _today_memo = wire.Cached(), wire.Cached()


def spikes(min_heads=8, min_outlets=8, factor=3.0) -> dict:
    """See _spikes. The usual question (the defaults) is answered from the last result until the windows change: it
    walks ~30,000 articles (0.3-2 s) and was asked by every tab every two minutes, and again by every hotspot query."""
    if (min_heads, min_outlets, factor) != (8, 8, 3.0):
        return _spikes(min_heads, min_outlets, factor)
    return _spikes_memo.get(_files_key(), _spikes)


def _spikes(min_heads=8, min_outlets=8, factor=3.0) -> dict:
    """Places where the news suddenly picked up: in the newest hour, at least `min_heads` different headlines (copies of
    one agency story count once) from `min_outlets` outlets, and at least `factor` times the place's own hourly rate in
    the hours before (up to five). Each series is compared with its own past: the translated one runs about an hour
    behind the English one, and after a restart one series can hold fewer hours than the other. A series with less
    than two hours before its newest hour is left out."""
    used, by = [], {}
    for name, win in (("English", english), ("other languages", translated)):
        newest, oldest = win.newest(), win.oldest()
        if not newest or not oldest:
            continue
        cut = newest - 3600
        base_h = min(5.0, (cut - oldest) / 3600)
        if base_h < 2:
            continue
        used.append({"series": name, "newest": newest, "baseline_h": round(base_h, 1)})
        for published, row in win.articles():
            place, lat, lon, outlet, title, url, lang, img = row[:8]
            if "(General)" in place or _SKIP_SPIKE.search(urlparse(url).path):
                continue                                     # region-wide pins; sport and showbiz pages
            c = by.setdefault(place, {"place": place, "lat": lat, "lon": lon, "now": {}, "before": 0.0, "outlets": set(), "seen_before": set()})
            h = _headline(title)
            if published > cut:
                c["outlets"].add(outlet)
                if h not in c["now"] or (c["now"][h]["lang"] != "eng" and lang == "eng"):
                    c["now"][h] = {"outlet": outlet, "title": title, "url": url, "lang": lang, "image": img, "time": published}
            elif published > cut - base_h * 3600 and (name, h) not in c["seen_before"]:
                c["seen_before"].add((name, h))
                c["before"] += 1 / base_h                    # this series' hourly rate of different headlines
    if not used:
        return {"spikes": [], "series": [], "note": "fewer than two hours of news before the newest hour: no baseline yet"}
    out = []
    for c in by.values():
        n, rate = len(c["now"]), c["before"]
        if n >= min_heads and len(c["outlets"]) >= min_outlets and n >= factor * max(rate, 0.5):
            # more news alone is not breaking news: a busy city can get eight unrelated stories in an hour. Keep the
            # place only when at least four headlines from four outlets share a story, and show that story first.
            story = _story(list(c["now"].values()), c["place"])
            if not story:
                continue
            same, words, n_out = story
            ids = {id(a) for a in same}
            arts = sorted(c["now"].values(), key=lambda a: (id(a) not in ids, a["lang"] != "eng", -(a["image"] is not None), -a["time"]))
            # id from the series and place, not the list index: an open card must not become another place on reload
            out.append({"id": f"spike:{name}:{c['place']}", "place": c["place"], "lat": c["lat"], "lon": c["lon"], "headlines": n, "outlets": len(c["outlets"]),
                        "story_words": words, "story_headlines": len(same), "story_outlets": n_out,
                        "rate_before": round(rate, 1), "times": round(n / max(rate, 0.5), 1), "first": min(a["time"] for a in arts),
                        "articles": arts[:10]})
    out.sort(key=lambda s: -s["times"])
    return {"spikes": out, "series": used, "newest": max(u["newest"] for u in used), "baseline_h": min(u["baseline_h"] for u in used),
            "rule": f"newest hour of each news series: >= {min_heads} different headlines from >= {min_outlets} outlets, >= {factor:g}x the place's own hourly rate in the hours before, and >= 4 headlines from 4 outlets sharing distinctive words ("
                    + ", ".join(f"{u['series']}: {u['baseline_h']} h" for u in used) + ")"}
