"""The registers Connections reads, each answer cached in data/connections.db.

- GLEIF (Global Legal Entity Identifier Foundation, api.gleif.org, no key, CC0): every company with an LEI code, its
  direct and ultimate parent (accounting consolidation) and, where a parent is not reported, the declared reason.
- Wikidata (no key, CC0): "owned by" (P127, with share), "parent organisation" (P749), "subsidiary" (P355),
  "owner of" (P1830), LEI (P1278) to join it with GLEIF. Wikidata limits clients: one request at a time here.
- ICIJ Offshore Leaks (local copy, icij.py): shareholders, beneficial owners, directors, intermediaries.
- OpenSanctions (local list of sanctioned companies from the weekly sanctions feed; their API with the free key for
  ownership records of sanctioned entities).
"""
import asyncio
import re
import sqlite3
import time

import httpx

from .. import config
from . import icij, store

GLEIF = "https://api.gleif.org/api/v1"
WD = "https://www.wikidata.org/w/api.php"
WEEK = 7 * 86400
_client = None
_gleif_gate = asyncio.Semaphore(4)
_gleif_times: list[float] = []   # GLEIF allows 60 requests a minute: stay at 55 in any 60 s
_wd_gate = asyncio.Semaphore(1)
_wd_last = [0.0]
_wd_cool = [0.0]          # after Wikidata refuses twice in a row, it is left alone for a minute (and the page says so)
_qs_cool = [0.0]          # the same for Wikidata's query service (a separate limit)
WDQS = "https://query.wikidata.org/sparql"


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        ua = config.USER_AGENT + (f" contact: {config.contact()}" if config.contact() else "")
        _client = httpx.AsyncClient(headers={"User-Agent": ua, "Accept": "application/json"}, timeout=25, follow_redirects=True)
    return _client


class SourceDown(Exception):
    """A register did not answer (or refused). The page says which one; nothing is guessed in its place."""


async def _get_json(url, params=None, gate=None, wd=False):
    if wd and time.monotonic() < _wd_cool[0]:
        raise SourceDown("limiting requests; paused for a minute")
    async with gate:
        for attempt in range(2):
            if wd:                                   # Wikimedia asks for no parallel requests from one client
                wait = 0.35 - (time.monotonic() - _wd_last[0])
                if wait > 0:
                    await asyncio.sleep(wait)
                _wd_last[0] = time.monotonic()
            elif gate is _gleif_gate:
                while True:
                    now = time.monotonic()
                    _gleif_times[:] = [t for t in _gleif_times if now - t < 60]
                    if len(_gleif_times) < 55:
                        break
                    await asyncio.sleep(60 - (now - _gleif_times[0]) + 0.05)
                _gleif_times.append(time.monotonic())
            try:
                r = await client().get(url, params=params)
            except httpx.HTTPError as e:
                raise SourceDown(f"{type(e).__name__}") from e
            if r.status_code == 404:
                return None
            if r.status_code == 429 and attempt == 0:
                await asyncio.sleep(min(8.0, float(r.headers.get("Retry-After", 5) or 5)) + 1)
                continue
            if r.status_code == 429 and wd:
                _wd_cool[0] = time.monotonic() + 60
            if r.status_code >= 400:
                raise SourceDown(f"HTTP {r.status_code}")
            try:
                return r.json()
            except ValueError as e:
                raise SourceDown("not JSON") from e
        raise SourceDown("HTTP 429 (limiting requests)")


async def cached(key, max_age, make):
    hit = await asyncio.to_thread(store.cache_get, key, max_age)
    if hit is not None:
        return hit
    body = await make()
    await asyncio.to_thread(store.cache_put, key, body)
    return body


# ---------------------------------------------------------------- GLEIF
EXCEPTION_WORDS = {
    "NATURAL_PERSONS": "controlled by natural persons, whom GLEIF does not name",
    "NON_CONSOLIDATING": "its parent does not prepare consolidated accounts",
    "NO_KNOWN_PERSON": "declares that no known person or company controls it",
    "NON_PUBLIC": "parent not made public (legal obstacle or detriment declared)",
    "BINDING_LEGAL_COMMITMENTS": "parent withheld under binding legal commitments",
    "LEGAL_OBSTACLES": "parent withheld because of legal obstacles",
    "DISCLOSURE_DETRIMENTAL": "parent withheld: disclosure declared detrimental",
    "DETRIMENT_NOT_EXCLUDED": "parent withheld: detriment not excluded",
    "CONSENT_NOT_OBTAINED": "parent withheld: the parent did not consent",
}


def _gleif_entity(rec):
    a, e = rec["attributes"], rec["attributes"]["entity"]
    addr = e.get("legalAddress") or {}
    hq = e.get("headquartersAddress") or {}
    legal = (e.get("legalName") or {}).get("name")
    others = [n.get("name") for n in (e.get("transliteratedOtherNames") or []) + (e.get("otherNames") or []) if n.get("name")]
    latin = lambda t: t and not re.search(r"[^\x00-\u024F\s\d\W]", t)
    shown = legal if latin(legal) else next((o for o in others if latin(o)), legal)   # a Latin-script name to read, the legal name kept in the facts
    return {"lei": rec["id"], "name": shown, "legal_name": legal,
            "other_names": [n.get("name") for n in (e.get("otherNames") or []) + (e.get("transliteratedOtherNames") or []) if n.get("name")][:4],
            "country": addr.get("country"), "city": addr.get("city"), "hq_city": hq.get("city"), "hq_country": hq.get("country"),
            "jurisdiction": e.get("jurisdiction"), "legal_form": (e.get("legalForm") or {}).get("other") or (e.get("legalForm") or {}).get("id"),
            "status": e.get("status"), "category": e.get("category"), "registered_as": e.get("registeredAs"),
            "postal": addr.get("postalCode"), "hq_postal": hq.get("postalCode"),
            "created": (e.get("creationDate") or "")[:10] or None, "lei_status": (a.get("registration") or {}).get("status"),
            "has": {k: list((v.get("links") or {}).keys()) for k, v in (rec.get("relationships") or {}).items() if k in ("direct-parent", "ultimate-parent")}}


async def gleif_record(lei):
    async def make():
        d = await _get_json(f"{GLEIF}/lei-records/{lei}", gate=_gleif_gate)
        return _gleif_entity(d["data"]) if d else None
    return await cached("gleif3:rec:" + lei, WEEK, make)


async def gleif_records(leis) -> dict:
    """Several records at once (GLEIF takes a list of LEIs in one request), each remembered a week like gleif_record."""
    out, need = {}, []
    for l in dict.fromkeys(leis):
        hit = await asyncio.to_thread(store.cache_get, "gleif3:rec:" + l, WEEK)
        if hit is not None:
            if hit:
                out[l] = hit
        else:
            need.append(l)
    for i in range(0, len(need), 100):
        chunk = need[i:i + 100]
        d = await _get_json(f"{GLEIF}/lei-records", params={"filter[lei]": ",".join(chunk), "page[size]": 100}, gate=_gleif_gate)
        for x in (d or {}).get("data", []):
            rec = _gleif_entity(x)
            out[rec["lei"]] = rec
            await asyncio.to_thread(store.cache_put, "gleif3:rec:" + rec["lei"], rec)
    return out


async def sparql(q: str) -> list:
    """Rows of a query to Wikidata's query service (POST, so long VALUES lists fit). One request at a time with the
    other Wikidata calls; after two refusals in a row the service is left alone for a minute."""
    if time.monotonic() < _qs_cool[0]:
        raise SourceDown("query service limiting requests; paused for a minute")
    async with _wd_gate:
        for attempt in range(2):
            wait = 0.35 - (time.monotonic() - _wd_last[0])
            if wait > 0:
                await asyncio.sleep(wait)
            _wd_last[0] = time.monotonic()
            try:
                r = await client().post(WDQS, data={"query": q}, headers={"Accept": "application/sparql-results+json"}, timeout=60)
            except httpx.HTTPError as e:
                raise SourceDown(type(e).__name__) from e
            if r.status_code in (429, 502, 503, 504) and attempt == 0:      # limited, or a passing server error: once more
                await asyncio.sleep(min(8.0, float(r.headers.get("Retry-After", 3) or 3)) + 1)
                continue
            if r.status_code == 429:
                _qs_cool[0] = time.monotonic() + 60
            if r.status_code >= 400:
                raise SourceDown(f"HTTP {r.status_code}")
            try:
                return r.json()["results"]["bindings"]
            except (ValueError, KeyError) as e:
                raise SourceDown("not JSON") from e
        raise SourceDown("HTTP 429 (limiting requests)")


async def gleif_parents(lei):
    """{'direct': record|None, 'ultimate': record|None, 'direct_exception': reason|None, 'ultimate_exception': ...}"""
    async def make():
        rec = await gleif_record(lei)
        out = {"direct": None, "ultimate": None, "direct_exception": None, "ultimate_exception": None}
        if not rec:
            return out
        for kind in ("direct", "ultimate"):
            links = rec["has"].get(kind + "-parent", [])
            if "lei-record" in links:
                d = await _get_json(f"{GLEIF}/lei-records/{lei}/{kind}-parent", gate=_gleif_gate)
                if d and d.get("data"):
                    out[kind] = _gleif_entity(d["data"])
            if not out[kind]:
                d = await _get_json(f"{GLEIF}/lei-records/{lei}/{kind}-parent-reporting-exception", gate=_gleif_gate)
                if d and d.get("data"):
                    out[kind + "_exception"] = d["data"]["attributes"].get("reason")
        return out
    return await cached("gleif2:par:" + lei, WEEK, make)


async def gleif_children(lei, page=1, size=50, kind="direct"):
    """kind "direct": companies naming it as direct parent; "ultimate": everything it consolidates at the top."""
    async def make():
        d = await _get_json(f"{GLEIF}/lei-records/{lei}/{kind}-children", params={"page[size]": size, "page[number]": page}, gate=_gleif_gate)
        if not d:
            return {"items": [], "total": 0}
        return {"items": [_gleif_entity(x) for x in d.get("data", [])], "total": d.get("meta", {}).get("pagination", {}).get("total", 0)}
    return await cached(f"gleif2:kids:{lei}:{page}:{size}" + ("" if kind == "direct" else ":" + kind), WEEK, make)


async def gleif_search(q):
    async def make():
        d = await _get_json(f"{GLEIF}/lei-records", params={"filter[fulltext]": q, "page[size]": 12}, gate=_gleif_gate)
        return [_gleif_entity(x) for x in (d or {}).get("data", [])]
    return await cached("gleif2:q:" + q.lower(), 86400, make)


# ---------------------------------------------------------------- Wikidata
WD_PROPS = ("P31", "P17", "P127", "P749", "P355", "P1830", "P1278", "P571", "P576", "P452", "P159", "P856", "P2622", "P1320", "P458")


def _wd_val(snak):
    v = (snak.get("datavalue") or {}).get("value")
    if isinstance(v, dict):
        return v.get("id") or v.get("time") or v.get("amount") or v.get("text")
    return v


def _wd_compact(e):
    claims = {}
    for p in WD_PROPS:
        out = []
        for c in e.get("claims", {}).get(p, []):
            if c.get("rank") == "deprecated":
                continue
            q = c.get("qualifiers") or {}
            qv = lambda k: _wd_val(q[k][0]["mainsnak"] if "mainsnak" in q[k][0] else q[k][0]) if k in q else None
            out.append({"v": _wd_val(c["mainsnak"]), "share": qv("P1107"), "start": qv("P580"), "end": qv("P582"), "rank": c.get("rank")})
        if out:
            claims[p] = out
    lab = e.get("labels", {})
    name = (lab.get("en") or lab.get("mul") or next(iter(lab.values()), {}) or {}).get("value")
    desc = (e.get("descriptions", {}).get("en") or {}).get("value")
    al = e.get("aliases", {})
    aliases = [a.get("value") for k in ("en", "mul") for a in al.get(k, []) if a.get("value")][:12]
    return {"qid": e.get("id"), "name": name, "desc": desc, "claims": claims, "aliases": aliases}


async def wd_entities(qids):
    """Compact items (labels, the properties above), cached per item a week. Missing items are left out."""
    qids = [q for q in dict.fromkeys(qids) if q and re.fullmatch(r"Q\d+", q)]
    have = {}
    for q in qids:
        hit = await asyncio.to_thread(store.cache_get, "wd:" + q, WEEK)
        if hit is not None:
            have[q] = hit
    need = [q for q in qids if q not in have]
    for i in range(0, len(need), 50):
        chunk = need[i:i + 50]
        d = await _get_json(WD, params={"action": "wbgetentities", "ids": "|".join(chunk), "props": "labels|descriptions|claims|aliases",
                                        "languages": "en|mul|de|fr|es|ru|zh", "format": "json"}, gate=_wd_gate, wd=True)
        for q, e in ((d or {}).get("entities") or {}).items():
            if "missing" in e:
                continue
            c = _wd_compact(e)
            have[q] = c
            await asyncio.to_thread(store.cache_put, "wd:" + q, c)
    return have


async def wd_reverse(prop, qid, limit=50):
    """Items whose `prop` points at qid (e.g. P127=Q -> things qid owns), via Wikidata's own search index."""
    async def make():
        d = await _get_json(WD, params={"action": "query", "list": "search", "srsearch": f"haswbstatement:{prop}={qid}", "srlimit": limit,
                                        "srnamespace": 0, "format": "json"}, gate=_wd_gate, wd=True)
        q = (d or {}).get("query") or {}
        return {"ids": [x["title"] for x in q.get("search", [])], "total": (q.get("searchinfo") or {}).get("totalhits", 0)}
    return await cached(f"wdrev:{prop}:{qid}:{limit}", WEEK, make)


async def wd_by_lei(lei):
    r = await wd_reverse("P1278", lei, 3)
    return r["ids"][0] if r["ids"] else None


async def wd_search(q):
    async def make():
        d = await _get_json(WD, params={"action": "wbsearchentities", "search": q, "language": "en", "uselang": "en", "type": "item",
                                        "limit": 12, "format": "json"}, gate=_wd_gate, wd=True)
        return [{"qid": h["id"], "name": h.get("label"), "desc": h.get("description")} for h in (d or {}).get("search", [])]
    return await cached("wdq:" + q.lower(), 86400, make)


# ---------------------------------------------------------------- ICIJ (local)
ICIJ_SAME = {"same_company_as", "same_id_as", "same_as"}
OWN_LINK = re.compile(r"sharehold|owner|beneficia|member of|partner of|protector|settlor|founder", re.I)
_icij_local = None


def _icij():
    import threading
    global _icij_local
    if _icij_local is None:
        _icij_local = threading.local()
    c = getattr(_icij_local, "c", None)
    if c is None:
        if not icij.db_path().exists():
            return None
        c = sqlite3.connect(f"file:{icij.db_path()}?mode=ro", uri=True, check_same_thread=False)
        c.row_factory = sqlite3.Row
        _icij_local.c = c
    return c


def icij_ready() -> bool:
    return icij.db_path().exists()


def icij_node(nid):
    c = _icij()
    if not c:
        return None
    r = c.execute("SELECT * FROM node WHERE id = ?", (nid,)).fetchone()
    return dict(r) if r else None


def icij_links(nid):
    """Every non-address link of a node, both directions, with the other end."""
    c = _icij()
    if not c:
        return []
    out = []
    for r in c.execute("SELECT r.*, n.id AS oid, n.kind AS okind, n.name AS oname, n.jur AS ojur, n.countries AS ocountries, n.source AS osource "
                       "FROM rel r JOIN node n ON n.id = r.b WHERE r.a = ? LIMIT 400", (nid,)):
        out.append({**dict(r), "dir": "out"})
    for r in c.execute("SELECT r.*, n.id AS oid, n.kind AS okind, n.name AS oname, n.jur AS ojur, n.countries AS ocountries, n.source AS osource "
                       "FROM rel r JOIN node n ON n.id = r.a WHERE r.b = ? LIMIT 400", (nid,)):
        out.append({**dict(r), "dir": "in"})
    return out


def icij_search(q, limit=20):
    c = _icij()
    if not c:
        return []
    words = [w for w in re.findall(r"\w+", q, re.UNICODE) if len(w) > 1][:6]
    if not words:
        return []
    expr = " ".join(f'"{w}"*' for w in words)
    rows = c.execute("SELECT n.* FROM names JOIN node n ON n.id = names.id WHERE names MATCH ? ORDER BY rank LIMIT ?", (expr, limit)).fetchall()
    return [dict(r) for r in rows]


def icij_generated():
    c = _icij()
    if not c:
        return None
    r = c.execute("SELECT value FROM info WHERE key='generated'").fetchone()
    return r[0] if r else None
