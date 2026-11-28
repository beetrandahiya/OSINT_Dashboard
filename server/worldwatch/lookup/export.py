"""A case written out: as JSON (everything stored, for keeping or another tool) and as a printable HTML case file.

The case file carries no scripts and loads nothing from elsewhere (its Content-Security-Policy forbids it).
It holds the consent record first, then identifiers, confirmed accounts with their evidence, the other
accounts, leads and decisions, exposure (breach names and kinds of data only), the dated timeline, and what
could not be checked. No coordinates and no breach contents appear, because none are stored.
"""
import html
import json
import time

from . import pivot, store

BOUNDARY = ("Public sources only. No face recognition, no face search, nothing that infers where a person lives, is or goes, "
            "no breach contents or passwords, no logged-in scraping. Every case needs its consent record.")


def data(sid) -> dict:
    s = store.subject(sid)
    an = pivot.analyse(sid)
    F = store.findings(sid)
    for f in F:
        f["evidence"] = an["evidence"].get(f["id"], [])
    return {"exported": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tool": "World Watch Investigate", "boundaries": BOUNDARY,
            "case": s, "identifiers": store.identifiers(sid), "findings": F, "leads": store.leads(sid), "timeline": pivot.timeline(sid),
            "scans": store.last_scan(sid), "checks_run": store.checks_run(sid)}


def _e(v) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def _a(url, text) -> str:
    return f'<a href="{_e(url)}">{_e(text)}</a>' if isinstance(url, str) and url.startswith(("http://", "https://")) else _e(text)


def _date(t) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else ""


CSS = """
body{font:13px/1.45 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Helvetica,Arial,sans-serif;color:#0b141b;margin:32px auto;max-width:900px;padding:0 24px}
h1{font:700 24px/1.2 "Space Grotesk",-apple-system,sans-serif;margin:0 0 4px}h2{font:600 16px/1.3 "Space Grotesk",-apple-system,sans-serif;margin:26px 0 8px;
padding-bottom:4px;border-bottom:1px solid #cfd6dc}h3{font-size:13px;margin:14px 0 4px;color:#3a4a56}
.soft{color:#55636e}table{width:100%;border-collapse:collapse;margin:4px 0}th{text-align:left;font-weight:600;color:#3a4a56;padding:4px 8px 4px 0;font-size:12px}
td{padding:5px 8px 5px 0;border-top:1px solid #e3e8ec;vertical-align:top}a{color:#0a6d99}.chip{display:inline-block;margin:1px 4px 1px 0;padding:0 7px;border-radius:9px;
background:#eef3f6;font-size:11px}.strong{background:#dff3e8}.box{border:1px solid #cfd6dc;border-radius:10px;padding:10px 14px;margin:8px 0}
img.av{width:36px;height:36px;border-radius:8px;object-fit:cover;vertical-align:middle;margin-right:8px;background:#eef3f6}
@media print{body{margin:0;max-width:none}a{color:inherit;text-decoration:none}h2{break-after:avoid}tr{break-inside:avoid}}
"""


def case_file(sid) -> str:
    d = data(sid)
    s, F = d["case"], [f for f in d["findings"]]
    an = pivot.analyse(sid)
    accounts = [f for f in F if f["kind"] in ("account", "profile", "website") and f.get("url")]
    confirmed = [f for f in accounts if not f["not_me"] and (f["confirmed"] or f["detail"].get("bound"))]
    other = [f for f in accounts if not f["not_me"] and f not in confirmed]
    not_me = [f for f in accounts if f["not_me"]]
    fps = store.fingerprints(sid)

    def chips(f):
        return "".join(f'<span class="chip{" strong" if c["code"] in ("confirmed", "bound", "reciprocal", "rel_me", "keybase_proof") else ""}">{_e(c["text"])}</span>'
                       for c in an["evidence"].get(f["id"], []))

    def pic(f):
        u = f["detail"].get("image") or (f.get("page") or {}).get("image")
        if not (isinstance(u, str) and u.startswith(("http://", "https://"))):
            return ""
        return f'<img class="av" alt="" src="/api/lookup/img?s={sid}&amp;u={_e(__import__("urllib.parse").parse.quote(u, safe=""))}">'

    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><title>Case file: {_e(s['label'])}</title><style>{CSS}</style></head><body>"]
    out.append(f"<p class=soft>World Watch Investigate · case file · printed {_e(d['exported'])}</p><h1>{_e(s['label'])}</h1>")
    out.append(f"<div class=box><b>Consent</b>: {_e(store.HOW.get(s['consent_how'], s['consent_how'] or 'none recorded'))}"
               + ("" if s["is_self"] else f" given by {_e(s['consent_by'])} on {_e(s['consent_at'])}; scope: {_e(s['consent_scope'])}")
               + (f"<br><span class=soft>Note: {_e(s['note'])}</span>" if s.get("note") else "") + f"<br><span class=soft>{_e(BOUNDARY)}</span></div>")
    rows = "".join(f"<tr><td>{_e(store.KINDS.get(i['kind'], i['kind']))}</td><td>{_e((i.get('detail') or {}).get('name') or 'uploaded picture') if i['kind'] == 'picture' else _e(i['value'])}"
                   + (" <span class=soft>(this picture carries location metadata; it was not read)</span>" if (i.get("detail") or {}).get("location_meta") else "")
                   + f"</td><td>{'entered' if i['source'] == 'seed' else 'followed from a lead, step ' + str(i['hop'])}</td><td>{_e(_date(i.get('scanned'))) or 'not scanned'}</td></tr>"
                   for i in d["identifiers"])
    out.append(f"<h2>Identifiers ({len(d['identifiers'])})</h2><table><tr><th>Kind</th><th>Value</th><th>How</th><th>Last scanned</th></tr>{rows}</table>")

    def acc_rows(lst, with_chips=True):
        return "".join(f"<tr><td style='white-space:nowrap'>{pic(f)}{_a(f['url'], pivot.site_of(f))}</td><td>{_e(f['title'])}"
                       + (f"<br><span class=soft>{_e((f.get('page') or {}).get('description') or f['detail'].get('bio') or '')[:200]}</span>" if with_chips else "")
                       + f"</td><td>{chips(f) if with_chips else ''}</td><td class=soft>{_e(f['tool'])}</td></tr>" for f in lst)
    out.append(f"<h2>Confirmed accounts ({len(confirmed)})</h2>" + (f"<table><tr><th>Site</th><th>Page</th><th>Evidence</th><th>Found by</th></tr>{acc_rows(confirmed)}</table>"
                                                                    if confirmed else "<p class=soft>None confirmed yet.</p>"))
    if other:
        out.append(f"<h2>Other accounts found, not confirmed ({len(other)})</h2><p class=soft>Found under an identifier of the case; each may belong to someone else.</p>"
                   f"<table><tr><th>Site</th><th>Page</th><th>Evidence</th><th>Found by</th></tr>{acc_rows(other)}</table>")
    if not_me:
        out.append(f"<h3>Marked “not me” ({len(not_me)})</h3><p class=soft>" + ", ".join(_e(pivot.site_of(f)) for f in not_me) + "</p>")
    L = d["leads"]
    if L:
        state = {"new": "waiting", "followed": "followed automatically", "approved": "approved", "rejected": "rejected"}
        out.append(f"<h2>Leads ({len(L)})</h2><table><tr><th>Lead</th><th>Strength</th><th>State</th><th>Evidence</th></tr>" + "".join(
            f"<tr><td>{_e(store.KINDS.get(l['kind'], l['kind']))}: {_e(l['value'])}<br><span class=soft>step {l['hop']}</span></td><td>{_e(l['strength'])}</td>"
            f"<td>{_e(state.get(l['state'], l['state']))}</td><td>" + "<br>".join(_a(ev.get('url'), ev['text']) for ev in l["evidence"]) + "</td></tr>" for l in L) + "</table>")
    br = [f for f in F if f["kind"] == "breach" and not f["not_me"]]
    ex = [f for f in F if f["kind"] == "exposure" and not f["not_me"]]
    if br or ex:
        out.append("<h2>Exposure</h2><p class=soft>Breach names and the kinds of data that leaked, from XposedOrNot; malware records from Hudson Rock. No leaked data or passwords are downloaded or stored.</p>")
        if br:
            out.append("<table><tr><th>Breach</th><th>Year</th><th>Kinds of data</th></tr>" + "".join(
                f"<tr><td>{_e(f['title'])}</td><td>{_e(f['detail'].get('year'))}</td><td>{_e(str(f['detail'].get('leaked') or '').replace(';', ', '))}</td></tr>" for f in br) + "</table>")
        for f in ex:
            out.append(f"<p>{_e(f['detail'].get('what') or f['title'])}</p>")
    pics = [i for i in d["identifiers"] if i["kind"] == "picture"]
    if pics:
        out.append("<h2>Picture files</h2><p class=soft>Compared only as files (difference hash): “same picture” means a copy of the same file, never the same face.</p>"
                   + "".join(f"<p>{_e((i.get('detail') or {}).get('name') or i['value'][:16] + '…')} · fingerprint {_e((fps.get('picture:' + i['value']) or {}).get('hash') or 'not computed yet')}"
                             + (" · carries location metadata (not read)" if (i.get("detail") or {}).get("location_meta") else "") + "</p>" for i in pics))
    tl = d["timeline"]
    if tl:
        out.append("<h2>Timeline</h2><p class=soft>Only dated facts. Entries from accounts that are not confirmed are marked.</p><table>" + "".join(
            f"<tr><td style='width:96px'>{_e(e['t'])}</td><td>{_e(e['what'])}{'' if e['confirmed'] else ' <span class=soft>(not confirmed)</span>'}</td><td class=soft>{_a(e.get('url'), e['src'])}</td></tr>"
            for e in tl) + "</table>")
    probs = (d.get("scans") or {}).get("summary", {}).get("problems") or []
    if probs:
        out.append("<h2>What could not be checked in the last scan</h2><ul>" + "".join(f"<li>{_e(p)}</li>" for p in probs) + "</ul>")
    out.append(f"<p class=soft style='margin-top:30px'>Every finding names its source. Nothing here is scored: “evidence” lists the reasons stated by the sources.</p></body></html>")
    return "".join(out)


def as_json(sid) -> str:
    return json.dumps(data(sid), indent=1, ensure_ascii=False)
