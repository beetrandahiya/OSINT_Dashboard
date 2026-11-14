"""Profiles of public figures from public records.

Everything here is about people in public roles (heads of state and government, politicians in office,
business leaders) or anyone the user searches for who has a Wikidata entry. It reads only sources that
publish this on purpose: Wikidata, Wikipedia, OpenSanctions' politically-exposed-persons data, LittleSis,
and GDELT for recent news mentions. Each fact carries the source it came from. Nothing here tracks where a
person is now; "reported at" means a news article named the person together with a place.
"""
import asyncio
import time

import httpx

from .. import config
from . import store

WDQS = "https://query.wikidata.org/sparql"
HEAD = {"User-Agent": config.USER_AGENT, "Accept": "application/sparql-results+json"}

# Wikidata property -> (section, human label). Grouped the way the profile is laid out.
POSITION = "P39"
REL = {  # person -> these, read from the person's own item
    "P102": ("identity", "party"), "P69": ("background", "educated at"), "P26": ("ties", "spouse"),
    "P40": ("ties", "child"), "P22": ("ties", "father"), "P25": ("ties", "mother"), "P3373": ("ties", "sibling"),
    "P463": ("ties", "member of"), "P166": ("background", "award"), "P108": ("holdings", "employer"),
    "P1830": ("holdings", "owns"),
}
BACK = {  # these items -> point at the person (the person is the object)
    "P112": ("holdings", "founded"), "P127": ("holdings", "owned by them"), "P169": ("holdings", "chief executive of"),
    "P488": ("holdings", "chair of"), "P749": ("holdings", "parent org of"),
}


async def _sparql(client, query):
    for attempt in range(2):
        r = await client.get(WDQS, params={"query": query, "format": "json"}, headers=HEAD, timeout=60)
        if r.status_code == 429 and attempt == 0:
            await asyncio.sleep(float(r.headers.get("Retry-After", 5)) + 1)
            continue
        r.raise_for_status()
        return r.json()["results"]["bindings"]


def _qid(uri):
    return uri.rsplit("/", 1)[-1]


async def search(query: str) -> list[dict]:
    """People matching a name, from Wikidata. Non-humans are dropped."""
    async with httpx.AsyncClient(headers={"User-Agent": config.USER_AGENT}, timeout=20) as c:
        r = await c.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities", "search": query, "language": "en", "uselang": "en", "type": "item", "limit": 15, "format": "json"})
        r.raise_for_status()
        hits = r.json().get("search", [])
        if not hits:
            return []
        ids = [h["id"] for h in hits]
        rows = await _sparql(c, "SELECT ?p WHERE { VALUES ?p {" + " ".join("wd:" + i for i in ids) + "} ?p wdt:P31 wd:Q5. }")
        humans = {_qid(x["p"]["value"]) for x in rows}
    return [{"qid": h["id"], "name": h["label"], "description": h.get("description", "")} for h in hits if h["id"] in humans]


async def _basics(client, qid):
    r = await client.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", headers={"User-Agent": config.USER_AGENT}, timeout=30)
    r.raise_for_status()
    e = r.json()["entities"][qid]
    claims, out = e.get("claims", {}), {}

    def first(pid):
        for st in claims.get(pid, []):
            v = st.get("mainsnak", {}).get("datavalue", {}).get("value")
            if v is not None:
                return v
        return None

    img = first("P18")
    out["image"] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{img.replace(' ', '_')}?width=400" if img else None
    born = first("P569")
    out["born"] = born["time"].lstrip("+")[:10] if isinstance(born, dict) and born.get("time") else None
    died = first("P570")
    out["died"] = died["time"].lstrip("+")[:10] if isinstance(died, dict) and died.get("time") else None
    out["labels"] = {"en": (e.get("labels", {}).get("en", {}) or {}).get("value")}
    out["sitelinks"] = {k: v["title"] for k, v in e.get("sitelinks", {}).items() if k in ("enwiki",)}
    out["official_website"] = first("P856")
    socials = {}
    for pid, name in [("P2002", "x.com/"), ("P2003", "instagram.com/"), ("P2013", "facebook.com/"), ("P7085", "tiktok.com/@"), ("P2397", None)]:
        v = first(pid)
        if v and name:
            socials[name] = "https://" + name + v
    out["socials"] = socials
    return out


async def _label_map(client, qids):
    qids = [q for q in qids if q]
    out = {}
    for i in range(0, len(qids), 180):
        batch = qids[i:i + 180]
        rows = await _sparql(client, "SELECT ?i ?iLabel WHERE { VALUES ?i {" + " ".join("wd:" + q for q in batch) + "} SERVICE wikibase:label { bd:serviceParam wikibase:language 'en'. } }")
        for x in rows:
            out[_qid(x["i"]["value"])] = x["iLabel"]["value"]
    return out


async def _relations(client, qid):
    forward = " ".join(f"p:{p}" for p in [POSITION, *REL])
    q = f"""SELECT ?prop ?v ?start ?end ?of WHERE {{
      VALUES ?prop {{ {forward} }} wd:{qid} ?prop ?st. ?st ?ps ?v. FILTER(STRSTARTS(STR(?ps),"http://www.wikidata.org/prop/statement/P"))
      OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }} OPTIONAL {{ ?st pq:P642 ?of }} }}"""
    rows = await _sparql(client, q)
    back = " ".join(f"{{ ?v wdt:{p} wd:{qid}. BIND('{p}' AS ?prop) }}" for p in BACK)
    brows = await _sparql(client, f"SELECT ?prop ?v WHERE {{ {back} }}")

    positions, ties, holdings, identity, background, qids = [], [], [], [], [], set()
    dv = lambda x, k: _qid(x[k]["value"]) if k in x and x[k]["value"].startswith("http") else (x[k]["value"] if k in x else None)
    seen = set()
    for x in rows:
        pid = _qid(x["prop"]["value"])
        v = dv(x, "v")
        if not v or not str(v).startswith("Q"):
            continue
        qids.add(v)
        if pid == POSITION:
            key = (v, (x.get("start", {}).get("value") or "")[:10])
            if key in seen:
                continue
            seen.add(key)
            of = dv(x, "of")
            if of:
                qids.add(of)
            positions.append({"item": v, "of": of, "start": (x.get("start", {}).get("value") or "")[:10], "end": (x.get("end", {}).get("value") or "")[:10]})
        else:
            sect, label = REL[pid]
            rec = {"item": v, "label": label}
            bucket = {"ties": ties, "holdings": holdings, "identity": identity, "background": background}[sect]
            if rec not in bucket:
                bucket.append(rec)
    for x in brows:
        pid, v = _qid(x["prop"]["value"]), dv(x, "v")
        if v and str(v).startswith("Q"):
            qids.add(v)
            holdings.append({"item": v, "label": BACK[pid][1]})
    return {"positions": positions, "ties": ties, "holdings": holdings, "identity": identity, "background": background}, qids


async def _wikipedia(client, title):
    try:
        r = await client.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": title, "format": "json", "redirects": 1},
            headers={"User-Agent": config.USER_AGENT}, timeout=20)
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        return next(iter(pages.values()), {}).get("extract")
    except httpx.HTTPError:
        return None


async def _sanctions(client, name, born=None):
    """Politically-exposed-person and sanctions listings from OpenSanctions. Their API needs a free key
    (data/opensanctions-key.txt); without it this section is skipped."""
    key = config.opensanctions_key()
    if not key:
        return [], "no OpenSanctions key set, so sanctions and PEP lists were not checked"
    try:
        props = {"name": [name]}
        if born:
            props["birthDate"] = [born]
        r = await client.post("https://api.opensanctions.org/match/default", params={"algorithm": "logic-v1"},
                              json={"queries": {"q": {"schema": "Person", "properties": props}}},
                              headers={"User-Agent": config.USER_AGENT, "Authorization": "ApiKey " + key}, timeout=20)
        if r.status_code in (401, 403):
            return [], "the OpenSanctions key was refused"
        if r.status_code != 200:
            return [], f"OpenSanctions answered {r.status_code}"
        out = []
        for m in r.json().get("responses", {}).get("q", {}).get("results", []):
            if m.get("score", 0) < 0.7:
                continue
            props = m.get("properties", {})
            out.append({"name": m.get("caption"), "score": round(m.get("score", 0), 2),
                        "listed_on": [d.get("title", d.get("name")) for d in m.get("datasets_full", [])] or m.get("datasets", []),
                        "topics": props.get("topics", []), "url": "https://www.opensanctions.org/entities/" + m.get("id", "")})
        return out, None
    except httpx.HTTPError as e:
        return [], f"OpenSanctions could not be reached ({type(e).__name__})"


async def _news(client, name):
    """Recent news articles naming the person, from GDELT. Best-effort: GDELT rate-limits hard."""
    try:
        r = await client.get("https://api.gdeltproject.org/api/v2/doc/doc", params={
            "query": f'"{name}"', "mode": "artlist", "maxrecords": 25, "format": "json", "sort": "datedesc", "timespan": "3d"},
            headers={"User-Agent": config.USER_AGENT}, timeout=20)
        if r.status_code != 200 or not r.text.strip().startswith("{"):
            return [], "GDELT did not answer (it rate-limits shared addresses)"
        arts = r.json().get("articles", [])
        seen, out = set(), []
        for a in arts:
            t = a.get("title", "").strip()
            if not t or t.lower() in seen:
                continue
            seen.add(t.lower())
            out.append({"title": t, "url": a.get("url"), "outlet": a.get("domain"), "seen": a.get("seendate"), "country": a.get("sourcecountry"), "lang": a.get("language")})
        return out[:20], None
    except httpx.HTTPError as e:
        return [], f"GDELT could not be reached ({type(e).__name__})"


async def profile(qid: str) -> dict:
    """The whole profile for one person, built fresh (callers cache it)."""
    problems = []
    async with httpx.AsyncClient() as client:
        basics = await _basics(client, qid)
        name = basics["labels"]["en"] or qid
        rel_task = _relations(client, qid)
        wiki_title = basics["sitelinks"].get("enwiki")
        results = await asyncio.gather(
            rel_task,
            _wikipedia(client, wiki_title) if wiki_title else _noop(None),
            _sanctions(client, name, basics["born"]),
            _news(client, name),
            return_exceptions=True,
        )
        rel_result, wiki, sanc_result, news_result = results
        if isinstance(rel_result, Exception):
            relations, qids = {"positions": [], "ties": [], "holdings": [], "identity": [], "background": []}, set()
            problems.append(f"Wikidata relations failed ({type(rel_result).__name__})")
        else:
            relations, qids = rel_result
        labels = {}
        if qids:
            try:
                labels = await _label_map(client, list(qids))
            except httpx.HTTPError:
                problems.append("Some Wikidata labels could not be loaded")
        intro = None if isinstance(wiki, Exception) else wiki
        sanctions, sprob = ([], "sanctions check failed") if isinstance(sanc_result, Exception) else sanc_result
        news, nprob = ([], "news check failed") if isinstance(news_result, Exception) else news_result
        for p in (sprob, nprob):
            if p:
                problems.append(p)

    def name_of(q):
        return labels.get(q, q)

    positions = sorted(
        [{**p, "name": name_of(p["item"]), "of": name_of(p["of"]) if p["of"] else None} for p in relations["positions"]],
        key=lambda p: p["start"] or "0000", reverse=True)
    current = [p for p in positions if not p["end"]]
    sect = lambda s: [{**r, "name": name_of(r["item"])} for r in relations[s]]
    return {
        "qid": qid, "name": name, "image": basics["image"], "born": basics["born"], "died": basics["died"],
        "intro": intro, "official_website": basics["official_website"], "socials": basics["socials"],
        "wikipedia": f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}" if wiki_title else None,
        "wikidata": f"https://www.wikidata.org/wiki/{qid}",
        "current_roles": current, "positions": positions,
        "identity": sect("identity"), "ties": sect("ties"), "holdings": sect("holdings"), "background": sect("background"),
        "sanctions": sanctions, "news": news, "problems": problems, "built": time.time(),
    }


async def _noop(v):
    return v


# ---- the People map layer: current heads of state and government at their countries ----
async def leaders() -> list[dict]:
    """Current heads of state and of government of sovereign states, each at the country's point.
    Two small queries, one per role: the combined query timed out on Wikidata's side."""
    out = {}
    async with httpx.AsyncClient() as client:
        for pid, role in (("P35", "Head of state"), ("P6", "Head of government")):
            q = f"""SELECT ?person ?personLabel ?country ?countryLabel ?coord WHERE {{
              ?country wdt:P31 wd:Q3624078; p:{pid} ?st; wdt:P625 ?coord. ?st ps:{pid} ?person.
              FILTER NOT EXISTS {{ ?st pq:P582 ?e }}. ?person wdt:P31 wd:Q5.
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
            for x in await _sparql(client, q):
                try:
                    lon, lat = map(float, x["coord"]["value"].removeprefix("Point(").removesuffix(")").split())
                except (KeyError, ValueError):
                    continue
                qid = _qid(x["person"]["value"])
                key = (qid, x["country"]["value"])
                if key in out:
                    out[key]["role"] = "Head of state and government"
                    continue
                out[key] = {"qid": qid, "name": x["personLabel"]["value"], "role": role,
                            "country": x["countryLabel"]["value"], "lon": lon, "lat": lat}
            await asyncio.sleep(1)
    return list(out.values())
