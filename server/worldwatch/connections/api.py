"""Routes of the Connections page (/connections). Read-only, public registers only."""
import asyncio
import re
import time

from starlette.responses import JSONResponse
from starlette.routing import Route

from .. import config
from . import icij, node, sanctioned, sources as S, store

NODE_TTL = 12 * 3600
_building: dict[str, asyncio.Task] = {}


def _ok(body, status=200):
    return JSONResponse({**body, "now": time.time()}, status_code=status, headers={"Cache-Control": "no-store"})


async def search(request):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 2:
        return _ok({"results": []})
    return _ok(await node.search(q[:120]))


async def get_node(request):
    ref = (request.query_params.get("ref") or "").strip()
    if not re.fullmatch(r"(lei:[0-9A-Za-z]{20}|wd:Q\d+|icij:\d+|os:[\w.\-]+)", ref):
        return _ok({"error": "unknown reference"}, 400)
    key = "node7:" + ref          # bump when the way nodes are built changes
    if not request.query_params.get("fresh"):
        hit = await asyncio.to_thread(store.cache_get, key, NODE_TTL)
        if hit:
            return _ok({**hit, "cached": True})
    # several pages asking for the same entity at once share one build
    task = _building.get(ref)
    if task is None:
        task = asyncio.create_task(node.build(ref))
        _building[ref] = task
        task.add_done_callback(lambda t, r=ref: _building.pop(r, None))
    body = await task
    body["built"] = time.time()
    if not body.get("error") and not body.get("problems"):
        await asyncio.to_thread(store.cache_put, key, body)
    return _ok(body)


async def more_holdings(request):
    """Further pages of GLEIF's subsidiary list (the node carries the first 50)."""
    lei = (request.query_params.get("lei") or "").upper()
    page = max(1, min(200, int(request.query_params.get("page") or 2)))
    if not re.fullmatch(r"[0-9A-Z]{20}", lei):
        return _ok({"error": "bad LEI"}, 400)
    try:
        kids = await S.gleif_children(lei, page)
    except S.SourceDown as e:
        return _ok({"error": f"GLEIF did not answer ({e})"}, 502)
    return _ok({"items": [{"ref": f"lei:{k['lei']}", "name": k["name"], "kind": "company", "country": k.get("country"),
                           "label": "direct subsidiary (consolidated)", "source": "GLEIF"} for k in kids["items"]], "total": kids["total"], "page": page})


async def asset(request):
    """A ship or aircraft from the map -> its registered owner / operator, then the matching records in the registers.
    A registered owner that reads as a private person is not searched on (boundary: private people are never a
    starting point)."""
    ref = request.query_params.get("ref") or ""
    out = {"ref": ref, "owners": [], "facts": [], "problems": []}
    if ref.startswith("ac:") and re.fullmatch(r"ac:[0-9a-fA-F]{6}", ref):
        from .. import web
        about = await web._aircraft_about(ref[3:].lower())
        if not about:
            out["problems"].append("the free aircraft registers (adsbdb, hexdb.io) do not know this aircraft")
            return _ok(out)
        out["title"] = " ".join(x for x in (about.get("reg"), about.get("maker"), about.get("model")) if x)
        out["facts"] = [{"label": k, "value": v, "source": about.get("source")} for k, v in
                        (("Registration", about.get("reg")), ("Maker", about.get("maker")), ("Model", about.get("model")),
                         ("Registered owner", about.get("owner")), ("Owner's country", about.get("country"))) if v]
        owner = (about.get("owner") or "").strip()
        if owner:
            # searched only in registers of organisations (GLEIF, Offshore Leaks' organisation index, sanctioned companies,
            # Wikidata items): a private owner's name finds no record about that person here
            res = await node.search(owner)
            out["owners"].append({"name": owner, "source": about.get("source"), "candidates": res["results"][:12],
                                  "note": "organisations with the same or a similar name; a name alone does not prove they are the same company"})
            out["problems"] += res.get("problems", [])
    elif ref.startswith("imo:") and re.fullmatch(r"imo:\d{7}", ref):
        imo = ref[4:]
        try:
            hit = await S.wd_reverse("P458", imo, 3)
            if hit["ids"]:
                n = await node.build("wd:" + hit["ids"][0])
                out["title"] = n.get("name")
                out["facts"] = n.get("facts", [])
                out["owners"] = [{"name": e["name"], "ref": e["ref"], "label": e["label"], "source": e["source"]} for e in n.get("owners", [])]
                out["node"] = n["ref"]
        except S.SourceDown as e:
            out["problems"].append(f"Wikidata did not answer ({e})")
        out["sanctions"] = await asyncio.to_thread(_ship_sanctions, imo)
        if not out.get("title") and not out["sanctions"]:
            out["problems"].append("no public register here names this ship's owner (ordinary ships' owners are only in paid or login-only registers)")
    else:
        return _ok({"error": "unknown asset"}, 400)
    return _ok(out)


def _ship_sanctions(imo):
    from .. import web
    st = web.collector.states.get("sanctioned")
    rec = ((st.payload or {}).get("vessels") or {}).get("imo", {}).get(imo) if st and st.payload else None
    if not rec:
        return []
    name, risk, lists, url, flag = rec
    return [{"name": name, "risk": risk, "lists": lists, "url": url, "flag": flag}]


async def state(request):
    meta = await asyncio.to_thread(store.meta_get, "icij")
    def count():
        try:
            return store.db().execute("SELECT count(*) FROM sanc").fetchone()[0] if sanctioned.ready() else 0
        except Exception:
            return 0
    return _ok({"icij": {"ready": S.icij_ready(), **(meta or {})}, "sanctions": await asyncio.to_thread(count),
                "opensanctions_key": bool(config.opensanctions_key())})


routes = [
    Route("/api/connections/search", search),
    Route("/api/connections/node", get_node),
    Route("/api/connections/holdings", more_holdings),
    Route("/api/connections/asset", asset),
    Route("/api/connections/state", state),
]
