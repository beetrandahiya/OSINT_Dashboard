"""Turning a list of links into a dossier: open every page a scan found, read what it shows about the account,
mark the ones that are dead, and ask the Internet Archive when it first saw the page.

Only the page itself is read, the way a browser would show it to anyone: its title, description, preview
picture and any profile details the page publishes in its own metadata. Nothing is logged into.
"""
import asyncio
import html as _html
import ipaddress
import json
import re
import socket
import time
import urllib.request
from urllib.parse import urljoin, urlparse

import httpx

BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
PARALLEL, TIMEOUT, MAX_BYTES = 8, 12, 600_000
GONE = re.compile(r"(page not found|user not found|account (?:has been )?suspended|doesn['’]t exist|does not exist|no longer available|404)", re.I)
LOGIN = re.compile(r"/(login|signin|sign-in|accounts/login|auth)(/|\?|$)", re.I)


def _meta(text, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(n) + r'["\'][^>]*content=["\']([^"\']*)', text, re.I) \
            or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']' + re.escape(n) + r'["\']', text, re.I)
        if m and m.group(1).strip():
            return _html.unescape(m.group(1).strip())
    return None


def _jsonld(text):
    """Profile facts a page publishes about itself in structured data (schema.org Person / ProfilePage)."""
    out = {}
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', text, re.S | re.I)[:4]:
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if not isinstance(it, dict):
                continue
            ent = it.get("mainEntity") if isinstance(it.get("mainEntity"), dict) else it
            kind = ent.get("@type")
            kind = kind if isinstance(kind, list) else [kind]
            if not {"Person", "ProfilePage"} & set(kind):        # a WebSite or Organization describes the site, not the person
                continue
            for k_out, k_in in (("name", "name"), ("alternate_name", "alternateName"), ("description", "description"),
                                ("created", "dateCreated"), ("published", "datePublished"), ("location", "homeLocation"),
                                ("works_for", "worksFor"), ("same_as", "sameAs")):
                v = ent.get(k_in)
                if isinstance(v, dict):
                    v = v.get("name")
                if isinstance(v, list):
                    v = [x.get("name") if isinstance(x, dict) else x for x in v][:8]
                if v and k_out not in out:
                    out[k_out] = v
    return out


class Refused(Exception):
    pass


def _bad_ip(a: str) -> bool:
    ip = ipaddress.ip_address(a.split("%")[0])
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return not ip.is_global or ip.is_multicast      # loopback, private, link-local, ULA, CGNAT 100.64/10 (Tailscale), ...


async def check_url(url: str) -> None:
    """Raise Refused unless the address is an http(s) page on the public internet. Found links come from strangers'
    pages and search results: one that points (or redirects) at this computer, the router or a Tailscale machine
    must not be fetched and its answer stored."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise Refused("not a web address")
    try:
        if _bad_ip(u.hostname):
            raise Refused("it points at a private or local network address")
        return
    except ValueError:
        pass                                          # a name, not an address: resolve it
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        raise Refused("its name does not resolve")
    if not infos or any(_bad_ip(i[4][0]) for i in infos):
        raise Refused("its name resolves to a private or local network address")


def _peer_ok(r: httpx.Response, url: str) -> bool:
    """The address we really connected to. httpx resolves the name again after check_url, so a name that changes
    its answer in between (DNS rebinding) is caught here, before the body is read. Through a configured proxy the
    peer is the proxy and the proxy resolves names; then only check_url's answer counts."""
    ns = r.extensions.get("network_stream")
    peer = ns and ns.get_extra_info("server_addr")
    host = urlparse(url).hostname or ""
    if not peer or (urllib.request.getproxies() and not urllib.request.proxy_bypass(host)):
        return True
    return not _bad_ip(peer[0])


async def read_page(client: httpx.AsyncClient, url: str) -> dict:
    """What a page shows: alive or not, its title, description, picture, and any profile facts it publishes.
    Redirects are followed by hand (at most 5), every hop checked like the first address."""
    start, final, body, status = urlparse(url), url, b"", 0
    try:
        for _ in range(6):
            await check_url(final)
            async with client.stream("GET", final, headers={"User-Agent": BROWSER, "Accept-Language": "en"}, follow_redirects=False) as r:
                if not _peer_ok(r, final):
                    raise Refused("it connected to a private or local network address")
                if r.is_redirect and r.headers.get("location"):
                    final = urljoin(final, r.headers["location"])
                    continue
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                status = r.status_code
                break
        else:
            return {"alive": None, "why": "it redirects more than 5 times", "read": time.time()}
    except Refused as e:
        return {"alive": None, "why": f"not opened: {e}", "read": time.time(), "final_url": final if final != url else None}
    except httpx.TimeoutException:
        return {"alive": None, "why": "did not answer in time", "read": time.time()}
    except httpx.HTTPError as e:
        return {"alive": None, "why": f"could not be reached ({type(e).__name__})", "read": time.time()}
    text = body.decode("utf-8", "replace")
    end = urlparse(final)
    out = {"status": status, "final_url": final if final != url else None, "read": time.time()}
    title = _meta(text, "og:title", "twitter:title") or (re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I) or [None, None])[1]
    out["title"] = _html.unescape(re.sub(r"\s+", " ", title)).strip()[:160] if title else None
    out["description"] = (_meta(text, "og:description", "description", "twitter:description") or "")[:400] or None
    img = _meta(text, "og:image", "twitter:image", "twitter:image:src")
    user = start.path.strip("/").split("/")[-1].lstrip("@").lower()
    personal = img and (re.search(r"avatar|profile|/users?/|userpic|/u/|photo|pfp|gravatar", img, re.I) or (len(user) > 2 and user in img.lower()))
    out["image"] = img if img and img.startswith("https://") and personal else None
    out["banner"] = img if img and img.startswith("https://") and not personal else None
    out["site"] = _meta(text, "og:site_name")
    out.update({k: v for k, v in _jsonld(text).items() if v})
    # Is the account there? Judge only on what is visible, and say why.
    if status in (404, 410):
        out.update(alive=False, why=f"the site answered {status} (not found)")
    elif status >= 500:
        out.update(alive=None, why=f"the site had an error ({status}); try again later")
    elif status in (401, 403, 429):
        out.update(alive=None, why=f"the site refused automated visits ({status}); it may well exist")
    elif start.path.strip("/") and not end.path.strip("/") and end.netloc.endswith(start.netloc.split(".", 1)[-1]):
        out.update(alive=False, why="the page sends visitors to the site's front page")
    elif LOGIN.search(end.path) and not LOGIN.search(start.path):
        out.update(alive=None, why="the page sends visitors to a login screen; it may exist but is not public")
    elif out["title"] and GONE.search(out["title"]):
        out.update(alive=False, why=f"the page title says “{out['title'][:60]}”")
    else:
        out.update(alive=True, why=None)
    return out


async def first_archived(client: httpx.AsyncClient, url: str) -> dict | None:
    """The oldest copy of the page in the Internet Archive: proof the page existed at least since then."""
    try:
        r = await client.get("https://web.archive.org/cdx/search/cdx", params={
            "url": re.sub(r"^https?://(www\.)?", "", url).rstrip("/"), "output": "json", "limit": 1, "fl": "timestamp,original", "filter": "statuscode:200"},
            headers={"User-Agent": BROWSER})
        if r.status_code != 200:
            return None
        rows = r.json()
        if len(rows) < 2:
            return {"first": None}
        ts = rows[1][0]
        return {"first": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", "snapshot": f"https://web.archive.org/web/{ts}/{rows[1][1]}"}
    except (httpx.HTTPError, ValueError, IndexError):
        return None


async def enrich(findings: list[dict], on_done=None, archive=True) -> tuple[dict[int, dict], list[str]]:
    """Read every finding that has a web address, then look up archive dates for the live ones.
    Two passes, so a slow Internet Archive never holds up the page reads. Returns (results, problems)."""
    gate = asyncio.Semaphore(PARALLEL)
    per_host: dict[str, asyncio.Semaphore] = {}
    out, problems = {}, []
    limits = httpx.Limits(max_connections=PARALLEL * 2, max_keepalive_connections=PARALLEL)
    todo = [f for f in findings if f.get("url", "").startswith("http")]
    async with httpx.AsyncClient(timeout=TIMEOUT, limits=limits) as client:
        async def one(f):
            host = urlparse(f["url"]).netloc
            per_host.setdefault(host, asyncio.Semaphore(1))   # never two requests at once to the same site
            async with gate, per_host[host]:
                out[f["id"]] = {"page": await read_page(client, f["url"]), "archive": None}
            if on_done:
                on_done()
        await asyncio.gather(*(one(f) for f in todo))
    if archive:
        live = [f for f in todo if out[f["id"]]["page"].get("alive") is not False]
        fails, done = 0, 0
        async with httpx.AsyncClient(timeout=8) as wb:
            for i in range(0, len(live), 3):                   # three at a time: the Internet Archive asks for gentle use
                batch = live[i:i + 3]
                res = await asyncio.gather(*(first_archived(wb, f["url"]) for f in batch))
                for f, a in zip(batch, res):
                    out[f["id"]]["archive"] = a
                    fails = fails + 1 if a is None else 0
                    done += 1
                if fails >= 6:                                 # it is not answering: stop asking, and say so
                    problems.append(f"The Internet Archive did not answer, so archive dates were looked up for {done - fails} of {len(live)} pages")
                    break
    return out, problems
