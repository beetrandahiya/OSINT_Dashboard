"""What public services say about an email address. Each check names its source and returns plain findings.
None of them downloads leaked data: they report that an address appears somewhere, and what kind of data leaked."""
import hashlib

import httpx

from .. import config

SERVICES = [   # shown to the user before a scan, so it is clear who receives the address
    ("XposedOrNot", "xposedornot.com", "the address itself"),
    ("Hudson Rock", "hudsonrock.com", "the address itself"),
    ("Gravatar", "gravatar.com", "only a scrambled form (hash) of the address"),
    ("OpenPGP key server", "keys.openpgp.org", "the address itself"),
    ("GitHub", "github.com", "the address itself, as a search of public commits"),
]


def _f(tool, kind, key, title, url=None, **detail):
    return {"tool": tool, "kind": kind, "key": key, "title": title, "url": url, "detail": detail}


async def breaches(c: httpx.AsyncClient, email: str) -> list[dict]:
    r = await c.get("https://api.xposedornot.com/v1/breach-analytics", params={"email": email})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    d = r.json()
    out = []
    for b in ((d.get("ExposedBreaches") or {}).get("breaches_details")) or []:
        out.append(_f("XposedOrNot", "breach", b["breach"], b["breach"], f"https://xposedornot.com/xposed/#{b['breach']}",
                      what=b.get("details"), domain=b.get("domain"), year=b.get("xposed_date"), leaked=b.get("xposed_data"),
                      records=b.get("xposed_records"), passwords=b.get("password_risk")))
    return out


async def infostealer(c: httpx.AsyncClient, email: str) -> list[dict]:
    r = await c.get("https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email", params={"email": email})
    r.raise_for_status()
    d = r.json()
    stealers = d.get("stealers") or []
    if not stealers:
        return []
    return [_f("Hudson Rock", "exposure", "infostealer", "Computer infected by password-stealing malware", "https://www.hudsonrock.com/free-tools",
               what=d.get("message"), infections=[{"date": s.get("date_compromised"), "computer": s.get("computer_name"), "system": s.get("operating_system"),
                                                   "saved_logins": s.get("total_user_services")} for s in stealers])]


async def gravatar(c: httpx.AsyncClient, email: str) -> list[dict]:
    h = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    r = await c.get(f"https://gravatar.com/{h}.json")
    if r.status_code == 404:
        return []
    r.raise_for_status()
    e = (r.json().get("entry") or [{}])[0]
    out = [_f("Gravatar", "profile", "gravatar", f"Gravatar profile “{e.get('displayName') or e.get('preferredUsername')}”", e.get("profileUrl"),
              username=e.get("preferredUsername"), about=e.get("aboutMe"), photo=e.get("thumbnailUrl"))]
    for a in e.get("accounts") or []:
        out.append(_f("Gravatar", "account", "gravatar:" + (a.get("shortname") or a.get("domain") or ""), f"{a.get('name') or a.get('shortname')} account linked on Gravatar", a.get("url"), username=a.get("username")))
    return out


async def pgp(c: httpx.AsyncClient, email: str) -> list[dict]:
    r = await c.get("https://keys.openpgp.org/vks/v1/by-email/" + email.replace("@", "%40"))
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return [_f("OpenPGP key server", "key", "pgp", "Public encryption key published", "https://keys.openpgp.org/search?q=" + email, what="A PGP key carrying this address is on the public key server.")]


async def github(c: httpx.AsyncClient, email: str) -> list[dict]:
    r = await c.get("https://api.github.com/search/commits", params={"q": f"author-email:{email}", "per_page": 30, "sort": "author-date"},
                    headers={"Accept": "application/vnd.github+json"})
    if r.status_code in (403, 429):
        raise RuntimeError("GitHub's limit for searches without an account is used up; try again in a minute")
    r.raise_for_status()
    d = r.json()
    repos, out = {}, []
    for it in d.get("items") or []:
        repo = it["repository"]["full_name"]
        repos.setdefault(repo, {"n": 0, "name": it["commit"]["author"].get("name"), "login": (it.get("author") or {}).get("login"), "url": it["repository"]["html_url"]})
        repos[repo]["n"] += 1
    for repo, v in repos.items():
        out.append(_f("GitHub", "code", "repo:" + repo, f"Commits in {repo}", v["url"], author_name=v["name"], account=v["login"], commits_seen=v["n"],
                      what="This address is written into public commits of this repository, where anyone can read it."))
    if d.get("total_count") and not out:
        out.append(_f("GitHub", "code", "commits", f"{d['total_count']} public commits carry this address", None))
    return out


CHECKS = [("XposedOrNot", breaches), ("Hudson Rock", infostealer), ("Gravatar", gravatar), ("OpenPGP key server", pgp), ("GitHub", github)]


async def search(email: str) -> tuple[list[dict], list[str]]:
    """Returns (findings, problems). A service that fails is reported, never silently skipped."""
    found, problems = [], []
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True) as c:
        for name, fn in CHECKS:
            try:
                found += await fn(c, email)
            except Exception as e:
                problems.append(f"{name}: {e if isinstance(e, RuntimeError) else type(e).__name__}")
    return found, problems
