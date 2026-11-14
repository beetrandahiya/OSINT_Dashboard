"""Does a public profile exist under this username? Checked site by site with the open WhatsMyName list
(github.com/WebBreacher/WhatsMyName, CC BY-SA 4.0), which gives for each site the profile address, what a
page looks like when the account exists, and what it looks like when it does not.

Such lists go stale: sites change their pages or start blocking automated visitors. So before a site's
answer is trusted, the site is tested with an account the list says exists and with a made-up name. Only
sites that get both right are used.
"""
import asyncio
import json
import secrets
import time
from urllib.parse import quote

import httpx

from .. import config

LIST_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
LIST_FILE = config.DATA / "whatsmyname.json"
TEST_FILE = config.DATA / "whatsmyname-selftest.json"
BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
PARALLEL, TIMEOUT = 40, 12


async def site_list(max_age=7 * 86400) -> list[dict]:
    """The list of sites, downloaded at most once a week and kept on disk."""
    if not LIST_FILE.exists() or time.time() - LIST_FILE.stat().st_mtime > max_age:
        try:
            async with httpx.AsyncClient(timeout=30, headers={"User-Agent": config.USER_AGENT}) as c:
                r = await c.get(LIST_URL)
                r.raise_for_status()
            config.DATA.mkdir(parents=True, exist_ok=True)
            LIST_FILE.write_text(r.text)
        except httpx.HTTPError:
            if not LIST_FILE.exists():
                raise
    return [s for s in json.loads(LIST_FILE.read_text())["sites"] if s.get("valid", True) is not False]


async def check(client: httpx.AsyncClient, site: dict, name: str) -> dict:
    """One site, one username. Answers 'found', 'missing' or 'unclear' (the page matched neither pattern, or
    the site did not answer); 'unclear' is never shown as a hit."""
    safe = name
    for ch in site.get("strip_bad_char", ""):
        safe = safe.replace(ch, "")
    url = site["uri_check"].replace("{account}", quote(safe, safe=""))
    shown = (site.get("uri_pretty") or site["uri_check"]).replace("{account}", quote(safe, safe=""))
    out = {"site": site["name"], "category": site.get("cat"), "url": shown, "state": "unclear", "why": None}
    try:
        headers = {"User-Agent": BROWSER, "Accept-Language": "en", **(site.get("headers") or {})}
        if site.get("post_body"):
            r = await client.post(url, content=site["post_body"].replace("{account}", safe), headers=headers)
        else:
            r = await client.get(url, headers=headers)
        text = r.text
        if r.status_code == site["e_code"] and site["e_string"] in text:
            out["state"] = "found"
        elif r.status_code == site.get("m_code") and (not site.get("m_string") or site["m_string"] in text):
            out["state"] = "missing"
        else:
            out["why"] = f"answered {r.status_code}, matching neither pattern"
    except httpx.TimeoutException:
        out["why"] = "no answer in time"
    except (httpx.HTTPError, UnicodeError, ValueError) as e:
        out["why"] = type(e).__name__
    return out


async def sweep(names_by_site, on_result=None) -> list[dict]:
    """Run many (site, username) checks, a limited number at once and never two at a time against one site."""
    gate = asyncio.Semaphore(PARALLEL)
    limits = httpx.Limits(max_connections=PARALLEL, max_keepalive_connections=0)
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, limits=limits, verify=True) as client:
        async def one(site, name):
            async with gate:
                res = await check(client, site, name)
            res["username"] = name
            if on_result:
                on_result(res)
            return res
        return await asyncio.gather(*(one(s, n) for s, n in names_by_site))


async def self_test() -> dict:
    """Test every site with its known account (must be found) and a made-up name (must not be found)."""
    sites = await site_list()
    fake = "ww" + secrets.token_hex(7)
    with_known = [s for s in sites if s.get("known")]
    real = await sweep([(s, s["known"][0]) for s in with_known])
    made_up = await sweep([(s, fake) for s in with_known])
    result = {"tested": time.time(), "sites": {}, "total": len(sites)}
    for s, a, b in zip(with_known, real, made_up):
        ok = a["state"] == "found" and b["state"] != "found"
        result["sites"][s["name"]] = {"ok": ok, "known": a["state"], "made_up": b["state"],
                                      "why": None if ok else ("says the made-up name exists" if b["state"] == "found" else a["why"] or "did not find its known account")}
    result["trusted"] = sum(1 for v in result["sites"].values() if v["ok"])
    result["false_alarm"] = sum(1 for v in result["sites"].values() if v["made_up"] == "found")
    result["blind"] = sum(1 for v in result["sites"].values() if v["known"] != "found")
    config.DATA.mkdir(parents=True, exist_ok=True)
    TEST_FILE.write_text(json.dumps(result))
    return result


def last_self_test() -> dict | None:
    return json.loads(TEST_FILE.read_text()) if TEST_FILE.exists() else None


async def search(usernames: list[str], on_result=None) -> dict:
    """The real sweep: only sites that passed the self-test are asked."""
    test = last_self_test()
    if not test:
        raise RuntimeError("the checker has not been tested on this computer yet")
    sites = [s for s in await site_list() if test["sites"].get(s["name"], {}).get("ok")]
    results = await sweep([(s, n) for n in usernames for s in sites], on_result)
    return {"asked": len(sites), "skipped": test["total"] - len(sites), "tested": test["tested"], "results": results}
