"""The Investigate page's API (/lookup). It handles personal identifiers, so by default it answers only to this
computer itself (127.0.0.1), even when the map is opened up to other devices. Set WW_LOOKUP_REMOTE=1 to change that.

Every route goes through one guard (refuse / guarded). Every case needs its consent record before anything is
sent anywhere: a scan of a case without one is refused. See pivot.py for the hard boundaries of this tool."""
import asyncio
import base64
import binascii
import ipaddress
import json
import os
import re
import time
from urllib.parse import urlsplit

from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from .. import config
from . import emails, enrich, export, images, pivot, sources, store, tools, usernames

job = {"running": None, "subject": None, "step": "", "done": 0, "total": 0, "problems": [], "finished": None}
MAX_BODY = 8_000_000            # a 5 MB picture as base64 plus the rest


def _local(request) -> bool:
    # request.client is the socket peer, or the address uvicorn took from X-Forwarded-For when the peer is a local
    # proxy (uvicorn's own rule). We never read X-Forwarded-For ourselves.
    return os.environ.get("WW_LOOKUP_REMOTE") == "1" or (request.client and request.client.host in ("127.0.0.1", "::1"))


LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def _hostname(netloc: str) -> str:
    """'[::1]:8710' -> '::1', 'Localhost:8710' -> 'localhost'."""
    netloc = netloc.strip().lower()
    if netloc.startswith("["):
        return netloc[1:netloc.find("]")] if "]" in netloc else ""
    return netloc.rsplit(":", 1)[0] if netloc.count(":") == 1 else netloc


def _host_ok(name: str) -> bool:
    """Which Host headers the lookup API answers. Checking it stops DNS rebinding: a hostile page whose own name
    has been pointed at 127.0.0.1 sends its own name as Host. Remote use (WW_LOOKUP_REMOTE=1, e.g. over Tailscale)
    adds IP addresses, single-word machine names (Tailscale's short names), *.ts.net and WW_ALLOWED_HOSTS:
    names a hostile site cannot hand to the browser as its own."""
    if name in LOOPBACK:
        return True
    extra = {h.strip().lower() for h in os.environ.get("WW_ALLOWED_HOSTS", "").split(",") if h.strip()}
    if name in extra or (name and name == os.environ.get("WW_HOST", "").lower() and name not in ("0.0.0.0", "::")):
        return True
    if os.environ.get("WW_LOOKUP_REMOTE") != "1":
        return False
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return bool(re.fullmatch(r"[a-z0-9-]{1,63}", name)) or name.endswith(".ts.net")


def refuse(request, write: bool):
    """None when the request may go on, else the refusal. One rule for every lookup route:
    - Host must be this computer's own name (see _host_ok);
    - Origin (or, without it, Referer) must be absent or this same page's origin, so other websites can neither
      drive nor read the API;
    - a request that changes something must be JSON and carry the X-WW header our page sends. A cross-site form
      or no-cors fetch cannot add either without a CORS preflight, which this server never grants."""
    host = request.headers.get("host", "")
    if not _local(request) or not _host_ok(_hostname(host)):
        return JSONResponse({"error": "The lookup tool only answers on the computer it runs on."}, status_code=403)
    src = request.headers.get("origin") or request.headers.get("referer")
    if src is not None and (src == "null" or urlsplit(src).netloc.lower() != host.lower()):
        return JSONResponse({"error": "The lookup tool only answers its own page."}, status_code=403)
    if write:
        ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if request.headers.get("x-ww") != "1" or (request.method == "POST" and ctype != "application/json"):
            return JSONResponse({"error": "The lookup tool only answers its own page."}, status_code=403)
    return None


def guarded(fn):
    async def wrapped(request):
        return refuse(request, request.method not in ("GET", "HEAD")) or await fn(request)
    return wrapped


def _err(text, code=400):
    return JSONResponse({"error": text}, status_code=code)


async def _body(request) -> dict:
    """The JSON body, refused when it is larger than MAX_BODY or not an object."""
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise ValueError("The request is too large.")
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise ValueError("The request is too large.")
    d = json.loads(raw or b"{}")
    if not isinstance(d, dict):
        raise ValueError("Expected a JSON object.")
    return d


def _sid(v):
    try:
        sid = int(v)
    except (TypeError, ValueError):
        return None
    return sid if store.subject(sid) else None


# Every check a scan can run: id -> (kinds of identifier it works on, name, what is sent where, note)
CHECKS = {
    "wmn":       (("username",), "Built-in checker (WhatsMyName list)", "the username to the websites that passed the test on this computer", ""),
    "apis":      (("username",), "Developer and social sites", "the username to the public APIs of Bluesky, Keybase, GitLab, Codeberg, npm and Docker Hub", ""),
    "maigret":   (("username",), "Maigret", tools.TOOLS["maigret"]["sends"], tools.TOOLS["maigret"]["first"]),
    "sherlock":  (("username",), "Sherlock", tools.TOOLS["sherlock"]["sends"], tools.TOOLS["sherlock"]["first"]),
    "services":  (("email",), "Breach and profile services", "the address to XposedOrNot, Hudson Rock, the OpenPGP key server and GitHub; Gravatar gets only a scrambled form", ""),
    "holehe":    (("email",), "Holehe", tools.TOOLS["holehe"]["sends"], tools.TOOLS["holehe"]["first"]),
    "records":   (("domain",), "Registry and certificate records", "the domain name to rdap.org and crt.sh", ""),
    "harvester": (("domain",), "theHarvester", tools.TOOLS["theharvester"]["sends"], tools.TOOLS["theharvester"]["first"]),
    "github":    (("github",), "GitHub account", "the account name to GitHub's public API", ""),
    "proofs":    (("github", "domain"), "Keybase proofs", "the GitHub account or domain to Keybase, which lists accounts that signed a proof for it", ""),
    "phone":     (("phone",), "Number plan", "nothing: the number is analysed on this computer", ""),
    "name":      (("name",), "Web search", "the exact name to DuckDuckGo", ""),
    "scholar":   (("name",), "Research records", "the name to ORCID and OpenAlex (results are only weak leads: namesakes are common)", ""),
    "brave":     (("username", "email", "name"), "Brave web search", "each username, address and name, in quotes, to Brave Search (with your key)", ""),
}
OPTIONS = {"read_pages": "Open every page found, read what it shows, mark dead links, and look up when it was first archived (on by default)",
           "follow_strong": "Follow strong leads automatically: identifiers that found pages tie to the subject for a stated reason (signed proofs, links both ways, "
                            "verified addresses, the same picture file), at most 2 steps from what you entered (on by default)",
           "history": "Ask the Internet Archive about each confirmed account: its oldest and newest archived copy and how its bio read back then (on by default)",
           "maigret_deep": "Maigret: all 3,000 sites instead of the 500 best known (takes 10 to 20 minutes)",
           "holehe_reset": "Holehe: also use password-reset forms (finds more, but can send reset emails to the address's inbox; off by default)"}
FOLLOW_CAP = 8


def _plan(sid):
    ids, test = store.identifiers(sid), usernames.last_self_test()
    kinds = {i["kind"] for i in ids}
    out = []
    for k, v in CHECKS.items():
        if not set(v[0]) & kinds:
            continue
        c = {"id": k, "for": v[0], "name": v[1], "sends": v[2], "note": v[3], "count": sum(1 for i in ids if i["kind"] in v[0])}
        if k == "brave" and not config.brave_key():
            c["needs"] = "a Brave Search key in data/brave-key.txt"
        out.append(c)
    return {"checks": out, "options": OPTIONS, "trusted_sites": test and test["trusted"], "needs_test": not test,
            "unscanned": sum(1 for i in ids if not i["scanned"] and i["kind"] != "picture")}


@guarded
async def state(request):
    test = usernames.last_self_test()
    subs = store.subjects()
    sid = _sid(request.query_params.get("subject"))
    if sid is None and subs:
        sid = subs[0]["id"]
    body = {"now": time.time(), "subjects": subs, "kinds": store.KINDS, "how": store.HOW, "job": job,
            "selftest": test and {k: test[k] for k in ("tested", "total", "trusted", "false_alarm", "blind")},
            "keys": {"brave": bool(config.brave_key()), "github": bool(config.github_token())}, "subject": None}
    if sid is not None:
        an = await asyncio.to_thread(pivot.analyse, sid)
        F = store.findings(sid)
        for f in F:
            f["site"] = pivot.site_of(f)
        body.update(subject=store.subject(sid), identifiers=store.identifiers(sid), findings=F, evidence=an["evidence"],
                    anchors=an["anchors"], leads=store.leads(sid), timeline=pivot.timeline(sid), fingerprints=store.fingerprints(sid),
                    last_scan=store.last_scan(sid), checks_run=store.checks_run(sid), plan=_plan(sid))
    return JSONResponse(body, headers={"Cache-Control": "no-store"})


# ---- cases ----

@guarded
async def subject_new(request):
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    label, me = str(d.get("label") or "").strip(), bool(d.get("self"))
    by, at, how, scope, note = (str(d.get(k) or "").strip() for k in ("consent_by", "consent_at", "consent_how", "consent_scope", "note"))
    if not 1 <= len(label) <= 80:
        return _err("Give the case a name (up to 80 characters).")
    if me:
        by, how, at = "the owner", "self", at or time.strftime("%Y-%m-%d")
        scope = scope or "my own public footprint"
    else:
        if how not in ("written", "verbal"):
            return _err("Say how consent was given: written or verbal.")
        if not 2 <= len(by) <= 120:
            return _err("Say who gave consent.")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", at) or not "2000-01-01" <= at <= time.strftime("%Y-%m-%d"):
            return _err("Give the date consent was given (not in the future).")
        if not 3 <= len(scope) <= 400:
            return _err("Describe what the person agreed to be looked up (the scope).")
    try:
        sid = store.add_subject(label, me, by, at, how, scope[:400], note[:600] or None)
    except ValueError as e:
        return _err(str(e), 409)
    return JSONResponse({"ok": True, "id": sid})


@guarded
async def subject_edit(request):
    sid = _sid(request.path_params["sid"])
    if sid is None:
        return _err("No such case.", 404)
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    label = d.get("label")
    if label is not None and not 1 <= len(str(label).strip()) <= 80:
        return _err("Give the case a name (up to 80 characters).")
    store.update_subject(sid, str(label).strip() if label is not None else None, str(d["note"])[:600] if "note" in d else None)
    return JSONResponse({"ok": True})


@guarded
async def subject_delete(request):
    sid = _sid(request.path_params["sid"])
    if sid is None:
        return _err("No such case.", 404)
    if job["running"]:
        return _err("Something is running; delete the case when it has finished.", 409)
    await asyncio.to_thread(store.delete_subject, sid)
    return JSONResponse({"ok": True})


# ---- identifiers ----

CHECK = {"username": r"[A-Za-z0-9._-]{2,40}", "email": r"[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}", "name": r".{3,80}", "phone": r"\+?[0-9 ()/-]{6,24}",
         "domain": r"([a-z0-9-]+\.)+[a-z]{2,}", "github": r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}"}   # GitHub: no leading, trailing or double hyphen


@guarded
async def add(request):
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    sid = _sid(d.get("subject"))
    if sid is None:
        return _err("Choose a case first.", 404)
    kind = d.get("kind")
    if kind == "picture":
        try:
            raw = base64.b64decode(str(d.get("data") or ""), validate=True)
            info = images.save_upload(raw)
        except (ValueError, binascii.Error) as e:
            return _err(str(e) if isinstance(e, ValueError) and not isinstance(e, binascii.Error) else "The picture could not be read.")
        name = re.sub(r"[^\w .()-]", "", str(d.get("name") or ""))[:80] or None
        if not store.add_identifier(sid, "picture", info.pop("file"), detail={**info, "name": name}):
            return _err("That picture is already in this case.", 409)
        return JSONResponse({"ok": True, "location_meta": info["location_meta"]})
    value = str(d.get("value") or "").strip()
    if kind in ("email", "domain"):
        value = value.lower()
    if kind not in CHECK or not re.fullmatch(CHECK[kind], value):
        return _err(f"That does not look like a valid {store.KINDS.get(kind, 'entry').lower()}.")
    if not store.add_identifier(sid, kind, value):
        return _err(f"{value} is already in this case.", 409)
    return JSONResponse({"ok": True})


@guarded
async def remove(request):
    if job["running"]:          # a running scan would keep saving findings for it, with nothing left to show or remove them
        return _err("A scan is running; remove it when the scan has finished.", 409)
    store.remove_identifier(int(request.path_params["id"]))
    return JSONResponse({"ok": True})


@guarded
async def mark(request):
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    sid = _sid(d.get("subject"))
    if sid is None:
        return _err("No such case.", 404)
    ids = [int(x) for x in (d.get("ids") or ([d["id"]] if "id" in d else []))][:500]
    store.mark(sid, ids, not_me=d.get("not_me"), confirmed=d.get("confirmed"))
    await asyncio.to_thread(pivot.update, sid)         # a confirmation can tie new pages and leads to the subject; local work only
    return JSONResponse({"ok": True})


@guarded
async def lead_action(request):
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    sid = _sid(d.get("subject"))
    lead = sid and store.lead(sid, int(request.path_params["id"]))
    if not lead:
        return _err("No such lead.", 404)
    act = d.get("action")
    if act == "approve":
        if lead["state"] not in ("new", "rejected"):
            return _err("This lead was already followed or approved.", 409)
        if lead["kind"] not in CHECK or not re.fullmatch(CHECK[lead["kind"]], lead["value"]):
            return _err("This lead is not a valid identifier.")
        store.add_identifier(sid, lead["kind"], lead["value"], source="pivot", hop=lead["hop"], lead=lead["id"])
        store.set_lead_state(sid, lead["id"], "approved")
    elif act == "reject":
        if lead["state"] in ("followed", "approved"):
            return _err("Remove the identifier it became instead; the lead is then remembered as rejected.", 409)
        store.set_lead_state(sid, lead["id"], "rejected")
    elif act == "undo" and lead["state"] == "rejected":
        store.set_lead_state(sid, lead["id"], "new")
    else:
        return _err("Unknown action.")
    await asyncio.to_thread(pivot.update, sid)         # an undone lead that nothing derives any more disappears
    return JSONResponse({"ok": True})


# ---- pictures: fingerprints from the browser, the found-picture proxy, uploaded seed pictures ----

_allow = {"key": None, "urls": set()}


def _allowed_images(sid):
    key = (sid, store.version())
    if _allow["key"] != key:
        _allow.update(key=key, urls=store.image_urls(sid))
    return _allow["urls"]


@guarded
async def fingerprints(request):
    try:
        d = await _body(request)
    except ValueError as e:
        return _err(str(e))
    sid = _sid(d.get("subject"))
    if sid is None:
        return _err("No such case.", 404)
    ok_urls = _allowed_images(sid) | {"picture:" + i["value"] for i in store.identifiers(sid) if i["kind"] == "picture"}
    items = [{"url": it["url"], "hash": it["hash"], "location_meta": bool(it.get("location_meta"))} for it in (d.get("items") or [])[:400]
             if isinstance(it, dict) and it.get("url") in ok_urls and re.fullmatch(r"[0-9a-f]{16}|", str(it.get("hash")))]
    store.save_fingerprints(sid, items)
    await asyncio.to_thread(pivot.update, sid)
    return JSONResponse({"ok": True, "saved": len(items)})


@guarded
async def image(request):
    """A found profile picture, fetched by this server: the browser can then fingerprint it, and the picture's
    site does not see the browser. Only addresses this case's findings name."""
    sid = _sid(request.query_params.get("s"))
    u = request.query_params.get("u") or ""
    if sid is None or u not in _allowed_images(sid):
        return Response(status_code=404)
    try:
        body, kind, meta = await images.fetch(u)
    except Exception as e:          # every failure is the same for the page: no picture
        return Response(str(e)[:120], status_code=502, media_type="text/plain")
    return Response(body, media_type=kind, headers={"Cache-Control": "private, max-age=86400", "X-Location-Meta": "1" if meta else "0",
                                                    "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; sandbox"})


@guarded
async def picture(request):
    sid = _sid(request.query_params.get("s"))
    name = request.path_params["name"]
    if sid is None or not any(i["kind"] == "picture" and i["value"] == name for i in store.identifiers(sid)):
        return Response(status_code=404)
    got = images.read_upload(name)
    if not got:
        return Response(status_code=404)
    # no-store: an uploaded picture that is removed (or its case deleted) must not live on in the browser's cache
    return Response(got[0], media_type=got[1], headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                                        "Content-Security-Policy": "default-src 'none'; sandbox"})


# ---- export ----

@guarded
async def export_json(request):
    sid = _sid(request.path_params["sid"])
    if sid is None:
        return Response(status_code=404)
    body = await asyncio.to_thread(export.as_json, sid)
    return Response(body, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="case-{sid}.json"', "Cache-Control": "no-store"})


@guarded
async def export_html(request):
    sid = _sid(request.path_params["sid"])
    if sid is None:
        return Response(status_code=404)
    body = await asyncio.to_thread(export.case_file, sid)
    return HTMLResponse(body, headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"})


@guarded
async def wipe(request):
    if job["running"]:
        return _err("A scan is running.", 409)
    await asyncio.to_thread(store.wipe)
    return JSONResponse({"ok": True})


# ---- running checks ----

def _begin(name, sid, total):
    job.update(running=name, subject=sid, step="", done=0, total=total, problems=[], finished=None)


async def _selftest():
    try:
        job["step"] = "Testing every site with a known account and a made-up name"
        await usernames.self_test()
    except Exception as e:
        job["problems"].append(f"Test failed: {type(e).__name__}: {e}")
    job.update(running=None, finished=time.time())


def _wants(i, want):
    return [c for c, v in CHECKS.items() if i["kind"] in v[0] and c in want and not (c == "brave" and not config.brave_key())]


async def _checks(sid, ids, want, summary, now):
    """Run the chosen checks for these identifiers; whatever happens to each, say so."""
    domains = {i["value"] for i in store.identifiers(sid) if i["kind"] == "domain"}

    async def step(check, ident, label, tool_names, work):
        if check not in want:
            return
        if check == "brave" and not config.brave_key():
            return
        if not store.identifier_exists(ident["id"]):
            job["done"] += 1
            return
        job["step"] = f"{label}: {ident['value']}"
        try:
            res = await work()
            found, problems = res if isinstance(res, tuple) else (res, [])
            ran = [t for t in tool_names if not any(p.startswith(t + ":") for p in problems)]
            store.save_findings(ident["id"], ran, found, now)
            job["problems"] += problems
            summary["findings"] += len({(f["tool"], f["key"]) for f in found})   # as stored: a tool listing one page twice counts once
        except Exception as e:
            known = (tools.ToolProblem, RuntimeError, sources.SourceProblem)
            job["problems"].append(f"{label} for {ident['value']}: {e if isinstance(e, known) else type(e).__name__ + ': ' + str(e)[:120]}")
        job["done"] += 1

    job["total"] += sum(len(_wants(i, want)) for i in ids)
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
            await step("apis", i, "Developer and social sites", [n for n, _ in sources.USERNAME_SOURCES], lambda v=v: sources.profiles(v, domains))
            await step("maigret", i, "Maigret", ["Maigret"], lambda v=v: tools.maigret(v, "maigret_deep" in want))
            await step("sherlock", i, "Sherlock", ["Sherlock"], lambda v=v: tools.sherlock(v))
            await step("brave", i, "Brave web search", ["Web search (Brave)"], lambda v=v: sources.brave(f'"{v}"', f"the username “{v}”"))
        elif k == "email":
            await step("services", i, "Breach and profile services", [n for n, _ in emails.CHECKS], lambda v=v: emails.search(v))
            await step("holehe", i, "Holehe", ["Holehe"], lambda v=v: tools.holehe(v, "holehe_reset" in want))
            await step("brave", i, "Brave web search", ["Web search (Brave)"], lambda v=v: sources.brave(f'"{v}"', f"the address {v}"))
        elif k == "domain":
            await step("records", i, "Registry and certificate records", ["Domain registry (RDAP)", "Certificate logs (crt.sh)"], lambda v=v: tools.domain_records(v))
            await step("harvester", i, "theHarvester", ["theHarvester"], lambda v=v: tools.theharvester(v))
            await step("proofs", i, "Keybase proofs", ["Keybase"], lambda v=v: sources.keybase_for("domain", v))
        elif k == "github":
            await step("github", i, "GitHub account", ["GitHub"], lambda v=v: tools.github_account(v))
            await step("proofs", i, "Keybase proofs", ["Keybase"], lambda v=v: sources.keybase_for("github", v))
        elif k == "phone":
            await step("phone", i, "Number plan", ["Number plan (offline)"], lambda v=v: asyncio.to_thread(tools.phone, v))
        elif k == "name":
            await step("name", i, "Web search", ["Web search (DuckDuckGo)"], lambda v=v: tools.name_mentions(v))
            await step("scholar", i, "Research records", ["ORCID", "OpenAlex"], lambda v=v: sources.scholars(v))
            await step("brave", i, "Brave web search", ["Web search (Brave)"], lambda v=v: sources.brave(f'"{v}"', f"the name “{v}”"))
    store.mark_scanned([i["id"] for i in ids if _wants(i, want)], now)        # only where a check really ran


async def _pivot_read(sid, want, summary):
    """Pivot (which also adds the pages anchors link to), read the pages, and pivot again with what they show."""
    job["step"] = "Looking for links between the pages"
    await asyncio.to_thread(pivot.update, sid)
    if "read_pages" in want:
        todo = store.pages_to_read(sid)
        if todo:
            job.update(step=f"Reading {len(todo)} pages found, then asking the Internet Archive about the live ones", done=0, total=len(todo))
            res, probs = await enrich.enrich(todo, on_done=lambda: job.__setitem__("done", job["done"] + 1))
            store.save_pages(sid, res)
            job["problems"] += probs
            summary["pages_read"] = summary.get("pages_read", 0) + len(res)
            summary["pages_dead"] = summary.get("pages_dead", 0) + sum(1 for v in res.values() if v["page"].get("alive") is False)
        await asyncio.to_thread(pivot.update, sid)


async def _history(sid):
    """The Internet Archive's history of each anchored account (one at a time: it asks for gentle use)."""
    an = pivot.analyse(sid)
    F = {f["id"]: f for f in store.findings(sid)}
    todo = [F[i] for i in an["anchors"] if i in F and F[i].get("url") and F[i]["kind"] in ("account", "profile", "website")
            and time.time() - ((F[i].get("history") or {}).get("asked") or 0) > 7 * 86400][:30]
    fails = 0
    for n, f in enumerate(todo):
        job.update(step=f"Archive history of confirmed accounts ({n + 1} of {len(todo)})")
        try:
            store.save_history(sid, f["id"], await sources.archive_history(f["url"]))
            fails = 0
        except Exception:
            fails += 1
            if fails >= 4:
                job["problems"].append(f"The Internet Archive did not answer; archive history was read for {n + 1 - fails} of {len(todo)} confirmed accounts")
                break
        await asyncio.sleep(1)


async def _scan(sid, want: set, only_new=False):
    scan_id, now, summary = store.scan_started(sid), time.time(), {"findings": 0, "checks": [], "followed": []}
    try:
        ids = [i for i in store.identifiers(sid) if not only_new or not i["scanned"]]
        await _checks(sid, ids, want, summary, now)
        await _pivot_read(sid, want, summary)
        if "follow_strong" in want:
            for _ in range(2):                 # leads carry their step count; none beyond 2 steps is followed
                todo = store.strong_to_follow(sid, max_hop=2)
                if not todo:
                    break
                if len(todo) > FOLLOW_CAP:
                    job["problems"].append(f"{len(todo) - FOLLOW_CAP} more strong leads wait in the Leads list ({FOLLOW_CAP} are followed per round)")
                new = []
                for lead in todo[:FOLLOW_CAP]:
                    if lead["kind"] in CHECK and re.fullmatch(CHECK[lead["kind"]], lead["value"]):
                        iid = store.add_identifier(sid, lead["kind"], lead["value"], source="pivot", hop=lead["hop"], lead=lead["id"])
                        if iid:
                            new.append(store.identifier(iid))
                            summary["followed"].append(f"{store.KINDS[lead['kind']]} {lead['value']}")
                    store.set_lead_state(sid, lead["id"], "followed")
                if not new:
                    continue
                job["step"] = f"Following {len(new)} strong leads"
                await _checks(sid, new, want, summary, time.time())
                await _pivot_read(sid, want, summary)
        if "history" in want:
            await _history(sid)
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
        return _err("Something is already running.", 409)
    if which == "selftest":
        _begin("selftest", None, 0)
        asyncio.create_task(_selftest())
        return JSONResponse({"ok": True})
    try:
        d = await _body(request)
    except ValueError:
        d = {}
    sid = _sid(d.get("subject"))
    if sid is None:
        return _err("Choose a case first.", 404)
    if not store.consent_ok(store.subject(sid)):        # the gate: nothing is sent anywhere for a case without its consent record
        return _err("This case has no complete consent record (who agreed, when, how, to what), so nothing can be checked for it.", 403)
    if which == "read":
        if not store.pages_to_read(sid):   # say so, instead of a scan entry that reads "0 findings from 0 checks"
            return JSONResponse({"ok": True, "note": "Every page found was read in the last 7 days; nothing to read again yet."})
        _begin("scan", sid, 0)
        asyncio.create_task(_scan(sid, {"read_pages"}))
    elif which == "scan":
        want = set(d.get("run") or []) & (set(CHECKS) | set(OPTIONS))
        if not want & (set(CHECKS) | {"read_pages"}):
            return _err("Nothing was chosen to run.")
        _begin("scan", sid, 0)
        asyncio.create_task(_scan(sid, want, bool(d.get("only_new"))))
    else:
        return _err("unknown", 404)
    return JSONResponse({"ok": True})


routes = [
    Route("/api/lookup/state", state),
    Route("/api/lookup/subjects", subject_new, methods=["POST"]),
    Route("/api/lookup/subjects/{sid:int}", subject_edit, methods=["POST"]),
    Route("/api/lookup/subjects/{sid:int}", subject_delete, methods=["DELETE"]),
    Route("/api/lookup/subjects/{sid:int}/export.json", export_json),
    Route("/api/lookup/subjects/{sid:int}/case-file", export_html),
    Route("/api/lookup/identifiers", add, methods=["POST"]),
    Route("/api/lookup/identifiers/{id:int}", remove, methods=["DELETE"]),
    Route("/api/lookup/mark", mark, methods=["POST"]),
    Route("/api/lookup/leads/{id:int}", lead_action, methods=["POST"]),
    Route("/api/lookup/fingerprints", fingerprints, methods=["POST"]),
    Route("/api/lookup/img", image),
    Route("/api/lookup/picture/{name}", picture),
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
        except _people.ProfileError as e:
            return JSONResponse({"error": str(e)}, status_code=404)
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
