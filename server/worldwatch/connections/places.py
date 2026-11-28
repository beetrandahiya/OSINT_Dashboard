"""Where a company sits, for the map view of Connections. In this order, and said on the page which one placed it:
  1. Wikidata: its headquarters (P159: the statement's own coordinates, else the headquarters place's), else the place
     it is located in (P131), else the item's own coordinates (P625: plants, ports, sites);
  2. GLEIF: the postal code of its headquarters address, else of its legal address, at that code's centre in
     GeoNames' postal-code table (CC BY 4.0; downloaded once, 20 MB, built into data/postal.db by the `postal` feed);
  3. GLEIF: the town named in that address, in the same table (the first place of that name in that country).
Anything else is listed as not placed, never guessed. A dot is a registered address or headquarters: not where the
company works.
"""
import asyncio
import io
import re
import sqlite3
import threading
import unicodedata
import zipfile

from .. import config
from . import sources as S

URL = "https://download.geonames.org/export/zip/allCountries.zip"
MONTH = 30 * 86400


def db_path():
    return config.DATA / "postal.db"


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("ß", "ss")
    return " ".join(re.split(r"[^a-z0-9]+", s)).strip()


def _code(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").upper())


def import_zip(zip_path: str) -> dict:
    """GeoNames allCountries postal file -> data/postal.db (runs in the helper process). Two tables: by country and
    postal code, and by country and folded place name (first row wins)."""
    tmp = db_path().with_suffix(".db.part")
    tmp.unlink(missing_ok=True)
    c = sqlite3.connect(tmp)
    c.executescript("""PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE code (cc TEXT, code TEXT, place TEXT, lat REAL, lon REAL, PRIMARY KEY (cc, code)) WITHOUT ROWID;
        CREATE TABLE name (cc TEXT, fold TEXT, place TEXT, lat REAL, lon REAL, PRIMARY KEY (cc, fold)) WITHOUT ROWID;""")
    n, codes, names = 0, [], []
    with zipfile.ZipFile(zip_path) as z, z.open("allCountries.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) < 11:
                continue
            try:
                lat, lon = float(p[9]), float(p[10])
            except ValueError:
                continue
            codes.append((p[0], _code(p[1]), p[2], lat, lon))
            names.append((p[0], fold(p[2]), p[2], lat, lon))
            n += 1
            if len(codes) >= 50000:
                c.executemany("INSERT OR IGNORE INTO code VALUES (?,?,?,?,?)", codes)
                c.executemany("INSERT OR IGNORE INTO name VALUES (?,?,?,?,?)", names)
                codes, names = [], []
    c.executemany("INSERT OR IGNORE INTO code VALUES (?,?,?,?,?)", codes)
    c.executemany("INSERT OR IGNORE INTO name VALUES (?,?,?,?,?)", names)
    c.commit()
    k = c.execute("SELECT count(*) FROM code").fetchone()[0]
    c.close()
    tmp.replace(db_path())
    return {"rows": n, "codes": k}


_local = threading.local()


def _pdb():
    if not db_path().exists():
        return None
    c = getattr(_local, "c", None)
    if c is None:
        c = _local.c = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True, check_same_thread=False)
    return c


def postal_ready() -> bool:
    return db_path().exists()


def by_postal(cc, code, town):
    """(lat, lon, place, how) from a GLEIF address, or None. Codes are tried whole, then the part before a space or a
    hyphen (GeoNames keeps outward codes only for the UK, Canada, the Netherlands...)."""
    c = _pdb()
    if not c or not cc:
        return None
    cc = cc.upper()
    raw = (code or "").upper().strip()
    tries = [_code(raw)] + [_code(re.split(r"[\s-]", raw)[0])] if raw else []
    for t in dict.fromkeys(x for x in tries if x):
        r = c.execute("SELECT place, lat, lon FROM code WHERE cc = ? AND code = ?", (cc, t)).fetchone()
        if r:
            return r[1], r[2], r[0], "postal code"
    for t in dict.fromkeys([fold(town), fold(re.split(r"[-,/(]", town or "")[0])]):
        if t:
            r = c.execute("SELECT place, lat, lon FROM name WHERE cc = ? AND fold = ?", (cc, t)).fetchone()
            if r:
                return r[1], r[2], r[0], "town"
    return None


# ---------------------------------------------------------------- Wikidata
def _km(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))


def _pt(v):
    m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", v or "")
    return (float(m.group(2)), float(m.group(1))) if m else None


async def wd_by_leis(leis) -> dict:
    """LEI -> Wikidata item carrying it (P1278), one query for all, remembered a week per LEI."""
    out, need = {}, []
    for l in dict.fromkeys(leis):
        hit = await asyncio.to_thread(S.store.cache_get, "wdlei:" + l, 7 * 86400)
        if hit is not None:
            if hit:
                out[l] = hit
        else:
            need.append(l)
    for i in range(0, len(need), 80):
        chunk = need[i:i + 80]
        rows = await S.sparql("SELECT ?lei ?c WHERE { VALUES ?lei { %s } ?c wdt:P1278 ?lei }" % " ".join(f'"{l}"' for l in chunk))
        got = {}
        for b in rows:
            got.setdefault(b["lei"]["value"], b["c"]["value"].rsplit("/", 1)[1])
        for l in chunk:
            await asyncio.to_thread(S.store.cache_put, "wdlei:" + l, got.get(l, ""))
            if got.get(l):
                out[l] = got[l]
    return out


async def wd_places(qids) -> dict:
    """QID -> {lat, lon, place, how} from Wikidata, one query per 60 items, remembered 30 days (also when none)."""
    out, need = {}, []
    for q in dict.fromkeys(q for q in qids if q):
        hit = await asyncio.to_thread(S.store.cache_get, "wdplace2:" + q, MONTH)
        if hit is not None:
            if hit:
                out[q] = hit
        else:
            need.append(q)
    for i in range(0, len(need), 60):
        chunk = need[i:i + 60]
        rows = await S.sparql("""SELECT ?c ?hqq ?hq ?hqLabel ?hqc ?loc ?locLabel ?locc ?own WHERE { VALUES ?c { %s }
          OPTIONAL { ?c p:P159 ?st . ?st ps:P159 ?hq . FILTER NOT EXISTS { ?st pq:P582 [] }
                     OPTIONAL { ?st pq:P625 ?hqq } OPTIONAL { ?hq wdt:P625 ?hqc } }
          OPTIONAL { ?c wdt:P131 ?loc . ?loc wdt:P625 ?locc }
          OPTIONAL { ?c wdt:P625 ?own }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul,de,fr,es,it". } }""" % " ".join("wd:" + q for q in chunk))
        best = {}
        for b in rows:
            q = b["c"]["value"].rsplit("/", 1)[1]
            v = lambda k: (b.get(k) or {}).get("value")
            hqq, hqc = _pt(v("hqq")), _pt(v("hqc"))
            if hqq and hqc and _km(hqq, hqc) > 50:      # the statement's own coordinates far from the place it names
                hqq = None                               # (Eurowings: "Düsseldorf" with a point near Dortmund): the place wins
            cands = [(0, hqq, v("hqLabel"), "headquarters"), (1, hqc, v("hqLabel"), "headquarters"),
                     (2, _pt(v("locc")), v("locLabel"), "located in"), (3, _pt(v("own")), None, "its own coordinates")]
            for rank, pt, place, how in cands:
                if pt and (q not in best or rank < best[q][0]):
                    best[q] = (rank, {"lat": pt[0], "lon": pt[1], "place": place, "how": how, "source": "Wikidata"})
        for q in chunk:
            body = best.get(q, (9, {}))[1]
            await asyncio.to_thread(S.store.cache_put, "wdplace2:" + q, body)
            if body:
                out[q] = body
    return out


async def places(refs: list[str]) -> dict:
    """refs (lei:/wd:/icij:/os:) -> {"places": {ref: place}, "unplaced": {ref: why}, "problems": [...]}."""
    problems = []
    leis = [r[4:] for r in refs if r.startswith("lei:")]
    qids = [r[3:] for r in refs if r.startswith("wd:")]
    try:
        lei2q = await wd_by_leis(leis)
    except S.SourceDown as e:
        lei2q = {}
        problems.append(f"Wikidata did not answer ({e}); places from GLEIF addresses only")
    try:
        wdp = await wd_places(set(qids) | set(lei2q.values()))
    except S.SourceDown as e:
        wdp = {}
        problems.append(f"Wikidata did not answer ({e}); places from GLEIF addresses only")
    recs = {}
    want = [l for l in leis if lei2q.get(l) not in wdp]
    if want:
        try:
            recs = await S.gleif_records(want)
        except S.SourceDown as e:
            problems.append(f"GLEIF did not answer ({e})")
    out, unplaced = {}, {}
    for r in refs:
        kind, _, key = r.partition(":")
        q = key if kind == "wd" else lei2q.get(key) if kind == "lei" else None
        if q and q in wdp:
            out[r] = {**wdp[q], "qid": q}
            continue
        if kind == "lei" and key in recs:
            g = recs[key]
            for code, town, cc, which in ((g.get("hq_postal"), g.get("hq_city"), g.get("hq_country"), "headquarters address"),
                                          (g.get("postal"), g.get("city"), g.get("country"), "legal address")):
                hit = await asyncio.to_thread(by_postal, cc, code, town)
                if hit:
                    label = " ".join(x for x in (town, code if hit[3] == "postal code" else None) if x) or hit[2]
                    out[r] = {"lat": hit[0], "lon": hit[1], "place": label.title() if label.isupper() else label,
                              "how": f"{which} ({'centre of its postal code' if hit[3] == 'postal code' else 'its town'})", "source": "GLEIF + GeoNames"}
                    break
            if r in out:
                continue
            unplaced[r] = "GLEIF address not found in the postal table" if postal_ready() else "postal table still being built"
            continue
        unplaced[r] = {"wd": "no headquarters or location in Wikidata", "icij": "Offshore Leaks gives no coordinates",
                       "os": "the sanctions list gives no coordinates"}.get(kind, "no location in the sources") if kind != "lei" else "no location in Wikidata, GLEIF record not read"
    return {"places": out, "unplaced": unplaced, "problems": problems, "postal": postal_ready()}
