"""Connections, 'their aircraft and ships now': two worked examples on real data fetched 28 Nov 2026 15:22-15:31 UTC.
Aircraft: adsb.fi (live positions) -> callsign code and register owner (adsbdb, hexdb.io) -> Wikidata ICAO codes of the
airlines in Deutsche Lufthansa AG's chain (GLEIF + Wikidata). Ships: Digitraffic AIS -> IMO -> Wikidata ship items with
owner / operator -> companies -> GLEIF parents."""
import json, math, datetime
from cam import Cam

A_DIR = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/assets"
AIRCAM = Cam(11.2, 42.0, 0.20, 11.2, 48.5, 1450, 920, 600)
SEACAM = Cam(22.5, 54.8, 0.17, 22.5, 59.4, 1450, 920, 600)
X0, X1, Y0, Y1 = 392, 1448, 62, 1064
WHITE, GREY, DIM, EDGE = "#fafafa", "#a1a1aa", "#71717a", "#09090b"
GLEIF_C, WD_C = "#7dd3fc", "#c4b5fd"
UTC = datetime.UTC


def hm(ts):
    return datetime.datetime.fromtimestamp(ts, UTC).strftime("%H:%M")


def gc_points(cam, a, b, n=40, lift=0.0):
    """Screen points along the great circle a -> b (lon, lat), slightly lifted in the middle so lines read as arcs."""
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    d = 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    if d < 1e-6: return [], 0
    out = []
    for i in range(n + 1):
        f = i / n; A = math.sin((1 - f) * d) / math.sin(d); B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        lat, lon = math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))
        out.append(cam.proj(lon, lat, lift * math.sin(math.pi * f) * min(1, d / .2)))
    return out, d * 6371


def path(pts):
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def inside(x, y, pad=0):
    return X0 + pad <= x <= X1 - pad and Y0 + pad <= y <= (Y1 if x > 1420 else 1000) - pad


def to_edge(cam, a, b, lift=.0):
    """Points of a -> b until the line leaves the free map area; returns (points, exit point or None, km)."""
    pts, km = gc_points(cam, a, b, 160, lift)
    keep = []
    for x, y, v in pts:
        if not v or not inside(x, y, 6):
            return keep, (keep[-1] if keep else None), km
        keep.append((x, y))
    return keep, None, km


def screen_rot(cam, lon, lat, hdg):
    """Heading in degrees turned into the rotation the symbol needs on this perspective view."""
    if hdg is None: return 0
    x0, y0, _ = cam.proj(lon, lat)
    d = .05
    x1, y1, _ = cam.proj(lon + d * math.sin(math.radians(hdg)) / max(.2, math.cos(math.radians(lat))), lat + d * math.cos(math.radians(hdg)))
    return math.degrees(math.atan2(x1 - x0, -(y1 - y0)))


def place_labels(cands, blocked, o, cls="pl"):
    """cands: (x, y, r, text, extra_cls). Greedy: right, left, below, above; skipped when nothing fits."""
    placed = blocked.setdefault("labels", []) if isinstance(blocked, dict) else []
    others = blocked.get("marks", []) if isinstance(blocked, dict) else blocked
    blocked = others
    for x, y, r, text, extra in cands:
        w = 6.9 * len(text)
        for x0, yy, anchor in ((x + r + 7, y + 4, "start"), (x - r - 7 - w, y + 4, "start"), (x - w / 2, y + r + 15, "start"), (x - w / 2, y - r - 7, "start"),
                               (x + r + 5, y - r - 4, "start"), (x - r - 5 - w, y - r - 4, "start"), (x + r + 5, y + r + 12, "start"), (x - r - 5 - w, y + r + 12, "start"),
                               (x + r + 7, y + 18, "start"), (x + r + 7, y - 10, "start"), (x - r - 7 - w, y + 18, "start"), (x - r - 7 - w, y - 10, "start")):
            b = (x0 - 3, yy - 13, x0 + w + 3, yy + 4)
            if b[0] < X0 + 4 or b[2] > X1 - 4 or b[1] < Y0 + 40 or b[3] > Y1 - 64: continue
            if any(not (b[2] < c[0] + 1 or b[0] > c[2] - 1 or b[3] < c[1] + 1 or b[1] > c[3] - 1) for c in placed + blocked): continue
            if b[0] < 1420 and b[3] > 1000: continue      # keep clear of the map tools along the bottom
            placed.append(b)
            o.append(f'<text x="{x0:.1f}" y="{yy:.1f}" class="{cls}{(" " + extra) if extra else ""}">{text}</text>')
            break
    return placed


def edge_mark(o, pt, text, col, up=False):
    x, y = pt
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{col}"/>')
    anchor = "end" if x > (X0 + X1) / 2 else "start"
    dx = -9 if anchor == "end" else 9
    dy = -8 if y > (Y0 + Y1) / 2 else 16
    o.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" class="pl em">{text}</text>')


# ============================== AIRCRAFT ==============================
AIR = json.load(open(f"{A_DIR}/air.json"))
NEAR = json.load(open(f"{A_DIR}/near.json"))
CO = AIR["companies"]
HQ_PLACE = {"Lufthansa": "Cologne", "Swiss International Air Lines": "Kloten", "Edelweiss Air": "Kloten", "Austrian Airlines": "Schwechat",
            "Air Dolomiti": "Villafranca", "Lufthansa CityLine": "Munich Airport", "Lufthansa City Airlines": "Munich Airport", "Eurowings": "Düsseldorf",
            "Brussels Airlines": "Brussels Airport", "Lufthansa Cargo": "Frankfurt", "Discover Airlines": "Frankfurt Airport", "Eurowings Europe": "Swieqi, Malta",
            "Helvetic Airways": "Kloten", "AirBaltic": "Mārupe, Latvia", "ITA Airways": "Rome", "SunExpress": "Antalya"}
SHORT = {"Swiss International Air Lines": "Swiss", "Lufthansa City Airlines": "Lufthansa City", "Lufthansa CityLine": "CityLine", "Austrian Airlines": "Austrian",
         "Brussels Airlines": "Brussels", "Lufthansa Cargo": "Lufthansa Cargo", "Discover Airlines": "Discover", "Edelweiss Air": "Edelweiss", "Air Dolomiti": "Air Dolomiti"}
SEL_HEX = "502d88"   # SWR868L, YL-ABT: Swiss flight number, registered to airBaltic


def air_rows():
    rows = [r for r in AIR["rows"] if r["lon"] is not None]
    linked = [r for r in rows if r["owner_group"] or r["op_group"]]
    ita = []                 # ITA Airways is in the chain (Wikidata lists it under Lufthansa): nothing is left aside now
    return rows, linked, ita


def air_counts():
    rows, linked, ita = air_rows()
    own = [r for r in linked if r["owner_group"]]
    out = [r for r in linked if not r["owner_group"] and r["owner"]]
    unk = [r for r in linked if not r["owner"]]
    looked = len(linked) + len(ita)
    known = sum(1 for r in linked + ita if r["owner"])
    by_src = {}
    for r in linked + ita:
        if r["owner"]: by_src[r["src"]] = by_src.get(r["src"], 0) + 1
    return dict(total=AIR["total"], linked=linked, own=own, out=out, unk=unk, ita=ita, looked=looked, known=known, by_src=by_src,
                byname=sum(1 for r in own if r["how"] == "owner name"))


def air_svg():
    from glyph import svg as gsvg, for_type
    rows, linked, ita = air_rows()
    cam = AIRCAM
    o = [f'<svg class="mk" viewBox="0 0 1920 1080" width="1920" height="1080" aria-hidden="true">']
    # every other aircraft in view, faint
    mine = {r["hex"] for r in rows}
    o.append('<g fill="#e4e4e7" fill-opacity=".28">')
    for a in NEAR["ac"]:
        if a.get("lat") is None or a["hex"] in mine: continue
        x, y, v = cam.proj(a["lon"], a["lat"])
        if v and inside(x, y): o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5"/>')
    o.append("</g>")
    # company headquarters
    hqs = {}
    for r in linked:
        q = r["owner_q"] if r["owner_group"] else r["op"]
        hqs.setdefault(q, []).append(r)
    lines_solid, lines_dash, edges = [], [], []
    for r in linked:
        q = r["owner_q"] if r["owner_group"] else r["op"]
        hq = CO[q]["hq"]
        pts, ex, km = to_edge(cam, (r["lon"], r["lat"]), hq, .002)
        sel = r["hex"] == SEL_HEX
        d = path(pts) if len(pts) > 1 else ""
        if not d: continue
        if r["owner_group"]: lines_solid.append(d)
        else: lines_dash.append((d, sel))
        if ex: edges.append((ex, q, km))
    o.append(f'<g fill="none" stroke="{WHITE}" stroke-opacity=".26" stroke-width=".9">' + "".join(f'<path d="{d}"/>' for d in lines_solid) + "</g>")
    o.append(f'<g fill="none" stroke="{WHITE}" stroke-dasharray="4 4">' + "".join(f'<path d="{d}" stroke-opacity="{.95 if s else .5}" stroke-width="{1.6 if s else 1}"/>' for d, s in lines_dash) + "</g>")
    # the selected aircraft's owner, outside the group: a grey line to the edge, toward Latvia
    sel = next(r for r in rows if r["hex"] == SEL_HEX)
    pts, ex, km = to_edge(cam, (sel["lon"], sel["lat"]), CO["Q300924"]["hq"], .002)
    o.append(f'<path d="{path(pts)}" fill="none" stroke="{GREY}" stroke-width="1.6" stroke-opacity=".95"/>')
    if ex: edge_mark(o, ex, f"Mārupe, Latvia · Air Baltic, its registered owner · {km:,.0f} km", GREY)
    else:
        x, y = pts[-1]
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7.5" fill="{EDGE}" fill-opacity=".7"/><circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{GREY}"/>'
                 f'<text x="{x - 12:.1f}" y="{y + 18:.1f}" text-anchor="end" class="pl em">Mārupe · Air Baltic, registered owner, outside the group</text>')
    # Malta etc.: edge marks for headquarters out of view
    seen = set()
    for (x, y), q, km in edges:
        if q in seen: continue
        seen.add(q); n = len(hqs[q])
        edge_mark(o, (x, y), f"{HQ_PLACE.get(CO[q]['name'])} · {CO[q]['name']} · {n} aircraft", WHITE)
    # HQ dots
    groups = {}
    for q, rs in hqs.items():
        lo, la = CO[q]["hq"]
        x, y, v = cam.proj(lo, la)
        if not (v and inside(x, y)): continue
        groups.setdefault((round(x / 6), round(y / 6)), []).append((q, rs, x, y))
    blocked, cands = [], []
    for key, g in sorted(groups.items(), key=lambda kv: -sum(len(rs) for _, rs, _, _ in kv[1])):
        x, y = g[0][2], g[0][3]; n = sum(len(rs) for _, rs, _, _ in g)
        rad = 5 + 1.9 * math.sqrt(n)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 2.5:.1f}" fill="{EDGE}" fill-opacity=".7"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{WHITE}"/>'
                 f'<text x="{x:.1f}" y="{y + 3.7:.1f}" text-anchor="middle" class="cn">{n}</text>')
        blocked.append((x - rad - 3, y - rad - 3, x + rad + 3, y + rad + 3))
        names = " + ".join(SHORT.get(CO[q]["name"], CO[q]["name"]) for q, _, _, _ in sorted(g, key=lambda t: -len(t[1])))
        cands.append((x, y, rad, f"{HQ_PLACE.get(CO[g[0][0]]['name'], '')} · {names}", "hq"))
    # aircraft
    for r in sorted(linked + ita, key=lambda r: (r["hex"] == SEL_HEX, r["owner_group"])):
        x, y, v = cam.proj(r["lon"], r["lat"])
        if not (v and inside(x, y)): continue
        col = WHITE if r["owner_group"] else ("#d4d4d8" if r["op_group"] else DIM)
        rot = screen_rot(cam, r["lon"], r["lat"], r["trk"])
        o.append(gsvg(for_type(r["type"], military=False), x, y, 22 if r["hex"] == SEL_HEX else 18, col, EDGE, rot=rot, edge_w=6))
        blocked.append((x - 9, y - 9, x + 9, y + 9))
        if r["hex"] == SEL_HEX:
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="20" fill="none" stroke="{EDGE}" stroke-width="4" stroke-opacity=".8"/>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="20" fill="none" stroke="{WHITE}" stroke-width="1.5"/>')
            cands.insert(0, (x, y, 20, f"{r['cs']} · flies as Swiss · owner Air Baltic", "sel"))
        elif r in ita:
            cands.append((x, y, 9, f"{r['cs']} · ITA Airways, not linked", "cs2 off"))
        elif not r["owner_group"] and r["owner"]:
            cands.append((x, y, 9, f"{r['cs']} · owner {r['owner']}", "cs2"))
        elif r["op"] in ("Q108251249", "Q1137136"):
            cands.append((x, y, 9, f"{r['cs']} · " + ("ITA Airways, Wikidata disagrees" if r["op"] == "Q108251249" else "SunExpress, two owners in Wikidata"), "cs2"))
    hqc = [c for c in cands if c[4] == "hq"]; acc = [c for c in cands if c[4] != "hq"]
    marks = [b for b in blocked if b[2] - b[0] > 19]                 # headquarters dots only
    lab = {"marks": marks}
    place_labels([c for c in acc if c[4] == "sel"], lab, o)
    place_labels(hqc, lab, o)
    lab["marks"] = blocked
    place_labels([c for c in acc if c[4] != "sel"], lab, o)
    o.append("</svg>")
    return "".join(o)


def air_left(S):
    c = air_counts()
    esc = S.esc
    codes = {}
    for r in c["linked"]:
        if r["op_group"]: codes[r["cs"][:3]] = codes.get(r["cs"][:3], 0) + 1
    code_s = ", ".join(f"{k} {v}" for k, v in sorted(codes.items(), key=lambda kv: -kv[1]))
    nflight = sum(codes.values())
    bare = len(c["linked"]) - nflight
    hel = sum(1 for r in c["out"] if r["owner"] == "Helvetic Airways"); bal = sum(1 for r in c["out"] if r["owner"] == "Air Baltic")
    steps = [
        ("552", f"aircraft within 250 NM of Munich", f"adsb.fi · {hm(AIR['now'])} UTC"),
        (str(nflight), f"call themselves by a group airline's code: {code_s}", "callsign = the airline's ICAO code in Wikidata"),
        (f"{c['known']}<small>/{c['looked']}</small>", "registered owner found (these and 2 bare “SWR” callsigns)",
         f"adsbdb {c['by_src'].get('adsbdb', 0)}, hexdb.io {c['by_src'].get('hexdb.io', 0)}, by transponder address"),
        (str(len(c["own"])), "registered to a group company: solid line",
         f"owner's airline code ({len(c['own']) - c['byname']}) or exact name ({c['byname']})"),
        (str(len(c["out"]) + len(c["unk"])), f"group flight numbers, owner outside the group ({hel} Helvetic, {bal} Air Baltic, {len(c['out']) - hel - bal} Alitalia) or not listed ({len(c['unk'])})",
         "dashed: linked by flight number only"),
    ]
    st = "".join(f'<div class="stp"><b class="num">{n}</b><div><span>{esc(t) if "<" not in t else t}</span><small>{esc(s)}</small></div></div>' for n, t, s in steps)
    # by company
    per = {}
    for r in c["linked"]:
        if r["owner_group"]: per.setdefault(r["owner_q"], [0, 0])[0] += 1
        if r["op_group"]: per.setdefault(r["op"], [0, 0])[1] += 1
    trs = "".join(f'<tr><td>{esc(CO[q]["name"])}</td><td class="r num">{a or "–"}</td><td class="r num">{b or "–"}</td></tr>'
                  for q, (a, b) in sorted(per.items(), key=lambda kv: -(kv[1][0] + kv[1][1])))
    return (f'<section class="pnl res"><div class="ph"><b>Their aircraft now</b><span>{len(c["linked"])} linked</span><span class="src">{hm(AIR["now"])} UTC</span></div>{st}</section>'
            f'<section class="pnl res"><div class="ph"><b>By company</b><span>in the chain, with aircraft in view</span></div>'
            f'<table class="dt fx co"><colgroup><col><col style="width:62px"><col style="width:62px"></colgroup><thead><tr><th>Company</th><th class="r">Owns</th><th class="r">Flies</th></tr></thead><tbody>{trs}</tbody></table>'
            f'<div class="ph2">Where the registers disagree</div><p class="small"><b>ITA Airways</b>: Lufthansa’s Wikidata item lists it as a subsidiary, its own item names the Italian government. '
            f'<b>SunExpress</b>: Wikidata names Lufthansa and Turkish Airlines as owners. Both linked, flagged on their cards.</p>'
            f'<p class="hint">The other {c["total"] - len(c["linked"])} aircraft were not looked up here; the app would, in the background.</p></section>')


def air_right(S):
    esc = S.esc
    sel = next(r for r in AIR["rows"] if r["hex"] == SEL_HEX)
    alt = f'{sel["alt"]:,} ft' if isinstance(sel["alt"], int) else str(sel["alt"])
    card = f'''<section class="pnl ent selac"><div class="eh"><span class="tag2">Aircraft · selected</span><h3>{esc(sel["cs"])}</h3>
<p>Airbus Canada A220-300 · {esc(sel["reg"])} (Latvia) · {alt} · {sel["gs"]:.0f} kt</p></div>
<div class="lk"><i class="ln dash"></i><div><b>Flies as Swiss International Air Lines</b><small>callsign code SWR = Swiss's ICAO code in Wikidata · Swiss is a GLEIF subsidiary of Deutsche Lufthansa AG</small></div></div>
<div class="lk"><i class="ln grey"></i><div><b>Registered to Air Baltic</b><small>adsbdb register, owner code BTI · Air Baltic Corporation is not in the chain: GLEIF records no parent (“no known person”), Wikidata gives the Government of Latvia as owner</small></div></div>
<p class="hint" style="margin-top:8px">So the line to Swiss is dashed: it is Swiss's flight, but not Swiss's aircraft.</p>
<div class="actions"><span class="btn ink">Follow it on the map</span><span class="btn">Open Air Baltic in Connections</span></div></section>'''
    subj = f'''<section class="pnl ent"><div class="eh"><span class="tag2">Company · Germany</span><h3>Deutsche Lufthansa AG</h3><p>LEI 529900PH63HYJ86ASW55 · Wikidata “Lufthansa” carries the same LEI</p></div>
<div class="kv"><div><b class="num">{AIR["gleif_children"]}</b><span>companies under it in GLEIF</span></div><div><b class="num">{sum(1 for c in CO.values() if c["group"])}</b><span>airlines in its chain, by ICAO code</span></div><div><b class="num">{len(air_rows()[1])}</b><span>of their aircraft in view now</span></div></div>
<div class="ph2">How an aircraft is linked <span>in this order</span></div>
<table class="dt ft2 how"><tbody>
<tr><th>Registered owner</th><td>the owner's airline code in the register (adsbdb, else hexdb.io) equals a chain airline's ICAO code; else its exact name</td><td class="sc">solid</td></tr>
<tr><th>Flight number</th><td>the callsign starts with a chain airline's ICAO code followed by digits</td><td class="sc">dashed</td></tr>
<tr><th>Never</th><td>similar names, the aircraft's paint, its route or airport</td><td class="sc">—</td></tr></tbody></table>
<div class="ph2">What a link means</div><p class="small">A register lists who an aircraft is registered to. That can be a leasing company or a sister airline, and the free registers are compiled by volunteers from national registers, so some entries are old. Each card shows the register's own words beside the match.</p>
<div class="src">adsb.fi {hm(AIR["now"])} · adsbdb, hexdb.io 15:25 · GLEIF 15:26 · Wikidata 15:27 UTC</div></section>'''
    return card + subj


def air_board(S, t):
    body = (air_svg() + S.topbar(t, "Connections", 'Who owns what <b>Deutsche Lufthansa AG</b>' + S.mode_seg("map") + '<span class="chip on">Their aircraft and ships now</span>', "Lufthansa")
            + f'<aside class="lcol">{air_left(S)}</aside><aside class="col">{air_right(S)}</aside>'
            + '<div class="gtools"><span class="btn">Fit</span><span class="btn">+</span><span class="btn">−</span><span class="leg">'
            + '<span><i class="dotw"></i>headquarters · number = aircraft</span><span><i class="ln wl"></i>registered owner</span><span><i class="ln wd"></i>flight number only</span>'
            + '<span><i class="ln go"></i>owner outside the group</span><span><i class="dotf"></i>other aircraft</span></span></div>')
    return S.board("connections-air", t, S.IMG["s-air"], body)


# ============================== SHIPS ==============================
SEA = json.load(open(f"{A_DIR}/sea.json"))
SCO = SEA["companies"]
FIN = "Q1418246"
DT_TIME = datetime.datetime.fromisoformat(SEA["data_time"].replace("Z", "+00:00")).timestamp()
LAG = (SEA["now"] - DT_TIME) / 60          # minutes between Digitraffic's update time and the moment ages were computed
GRIM = next(r for r in SEA["gleif"]["Finnlines"] if r["lei"] == "7437006VBPTLWEHRP329")
PALERMO = (13.3614, 38.1157)
SHIPKEY = lambda t: ("passenger" if 60 <= (t or 0) <= 69 else "cargo" if 70 <= (t or 0) <= 79 else "tanker_s" if 80 <= (t or 0) <= 89 else
                     "hsc" if 40 <= (t or 0) <= 49 else "tug" if t in (31, 32, 52) else "warship_s" if t == 35 else "fishing" if t == 30 else
                     "sar" if t == 51 else "sailing" if t == 36 else "pleasure" if t == 37 else "cargo")


def age_min(s):
    return max(0.0, s["age"] - LAG)


def ago_s(m):
    return "under 1 min" if m < 1 else f"{m:.0f} min" if m < 90 else f"{m / 60:.0f} h"


def sea_counts():
    sh = SEA["ships"]
    imo = [s for s in sh if s["imo"] and len(str(s["imo"])) == 7]
    linked = [s for s in sh if s["links"]]
    comps = {}
    for s in linked:
        for k, q in s["links"]: comps.setdefault(q, []).append((s, k))
    return dict(pos=sum(1 for _ in SEA["ships"]), imo=len(imo), wd=sum(1 for s in imo if s["wd"]), linked=linked, comps=comps,
                fresh=sum(1 for s in sh if age_min(s) <= 60))


def sea_svg():
    cam = SEACAM
    c = sea_counts()
    o = [f'<svg class="mk" viewBox="0 0 1920 1080" width="1920" height="1080" aria-hidden="true">']
    for s in SEA["ships"]:
        if s["links"]: continue
        x, y, v = cam.proj(s["lon"], s["lat"])
        if v and inside(x, y):
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="#7dd3fc" fill-opacity="{.55 if age_min(s) <= 60 else .18}"/>')
    # ship -> company lines (Wikidata), company -> parent lines (Wikidata / GLEIF)
    lines, fin_lines, edges = [], [], {}
    def hq_in_view(q):
        hq = SCO[q]["hq"]
        if not hq: return False
        x, y, v = cam.proj(*hq)
        return v and inside(x, y)
    for s in c["linked"]:
        for k, q in s["links"]:
            hq = SCO[q]["hq"]
            if not hq or (not hq_in_view(q) and len(c["comps"][q]) < 2): continue
            pts, ex, km = to_edge(cam, (s["lon"], s["lat"]), hq, .002)
            if len(pts) < 2: continue
            d = path(pts)
            (fin_lines if q == FIN else lines).append((d, k))
            if ex: edges.setdefault(q, (ex, km, 0)); edges[q] = (edges[q][0], km, edges[q][2] + 1)
    o.append(f'<g fill="none" stroke="{WD_C}" stroke-width=".9">' + "".join(f'<path d="{d}" stroke-opacity=".38"{" stroke-dasharray=&quot;3 3&quot;" if k == "operator" else ""}/>' for d, k in lines) + "</g>")
    o.append(f'<g fill="none" stroke="{WD_C}" stroke-width="1.5">' + "".join(f'<path d="{d}" stroke-opacity=".95"{" stroke-dasharray=&quot;4 3&quot;" if k == "operator" else ""}/>' for d, k in fin_lines) + "</g>")
    # parent chains between companies
    def comp_line(qa, qb_hq, col, w=1.4, op=.9, label=None):
        pts, ex, km = to_edge(cam, SCO[qa]["hq"], qb_hq, .006)
        if len(pts) > 1: o.append(f'<path d="{path(pts)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}"/>')
        if ex and label: edge_mark(o, ex, label.format(km=km), col)
    comp_line(FIN, PALERMO, GLEIF_C, 1.8, 1, "Palermo · GRIMALDI GROUP S.P.A., Finnlines' parent in GLEIF · {km:,.0f} km")
    by_name = {v["name"]: k for k, v in SCO.items() if v["name"]}
    for child, parent in (("Silja Line", "Tallink"), ("Eckerö Line", "Rederiaktiebolaget Eckerö"), ("Birka Cruises", "Rederiaktiebolaget Eckerö")):
        if child in by_name and parent in by_name and SCO[by_name[parent]]["hq"]:
            comp_line(by_name[child], SCO[by_name[parent]]["hq"], WD_C, 1.2, .7)
    for q, (ex, km, n) in edges.items():
        if n >= 2: edge_mark(o, ex, f"{SCO[q]['hqname']} · {SCO[q]['name']} · {n} ships", WD_C)
    # company dots
    groups = {}
    for q, lst in c["comps"].items():
        hq = SCO[q]["hq"]
        if not hq: continue
        x, y, v = cam.proj(*hq)
        if not (v and inside(x, y)): continue
        groups.setdefault((round(x / 6), round(y / 6)), []).append((q, lst, x, y))
    blocked, cands = [], []
    for key, g in sorted(groups.items(), key=lambda kv: -sum(len(l) for _, l, _, _ in kv[1])):
        x, y = g[0][2], g[0][3]; n = sum(len(l) for _, l, _, _ in g)
        isfin = any(q == FIN for q, _, _, _ in g)
        rad = 4.5 + 1.9 * math.sqrt(n)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 2.5:.1f}" fill="{EDGE}" fill-opacity=".7"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{WHITE}"/>'
                 f'<text x="{x:.1f}" y="{y + 3.7:.1f}" text-anchor="middle" class="cn">{n}</text>')
        if isfin:
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 9:.1f}" fill="none" stroke="{EDGE}" stroke-width="4" stroke-opacity=".8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 9:.1f}" fill="none" stroke="{WHITE}" stroke-width="1.5"/>')
        e = rad + (9 if isfin else 0) + 3
        blocked.append((x - e, y - e, x + e, y + e))
        names = sorted(g, key=lambda t: (t[0] != FIN, -len(t[1])))
        nm = SCO[names[0][0]]["name"] + (f" + {len(names) - 1} more" if len(names) > 1 else "")
        cands.append((x, y, rad + (9 if isfin else 0), f"{SCO[names[0][0]]['hqname']} · {nm}", "hq"))
    from glyph import svg as gsvg
    for s in sorted(c["linked"], key=lambda s: any(q == FIN for _, q in s["links"])):
        x, y, v = cam.proj(s["lon"], s["lat"])
        if not (v and inside(x, y)): continue
        isfin = any(q == FIN for _, q in s["links"])
        old = age_min(s) > 60
        hdg = s["hdg"] if s["hdg"] not in (None, 511) else s["cog"]
        col = WHITE if isfin else "#d4d4d8"
        o.append(f'<g opacity="{.5 if old else 1}">' + gsvg(SHIPKEY(s["type"]), x, y, 19 if isfin else 14, col, EDGE, rot=screen_rot(cam, s["lon"], s["lat"], hdg), edge_w=6) + "</g>")
        blocked.append((x - 8, y - 8, x + 8, y + 8))
        if isfin: cands.insert(0, (x, y, 10, s["name"].title() + (f" · last report {ago_s(age_min(s))} ago" if old else ""), "cs2"))
    lab = {"marks": [b for b in blocked if b[2] - b[0] > 19]}
    place_labels([c for c in cands if c[4] == "hq"], lab, o)
    lab["marks"] = blocked
    place_labels([c for c in cands if c[4] != "hq"], lab, o)
    o.append("</svg>")
    return "".join(o)


def sea_left(S):
    esc = S.esc
    c = sea_counts()
    steps = [
        (f"{c['pos']:,}", "ships with a position on Digitraffic", f"Finland's open AIS feed · Finnish waters only · {datetime.datetime.fromtimestamp(DT_TIME, UTC):%H:%M} UTC"),
        (f"{c['imo']:,}", "carry an IMO number", "the hull's permanent number; names and flags change, the IMO number does not"),
        (f"{c['wd']:,}", "found in Wikidata by that IMO number", "property P458 on a ship item"),
        (str(len(c["linked"])), "name an owner or an operator there", "owned by (P127): solid · operated by (P137): dashed"),
        (str(len(c["comps"])), "companies they lead to, then up each company's own chain", "GLEIF by the company's LEI, Wikidata's parent organisation"),
    ]
    st = "".join(f'<div class="stp"><b class="num">{n}</b><div><span>{esc(t)}</span><small>{esc(s)}</small></div></div>' for n, t, s in steps)
    top = sorted(c["comps"].items(), key=lambda kv: -len(kv[1]))[:11]
    trs = "".join(f'<tr class="{"sel" if q == FIN else ""}"><td>{esc(SCO[q]["name"])} <span class="q">· {esc(SCO[q]["hqname"] or "no headquarters in Wikidata")}</span></td><td class="r num">{len(l)}</td></tr>' for q, l in top)
    rest = len(c["comps"]) - len(top)
    return (f'<section class="pnl res"><div class="ph"><b>Their ships now</b><span>{len(c["linked"])} linked</span><span class="src">Digitraffic, Wikidata</span></div>{st}</section>'
            f'<section class="pnl res"><div class="ph"><b>By company</b><span>ships in view</span></div><table class="dt fx co"><colgroup><col><col style="width:56px"></colgroup>'
            f'<thead><tr><th>Company</th><th class="r">Ships</th></tr></thead><tbody>{trs}</tbody></table><div class="rmore">{rest} more companies with one ship each</div>'
            '<p class="hint">Ship owners are not in any free register. Wikidata covers ferries, icebreakers, research and navy ships well, cargo ships hardly at all. Equasis, the official database, needs a login and forbids automated use, so it is not used.</p></section>')


def sea_right(S):
    esc = S.esc
    c = sea_counts()
    fin = sorted(c["comps"][FIN], key=lambda t: age_min(t[0]))
    trs = "".join(f'<tr><td>{esc(s["name"].title())}<small>IMO {s["imo"]} · {"owner" if k == "owner" else "operator"}</small></td><td class="r num">{s["sog"]:.1f} kn</td><td class="r">{ago_s(age_min(s))}</td></tr>' for s, k in fin)
    return f'''<section class="pnl ent"><div class="eh"><span class="tag2">Company · Finland</span><h3>Finnlines Oyj</h3><p>LEI {GRIM["lei"]} · Wikidata “Finnlines” carries the same LEI · Helsinki</p></div>
<div class="kv"><div><b class="num">{len(fin)}</b><span>of its ships in view</span></div><div><b class="num">1</b><span>parent above it in GLEIF</span></div><div><b class="num">11</b><span>companies under that parent</span></div></div>
<div class="ph2">Up the chain <span>GLEIF</span></div>
<div class="chain"><div><b>Finnlines Oyj</b><small>Helsinki · direct and ultimate parent:</small></div><div><b>GRIMALDI GROUP S.P.A.</b><small>Palermo (registered address) · LEI {GRIM["parent"][0]}</small></div>
<div class="endc">Grimaldi Group declares that it is controlled by natural persons. GLEIF does not name them, so the chain stops here.</div></div>
<div class="ph2">Its ships now <span>Wikidata, matched by IMO</span></div>
<table class="dt fx"><colgroup><col><col style="width:64px"><col style="width:82px"></colgroup><thead><tr><th>Ship</th><th class="r">Speed</th><th class="r">Report</th></tr></thead><tbody>{trs}</tbody></table>
<p class="hint">Three were last reported 9 to 23 hours ago, heading south-west at about 20 knots. Digitraffic hears only Finnish waters, so they are drawn faded where they were last heard.</p>
<div class="actions"><span class="btn ink">Show Grimaldi's other companies</span><span class="btn">Wikidata</span><span class="btn">GLEIF</span></div>
<div class="src">Digitraffic {datetime.datetime.fromtimestamp(DT_TIME, UTC):%H:%M} · Wikidata 15:28-15:31 · GLEIF 15:29 UTC</div></section>'''


def sea_board(S, t):
    body = (sea_svg() + S.topbar(t, "Connections", 'Who owns what <b>Finnlines Oyj</b>' + S.mode_seg("map") + '<span class="chip on">Their aircraft and ships now</span>', "Finnlines")
            + f'<aside class="lcol">{sea_left(S)}</aside><aside class="col">{sea_right(S)}</aside>'
            + '<div class="gtools"><span class="btn">Fit</span><span class="btn">+</span><span class="btn">−</span><span class="leg">'
            + '<span><i class="dotw"></i>company · number = ships</span><span><i class="ln wv"></i>owner (Wikidata)</span><span><i class="ln wvd"></i>operator (Wikidata)</span>'
            + '<span><i class="ln gs"></i>parent (GLEIF)</span><span><i class="dots"></i>other ships</span></span></div>')
    return S.board("connections-sea", t, S.IMG["s-sea"], body)
