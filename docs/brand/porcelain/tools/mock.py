"""App mock-up in the Porcelain look: the Dense layout (map, column on the right), built from the stored feed data."""
import html, math, datetime, sys
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/lang")
import mapdata as M, glyph as GL, porcelain as P
esc = lambda s: html.escape(str(s), quote=True)
UTC = datetime.UTC
CAP_T = 1795835300   # 28 Nov 2026 03:08 UTC, newest fast feed in the store
V = M.View(36.0, 44.2, 3.2)
VIEW_CENTRE = (44.2, 36.0, 3.2)

# Map and data colours per theme (Tailwind CSS v3.4.17 steps)
TH = {
    "l": dict(sea="#f0f9ff", land="#ffffff", border="#d4d4d8", coast="#a1a1aa", label="#71717a",
              conf="#e11d48", conf_area="#e11d48", mil="#4338ca", ship="#0369a1", news="#18181b", edge="#ffffff",
              ring="#010101", halo="#ffffff"),
    "d": dict(sea="#09090b", land="#18181b", border="#3f3f46", coast="#52525b", label="#a1a1aa",
              conf="#fb7185", conf_area="#fb7185", mil="#a5b4fc", ship="#7dd3fc", news="#e4e4e7", edge="#09090b",
              ring="#fafafa", halo="#09090b"),
}

_cache = {}


def data():
    if _cache: return _cache
    u, ut = M.payload("unrest"); n, nt = M.payload("news"); a, at = M.payload("aircraft_military")
    s, st = M.payload("ships"); f, ft = M.payload("front_ukraine"); l, lt = M.payload("launches")
    o, ot = M.payload("outages")
    _cache.update(unrest=u, ut=ut, news=n, nt=nt, mil=a, at=at, ships=s, st=st, front=f, ft=ft, launches=l, lt=lt,
                  outages=o, ot=ot, countries=M.countries(V))
    return _cache


def kind_of(g):
    c = max(g["codes"], key=g["codes"].get) if g.get("codes") else "190"
    return {"190": "clash", "191": "blockade", "192": "occupy", "193": "smallarms", "194": "artillery", "195": "aerial",
            "196": "ceasefire", "180": "attack", "181": "abduct", "182": "attack", "183": "bombing", "185": "assassin",
            "186": "assassin", "200": "mass", "140": "protest", "141": "protest", "143": "strike", "144": "obstruct",
            "145": "riot"}.get(c[:3], "protest" if g["cat"] == "protest" else "clash")


def hhmm(ts):
    return datetime.datetime.fromtimestamp(ts, UTC).strftime("%H:%M")


def day(ts):
    return datetime.datetime.fromtimestamp(ts, UTC).strftime("%-d %b")


def map_svg(t):
    D = data(); c = TH[t]; o = [f'<svg class="map" viewBox="0 0 {M.W} {M.H}" width="{M.W}" height="{M.H}" aria-hidden="true">']
    o.append(f'<rect width="{M.W}" height="{M.H}" fill="{c["sea"]}"/>')
    o.append(f'<g fill="{c["land"]}" stroke="{c["border"]}" stroke-width=".7" stroke-linejoin="round">')
    for iso, name, g in D["countries"]:
        o.append(f'<path d="{M.path(g)}"/>')
    o.append("</g>")
    # front line: occupied areas
    o.append(f'<g fill="{c["conf_area"]}" fill-opacity=".16" stroke="{c["conf_area"]}" stroke-opacity=".7" stroke-width=".8">')
    for a in D["front"]["areas"]:
        if a["kind"] != "occupied": continue
        d = "".join("M" + "L".join("%.1f %.1f" % V.px(*p) for p in ring) + "Z" for ring in a["rings"])
        o.append(f'<path d="{d}"/>')
    o.append("</g>")
    # news places: ink dots sized by outlets (area), smallest first
    places = sorted([p for p in D["news"]["places"] if V.inside(p["lon"], p["lat"])], key=lambda p: p["outlets"])
    o.append(f'<g fill="{c["news"]}">')
    for p in places:
        x, y = V.px(p["lon"], p["lat"]); r = min(7.5, 1.1 + 0.55 * math.sqrt(p["outlets"]))
        op = .16 if p["outlets"] < 3 else .38
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill-opacity="{op}"/>')
    o.append("</g>")
    # ships (Finland's open AIS): small dots
    o.append(f'<g fill="{c["ship"]}" fill-opacity=".8">')
    for sh in D["ships"]["ships"]:
        if V.inside(sh["lon"], sh["lat"]):
            x, y = V.px(sh["lon"], sh["lat"]); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.3"/>')
    o.append("</g>")
    # protests and clashes (2+ outlets): approved symbols, size by outlets
    gs = sorted([g for g in D["unrest"]["groups"] if g["outlets"] >= 2 and V.inside(g["lon"], g["lat"])], key=lambda g: g["outlets"])
    for g in gs:
        x, y = V.px(g["lon"], g["lat"]); sz = 13 + min(13, 2.2 * math.sqrt(g["outlets"]))
        o.append(GL.svg(kind_of(g), x, y, sz, c["conf"], c["edge"], edge_w=7))
    # military aircraft
    for a in D["mil"]["aircraft"]:
        if a.get("lat") and V.inside(a["lon"], a["lat"]):
            x, y = V.px(a["lon"], a["lat"])
            o.append(GL.svg(GL.for_type(a.get("type")), x, y, 24, c["mil"], c["edge"], rot=a.get("track") or 0, edge_w=6))
    # selection: Kharkiv clash, one hairline ring with a halo (the footprint ring)
    x, y = V.px(36.2527, 49.9808)
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="21" fill="none" stroke="{c["halo"]}" stroke-width="4" stroke-opacity=".9"/>'
             f'<circle cx="{x:.1f}" cy="{y:.1f}" r="21" fill="none" stroke="{c["ring"]}" stroke-width="1.4"/>')
    # a few place labels
    for name, lon, lat, dx, dy in [("Kyiv", 30.52, 50.45, -10, -14), ("Moscow", 37.62, 55.75, 14, 4), ("Tehran", 51.39, 35.69, 14, 4),
                                   ("Riyadh", 46.72, 24.69, 14, 4), ("Istanbul", 28.98, 41.01, -12, 18), ("Cairo", 31.24, 30.04, -14, 16),
                                   ("Berlin", 13.40, 52.52, 10, -8), ("Munich", 11.58, 48.14, 10, 12), ("Baghdad", 44.36, 33.31, 12, 14)]:
        if not V.inside(lon, lat): continue
        x, y = V.px(lon, lat)
        anchor = "end" if dx < 0 else "start"
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{c["label"]}"/><text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" '
                 f'font-family="B612, system-ui, sans-serif" font-size="11.5" letter-spacing=".04em" fill="{c["label"]}">{name}</text>')
    o.append("</svg>")
    return "".join(o)


def lat_s(v, p, n):
    return f"{abs(v):.1f}° {p if v >= 0 else n}"


WMVB, WMH = "0 -17 120 22", 22


def topbar(t, wm_path, wm_w):
    icon = P.flat_svg("light" if t == "l" else "dark", "tb" + t)
    icon = icon.replace("<svg ", '<svg width="28" height="28" ', 1)
    tabs = "".join(f'<span class="tab{" on" if i == 0 else ""}">{n}</span>' for i, n in enumerate(["Map", "Connections", "Investigate", "Sources"]))
    return (f'<header class="tb"><span class="brand">{icon}<svg class="wm" viewBox="{WMVB}" width="{wm_w:.0f}" height="{WMH:.1f}" aria-label="World Watch">'
            f'<path d="{wm_path}" fill="currentColor"/></svg></span><nav class="tabs">{tabs}</nav>'
            f'<span class="view">Theatre <b>Europe and the Middle East</b></span>'
            f'<span class="search"><i class="lens"></i>Find a place, person or company</span>'
            f'<span class="feeds"><i class="dot live"></i>41 of 45 feeds live</span><span class="gear" aria-label="Settings"></span></header>')


def card():
    D = data(); g = [x for x in D["unrest"]["groups"] if x["id"] == "-1041320|clash|20261127"][0]
    acts = "".join(f'<li><span>{esc(k)}</span><b class="num">{v}</b></li>' for k, v in g["actions"].items())
    return f'''<section class="card">
  <div class="eyebrow"><i class="sw conf"></i>Armed clash · machine-coded</div>
  <h3>Kharkiv</h3><div class="sub">Kharkiv Oblast, Ukraine · <span class="num">49.98 N 36.25 E</span><br>{day(g["first"])} {hhmm(g["first"])}–{hhmm(g["last"])} UTC · {esc(g["action"])}</div>
  <div class="facts"><div><b class="num">{g["outlets"]}</b><span>outlets</span></div><div><b class="num">{g["events"]}</b><span>events</span></div><div><b class="num">{len(g["actions"])}</b><span>kinds of action</span></div></div>
  <div class="reps"><div class="rh">Reports <span>words from the address</span></div>
    <p>Russian forces hit Kyiv with ballistic missiles, seven wounded, mayor says <em>hawaiitribune-herald.com</em></p>
</div>
  <div class="actions"><span class="btn ink">Country dossier</span><span class="btn">Spy passes</span><span class="btn">From orbit</span></div>
  <div class="src">GDELT Events 2.0 · not verified · updated {hhmm(D["ut"])} UTC</div>
</section>'''


def ico(key, col, size=18):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{GL.svg(key, size / 2, size / 2, size, col, "var(--u-panel)", edge_w=6)}</svg>'


def now_list():
    D = data()
    gs = sorted([g for g in D["unrest"]["groups"] if V.inside(g["lon"], g["lat"])], key=lambda g: -g["outlets"])
    seen, rows = set(), []
    for g in gs:
        if g["place"] in seen: continue
        seen.add(g["place"]); rows.append(g)
        if len(rows) == 5: break
    sig = "".join(f'<li class="{"sel" if g["place"].startswith("Kharkiv") else ""}"><i class="g">{ico(kind_of(g), "var(--u-conf)")}</i>'
                  f'<span class="t">{esc(g["place"].split(",")[0])}<small>{esc(g["action"])}</small></span><b class="num">{g["outlets"]}</b></li>' for g in rows)
    up = [x for x in D["launches"]["launches"] if x["net"] > "2026-11-28T03:08"][:2]
    com = "".join(f'<li><i class="g">{ico("launch", "var(--u-sat)")}</i><span class="t">{esc(x["name"].split(" | ")[1])}<small>{esc(x["name"].split(" | ")[0])} · {esc(x["status"])}</small></span>'
                  f'<b class="num">{x["net"][8:10]} Nov {x["net"][11:16]}</b></li>' for x in up)
    return f'''<section class="list"><div class="lh"><b>Now</b><span>in this view</span></div>
  <div class="grp">Signals <span>outlets, 24 h</span></div><ul>{sig}</ul>
  <div class="grp">Coming up <span>UTC</span></div><ul>{com}</ul></section>'''


def tiles():
    D = data()
    occ = f'{D["front"]["occupied_km2"]:,}'
    t = [("clash", "conf", "Protests, clashes", f'{len(D["unrest"]["groups"])}', "GDELT", hhmm(D["ut"])),
         ("news", "news", "News places", f'{len(D["news"]["places"]):,}', "GDELT", hhmm(D["nt"])),
         ("strategic", "mil", "Military aircraft", f'{len(D["mil"]["aircraft"])}', "adsb.fi", hhmm(D["at"])),
         ("occupied", "conf", "km² occupied", f'{occ}', "DeepState", day(D["ft"])),
         ("cargo", "ship", "Ships", f'{len(D["ships"]["ships"])}', "Digitraffic", hhmm(D["st"])),
         ("launch", "sat", "Launches", f'{len(D["launches"]["launches"])}', "Launch Library 2", hhmm(D["lt"]))]
    cells = "".join(f'<div class="tile"><i class="g">{ico(k, f"var(--u-{col})", 16)}</i>'
                    f'<b class="num">{v}</b><span class="n">{n}</span><span class="s"><i class="dot live"></i>{s} · {a}</span></div>' for k, col, n, v, s, a in t)
    return f'<section class="tiles">{cells}<div class="more"><span>6 of 39 layers on</span><b>All layers</b></div></section>'


def seen_from():
    lat, lon, z = VIEW_CENTRE
    return (f'<div class="seen"><span>Seen from</span> <b class="num">{lat_s(lat, "N", "S")} {lat_s(lon, "E", "W")}</b> · zoom {z} · '
            f'{datetime.datetime.fromtimestamp(CAP_T, UTC).strftime("%-d %b %Y %H:%M")} UTC</div>')


def views():
    return '<nav class="views">' + "".join(f'<span class="v{" on" if n == "Theatre" else ""}">{n}</span>' for n in
                                           ["Whole Earth", "Theatre", "Day and night", "Look down", "Over the pole", "Flat map"]) + "</nav>"


def board(t, wm):
    return (f'<div class="fit" data-w="1440" data-h="900"><div class="board ui {t}">{map_svg(t)}{topbar(t, *wm)}'
            f'<aside class="col">{card()}{now_list()}{tiles()}</aside>{views()}{seen_from()}</div></div>')
