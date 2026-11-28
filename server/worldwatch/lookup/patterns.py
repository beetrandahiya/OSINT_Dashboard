"""Recognising "site + username" in any web address.

The WhatsMyName list (already used by the username checker) gives every site's profile address with an
{account} placeholder; a few large platforms are added here by hand. A link such as
https://twitter.com/someone or https://someone.carrd.co becomes ("twitter.com", "someone"). This only reads
addresses: nothing is fetched.
"""
import json
import re
from urllib.parse import parse_qs, urlsplit

from .. import config

BUILTIN = [
    ("GitHub", "https://github.com/{account}"), ("GitLab", "https://gitlab.com/{account}"), ("Codeberg", "https://codeberg.org/{account}"),
    ("X (Twitter)", "https://twitter.com/{account}"), ("X (Twitter)", "https://x.com/{account}"), ("Instagram", "https://instagram.com/{account}"),
    ("Bluesky", "https://bsky.app/profile/{account}"), ("Keybase", "https://keybase.io/{account}"), ("Reddit", "https://reddit.com/user/{account}"),
    ("Reddit", "https://reddit.com/u/{account}"), ("Hacker News", "https://news.ycombinator.com/user?id={account}"), ("npm", "https://npmjs.com/~{account}"),
    ("Docker Hub", "https://hub.docker.com/u/{account}"), ("LinkedIn", "https://linkedin.com/in/{account}"), ("YouTube", "https://youtube.com/@{account}"),
    ("Telegram", "https://t.me/{account}"), ("Medium", "https://medium.com/@{account}"), ("Mastodon", "https://mastodon.social/@{account}"),
    ("Facebook", "https://facebook.com/{account}"), ("TikTok", "https://tiktok.com/@{account}"), ("Twitch", "https://twitch.tv/{account}"),
    ("PyPI", "https://pypi.org/user/{account}"), ("Threads", "https://threads.net/@{account}"), ("DEV", "https://dev.to/{account}"),
    ("Linktree", "https://linktr.ee/{account}"), ("About.me", "https://about.me/{account}"), ("Gravatar", "https://gravatar.com/{account}"),
    ("SourceHut", "https://sr.ht/~{account}"), ("Hugging Face", "https://huggingface.co/{account}"), ("Kaggle", "https://kaggle.com/{account}"),
]
ALIAS = {"x.com": "twitter.com", "mobile.twitter.com": "twitter.com", "old.reddit.com": "reddit.com", "m.facebook.com": "facebook.com",
         "m.youtube.com": "youtube.com", "mobile.x.com": "twitter.com"}
# path words that are pages of the site, never a username
RESERVED = set("""about account accounts admin api apps blog careers contact dashboard developers docs download events explore feed help home
hashtag i intent join legal login logout marketplace messages new notifications p pages pricing privacy profile search security settings share
shop signin signup site sponsors status support terms topics trending tv user users watch www search_results orgs organizations features
enterprise team teams collections marketplace login.php sharer sharer.php dialog plugins policies policy""".split())
# hosts of platforms: a link to one of these is a page on a platform, not someone's own website
PLATFORMS = set("""google.com youtube.com facebook.com wikipedia.org wikimedia.org apple.com microsoft.com amazon.com paypal.com patreon.com ko-fi.com
buymeacoffee.com discord.gg discord.com spotify.com soundcloud.com bandcamp.com flickr.com vimeo.com pinterest.com tumblr.com wordpress.com
blogspot.com substack.com notion.site github.io gitlab.io pages.dev netlify.app vercel.app herokuapp.com archive.org web.archive.org
goo.gl bit.ly t.co lnkd.in ow.ly tinyurl.com linktr.ee mailto""".split())

_cache = {"mtime": None, "index": None}


def host_of(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    h = h[4:] if h.startswith("www.") else h
    return ALIAS.get(h, h)


def _compile(site: str, pattern: str):
    """(site, host key, is_subdomain, regex) for one profile address, or None when it is not a profile page."""
    p = pattern.strip()
    if "{account}" not in p or re.search(r"search|/api/|api\.|\?q=|query=|keywords=|ajax", p, re.I):
        return None
    u = urlsplit(p.replace("{account}", "ACCOUNTX"))
    host = (u.hostname or "").lower()
    if not host or "web.archive.org" in host or host in ("archive.org",):
        return None
    host = host[4:] if host.startswith("www.") else host
    if "accountx" in host:                                    # https://{account}.carrd.co
        suffix = host.split("accountx", 1)[1]
        if not suffix.startswith(".") or suffix.count(".") < 2 and len(suffix) < 5:
            return None
        return site, ALIAS.get(suffix[1:], suffix[1:]), True, None
    path, query = u.path, u.query
    if "ACCOUNTX" in query:                                    # ...?id={account}
        key = next((k for k, v in parse_qs(query).items() if "ACCOUNTX" in v[0]), None)
        if not key:
            return None
        rx = re.compile("^" + re.escape(path.rstrip("/")) + "/?$", re.I)
        return site, ALIAS.get(host, host), False, (rx, key)
    if "ACCOUNTX" not in path:
        return None
    before, after = path.split("ACCOUNTX", 1)
    if not before.strip("/") and not before.endswith(("@", "~")) and before != "/":
        return None
    after = after.rstrip("/")
    rx = re.compile("^" + re.escape(before) + r"([^/?#&]+)" + re.escape(after) + r"(?:/.*)?$", re.I)
    return site, ALIAS.get(host, host), False, rx


def index():
    """Profile patterns by host, rebuilt when the WhatsMyName file changes."""
    f = config.DATA / "whatsmyname.json"
    mtime = f.stat().st_mtime if f.exists() else 0
    if _cache["index"] is not None and _cache["mtime"] == mtime:
        return _cache["index"]
    pats = list(BUILTIN)
    if f.exists():
        try:
            for s in json.loads(f.read_text()).get("sites", []):
                pats.append((s.get("name") or "?", s.get("uri_pretty") or s.get("uri_check") or ""))
        except (ValueError, OSError):
            pass
    by_host, subs = {}, {}
    for site, p in pats:
        c = _compile(site, p)
        if not c:
            continue
        site, host, is_sub, rx = c
        if is_sub:
            subs.setdefault(host, site)
        else:
            by_host.setdefault(host, []).append((site, rx))
    _cache.update(mtime=mtime, index=(by_host, subs))
    return by_host, subs


def match(url: str):
    """(site name, canonical host, username) when the address is someone's profile page on a known site, else None."""
    if not isinstance(url, str) or not re.match(r"https?://", url, re.I):
        return None
    by_host, subs = index()
    u = urlsplit(url)
    host = host_of(url)
    for site, rx in by_host.get(host, []):
        if isinstance(rx, tuple):
            rxp, key = rx
            if rxp.match(u.path.rstrip("/") or "/"):
                v = (parse_qs(u.query).get(key) or [""])[0]
                if _ok(v):
                    return site, host, v
            continue
        m = rx.match(u.path or "/")
        if m and _ok(m.group(1)):
            return site, host, m.group(1).lstrip("@~")
    parts = host.split(".", 1)
    if len(parts) == 2 and parts[1] in subs and _ok(parts[0]) and parts[0] not in ("www", "m", "blog", "api", "docs", "help"):
        return subs[parts[1]], parts[1], parts[0]
    return None


def _ok(v: str) -> bool:
    v = (v or "").strip().lstrip("@~")
    return 1 < len(v) <= 60 and v.lower() not in RESERVED and bool(re.fullmatch(r"[A-Za-z0-9._%-]+", v)) and not v.isdigit()   # numeric ids are not usernames


def is_platform(url: str) -> bool:
    """A link to a platform or link shortener, not to someone's own website."""
    h = host_of(url)
    if not h:
        return True
    by_host, subs = index()
    if h in by_host or h in subs or any(h == p or h.endswith("." + p) for p in PLATFORMS):
        return True
    return any(h.endswith("." + s) for s in subs)


def site_label(host: str) -> str:
    by_host, subs = index()
    if host in by_host:
        return by_host[host][0][0]
    return subs.get(host, host)
