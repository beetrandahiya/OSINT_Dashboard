"""Their aircraft and ships now: the live aircraft and ships of the companies in one Connections structure.

The structure's companies come from the page (the refs it has drawn), plus their current subsidiaries that carry an
airline code in Wikidata (one level down: Eurowings Europe under Eurowings). Links, as agreed with the owner:
  - aircraft, registered owner (solid): the owner's airline code in the free registers (adsbdb, else hexdb.io, looked up
    by transponder address) is one of the companies' ICAO codes (Wikidata P230); else the owner's name is a company's
    name (joins.same_name);
  - aircraft, flight number only (dashed): the callsign is a company's ICAO code followed by digits, and the register
    names no company of the structure (someone else's aircraft, or no owner listed, or not looked up yet);
  - ship, owner / operator: a Wikidata ship item with that IMO number names the company as owner (P127, solid) or
    operator (P137, dashed). Ordinary ships' owners are in no free source.
Never on look-alike names, paint, routes or airports. Where Wikidata contradicts itself (a parent lists the company as a
subsidiary, the company's own item names other parents) the link is kept and flagged.
"""
import asyncio
import json
import re
import time

from .. import db
from . import joins
from . import places as P
from . import sources as S

WEEK = 7 * 86400
CALLSIGN = re.compile(r"([A-Z]{3})\d[0-9A-Z]*$")
FEEDS = (("aircraft_view", "adsb.fi, where the map was last looked at"), ("aircraft_near", "adsb.fi, around Munich"),
         ("aircraft_military", "adsb.fi military"), ("aircraft_world", "OpenSky worldwide snapshot"))


def _poss(name):
    return name + ("'" if name.endswith("s") else "'s")


def _q(u):
    return u.rsplit("/", 1)[1] if u else None


async def _per_item(prefix, qids, max_age, query, collect):
    """Cached per item: run `query` (a SPARQL text with %s for the VALUES) for the items not cached, `collect(rows)`
    turns the rows into {qid: body}; items without rows are cached empty too."""
    out, need = {}, []
    for q in dict.fromkeys(q for q in qids if q):
        hit = await asyncio.to_thread(S.store.cache_get, prefix + q, max_age)
        if hit is not None:
            out[q] = hit
        else:
            need.append(q)
    for i in range(0, len(need), 60):
        chunk = need[i:i + 60]
        got = collect(await S.sparql(query % " ".join("wd:" + q for q in chunk)))
        for q in chunk:
            body = got.get(q) or {}
            out[q] = body
            await asyncio.to_thread(S.store.cache_put, prefix + q, body)
    return out


def _facts_rows(rows):
    out = {}
    for b in rows:
        v = lambda k: (b.get(k) or {}).get("value")
        q = _q(v("c"))
        f = out.setdefault(q, {"name": v("cLabel"), "icao": [], "lei": None, "parents": [], "dissolved": None})
        if v("icao") and v("icao") not in f["icao"]:
            f["icao"].append(v("icao"))
        f["lei"] = f["lei"] or v("lei")
        if v("par") and [_q(v("par")), v("parLabel"), v("pp")] not in f["parents"]:
            f["parents"].append([_q(v("par")), v("parLabel"), v("pp")])
        f["dissolved"] = f["dissolved"] or (v("dis") or "")[:10] or None
    return out


async def company_facts(qids):
    """Name, ICAO airline codes, LEI, current parents and owners (with names) and dissolution of each item."""
    return await _per_item("cxfacts:", qids, WEEK, """SELECT ?c ?cLabel ?icao ?lei ?par ?parLabel ?pp ?dis WHERE { VALUES ?c { %s }
      OPTIONAL { ?c wdt:P230 ?icao }
      OPTIONAL { ?c wdt:P1278 ?lei }
      OPTIONAL { { ?c p:P749 ?st . ?st ps:P749 ?par . BIND("parent" AS ?pp) } UNION { ?c p:P127 ?st . ?st ps:P127 ?par . BIND("owner" AS ?pp) }
                 FILTER NOT EXISTS { ?st pq:P582 [] } FILTER NOT EXISTS { ?st wikibase:rank wikibase:DeprecatedRank } }
      OPTIONAL { ?c wdt:P576 ?dis }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul,de,fr,es,it". } }""", _facts_rows)


def _kids_rows(rows):
    out = {}
    for b in rows:
        q, k = _q(b["c"]["value"]), _q(b["k"]["value"])
        ks = out.setdefault(q, {"kids": []})["kids"]
        if k not in ks:
            ks.append(k)
    return out


async def airline_children(qids):
    """Current subsidiaries / owned companies of each item that carry an airline code, not dissolved."""
    return await _per_item("cxkids:", qids, WEEK, """SELECT ?c ?k WHERE { VALUES ?c { %s }
      { ?c p:P355 ?st . ?st ps:P355 ?k } UNION { ?c p:P1830 ?st . ?st ps:P1830 ?k }
      UNION { ?k p:P749 ?st . ?st ps:P749 ?c } UNION { ?k p:P127 ?st . ?st ps:P127 ?c }
      FILTER NOT EXISTS { ?st pq:P582 [] } FILTER NOT EXISTS { ?k wdt:P576 [] } ?k wdt:P230 [] }""", _kids_rows)


def _ship_rows(rows):
    out = {}
    for b in rows:
        v = lambda k: (b.get(k) or {}).get("value")
        q = _q(v("c"))
        out.setdefault(q, {"ships": []})["ships"].append({"imo": v("imo"), "qid": _q(v("s")), "name": v("sLabel"), "how": v("how")})
    return out


async def ships_of(qids):
    """Ships Wikidata says each item owns (P127) or operates (P137), with their IMO numbers; retired ones left out."""
    # the join order is pinned (the planner otherwise starts from every ship with an IMO number and times out)
    return await _per_item("cxships:", qids, WEEK, """SELECT ?c ?s ?sLabel ?imo ?how WHERE { hint:Query hint:optimizer "None" .
      VALUES ?c { %s }
      { ?st ps:P127 ?c . ?s p:P127 ?st . BIND("owner" AS ?how) } UNION { ?st ps:P137 ?c . ?s p:P137 ?st . BIND("operator" AS ?how) }
      ?s wdt:P458 ?imo .
      FILTER NOT EXISTS { ?st pq:P582 [] } FILTER NOT EXISTS { ?s wdt:P576 [] } FILTER NOT EXISTS { ?s wdt:P730 [] }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". } }""", _ship_rows)


# ---------------------------------------------------------------- the registers' owners, as already looked up
_owners = {"at": 0.0, "map": {}}


def _load_owners():
    with db._lock:
        rows = db.conn().execute("SELECT key, body FROM lookups WHERE key LIKE 'acabout:%'").fetchall()
    out = {}
    for k, body in rows:
        try:
            b = json.loads(body)
        except ValueError:
            continue
        if b and b.get("owner"):
            out[k[8:]] = b
    return out


async def owner_index():
    if time.time() - _owners["at"] > 120:
        _owners["map"] = await asyncio.to_thread(_load_owners)
        _owners["at"] = time.time()
    return _owners["map"]


# lookups of aircraft flying a structure's code whose register entry we have not read yet: one a second, in the background
_queue: list = []
_task = {"t": None}


def _kick(hexes):
    for h in hexes:
        if h not in _queue and len(_queue) < 400:
            _queue.append(h)
    if _queue and (_task["t"] is None or _task["t"].done()):
        _task["t"] = asyncio.create_task(_drain())


async def _drain():
    from .. import web
    while _queue:
        h = _queue.pop(0)
        try:
            body = await web._aircraft_about(h)
            if body and body.get("owner"):
                _owners["map"][h] = body
        except Exception:
            pass
        await asyncio.sleep(1.1)


# ---------------------------------------------------------------- live positions
def _live_aircraft():
    from .. import web
    planes = {}
    for name, title in FEEDS:
        st = web.collector.states.get(name)
        if not st or not st.payload:
            continue
        dt = st.data_time or st.fetched or 0
        for a in st.payload.get("aircraft", []):
            if a.get("lat") is None or not a.get("hex"):
                continue
            t = a.get("last_contact") or dt - (a.get("seen_pos_s") or 0)
            old = planes.get(a["hex"])
            if old and old["time"] >= t:
                continue
            alt = a.get("alt_ft")
            if alt is None and a.get("alt_m") is not None:
                alt = round(a["alt_m"] * 3.28084)
            gs = a.get("gs_kt")
            if gs is None and a.get("gs_ms") is not None:
                gs = round(a["gs_ms"] * 1.94384)
            planes[a["hex"]] = {"hex": a["hex"], "flight": (a.get("flight") or "").strip(), "lat": a["lat"], "lon": a["lon"], "track": a.get("track"),
                                "alt_ft": alt, "gs_kt": gs, "ground": a.get("on_ground") or alt == "ground", "type": a.get("type") or (old or {}).get("type"),
                                "category": a.get("category"), "reg": a.get("reg") or (old or {}).get("reg"), "time": t, "src": title,
                                "military": a.get("military")}
    return planes


def _live_ships():
    from .. import web
    from ..ais import stream as ais_stream
    st = web.collector.states.get("ships")
    out = {}
    both = [(s, "Digitraffic AIS (Finnish waters)") for s in ((st.payload or {}).get("ships", []) if st and st.payload else [])]
    both += [(s, "aisstream.io (worldwide AIS)") for s in ais_stream.ships()]
    for s, src in both:
        if s.get("imo") and s.get("lat") is not None:
            old = out.get(str(s["imo"]))
            if not old or (s.get("time") or 0) > (old.get("time") or 0):
                out[str(s["imo"])] = {**s, "src": src}
    return out


def _feed_times():
    from .. import web
    from ..ais import stream as ais_stream
    out = {}
    for name, title in FEEDS + (("ships", "Digitraffic AIS (Finnish waters)"),):
        st = web.collector.states.get(name)
        if st and (st.data_time or st.fetched):
            out[title] = st.data_time or st.fetched
    a = ais_stream.status()
    if a.get("last_message"):
        out["aisstream.io (worldwide AIS)"] = a["last_message"]
    return out


# ---------------------------------------------------------------- the answer
async def assets(refs: list[str], same: dict | None = None) -> dict:
    """refs: the structure the page has drawn, the entity it was opened on first. same: {wd:Q -> the page's ref} for
    companies the page knows under another ref (a GLEIF record joined to a Wikidata item by name and group)."""
    problems = []
    refs = [r for r in dict.fromkeys(refs) if r.startswith(("lei:", "wd:"))][:120]
    focus = refs[0] if refs else None
    leis = [r[4:] for r in refs if r.startswith("lei:")]
    try:
        lei2q = await P.wd_by_leis(leis)
    except S.SourceDown as e:
        return {"error": f"Wikidata did not answer ({e}); the companies' airline codes and ships come from Wikidata"}
    q2ref = {}
    for a, canon in (same or {}).items():
        if a.startswith("wd:") and canon in refs:
            q2ref[a[3:]] = canon
    for r in refs:
        q = r[3:] if r.startswith("wd:") else lei2q.get(r[4:])
        if q:
            q2ref.setdefault(q, r)
    chain = list(q2ref)
    try:
        facts = await company_facts(chain)
        kids = await airline_children(chain)
        extra = [k for q in chain for k in (kids.get(q) or {}).get("kids", []) if k not in q2ref]
        via = {k: q for q in chain for k in (kids.get(q) or {}).get("kids", [])}
        facts.update(await company_facts(extra))
        allq = chain + list(dict.fromkeys(extra))
    except S.SourceDown as e:
        return {"error": f"Wikidata did not answer ({e}); the companies' airline codes and ships come from Wikidata"}
    try:
        ships = await ships_of(allq)
    except S.SourceDown as e:
        ships = {}
        problems.append(f"Wikidata did not answer for the ships ({e}); aircraft only this time")
    structure = set(allq)

    # companies, keyed by the ref the page knows them by (or their LEI / Wikidata id when the page does not draw them)
    comp, by_code, names = {}, {}, []
    for q in allq:
        f = facts.get(q) or {}
        ref = q2ref.get(q) or (f"lei:{f['lei']}" if f.get("lei") else f"wd:{q}")
        inside = [p for p in f.get("parents", []) if p[0] in structure]
        outside = [p for p in f.get("parents", []) if p[0] not in structure]
        flags = []
        if outside:
            who = ", ".join(f"{p[1] or p[0]} ({'parent' if p[2] == 'parent' else 'owner'})" for p in outside[:4])
            if inside or ref == focus:
                flags.append(f"Wikidata also names {who}")
            else:
                flags.append(f"Wikidata disagrees: a company of this structure lists it, but its own item names only {who}")
        comp[ref] = {"ref": ref, "qid": q, "lei": f.get("lei"), "name": f.get("name") or q, "icao": f.get("icao", []), "flags": flags,
                     "in_graph": q in q2ref, "via": (facts.get(via.get(q)) or {}).get("name") if q not in q2ref else None,
                     "owns": 0, "flies": 0, "ships": 0}
        for c in f.get("icao", []):
            by_code.setdefault(c, []).append(ref)
        names.append((joins.variants(f.get("name")), ref))
    for c, lst in by_code.items():          # one code, several items (a brand beside the company): the one with an LEI
        if len(lst) > 1:
            lst.sort(key=lambda r: (not comp[r]["lei"], not comp[r]["in_graph"]))
    code_of = {c: lst[0] for c, lst in by_code.items()}

    def by_name(owner):
        v = joins.variants(owner)
        hits = {ref for vv, ref in names if joins.same_name(v, vv)}
        return hits.pop() if len(hits) == 1 else None

    # aircraft
    planes = await asyncio.to_thread(_live_aircraft)
    owners = await owner_index()
    out, look_up = [], []
    for h, a in planes.items():
        m = CALLSIGN.match(a["flight"])
        op = code_of.get(m.group(1)) if m else None
        reg = owners.get(h)
        own = None
        if reg:
            own = code_of.get((reg.get("owner_code") or "").upper()) or by_name(reg.get("owner"))
        if not op and not own:
            continue
        if op and not reg:
            look_up.append(h)
        model = " ".join(x for x in ((reg or {}).get("maker"), (reg or {}).get("model")) if x) or None
        if own:
            link = {"ref": own, "how": "owner", "words": f"registered to {reg['owner']} ({reg.get('source')}"
                    + (f", owner code {reg['owner_code']}" if reg.get("owner_code") else "") + ")"}
            comp[own]["owns"] += 1
        else:
            link = {"ref": op, "how": "flight", "words": f"flies under {_poss(comp[op]['name'])} code {m.group(1)}"}
        if op:
            comp[op]["flies"] += 1
        owner = None
        if reg and not own:
            owner = {"name": reg["owner"], "code": reg.get("owner_code"), "src": reg.get("source"), "outside": True}
        out.append({"kind": "aircraft", "id": h, "label": a["flight"] or a.get("reg") or h, **{k: a[k] for k in ("lat", "lon", "track", "alt_ft", "gs_kt", "ground", "type", "category", "time", "src", "military")},
                    "reg": (reg or {}).get("reg") or a.get("reg"), "model": model, "link": link, "flight_ref": op, "owner": owner,
                    "register": "not looked up yet" if op and not reg else None})
    _kick(look_up)

    # ships
    live = await asyncio.to_thread(_live_ships)
    for q in allq:
        ref = next((r for r, c in comp.items() if c["qid"] == q), None)
        per = {}
        for sh in (ships.get(q) or {}).get("ships", []):       # one entry per ship: owner and operator together
            per.setdefault(str(sh["imo"]), []).append(sh)
        for imo, rows in per.items():
            s = live.get(imo)
            if not s or not ref:
                continue
            hows = {r["how"] for r in rows}
            wdname = next((r["name"] for r in rows if r.get("name") and not re.match(r"^(IMO\b|Q\d+$)", r["name"])), None)
            label = s.get("name") or wdname or f"IMO {imo}"
            verb = "owned and operated" if hows == {"owner", "operator"} else "owned" if "owner" in hows else "operated"
            comp[ref]["ships"] += 1
            out.append({"kind": "ship", "id": s.get("mmsi"), "label": label, "imo": imo, "lat": s["lat"], "lon": s["lon"],
                        "course": s.get("course"), "heading": s.get("heading"), "speed_kn": s.get("speed_kn"), "time": s.get("time"),
                        "src": s["src"], "ship_kind": s.get("kind"),
                        "link": {"ref": ref, "how": "owner" if "owner" in hows else "operator",
                                 "words": f"Wikidata: {wdname or label.title()} (IMO {imo}) is {verb} by {comp[ref]['name']}"},
                        "wd": rows[0].get("qid")})

    # where the companies with assets sit (the page has the others)
    with_assets = [r for r, c in comp.items() if c["owns"] or c["flies"] or c["ships"]]
    try:
        pl = await P.places(with_assets)
    except S.SourceDown as e:
        pl = {"places": {}, "problems": [f"places: {e}"]}
    for r in with_assets:
        comp[r]["place"] = pl["places"].get(r)
    problems += pl.get("problems", [])
    return {"companies": comp, "assets": out, "pending": len(_queue), "feeds": await asyncio.to_thread(_feed_times),
            "aircraft_seen": len(planes), "ships_seen": len(live), "problems": problems, "now": time.time()}
