"""Build the globe identity page (page.html) from gmarks + directions. Run with uv (uharfbuzz, fonttools, shapely, numpy)."""
import base64, datetime as dt, html, json, math, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "logo" / "tools"))
import typo                                   # noqa: E402  (outlined, kerned wordmarks)
import gmarks as G                            # noqa: E402
import geo                                    # noqa: E402
from gdirs import DIRS, SRC              # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
(OUT / "png").mkdir(exist_ok=True)
esc = lambda s: html.escape(s, quote=True)
F = G.F
BUILT = dt.datetime(2026, 11, 28, 12, 0)     # the moment used for the sun in the clock strip


# ------------------------------------------------------------------ sprite: every mark once, reused with <use>
SPRITE = []


def sym(id_, svg, vb="0 0 64 64"):
    SPRITE.append(f'<symbol id="{id_}" viewBox="{vb}">{G.inner(svg)}</symbol>')


for d in DIRS:
    k = d["key"]
    for v in ("full", "small"):
        sym(f"mk-{k}-{v}-icon", G.mark(k, v, f"{k}{v}i", "icon"))
        sym(f"mk-{k}-{v}-dark", G.mark(k, v, f"{k}{v}d", "on-dark", gap=d["dark"]["bg"]))
        sym(f"mk-{k}-{v}-light", G.mark(k, v, f"{k}{v}l", "on-light", gap=d["light"]["bg"]))
    if k == "oko":
        sym("mk-oko-ticks-icon", G.m_oko("full", "okot", "icon", ticks=True))


def mk(id_, w, h=None, x=None, y=None, cls=""):
    h = h or w
    if x is None:
        return f'<svg class="{cls}" viewBox="0 0 64 64" width="{w}" height="{h}" aria-hidden="true"><use href="#{id_}"/></svg>'
    return f'<use href="#{id_}" x="{F(x)}" y="{F(y)}" width="{F(w)}" height="{F(h)}"/>'


# ------------------------------------------------------------------ wordmarks as outlined paths (no font needed)
WM = {}
for d in DIRS:
    wm = d["wm"]
    path, width, cap = typo.text_path(wm["font"], wm["text"], 100, wm["track"])
    xmin, ymin, xmax, ymax = typo.ink_bounds(wm["font"], wm["text"], 100, wm["track"])
    # svg y grows down; ink_bounds gives font units flipped already (ymin negative = above baseline)
    top, bottom = min(ymin, -ymax), max(-ymin, ymax)
    WM[d["key"]] = dict(d=path, w=width, cap=cap)
    for tone in ("dark", "light"):
        fill = d[tone]["ink"]
        SPRITE.append(f'<symbol id="wm-{d["key"]}-{tone}" viewBox="0 {F(-cap)} {F(width)} {F(cap)}" overflow="visible">'
                      f'<path d="{path}" fill="{fill}"/></symbol>')


def wordmark(key, tone, x, y_base, cap_h):
    w = WM[key]
    s = cap_h / w["cap"]
    return (f'<use href="#wm-{key}-{tone}" x="{F(x)}" y="{F(y_base - cap_h)}" width="{F(w["w"] * s)}" height="{F(cap_h)}"/>',
            w["w"] * s)


def T(x, y, s, size=12, fill="#000", weight=400, fam="Inter", anchor="start", ls=0, op=1):
    return (f'<text x="{F(x)}" y="{F(y)}" font-family="{fam}, system-ui, sans-serif" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{esc(s)}</text>')


def MONO(x, y, s, size=11, fill="#000", weight=500, anchor="start", op=1):
    return T(x, y, s, size, fill, weight, "IBM Plex Mono", anchor, 0, op)


def svgbox(w, h, body, label, cls="spec"):
    return f'<svg class="{cls}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">{body}</svg>'


# ------------------------------------------------------------------ devices
def dev_oko_loader(t, tone):
    w, h = 520, 200
    s = 236 / (2 * G.MOL_A)
    cx, cy = 190, 100
    A, B, c, R = G.MOL_A * s, G.MOL_B * s, G.MOL_A * G.MOL_E * s, G.RE * s
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += f'<circle cx="{F(cx - c)}" cy="{cy}" r="{F(R)}" fill="{t["ink"]}"/>'
    for x, y in G.molniya_times(24):
        b += f'<circle cx="{F(cx - x * s)}" cy="{F(cy - y * s)}" r="2.6" fill="{t["sub"]}" opacity=".55"/>'
    b += (f'<circle class="kd" data-cx="{F(cx)}" data-cy="{F(cy)}" data-s="{s}" r="4.2" fill="{t["acc"]}" '
          f'cx="{F(cx - A)}" cy="{cy}"/>')
    b += MONO(350, 94, "Loading", 13, t["ink"]) + MONO(350, 114, "24 dots = 11.94 h", 11, t["sub"], 400)
    return svgbox(w, h, b, "Loading dots along the Molniya orbit", "spec kepler")


def dev_oko_ruler(t, tone):
    w, h = 520, 200
    x0, x1, y = 24, 496, 112
    sc = (x1 - x0) / 40000
    X = lambda km: x0 + km * sc
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += f'<rect x="{x0 - 6}" y="{y - 30}" width="6" height="60" fill="{t["ink"]}"/>'
    b += f'<rect x="{F(X(160))}" y="{y - 14}" width="{F(X(2000) - X(160))}" height="28" fill="{t["acc"]}"/>'
    b += f'<rect x="{F(X(2000))}" y="{y - 14}" width="{F(X(35786) - X(2000))}" height="28" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    b += f'<line x1="{F(X(35786))}" y1="{y - 22}" x2="{F(X(35786))}" y2="{y + 22}" stroke="{t["ink"]}" stroke-width="2.5"/>'
    b += f'<line x1="{F(X(39700))}" y1="{y - 22}" x2="{F(X(39700))}" y2="{y + 22}" stroke="{t["acc"]}" stroke-width="2.5" stroke-dasharray="3 3"/>'
    b += MONO(X(160), y - 24, "LEO", 11, t["ink"]) + MONO(X(2000) + 8, y + 5, "MEO", 11, t["sub"])
    b += MONO(X(35786), y - 28, "GEO 35,786", 10.5, t["ink"], anchor="end")
    b += MONO(X(39700), y + 40, "Oko apogee 39,700", 10.5, t["sub"], anchor="end")
    for km in (0, 10000, 20000, 30000, 40000):
        b += f'<line x1="{F(X(km))}" y1="{y + 50}" x2="{F(X(km))}" y2="{y + 56}" stroke="{t["line"]}"/>'
        b += MONO(X(km), y + 70, f"{km:,} km" if km else "ground", 10, t["sub"], 400, "end" if km == 40000 else ("middle" if km else "start"))
    return svgbox(w, h, b, "Altitude ruler to scale")


def dev_fp_chips(t, tone):
    w, h = 520, 200
    rows = [("ISS", "420 km", "3.1 %", 20.3), ("Sentinel-2", "786 km", "5.5 %", 27.1), ("GPS", "20,200 km", "38.0 %", 76.1)]
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    for i, (n, alt, share, rho) in enumerate(rows):
        y = 30 + i * 52
        b += f'<rect x="24" y="{y}" width="470" height="38" rx="19" fill="{t["panel"]}" stroke="{t["line"]}"/>'
        b += f'<circle cx="44" cy="{y + 19}" r="12" fill="{t["ink"]}"/>'
        d = G.onlimb(geo.small_circle(geo.MUC[0], geo.MUC[1], rho, 240), G.FP_CAM, 12, 44, y + 19)
        b += f'<path d="{d}" fill="{t["acc"]}"/>'
        b += T(66, y + 24, n, 13, t["ink"], 600) + MONO(160, y + 24, alt, 12, t["sub"], 400)
        b += MONO(478, y + 24, f"sees {share} of the Earth", 12, t["ink"], 500, "end")
    return svgbox(w, h, b, "Coverage chips")


def dev_fp_scale(t, tone):
    w, h = 520, 200
    cam, r, cx, cy = (35.0, 0.0), 84, 140, 100
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    for i, (n, alt) in enumerate([("GEO", 35786), ("GPS", 20200), ("Sentinel-2", 786), ("ISS", 420)]):
        rho = geo.horizon_angle(alt)
        d = G.onlimb(geo.small_circle(geo.MUC[0], geo.MUC[1], rho, 360), cam, r, cx, cy)
        op = [.18, .3, .55, .9][i]
        b += f'<path d="{d}" fill="{t["acc"]}" fill-opacity="{op}" stroke="{t["acc"]}" stroke-width="1"/>'
    mx, my, _ = geo.project_pts([geo.MUC], cam, cx, cy, r)[0]
    b += f'<circle cx="{F(mx)}" cy="{F(my)}" r="3" fill="{t["ink"]}"/>'
    lab = [("ISS, 420 km", "20.3°"), ("Sentinel-2, 786 km", "27.1°"), ("GPS, 20,200 km", "76.1°"), ("GEO, 35,786 km", "81.3°")]
    for i, (a, bb) in enumerate(lab):
        y = 52 + i * 32
        b += T(270, y, a, 13, t["ink"], 500) + MONO(496, y, bb, 12, t["sub"], 400, "end")
    return svgbox(w, h, b, "Horizon scale for four satellites")


def dev_un_switch(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    for i, sel in enumerate(("globe", "map")):
        y = 40 + i * 70
        b += f'<rect x="24" y="{y}" width="260" height="48" rx="12" fill="{t["panel"]}" stroke="{t["line"]}"/>'
        selx = 28 if sel == "globe" else 154
        b += f'<rect x="{selx}" y="{y + 4}" width="126" height="40" rx="9" fill="{t["acc"]}"/>'
        on, off = (t["bg"], t["ink"])
        gcol = on if sel == "globe" else off
        mcol = on if sel == "map" else off
        # half globe glyph
        gx, gy = 52, y + 24
        b += f'<path d="M{gx},{gy - 12} A12,12 0 0 0 {gx},{gy + 12} Z" fill="{gcol}"/>'
        b += f'<path d="M{gx},{gy - 12} A6,12 0 0 0 {gx},{gy + 12}" fill="none" stroke="{t["acc"] if sel == "globe" else t["panel"]}" stroke-width="1.6"/>'
        b += T(64, gy + 5, "Globe", 14, gcol, 600)
        mx = 176
        for cc in range(2):
            for rr in range(2):
                b += f'<rect x="{mx + cc * 9}" y="{gy - 9 + rr * 9}" width="7.5" height="7.5" fill="{mcol}"/>'
        b += T(200, gy + 5, "Map", 14, mcol, 600)
    b += MONO(310, 70, "Globe selected", 11, t["sub"], 400) + MONO(310, 140, "Map selected", 11, t["sub"], 400)
    return svgbox(w, h, b, "Map and globe switch")


def dev_un_tiles(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    rows = [(2, 2, 1), (6, 34, 22), (10, 544, 355), (14, 8718, 5685)]
    for i, (z, x, y) in enumerate(rows):
        X = 24 + i * 124
        size = [56, 40, 26, 14][i]
        b += f'<rect x="{X}" y="{100 - size / 2 - 20}" width="{size}" height="{size}" fill="{t["acc"]}"/>'
        b += MONO(X, 128, f"zoom {z}", 11, t["sub"], 400) + MONO(X, 148, f"{x} / {y}", 14, t["ink"], 600)
    b += T(24, 182, "Munich, 48.14° N 11.58° E: its tile at each zoom (x / y)", 12, t["sub"])
    return svgbox(w, h, b, "Tile address stamp")


def dev_ah_share(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    x0, x1 = 170, 470
    sc = (x1 - x0) / 50
    rows = [("Whole Earth", 28.7), ("Seen above Munich", 45.5), ("Best any view", 46.7)]
    for i, (n, v) in enumerate(rows):
        y = 40 + i * 44
        b += T(24, y + 15, n, 13, t["ink"], 500)
        b += f'<rect x="{x0}" y="{y}" width="{F(50 * sc)}" height="20" fill="{t["panel"]}"/>'
        b += f'<rect x="{x0}" y="{y}" width="{F(v * sc)}" height="20" fill="{t["acc"] if i == 1 else t["sub"]}"/>'
        b += MONO(x0 + v * sc + 8, y + 15, f"{v} %", 12, t["ink"], 600)
    for v in (0, 25, 50):
        b += MONO(x0 + v * sc, 182, f"{v} %", 10, t["sub"], 400, "middle")
    b += T(24, 182, "Land share", 11, t["sub"])
    return svgbox(w, h, b, "Land share bars")


def dev_ah_dots(t, tone):
    import numpy as np, shapely
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    land = G._land()
    cx, cy, r, step = 260, 100, 92, 5.0
    xs, ys, pts = [], [], []
    p0, l0 = geo.MUC[0] * geo.D, geo.MUC[1]
    for j in range(-int(r / step), int(r / step) + 1):
        for i in range(-int(r / step), int(r / step) + 1):
            x, y = i * step / r, -j * step / r
            rho = math.hypot(x, y)
            if rho >= 0.985:
                continue
            c = math.asin(rho)
            if rho == 0:
                la, lo = geo.MUC
            else:
                la = math.degrees(math.asin(math.cos(c) * math.sin(p0) + y * math.sin(c) * math.cos(p0) / rho))
                lo = l0 + math.degrees(math.atan2(x * math.sin(c), rho * math.cos(c) * math.cos(p0) - y * math.sin(c) * math.sin(p0)))
            pts.append((cx + i * step, cy + j * step)); xs.append(((lo + 540) % 360) - 180); ys.append(la)
    inside = shapely.contains_xy(land, np.array(xs), np.array(ys))
    b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["line"]}"/>'
    for (px, py), on in zip(pts, inside):
        b += f'<circle cx="{F(px)}" cy="{F(py)}" r="{1.6 if on else .7}" fill="{t["acc"] if on else t["line"]}"/>'
    b += f'<circle cx="{cx}" cy="{cy}" r="3.2" fill="{t["ink"]}"/>'
    return svgbox(w, h, b, "Points of light background")


def octant_glyph(x, y, s, fill, globe, line=None):
    cam, r = G.OC_CAM, s / 2
    d = G.onlimb(G.slerp((90, 0), (0, 0)) + G.slerp((0, 0), (0, 90)) + G.slerp((0, 90), (90, 0)), cam, r, x, y)
    st = f' stroke="{line}"' if line else ""
    return f'<circle cx="{F(x)}" cy="{F(y)}" r="{F(r)}" fill="{globe}"{st}/><path d="{d}" fill="{fill}"/>'


def dev_oc_hint(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += octant_glyph(110, 100, 160, t["acc"], t["panel"], t["line"])
    # right-angle marks at the three corners (computed screen positions)
    cam, r, cx, cy = G.OC_CAM, 80, 110, 100
    for (la, lo), (la2, lo2), (la3, lo3) in [((90, 0), (80, 0), (80, 90)), ((0, 0), (10, 0), (0, 10)), ((0, 90), (10, 90), (0, 80))]:
        P = geo.project_pts([(la, lo), (la2, lo2), (la3, lo3)], cam, cx, cy, r)
        (ax, ay, _), (bx, by, _), (qx, qy, _) = P
        k = 0.55
        ux, uy = ax + (bx - ax) * k, ay + (by - ay) * k
        vx, vy = ax + (qx - ax) * k, ay + (qy - ay) * k
        wx, wy = ux + vx - ax, uy + vy - ay
        b += f'<path d="M{F(ux)},{F(uy)} L{F(wx)},{F(wy)} L{F(vx)},{F(vy)}" fill="none" stroke="{t["ink"]}" stroke-width="1.6"/>'
    b += MONO(230, 92, "90° + 90° + 90° = 270°", 15, t["ink"], 600)
    b += T(230, 118, "On a flat page the angles of a triangle make 180°.", 12, t["sub"])
    b += T(230, 136, "The extra 90° is the curvature: 1/8 of a sphere.", 12, t["sub"])
    return svgbox(w, h, b, "Curvature hint")


def dev_oc_progress(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    for i in range(8):
        on = i < 5
        b += octant_glyph(52 + i * 59, 92, 46, t["acc"] if on else t["line"], t["panel"], t["line"])
    b += MONO(24, 160, "5 of 8", 14, t["ink"], 600) + T(84, 160, "Scan progress in eighths (example state)", 12, t["sub"])
    return svgbox(w, h, b, "Progress in eighths")


def lune_glyph(x, y, s, fill, globe):
    r = s / 2
    pts = [(-90 + i * 2, 7.5) for i in range(91)] + [(90 - i * 2, 22.5) for i in range(91)]
    return f'<circle cx="{F(x)}" cy="{F(y)}" r="{F(r)}" fill="{globe}"/><path d="{G.onlimb(pts, (0, 15), r, x, y)}" fill="{fill}"/>'


def dev_lu_clock(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    _, slat, slon = geo.sun(BUILT)
    x0, span = 24, 472
    wd = span / 24
    X = lambda lon: x0 + ((lon + 172.5) % 360) / 360 * span     # zones are centred on multiples of 15 deg
    for i in range(24):
        centre = -165 + 15 * i                                   # UTC-11 ... UTC+12
        cx = X(centre)
        fill = t["acc"] if centre == 15 else t["line"]
        b += f'<path d="M{F(cx)},50 Q{F(cx + wd * .62)},95 {F(cx)},140 Q{F(cx - wd * .62)},95 {F(cx)},50 Z" fill="{fill}"/>'
    sx = X(slon)
    b += f'<line x1="{F(sx)}" y1="44" x2="{F(sx)}" y2="146" stroke="#E40166" stroke-width="2"/>'
    b += MONO(x0, 168, "UTC\u221211", 10, t["sub"], 400) + MONO(x0 + span, 168, "UTC+12", 10, t["sub"], 400, "end")
    b += MONO(X(15), 36, "UTC+1", 11, t["ink"], 600, "middle")
    ew = "E" if slon >= 0 else "W"
    b += MONO(x0 + span / 2, 190, f"magenta: sun overhead, {abs(slon):.1f}\u00b0 {ew}, 28 Nov 2026 12:00 UTC", 10, t["sub"], 400, "middle")
    return svgbox(w, h, b, "World clock strip")


def dev_lu_stamp(t, tone):
    w, h = 520, 200
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += f'<rect x="24" y="44" width="472" height="60" rx="10" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    b += T(40, 70, "Quake near Innsbruck", 14, t["ink"], 600) + T(40, 90, "USGS (example card)", 12, t["sub"])
    b += f'<rect x="300" y="60" width="180" height="28" rx="14" fill="{t["bg"]}" stroke="{t["line"]}"/>'
    b += lune_glyph(318, 74, 18, t["bg"], t["acc"])
    b += MONO(334, 79, "14:02 UTC+1 · CET", 12, t["ink"], 500)
    b += T(24, 140, "Every time carries its hour: the lune of the zone it is shown in.", 12, t["sub"])
    return svgbox(w, h, b, "Hour stamp")


DEVICES = {"oko": [dev_oko_loader, dev_oko_ruler], "footprint": [dev_fp_chips, dev_fp_scale],
           "unrolled": [dev_un_switch, dev_un_tiles], "above": [dev_ah_share, dev_ah_dots],
           "octant": [dev_oc_hint, dev_oc_progress], "lune": [dev_lu_clock, dev_lu_stamp]}


# ------------------------------------------------------------------ in use: top bar and splash
def topbar(d, tone):
    t = d[tone]
    w, h = 960, 60
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/><line x1="0" y1="{h - .5}" x2="{w}" y2="{h - .5}" stroke="{t["line"]}"/>'
    b += mk(f"mk-{d['key']}-small-icon", 30, x=18, y=15)
    use, ww = wordmark(d["key"], tone, 60, 37, 13)
    b += use
    x = 60 + ww + 34
    for i, n in enumerate(["Map", "Connections", "Investigate", "Sources"]):
        wdt = 9 + len(n) * 7.3
        if i == 0:
            b += f'<rect x="{F(x - 10)}" y="16" width="{F(wdt + 8)}" height="28" rx="8" fill="{t["panel"]}"/>'
        b += T(x, 35, n, 13.5, t["ink"] if i == 0 else t["sub"], 600 if i == 0 else 500)
        x += wdt + 18
    b += f'<rect x="{w - 330}" y="15" width="200" height="30" rx="15" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    b += T(w - 314, 35, "Find a person or country", 12.5, t["sub"])
    b += f'<rect x="{w - 116}" y="15" width="98" height="30" rx="15" fill="none" stroke="{t["line"]}"/>'
    b += f'<circle cx="{w - 98}" cy="30" r="4" fill="{t["acc"]}"/>' + T(w - 88, 35, "Feeds", 12.5, t["ink"], 500)
    return svgbox(w, h, b, f"Top bar, {tone}", "spec bar")


SPLASH_LINE = "Real data only. Every layer shows its source."


def splash(d, tone):
    t = d[tone]
    w, h = 960, 380
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    if d["key"] == "above":
        # the points-of-light device fills the right side
        pass
    b += mk(f"mk-{d['key']}-full-{tone}", 190, x=70, y=95)
    use, ww = wordmark(d["key"], tone, 310, 186, 42)
    b += use
    b += T(312, 232, SPLASH_LINE, 22, t["sub"], 400)
    fact = {"oko": "Molniya orbit to scale · 600 × 39,700 km · 11.94 h",
            "unrolled": "Seam at 0° · Munich = tile 2/2/1",
            "footprint": "Sentinel-2 at 786 km sees 27.1° around Munich",
            "above": "Above Munich: 45.5 % land in view",
            "octant": "90° + 90° + 90° = 270° · Munich inside",
            "lune": "UTC+1 · 7.5° E to 22.5° E · Munich inside"}[d["key"]]
    b += MONO(312, 284, fact, 17, t["acc"], 500)
    b += MONO(312, 312, "Starting feeds…", 15, t["sub"], 400)
    return svgbox(w, h, b, f"Splash, {tone}", "spec splash")


def lockup(d, tone):
    t = d[tone]
    w, h = 520, 150
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>'
    b += mk(f"mk-{d['key']}-full-{tone}", 86, x=32, y=32)
    use, ww = wordmark(d["key"], tone, 140, 90, 26)
    return svgbox(w, h, b + use, f"Lockup, {tone}", "spec")


# ------------------------------------------------------------------ real-size renders (Chromium, 1 device pixel per px)
def render_strips():
    marks = {d["key"]: {"full": G.mark(d["key"], "full", "a", "icon"), "small": G.mark(d["key"], "small", "b", "icon")} for d in DIRS}
    (OUT / "marks.json").write_text(json.dumps(marks))
    subprocess.run(["node", str(HERE / "strips.js"), str(OUT / "marks.json"), str(OUT / "png")], check=True)
    for d in DIRS:
        for bg in ("dark", "light", "dock"):
            pathlib.Path(OUT / "marks").mkdir(exist_ok=True)
        (OUT / "marks" / f"{d['key']}.svg").write_text(marks[d["key"]]["full"])
        (OUT / "marks" / f"{d['key']}-small.svg").write_text(marks[d["key"]]["small"])


def png(key, bg):
    return "data:image/png;base64," + base64.b64encode((OUT / "png" / f"{key}-{bg}.png").read_bytes()).decode()


# ------------------------------------------------------------------ page
def section(d):
    k = d["key"]
    rank = {1: "First choice", 2: "Second choice", 3: "Third choice"}.get(d["rank"], "Also drawn")
    s = f'<section class="dir" id="{k}"><header class="dhead"><p class="eyebrow">{rank} · palette: {esc(d["agency"])}</p>'
    s += f'<h2>{esc(d["name"])}</h2><p class="idea">{esc(d["idea"])}</p></header>'
    # hero
    s += '<div class="hero2"><div class="bigmark">' + mk(f"mk-{k}-full-icon", 220, cls="big") + "</div>"
    s += '<div class="story">' + "".join(f"<p>{esc(p)}</p>" for p in d["story"])
    s += '<dl class="facts">' + "".join(f"<div><dt>{esc(a)}</dt><dd>{esc(b)}</dd></div>" for a, b in d["facts"]) + "</dl></div></div>"
    # sizes
    s += '<h3>At real size</h3><p class="note">16, 24, 32 and 48 px, rendered at one device pixel per pixel on a dark taskbar, a light taskbar and a Dock-like shelf. Below, the same pictures enlarged three times, pixel for pixel.</p>'
    s += '<div class="sizes">' + "".join(f'<figure><img src="{png(k, bg)}" alt="{esc(d["name"])} at 16 to 48 px, {bg}" class="px"><figcaption>{lab}</figcaption></figure>'
                                         for bg, lab in (("dark", "Windows, dark"), ("light", "Windows, light"), ("dock", "macOS Dock"))) + "</div>"
    s += f'<div class="zoom"><img src="{png(k, "dark")}" alt="" class="z4"><img src="{png(k, "light")}" alt="" class="z4"></div>'
    s += f'<p class="note">{esc(d["small"])}</p>'
    # lockups + colour
    s += '<div class="two"><div><h3>Wordmark</h3>' + lockup(d, "dark") + lockup(d, "light")
    s += f'<p class="note">{esc(d["wm"]["family"])}, outlined (no font needed). Text in the app: Inter; numbers: IBM Plex Mono.</p></div>'
    s += '<div><h3>Colour</h3><ul class="swatches">'
    for c in d["palette"]:
        s += (f'<li><span class="chip" style="background:{c["hex"]}"></span><span class="sw-name">{esc(c["name"])}</span>'
              f'<code>{c["hex"]}</code><span class="sw-role">{esc(c["role"])}</span>'
              f'<span class="share"><span style="width:{c["share"]}%"></span></span><span class="pc">{c["share"]} %</span></li>')
    src = SRC[d["src"]]
    s += f'</ul><p class="note">Source: <a href="{src[1]}">{esc(src[0])}</a>. {esc(src[2])} {esc(d["mixes"])}</p></div></div>'
    # devices
    s += "<h3>Two graphic devices</h3><div class=\"devs\">"
    for fn, (name, cap) in zip(DEVICES[k], d["devices"]):
        s += f'<figure class="dev"><div class="pair">{fn(d["dark"], "dark")}{fn(d["light"], "light")}</div><figcaption><b>{esc(name)}.</b> {esc(cap)}</figcaption></figure>'
    s += "</div>"
    # in use
    s += '<h3>In use</h3><div class="use">' + topbar(d, "dark") + topbar(d, "light") + '<div class="splashes">' + splash(d, "dark") + splash(d, "light") + "</div></div>"
    s += f'<p class="note">Top bar and splash are mock-ups; the nav labels are the app’s real pages, the splash line is the project’s first rule.</p>'
    s += f'<div class="verdict"><div><h4>What works</h4><p>{esc(d["good"])}</p></div><div><h4>What does not</h4><p>{esc(d["weak"])}</p></div></div>'
    return s + "</section>"


def overview():
    s = '<div class="overview">'
    order = sorted(DIRS, key=lambda d: d["rank"] or 9)
    for d in order:
        tag = {1: "1st", 2: "2nd", 3: "3rd"}.get(d["rank"], "")
        s += (f'<a class="ov" href="#{d["key"]}"><span class="ovmark">{mk(f"mk-{d["key"]}-full-icon", 84)}</span>'
              f'<span class="ovsmall">{mk(f"mk-{d["key"]}-small-icon", 24)}{mk(f"mk-{d["key"]}-small-icon", 16)}</span>'
              f'<span class="ovname">{esc(d["name"])}{f" <em>{tag}</em>" if tag else ""}</span>'
              f'<span class="ovidea">{esc(d["idea"].split(":")[0].split(";")[0])}</span></a>')
    return s + "</div>"


CSS = open(HERE / "page.css").read()
JS = open(HERE / "page.js").read()


def main():
    render_strips()
    order = sorted(DIRS, key=lambda d: d["rank"] or 9)
    sprite = '<svg width="0" height="0" style="position:absolute" aria-hidden="true">' + "".join(SPRITE) + "</svg>"
    body = (f'<title>World Watch globe marks</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">'
            f"<style>{CSS}</style>{sprite}<main class=\"wrap\">")
    body += open(HERE / "intro.html").read()
    body += overview()
    body += "".join(section(d) for d in order)
    body += open(HERE / "outro.html").read()
    body += f"</main><script>{JS}</script>"
    (OUT / "page.html").write_text(body)
    print("page", round(len(body) / 1024), "KB")


if __name__ == "__main__":
    main()
