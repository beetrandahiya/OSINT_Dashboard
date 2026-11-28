"""The pivot engine and same-person evidence of a case: from what was found, which further identifiers belong
to the same person (leads), and why each found account might be theirs (evidence chips).

HARD BOUNDARIES (non-negotiable, also stated on the page):
- No face recognition and no face-search engines (PimEyes, FaceCheck, Yandex face search), automated or
  linked. Pictures are compared only as files: a 64-bit difference hash says "same picture" (a copy, resized
  or recompressed), never "same face".
- Nothing infers where a person lives, is or goes. A picture's GPS metadata is only reported as present;
  coordinates are never read. Places a profile states about itself are shown as text, never placed on a map.
- No breach dump contents or passwords: breach names and the kinds of data only.
- No logged-in scraping and nothing past a login, captcha or bot shield.
- A case cannot start without its consent record, and there is no "search any person" without a case.

How it works. An "anchor" is an account that belongs to the subject for a stated reason: the owner marked it
confirmed, or it is the identifier itself (the GitHub profile of the GitHub account entered, the Gravatar of
the address entered, a Keybase account that proved control of the GitHub account entered...). Leads come only
from anchors and from explicit searches, never from unconfirmed pages (those are often namesakes).

STRONG leads (followed automatically during a scan, at most 2 steps from what was entered):
  - reciprocal links: an anchor's page links to B and B's page links back to an anchor (rel="me" both ways is
    the explicit form of this);
  - an email in the public commits of an anchored GitHub account, a GitHub-verified profile email, and the
    GitHub account GitHub itself attributes an entered address's commits to;
  - Keybase proofs (signed statements) of a Keybase account tied to the case;
  - other addresses on the same PGP key (keys.openpgp.org publishes only addresses their owner confirmed);
  - an identical picture fingerprint to an anchor's picture or an uploaded seed picture.
WEAK leads wait for the owner: display names, one-way links, similar usernames, web and name-search hits.
Anything from a full-name source is always weak. There is no score anywhere: only the stated reasons.
"""
import hashlib
import re
import unicodedata

from . import patterns, store

SAME_PICTURE = 6        # bits of 64 that may differ for "same picture" (resized or recompressed copies)
CHECK = {"username": r"[A-Za-z0-9._-]{2,40}", "email": r"[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}", "name": r".{3,80}",
         "domain": r"([a-z0-9-]+\.)+[a-z]{2,}", "github": r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}"}
DEFAULT_PIC = re.compile(r"default|placeholder|blank|anonymous|no[-_]?avatar|avatar[-_]?default|missing|mystery|silhouette|/0{32}|[?&]d=mp\b|forcedefault|[?&]f=y\b", re.I)
SEARCH_TOOLS = ("Web search (Brave)", "Web search (DuckDuckGo)")
_memo = {}


def fold(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def usable_fp(h) -> bool:
    """A flat or nearly flat picture (a blank square, a single colour) says nothing about who uses it."""
    return isinstance(h, str) and len(h) == 16 and 6 <= bin(int(h, 16)).count("1") <= 58


def _urls_in(v) -> list:
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str) and x.startswith(("http://", "https://"))]
    return re.findall(r"https?://[^\s'\",\]\)]+", str(v or ""))


def _web(v):
    v = str(v or "").strip()
    if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(/\S*)?", v, re.I):
        return "https://" + v
    return v if v.startswith(("http://", "https://")) else None


def _domain(url) -> str | None:
    """The website's domain when the address is someone's own site (not a platform or a link shortener)."""
    if not url or patterns.is_platform(url):
        return None
    h = patterns.host_of(url)
    return h if re.fullmatch(CHECK["domain"], h or "") else None


def _keys(url):
    """What a link points at: the page itself, the account (site + username) and, for a personal site, its domain."""
    out = set()
    if not url:
        return out
    out.add(("url", store.norm_url(url)))
    m = patterns.match(url)
    if m:
        out.add(("acct", f"{m[1]}:{m[2].lower()}"))
    d = _domain(url)
    if d:
        out.add(("dom", d))
    return out


def site_of(f) -> str:
    if f.get("url"):
        m = patterns.match(f["url"])
        if m:
            return m[0]
        return patterns.host_of(f["url"]) or f["title"]
    return f["tool"]


class Facts:
    """What one finding says: what it is (own keys) and what it points at (links, emails, names, pictures)."""

    def __init__(self, f):
        d, p = f["detail"] or {}, f.get("page") or {}
        self.f, self.id = f, f["id"]
        self.own = set()
        for u in (f.get("url"), p.get("final_url")):
            self.own |= {k for k in _keys(u) if k[0] != "dom" or f["kind"] == "website"}
        if d.get("verified_domain"):
            self.own.add(("dom", d["verified_domain"].lower()))
        self.ident = patterns.match(f["url"]) if f.get("url") else None
        links = []
        links += [(u, "rel_me") for u in p.get("rel_me") or []]
        links += [(u, "link") for u in (p.get("links") or []) + _urls_in(p.get("same_as")) + _urls_in(d.get("links"))]
        for k in ("website", "blog", "profile_url"):
            if _web(d.get(k)):
                links.append((_web(d[k]), "website"))
        if d.get("twitter_username"):
            links.append((f"https://twitter.com/{d['twitter_username']}", "link"))
        for pr in d.get("proofs") or []:
            u = f"https://{pr.get('name')}" if pr.get("service") in ("dns", "generic_web_site", "web") and pr.get("name") else pr.get("url")
            if u:
                links.append((u, "proof"))
        if d.get("verified_domain"):
            links.append((f"https://{d['verified_domain']}", "handle"))
        self.links = []                    # [(url, how, keys)]
        self.targets = {}                  # key -> {hows}
        for u, how in links:
            ks = _keys(u) - self.own
            if not ks:
                continue
            self.links.append((u, how, ks))
            for k in ks:
                self.targets.setdefault(k, set()).add(how)
        mails = []
        for e in re.split(r"[,\s]+", str(d.get("email") or "")):
            if re.fullmatch(CHECK["email"], e) and "noreply" not in e:
                mails.append((e.lower(), "verified" if d.get("email_verified_by") else "listed"))
        self.emails = mails
        self.names = [n for n in (d.get("fullname"), d.get("name"), d.get("full_name"), p.get("name")) if isinstance(n, str) and len(fold(n)) > 2]
        self.pics = [u for u in (d.get("image"), d.get("photo"), p.get("image")) if isinstance(u, str) and u.startswith(("http://", "https://"))]


def analyse(sid):
    """Evidence chips per finding, the leads, and the link findings to keep. Cached until the case changes."""
    ver = store.version()
    hit = _memo.get(sid)
    if hit and hit[0] == ver:
        return hit[1]
    idents = store.identifiers(sid)
    F = [f for f in store.findings(sid, with_private=True) if not f["not_me"]]
    fps = store.fingerprints(sid)
    res = _analyse(idents, F, fps)
    _memo[sid] = (ver, res)
    return res


def _analyse(idents, F, fps):
    by_ident = {i["id"]: i for i in idents}
    known = {(i["kind"], store.lead_norm(i["kind"], i["value"])) for i in idents}
    id_emails = {i["value"].lower() for i in idents if i["kind"] == "email"}
    id_domains = {store.lead_norm("domain", i["value"]) for i in idents if i["kind"] == "domain"}
    id_names = {fold(i["value"]) for i in idents if i["kind"] == "name"}
    hashes = {}
    for e in id_emails:
        hashes[hashlib.md5(e.encode()).hexdigest()] = e
        hashes[hashlib.sha256(e.encode()).hexdigest()] = e
    seed_fps = {k: v["hash"] for k, v in fps.items() if k.startswith("picture:") and usable_fp(v["hash"])}

    facts = [Facts(f) for f in F]
    fid = {x.id: x for x in facts}
    anchors = [x for x in facts if x.f["confirmed"] or x.f["detail"].get("bound")]
    reason = {x.id: ("confirmed by you" if x.f["confirmed"] else x.f["detail"]["bound"]) for x in anchors}
    anchor_keys = set().union(*(x.own for x in anchors)) if anchors else set()
    anchor_keys |= {("dom", d) for d in id_domains} | {("acct", f"github.com:{i['value'].lower()}") for i in idents if i["kind"] == "github"}
    anchor_names = {fold(n) for x in anchors for n in x.names} | id_names
    anchor_sites = {d for x in anchors for _, how, ks in x.links if how == "website" for k, d in ks if k == "dom"} | id_domains

    def pic_fp(u):
        v = fps.get(u)
        return v["hash"] if v and usable_fp(v["hash"]) and not DEFAULT_PIC.search(u) else None

    anchor_fps = {}
    for a in anchors:
        for u in a.pics:
            if pic_fp(u):
                anchor_fps[u] = (pic_fp(u), a)

    def label(x):
        return f"{site_of(x.f)} ({reason[x.id]})" if x.id in reason else site_of(x.f)

    # ---- evidence chips ----
    evidence = {}
    for x in facts:
        chips = []
        if x.id in reason:
            chips.append({"code": "confirmed" if x.f["confirmed"] else "bound", "text": reason[x.id].capitalize()})
        for a in anchors:
            if a is x:
                continue
            x2a, a2x = set(x.targets) & a.own, set(a.targets) & x.own
            if x2a and a2x:
                relme = any("rel_me" in x.targets[k] for k in x2a) and any("rel_me" in a.targets[k] for k in a2x)
                chips.append({"code": "rel_me" if relme else "reciprocal", "text": ("Says rel=\"me\" both ways with " if relme else "Links both ways with ") + label(a),
                              "fid": a.id, "url": a.f.get("url")})
            elif a2x:
                how = " (Keybase proof)" if any("proof" in a.targets[k] for k in a2x) else ""
                chips.append({"code": "keybase_proof" if how else "linked_from", "text": f"Linked from {label(a)}{how}", "fid": a.id, "url": a.f.get("url")})
            elif x2a:
                chips.append({"code": "links_to", "text": f"Links to {label(a)}", "fid": a.id, "url": a.f.get("url")})
        for k in set(x.targets):
            if k[0] == "dom" and k[1] in id_domains and x.id not in reason:
                chips.append({"code": "links_to", "text": f"Links to {k[1]}, a domain in this case"})
        for e, _ in x.emails:
            if e in id_emails:
                chips.append({"code": "same_email", "text": f"Shows the address {e}, which is in this case"})
        if x.id not in reason:
            if any(fold(n) in anchor_names for n in x.names):
                chips.append({"code": "same_name", "text": "Same display name as " + ("a confirmed account" if anchors else "the name in this case") + ": " + x.names[0]})
            sites = {k[1] for _, how, ks in x.links if how == "website" for k in ks if k[0] == "dom"}
            if sites & anchor_sites and not any(c["code"] == "links_to" for c in chips):
                chips.append({"code": "same_website", "text": f"Same website as a confirmed account: {sorted(sites & anchor_sites)[0]}"})
            best = None
            for u in x.pics:
                h = pic_fp(u)
                if not h:
                    continue
                for su, sh in seed_fps.items():
                    dist = hamming(h, sh)
                    if dist <= SAME_PICTURE and (best is None or dist < best[0]):
                        best = (dist, "the picture file you uploaded", None)
                for au, (ah, a) in anchor_fps.items():
                    dist = hamming(h, ah)
                    if a is not x and dist <= SAME_PICTURE and (best is None or dist < best[0]):
                        best = (dist, label(a), a.id)
            if best:
                chips.append({"code": "same_picture", "distance": best[0], "fid": best[2],
                              "text": f"Same picture as {best[1]} ({best[0]} of 64 bits differ{', identical' if best[0] == 0 else ''})"})
        for u in x.pics:
            for h, e in hashes.items():
                if h in u.lower():
                    chips.append({"code": "same_gravatar", "text": f"Its picture is the Gravatar of {e} (same address hash)"})
                    break
        if chips:
            evidence[x.id] = chips

    # ---- leads ----
    leads = {}

    def add(kind, value, strong, hop, text, url=None, src=None):
        value = (value or "").strip()
        if kind == "domain":
            value = store.lead_norm("domain", value)
        if kind == "email":
            value = value.lower()
        if not re.fullmatch(CHECK[kind], value) or (kind, store.lead_norm(kind, value)) in known:
            return
        e = leads.setdefault((kind, store.lead_norm(kind, value)), {"kind": kind, "value": value, "strength": "weak", "hop": hop, "evidence": []})
        if strong:
            e["strength"] = "strong"
        e["hop"] = min(e["hop"], hop)
        ev = {"text": text, "strong": bool(strong), "url": url, "fid": src}
        if not any(x["text"] == ev["text"] for x in e["evidence"]) and len(e["evidence"]) < 8:
            e["evidence"].append(ev)

    def hop_of(x):
        return (by_ident.get(x.f["identifier"]) or {}).get("hop", 0) + 1

    owners = {}                                        # key -> facts of findings that are that page or account
    for x in facts:
        for k in x.own:
            owners.setdefault(k, []).append(x)

    link_findings = {}
    for a in anchors:
        for u, how, ks in a.links:
            ys = [y for k in ks for y in owners.get(k, []) if y is not a]
            back = [y for y in ys if set(y.targets) & (anchor_keys | a.own)]
            relme = how == "rel_me" and any("rel_me" in hw for y in back for k, hw in y.targets.items() if k in anchor_keys | a.own)
            strong = bool(back) or how == "proof"
            if how == "proof":
                tail = ": a Keybase proof, a statement signed with the account's key"
            elif back:
                tail = " and that page links back" + (' (rel="me" both ways)' if relme else "")
            else:
                tail = (", one way: that page does not link back" if any(y.f.get("page") for y in ys) else ", one way so far: that page has not been read")
            m = patterns.match(u)
            if m:
                kind = "github" if m[1] == "github.com" else "username"
                add(kind, m[2], strong, hop_of(a), f"{label(a)} links to the {m[0]} account {m[2]}{tail}", u, a.id)
                if not ys and how != "proof":
                    link_findings.setdefault(a.f["identifier"], []).append(_link_finding(u, m[0], f"{m[1]}:{m[2].lower()}", f"{m[0]} profile {m[2]}", label(a)))
            else:
                d = _domain(u)
                if d:
                    add("domain", d, strong, hop_of(a), f"{label(a)} links to the website {d}{tail}", u, a.id)
                    if not ys and how != "handle":
                        link_findings.setdefault(a.f["identifier"], []).append(_link_finding(u, "Website", "site:" + d, f"Website {d}", label(a), kind="website"))
        for e, how in a.emails:
            add("email", e, how == "verified", hop_of(a), f"{label(a)} shows the address {e}" +
                (f"; verified by {a.f['detail']['email_verified_by']}" if how == "verified" else ", as the account itself states"), a.f.get("url"), a.id)
        for n in a.names:
            if fold(n) not in id_names:
                add("name", n, False, hop_of(a), f"{label(a)} shows the name “{n}”", a.f.get("url"), a.id)

    for x in facts:
        f, d, ident = x.f, x.f["detail"], by_ident.get(x.f["identifier"]) or {}
        if f["tool"] == "GitHub" and f["kind"] == "email" and d.get("address") and ident.get("kind") == "github":
            add("email", d["address"], True, hop_of(x), f"The address is in public commits of the GitHub account {d.get('via_account') or ident.get('value')}, "
                "which is in this case", f.get("url"), x.id)
        if f["tool"] == "GitHub" and f["kind"] == "code" and d.get("account") and ident.get("kind") == "email":
            add("github", d["account"], True, hop_of(x), f"GitHub attributes commits by {ident['value']} in {f['key'][5:]} to the account {d['account']}; "
                "GitHub does that only for an address verified on that account", f.get("url"), x.id)
        if f["tool"] == "OpenPGP key server":
            for e in d.get("other_addresses") or []:
                add("email", e, True, hop_of(x), f"On the same PGP key as {ident.get('value')}; keys.openpgp.org publishes an address only after its owner confirmed it",
                    f.get("url"), x.id)
            for n in d.get("names") or []:
                if fold(n) not in id_names:
                    add("name", n, False, hop_of(x), f"The name on the PGP key of {ident.get('value')}", f.get("url"), x.id)
        if f["tool"] == "Keybase" and x not in anchors:
            tied = [k for k in x.targets if k in anchor_keys and "proof" in x.targets[k]]
            if tied:
                for u, how, ks in x.links:
                    if how != "proof" or ks & anchor_keys:
                        continue
                    m = patterns.match(u)
                    if m:
                        add("github" if m[1] == "github.com" else "username", m[2], True, hop_of(x),
                            f"Keybase {f['title'][8:]} proved control of an account in this case and also of the {m[0]} account {m[2]}", u, x.id)
                    elif _domain(u):
                        add("domain", _domain(u), True, hop_of(x), f"Keybase {f['title'][8:]} proved control of an account in this case and also of {_domain(u)}", u, x.id)
        if f["tool"] in SEARCH_TOOLS and f.get("url"):
            m = patterns.match(f["url"])
            if m:
                add("github" if m[1] == "github.com" else "username", m[2], False, hop_of(x),
                    f"A search ({f['tool']}{': ' + d['query'] if d.get('query') else ''}) returned this {m[0]} profile; namesakes are common", f["url"], x.id)
        if x.id in reason or not x.ident:
            continue
        strong_chips = [c for c in evidence.get(x.id, []) if c["code"] in ("reciprocal", "rel_me", "keybase_proof") or (c["code"] == "same_picture" and c["distance"] == 0)]
        if strong_chips:
            add("github" if x.ident[1] == "github.com" else "username", x.ident[2], True, hop_of(x),
                f"The {x.ident[0]} account {x.ident[2]}: " + "; ".join(c["text"] for c in strong_chips[:3]), f.get("url"), x.id)
    return {"evidence": evidence, "leads": list(leads.values()), "link_findings": link_findings,
            "anchors": {x.id: reason[x.id] for x in anchors}}


def _link_finding(url, site, key, title, source, kind="account"):
    return {"tool": "Links between pages", "kind": kind, "key": key, "title": title, "url": url,
            "detail": {"linked_from": source, "what": f"{source} links to this page. Opened by the page reader to see whether it links back."}}


def update(sid):
    """Re-derive leads and link findings after a scan step, a confirmation or new picture fingerprints."""
    res = analyse(sid)
    store.upsert_leads(sid, res["leads"])
    now = __import__("time").time()
    for i in store.identifiers(sid):
        store.save_findings(i["id"], ["Links between pages"], res["link_findings"].get(i["id"], []), now)
    return analyse(sid)


# ---- the timeline: dated facts only, the same list for the page and the printed case file ----

def timeline(sid):
    F = [f for f in store.findings(sid) if not f["not_me"]]
    ev = []

    def add(date, what, src, url, f):
        t = str(date or "")[:10]
        if re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", t):
            ev.append({"t": t, "what": what, "src": src, "url": url, "fid": f["id"], "confirmed": bool(f["confirmed"] or f["detail"].get("bound"))})

    for f in F:
        d, p, site = f["detail"] or {}, f.get("page") or {}, site_of(f)
        if f["kind"] == "breach":
            add(d.get("year"), f"The address appears in the {f['title']} breach", "XposedOrNot", f.get("url"), f)
            continue
        if f["kind"] == "exposure":
            for i in d.get("infections") or []:
                add(i.get("date"), "A computer using the address was infected by password-stealing malware", "Hudson Rock", f.get("url"), f)
            continue
        if f["kind"] == "registration":
            add(d.get("registered"), f"Domain registered ({f['title'].replace('Registration record of ', '')})", "Domain registry", f.get("url"), f)
            continue
        add(d.get("created_at"), f"{site} account created", f["tool"], f.get("url"), f)
        add(p.get("created"), f"{site} profile created, as the page states", site, f.get("url"), f)
        add(d.get("latest_activity_at"), f"Latest activity on {site}", f["tool"], f.get("url"), f)
        first = (f.get("history") or {}).get("first") or (f.get("archive") or {}).get("first")
        add(first, f"Earliest archived copy of the {site} page", "Internet Archive",
            (f.get("history") or {}).get("first_url") or (f.get("archive") or {}).get("snapshot"), f)
        if (f.get("history") or {}).get("last") and f["history"]["last"] != first:
            add(f["history"]["last"], f"Newest archived copy of the {site} page", "Internet Archive", f["history"].get("last_url"), f)
    ev.sort(key=lambda e: e["t"])
    return ev
