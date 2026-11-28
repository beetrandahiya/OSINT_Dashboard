"""World Watch logo marks on a 64-unit grid.

Every mark is a function (variant, uid) -> inner SVG markup for viewBox 0 0 64 64.
variant: "full" (32 px and up) or "small" (16 and 24 px: fewer parts, heavier strokes).
uid makes clipPath ids unique when many marks share one HTML page.
"""
import math

R = 14  # tile corner radius on the 64 grid (about the macOS / Fluent plate rounding)


def tile(fill, extra=""):
    return f'<rect width="64" height="64" rx="{R}" fill="{fill}"{extra}/>'


def clip(uid):
    return f'<clipPath id="c{uid}"><rect width="64" height="64" rx="{R}"/></clipPath>'


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def pts(ps):
    return " ".join(f"{f(x)},{f(y)}" for x, y in ps)


# ---------------------------------------------------------------- palettes
# Every hex here is quoted from a published source; see PALETTES in sheet.py for URLs.
BP = dict(black="#111418", dg1="#1C2127", dg3="#2F343C", g4="#ABB3BF", lg5="#F6F7F9", white="#FFFFFF",
          blue3="#2D72D2", blue4="#4C90F0")                       # Palantir Blueprint
ESA = dict(deep="#003247", deep2="#01374E", blue="#009BDB", sky="#6DCFF6", grey="#9FB0BB", paper="#E8E8E4",
           ink="#00121A")                                          # ESA
BRG = dict(petrol="#007194", t80="#338DA9", t60="#66AABF", t40="#99C6D4", t20="#CCE3EA", black="#000000",
           white="#FFFFFF")                                        # Bundesregierung
UN = dict(blue="#009EDB", white="#FFFFFF", ink="#000000")           # United Nations
NGA = dict(ink="#1B1B1B", navy="#154E7D", navy2="#0D2F4B", teal="#2FA3AA", mist="#F0F0F0", grey="#DFE1E2",
           blue2="#447197")                                        # NGA website
AND = dict(black="#010101", grey="#8E9291", green="#505544", lime="#DFF140", white="#FFFFFF")   # Anduril
NASA = dict(blue="#0032A0", red="#E4002B", white="#FFFFFF", black="#000000")                   # NASA
NATO = dict(blue="#004990", light="#118ACB", black="#000000", white="#FFFFFF")                 # NATO
GOV = dict(ink="#0B0C0C", blue="#1D70B8", dblue="#0F385C", red="#CA3535", green="#0F7A52", white="#FFFFFF")  # GOV.UK
EU = dict(blue="#003399", yellow="#FFCC00", white="#FFFFFF")       # EU emblem
CAN = dict(slate="#26374A", link="#284162", text="#333333", red="#D3080C", white="#FFFFFF")    # Canada.ca


# ---------------------------------------------------------------- 01 Cocked hat
def _bearing(p, q, w, col):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    a = (p[0] - ux * 120, p[1] - uy * 120)
    b = (p[0] + ux * 120, p[1] + uy * 120)
    return f'<line x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" stroke="{col}" stroke-width="{w}"/>'


COCKED = {
    "full": dict(P=[(23, 39), (42, 36.5), (31.5, 22)], w=3.6),
    "small": dict(P=[(16.5, 43), (47.5, 39), (30.5, 14.5)], w=6.2),
}


def rot(P, deg, c=(32, 32.5)):
    t = math.radians(deg)
    return [(c[0] + (x - c[0]) * math.cos(t) - (y - c[1]) * math.sin(t),
             c[1] + (x - c[0]) * math.sin(t) + (y - c[1]) * math.cos(t)) for x, y in P]


def m_cocked(v, uid, pal=None):
    pal = pal or dict(plate=BP["black"], line=BP["lg5"], acc=BP["blue4"])
    g = COCKED[v]
    P, w = rot(g["P"], 25), g["w"]
    lines = "".join(_bearing(P[i], P[(i + 1) % 3], w, pal["line"]) for i in range(3))
    return (clip(uid) + tile(pal["plate"]) + f'<g clip-path="url(#c{uid})">{lines}'
            f'<polygon points="{pts(P)}" fill="{pal["acc"]}"/></g>')


# ---------------------------------------------------------------- 02 Terminator
DECL = -21.3  # solar declination on 28 Nov (degrees); real value for the date the sheet was made


def _terminator_lat(dlon, alt=0.0, decl=DECL):
    """Latitude (deg) where the sun's altitude equals `alt` at hour-angle dlon (deg). South is day."""
    d = math.radians(decl)
    a = math.radians(alt)
    lo, hi = -90.0, 90.0
    def h(phi):
        p = math.radians(phi)
        return math.asin(max(-1, min(1, math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(math.radians(dlon))))) - a
    for _ in range(50):
        mid = (lo + hi) / 2
        if h(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def terminator_path(x0, x1, ytop, ybot, sub_x, width_deg, alt, closed_to="bottom", n=96):
    """Polyline of the alt-contour across [x0,x1]; x maps to hour angle, y maps latitude linearly."""
    pts_ = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        dlon = (x - sub_x) / (x1 - x0) * width_deg
        lat = _terminator_lat(dlon, alt)
        y = ytop + (90 - lat) / 180 * (ybot - ytop)
        pts_.append((x, y))
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts_)
    if closed_to == "bottom":
        d += f" L{f(x1)} {f(ybot + 40)} L{f(x0)} {f(ybot + 40)} Z"
    return d


def m_term(v, uid, pal=None):
    """The flat world map (2:1) with the day/night line computed for 28 Nov 2026, floating on space."""
    pal = pal or dict(space=ESA["ink"], night=ESA["deep"], twi=ESA["blue"], day=ESA["paper"])
    x0, x1, y0, y1, r = (3, 61, 17.5, 46.5, 3.5) if v == "full" else (1.5, 62.5, 15, 49, 4.5)
    sub = x0 + (x1 - x0) * 0.62
    day = terminator_path(x0, x1, y0, y1, sub, 360, 0)
    tw = terminator_path(x0, x1, y0, y1, sub, 360, -12 if v == "full" else -18)
    return (tile(pal["space"]) +
            f'<clipPath id="m{uid}"><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{r}"/></clipPath>'
            f'<g clip-path="url(#m{uid})"><rect width="64" height="64" fill="{pal["night"]}"/>'
            f'<path d="{tw}" fill="{pal["twi"]}"/><path d="{day}" fill="{pal["day"]}"/></g>')


# ---------------------------------------------------------------- 03 Quadkey 1-2-0-2-3
# Munich 48.137 N, 11.575 E -> Web Mercator quadkey 1 2 0 2 3 0 ...
def quad_cells(digits):
    x0, y0, s = 0.0, 0.0, 64.0
    out = []
    for dch in digits:
        dgt = int(dch)
        s /= 2
        x0 += s * (dgt % 2)
        y0 += s * (dgt // 2)
        out.append((x0, y0, s))
    return out


def m_quad(v, uid, pal=None):
    pal = pal or dict(plate=BRG["petrol"], steps=[BRG["t60"], BRG["t40"], BRG["t20"], BRG["white"], BRG["petrol"]],
                      grid=BRG["t80"])
    digits = "12023" if v == "full" else "120"
    cells = quad_cells(digits)
    steps = pal["steps"] if v == "full" else [pal["steps"][0], pal["steps"][2], pal["steps"][3]]
    out = clip(uid) + tile(pal["plate"]) + f'<g clip-path="url(#c{uid})">'
    for (x, y, s), col in zip(cells, steps):
        out += f'<rect x="{f(x)}" y="{f(y)}" width="{f(s)}" height="{f(s)}" fill="{col}"/>'
    if v == "full":
        out += f'<path d="M32 0V64M0 32H64" stroke="{pal["grid"]}" stroke-width="1"/>'
    return out + "</g>"


# ---------------------------------------------------------------- 04 Great circle
def m_gc(v, uid, pal=None):
    """A great-circle route (solid, bowed) beside the straight line the flat map suggests (dashed)."""
    pal = pal or dict(plate=UN["blue"], fg=UN["white"])
    fg, pl = pal["fg"], pal["plate"]
    if v == "full":
        a, b, c1, c2, sw, rn, rd = (11, 48), (53, 34), (18, 12), (42, 10), 5, 4, 5.6
    else:
        a, b, c1, c2, sw, rn, rd = (10, 49), (54, 33), (18, 9), (44, 8), 8, 5.5, 8
    out = tile(pl) + (f'<path d="M{a[0]} {a[1]} C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {b[0]} {b[1]}" fill="none" '
                      f'stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>')
    if v == "full":
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        s0 = (a[0] + ux * (rn + 5), a[1] + uy * (rn + 5))
        e0 = (b[0] - ux * (rd + 4), b[1] - uy * (rd + 4))
        out += (f'<line x1="{f(s0[0])}" y1="{f(s0[1])}" x2="{f(e0[0])}" y2="{f(e0[1])}" stroke="{fg}" '
                f'stroke-width="2.6" stroke-dasharray="3.4 3"/>')
    out += (f'<circle cx="{a[0]}" cy="{a[1]}" r="{rn}" fill="{pl}" stroke="{fg}" stroke-width="{f(sw * .7)}"/>'
            f'<circle cx="{b[0]}" cy="{b[1]}" r="{rd}" fill="{fg}"/>')
    return out


# ---------------------------------------------------------------- 05 Plot (radar history dots)
def m_plot(v, uid, pal=None):
    """Radar history dots: only positions actually reported, the newest one (the diamond) leading."""
    pal = pal or dict(plate=NGA["navy2"], dot=NGA["mist"], tgt=NGA["teal"])
    if v == "full":
        dots, r, head, hs, ang = [(12, 51), (14, 42), (19, 34), (26, 28.5)], 3, (40, 25), 8.5, -12
    else:
        dots, r, head, hs, ang = [(12, 50), (18, 36)], 5, (37, 26), 11, -20
    out = tile(pal["plate"])
    for x, y in dots:
        out += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{pal["dot"]}"/>'
    hx, hy = head
    t = math.radians(ang)
    ux, uy = math.cos(t), math.sin(t)
    px, py = -uy, ux
    d = [(hx + ux * hs * 1.25, hy + uy * hs * 1.25), (hx + px * hs * .8, hy + py * hs * .8),
         (hx - ux * hs * .9, hy - uy * hs * .9), (hx - px * hs * .8, hy - py * hs * .8)]
    return out + f'<polygon points="{pts(d)}" fill="{pal["tgt"]}"/>'


# ---------------------------------------------------------------- 06 W trace
def m_trace(v, uid, pal=None):
    pal = pal or dict(plate=AND["black"], base=AND["grey"], sig=AND["lime"])
    if v == "full":
        base = "M6 36 H16 M48 36 H58"
        w = "M16 36 L20 15 L26 49 L32 25 L38 49 L44 15 L48 36"
        sw = 4.4
    else:
        base = "M3 36 H9 M55 36 H61"
        w = "M9 36 L14 10 L23 52 L32 24 L41 52 L50 10 L55 36"
        sw = 7
    return (tile(pal["plate"]) +
            f'<path d="{base}" stroke="{pal["base"]}" stroke-width="{sw}" stroke-linecap="square" fill="none"/>'
            f'<path d="{w}" stroke="{pal["sig"]}" stroke-width="{sw}" stroke-linejoin="miter" '
            f'stroke-miterlimit="10" stroke-linecap="square" fill="none"/>')


# ---------------------------------------------------------------- 07 GMT bezel
def _arc(cx, cy, r, a0, a1):
    """Arc from clock angle a0 to a1 (degrees, 0 = 12 o'clock, clockwise)."""
    def p(a):
        t = math.radians(a)
        return cx + r * math.sin(t), cy - r * math.cos(t)
    x0, y0 = p(a0)
    x1, y1 = p(a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{f(x0)} {f(y0)} A{f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}"


def m_gmt(v, uid, pal=None):
    """A 24-hour bezel: the day half (06-18 h) solid, the night half faint, one pointer into the night."""
    pal = pal or dict(plate=NASA["blue"], fg=NASA["white"], hand=NASA["red"])
    cx = cy = 32
    r, w = (20, 8) if v == "full" else (21, 11)
    out = tile(pal["plate"])
    out += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{pal["fg"]}" stroke-width="{w}" opacity=".38"/>'
    out += f'<path d="{_arc(cx, cy, r, 90, 270)}" fill="none" stroke="{pal["fg"]}" stroke-width="{w}"/>'
    ang = math.radians(-55)
    ux, uy = math.sin(ang), -math.cos(ang)
    px, py = -uy, ux
    L = r - w / 2 - 2.5
    bw = 4 if v == "full" else 6
    tri = [(cx + ux * L, cy + uy * L), (cx + px * bw, cy + py * bw), (cx - px * bw, cy - py * bw)]
    out += f'<polygon points="{pts(tri)}" fill="{pal["hand"]}"/><circle cx="{cx}" cy="{cy}" r="{bw}" fill="{pal["hand"]}"/>'
    return out


# ---------------------------------------------------------------- 08 Contact (hull down)
def m_contact(v, uid, pal=None):
    """Hull down: beyond the curve of the Earth only a ship's mast shows above the horizon."""
    pal = pal or dict(plate=NATO["blue"], sea=NATO["light"], mast=NATO["white"])
    R_, top, mx, mw, mt = (92, 42, 41, 4.2, 24) if v == "full" else (80, 40, 40, 7, 15)
    cy = top + R_
    foot = cy - math.sqrt(R_ ** 2 - (mx - 32) ** 2)
    return (clip(uid) + tile(pal["plate"]) + f'<g clip-path="url(#c{uid})">'
            f'<circle cx="32" cy="{cy}" r="{R_}" fill="{pal["sea"]}"/>'
            f'<rect x="{f(mx - mw / 2)}" y="{mt}" width="{f(mw)}" height="{f(foot - mt + 1)}" fill="{pal["mast"]}"/></g>')


# ---------------------------------------------------------------- 09 Shells (beneficial ownership)
def m_shells(v, uid, pal=None):
    pal = pal or dict(plate=GOV["blue"], fg=GOV["white"], core=GOV["white"])
    out = tile(pal["plate"])
    if v == "full":
        sw = 4.4
        # outer edges: S1 9..55, S2 20..47, core 31..39 ; gaps of 4 toward bottom-right
        for a, b in [(9, 55), (20.5, 46.6)]:
            h = sw / 2
            out += (f'<rect x="{f(a + h)}" y="{f(a + h)}" width="{f(b - a - sw)}" height="{f(b - a - sw)}" '
                    f'fill="none" stroke="{pal["fg"]}" stroke-width="{sw}"/>')
        out += f'<rect x="30.6" y="30.6" width="11.6" height="11.6" fill="{pal["core"]}"/>'
    else:
        sw = 7
        a, b = 6, 58
        h = sw / 2
        out += (f'<rect x="{f(a + h)}" y="{f(a + h)}" width="{f(b - a - sw)}" height="{f(b - a - sw)}" '
                f'fill="none" stroke="{pal["fg"]}" stroke-width="{sw}"/>')
        out += f'<rect x="26" y="26" width="20" height="20" fill="{pal["core"]}"/>'
    return out


# ---------------------------------------------------------------- 10 Footnote
def m_foot(v, uid, pal=None):
    """W for World Watch with its reference mark: nothing appears without a source."""
    import typo
    pal = pal or dict(plate=CAN["slate"], fg=CAN["white"], acc=CAN["red"])
    key = "fraunces-600"
    size, x, y, fs, fx, fy = (44, 7, 48, 22, 46, 30) if v == "full" else (50, 3, 51, 26, 46, 30)
    d, _, _ = typo.text_path(key, "W", size)
    d1, _, _ = typo.text_path(key, "1", fs)
    return (tile(pal["plate"]) + f'<path transform="translate({x} {y})" d="{d}" fill="{pal["fg"]}"/>'
            f'<path transform="translate({fx} {fy})" d="{d1}" fill="{pal["acc"]}"/>')


MARKS = {
    "01-cocked-hat": m_cocked,
    "02-terminator": m_term,
    "03-quadkey": m_quad,
    "04-great-circle": m_gc,
    "05-plot": m_plot,
    "06-w-trace": m_trace,
    "07-gmt": m_gmt,
    "08-contact": m_contact,
    "09-shells": m_shells,
    "10-footnote": m_foot,
}

_uid = [0]


def svg(key, variant="full", size=None, pal=None):
    _uid[0] += 1
    uid = f"{key[:2]}{variant[0]}{_uid[0]}"
    s = f' width="{size}" height="{size}"' if size else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"{s}>'
            + MARKS[key](variant, uid, pal) + "</svg>")
