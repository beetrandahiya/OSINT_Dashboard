"""The lookup page's API. It handles personal identifiers, so by default it answers only to this computer
itself (127.0.0.1), even when the map is opened up to other devices. Set WW_LOOKUP_REMOTE=1 to change that."""
import asyncio
import os
import re
import time

from starlette.responses import JSONResponse
from starlette.routing import Route

from . import emails, store, usernames

job = {"running": None, "step": "", "done": 0, "total": 0, "problems": [], "finished": None}


def _local(request) -> bool:
    return os.environ.get("WW_LOOKUP_REMOTE") == "1" or (request.client and request.client.host in ("127.0.0.1", "::1"))


def guarded(fn):
    async def wrapped(request):
        if not _local(request):
            return JSONResponse({"error": "The lookup tool only answers on the computer it runs on."}, status_code=403)
        return await fn(request)
    return wrapped


def _plan():
    ids, test = store.identifiers(), usernames.last_self_test()
    names = [i for i in ids if i["kind"] == "username"]
    mails = [i for i in ids if i["kind"] == "email"]
    other = [i for i in ids if i["kind"] not in ("username", "email")]
    steps = []
    if names:
        steps.append({"what": f"{len(names)} username{'s' if len(names) > 1 else ''} ({', '.join(i['value'] for i in names)})",
                      "to": f"{test['trusted']} websites, one page request each per username" if test else "nothing yet: the checker must be tested first",
                      "sends": "the username, as part of a profile address"})
    for name, host, sends in emails.SERVICES if mails else []:
        steps.append({"what": f"{len(mails)} email address{'es' if len(mails) > 1 else ''}", "to": f"{name} ({host})", "sends": sends})
    return {"steps": steps, "not_yet": [f"{store.KINDS[i['kind']]} “{i['value']}”" for i in other], "needs_test": bool(names) and not test}


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


async def _scan():
    scan_id, now, summary = store.scan_started(), time.time(), {"usernames": 0, "emails": 0}
    try:
        ids = store.identifiers()
        names = [i for i in ids if i["kind"] == "username"]
        if names and usernames.last_self_test():
            job["step"] = "Checking usernames"
            by_value = {i["value"]: i for i in names}
            job["total"] = len(names) * usernames.last_self_test()["trusted"]
            res = await usernames.search(list(by_value), lambda r: job.__setitem__("done", job["done"] + 1))
            for value, ident in by_value.items():
                hits = [{"tool": "Username sweep", "kind": "account", "key": r["site"], "title": f"{r['site']} profile", "url": r["url"],
                         "detail": {"category": r["category"], "what": "A public profile page exists under this username. It may belong to someone else with the same name."}}
                        for r in res["results"] if r["username"] == value and r["state"] == "found"]
                store.save_findings(ident["id"], ["Username sweep"], hits, now)
                summary["usernames"] += len(hits)
            unclear = sum(1 for r in res["results"] if r["state"] == "unclear")
            if unclear:
                job["problems"].append(f"{unclear} site answers were unclear (blocked, slow or changed) and are not counted as hits.")
        for ident in [i for i in ids if i["kind"] == "email"]:
            job["step"] = f"Checking {ident['value']}"
            found, problems = await emails.search(ident["value"])
            ran = [n for n, _ in emails.CHECKS if not any(p.startswith(n + ":") for p in problems)]
            store.save_findings(ident["id"], ran, found, now)
            job["problems"] += problems
            summary["emails"] += len(found)
    except Exception as e:
        job["problems"].append(f"Scan stopped: {type(e).__name__}: {e}")
    summary["problems"] = list(job["problems"])
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
    elif which == "scan":
        if _plan()["needs_test"]:
            return JSONResponse({"error": "Test the checker first."}, status_code=409)
        _begin("scan", 0)
        asyncio.create_task(_scan())
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
