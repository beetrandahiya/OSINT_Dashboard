"""One entity as Connections shows it: the records of every source joined on shared identifiers (an LEI code in GLEIF
and in Wikidata's P1278), never on names alone, plus its owners, its holdings and the people and firms around it.

References ("refs") name a record in one source: lei:<LEI>, wd:<QID>, icij:<node id>. The canonical ref of a joined
entity is its LEI if it has one, else its Wikidata id, else the record it started from.

Edges point from owner to asset. Every edge says which source states it and how (direct parent for accounts,
"owned by" with share, shareholder of, beneficial owner of...), with dates where the source gives them.
"""
import asyncio
import re

from . import icij as icij_mod
from . import sanctioned as sanc
from . import sources as S

STATE_CLASSES = {"Q6256", "Q3624078", "Q7275", "Q327333", "Q2659904", "Q1802419", "Q35798", "Q192350"}   # country, sovereign state, state, govt agency, govt org...
HUMAN = "Q5"
ICIJ_URL = "https://offshoreleaks.icij.org/nodes/"


def _edge(ref, name, kind, country, label, source, **kw):
    return {"ref": ref, "name": name, "kind": kind, "country": country, "label": label, "source": source, **{k: v for k, v in kw.items() if v not in (None, "", [])}}


def _wd_kind(item):
    p31 = {c["v"] for c in item.get("claims", {}).get("P31", [])}
    if HUMAN in p31:
        return "person"
    if p31 & STATE_CLASSES:
        return "state"
    return "organisation"


def _gleif_kind(rec):
    return "state" if (rec.get("category") or "") in ("RESIDENT_GOVERNMENT_ENTITY", "INTERNATIONAL_ORGANIZATION") else "company"


def _icij_kind(kind, name):
    k = icij_mod.KIND_NAME.get(kind, "entity")
    if re.fullmatch(r"\s*(the\s+)?bearer(\s+shares?)?\s*", name or "", re.I):
        return "bearer"                       # bearer shares: whoever holds the paper certificate owns the company
    if k == "officer":
        return "company" if icij_mod.ORG.search(name or "") else "person"
    return {"entity": "company", "intermediary": "intermediary", "other": "company"}[k]


def _wd_time(t):
    return t[1:11] if isinstance(t, str) and t.startswith(("+", "-")) else t


async def _safe(problems, label, coro):
    try:
        return await coro
    except S.SourceDown as e:
        problems.append(f"{label} did not answer ({e})")
    except Exception as e:                          # one source failing must not blank the entity
        problems.append(f"{label}: {type(e).__name__}")
    return None


async def build(ref: str, holdings_limit: int = 60) -> dict:
    problems: list[str] = []
    kind_of, _, key = ref.partition(":")
    leis, qids, icij_ids = set(), set(), set()
    if kind_of == "lei":
        leis.add(key.upper())
    elif kind_of == "wd":
        qids.add(key.upper())
    elif kind_of == "icij":
        icij_ids.add(int(key))
    elif kind_of == "os":
        osrow = sanc.get(key)
        if not osrow:
            return {"ref": ref, "error": "not in the local sanctions list (it is filled by the weekly sanctions feed)"}
        leis.update(sanc.leis_of(osrow))
    else:
        return {"ref": ref, "error": "unknown reference"}

    # --- join: LEI <-> Wikidata
    for lei in list(leis):
        q = await _safe(problems, "Wikidata", S.wd_by_lei(lei))
        if q:
            qids.add(q)
    items = await _safe(problems, "Wikidata", S.wd_entities(list(qids))) or {}
    for it in items.values():
        for c in it["claims"].get("P1278", []):
            if c["v"]:
                leis.add(str(c["v"]).upper())
    gleif = {}
    for lei in leis:
        rec = await _safe(problems, "GLEIF", S.gleif_record(lei))
        if rec:
            gleif[lei] = rec

    canon = (f"lei:{sorted(gleif)[0]}" if gleif else f"wd:{sorted(qids)[0]}" if qids else ref)
    osrow = locals().get("osrow")
    node = {"ref": canon, "refs": sorted({f"lei:{l}" for l in gleif} | {f"wd:{q}" for q in items} | {f"icij:{i}" for i in icij_ids}),
            "facts": [], "links": [], "owners": [], "holdings": [], "holdings_total": {}, "roles": [], "exceptions": [], "related": [],
            "problems": problems}
    names, kinds, countries = [], [], []

    # --- facts per source
    for lei, g in gleif.items():
        names.append(g["name"]); kinds.append(_gleif_kind(g)); countries.append(g.get("country"))
        node["facts"] += [{"label": k, "value": v, "source": "GLEIF"} for k, v in (
            ("LEI", lei), ("Legal name", g.get("legal_name") or g["name"]), ("Other names", ", ".join(g.get("other_names") or [])),
            ("Legal form", g.get("legal_form")), ("Jurisdiction", g.get("jurisdiction")),
            ("Registered in", ", ".join(x for x in (g.get("city"), g.get("country")) if x)),
            ("Headquarters", ", ".join(x for x in (g.get("hq_city"), g.get("hq_country")) if x)),
            ("Register number", g.get("registered_as")), ("Status", g.get("status")), ("Founded (per GLEIF)", g.get("created")),
            ("LEI record", g.get("lei_status"))) if v]
        node["links"].append({"label": "GLEIF record", "url": f"https://search.gleif.org/#/record/{lei}"})
    for q, it in items.items():
        names.append(it["name"]); kinds.append(_wd_kind(it))
        c = it["claims"]
        node["facts"] += [{"label": k, "value": v, "source": "Wikidata"} for k, v in (
            ("Description", it.get("desc")), ("Founded", _wd_time((c.get("P571") or [{}])[0].get("v"))),
            ("Dissolved", _wd_time((c.get("P576") or [{}])[0].get("v"))), ("Website", (c.get("P856") or [{}])[0].get("v")),
            ("UK company number", (c.get("P2622") or [{}])[0].get("v")), ("IMO number", (c.get("P458") or [{}])[0].get("v"))) if v]
        node["links"].append({"label": "Wikidata " + q, "url": f"https://www.wikidata.org/wiki/{q}"})
    # ICIJ's own matches ("same company as", "same id as", "same name and registration date as") join records: a
    # shareholder company appears as an officer record, its own shareholders sit on its entity record
    seen_i, todo = set(), list(icij_ids)
    while todo and len(seen_i) < 6:
        i = todo.pop()
        if i in seen_i:
            continue
        seen_i.add(i)
        for l in S.icij_links(i):
            if l["type"] in S.ICIJ_SAME and l["oid"] not in seen_i:
                todo.append(l["oid"])
    icij_ids = seen_i
    if icij_ids:
        node["refs"] = sorted(set(node["refs"]) | {f"icij:{i}" for i in icij_ids})
    icij_rows = {}
    for i in sorted(icij_ids, key=lambda x: (S.icij_node(x) or {}).get("kind", 9)):
        n = S.icij_node(i)
        if not n:
            problems.append(f"Offshore Leaks has no record {i}")
            continue
        icij_rows[i] = n
        names.append(n["name"]); kinds.append(_icij_kind(n["kind"], n["name"])); countries.append(n.get("countries"))
        node["facts"] += [{"label": k, "value": v, "source": "Offshore Leaks"} for k, v in (
            ("Record kind", icij_mod.KIND_NAME.get(n["kind"])), ("Jurisdiction", n.get("jur")), ("Countries linked", n.get("countries")),
            ("Incorporated", n.get("inc")), ("Inactive / struck off", n.get("gone")), ("Status", n.get("status")),
            ("Company type", n.get("ctype")), ("Set up through", n.get("provider")), ("Registered office (as ICIJ shows it)", n.get("addr")),
            ("Leak", n.get("source"))) if v]
        node["links"].append({"label": "ICIJ Offshore Leaks page", "url": ICIJ_URL + str(i)})
    if osrow:
        names.append(osrow["name"]); kinds.append("company"); countries.append(osrow.get("countries"))
        node["facts"] += [{"label": k, "value": v, "source": "OpenSanctions"} for k, v in (
            ("Listed name", osrow["name"]), ("Also known as", (osrow.get("aliases") or "").replace(";", "; ")[:300]),
            ("Countries", osrow.get("countries")), ("Identifiers", (osrow.get("identifiers") or "").replace(";", "; ")[:300]),
            ("Sanctions", osrow.get("sanctions")), ("On lists since", (osrow.get("first_seen") or "")[:10])) if v]
        node["links"].append({"label": "OpenSanctions record", "url": "https://www.opensanctions.org/entities/" + key})
    node["name"] = next((x for x in names if x), key)
    node["kind"] = "person" if "person" in kinds else "state" if "state" in kinds else (kinds[0] if kinds else "organisation")
    node["country"] = next((x for x in countries if x), None)

    owners, holdings = {}, {}

    def add(bucket, e):
        k = e["ref"]
        if k in bucket:                                 # the same link from two sources: keep both statements
            b = bucket[k]
            b["also"] = b.get("also", []) + [{"label": e["label"], "source": e["source"], **({"share": e["share"]} if e.get("share") else {})}]
        else:
            bucket[k] = e

    # --- GLEIF parents and children
    for lei in gleif:
        par = await _safe(problems, "GLEIF", S.gleif_parents(lei)) or {}
        d, u = par.get("direct"), par.get("ultimate")
        if d:
            add(owners, _edge(f"lei:{d['lei']}", d["name"], _gleif_kind(d), d.get("country"), "direct parent (consolidates its accounts)", "GLEIF"))
        elif par.get("direct_exception"):
            node["exceptions"].append({"text": S.EXCEPTION_WORDS.get(par["direct_exception"], par["direct_exception"]), "code": par["direct_exception"], "source": "GLEIF", "level": "direct"})
        if u and (not d or u["lei"] != d["lei"]) and not d:
            add(owners, _edge(f"lei:{u['lei']}", u["name"], _gleif_kind(u), u.get("country"), "ultimate parent (links in between not reported)", "GLEIF", ultimate=True))
        if not u and par.get("ultimate_exception") and par.get("ultimate_exception") != par.get("direct_exception"):
            node["exceptions"].append({"text": S.EXCEPTION_WORDS.get(par["ultimate_exception"], par["ultimate_exception"]), "code": par["ultimate_exception"], "source": "GLEIF", "level": "ultimate"})
        kids = await _safe(problems, "GLEIF", S.gleif_children(lei)) or {"items": [], "total": 0}
        node["holdings_total"]["GLEIF"] = kids["total"]
        for k in kids["items"]:
            add(holdings, _edge(f"lei:{k['lei']}", k["name"], _gleif_kind(k), k.get("country"), "direct subsidiary (consolidated)", "GLEIF"))

    # --- Wikidata owners and holdings
    wd_owner, wd_hold = [], []          # (qid, label, share, start, end)
    for q, it in items.items():
        c = it["claims"]
        for p, lab in (("P127", "owned by"), ("P749", "parent organisation")):
            for cl in c.get(p, []):
                if cl["v"] and not cl.get("end"):
                    wd_owner.append((cl["v"], lab, cl.get("share"), cl.get("start")))
        for p, lab in (("P355", "subsidiary"), ("P1830", "owner of")):
            for cl in c.get(p, []):
                if cl["v"] and not cl.get("end"):
                    wd_hold.append((cl["v"], lab, cl.get("share"), cl.get("start")))
        for p, lab in (("P355", "lists it as a subsidiary"), ("P1830", "says it owns it")):
            r = await _safe(problems, "Wikidata", S.wd_reverse(p, q))
            for x in (r or {}).get("ids", []):
                wd_owner.append((x, lab, None, None))
        tot = 0
        for p, lab in (("P127", "owned by it"), ("P749", "names it as parent")):
            r = await _safe(problems, "Wikidata", S.wd_reverse(p, q))
            tot += (r or {}).get("total", 0)
            for x in (r or {}).get("ids", []):
                wd_hold.append((x, lab, None, None))
        node["holdings_total"]["Wikidata"] = tot + len(c.get("P355", [])) + len(c.get("P1830", []))
    want = [x[0] for x in wd_owner + wd_hold if x[0] not in items]
    more = await _safe(problems, "Wikidata", S.wd_entities(want)) or {}
    for (qid, lab, share, start), bucket in [(x, owners) for x in wd_owner] + [(x, holdings) for x in wd_hold]:
        it = more.get(qid)
        if not it or qid in items:
            continue
        lei = next((str(c["v"]).upper() for c in it["claims"].get("P1278", []) if c["v"]), None)
        r = f"lei:{lei}" if lei else f"wd:{qid}"
        add(bucket, _edge(r, it["name"] or qid, _wd_kind(it), None, lab, "Wikidata", share=share, start=_wd_time(start), desc=it.get("desc")))

    # --- Offshore Leaks
    for i in icij_rows:
        for l in S.icij_links(i):
            other = f"icij:{l['oid']}"
            okind = _icij_kind(l["okind"], l["oname"])
            base = dict(start=l.get("start"), end=l.get("end"), leak=l.get("source"))
            link = l.get("link") or l.get("type")
            if l["type"] == "officer_of" and S.OWN_LINK.search(link or ""):
                e = _edge(other, l["oname"], okind, l.get("ocountries"), link, "Offshore Leaks", **base)
                add(owners if l["dir"] == "in" else holdings, e)
            elif l["type"] in ("officer_of", "intermediary_of"):
                node["roles"].append({**_edge(other, l["oname"], okind, l.get("ocountries"), link, "Offshore Leaks", **base),
                                      "dir": "holds a role here" if l["dir"] == "in" else "role it holds"})
            elif l["type"] in S.ICIJ_SAME and l["oid"] in icij_rows or l["oid"] in icij_ids:
                continue                                # joined above
            elif l["type"] == "same_name_as" and icij_rows[i]["kind"] in (2, 3) and l["okind"] in (1, 4):
                # a shareholder company (officer record) and a company record of the same name: ICIJ links them, but a
                # name is not proof, so the chain goes on through a dashed "same name" step instead of a merge
                add(owners, _edge(other, l["oname"], okind, l.get("ocountries"), "same name as (ICIJ's link; may be another company)",
                                  "Offshore Leaks", samename=True, **base))
            else:                                       # same name as / similar / connected to
                node["related"].append(_edge(other, l["oname"], okind, l.get("ocountries"), link, "Offshore Leaks", **base))
        node["holdings_total"]["Offshore Leaks"] = sum(1 for e in holdings.values() if e["source"] == "Offshore Leaks")

    # --- sanctions lists (local copy of OpenSanctions' sanctioned companies; matched on LEI, else exact name)
    node["sanctions"] = await asyncio.to_thread(sanc.match, sorted(gleif), node["name"], node.get("country"))

    node["owners"] = list(owners.values())
    hl = list(holdings.values())
    node["holdings_count"] = len(hl)
    node["holdings"] = hl[:holdings_limit]
    return node


async def search(q: str) -> dict:
    """Organisations by name in every source; registration codes (LEI) and Wikidata ids directly."""
    q = q.strip()
    out, problems = [], []
    if re.fullmatch(r"[0-9A-Z]{18}[0-9]{2}", q.upper()):
        out.append({"ref": f"lei:{q.upper()}", "name": q.upper(), "source": "GLEIF", "kind": "company", "note": "LEI code"})
    if re.fullmatch(r"[Qq]\d+", q):
        out.append({"ref": f"wd:{q.upper()}", "name": q.upper(), "source": "Wikidata", "kind": "organisation", "note": "Wikidata id"})
    g, w = await asyncio.gather(_safe(problems, "GLEIF", S.gleif_search(q)), _safe(problems, "Wikidata", S.wd_search(q)))
    for r in g or []:
        out.append({"ref": f"lei:{r['lei']}", "name": r["name"], "source": "GLEIF", "kind": _gleif_kind(r), "country": r.get("country"),
                    "note": ", ".join(x for x in (r.get("city"), r.get("status") if r.get("status") != "ACTIVE" else None) if x)})
    for r in w or []:
        out.append({"ref": f"wd:{r['qid']}", "name": r["name"], "source": "Wikidata", "kind": "organisation", "note": r.get("desc")})
    for r in await asyncio.to_thread(S.icij_search, q, 25):
        out.append({"ref": f"icij:{r['id']}", "name": r["name"], "source": "Offshore Leaks", "kind": _icij_kind(r["kind"], r["name"]),
                    "country": r.get("countries"), "note": ", ".join(x for x in (r.get("jur"), r.get("source"), (f"inc. {r['inc']}" if r.get("inc") else None)) if x)})
    for r in await asyncio.to_thread(sanc.search, q, 15):
        out.append({"ref": r.get("ref"), "name": r["name"], "source": "OpenSanctions", "kind": "sanctioned", "country": r.get("countries"),
                    "note": "on " + ", ".join(r.get("lists", [])[:3]), "url": r.get("url"), "sanction": True})
    return {"results": out, "problems": problems, "icij": S.icij_ready()}
