"""More public sources for a case, each asked through its own open API.

Boundaries (the same for the whole Investigate page): public sources only, no login, nothing past a login,
captcha or bot shield (DBLP and PyPI's user pages answered with bot checks when probed on 2026-11-28, so they
are not used); no face recognition or face search; nothing that infers where a person lives, is or goes;
no breach contents. Results from a full-name search are only ever weak leads: namesakes are certain.

Each function returns findings in the shared shape (tool, kind, key, title, url, detail) and raises on
failure, so the scan lists the failure by name. One request at a time per host.
"""
import asyncio
import re
import time

import httpx

from .. import config

UA = {"User-Agent": config.USER_AGENT}
NOT_THEM = "A public profile exists under this name. It may belong to someone else with the same name."


def _f(tool, kind, key, title, url=None, **detail):
    return {"tool": tool, "kind": kind, "key": key, "title": title, "url": url, "detail": {k: v for k, v in detail.items() if v not in (None, "", [], {})}}


class SourceProblem(Exception):
    pass


def _check(r, name):
    if r.status_code == 429:
        raise SourceProblem(f"{name} is limiting requests from this network; try again later")
    if r.status_code >= 400:
        raise SourceProblem(f"{name} answered {r.status_code}")


# ---- usernames: developer and social platforms with open APIs ----

async def bluesky(c: httpx.AsyncClient, username: str, domains=()) -> list[dict]:
    """The Bluesky account with this handle (username.bsky.social, or the name itself when it is a domain), plus
    accounts whose own-domain handle starts with the name. A handle that is a web domain was proved by that
    domain (DNS or a file on the site), so such an account and the domain belong together."""
    out, seen = [], set()
    actors = [username if "." in username else f"{username}.bsky.social"]
    r = await c.get("https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors", params={"q": username, "limit": 25})
    _check(r, "Bluesky")
    for a in r.json().get("actors") or []:
        h = (a.get("handle") or "").lower()
        if h.endswith(".bsky.social"):
            continue
        if h.split(".")[0] == username.lower() or h == username.lower():
            actors.append(h)
    for actor in dict.fromkeys(actors):
        await asyncio.sleep(0.3)
        r = await c.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile", params={"actor": actor})
        if r.status_code == 400:                       # "Profile not found"
            continue
        _check(r, "Bluesky")
        p = r.json()
        h = p.get("handle") or actor
        if h in seen:
            continue
        seen.add(h)
        own = not h.endswith(".bsky.social")
        out.append(_f("Bluesky", "account", "bluesky:" + h, f"Bluesky @{h}", f"https://bsky.app/profile/{h}", handle=h, name=p.get("displayName"),
                      bio=p.get("description"), image=p.get("avatar"), created_at=(p.get("createdAt") or "")[:10], followers=p.get("followersCount"),
                      posts=p.get("postsCount"), links=[x.get("url") for x in p.get("links") or [] if x.get("url")][:10] or None,
                      verified_domain=h if own else None, bound=f"its handle is the domain {h}, which you entered" if own and h in domains else None,
                      what=("Its handle is a web domain: Bluesky accepts that only after the domain proved it belongs to this account. " if own else "")
                           + "A public profile; it may belong to someone else with the same name unless other evidence ties it."))
    return out


def _keybase_finding(them: dict, how: str | None) -> dict:
    b, prof = them.get("basics") or {}, them.get("profile") or {}
    u = b.get("username_cased") or b.get("username")
    proofs = [{"service": p.get("proof_type"), "name": p.get("nametag"), "url": p.get("service_url"), "proof": p.get("human_url") or p.get("proof_url")}
              for p in (them.get("proofs_summary") or {}).get("all") or [] if p.get("state") == 1]
    return _f("Keybase", "account", "keybase:" + u.lower(), f"Keybase {u}", f"https://keybase.io/{u}", name=prof.get("full_name"), bio=prof.get("bio"),
              location=prof.get("location"), image=((them.get("pictures") or {}).get("primary") or {}).get("url"),
              created_at=time.strftime("%Y-%m-%d", time.gmtime(b["ctime"])) if b.get("ctime") else None, proofs=proofs or None, bound=how,
              what="Keybase proofs are statements signed with the account's key and posted on the other service, so each proof listed "
                   "here was made by whoever controls both accounts." + ("" if how else " " + NOT_THEM))


async def keybase(c: httpx.AsyncClient, username: str) -> list[dict]:
    r = await c.get("https://keybase.io/_/api/1.0/user/lookup.json", params={"usernames": username, "fields": "basics,profile,proofs_summary,pictures"})
    _check(r, "Keybase")
    them = [t for t in r.json().get("them") or [] if t]
    return [_keybase_finding(t, None) for t in them]


async def keybase_by(c: httpx.AsyncClient, service: str, name: str) -> list[dict]:
    """Keybase accounts that proved they control this GitHub account or domain: those are tied to the case."""
    r = await c.get("https://keybase.io/_/api/1.0/user/lookup.json", params={service: name, "fields": "basics,profile,proofs_summary,pictures"})
    _check(r, "Keybase")
    what = {"github": f"it has a signed proof for the GitHub account {name}", "domain": f"it has a signed proof for the domain {name}"}[service]
    return [_keybase_finding(t, what) for t in r.json().get("them") or [] if t]


async def gitlab(c: httpx.AsyncClient, username: str) -> list[dict]:
    r = await c.get("https://gitlab.com/api/v4/users", params={"username": username})
    _check(r, "GitLab")
    return [_f("GitLab", "account", "gitlab", f"GitLab {u.get('username')}", u.get("web_url"), name=u.get("name"), image=u.get("avatar_url"),
               email=u.get("public_email"), email_verified_by="GitLab (a public email must be one the account verified)" if u.get("public_email") else None,
               state=u.get("state"), what=NOT_THEM) for u in r.json() or [] if u.get("web_url")]


async def codeberg(c: httpx.AsyncClient, username: str) -> list[dict]:
    r = await c.get(f"https://codeberg.org/api/v1/users/{username}")
    if r.status_code == 404:
        return []
    _check(r, "Codeberg")
    u = r.json()
    mail = u.get("email") if u.get("email") and "noreply" not in u["email"] else None
    return [_f("Codeberg", "account", "codeberg", f"Codeberg {u.get('login')}", u.get("html_url"), name=u.get("full_name"), bio=u.get("description"),
               website=u.get("website"), location=u.get("location"), image=u.get("avatar_url"), email=mail, created_at=(u.get("created") or "")[:10],
               followers=u.get("followers_count"), what=NOT_THEM)]


async def npm(c: httpx.AsyncClient, username: str) -> list[dict]:
    r = await c.get("https://registry.npmjs.org/-/v1/search", params={"text": f"maintainer:{username}", "size": 20})
    _check(r, "npm")
    objs = r.json().get("objects") or []
    if not objs:
        return []
    mails = {m.get("email") for o in objs for m in (o.get("package") or {}).get("maintainers") or [] if (m.get("username") or "").lower() == username.lower() and m.get("email")}
    pkgs = [o["package"]["name"] for o in objs if o.get("package", {}).get("name")]
    return [_f("npm", "account", "npm", f"npm packages maintained by {username}", f"https://www.npmjs.com/~{username}", packages=", ".join(pkgs[:12]),
               packages_seen=len(pkgs), email=sorted(mails)[0] if len(mails) == 1 else None,
               what="npm lists this username as a maintainer of these packages. It may be someone else with the same name.")]


async def dockerhub(c: httpx.AsyncClient, username: str) -> list[dict]:
    r = await c.get(f"https://hub.docker.com/v2/users/{username}")
    if r.status_code == 404:
        return []
    _check(r, "Docker Hub")
    u = r.json()
    return [_f("Docker Hub", "account", "dockerhub", f"Docker Hub {u.get('username') or username}", f"https://hub.docker.com/u/{username}",
               name=u.get("full_name"), location=u.get("location"), company=u.get("company"), website=u.get("profile_url"),
               created_at=(u.get("date_joined") or "")[:10], image=u.get("gravatar_url"), account_type=u.get("type"), what=NOT_THEM)]


USERNAME_SOURCES = [("Bluesky", bluesky), ("Keybase", keybase), ("GitLab", gitlab), ("Codeberg", codeberg), ("npm", npm), ("Docker Hub", dockerhub)]


async def profiles(username: str, domains=()) -> tuple[list[dict], list[str]]:
    """Every username source at once (each a different host); within one source, one request at a time."""
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        async def one(name, fn):
            try:
                return (await (fn(c, username, domains) if fn is bluesky else fn(c, username))), None
            except Exception as e:
                return [], f"{name}: {e if isinstance(e, SourceProblem) else type(e).__name__}"
        res = await asyncio.gather(*(one(n, fn) for n, fn in USERNAME_SOURCES))
    return [f for found, _ in res for f in found], [p for _, p in res if p]


async def keybase_for(service: str, name: str) -> tuple[list[dict], list[str]]:
    async with httpx.AsyncClient(timeout=20, headers=UA) as c:
        try:
            return await keybase_by(c, service, name), []
        except Exception as e:
            return [], [f"Keybase: {e if isinstance(e, SourceProblem) else type(e).__name__}"]


# ---- full names: research records (always weak: namesakes are certain) ----

NAMESAKE = "A record under this name. Namesakes are common: this is a weak lead until something else ties it to the subject."


async def orcid(c: httpx.AsyncClient, name: str) -> list[dict]:
    parts = [p.replace('"', "") for p in name.split()]
    # "Guido van Rossum": the family name may be several words, so try the first word as given name, then the last as family name
    tries = ([f'given-names:"{parts[0]}" AND family-name:"{" ".join(parts[1:])}"', f'given-names:"{" ".join(parts[:-1])}" AND family-name:"{parts[-1]}"']
             if len(parts) > 1 else [f'"{parts[0]}"'])
    rows = []
    for q in dict.fromkeys(tries):
        r = await c.get("https://pub.orcid.org/v3.0/expanded-search/", params={"q": q, "rows": 10}, headers={"Accept": "application/json"})
        _check(r, "ORCID")
        rows = r.json().get("expanded-result") or []
        if rows:
            break
        await asyncio.sleep(0.5)
    out = []
    for x in rows:
        oid = x.get("orcid-id")
        if not oid:
            continue
        nm = " ".join(filter(None, [x.get("given-names"), x.get("family-names")]))
        out.append(_f("ORCID", "record", "orcid:" + oid, f"ORCID record of {nm or oid}", f"https://orcid.org/{oid}", name=nm, credit_name=x.get("credit-name"),
                      institutions=", ".join((x.get("institution-name") or [])[:6]), email=", ".join(x.get("email") or []) or None, what=NAMESAKE))
    return out


async def openalex(c: httpx.AsyncClient, name: str) -> list[dict]:
    r = await c.get("https://api.openalex.org/authors", params={"search": name, "per-page": 10})
    _check(r, "OpenAlex")
    out = []
    for a in r.json().get("results") or []:
        aid = (a.get("id") or "").rsplit("/", 1)[-1]
        if not aid:
            continue
        inst = [i.get("display_name") for i in a.get("last_known_institutions") or [] if i.get("display_name")]
        years = [y for x in a.get("affiliations") or [] for y in x.get("years") or []]
        out.append(_f("OpenAlex", "record", "openalex:" + aid, f"OpenAlex author {a.get('display_name')}", f"https://openalex.org/authors/{aid}",
                      name=a.get("display_name"), institutions=", ".join(inst[:4]), works=a.get("works_count"), cited_by=a.get("cited_by_count"),
                      orcid=a.get("orcid"), active_years=f"{min(years)} to {max(years)}" if years else None, what=NAMESAKE))
    return out


async def scholars(name: str) -> tuple[list[dict], list[str]]:
    found, problems = [], []
    async with httpx.AsyncClient(timeout=20, headers=UA, follow_redirects=True) as c:
        for label, fn in (("ORCID", orcid), ("OpenAlex", openalex)):
            try:
                found += await fn(c, name)
            except Exception as e:
                problems.append(f"{label}: {e if isinstance(e, SourceProblem) else type(e).__name__}")
    return found, problems


# ---- web search with Brave (needs the owner's Brave Search key; results are weak leads) ----

async def brave(query: str, what: str) -> list[dict]:
    key = config.brave_key()
    if not key:
        raise SourceProblem("no Brave Search key (data/brave-key.txt)")
    async with httpx.AsyncClient(timeout=20, headers={**UA, "Accept": "application/json", "X-Subscription-Token": key}) as c:
        r = await c.get("https://api.search.brave.com/res/v1/web/search", params={"q": query, "count": 20, "safesearch": "moderate"})
    if r.status_code in (401, 403, 422):
        raise SourceProblem("the Brave Search key was refused")
    _check(r, "Brave Search")
    out = []
    for x in ((r.json().get("web") or {}).get("results") or [])[:20]:
        u = x.get("url")
        if not isinstance(u, str) or not u.startswith(("http://", "https://")):
            continue
        out.append(_f("Web search (Brave)", "mention", u, re.sub(r"<[^>]+>", "", x.get("title") or u)[:110], u,
                      snippet=re.sub(r"<[^>]+>", "", x.get("description") or "")[:300], query=query,
                      what=f"A web page a search for {what} returns. It may be about someone else."))
    return out


# ---- the Internet Archive: when a confirmed profile was first and last archived, and its bio back then ----

async def archive_history(url: str) -> dict:
    from . import enrich
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": enrich.BROWSER}) as c:
        first = await enrich.closest_archived(c, url, "19960101")
        await asyncio.sleep(1)
        last = await enrich.closest_archived(c, url, time.strftime("%Y%m%d"))
        if first is None and last is None:
            raise SourceProblem("the Internet Archive did not answer")
        out = {"first": (first or {}).get("first"), "first_url": (first or {}).get("snapshot"), "last": (last or {}).get("first"),
               "last_url": (last or {}).get("snapshot"), "asked": time.time()}
        if first and first.get("ts") and (last or {}).get("ts") != first["ts"]:
            try:                                       # the oldest copy as it was stored (id_: without the archive's toolbar)
                await asyncio.sleep(1)
                raw = re.sub(r"^https?://(www\.)?", "", url)
                r = await c.get(f"https://web.archive.org/web/{first['ts']}id_/https://{raw}")
                if r.status_code == 200:
                    out["bio_then"] = enrich._meta(r.text[:400_000], "og:description", "description", "twitter:description")
                    out["title_then"] = (enrich._meta(r.text[:400_000], "og:title") or "")[:160] or None
            except httpx.HTTPError:
                out["bio_note"] = "the oldest copy could not be opened"
    return out
