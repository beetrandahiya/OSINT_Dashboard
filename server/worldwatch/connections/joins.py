"""The second way two register records are taken to be one company, used only where no LEI joins them.

Wikidata often lacks the LEI code that GLEIF has (Swiss, Austrian Airlines, Air Dolomiti, Lufthansa CityLine and
Lufthansa Cargo did on 28 Nov 2026), and the same company then appeared twice. Records are joined only when all hold:
  1. the names agree after legal forms, case, accents and punctuation are set aside ("Lufthansa Cargo Aktiengesellschaft"
     = "Lufthansa Cargo"), or one register's name is the other's name before a dash or bracket, another recorded name
     or an alias ("AIR DOLOMITI S.P.A. - LINEE AEREE REGIONALI EUROPEE" = "Air Dolomiti"); such a shortened or other name
     needs two words, or the same country on both sides (a Mexican "INTERNATIONAL PARTS DISTRIBUTION", other name
     "INTERNATIONAL", had matched the truck maker International). Never a shorter name inside a longer one:
     "Lufthansa" is not "Lufthansa Cargo";
  2. both registers place it in the same group: GLEIF as a direct or ultimate child of a company, Wikidata under the
     item that carries that company's LEI, or under that item's own parent (Wikidata often keeps a "group" item, such
     as Lufthansa Group, beside the company that carries the LEI);
  3. the countries do not disagree, when both registers give one;
  4. exactly one record on each side fits, and the Wikidata item does not carry a different LEI.
Every join says so on the page, with the parent it rests on.
"""
import re
import unicodedata

from .. import geo
from . import sources as S

LEGAL = {
    "ag", "aktiengesellschaft", "gmbh", "mbh", "se", "sa", "spa", "srl", "sarl", "sas", "nv", "bv", "ltd", "limited", "plc", "inc",
    "incorporated", "corp", "corporation", "llc", "lp", "llp", "co", "company", "kg", "kgaa", "oy", "oyj", "ab", "abp", "as", "asa", "aps",
    "pjsc", "ojsc", "jsc", "cjsc", "pao", "oao", "zao", "ooo", "sl", "slu", "sau", "spzoo", "zoo", "kft", "rt", "zrt", "nyrt", "doo", "ad",
    "bhd", "sdn", "pte", "pty", "kk", "the", "and",
}
SPLIT = re.compile(r"\s+[-–—]\s+|\s*\(")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("&", " and ")
    s = re.sub(r"\b(s)\.(p)\.(a)\.", "spa", s)                      # S.p.A., S.r.l., S.A., N.V. ...
    s = re.sub(r"\b([a-z])\.(?=[a-z]\.)", r"\1", s)
    s = re.sub(r"\b([a-z])\.", r"\1", s)
    s = re.sub(r"sp\.?\s*z\s*o\.?\s*o\.?", "spzoo", s)
    return " ".join(w for w in re.split(r"[^a-z0-9]+", s) if w and w not in LEGAL)


def variants(name: str | None, others=()) -> dict[str, bool]:
    """The forms of a company's names that may be compared, each marked strong (the full main name) or not (the part
    before a dash or bracket, another recorded name, an alias)."""
    out: dict[str, bool] = {}
    for i, n in enumerate([name, *(others or [])]):
        if not n:
            continue
        for j, part in enumerate((n, SPLIT.split(n, 1)[0])):
            f = _fold(part)
            if len(f) >= 3:
                out[f] = out.get(f, False) or (i == 0 and j == 0)
    return out


def same_name(a: dict, b: dict, ca=None, cb=None) -> bool:
    """Main name against main name: the countries must not disagree. Through another name, alias or shortened form:
    at least two words, or one word with the same country known on both sides ("International" alone is a name many
    companies carry)."""
    if ca and cb and ca.upper() != cb.upper():
        return False
    for f in a.keys() & b.keys():
        if (a[f] and b[f]) or len(f.split()) >= 2 or (ca and cb):
            return True
    return False


def wd_country(item) -> str | None:
    """Two-letter code of the item's country (P17), when our country table knows it."""
    for c in item.get("claims", {}).get("P17", []):
        if c.get("v") and not c.get("end"):
            iso = geo.by_qid(c["v"])
            if iso:
                return iso
    return None


def _countries_agree(a, b) -> bool:
    return not a or not b or a.upper() == b.upper()


def _wd_lei(item):
    return next((str(c["v"]).upper() for c in item.get("claims", {}).get("P1278", []) if c.get("v")), None)


def _wd_variants(item):
    return variants(item.get("name"), item.get("aliases") or [])


def _gleif_variants(rec):
    return variants(rec.get("legal_name") or rec.get("name"), [rec.get("name"), *(rec.get("other_names") or [])])


MAX_GROUP = 4              # LEIs taken as one group's tops
MAX_PAGES = 3              # 200 children a page


async def gleif_group(leis) -> list[dict]:
    """Every company GLEIF puts under these LEIs. A top company's ultimate children include its direct ones, so one list
    per LEI: the ultimate children, or the direct ones when it heads nothing itself (a company in the middle of a chain)."""
    out, seen = [], set()
    for lei in list(dict.fromkeys(leis))[:MAX_GROUP]:
        first = await S.gleif_children(lei, 1, 200, "ultimate")
        kind = "ultimate"
        if not first["total"]:
            first, kind = await S.gleif_children(lei, 1, 200, "direct"), "direct"
        pages = [first] + [await S.gleif_children(lei, n, 200, kind) for n in range(2, min(MAX_PAGES, -(-first["total"] // 200)) + 1)]
        for pg in pages:
            for k in pg["items"]:
                if k["lei"] not in seen:
                    seen.add(k["lei"]); out.append(k)
    return out


async def wd_children(q) -> list[str]:
    """Items Wikidata puts under q: its subsidiaries (P355), what it owns (P1830), and items naming it as parent or owner."""
    it = (await S.wd_entities([q])).get(q) or {}
    ids = [c["v"] for prop in ("P355", "P1830") for c in it.get("claims", {}).get(prop, []) if c.get("v") and not c.get("end")]
    for prop in ("P749", "P127"):
        ids += (await S.wd_reverse(prop, q)).get("ids", [])
    return list(dict.fromkeys(ids))


def _parents(item) -> list[str]:
    return [x["v"] for prop in ("P749", "P127") for x in item.get("claims", {}).get(prop, []) if x.get("v") and not x.get("end")]


async def group_leis(q) -> list[str]:
    """The LEIs heading the group Wikidata calls q: q's own LEI, or, when q has none (Wikidata often keeps a 'group'
    item beside the company that carries the LEI, e.g. Lufthansa Group beside Lufthansa), the LEIs of q's own
    subsidiaries."""
    it = (await S.wd_entities([q])).get(q) or {}
    own = _wd_lei(it)
    if own:
        return [own]
    kids = await S.wd_entities((await wd_children(q))[:50])
    return [l for l in (_wd_lei(k) for k in kids.values()) if l][:MAX_GROUP]


def _fits_gleif(variants_, country, recs):
    return [k for k in recs if same_name(variants_, _gleif_variants(k), country, k.get("country"))]


async def wikidata_for_gleif(rec: dict) -> tuple[str | None, str | None]:
    """A GLEIF record with no Wikidata item by LEI: look among the Wikidata items under its GLEIF parent's Wikidata
    item, and under that item's own Wikidata parents (the group item). Returns (qid, how) or (None, None)."""
    lei = rec["lei"]
    par = await S.gleif_parents(lei)
    mine = _gleif_variants(rec)
    tops = [p for p in (par.get("direct"), par.get("ultimate")) if p]
    for p in tops:
        pq = await S.wd_by_lei(p["lei"])
        if not pq:
            continue
        pit = (await S.wd_entities([pq])).get(pq) or {}
        pool = await wd_children(pq)
        for gp in _parents(pit)[:3]:                       # one step up in Wikidata: the group item
            pool += await wd_children(gp)
        items = await S.wd_entities(list(dict.fromkeys(pool)))
        fits = [q for q, it in items.items()
                if same_name(mine, _wd_variants(it), rec.get("country"), wd_country(it)) and _wd_lei(it) in (None, lei)]
        if len(fits) == 1:
            return fits[0], f"both registers place it in the same group, under {p['name']}"
        if len(fits) > 1:
            return None, None                              # two candidates: no join
    return None, None


async def gleif_for_wikidata(item: dict) -> tuple[dict | None, str | None]:
    """A Wikidata item with no LEI: look among the GLEIF companies of the group its Wikidata parent or owner heads.
    Returns (GLEIF record, how) or (None, None)."""
    if _wd_lei(item):
        return None, None
    mine, country = _wd_variants(item), wd_country(item)
    parents = await S.wd_entities(_parents(item)[:3])
    for q, pit in parents.items():
        leis = await group_leis(q)
        if not leis:
            continue
        fits = _fits_gleif(mine, country, await gleif_group(leis))
        if len(fits) == 1:
            return fits[0], f"both registers place it in the same group, under {pit.get('name') or q}"
        if len(fits) > 1:
            return None, None
    return None, None


async def resolve_holdings(bucket: dict, leis: list[str], via: str) -> list[dict]:
    """Holdings Wikidata lists without an LEI: when exactly one company of this entity's GLEIF group has the same name
    (and no other country), the holding takes that LEI, so the graph shows one box. Merges into a GLEIF edge that is
    already there."""
    wd = [e for e in bucket.values() if e["ref"].startswith("wd:") and e["source"] == "Wikidata"]
    if not wd or not leis:
        return []
    group = await gleif_group(leis)
    taken, joins = {}, []
    for w in wd:
        fits = _fits_gleif(variants(w["name"], w.get("aliases") or []), w.get("country"), group)
        if len(fits) == 1:
            taken.setdefault(fits[0]["lei"], []).append((w, fits[0]))
    for lei, pairs in taken.items():
        if len(pairs) != 1:
            continue                                        # two Wikidata items fit one GLEIF company: leave both
        w, rec = pairs[0]
        bucket.pop(w["ref"], None)
        ref = f"lei:{lei}"
        if ref in bucket:
            g = bucket[ref]
            g["also"] = g.get("also", []) + [{"label": w["label"], "source": "Wikidata", **({"share": w["share"]} if w.get("share") else {})}]
            g["alias"] = sorted(set(g.get("alias", [])) | {w["ref"]})
        else:
            bucket[ref] = {**w, "ref": ref, "alias": [w["ref"]], "joined": f"Wikidata item joined to GLEIF {lei} by name: {via}"}
        joins.append({"refs": [ref, w["ref"]], "name": w["name"]})
    return joins


def merge_edges(bucket: dict) -> list[dict]:
    """Owners or holdings of one entity: a Wikidata edge without an LEI and a GLEIF edge for the same company (same
    name, countries not disagreeing, one to one) become one edge. Both registers place it under this entity, which is
    rule 2. Returns the joins made, for the page."""
    gleif = [e for e in bucket.values() if e["ref"].startswith("lei:") and e["source"] == "GLEIF"]
    wd = [e for e in bucket.values() if e["ref"].startswith("wd:") and e["source"] == "Wikidata"]
    gv = {e["ref"]: variants(e["name"], e.get("other_names") or []) for e in gleif}
    pairs = {}
    for w in wd:
        wv = variants(w["name"], w.get("aliases") or [])
        hits = [g for g in gleif if same_name(gv[g["ref"]], wv, g.get("country"), w.get("country"))]
        if len(hits) == 1:
            pairs.setdefault(hits[0]["ref"], []).append(w)
    joins = []
    for gref, ws in pairs.items():
        if len(ws) != 1:
            continue                                    # two Wikidata items fit one GLEIF record: leave both
        w, g = ws[0], bucket[gref]
        g["also"] = g.get("also", []) + [{"label": w["label"], "source": "Wikidata", **({"share": w["share"]} if w.get("share") else {})}]
        g["alias"] = sorted(set(g.get("alias", [])) | {w["ref"]})
        if w.get("desc") and not g.get("desc"):
            g["desc"] = w["desc"]
        bucket.pop(w["ref"], None)
        joins.append({"refs": [gref, w["ref"]], "name": g["name"]})
    return joins


async def revive_dissolved(gone: list[dict], leis) -> list[dict]:
    """Holdings Wikidata gives as dissolved whose namesake in this entity's GLEIF group is an ACTIVE company: GLEIF's word
    wins (the airline Germanwings stopped flying; Germanwings GmbH is still an active company in the Lufthansa group)."""
    if not gone or not leis:
        return []
    group = await gleif_group(leis)
    out = []
    for w in gone:
        fits = _fits_gleif(variants(w["name"], w.get("aliases") or []), w.get("country"), group)
        if len(fits) == 1 and (fits[0].get("status") or "").upper() == "ACTIVE":
            out.append({**w, "ref": f"lei:{fits[0]['lei']}", "alias": [w["ref"]], "joined": "Wikidata gives it as dissolved; GLEIF lists the company as active"})
    return out
