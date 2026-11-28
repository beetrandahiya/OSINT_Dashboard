"""Direction A, denser, on all four pages: Map, Connections, Investigate, Sources. 1920 x 1080 boards.
Real data only: the server store (newest 28 Nov 2026 03:08 UTC), live Connections answers and the reserved-identifier
checks fetched 28 Nov 12:36-12:38 UTC, the fetch log for Sources."""
import sys, json, math, html, sqlite3, datetime, os, base64
LANG = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/lang"
HERE = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between"
sys.path.insert(0, LANG); sys.path.insert(0, HERE)
import render as RD
import mock, glyph as GL, mapdata as M, porcelain as P
from cam import Cam
esc = lambda s: html.escape(str(s), quote=True)
UTC = datetime.UTC
T = 1795835320                      # 28 Nov 2026 03:08:40 UTC, newest fast feed in the store
W, H = 1920, 1080
MAPCAM = Cam(19, 35, 0.42, 34, 49, 1500, 920, 450)
X0, X1 = 392, 1448                  # map area free of the two columns
DB = sqlite3.connect("file:/home/user/OSINT_Dashboard/data/worldwatch.db?mode=ro", uri=True)
D = mock.data()


def pl(f):
    return json.loads(DB.execute("select payload from latest where feed=?", (f,)).fetchone()[0])


def dt(ts, fmt="%-d %b %H:%M"):
    return datetime.datetime.fromtimestamp(ts, UTC).strftime(fmt)


def ago(ts, now=T):
    s = max(0, now - ts)
    if s < 90: return f"{int(s)} s"
    if s < 5400: return f"{int(s / 60)} min"
    if s < 172800: return f"{s / 3600:.0f} h"
    return f"{s / 86400:.0f} d"


def num(v):
    return f"{v:,}" if isinstance(v, int) else v


def ico(key, col, size=16, edge="var(--u-panel)"):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">{GL.svg(key, size / 2, size / 2, size, col, edge, edge_w=6)}</svg>'


def inview(lon, lat):
    x, y, v = MAPCAM.proj(lon, lat)
    return v and X0 <= x <= X1 and 58 <= y <= H


def pick_wm():
    return mock.WMVB_PATH, mock.WMW


def topbar(t, active, context, search, extra="", left=True, right=True, folded=False):
    il = P.flat_svg("light", "tbl" + active).replace("<svg ", '<svg class="ic-l" width="28" height="28" ', 1)
    idk = P.flat_svg("dark", "tbd" + active).replace("<svg ", '<svg class="ic-d" width="28" height="28" ', 1)
    tabs = "".join(f'<span class="tab{" on" if n == active else ""}">{n}</span>' for n in ["Map", "Connections", "Investigate", "Sources"])
    d, w = pick_wm()
    lb = f'<span class="fold l{" off" if folded else ""}" title="{"Show" if folded else "Hide"} the left panel" aria-label="{"Show" if folded else "Hide"} the left panel"><i></i></span>' if left else ""
    rb = f'<span class="fold r{" off" if folded else ""}" title="{"Show" if folded else "Hide"} the right panel" aria-label="{"Show" if folded else "Hide"} the right panel"><i></i></span>' if right else ""
    return (f'<header class="tb"><span class="brand">{il}{idk}<svg class="wm" viewBox="{mock.WMVB}" width="{w:.0f}" height="{mock.WMH:.1f}" aria-label="World Watch">'
            f'<path d="{d}" fill="currentColor"/></svg></span>{lb}<nav class="tabs">{tabs}</nav><span class="view">{context}</span>'
            f'<span class="search"><i class="lens"></i>{search}</span>{extra}'
            f'<span class="feeds"><i class="dot live"></i>37 of 45 ok<span class="sep">·</span><i class="dot fail"></i>3 failing</span>{rb}<span class="gear" aria-label="Settings"></span></header>')


def board(name, t, bg, body, extra_cls=""):
    style = f' style="background-image:url({bg})"' if bg else ""
    return (f'<div class="fit" data-w="{W}" data-h="{H}"><div class="board big ui {t} smoke suite{" plain" if not bg else ""} {extra_cls}" data-board="{name}"{style}>{body}</div></div>')


# ============================== MAP ==============================
C = dict(conf="#fb7185", mil="#a5b4fc", ship="#7dd3fc", news="#e4e4e7", edge="#09090b", ring="#fafafa", halo="#09090b",
         label="#e4e4e7", avoid="#f87171", notice="#facc15", gpshi="#f87171", gpslo="#facc15", cable="#e4e4e7")


def ring_path(ring):
    pts = [MAPCAM.proj(lo, la) for lo, la in ring]
    if sum(1 for p in pts if p[2]) < len(pts) * .9: return ""
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y, v in pts if v) + "Z"


def map_svg():
    o = [f'<svg class="mk" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">']
    # cables, faint
    o.append(f'<g fill="none" stroke="{C["cable"]}" stroke-opacity=".16" stroke-width=".9">')
    for f in pl("cables")["features"]:
        g = f["geometry"]; lines = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for ln in lines:
            seg, cur = [], []
            for lo, la in ln:
                x, y, v = MAPCAM.proj(lo, la)
                if v and -50 < x < W + 50 and -50 < y < H + 50: cur.append(f"{x:.1f} {y:.1f}")
                else:
                    if len(cur) > 1: seg.append(cur)
                    cur = []
            if len(cur) > 1: seg.append(cur)
            for s in seg: o.append('<path d="M' + "L".join(s) + '"/>')
    o.append("</g>")
    # GPS interference (GPSJAM, the day before), hexagons
    gp = pl("gps")
    for lvl, col, op in (("some", C["gpslo"], .07), ("high", C["gpshi"], .18)):
        o.append(f'<g fill="{col}" fill-opacity="{op}">')
        for f in gp["features"]:
            if f["properties"]["level"] != lvl: continue
            p = ring_path(f["geometry"]["coordinates"][0])
            if p: o.append(f'<path d="{p}"/>')
        o.append("</g>")
    # airspace warnings: outlines
    for z in pl("airspace")["zones"]:
        col = C["avoid"] if z["level"] in ("avoid", "prohibited") else C["notice"]
        for fir, polys in (z.get("shapes") or {}).items():
            for ring in polys:
                p = ring_path(ring)
                if p: o.append(f'<path d="{p}" fill="none" stroke="{col}" stroke-opacity=".38" stroke-width="1" stroke-dasharray="5 4"/>')
    # front line
    o.append(f'<g fill="{C["conf"]}" fill-opacity=".22" stroke="{C["conf"]}" stroke-opacity=".85" stroke-width="1">')
    for a in D["front"]["areas"]:
        if a["kind"] != "occupied": continue
        for ring in a["rings"]:
            p = ring_path(ring)
            if p: o.append(f'<path d="{p}"/>')
    o.append("</g>")
    # news places
    o.append(f'<g fill="{C["news"]}">')
    for p in sorted([p for p in D["news"]["places"] if inview(p["lon"], p["lat"])], key=lambda p: p["outlets"]):
        x, y, _ = MAPCAM.proj(p["lon"], p["lat"]); r = min(8, 1.2 + .6 * math.sqrt(p["outlets"]))
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill-opacity="{.2 if p["outlets"] < 3 else .5}"/>')
    o.append("</g>")
    o.append(f'<g fill="{C["ship"]}" fill-opacity=".85">')
    for s in D["ships"]["ships"]:
        if inview(s["lon"], s["lat"]):
            x, y, _ = MAPCAM.proj(s["lon"], s["lat"]); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4"/>')
    o.append("</g>")
    for g in sorted([g for g in D["unrest"]["groups"] if g["outlets"] >= 2 and inview(g["lon"], g["lat"])], key=lambda g: g["outlets"]):
        x, y, _ = MAPCAM.proj(g["lon"], g["lat"]); sz = 14 + min(14, 2.3 * math.sqrt(g["outlets"]))
        o.append(GL.svg(mock.kind_of(g), x, y, sz, C["conf"], C["edge"], edge_w=7))
    for a in D["mil"]["aircraft"]:
        if a.get("lat") and inview(a["lon"], a["lat"]):
            x, y, _ = MAPCAM.proj(a["lon"], a["lat"])
            o.append(GL.svg(GL.for_type(a.get("type")), x, y, 26, C["mil"], C["edge"], rot=a.get("track") or 0, edge_w=6))
            o.append(f'<text x="{x + 15:.1f}" y="{y + 4:.1f}" class="cs">{esc(a.get("flight") or a["hex"])}</text>')
    x, y, _ = MAPCAM.proj(36.2527, 49.9808)
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="23" fill="none" stroke="{C["halo"]}" stroke-width="4" stroke-opacity=".85"/>'
             f'<circle cx="{x:.1f}" cy="{y:.1f}" r="23" fill="none" stroke="{C["ring"]}" stroke-width="1.5"/>')
    for name, lon, lat, dx, dy in [("Kyiv", 30.52, 50.45, -10, -14), ("Moscow", 37.62, 55.75, 14, 4), ("Istanbul", 28.98, 41.01, -12, 18),
                                   ("Berlin", 13.40, 52.52, 10, -8), ("Munich", 11.58, 48.14, 10, 12), ("Warsaw", 21.01, 52.23, 10, -8),
                                   ("Ankara", 32.86, 39.93, 12, 14), ("Tbilisi", 44.79, 41.72, 12, 4), ("Athens", 23.73, 37.98, -12, 16),
                                   ("Minsk", 27.56, 53.90, 10, -8), ("Bucharest", 26.10, 44.43, 10, 14), ("Rome", 12.50, 41.90, 10, 14)]:
        x, y, v = MAPCAM.proj(lon, lat)
        if not v or not (X0 < x < X1): continue
        anchor = "end" if dx < 0 else "start"
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{C["label"]}"/><text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" class="pl">{name}</text>')
    o.append("</svg>")
    return "".join(o)


def world_signals():
    seen, rows = set(), []
    for g in sorted([g for g in D["unrest"]["groups"] if g["outlets"] >= 2], key=lambda g: -g["outlets"]):
        if g["place"] in seen: continue
        seen.add(g["place"]); rows.append(g)
        if len(rows) == 5: break
    tr = "".join(f'<tr class="{"sel" if g["place"].startswith("Kharkiv") else ""}"><td class="g">{ico(mock.kind_of(g), "var(--u-conf)")}</td>'
                 f'<td><b>{esc(g["place"].split(",")[0])}</b><small>{esc(g["place"].split(",")[-1].strip())} · {esc(g["action"])}</small></td>'
                 f'<td class="num r">{g["outlets"]}</td><td class="num r q nw">{ago(g["last"])}</td></tr>' for g in rows)
    return (f'<section class="pnl"><div class="ph"><b>World</b><span>protests and clashes, 24 h</span><span class="src">GDELT · {dt(D["ut"], "%H:%M")}</span></div>'
            f'<table class="dt fx"><colgroup><col style="width:22px"><col><col style="width:58px"><col style="width:42px"></colgroup><thead><tr><th></th><th>Place · coded as</th><th class="r">Outlets</th><th class="r">Ago</th></tr></thead><tbody>{tr}</tbody></table></section>')


def watch():
    f = pl("front_ukraine"); up = f["update"]; wk = f["week"]
    u = pl("usni_fleet"); ships = u["ships"]
    by = {}
    for s in ships: by.setdefault(s["port"] or s["region"], []).append(s["name"].replace("USS ", ""))
    fleet = "; ".join(f'{esc(", ".join(v))} <em>{esc(k.split(",")[0].replace("the ", ""))}</em>' for k, v in by.items())
    a = pl("airspace"); zones = a["zones"]
    av = [z for z in zones if z["level"] in ("avoid", "prohibited")]
    names = sorted({z["title"].replace("Airspace of ", "").split(" –")[0] for z in av if z["source"] == "EASA"})
    q5 = sorted([q for q in pl("quakes")["quakes"] if q["mag"] >= 5], key=lambda q: -q["mag"])
    lastok = DB.execute("select max(started) from fetches where feed='outages' and ok=1").fetchone()[0]
    return f'''<section class="pnl"><div class="ph"><b>Watch</b><span>standing situations</span></div>
<div class="wrow"><div class="wh"><i class="g">{ico("occupied", "var(--u-conf)")}</i><b>Front line, Ukraine</b><span class="src">DeepState · {dt(up["time"])}</span></div>
 <p><span class="num">{f["occupied_km2"]:,}</span> km² occupied, <span class="num">+{f["occupied_km2"] - wk["occupied_km2"]}</span> since {dt(wk["time"], "%-d %b")}. Newest note: “{esc(up["text"])}”</p></div>
<div class="wrow dead"><div class="wh"><i class="g">{ico("outage", "var(--u-wait)")}</i><b>Internet outages</b><span class="src"><i class="dot fail"></i>IODA · failing</span></div>
 <p>IODA has not answered since {dt(lastok)} UTC (timed out). The map keeps its last list of 127 events, marked with that age.</p></div>
<div class="wrow"><div class="wh"><i class="g">{ico("carrier", "var(--u-ship)")}</i><b>US carriers and amphibs</b><span class="src late"><i class="dot late"></i>USNI · {dt(u["published"], "%-d %b")} · {ago(u["published"])} old</span></div>
 <p class="fleet">{fleet}.</p></div>
<div class="wrow"><div class="wh"><i class="g">{ico("as_avoid", "var(--u-fail)")}</i><b>Airspace</b><span class="src">EASA, FAA · {len(zones)} warnings · {len(a["tfrs"])} US TFRs</span></div>
 <p>Do not fly: {esc(", ".join(names[:9]))} and {len(names) - 9} more.</p></div>

</section>'''


def markets():
    m = pl("markets")["quotes"]; fx = pl("fx"); cr = pl("crypto")["bitcoin"]
    rows = "".join(f'<tr><td>{esc(q["name"])}</td><td class="num r">{q["price"]:,.2f}</td><td class="num r {"up" if q["price"] >= q["previous_close"] else "dn"}">'
                   f'{(q["price"] / q["previous_close"] - 1) * 100:+.1f}%</td><td class="num r q">{dt(q["time"], "%-d %b")}</td></tr>' for q in m)
    rows += f'<tr><td>Bitcoin</td><td class="num r">{cr["usd"]:,}</td><td class="num r {"up" if cr["usd_24h_change"] >= 0 else "dn"}">{cr["usd_24h_change"]:+.1f}%</td><td class="num r q">{dt(cr["last_updated_at"], "%H:%M")}</td></tr>'
    return f'<section class="pnl"><div class="ph"><b>Markets</b><span>delayed, unofficial</span><span class="src">Yahoo, CoinGecko</span></div><table class="dt mk2 fx"><colgroup><col><col style="width:80px"><col style="width:54px"><col style="width:58px"></colgroup>{rows}</table></section>'


def tiles12():
    F = {r["name"]: r for r in json.load(open(f"{HERE}/feeds.json"))}
    def st(n):
        s = F[n]["state"]; return {"ok": "live", "late": "late", "failing": "fail"}.get(s, "")
    def t(key, col, val, name, feed, src):
        r = F[feed]; s = r["state"]
        lastok = DB.execute("select max(started) from fetches where feed=? and ok=1", (feed,)).fetchone()[0]
        when = dt(r["fetched"], "%H:%M") if s == "ok" else (("from " + dt(lastok or r["data_time"], "%-d %b")) if s == "failing" else dt(r["data_time"] or r["fetched"], "%-d %b"))
        return (f'<div class="tile {"bad" if s == "failing" else ""}"><i class="g">{ico(key, f"var(--u-{col})")}</i><b class="num">{val}</b>'
                f'<span class="n">{name}</span><span class="s"><i class="dot {st(feed)}"></i>{src} · {when}</span></div>')
    g = pl("gps")
    cells = [t("clash", "conf", "445", "Protests, clashes", "unrest", "GDELT"), t("news", "news", "2,152", "News places", "news", "GDELT"),
             t("strategic", "mil", "23", "Military aircraft", "aircraft_military", "adsb.fi"), t("narrow", "news", "6,830", "Aircraft, world", "aircraft_world", "OpenSky"),
             t("cargo", "ship", "663", "Ships, Baltic", "ships", "Digitraffic"), t("occupied", "conf", f'{D["front"]["occupied_km2"]:,}', "km² occupied", "front_ukraine", "DeepState"),
             t("as_avoid", "fail", "81", "Airspace warnings", "airspace", "EASA, FAA"), t("gps", "late", f'{len(g["features"]):,}', f'GPS cells, {g["day"][8:]} Nov', "gps", "GPSJAM"),
             t("cable", "news", "714", "Undersea cables", "cables", "TeleGeography"), t("sat_img", "sat", "170", "Satellites", "satellites", "CelesTrak"),
             t("launch", "sat", "20", "Launches", "launches", "LL2"), t("outage", "wait", "127", "Outages, 7 d", "outages", "IODA")]
    return f'<section class="tiles t12">{"".join(cells)}<div class="more"><span>12 of 39 layers on</span><b>All layers</b></div></section>'


FULLCAM = Cam(19, 35, 0.42, 34, 49, 1500, 960, 450)
SIDECAM = MAPCAM


def map_board(t, folded=False):
    global MAPCAM, X0, X1
    MAPCAM, X0, X1 = (FULLCAM, 0, W) if folded else (SIDECAM, 392, 1448)
    clock = f'<span class="clock"><b class="num">03:08</b> UTC<span class="sep">·</span><b class="num">04:08</b> Munich</span>'
    body = map_svg() + topbar(t, "Map", 'Theatre <b>Europe and the Middle East</b>', "Find a place, person or company", clock, folded=folded)
    if folded:
        body += '<span class="handle l" title="Show the left panel"><i></i></span><span class="handle r" title="Show the right panel"><i></i></span>'
    else:
        body += f'<aside class="lcol">{world_signals()}{watch()}{markets()}</aside><aside class="col">{mock.card()}{mock.now_list()}{tiles12()}</aside>'
    body += views_ctl(open_=folded, x=(24 if folded else 404))
    seen_x = 28 if folded else 408
    body += (f'<div class="seen" style="left:{seen_x}px;bottom:{178 if folded else 64}px"><span>Seen from</span> <b class="num">35.0° N 19.0° E · 2,676 km up</b> · looking at 49.0° N 34.0° E · 28 Nov 2026 03:08 UTC</div>'
             f'<div class="key" style="left:{24 if folded else 404}px"><span><i class="sw" style="background:#f87171"></i>Do not fly</span><span><i class="sw" style="background:#facc15"></i>GPS interference, 27 Nov</span>'
             '<span><i class="sw" style="background:#fb7185"></i>Occupied</span><span><i class="sw ln"></i>Cables</span></div>')
    out = board("map", t, IMG["s-map-full" if folded else "s-map"], body)
    MAPCAM, X0, X1 = SIDECAM, 392, 1448
    return out


def views_ctl(open_=False, x=404):
    names = ["Whole Earth", "Theatre", "Day and night", "Look down", "Over the pole", "Low orbit"]
    btn = f'<span class="vbtn{" on" if open_ else ""}" style="left:{x}px"><i class="vic"></i>Views<b>Theatre</b><i class="chev"></i></span>'
    if not open_: return btn
    strip = '<nav class="vstrip" style="left:%dpx;bottom:62px">' % x + "".join(f'<span class="vt{" on" if n == "Theatre" else ""}"><img src="{IMG["t-A-%d" % i]}" width="128" height="72" alt=""><span>{n}</span></span>' for i, n in enumerate(names)) + "</nav>"
    return strip + btn


# ============================== CONNECTIONS ==============================
CONN = json.load(open(f"{HERE}/conn.json")); ROS = CONN["parent"]; CTIME = os.path.getmtime(f"{HERE}/conn.json")
SRC_COL = {"GLEIF": "#7dd3fc", "Wikidata": "#c4b5fd", "Offshore Leaks": "#5eead4", "OpenSanctions": "#fb7185"}
FLAGISH = {"RU": "Russia", "DE": "Germany", "IE": "Ireland", "CH": "Switzerland", "LU": "Luxembourg", "GB": "United Kingdom"}


def conn_results():
    res = CONN["search"]; groups = {}
    for r in res: groups.setdefault(r["source"], []).append(r)
    show = {"GLEIF": 6, "Wikidata": 5, "Offshore Leaks": 3, "OpenSanctions": 6}
    o = []
    for src in ["GLEIF", "Wikidata", "Offshore Leaks", "OpenSanctions"]:
        rows = groups.get(src, []); n = show[src]
        o.append(f'<div class="rg"><i class="sw" style="background:{SRC_COL[src]}"></i><b>{"Sanctions" if src == "OpenSanctions" else src}</b><span class="num">{len(rows)}</span></div>')
        for r in rows[:n]:
            sel = " sel" if r["ref"] == "lei:253400JT3MQWNDKMJE44" else ""
            note = r.get("note") or ""
            if src == "OpenSanctions": note = (note.replace("on ", "", 1).split(",")[0] + (" and more" if note.count(",") else ""))
            ctry = (r.get("country") or "").upper()
            o.append(f'<div class="rr{sel}"><span class="rn">{esc(r["name"])}</span><small>{esc(FLAGISH.get(ctry, r.get("country") or ""))}{" · " if ctry and note else ""}{esc(note)}</small></div>')
        if len(rows) > n: o.append(f'<div class="rmore">{len(rows) - n} more</div>')
    return (f'<section class="pnl res"><div class="ph"><b>Results</b><span>“Rosneft” in four registers</span><span class="src">{len(res)} found</span></div>{"".join(o)}'
            '<p class="hint">Only organisations can be searched. People appear only where a public register links them to a company.</p></section>')


def conn_graph():
    hold = [h for h in ROS["holdings"] if "patent" not in (h.get("desc") or "")]
    gle = [h for h in hold if h["source"] == "GLEIF"]; wd = [h for h in hold if h["source"] == "Wikidata"]
    cols, cw, chh, gx0, gy0 = 5, 196, 50, 414, 384
    cards, edges = [], []
    cx, cy = 920, 286   # bottom of the Rosneft node
    for i, h in enumerate(gle + wd):
        c, r = i % cols, i // cols
        x, y = gx0 + c * (cw + 10), gy0 + r * (chh + 14)
        col = SRC_COL[h["source"]]; sel = h["name"] == "Rosneft Deutschland GmbH"
        edges.append(f'<path d="M{cx} {cy} C{cx} {cy + 50} {x + cw / 2} {y - 46} {x + cw / 2} {y}" stroke="{col}" stroke-opacity="{.9 if sel else .45}" stroke-width="{1.6 if sel else 1}" fill="none"/>')
        label = {"direct subsidiary (consolidated)": "direct subsidiary", "names it as parent": "names it as parent", "owned by it": "owned by it", "subsidiary": "subsidiary"}.get(h.get("label"), h.get("label") or "")
        cards.append(f'<div class="gn small{" on" if sel else ""}" style="left:{x}px;top:{y}px;width:{cw}px"><b>{esc(h["name"])}</b>'
                     f'<small><i class="sw" style="background:{col}"></i>{esc(label)}{(" · " + esc(h["desc"])) if h.get("desc") else ""}</small></div>')
        if sel: dx, dy = x, y
    # chain continues from Rosneft Deutschland to its own holding
    edges.append(f'<path d="M{dx + cw / 2} {dy + chh} L{dx + cw / 2} {dy + chh + 300}" stroke="{SRC_COL["Wikidata"]}" stroke-opacity=".9" stroke-width="1.6" fill="none"/>')
    cards.append(f'<div class="gn small" style="left:{dx - 20}px;top:{dy + chh + 300}px;width:{cw + 40}px"><b>Transalpine Ölleitung in Österreich</b><small><i class="sw" style="background:{SRC_COL["Wikidata"]}"></i>owned by Rosneft Deutschland · Austrian company</small></div>')
    s = ROS["sanctions"][0]
    svg = f'<svg class="gl" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">' + "".join(edges) + (
        f'<path d="M920 156 L920 196" stroke="#a1a1aa" stroke-dasharray="4 4" fill="none"/>'
        f'<path d="M730 240 L604 240" stroke="{SRC_COL["OpenSanctions"]}" stroke-width="1.4" fill="none"/>'
        f'<path d="M1110 240 L1236 240" stroke="{SRC_COL["Offshore Leaks"]}" stroke-dasharray="5 4" fill="none"/>') + "</svg>"
    return svg + f'''<div class="gn end" style="left:690px;top:92px;width:460px"><span class="tag">Where the chain stops</span><b>Rosneft declares that no known person or company controls it.</b><small>GLEIF reporting exception NO_KNOWN_PERSON, direct and ultimate</small></div>
<div class="gn big on" style="left:730px;top:196px;width:380px"><span class="tag">Selected · Russia</span><b>Rosneft</b><small>{esc(ROS["facts"][1]["value"])}</small><span class="chips"><span class="chip red">Sanctioned · 8 lists by LEI</span><span class="chip">GLEIF</span><span class="chip">Wikidata</span></span></div>
<div class="gn" style="left:404px;top:206px;width:200px"><span class="tag" style="color:{SRC_COL["OpenSanctions"]}">OpenSanctions</span><b>Rosneft</b><small>same LEI · listed since {s["since"][:4]}</small></div>
<div class="gn dash" style="left:1236px;top:200px;width:200px"><span class="tag" style="color:{SRC_COL["Offshore Leaks"]}">Offshore Leaks · same name only</span><b>ROSNEFT INC.</b><small>Panama, Panama Papers, inc. 2005-10-04 · may be someone else</small></div>
<div class="glabel" style="left:930px;top:340px">{len(gle)} in GLEIF · {ROS["holdings_total"]["Wikidata"]} in Wikidata, 24 loaded, a patent left out</div>
{"".join(cards)}
<div class="gtools"><span class="btn">Fit</span><span class="btn">+</span><span class="btn">−</span><span class="leg">{"".join(f'<span><i class="ln" style="background:{c}"></i>{"Sanctions" if k == "OpenSanctions" else k}</span>' for k, c in SRC_COL.items())}<span><i class="ln dash"></i>same name only</span></span></div>'''


def conn_panel():
    facts = [f for f in ROS["facts"] if f["label"] not in ("LEI record",)]
    rows = "".join(f'<tr><th>{esc(f["label"])}</th><td class="{"mono" if f["label"] in ("LEI", "Register number", "Legal form") else ""}">{esc(f["value"])}</td><td class="sc">{esc(f["source"])}</td></tr>' for f in facts)
    s = ROS["sanctions"][0]
    lists = "".join(f"<li>{esc(x)}</li>" for x in s["lists"])
    return f'''<section class="pnl ent"><div class="eh"><span class="tag2">Company · Russia</span><h3>Rosneft</h3><p>{esc(ROS["facts"][1]["value"])}</p>
<div class="chips"><span class="chip">ACTIVE in GLEIF</span><span class="chip red">On 8 sanctions lists</span></div></div>
<div class="kv"><div><b class="num">0</b><span>owners declared</span></div><div><b class="num">30</b><span>holdings found</span></div><div><b class="num">8</b><span>sanctions lists</span></div></div>
<div class="ph2">Facts <span>each with its source</span></div><table class="dt ft2"><tbody>{rows}</tbody></table>
<div class="ph2">Sanctions <span>OpenSanctions, matched on its LEI</span></div><ul class="lists">{lists}</ul>
<div class="ph2">Owners</div><p class="small">GLEIF: declares that no known person or company controls it (direct and ultimate). Wikidata names no owner.</p>
<div class="actions"><span class="btn ink">Open in GLEIF</span><span class="btn">Wikidata</span><span class="btn">OpenSanctions</span><span class="btn">Report</span></div>
<div class="src">GLEIF, Wikidata, OpenSanctions, Offshore Leaks · all answered · {dt(CTIME, "%-d %b %H:%M")} UTC</div></section>'''


def mode_seg(on):
    return f'<span class="seg"><span class="{"on" if on == "graph" else ""}">Graph</span><span class="{"on" if on == "map" else ""}">On the map</span></span>'


def conn_board(t):
    body = (topbar(t, "Connections", 'Who owns what <b>Rosneft</b>' + mode_seg("graph"), "Rosneft") + f'<aside class="lcol">{conn_results()}</aside>'
            + f'<div class="graph">{conn_graph()}</div><aside class="col">{conn_panel()}</aside>')
    return board("connections", t, None, body)


WDP = json.load(open(f"{HERE}/wd-places.json"))
CCAM = Cam(58, 38, 1.0, 58, 55, 1240, 935, 600)


def conn_places():
    gc = WDP["gleif_cities"]; it = WDP["items"]
    rows = [dict(name="Rosneft", lat=it["Q1141123"]["coord"]["latitude"], lon=it["Q1141123"]["coord"]["longitude"], how="headquarters, Wikidata", place="Moscow", src="self"),
            dict(name="“RN-Capital” LLC", lat=gc["Q649"]["lat"], lon=gc["Q649"]["lon"], how="address, GLEIF", place="Moscow", src="GLEIF"),
            dict(name="Rosneft Deutschland GmbH", lat=gc["Q64"]["lat"], lon=gc["Q64"]["lon"], how="address, GLEIF", place="Berlin", src="GLEIF"),
            dict(name="Transalpine Ölleitung in Österreich", lat=gc["Q261697"]["lat"], lon=gc["Q261697"]["lon"], how="address, GLEIF", place="Matrei in Osttirol", src="chain")]
    unplaced = []
    for h in ROS["holdings"]:
        if not h["ref"].startswith("wd:") or "patent" in (h.get("desc") or ""): continue
        r = it.get(h["ref"][3:]) or {}
        if r.get("coord"):
            place = r.get("via") or h["name"]
            if place.endswith("headquarter"): place = "Moscow"
            rows.append(dict(name=h["name"], lat=r["coord"]["latitude"], lon=r["coord"]["longitude"], place=place,
                             how=("headquarters, Wikidata" if r.get("src") == "P159" else "located in, Wikidata" if r.get("src") == "P131" else "the site itself, Wikidata"), src="Wikidata"))
        else:
            unplaced.append(h["name"])
    return rows, unplaced


def conn_map_svg(rows):
    import math as m
    o = [f'<svg class="mk" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">']
    hq = rows[0]
    def arc(a, b, col, w=1.1, op=.75):
        la1, lo1, la2, lo2 = map(m.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
        dd = 2 * m.asin(m.sqrt(m.sin((la2 - la1) / 2) ** 2 + m.cos(la1) * m.cos(la2) * m.sin((lo2 - lo1) / 2) ** 2))
        if dd < 1e-4: return ""
        pts = []
        for i in range(33):
            f = i / 32; A = m.sin((1 - f) * dd) / m.sin(dd); B = m.sin(f * dd) / m.sin(dd)
            x = A * m.cos(la1) * m.cos(lo1) + B * m.cos(la2) * m.cos(lo2); y = A * m.cos(la1) * m.sin(lo1) + B * m.cos(la2) * m.sin(lo2); z = A * m.sin(la1) + B * m.sin(la2)
            lat, lon = m.degrees(m.atan2(z, m.hypot(x, y))), m.degrees(m.atan2(y, x))
            px, py, v = CCAM.proj(lon, lat, .03 * m.sin(m.pi * f) * min(1, dd / .3))
            pts.append(f"{px:.1f} {py:.1f}")
        return f'<path d="M{"L".join(pts)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}"/>'
    for r in rows[1:]:
        if r["src"] == "chain":
            o.append(arc(rows[2], r, SRC_COL["Wikidata"], 1.6, .95))
        else:
            o.append(arc(hq, r, SRC_COL["GLEIF"] if r["src"] == "GLEIF" else SRC_COL["Wikidata"], 1.6 if r["name"].startswith("Rosneft Deutschland") else 1.1, .95 if r["name"].startswith("Rosneft Deutschland") else .6))
    groups = {}
    for r in rows:
        groups.setdefault((round(r["lat"], 2), round(r["lon"], 2)), []).append(r)
    boxes, labels = [], []
    for (lat, lon), g in sorted(groups.items(), key=lambda kv: (-any(r["src"] == "self" for r in kv[1]), -len(kv[1]))):
        x, y, v = CCAM.proj(lon, lat)
        if not v: continue
        n = len(g); rad = 4 + 2.2 * m.sqrt(n)
        boxes.append((x - rad - 3, y - rad - 3, x + rad + 3, y + rad + 3))
        col = "#fafafa" if any(r["src"] == "self" for r in g) else (SRC_COL["GLEIF"] if all(r["src"] in ("GLEIF",) for r in g) else SRC_COL["Wikidata"])
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 2.5:.1f}" fill="#09090b" fill-opacity=".7"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{col}"/>')
        if n > 1: o.append(f'<text x="{x:.1f}" y="{y + 3.6:.1f}" text-anchor="middle" class="cn">{n}</text>')
        if any(r["src"] == "self" for r in g):
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 9:.1f}" fill="none" stroke="#09090b" stroke-width="4" stroke-opacity=".8"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{rad + 9:.1f}" fill="none" stroke="#fafafa" stroke-width="1.5"/>')
        label = g[0]["place"] if n > 1 or g[0]["how"].startswith(("headquarters", "address", "located")) else g[0]["name"]
        if g[0]["name"].startswith("Rosneft Deutschland"): label = "Berlin · Rosneft Deutschland"
        labels.append((x, y + 4, rad + (9 if any(r["src"] == "self" for r in g) else 0), label))
    placed = []
    for x, y, rad, label in labels:
        w = 7.1 * len(label)
        for side, x0, yy in ((1, x + rad + 8, y), (-1, x - rad - 8 - w, y), (0, x - w / 2, y + rad + 16), (0, x - w / 2, y - rad - 10)):
            b = (x0 - 2, yy - 13, x0 + w + 2, yy + 3)
            if b[0] < 392 or b[2] > 1448: continue
            hit = any(not (b[2] < c[0] or b[0] > c[2] or b[3] < c[1] or b[1] > c[3]) for c in placed + [bb for bb in boxes if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3])])
            if not hit:
                placed.append(b)
                o.append(f'<text x="{x0:.1f}" y="{yy:.1f}" class="pl">{esc(label)}</text>')
                break
    o.append("</svg>")
    return "".join(o)


def conn_places_panel(rows, unplaced):
    by = {}
    for r in rows: by.setdefault(r["place"], []).append(r)
    order = sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    K = 5
    li = "".join(f'<div class="rg2"><b>{esc(k)}</b><span class="num">{len(v)}</span></div>' + "".join(f'<div class="rr"><span class="rn">{esc(r["name"])}</span><small>{esc(r["how"])}</small></div>' for r in v) for k, v in order[:K])
    rest = sum(len(v) for k, v in order[K:])
    return (f'<section class="pnl res"><div class="ph"><b>On the map</b><span>{len(rows)} of {len(rows) + len(unplaced)} placed</span><span class="src">Wikidata, GLEIF</span></div>{li}'
            f'<div class="rmore">{rest} more in {len(order) - K} other places</div>'
            f'<div class="ph2">Not placed <span>no location in either register</span></div>' + "".join(f'<div class="rr off"><span class="rn">{esc(n)}</span></div>' for n in unplaced)
            + '<p class="hint">A dot is a company’s registered address or headquarters, or the site itself for a refinery. It is not where a company operates.</p></section>')


def conn_map_board(t):
    rows, unplaced = conn_places()
    body = (conn_map_svg(rows) + topbar(t, "Connections", 'Who owns what <b>Rosneft</b>' + mode_seg("map"), "Rosneft")
            + f'<aside class="lcol">{conn_places_panel(rows, unplaced)}</aside><aside class="col">{conn_panel()}</aside>'
            + '<div class="gtools"><span class="btn">Fit</span><span class="btn">+</span><span class="btn">−</span><span class="leg">'
            + f'<span><i class="ln" style="background:{SRC_COL["GLEIF"]}"></i>GLEIF</span><span><i class="ln" style="background:{SRC_COL["Wikidata"]}"></i>Wikidata</span>'
            + '<span><i class="dotw"></i>Rosneft</span><span>number = companies at one place</span></span></div>')
    return board("connections-map", t, IMG["s-conn"], body)


# ============================== INVESTIGATE ==============================
X = json.load(open(f"{LANG}/case/xon2.json")); HRK = json.load(open(f"{LANG}/case/hr.json")); RDAP = json.load(open(f"{LANG}/case/rdap.json"))
ST = json.load(open("/home/user/OSINT_Dashboard/data/whatsmyname-selftest.json"))
MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def inv_side():
    return f'''<section class="pnl side"><div class="ph"><b>Investigate</b><span>public sources, on request</span></div>
<div class="ph2">Cases</div>
<div class="case off"><b>Me (self-test)</b><small>consent: self · not shown in mock-ups</small></div>
<div class="case on"><b>Case 0 · Reserved test identifiers</b><small>consent: not needed, RFC 2606 test addresses</small></div>
<span class="btn">New case</span>
<div class="ph2">Identifiers</div>
<div class="idr"><i class="dot live"></i><span class="mono">test@example.com</span><small>email · checked 12:38</small></div>
<div class="idr"><i class="dot live"></i><span class="mono">example.com</span><small>domain · checked 12:38</small></div>
<div class="field">Add a username, email, name, domain or picture</div>
<div class="ph2">Username checker</div>
<p class="small"><span class="num">{ST["trusted"]}</span> of <span class="num">{ST["total"]}</span> sites trusted on this computer, <span class="num">{ST["blind"]}</span> blind, <span class="num">{ST["false_alarm"]}</span> false alarms · tested {dt(ST["tested"], "%-d %b")}</p>
<span class="btn">Test the checker</span>
<div class="ph2">Scan</div>
<p class="small">Sends each identifier only to the services listed before you start. Password-reset probing stays off.</p>
<div class="actions"><span class="btn ink">Scan</span><span class="btn">Read the pages</span></div>
<div class="ph2">Stored on this computer</div><span class="btn danger">Delete all cases</span></section>'''


def inv_main():
    ex = X["ExposedBreaches"]["breaches_details"]; st = HRK["stealers"]
    days = sorted({s["date_compromised"][:10] for s in st})
    yw = [(int(k[1:]), v) for k, v in X["BreachMetrics"]["yearwise_details"][0].items() if int(k[1:]) >= 2009]
    mx = max(v for _, v in yw); bw = 520 / len(yw)
    bars = "".join(f'<rect x="{i * bw + 2:.1f}" y="{90 - 90 * v / mx:.1f}" width="{bw - 4:.1f}" height="{90 * v / mx:.1f}" rx="1.5" class="{"hi" if y == 2026 else ""}"/>' for i, (y, v) in enumerate(yw))
    labs = "".join(f'<text x="{i * bw + bw / 2:.1f}" y="104" text-anchor="middle">{y}</text>' for i, (y, v) in enumerate(yw) if y in (2009, 2012, 2015, 2018, 2021, 2024, 2026))
    dtc = {}
    for r in ex:
        for k in r["xposed_data"].split(";"):
            if k: dtc[k] = dtc.get(k, 0) + 1
    top = sorted(dtc.items(), key=lambda x: -x[1])[:8]
    dbars = "".join(f'<div class="hb"><span>{esc(k)}</span><i style="width:{v / len(ex) * 100:.0f}%"></i><b class="num">{v}</b></div>' for k, v in top)
    big = sorted(ex, key=lambda r: -int(r["xposed_records"] or 0))[:7]
    rows = "".join(f'<tr><td>{esc(r["breach"])}</td><td class="num">{r["xposed_date"]}</td><td class="num r">{int(r["xposed_records"]):,}</td><td class="q">{esc(r["xposed_data"].replace(";", ", "))}</td></tr>' for r in big)
    ev = {e["eventAction"]: e["eventDate"][:10] for e in RDAP["events"]}
    checks = [("XposedOrNot", "email", "216 breaches", "live"), ("Hudson Rock Cavalier", "email", f"{len(st)} infected computers", "live"),
              ("Gravatar", "email hash", "no picture", "live"), ("rdap.org", "domain", "registration record", "live"), ("crt.sh", "domain", "error page", "fail")]
    ch = "".join(f'<tr><td><i class="dot {s}"></i>{n}</td><td class="q">{w}</td><td>{a}</td></tr>' for n, w, a, s in checks)
    return f'''<nav class="itabs"><span>Accounts <i>0</i></span><span>Leads <i>0</i></span><span>Timeline</span><span class="on">Dossier</span><span>Graph</span></nav>
<section class="pnl dmain"><div class="ph"><b>Dossier</b><span>Case 0 · findings only</span><span class="src">checked 28 Nov 12:38 UTC</span></div>
<div class="kv k4"><div><b class="num">{len(ex)}</b><span>breaches name the address</span></div><div><b class="num">{len(st)}</b><span>infected computers had it saved</span></div><div><b class="num">0</b><span>accounts (no username seed)</span></div><div><b class="num">1995</b><span>domain registered</span></div></div>
<div class="g2"><div><div class="ph2">Breaches by the year the data leaked <span>XposedOrNot</span></div><svg viewBox="0 0 520 108" class="yb" role="img" aria-label="Breaches per year, 2009 to 2026">{bars}{labs}</svg></div>
<div><div class="ph2">What leaked <span>breaches holding each kind of data</span></div>{dbars}</div></div>
<div class="ph2">Largest breaches <span>names and data types only; no records are downloaded</span></div>
<table class="dt bt"><thead><tr><th>Breach</th><th>Year</th><th class="r">Records</th><th>Data types</th></tr></thead><tbody>{rows}</tbody></table>
<div class="g3"><div><div class="ph2">Info-stealer logs</div><p class="small"><span class="num">{len(st)}</span> computers infected by info-stealer malware had this address saved, compromised {days[0][8:].lstrip("0")}–{days[-1][8:].lstrip("0")} Nov 2026 (Hudson Rock). Saved logins are not shown.</p></div>
<div><div class="ph2">Domain <span>RDAP</span></div><p class="small">example.com: registered <span class="num">{ev["registration"]}</span>, expires <span class="num">{ev["expiration"]}</span>, registrar “RESERVED-Internet Assigned Numbers Authority”, Cloudflare name servers.</p></div>
<div><div class="ph2">Checks run</div><table class="dt chk"><tbody>{ch}</tbody></table></div></div></section>'''


def inv_timeline():
    ex = X["ExposedBreaches"]["breaches_details"]; ev = {e["eventAction"]: e["eventDate"][:10] for e in RDAP["events"]}
    old = sorted(ex, key=lambda r: (str(r["xposed_date"]), r.get("added") or ""))[:2]
    new = sorted(ex, key=lambda r: r.get("added") or "", reverse=True)[:3]
    st = HRK["stealers"]; days = sorted({s["date_compromised"][:10] for s in st})
    items = [(ev["registration"], "example.com registered", "RDAP")]
    items += [(str(r["xposed_date"]), f'{r["breach"]} leak ({int(r["xposed_records"]):,} records)', "XposedOrNot") for r in old]
    items += [("2019", "Collection-1 and Verifications, the two largest", "XposedOrNot")]
    items += [(ev["last changed"], "domain record last changed", "RDAP")]
    items += [(r["added"][:10], f'{r["breach"]} added to the breach list', "XposedOrNot") for r in sorted(new, key=lambda r: r["added"])]
    items += [(days[0], f"first of {len(st)} infected computers", "Hudson Rock"), (days[-1], "newest infected computer", "Hudson Rock"),
              ("2026-11-28", "checked by World Watch, 12:38 UTC", "this case")]
    li = "".join(f'<li><span class="num">{esc(d)}</span><b>{esc(t)}</b><small>{esc(s)}</small></li>' for d, t, s in items)
    return f'<section class="pnl tl"><div class="ph"><b>Timeline</b><span>dated facts only</span></div><ol class="tli">{li}</ol><p class="hint">Dates come from the sources. Undated findings are left out.</p></section>'


def inv_board(t):
    body = topbar(t, "Investigate", 'Case <b>Reserved test identifiers</b> · specimen', "Find in this case") + \
        f'<aside class="lcol">{inv_side()}</aside><div class="imain">{inv_main()}</div><aside class="col">{inv_timeline()}</aside>'
    return board("investigate", t, None, body)


# ============================== SOURCES ==============================
FE = json.load(open(f"{HERE}/feeds.json"))
GROUPS = [("Conflict and politics", ["unrest", "news", "news_translated", "front_ukraine", "airspace", "navwarn", "travel_advice", "courts_icc"]),
          ("Air", ["aircraft_near", "aircraft_view", "aircraft_military", "aircraft_world", "vip_aircraft", "gps_live", "gps"]),
          ("Sea", ["ships", "ships_world", "usni_fleet", "sanctioned"]),
          ("Space", ["satellites", "sat_catalog", "recon_sats", "launches", "space_weather"]),
          ("Networks", ["outages", "cf_radar", "cables", "cable_faults"]),
          ("Earth", ["quakes", "gdacs", "eonet", "fires", "radar", "ems", "maxar_events"]),
          ("Sites, people, pictures", ["sites", "cameras", "sdr", "icij", "flags"]),
          ("Markets and Munich", ["markets", "crypto", "fx", "munich_weather", "mvg"])]


def size(b):
    if b is None: return ""
    return f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{b / 1e3:.0f} KB"


def every(s):
    return f"{s // 86400} d" if s >= 86400 else f"{s // 3600} h" if s >= 3600 else f"{s // 60} min" if s >= 60 else f"{s} s"


def src_table(groups):
    F = {r["name"]: r for r in FE}
    o = ['<table class="dt ftab"><colgroup><col style="width:78px"><col><col style="width:54px"><col style="width:54px"><col style="width:66px"><col style="width:58px"><col style="width:52px"><col style="width:46px"></colgroup><thead><tr><th>State</th><th>Feed · source</th><th class="r">Fetched</th><th class="r">Data</th><th class="r">Items</th><th class="r">Size</th><th class="r">Every</th><th class="r">24 h</th></tr></thead>']
    for g, names in groups:
        o.append(f'<tbody><tr class="gh"><th colspan="8">{g}</th></tr>')
        for n in names:
            r = F[n]; s = r["state"]
            dot = {"ok": "live", "late": "late", "failing": "fail"}.get(s, "")
            sel = " sel" if n == "aircraft_world" else ""
            o.append(f'<tr class="{s.replace(" ", "-")}{sel}"><td><i class="dot {dot}"></i>{s}</td><td><b>{esc(r["layer"])}</b><small>{esc(r["source"])}</small></td>'
                     f'<td class="num r">{ago(r["fetched"]) if r["fetched"] else ""}</td><td class="num r">{ago(r["data_time"]) if r["data_time"] else ""}</td>'
                     f'<td class="num r">{num(r["items"]) if r["items"] is not None else ""}</td><td class="num r">{size(r["size"])}</td><td class="num r">{every(r["every"])}</td>'
                     f'<td class="num r">{r["ok24"]}{f" / <em>{r[chr(98)+chr(97)+chr(100)+"24"]}</em>" if r["bad24"] else ""}</td></tr>')
        o.append("</tbody>")
    o.append("</table>")
    return "".join(o)


def src_board(t):
    from collections import Counter
    c = Counter(r["state"] for r in FE); b24 = sum(r["bytes24"] for r in FE); n24 = sum(r["ok24"] + r["bad24"] for r in FE)
    w = next(r for r in FE if r["name"] == "aircraft_world")
    log = "".join(f'<tr><td class="num">{dt(float(l["t"]), "%H:%M")}</td><td><i class="dot {"live" if l["ok"] else "fail"} mr"></i>{"ok" if l["ok"] else esc((l["e"] or "")[:34])}</td><td class="num r">{(l["ms"] or 0) / 1000:.1f} s</td></tr>' for l in w["log"])
    keys = [("aisstream.io", "Ships worldwide", "data/aisstream-key.txt"), ("Cloudflare Radar", "Hijacks, outage notes", "data/cloudflare-token.txt"),
            ("OpenSanctions", "Sanctions in dossiers", "data/opensanctions-key.txt"), ("Windy", "Webcams", "data/windy-key.txt"),
            ("Brave Search", "Ship photos", "data/brave-key.txt"), ("GitHub", "Investigate leads", "data/github-token.txt")]
    kr = "".join(f'<tr><td><i class="dot mr"></i>{k}</td><td class="q">{u}</td></tr>' for k, u, f in keys)
    summary = (f'<div class="sumrow"><div><b class="num">{c["ok"]}</b><span><i class="dot live"></i>ok</span></div><div><b class="num">{c["late"]}</b><span><i class="dot late"></i>late</span></div>'
               f'<div><b class="num">{c["failing"]}</b><span><i class="dot fail"></i>failing</span></div><div><b class="num">{c["not set up"]}</b><span><i class="dot"></i>not set up</span></div>'
               f'<div><b class="num">{c["on request"]}</b><span>on request</span></div><div><b class="num">{b24 / 1e6:,.0f} MB</b><span>downloaded, 24 h</span></div>'
               f'<div><b class="num">{n24:,}</b><span>requests, 24 h</span></div><div><b class="num">0 of 6</b><span>keys set on this server</span></div></div>')
    half = GROUPS[:4], GROUPS[4:]
    body = (topbar(t, "Sources", 'Feeds <b>45</b> · cloud test server · 28 Nov 2026 03:08 UTC', "Find a feed or source")
            + f'<div class="smain">{summary}<div class="two"><section class="pnl">{src_table(half[0])}</section><section class="pnl">{src_table(half[1])}</section></div></div>'
            + f'''<aside class="col"><section class="pnl ent"><div class="eh"><span class="tag2">Feed · failing</span><h3>Aircraft worldwide</h3><p>OpenSky Network · every 20 min · late after 1 h</p>
<div class="chips"><span class="chip red">{esc(w["error"])}</span></div></div>
<div class="kv"><div><b class="num">{w["bad24"]}</b><span>failed, 24 h</span></div><div><b class="num">{num(w["items"])}</b><span>aircraft in the last good copy</span></div><div><b class="num">{ago(w["data_time"])}</b><span>age of that copy</span></div></div>
<div class="ph2">Last tries</div><table class="dt"><tbody>{log}</tbody></table>
<p class="small">The map keeps the last good snapshot and greys it out with its age. From this cloud server OpenSky often times out; from your network it answered before.</p>
<div class="ph2">Keys <span>all free; files stay out of git</span></div><table class="dt"><tbody>{kr}</tbody></table>
<div class="src">collector log, 7 days kept · times relative to 03:08 UTC</div></section></aside>''')
    return board("sources", t, None, body)
