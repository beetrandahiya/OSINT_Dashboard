"""Country outlines and codes, for the country dossier and for matching feed items to countries.

Built once from two public files and kept in data/countries-geo.json (about 2 MB; not in git):
- Natural Earth admin-0 countries at 1:50 million (public domain): names, ISO and FIPS codes, Wikidata ids,
  population estimate, outlines. Outlines at this scale are accurate to a few kilometres: fine for "is this
  aircraft over the country", not for anything near a border.
- VATSpy's country list (VATSIM community, CC BY-SA 4.0): which two-letter ICAO prefix belongs to which country,
  so a flight region code such as OIIX can be tied to Iran.

GDELT and the US State Department use FIPS 10-4 country codes (Germany = GM, Israel = IS); everything else here
uses ISO 3166 (DE, IL). Natural Earth carries both; the few it leaves blank are filled in below by hand.
"""
import asyncio
import bisect
import json
import math
import re
import unicodedata
from array import array

from . import config

FILE = config.DATA / "countries-geo.json"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
VATSPY_DAT = "https://raw.githubusercontent.com/vatsimnetwork/vatspy-data-project/master/VATSpy.dat"
ROW = 0.05            # degrees of latitude per scan row for the inside/outside test (about 5.5 km)
VERSION = 1

# FIPS 10-4 codes Natural Earth leaves blank (-99). GDELT codes Gaza and the West Bank as GZ / WE.
FIPS_FIX = {"IL": ["IS"], "NO": ["NO"], "PS": ["GZ", "WE"], "SS": ["OD"], "AX": []}
# Names in other sources that Natural Earth spells differently.
ALIAS = {"korea, north": "KP", "north korea": "KP", "korea, south": "KR", "south korea": "KR", "russian federation": "RU",
         "burma": "MM", "czech republic": "CZ", "ivory coast": "CI", "cote d'ivoire": "CI", "congo, democratic republic of the": "CD",
         "democratic republic of the congo": "CD", "dr congo": "CD", "congo (kinshasa)": "CD", "congo (brazzaville)": "CG",
         "republic of the congo": "CG", "congo": "CG", "united states": "US", "usa": "US", "united states of america": "US",
         "united kingdom": "GB", "uk": "GB", "great britain": "GB", "east timor": "TL", "timor leste": "TL", "cape verde": "CV",
         "swaziland": "SZ", "eswatini": "SZ", "macedonia": "MK", "north macedonia": "MK", "vatican": "VA", "holy see": "VA",
         "palestinian territories": "PS", "gaza": "PS", "west bank": "PS", "the west bank": "PS", "turkiye": "TR", "türkiye": "TR",
         "the bahamas": "BS", "bahamas": "BS", "the gambia": "GM", "gambia": "GM", "laos": "LA", "syria": "SY", "iran": "IR",
         "vietnam": "VN", "viet nam": "VN", "brunei": "BN", "micronesia": "FM", "taiwan": "TW", "kosovo": "XK", "moldova": "MD",
         "bosnia and herzegovina": "BA", "bosnia": "BA", "south sudan": "SS", "sudan": "SD", "tanzania": "TZ", "bolivia": "BO",
         "venezuela": "VE", "saint kitts and nevis": "KN", "saint lucia": "LC", "saint vincent and the grenadines": "VC",
         "sao tome and principe": "ST", "curacao": "CW", "hong kong": "HK", "macau": "MO", "macao": "MO",
         "falkland islands": "FK", "reunion": "RE", "netherlands antilles": "CW", "serbia and montenegro": "RS",
         "french guiana": "FR", "french guyana": "FR", "bosnia-herzegovina": "BA", "hong kong sar": "HK", "surinam": "SR",
         "santa lucia": "LC", "puerto rico, usa": "PR", "guadeloupe": "FR", "martinique": "FR", "mayotte": "FR", "bonaire": "NL"}

_lock = asyncio.Lock()
C: dict[str, dict] = {}            # ISO2 -> country
_by_fips: dict[str, str] = {}
_by_name: dict[str, str] = {}
_by_qid: dict[str, str] = {}
_by_iso3: dict[str, str] = {}
_icao: dict[str, str] = {}         # two-letter ICAO prefix (or one letter: K, C) -> ISO2


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9',()]+", " ", s).split())


async def ensure(client=None) -> bool:
    """Load the table, building it from the two public files the first time. Returns False if that failed.
    The work runs in a short-lived child process: parsing the files takes ~40 MB that Python would otherwise keep;
    only the compact result (arrays and name indexes) comes back."""
    if C:
        return True
    async with _lock:
        if C:
            return True
        from .feeds import _in_child
        try:
            got = await asyncio.to_thread(_in_child, _prepare)
        except Exception:
            return False
        if not got:
            return False
        for mine, theirs in zip((C, _by_fips, _by_name, _by_qid, _by_iso3, _icao), got):
            mine.clear()
            mine.update(theirs)
        return True


def _prepare():
    """In the child: read (or build and save) the table, index it, and hand back the compact parts."""
    try:
        raw = json.loads(FILE.read_text())
        if raw.get("version") != VERSION:
            raise ValueError("old version")
    except (OSError, ValueError):
        import httpx

        async def go():
            async with httpx.AsyncClient(timeout=60, headers={"User-Agent": config.USER_AGENT}) as c:
                return await _build(c)
        raw = asyncio.run(go())
        if not raw:
            return None
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(raw, separators=(",", ":")))
    _load(raw)
    return C, _by_fips, _by_name, _by_qid, _by_iso3, _icao


async def _build(c) -> dict | None:
    try:
        r = await c.get(NE_URL)
        r.raise_for_status()
        ne = r.json()
        r = await c.get(VATSPY_DAT)
        r.raise_for_status()
        dat = r.text
    except Exception:
        return None
    out = []
    for f in ne["features"]:
        p, g = f["properties"], f["geometry"]
        iso = p.get("ISO_A2_EH") if p.get("ISO_A2_EH") not in (None, "-99") else p.get("ISO_A2")
        if not iso or iso == "-99":
            iso = "X-" + p["ADM0_A3"]            # Somaliland, N. Cyprus, Siachen: no ISO code; keyed by Natural Earth's own
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = [[[round(x, 3), round(y, 3)] for x, y in poly[0]] for poly in polys]
        fips = FIPS_FIX.get(iso, [p["FIPS_10"]] if p.get("FIPS_10") not in (None, "-99") else [])
        names = sorted({n for n in (p.get("NAME"), p.get("NAME_LONG"), p.get("ADMIN"), p.get("FORMAL_EN"), p.get("NAME_EN"), p.get("NAME_CIAWF"),
                                     p.get("NAME_SORT"), p.get("GEOUNIT"), p.get("BRK_NAME")) if n})
        out.append({"iso": iso, "iso3": p.get("ISO_A3_EH") if p.get("ISO_A3_EH") != "-99" else None, "fips": fips, "name": p.get("NAME_EN") or p["NAME"],
                    "names": names, "qid": p.get("WIKIDATAID"), "pop": p.get("POP_EST"), "pop_year": p.get("POP_YEAR"),
                    "continent": p.get("CONTINENT"), "region": p.get("SUBREGION"), "label": [p.get("LABEL_X"), p.get("LABEL_Y")], "rings": rings})
    prefixes = {}
    sect = None
    for line in dat.splitlines():
        if line.startswith("["):
            sect = line.strip()
            continue
        if sect == "[Countries]" and "|" in line:
            name, pre = line.split("|")[:2]
            if pre.strip():
                prefixes[pre.strip().upper()] = name.strip()
    return {"version": VERSION, "countries": out, "icao": prefixes}


def _load(raw: dict) -> None:
    for c in raw["countries"]:
        rings, xs, ys = c.pop("rings"), [], []
        verts, rows = [], {}
        for ring in rings:
            for i in range(len(ring) - 1):                     # scan-line crossings: for each row of latitude, where the outline crosses it
                (x1, y1), (x2, y2) = ring[i], ring[i + 1]
                if y1 == y2:
                    continue
                lo, hi = min(y1, y2), max(y1, y2)
                k = math.ceil(lo / ROW - 0.5)
                while (k + 0.5) * ROW < hi:
                    y = (k + 0.5) * ROW
                    if y >= lo:
                        rows.setdefault(k, []).append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                    k += 1
            for x, y in ring:
                xs.append(x)
                ys.append(y)
                verts += (x, y)
        c["rows"] = {k: array("f", sorted(v)) for k, v in rows.items()}
        c["verts"] = {}                                         # outline points bucketed by whole degree of latitude
        for i in range(0, len(verts), 2):
            c["verts"].setdefault(math.floor(verts[i + 1]), array("f")).extend((verts[i], verts[i + 1]))
        c["bbox"] = [min(xs), min(ys), max(xs), max(ys)] if xs else None
        iso = c["iso"]
        # Some countries are several Natural Earth units (France has its overseas parts as separate polygons in one feature;
        # Indian Ocean Territories carry AU): merge them into the first.
        if iso in C:
            o = C[iso]
            for k, v in c["rows"].items():
                o["rows"][k] = array("f", sorted(list(o["rows"].get(k, [])) + list(v)))
            for k, v in c["verts"].items():
                o["verts"].setdefault(k, array("f")).extend(v)
            o["bbox"] = [min(o["bbox"][0], c["bbox"][0]), min(o["bbox"][1], c["bbox"][1]), max(o["bbox"][2], c["bbox"][2]), max(o["bbox"][3], c["bbox"][3])]
            continue
        C[iso] = c
        for f in c["fips"]:
            _by_fips.setdefault(f, iso)
        for n in c["names"]:
            _by_name.setdefault(norm(n), iso)
        if c.get("qid"):
            _by_qid[c["qid"]] = iso
        if c.get("iso3"):
            _by_iso3[c["iso3"]] = iso
    for n, iso in ALIAS.items():
        if iso in C:
            _by_name[norm(n)] = iso
    for pre, name in raw["icao"].items():
        iso = by_name(name)
        if iso:
            _icao[pre] = iso


_name_re = None


def named(text: str | None) -> set[str]:
    """Countries whose name appears in a text (word-bounded, names of 4+ letters), e.g. a Maxar event title."""
    global _name_re
    if _name_re is None:
        names = sorted((n for n in _by_name if len(n) >= 4), key=len, reverse=True)
        _name_re = re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b")
    return {_by_name[m] for m in _name_re.findall(norm(text or ""))}


def by_fips(code: str | None) -> str | None:
    return _by_fips.get((code or "").upper())


def by_name(name: str | None) -> str | None:
    n = norm(name or "")
    if not n:
        return None
    if n in _by_name:
        return _by_name[n]
    n2 = re.sub(r"^the ", "", re.sub(r"\s*\(.*?\)", "", n)).strip()
    return _by_name.get(n2)


def by_qid(qid: str | None) -> str | None:
    return _by_qid.get(qid or "")


def by_iso3(code: str | None) -> str | None:
    return _by_iso3.get((code or "").upper())


def by_icao(code: str | None) -> str | None:
    """A flight region or airport code -> the country whose prefix it carries (two letters, or K / C / Y... one letter)."""
    code = (code or "").upper()
    return _icao.get(code[:2]) or _icao.get(code[:1])


def contains(iso: str, lon: float, lat: float) -> bool:
    """Is the point inside the country's outline? Even-odd count of outline crossings left of the point on its row."""
    c = C.get(iso)
    if not c or lon is None or lat is None:
        return False
    b = c["bbox"]
    if not (b[0] <= lon <= b[2] and b[1] <= lat <= b[3]):
        return False
    row = c["rows"].get(math.floor(lat / ROW))
    return bool(row) and bisect.bisect_left(row, lon) % 2 == 1


def around(iso: str, lon, lat, within_km: float = 25) -> bool:
    """Inside the outline, or within a short distance of it: coastal cities sit on the line at this scale."""
    return contains(iso, lon, lat) or near(iso, lon, lat, within_km) is not None


def where(lon: float, lat: float) -> str | None:
    """The country a point lies in, if any (slow-ish: tests every country whose box holds the point)."""
    for iso, c in C.items():
        b = c["bbox"]
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3] and contains(iso, lon, lat):
            return iso
    return None


def km(lat1, lon1, lat2, lon2) -> float:
    r = math.radians
    h = math.sin(r(lat2 - lat1) / 2) ** 2 + math.cos(r(lat1)) * math.cos(r(lat2)) * math.sin(r(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(min(1.0, h)))


def near(iso: str, lon: float, lat: float, within_km: float) -> float | None:
    """Distance in km from a point outside the country to the nearest point of its outline (outline vertices, so
    accurate to a few km), if within the limit; 0 if inside; None if farther."""
    c = C.get(iso)
    if not c or lon is None or lat is None:
        return None
    if contains(iso, lon, lat):
        return 0.0
    b, pad = c["bbox"], within_km / 111 / max(0.2, math.cos(math.radians(lat)))
    if not (b[0] - pad <= lon <= b[2] + pad and b[1] - within_km / 111 <= lat <= b[3] + within_km / 111):
        return None
    best, dlat = None, within_km / 111
    dlon = dlat / max(0.05, math.cos(math.radians(lat)))
    for deg in range(math.floor(lat - dlat), math.floor(lat + dlat) + 1):
        v = c["verts"].get(deg)
        if not v:
            continue
        for i in range(0, len(v), 2):
            if abs(v[i] - lon) > dlon or abs(v[i + 1] - lat) > dlat:
                continue
            d = km(lat, lon, v[i + 1], v[i])
            if best is None or d < best:
                best = d
    return best if best is not None and best <= within_km else None


def public(iso: str) -> dict | None:
    c = C.get(iso)
    if not c:
        return None
    return {k: c.get(k) for k in ("iso", "iso3", "fips", "name", "qid", "pop", "pop_year", "continent", "region", "label", "bbox")}


# Short names people type that Natural Earth does not list (its codes are matched separately).
ALIASES = {"US": ["America", "United States", "USA", "U.S.", "U.S.A."], "GB": ["UK", "U.K.", "Britain", "Great Britain", "England", "Scotland", "Wales"],
           "AE": ["UAE", "Emirates"], "RU": ["Russia"], "KR": ["South Korea", "ROK"], "KP": ["North Korea", "DPRK"], "CN": ["PRC"],
           "TW": ["ROC"], "CD": ["DRC", "Congo-Kinshasa"], "CG": ["Congo-Brazzaville"], "CZ": ["Czech Republic"], "NL": ["Holland"],
           "VA": ["Vatican"], "CI": ["Ivory Coast"], "MM": ["Burma"], "TR": ["Turkiye"], "SA": ["KSA"], "VN": ["Vietnam"],
           "LA": ["Laos"], "SY": ["Syria"], "IR": ["Persia"], "PS": ["Palestine", "Gaza", "West Bank"], "BA": ["Bosnia"],
           "MK": ["Macedonia"], "SZ": ["Swaziland"], "CV": ["Cape Verde"], "TL": ["East Timor"]}


def listing() -> list[dict]:
    """For the search box: names, plus ISO codes ("US", "USA") and common short names, kept apart so a typed code
    matches only whole."""
    return sorted(({"iso": c["iso"], "name": c["name"], "names": sorted(set(c["names"]) | set(ALIASES.get(c["iso"], []))),
                    "codes": [x for x in (c["iso"], c.get("iso3")) if x]}
                   for c in C.values() if not c["iso"].startswith("X-")), key=lambda c: c["name"])
