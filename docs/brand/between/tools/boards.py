"""Six 1920 x 1080 boards: three 'between' directions x light and dark, Dense layout, Porcelain parts, real data."""
import sys, math, html, base64, json
LANG = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/lang"
HERE = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between"
sys.path.insert(0, LANG); sys.path.insert(0, HERE)
import render as RD
import mock, glyph as GL, mapdata as M
from cam import Cam
esc = lambda s: html.escape(str(s), quote=True)
W, H, COLX = 1920, 1080, 1440
CAM = RD.THEATRE()


class CamView:
    def inside(self, lon, lat, pad=0):
        x, y, vis = CAM.proj(lon, lat)
        return vis and 0 <= x <= COLX and 56 <= y <= H


mock.data(); mock.V = CamView()   # "in this view" now means visible in the theatre camera and not under the column
PAL = {"dark": dict(conf="#fb7185", mil="#a5b4fc", ship="#7dd3fc", news="#e4e4e7", edge="#09090b", ring="#fafafa", halo="#09090b", label="#d4d4d8", area="#fb7185"),
       "light": dict(conf="#e11d48", mil="#4338ca", ship="#0369a1", news="#18181b", edge="#ffffff", ring="#010101", halo="#ffffff", label="#52525b", area="#e11d48")}


def b64(path):
    return "data:image/webp;base64," + base64.b64encode(open(path, "rb").read()).decode()


def markers(pal):
    D = mock.data(); c = PAL[pal]; o = [f'<svg class="mk" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">']
    o.append(f'<g fill="{c["area"]}" fill-opacity=".2" stroke="{c["area"]}" stroke-opacity=".8" stroke-width="1">')
    for a in D["front"]["areas"]:
        if a["kind"] != "occupied": continue
        for ring in a["rings"]:
            pts = [CAM.proj(lo, la) for lo, la in ring]
            if not all(p[2] for p in pts): continue
            o.append('<path d="M' + "L".join(f"{x:.1f} {y:.1f}" for x, y, _ in pts) + 'Z"/>')
    o.append("</g>")
    places = sorted([p for p in D["news"]["places"] if mock.V.inside(p["lon"], p["lat"])], key=lambda p: p["outlets"])
    o.append(f'<g fill="{c["news"]}">')
    for p in places:
        x, y, _ = CAM.proj(p["lon"], p["lat"]); rr = min(8, 1.2 + .6 * math.sqrt(p["outlets"]))
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.1f}" fill-opacity="{.2 if p["outlets"] < 3 else .5}"/>')
    o.append("</g>")
    o.append(f'<g fill="{c["ship"]}" fill-opacity=".85">')
    for s in D["ships"]["ships"]:
        if mock.V.inside(s["lon"], s["lat"]):
            x, y, _ = CAM.proj(s["lon"], s["lat"]); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4"/>')
    o.append("</g>")
    for g in sorted([g for g in D["unrest"]["groups"] if g["outlets"] >= 2 and mock.V.inside(g["lon"], g["lat"])], key=lambda g: g["outlets"]):
        x, y, _ = CAM.proj(g["lon"], g["lat"]); sz = 14 + min(14, 2.3 * math.sqrt(g["outlets"]))
        o.append(GL.svg(mock.kind_of(g), x, y, sz, c["conf"], c["edge"], edge_w=7))
    for a in D["mil"]["aircraft"]:
        if a.get("lat") and mock.V.inside(a["lon"], a["lat"]):
            x, y, _ = CAM.proj(a["lon"], a["lat"])
            o.append(GL.svg(GL.for_type(a.get("type")), x, y, 26, c["mil"], c["edge"], rot=a.get("track") or 0, edge_w=6))
    x, y, _ = CAM.proj(36.2527, 49.9808)
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="23" fill="none" stroke="{c["halo"]}" stroke-width="4" stroke-opacity=".85"/>'
             f'<circle cx="{x:.1f}" cy="{y:.1f}" r="23" fill="none" stroke="{c["ring"]}" stroke-width="1.5"/>')
    for name, lon, lat, dx, dy in [("Kyiv", 30.52, 50.45, -10, -14), ("Moscow", 37.62, 55.75, 14, 4), ("Istanbul", 28.98, 41.01, -12, 18),
                                   ("Berlin", 13.40, 52.52, 10, -8), ("Munich", 11.58, 48.14, 10, 12), ("Warsaw", 21.01, 52.23, 10, -8),
                                   ("Ankara", 32.86, 39.93, 12, 14), ("Tbilisi", 44.79, 41.72, 12, 4), ("Athens", 23.73, 37.98, -12, 16)]:
        x, y, vis = CAM.proj(lon, lat)
        if not vis or x > COLX: continue
        anchor = "end" if dx < 0 else "start"
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{c["label"]}"/><text x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" '
                 f'font-family="B612, system-ui, sans-serif" font-size="12.5" letter-spacing=".04em" fill="{c["label"]}" '
                 f'style="paint-order:stroke;stroke:{c["halo"]};stroke-width:3px;stroke-opacity:.6">{name}</text>')
    o.append("</svg>")
    return "".join(o)


def views_strip(thumbs):
    names = ["Whole Earth", "Theatre", "Day and night", "Look down", "Over the pole", "Low orbit"]
    cells = "".join(f'<span class="vt{" on" if n == "Theatre" else ""}"><img src="{thumbs[i]}" width="128" height="72" alt=""><span>{n}</span></span>' for i, n in enumerate(names))
    return f'<nav class="vstrip">{cells}</nav>'


def board(direction, theme, ground_img, thumbs, pal, material):
    t = "l" if theme == "light" else "d"
    lat, lon = 49.0, 34.0
    seen = (f'<div class="seen"><span>Seen from</span> <b class="num">35.0° N 19.0° E · 2,676 km up</b> · looking at 49.0° N 34.0° E · '
            f'28 Nov 2026 03:08 UTC</div>')
    return (f'<div class="fit" data-w="{W}" data-h="{H}"><div class="board big ui {t} {material} gpal-{pal}" style="background-image:url({ground_img})">'
            f'{markers(pal)}{mock.topbar(t, mock.WMVB_PATH, mock.WMW)}<aside class="col">{mock.card()}{mock.now_list()}{mock.tiles()}</aside>'
            f'{views_strip(thumbs)}{seen}</div></div>')
