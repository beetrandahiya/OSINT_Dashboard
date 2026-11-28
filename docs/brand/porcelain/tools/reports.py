"""Two printed documents in the Porcelain language, from real answers fetched on 28 Nov 2026:
the Connections report (GLEIF, Wikidata, OpenSanctions via our connections package, 12:36 UTC) and an Investigate case
file built on reserved test identifiers (RFC 2606) checked at 12:38 UTC: XposedOrNot, Hudson Rock Cavalier, Gravatar,
RDAP, crt.sh."""
import json, html
import porcelain as P
HERE = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/lang"
esc = lambda s: html.escape(str(s), quote=True)
R = json.load(open(f"{HERE}/rosneft.json"))
X = json.load(open(f"{HERE}/case/xon2.json")); HR = json.load(open(f"{HERE}/case/hr.json")); RD = json.load(open(f"{HERE}/case/rdap.json"))


def head(kind, sub, wm):
    icon = P.flat_svg("light", "doc" + kind[:2]).replace("<svg ", '<svg width="26" height="26" ', 1)
    d, vb, w, h = wm
    return (f'<div class="dh"><span class="db">{icon}<svg viewBox="{vb}" width="{w * .82:.0f}" height="{h * .82:.1f}" aria-label="World Watch"><path d="{d}" fill="#010101"/></svg></span>'
            f'<span class="dk"><b>{kind}</b><span>{sub}</span></span></div>')


def fact(child, label):
    for f in child["facts"]:
        if f["label"] == label: return f["value"]
    return ""


def connections(wm):
    c = R["child"]; p = R["parents"][0]; s = p["sanctions"][0]
    lists = "".join(f"<li>{esc(x)}</li>" for x in s["lists"])
    def facts(n, keys):
        rows = [f for f in n["facts"] if f["label"] in keys]
        return "".join(f'<tr><th>{esc(f["label"])}</th><td class="{"mono" if f["label"] in ("LEI", "Register number", "Legal form") else "num" if f["label"].startswith("Founded") else ""}">{esc(f["value"])}</td><td class="srcc">{esc(f["source"])}</td></tr>' for f in rows)
    keys = ["Legal form", "Register number", "Registered in", "Status", "Founded (per GLEIF)"]
    hold = c["holdings"][0]
    return f'''<article class="a4 doc">
{head("Connections report", "Who owns it, from public registers", wm)}
<div class="dtitle"><div class="eyebrow">Subject</div><h2>Rosneft Deutschland GmbH</h2>
<p class="dsub">Berlin, Germany · LEI <span class="mono">391200PKEUF3Y2NUMW25</span> · register <span class="mono">HRB 184025</span> · active since 23 Feb 2016</p></div>
<div class="dfacts"><div><b>1</b><span>owner found, one level up</span></div><div><b>8</b><span>OpenSanctions lists name that owner, matched by its LEI</span></div><div><b>0</b><span>lists name the subject itself</span></div></div>
<div class="chain">
  <div class="node end"><span class="tag">Where the chain stops</span><b>PJSC Rosneft declares that no known person or company controls it.</b><span class="by">GLEIF reporting exception NO_KNOWN_PERSON, direct and ultimate</span></div>
  <div class="link dashed"></div>
  <div class="node"><span class="stamp s-red">Sanctioned by LEI</span><span class="tag">Owner · Russia</span><b>Rosneft</b>
    <span class="orig">{esc(fact(p, "Legal name"))}</span>
    <span class="small">LEI <span class="mono">253400JT3MQWNDKMJE44</span> · reg. <span class="mono">1027700043502</span> · Moscow · since 6 Dec 1995</span></div>
  <div class="link tall"><span class="how">direct parent, consolidates its accounts <i>GLEIF</i><br>parent organisation; lists it as a subsidiary <i>Wikidata</i></span></div>
  <div class="node subj"><span class="tag">Subject · Germany</span><b>Rosneft Deutschland GmbH</b><span class="small">LEI <span class="mono">391200PKEUF3Y2NUMW25</span> · HRB <span class="mono">184025</span> · Berlin</span></div>
  <div class="link"><span class="how">owned by it <i>Wikidata</i></span></div>
  <div class="node hold"><span class="tag">Holding · Austria</span><b>{esc(hold["name"])}</b><span class="by">{esc(hold["desc"])}</span></div>
</div>
<div class="cols">
  <section><h4>Sanctions</h4><p>OpenSanctions entity <span class="mono">{esc(s["id"])}</span>, listed since {s["since"][8:10].lstrip("0")} Apr {s["since"][:4]}, matched on LEI 253400JT3MQWNDKMJE44:</p><ul class="lists">{lists}</ul></section>
  <section><h4>Rosneft's other holdings</h4><p>GLEIF lists {p["holdings_total"]["GLEIF"]} direct subsidiaries with an LEI: “RN-Capital” LLC (Russia) and Rosneft Deutschland GmbH. Wikidata lists {p["holdings_total"]["Wikidata"]}; they are missing here because Wikidata refused the request.</p>
  <h4>Did not answer</h4><p class="prob">Wikidata (HTTP 429, four times) for PJSC Rosneft: its Wikidata facts and holdings are not in this report.</p></section>
</div>
<div class="dfoot"><span>Compiled 28 Nov 2026 12:36 UTC from GLEIF (CC0), Wikidata (CC0) and OpenSanctions (CC BY-NC 4.0). Nothing is inferred: every line names its source.</span><span class="mono">1 / 1</span></div>
</article>'''


def bars():
    y = X["BreachMetrics"]["yearwise_details"][0]
    ys = [(int(k[1:]), v) for k, v in y.items() if int(k[1:]) >= 2009]
    mx = max(v for _, v in ys); W, H = 300, 74; bw = W / len(ys)
    o = [f'<svg viewBox="0 0 {W} {H + 16}" width="100%" class="bars" role="img" aria-label="Breaches by year the data was exposed, 2009 to 2026">']
    for i, (yr, v) in enumerate(ys):
        h = H * v / mx; x = i * bw
        o.append(f'<rect x="{x + 1.5:.1f}" y="{H - h:.1f}" width="{bw - 3:.1f}" height="{h:.1f}" rx="1" fill="#010101" fill-opacity="{1 if yr == 2026 else .78}"/>')
        if yr in (2009, 2014, 2019, 2026):
            anc, tx = ("start", x + 1.5) if yr == 2009 else ("end", x + bw - 1.5) if yr == 2026 else ("middle", x + bw / 2)
            o.append(f'<text x="{tx:.1f}" y="{H + 12}" text-anchor="{anc}">{yr}</text>')
    o.append(f'<text x="{W - bw / 2:.1f}" y="{H - H * ys[-1][1] / mx - 4:.1f}" text-anchor="middle" class="v">{ys[-1][1]}</text></svg>')
    return "".join(o)


def casefile(wm):
    ex = X["ExposedBreaches"]["breaches_details"]
    big = sorted(ex, key=lambda r: -int(r["xposed_records"] or 0))[:5]
    rows = "".join(f'<tr><td>{esc(r["breach"])}</td><td class="num">{r["xposed_date"]}</td><td class="num r">{int(r["xposed_records"]):,}</td><td>{esc(r["xposed_data"].replace(";", ", "))}</td></tr>' for r in big)
    newest = sorted(ex, key=lambda r: r.get("added") or "", reverse=True)[:3]
    nrows = ", ".join(f'{esc(r["breach"])} ({r["added"][8:10].lstrip("0")} {["", "Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(r["added"][5:7])]})' for r in newest)
    ev = {e["eventAction"]: e["eventDate"][:10] for e in RD["events"]}
    ns = ", ".join(n["ldhName"].lower() for n in RD["nameservers"])
    st = HR["stealers"]; days = sorted({s["date_compromised"][:10] for s in st})
    chips = "".join(f'<span class="chip">{c}</span>' for c in ["links both ways", "rel=me both ways", "verified email", "same picture file", "PGP or Keybase proof", "commit email"])
    return f'''<article class="a4 doc">
{head("Case file", "Investigate · findings only", wm)}
<span class="stamp s-red big">Specimen</span>
<div class="dtitle"><div class="eyebrow">Case 0</div><h2>Reserved test identifiers</h2>
<p class="dsub">Seeds: email <span class="mono">test@example.com</span> · domain <span class="mono">example.com</span> · checked 28 Nov 2026 12:38 UTC</p></div>
<section class="consent"><h4>Consent record</h4><p>Not needed for this specimen: both identifiers are reserved for testing (RFC 2606) and belong to no one. In a real case this block comes first and says who consented, when, how and to what scope. Without it no scan runs.</p></section>
<div class="dfacts"><div><b>{len(ex)}</b><span>breaches name the address</span></div><div><b>{len(st)}</b><span>infected computers had it saved</span></div><div><b>0</b><span>accounts: no username seed</span></div><div><b>1995</b><span>domain registered</span></div></div>
<div class="cols">
  <section><h4>Breaches by year the data leaked</h4>{bars()}<p class="small">XposedOrNot. Breach names and data types only; no records are downloaded. Newest added: {nrows}.</p></section>
  <section><h4>Info-stealer logs</h4><p>{len(st)} computers infected by info-stealer malware had this address saved; compromised {days[0][8:10].lstrip("0")}–{days[-1][8:10].lstrip("0")} Nov 2026 (Hudson Rock Cavalier). The saved logins are not shown.</p>
  <h4>Domain</h4><p>example.com: registered <span class="num">{ev["registration"]}</span>, expires <span class="num">{ev["expiration"]}</span>, registrar “RESERVED-Internet Assigned Numbers Authority”, name servers {esc(ns)} (RDAP).</p></section>
</div>
<table class="ft"><thead><tr><th>Largest breaches</th><th>Year</th><th class="r">Records</th><th>Data types</th></tr></thead><tbody>{rows}</tbody></table>
<section class="acc"><h4>Accounts by evidence</h4><p>None. Accounts are found from a username or a confirmed profile; this case has neither. Real cases list each account with the evidence that ties it to the subject, never a score:</p><div class="chips">{chips}</div></section>
<section><h4>Did not answer</h4><p class="prob">crt.sh (certificate search) returned an error page. Gravatar has no picture for the address.</p></section>
<div class="dfoot"><span>World Watch Investigate. Public sources only, on request. No passwords or leaked records, no face search, no location of a person.</span><span class="mono">1 / 1</span></div>
</article>'''
