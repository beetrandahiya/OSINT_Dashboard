"""The lookup page's API. It handles personal identifiers, so by default it answers only to this computer
itself (127.0.0.1), even when the map is opened up to other devices. Set WW_LOOKUP_REMOTE=1 to change that."""
import asyncio
import os
import re
import time

from starlette.responses import JSONResponse
from starlette.routing import Route

from . import emails, enrich, store, tools, usernames

job = {"running": None, "step": "", "done": 0, "total": 0, "problems": [], "finished": None}


def _local(request) -> bool:
    return os.environ.get("WW_LOOKUP_REMOTE") == "1" or (request.client and request.client.host in ("127.0.0.1", "::1"))


def guarded(fn):
    async def wrapped(request):
        if not _local(request):
            return JSONResponse({"error": "The lookup tool only answers on the computer it runs on."}, status_code=403)
        return await fn(request)
    return wrapped


# Every check a scan can run: id -> (kind of identifier it works on, name, what is sent where, note)
CHECKS = {
    "wmn":       ("username", "Built-in checker (WhatsMyName list)", "the username to the websites that passed the test on this computer", ""),
    "maigret":   ("username", "Maigret", tools.TOOLS["maigret"]["sends"], tools.TOOLS["maigret"]["first"]),
    "sherlock":  ("username", "Sherlock", tools.TOOLS["sherlock"]["sends"], tools.TOOLS["sherlock"]["first"]),
    "services":  ("email", "Breach and profile services", "the address to XposedOrNot, Hudson Rock, the OpenPGP key server and GitHub; Gravatar gets only a scrambled form", ""),
    "holehe":    ("email", "Holehe", tools.TOOLS["holehe"]["sends"], tools.TOOLS["holehe"]["first"]),
    "records":   ("domain", "Registry and certificate records", "the domain name to rdap.org and crt.sh", ""),
    "harvester": ("domain", "theHarvester", tools.TOOLS["theharvester"]["sends"], tools.TOOLS["theharvester"]["first"]),
    "github":    ("github", "GitHub account", "the account name to GitHub's public API", ""),
    "phone":     ("phone", "Number plan", "nothing: the number is analysed on this computer", ""),
    "name":      ("name", "Web search", "the exact name to DuckDuckGo", ""),
}
OPTIONS = {"read_pages": "Open every page found, read what it shows, mark dead links, and look up when it was first archived (on by default)",
           "maigret_deep": "Maigret: all 3,000 sites instead of the 500 best known (takes 10 to 20 minutes)",
           "holehe_reset": "Holehe: also use password-reset forms (finds more, but can send reset emails to your inbox)"}


def _plan():
    ids, test = store.identifiers(), usernames.last_self_test()
    kinds = {i["kind"] for i in ids}
    return {"checks": [{"id": k, "for": v[0], "name": v[1], "sends": v[2], "note": v[3], "count": sum(1 for i in ids if i["kind"] == v[0])}
                       for k, v in CHECKS.items() if v[0] in kinds],
            "options": OPTIONS, "trusted_sites": test and test["trusted"], "needs_test": not test}


@guarded
async def state(request):
    test = usernames.last_self_test()
    return JSONResponse({"now": time.time(), "identifiers": store.identifiers(), "findings": store.findings(), "kinds": store.KINDS,
                         "selftest": test and {k: test[k] for k in ("tested", "total", "trusted", "false_alarm", "blind")},
                         "job": job, "last_scan": store.last_scan(), "plan": _plan()}, headers={"Cache-Control": "no-store"})


CHECK = {"username": r"[A-Za-z0-9._-]{2,40}", "email": r"[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}", "name": r".{3,80}", "phone": r"\+?[0-9 ()/-]{6,24}",
         "domain": r"([a-z0-9-]+\.)+[a-z]{2,}", "github": r"[A-Za-z0-9-]{1,39}"}


@guarded
async def add(request):
    d = await request.json()
    kind, value = d.get("kind"), (d.get("value") or "").strip()
    if kind in ("email", "domain"):
        value = value.lower()
    if kind not in CHECK or not re.fullmatch(CHECK[kind], value):
        return JSONResponse({"error": f"That does not look like a valid {store.KINDS.get(kind, 'entry').lower()}."}, status_code=400)
    store.add_identifier(kind, value)
    return JSONResponse({"ok": True})


@guarded
async def remove(request):
    store.remove_identifier(int(request.path_params["id"]))
    return JSONResponse({"ok": True})


@guarded
async def mark(request):
    d = await request.json()
    store.mark(int(d["id"]), bool(d["not_me"]))
    return JSONResponse({"ok": True})


@guarded
async def wipe(request):
    if job["running"]:
        return JSONResponse({"error": "A scan is running."}, status_code=409)
    store.wipe()
    return JSONResponse({"ok": True})


def _begin(name, total):
    job.update(running=name, step="", done=0, total=total, problems=[], finished=None)


async def _selftest():
    try:
        job["step"] = "Testing every site with a known account and a made-up name"
        await usernames.self_test()
    except Exception as e:
        job["problems"].append(f"Test failed: {type(e).__name__}: {e}")
    job.update(running=None, finished=time.time())


async def _scan(want: set):
    scan_id, now, summary = store.scan_started(), time.time(), {"findings": 0, "checks": []}
    ids = store.identifiers()

    async def step(check, ident, label, tool_names, work):
        """Run one check for one identifier; whatever happens, say so."""
        if check not in want:
            return
        job["step"] = f"{label}: {ident['value']}"
        try:
            res = await work()
            found, problems = res if isinstance(res, tuple) else (res, [])
            ran = [t for t in tool_names if not any(p.startswith(t + ":") for p in problems)]
            store.save_findings(ident["id"], ran, found, now)
            job["problems"] += problems
            summary["findings"] += len(found)
        except Exception as e:
            job["problems"].append(f"{label} for {ident['value']}: {e if isinstance(e, (tools.ToolProblem, RuntimeError)) else type(e).__name__ + ': ' + str(e)[:120]}")
        job["done"] += 1

    try:
        todo = [(c, i) for i in ids for c, v in CHECKS.items() if v[0] == i["kind"] and c in want]
        job["total"] = len(todo)
        for i in ids:
            v, k = i["value"], i["kind"]
            if k == "username":
                async def wmn(v=v):
                    if not usernames.last_self_test():
                        raise RuntimeError("skipped, the checker has not been tested on this computer yet")
                    res = await usernames.search([v])
                    unclear = sum(1 for r in res["results"] if r["state"] == "unclear")
                    hits = [{"tool": "Built-in checker", "kind": "account", "key": r["site"], "title": f"{r['site']} profile", "url": r["url"],
                             "detail": {"topics": r["category"], "what": "A public profile page exists under this username. It may belong to someone else with the same name."}}
                            for r in res["results"] if r["state"] == "found"]
                    return hits, ([f"Built-in checker note: {unclear} site answers were unclear and are not counted as hits."] if unclear else [])
                await step("wmn", i, "Built-in checker", ["Built-in checker"], wmn)
                await step("maigret", i, "Maigret", ["Maigret"], lambda v=v: tools.maigret(v, "maigret_deep" in want))
                await step("sherlock", i, "Sherlock", ["Sherlock"], lambda v=v: tools.sherlock(v))
            elif k == "email":
                await step("services", i, "Breach and profile services", [n for n, _ in emails.CHECKS], lambda v=v: emails.search(v))
                await step("holehe", i, "Holehe", ["Holehe"], lambda v=v: tools.holehe(v, "holehe_reset" in want))
            elif k == "domain":
                await step("records", i, "Registry and certificate records", ["Domain registry (RDAP)", "Certificate logs (crt.sh)"], lambda v=v: tools.domain_records(v))
                await step("harvester", i, "theHarvester", ["theHarvester"], lambda v=v: tools.theharvester(v))
            elif k == "github":
                await step("github", i, "GitHub account", ["GitHub"], lambda v=v: tools.github_account(v))
            elif k == "phone":
                await step("phone", i, "Number plan", ["Number plan (offline)"], lambda v=v: asyncio.to_thread(tools.phone, v))
            elif k == "name":
                await step("name", i, "Web search", ["Web search (DuckDuckGo)"], lambda v=v: tools.name_mentions(v))
        if "read_pages" in want:
            todo = store.pages_to_read()
            if todo:
                job.update(step=f"Reading {len(todo)} pages found", done=0, total=len(todo))
                job.__setitem__("step", f"Reading {len(todo)} pages found, then asking the Internet Archive about the live ones")
                res, probs = await enrich.enrich(todo, on_done=lambda: job.__setitem__("done", job["done"] + 1))
                store.save_pages(res)
                job["problems"] += probs
                dead = sum(1 for v in res.values() if v["page"].get("alive") is False)
                summary["pages_read"], summary["pages_dead"] = len(res), dead
    except Exception as e:
        job["problems"].append(f"Scan stopped: {type(e).__name__}: {e}")
    summary["problems"] = list(job["problems"])
    summary["checks"] = sorted(want & set(CHECKS))
    store.scan_finished(scan_id, summary)
    job.update(running=None, finished=time.time())


@guarded
async def start(request):
    which = request.path_params["what"]
    if job["running"]:
        return JSONResponse({"error": "Something is already running."}, status_code=409)
    if which == "selftest":
        _begin("selftest", 0)
        asyncio.create_task(_selftest())
    elif which == "read":
        _begin("scan", 0)
        asyncio.create_task(_scan({"read_pages"}))
    elif which == "scan":
        try:
            want = set((await request.json()).get("run") or [])
        except ValueError:
            want = set()
        want &= set(CHECKS) | set(OPTIONS)
        if not want & (set(CHECKS) | {"read_pages"}):
            return JSONResponse({"error": "Nothing was chosen to run."}, status_code=400)
        _begin("scan", 0)
        asyncio.create_task(_scan(want))
    else:
        return JSONResponse({"error": "unknown"}, status_code=404)
    return JSONResponse({"ok": True})


routes = [
    Route("/api/lookup/state", state),
    Route("/api/lookup/identifiers", add, methods=["POST"]),
    Route("/api/lookup/identifiers/{id:int}", remove, methods=["DELETE"]),
    Route("/api/lookup/mark", mark, methods=["POST"]),
    Route("/api/lookup/wipe", wipe, methods=["POST"]),
    Route("/api/lookup/run/{what}", start, methods=["POST"]),
]


# ---- public figures (profiles are not personal data about the owner; same page, own routes) ----
from . import people as _people

_people_job = {"running": False}


async def people_search(request):
    q = (request.query_params.get("q") or "").strip()
    if len(q) < 2:
        return JSONResponse({"results": []})
    key = "search:" + q.lower()
    hit = store.cache_get(key, 86400)
    if hit:
        return JSONResponse({"results": hit["body"]})
    try:
        res = await _people.search(q)
        store.cache_put(key, res)
        return JSONResponse({"results": res})
    except Exception as e:
        busy = getattr(getattr(e, "response", None), "status_code", None) == 429
        return JSONResponse({"error": "Wikidata is limiting requests from this network right now; try again in a few minutes" if busy
                             else f"Wikidata search failed ({type(e).__name__})"}, status_code=502)


async def people_profile(request):
    qid = request.path_params["qid"]
    if not re.fullmatch(r"Q[0-9]{1,12}", qid):
        return JSONResponse({"error": "not a Wikidata id"}, status_code=400)
    fresh = request.query_params.get("fresh") == "1"
    hit = None if fresh else store.cache_get("profile4:" + qid, 86400)
    if not hit:
        try:
            body = await _people.profile(qid)
        except Exception as e:
            return JSONResponse({"error": f"Could not build the profile ({type(e).__name__}: {str(e)[:120]})"}, status_code=502)
        store.cache_put("profile4:" + qid, body)
        hit = {"fetched": body["built"], "body": body}
    return JSONResponse({**hit["body"], "fetched": hit["fetched"], "now": time.time()}, headers={"Cache-Control": "no-store"})


async def people_today(request):
    """Where the news placed each head of state or government in the last six hours (see news.leaders_today)."""
    from .. import news as news_window
    hit = store.cache_get("leaders", 30 * 86400)
    if not hit:
        return JSONResponse({"today": [], "note": "the list of leaders has not been loaded yet", "now": time.time()})
    news_window.set_watch(l["name"] for l in hit["body"])
    body = await asyncio.to_thread(news_window.leaders_today, hit["body"])
    return JSONResponse({"today": body, "window_h": news_window.WINDOW // 3600, "newest": news_window.english.newest(), "now": time.time()},
                        headers={"Cache-Control": "no-store"})


async def people_leaders(request):
    hit, note = store.cache_get("leaders", 12 * 3600), None
    if not hit:
        try:
            body = await _people.leaders()
            if not body:
                raise RuntimeError("empty answer")
            store.cache_put("leaders", body)
            hit = {"fetched": time.time(), "body": body}
        except Exception as e:
            hit = store.cache_get("leaders", 30 * 86400)          # an older list beats an empty map
            if not hit:
                return JSONResponse({"error": f"Wikidata did not answer ({type(e).__name__}); trying again shortly"}, status_code=502)
            note = f"Wikidata did not answer ({type(e).__name__}); showing the list from {time.strftime('%d %b %H:%M', time.gmtime(hit['fetched']))} UTC"
    return JSONResponse({"leaders": hit["body"], "fetched": hit["fetched"], "note": note, "now": time.time()}, headers={"Cache-Control": "no-store"})


routes += [
    Route("/api/people/search", people_search),
    Route("/api/people/leaders", people_leaders),
    Route("/api/people/today", people_today),
    Route("/api/people/profile/{qid}", people_profile),
]
