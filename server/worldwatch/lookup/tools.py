"""The standard open-source OSINT tools (the ones a Kali Linux install ships), run as they are.

Each tool is started as its own program through `uvx`, which downloads it on first use into uv's own tool
cache and keeps it apart from World Watch. Nothing of theirs is copied into this code; we only read what
they print or write. A tool that fails or is missing is reported by name, never skipped silently.
"""
import asyncio
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import httpx

from .. import config

# name -> what it is, what it is asked, where the requests go, how heavy the first download is
TOOLS = {
    "maigret": {"title": "Maigret", "for": "username", "sends": "the username to up to 3,000 websites, and reads public profile details (name, picture, links) from the pages it finds",
                "first": "about 190 MB on first use"},
    "sherlock": {"title": "Sherlock", "for": "username", "sends": "the username to about 400 websites", "first": "about 30 MB on first use"},
    "holehe": {"title": "Holehe", "for": "email", "sends": "the email address to the sign-up or login forms of about 120 websites, to see which say it is already registered",
               "first": "about 20 MB on first use"},
    "theharvester": {"title": "theHarvester", "for": "domain", "sends": "the domain name to public search sources (certificate logs, DNS databases, URL scanners)",
                     "first": "about 120 MB on first use, fetched from GitHub"},
}


class ToolProblem(Exception):
    pass


async def run(args: list[str], timeout: int, cwd: str | None = None) -> str:
    """Start one tool and return everything it printed."""
    uvx = shutil.which("uvx") or shutil.which("uvx", path=os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin:/usr/local/bin")
    if not uvx:
        raise ToolProblem("uvx was not found on this computer (it comes with uv)")
    env = {**os.environ, "NO_COLOR": "1", "PYTHONUNBUFFERED": "1", "COLUMNS": "200"}
    p = await asyncio.create_subprocess_exec(uvx, "--quiet", *args, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        raise ToolProblem(f"stopped after {timeout // 60} minutes without finishing")
    text = out.decode("utf-8", "replace")
    if p.returncode not in (0, None) and not text.strip():
        raise ToolProblem(f"ended with error code {p.returncode}")
    return text


def _f(tool, kind, key, title, url=None, **detail):
    return {"tool": tool, "kind": kind, "key": key, "title": title, "url": url, "detail": {k: v for k, v in detail.items() if v not in (None, "", [], {})}}


KEEP = ("fullname", "name", "username", "bio", "location", "country", "city", "created_at", "follower_count", "following_count", "image", "links", "website",
        "email", "phone", "gender", "is_verified", "is_private", "latest_activity_at", "last_seen", "uid", "id", "twitter_username", "telegram", "company", "blog")


async def maigret(username: str, deep: bool) -> list[dict]:
    with tempfile.TemporaryDirectory() as d:
        args = ["maigret", username, "--json", "simple", "--folderoutput", d, "--no-progressbar", "--no-color", "--timeout", "15", "--retries", "1"]
        args += ["-a"] if deep else ["--top-sites", "500"]
        text = await run(args, 1500 if deep else 600)
        files = list(Path(d).glob("report_*_simple.json"))
        if not files:
            raise ToolProblem("wrote no report: " + (text.strip().splitlines() or ["no output"])[-1][:160])
        out = []
        for f in files:                       # Maigret also follows usernames it finds on profile pages; each gets its own report
            who = re.match(r"report_(.+)_simple\.json", f.name).group(1)
            for site, v in json.loads(f.read_text()).items():
                st = v.get("status") or {}
                if st.get("status") != "Claimed":
                    continue
                ids = {k: val for k, val in (st.get("ids") or {}).items() if k in KEEP and val not in (None, "", "None", "False")}
                extra = {} if who == username else {"reached_through": f"the username “{who}”, which Maigret found on one of the profile pages and followed"}
                out.append(_f("Maigret", "account", site + ("" if who == username else ":" + who), f"{site} profile" + ("" if who == username else f" ({who})"),
                              v.get("url_user") or st.get("url"), topics=", ".join(st.get("tags") or []) or None, **ids, **extra,
                              what="A public profile page exists under this username. It may belong to someone else with the same name."
                                   + (" Maigret read the details below from that page." if ids else "")))
        return out


async def sherlock(username: str) -> list[dict]:
    with tempfile.TemporaryDirectory() as d:
        text = await run(["--from", "sherlock-project", "sherlock", username, "--print-found", "--no-color", "--timeout", "12", "--folderoutput", d], 600, cwd=d)
    out = []
    for m in re.finditer(r"^\[\+\]\s+(.+?):\s+(https?://\S+)", text, re.M):
        out.append(_f("Sherlock", "account", m.group(1), f"{m.group(1)} profile", m.group(2),
                      what="A public profile page exists under this username. It may belong to someone else with the same name."))
    if not out and "Search completed" not in text:
        raise ToolProblem((text.strip().splitlines() or ["no output"])[-1][:160])
    return out


async def holehe(email: str, password_reset: bool) -> list[dict]:
    args = ["holehe", email, "--no-color", "--no-clear", "-T", "15"] + ([] if password_reset else ["-NP"])
    text = await run(args, 400)
    if "websites checked" not in text:
        raise ToolProblem((text.strip().splitlines() or ["no output"])[-1][:160])
    limited = len(re.findall(r"^\[x\]\s+\S+\.\S+", text, re.M))
    checked = re.search(r"(\d+) websites checked", text)
    out = [_f("Holehe", "registered", m.group(1), f"Registered at {m.group(1)}", "https://" + m.group(1),
              what="This website's sign-up or login form says an account already exists for this address. Holehe's site checks are not all up to date, so treat single hits with care.")
           for m in re.finditer(r"^\[\+\]\s+(\S+)", text, re.M) if "." in m.group(1) and "Email used" not in m.group(0)]
    if limited:
        out.append(_f("Holehe", "note", "rate-limited", f"{limited} of {checked.group(1) if checked else 'its'} sites refused to answer",
                      None, what="These sites rate-limited or blocked the question, so nothing is known about them. Trying again later may help."))
    return out


async def theharvester(domain: str) -> tuple[list[dict], list[str]]:
    sources = "crtsh,certspotter,rapiddns,hackertarget,otx,urlscan,duckduckgo,waybackarchive,commoncrawl,subdomaincenter,thc"   # the ones that need no key
    with tempfile.TemporaryDirectory() as d:
        base = str(Path(d) / "out")
        text = await run(["--from", "git+https://github.com/laramies/theHarvester", "theHarvester", "-d", domain, "-b", sources, "-l", "300", "-f", base], 600, cwd=d)
        if not Path(base + ".json").exists():
            raise ToolProblem((text.strip().splitlines() or ["no output"])[-1][:160])
        data = json.loads(Path(base + ".json").read_text())
        failed = []
        if Path(base + ".jsonl").exists():
            for line in Path(base + ".jsonl").read_text().splitlines():
                try:
                    failed += [f"{s['source']} ({s.get('stop_reason') or 'failed'})" for s in json.loads(line).get("source_executions", []) if s.get("status") == "failed"]
                except ValueError:
                    pass
    out = []
    for h in sorted(set(data.get("hosts") or [])):
        name = h.split(":")[0]
        out.append(_f("theHarvester", "host", name, name, "https://" + name, address=h.split(":")[1] if ":" in h else None, what="A host name under this domain that appears in public records."))
    for e in sorted(set(data.get("emails") or [])):
        out.append(_f("theHarvester", "email", e, e, None, what="An email address at this domain that appears on public pages."))
    for u in sorted(set(data.get("interesting_urls") or []))[:40]:
        out.append(_f("theHarvester", "url", u, u[:80], u))
    problems = [f"theHarvester: {len(failed)} of its sources did not answer: {', '.join(failed[:8])}"] if failed else []
    return out, problems


# ---- small checks done here, without an outside tool ----

async def domain_records(domain: str) -> list[dict]:
    out = []
    async with httpx.AsyncClient(timeout=25, headers={"User-Agent": config.USER_AGENT}, follow_redirects=True) as c:
        r = await c.get(f"https://rdap.org/domain/{domain}")
        if r.status_code == 200:
            d = r.json()
            ev = {e["eventAction"]: e["eventDate"][:10] for e in d.get("events") or [] if e.get("eventDate")}
            who = []
            for ent in d.get("entities") or []:
                for item in (ent.get("vcardArray") or [None, []])[1]:
                    if item[0] in ("fn", "org", "email") and item[3]:
                        who.append(f"{'/'.join(ent.get('roles') or [])}: {item[3]}")
            out.append(_f("Domain registry (RDAP)", "registration", "rdap", f"Registration record of {domain}", f"https://rdap.org/domain/{domain}",
                          registered=ev.get("registration"), expires=ev.get("expiration"), last_changed=ev.get("last changed"),
                          name_servers=", ".join(n.get("ldhName", "").lower() for n in d.get("nameservers") or []), listed_contacts="; ".join(dict.fromkeys(who)) or "none shown (redacted)",
                          what="What the domain registry publishes about this domain. Personal contact details are usually hidden since 2018."))
        r = await c.get("https://crt.sh/", params={"q": domain, "output": "json"})
        if r.status_code == 200:
            names = sorted({n.strip().lower() for row in r.json() for n in row.get("name_value", "").split("\n") if n.strip().endswith(domain) and "*" not in n})
            for n in names[:150]:
                out.append(_f("Certificate logs (crt.sh)", "host", n, n, "https://" + n, what="A security certificate was issued for this host name, which makes the name public for ever."))
        else:
            raise ToolProblem(f"crt.sh answered {r.status_code}; the registry record was still read")
    return out


def phone(number: str) -> list[dict]:
    import phonenumbers
    from phonenumbers import carrier, geocoder, number_type, timezone
    n = phonenumbers.parse(number, None if number.strip().startswith("+") else "DE")
    kinds = {0: "landline", 1: "mobile", 2: "landline or mobile", 3: "toll-free", 4: "premium rate", 6: "internet telephony (VoIP)", 7: "personal number"}
    return [_f("Number plan (offline)", "phone", "plan", phonenumbers.format_number(n, phonenumbers.PhoneNumberFormat.INTERNATIONAL), None,
               valid_number="yes" if phonenumbers.is_valid_number(n) else "no", line_type=kinds.get(number_type(n), "other"),
               region=geocoder.description_for_number(n, "en") or None, original_carrier=carrier.name_for_number(n, "en") or None, time_zone=", ".join(timezone.time_zones_for_number(n)),
               what="Read from the public numbering plan, on this computer; nothing was sent anywhere. The carrier is the one the number block was first given to; a ported number may be elsewhere now.")]


async def github_account(user: str) -> list[dict]:
    out = []
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": config.USER_AGENT, "Accept": "application/vnd.github+json"}) as c:
        r = await c.get(f"https://api.github.com/users/{user}")
        if r.status_code in (403, 429):
            raise ToolProblem("GitHub's hourly limit for requests without an account is used up")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        u = r.json()
        out.append(_f("GitHub", "profile", "profile", f"GitHub profile {u['login']}", u["html_url"], name=u.get("name"), bio=u.get("bio"), company=u.get("company"), location=u.get("location"),
                      email=u.get("email"), website=u.get("blog"), twitter_username=u.get("twitter_username"), public_repositories=u.get("public_repos"), followers=u.get("followers"),
                      created_at=(u.get("created_at") or "")[:10], image=u.get("avatar_url"), what="What the GitHub profile shows to everyone."))
        ev = await c.get(f"https://api.github.com/users/{user}/events/public", params={"per_page": 100})
        seen = {}
        for e in ev.json() if ev.status_code == 200 else []:
            for cm in (e.get("payload") or {}).get("commits") or []:
                a = cm.get("author") or {}
                if a.get("email") and "noreply" not in a["email"]:
                    seen.setdefault(a["email"], {"name": a.get("name"), "repo": e["repo"]["name"]})
        for mail, v in seen.items():
            out.append(_f("GitHub", "email", "commit-email:" + mail, f"Email in public commits: {mail}", f"https://github.com/{v['repo']}", author_name=v["name"], repository=v["repo"],
                          what="This address is written into recent public commits of this account, where anyone can read it."))
    return out


async def name_mentions(name: str) -> list[dict]:
    """A plain web search for the exact name. Namesakes are certain; this is only a starting list."""
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"}) as c:
        r = await c.post("https://html.duckduckgo.com/html/", data={"q": f'"{name}"'})
    if r.status_code != 200 or "result__a" not in r.text:
        raise ToolProblem("DuckDuckGo did not return results (it often blocks automated searches)")
    import html as _h
    from urllib.parse import parse_qs, urlparse
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        url = _h.unescape(m.group(1))
        if "uddg=" in url:
            url = parse_qs(urlparse(url).query).get("uddg", [url])[0]
        title = _h.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        out.append(_f("Web search (DuckDuckGo)", "mention", url, title[:90] or url, url, what="A web page that a search for the exact name returns. It may be about someone else with the same name."))
    return out[:25]
