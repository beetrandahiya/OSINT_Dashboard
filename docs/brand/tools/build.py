"""Build lockups and the brand book (sheet.html) for the ten World Watch directions."""
import base64, html, json, math, pathlib, re
import marks as M
import typo
from directions import DIRECTIONS, TOP3, BY_KEY, SRC, MUC_SUNRISE_UTC, MUC_SUNSET_UTC, SUBSOLAR_LON_1200Z

ROOT = pathlib.Path(__file__).resolve().parent.parent
_n = [0]


def uid(p="u"):
    _n[0] += 1
    return f"{p}{_n[0]}"


def esc(s):
    return html.escape(s, quote=True)


def F(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------ text helpers
def outline(font, text, size, x, y, fill, track=0.0, anchor="start", extra=""):
    d, w, cap = typo.text_path(font, text, size, track)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    return f'<path transform="translate({F(x)} {F(y)})" d="{d}" fill="{fill}"{extra}/>', w


def wordmark(D, cap, x, y, fill, anchor="start"):
    wm = D["wm"]
    d, w, capu = typo.text_path(wm["font"], wm["text"], 100, wm["track"])
    s = cap / capu
    ww = w * s
    if anchor == "middle":
        x -= ww / 2
    return f'<path transform="translate({F(x)} {F(y)}) scale({F(s)})" d="{d}" fill="{fill}"/>', ww


def T(x, y, s, size=12, fill="#000", weight=400, family="Inter", anchor="start", ls=0, op=1):
    return (f'<text x="{F(x)}" y="{F(y)}" font-family="{family}, system-ui, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{esc(s)}</text>')


def MONO(x, y, s, size=11, fill="#000", weight=400, anchor="start", op=1, ls=0):
    return T(x, y, s, size, fill, weight, "IBM Plex Mono", anchor, ls, op)


def mark_at(key, x, y, size, variant=None):
    v = variant or ("small" if size <= 24 else "full")
    return (f'<svg x="{F(x)}" y="{F(y)}" width="{F(size)}" height="{F(size)}" viewBox="0 0 64 64">'
            + M.MARKS[key](v, uid("m")) + "</svg>")


def svgwrap(w, h, body, cls="", label=""):
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(label)}" '
            f'xmlns="http://www.w3.org/2000/svg">{body}</svg>')


# ------------------------------------------------------------------ lockups
def lockup_svg(D, ink, standalone=True):
    mark = M.MARKS[D["key"]]("full", uid("L"))
    wm, w = wordmark(D, 22, 64 + 18, 32 + 11, ink)
    W = 64 + 18 + w + 2
    body = f'<svg x="0" y="0" width="64" height="64" viewBox="0 0 64 64">{mark}</svg>{wm}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {F(W)} 64" width="{F(W * 3)}" height="192">'
            f'{body}</svg>'), W


# ------------------------------------------------------------------ geometry helpers
def term_band(x0, x1, y0, y1, sub_lon, c, r=6, n=160):
    """Map band (equirectangular, lon -180..180) with real night / twilight / day for declination of 28 Nov."""
    sub_x = x0 + (sub_lon + 180) / 360 * (x1 - x0)
    day = M.terminator_path(x0, x1, y0, y1, sub_x, 360, 0, n=n)
    tw = M.terminator_path(x0, x1, y0, y1, sub_x, 360, -12, n=n)
    cid = uid("tb")
    return (f'<clipPath id="{cid}"><rect x="{F(x0)}" y="{F(y0)}" width="{F(x1 - x0)}" height="{F(y1 - y0)}" rx="{r}"/></clipPath>'
            f'<g clip-path="url(#{cid})"><rect x="{F(x0)}" y="{F(y0)}" width="{F(x1 - x0)}" height="{F(y1 - y0)}" fill="{c["night"]}"/>'
            f'<path d="{tw}" fill="{c["twi"]}"/><path d="{day}" fill="{c["day"]}"/></g>')


def arc_d(cx, cy, r, a0, a1):
    return M._arc(cx, cy, r, a0, a1)


# ------------------------------------------------------------------ devices, per direction
def dev_panel(c, w, h, inner, title=None):
    t = T(20, 30, title, 13, c["ink"], 600) if title else ""
    return (f'<rect width="{w}" height="{h}" rx="14" fill="{c["panel"]}"/>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="13.5" fill="none" stroke="{c["line"]}"/>' + t + inner)


def skeleton(c, x, y, rows=3, w=200):
    out = ""
    for i in range(rows):
        ww = w * (0.92 - 0.18 * (i % 3))
        out += f'<rect x="{x}" y="{y + i * 18}" width="{F(ww)}" height="7" rx="3.5" fill="{c["sub"]}" opacity=".28"/>'
    return out


def devices(D, theme):
    c = D[theme]
    k = D["key"]
    W, H = 560, 210
    out = []
    if k == "01-cocked-hat":
        P = M.rot(M.COCKED["full"]["P"], 25)
        s, ox, oy = 3.2, 410, 105
        Q = [(ox + (x - 32) * s, oy + (y - 32.5) * s) for x, y in P]
        lines = "".join(M._bearing(Q[i], Q[(i + 1) % 3], 1.4, c["sub"]) for i in range(3))
        cid = uid("cp")
        inner = (f'<clipPath id="{cid}"><rect width="{W}" height="{H}" rx="14"/></clipPath><g clip-path="url(#{cid})" opacity=".9">{lines}'
                 f'<polygon points="{M.pts(Q)}" fill="{c["acc"]}"/></g>' + skeleton(c, 20, 56, 4, 220)
                 + MONO(20, 186, "BEARING RULES  ·  ANGLES OF THE MARK", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner, "Signals"))
        # fix badges
        inner = ""
        labels = [("1 source", "single report"), ("2 agree", "two sources cross"), ("3 agree", "triangle = spread")]
        for i, (a, b) in enumerate(labels):
            x = 20 + i * 178
            inner += f'<rect x="{x}" y="58" width="164" height="92" rx="10" fill="{c["bg"]}" stroke="{c["line"]}"/>'
            cx, cy = x + 40, 104
            if i == 0:
                inner += f'<line x1="{cx - 22}" y1="{cy + 14}" x2="{cx + 22}" y2="{cy - 14}" stroke="{c["ink"]}" stroke-width="2.4"/>'
            elif i == 1:
                inner += (f'<line x1="{cx - 22}" y1="{cy + 14}" x2="{cx + 22}" y2="{cy - 14}" stroke="{c["ink"]}" stroke-width="2.4"/>'
                          f'<line x1="{cx - 20}" y1="{cy - 12}" x2="{cx + 20}" y2="{cy + 12}" stroke="{c["ink"]}" stroke-width="2.4"/>'
                          f'<circle cx="{cx}" cy="{cy}" r="3.6" fill="{c["acc"]}"/>')
            else:
                tri = [(cx - 7, cy + 5), (cx + 8, cy + 3), (cx, cy - 8)]
                ls = "".join(M._bearing(tri[j], tri[(j + 1) % 3], 2.4, c["ink"]) for j in range(3))
                cid2 = uid("fb")
                inner += (f'<clipPath id="{cid2}"><circle cx="{cx}" cy="{cy}" r="25"/></clipPath><g clip-path="url(#{cid2})">{ls}</g>'
                          f'<polygon points="{M.pts(tri)}" fill="{c["acc"]}"/>')
            inner += T(x + 76, 100, a, 14, c["ink"], 600) + T(x + 76, 118, b, 11, c["sub"])
        inner += MONO(20, 186, "FIX BADGE  ·  HOW MANY INDEPENDENT SOURCES AGREE", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner, "Fix badge"))
    elif k == "02-terminator":
        band = term_band(20, 284, 44, 176, SUBSOLAR_LON_1200Z,
                         dict(night=M.ESA["deep"], twi=M.ESA["blue"], day=M.ESA["paper"] if theme == "dark" else "#FFFFFF"), r=6)
        inner = band + (T(306, 66, "Computed, not drawn by hand", 13, c["ink"], 600)
                        + MONO(306, 90, "28 NOV 2026 12:00 UTC", 11, c["sub"]) + MONO(306, 108, "SUBSOLAR 21.3 S  3 W", 11, c["sub"])
                        + T(306, 132, "Night, twilight (0 to -12°) and day,", 12, c["sub"]) + T(306, 150, "the same rule the app uses.", 12, c["sub"])
                        + MONO(306, 196, "TERMINATOR RULE", 10, c["sub"]))
        if theme == "light":
            inner = f'<rect x="20" y="44" width="264" height="132" rx="6" fill="none" stroke="{c["line"]}"/>' + inner
        out.append(dev_panel(c, W, H, inner))
        segs = [(M.ESA["deep"], "night"), (M.ESA["blue"], "twilight"), (M.ESA["paper"] if theme == "dark" else "#FFFFFF", "day")]
        inner = ""
        x = 20
        for i, (col, lab) in enumerate(segs):
            ww = [210, 90, 220][i]
            inner += f'<rect x="{x}" y="70" width="{ww}" height="18" fill="{col}" stroke="{c["line"]}" stroke-width=".8"/>' + MONO(x, 108, lab.upper(), 10, c["sub"])
            x += ww
        inner += f'<rect x="20" y="70" width="520" height="18" fill="none" stroke="{c["line"]}"/>'
        inner += f'<rect x="268" y="62" width="3" height="34" fill="{c["ink"]}"/>' + T(275, 58, "loading: feeds still arriving", 11, c["sub"])
        inner += MONO(20, 186, "TWILIGHT SCALE  ·  PROGRESS AND LEGEND", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner, "Twilight scale"))
    elif k == "03-quadkey":
        x0, y0, s0 = 330, 22, 168
        cells = [(x0, y0, s0)]
        g = ""
        x, y, s = x0, y0, s0
        for dch in "120230":
            g += f'<path d="M{F(x + s / 2)} {F(y)}V{F(y + s)}M{F(x)} {F(y + s / 2)}H{F(x + s)}" stroke="{c["line"]}" stroke-width="1"/>'
            dg = int(dch)
            s /= 2
            x += s * (dg % 2)
            y += s * (dg // 2)
        g = f'<rect x="{x0}" y="{y0}" width="{s0}" height="{s0}" fill="none" stroke="{c["line"]}"/>' + g
        g += f'<rect x="{F(x)}" y="{F(y)}" width="{F(s)}" height="{F(s)}" fill="{c["acc"]}"/>'
        inner = g + skeleton(c, 20, 56, 4, 220) + MONO(20, 186, "TILE GRID  ·  CONVERGES ON THE SELECTED ITEM", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner, "Selected"))
        inner = (f'<rect x="20" y="58" width="300" height="92" rx="4" fill="none" stroke="{c["acc"]}" stroke-width="1.5"/>'
                 + MONO(36, 88, "QK 120230", 22, c["ink"], 500) + MONO(36, 112, "48.137 N  11.575 E", 13, c["sub"])
                 + MONO(36, 134, "ZOOM 6 TILE  ·  MUNICH", 10, c["sub"])
                 + T(344, 92, "A real location reference:", 12, c["ink"], 600)
                 + T(344, 110, "the tile address of the place,", 12, c["sub"]) + T(344, 128, "printed on cards and covers.", 12, c["sub"])
                 + MONO(20, 186, "QUADKEY STAMP", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner, "Quadkey stamp"))
    elif k == "04-great-circle":
        nodes = [(70, 150, "Vessel"), (190, 90, "Operator"), (330, 140, "Holding"), (450, 70, "Owner"), (300, 60, "Insurer")]
        edges = [(0, 1), (1, 2), (2, 3), (1, 4)]
        g = ""
        for a, b in edges:
            (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - abs(x2 - x1) * 0.28 - 10
            g += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c["sub"]}" stroke-width="1" stroke-dasharray="3 3" opacity=".6"/>'
            g += f'<path d="M{x1} {y1} Q{F(mx)} {F(my)} {x2} {y2}" fill="none" stroke="{c["acc"]}" stroke-width="2"/>'
        for i, (x, y, lab) in enumerate(nodes):
            g += (f'<circle cx="{x}" cy="{y}" r="6" fill="{c["panel"] if i == 0 else c["acc"]}" stroke="{c["acc"]}" stroke-width="2.4"/>'
                  + T(x, y + 22, lab, 11, c["sub"], 500, anchor="middle"))
        inner = g + MONO(20, 196, "CONNECTION ARCS  ·  EXAMPLE LABELS", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
        inner = (f'<path d="M40 130 C120 40 440 40 520 130" fill="none" stroke="{c["acc"]}" stroke-width="3" stroke-linecap="round"/>'
                 f'<line x1="56" y1="130" x2="504" y2="130" stroke="{c["sub"]}" stroke-width="1.4" stroke-dasharray="5 5"/>'
                 f'<circle cx="40" cy="130" r="6" fill="{c["panel"]}" stroke="{c["acc"]}" stroke-width="3"/><circle cx="520" cy="130" r="8" fill="{c["acc"]}"/>'
                 + T(280, 152, "solid: the real shortest path   ·   dashed: what the flat map suggests", 11, c["sub"], anchor="middle")
                 + MONO(20, 186, "ARC RULE  ·  DIVIDER AND LOADING LINE", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner))
    elif k == "05-plot":
        pts_ = [(40 + i * 62, 150 - 70 * math.sin(i / 6 * math.pi * 0.9)) for i in range(7)]
        g = ""
        for i, (x, y) in enumerate(pts_):
            if i < 4:
                g += f'<circle cx="{F(x)}" cy="{F(y)}" r="6" fill="{c["ink"]}"/>'
            else:
                g += f'<circle cx="{F(x)}" cy="{F(y)}" r="5.2" fill="none" stroke="{c["sub"]}" stroke-width="1.4" opacity=".6"/>'
        x, y = pts_[3]
        g += f'<polygon points="{F(x + 14)},{F(y)} {F(x)},{F(y - 10)} {F(x - 10)},{F(y)} {F(x)},{F(y + 10)}" fill="{c["acc"] if theme == "dark" else "#2FA3AA"}"/>'
        inner = g + T(20, 30, "4 of 7 feeds answered", 13, c["ink"], 600) + MONO(20, 196, "HISTORY-DOT PROGRESS  ·  ONE DOT PER ANSWER", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
        tx, ty = 90, 120
        inner = (f'<circle cx="40" cy="160" r="3.4" fill="{c["sub"]}"/><circle cx="56" cy="148" r="3.4" fill="{c["sub"]}"/><circle cx="72" cy="135" r="3.4" fill="{c["sub"]}"/>'
                 f'<polygon points="{tx + 14},{ty} {tx},{ty - 10} {tx - 10},{ty} {tx},{ty + 10}" fill="#2FA3AA"/>'
                 f'<line x1="{tx + 16}" y1="{ty - 6}" x2="200" y2="72" stroke="{c["ink"]}" stroke-width="1.2"/>'
                 + MONO(206, 66, "RCH4992", 15, c["ink"], 500) + MONO(206, 86, "C17  FL306", 13, c["sub"]) + MONO(206, 104, "535 KT  063°", 13, c["sub"])
                 + T(380, 70, "Air-traffic label style", 12, c["ink"], 600) + T(380, 88, "for captions on the map.", 12, c["sub"])
                 + T(380, 106, "Values: a real capture,", 12, c["sub"]) + T(380, 124, "17 Nov 2026.", 12, c["sub"])
                 + MONO(20, 196, "LEADER LINE AND DATA BLOCK", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner))
    elif k == "06-w-trace":
        vals = [2, 2, 3, 2, 2, 3, 2, 9, 4, 2, 2, 3, 2, 2, 2, 3, 12, 6, 3, 2, 2, 2, 3, 2, 2, 4, 2, 2, 3, 2, 2, 2]
        x0, x1, base = 20, W - 20, 140
        step = (x1 - x0) / (len(vals) - 1)
        pts_ = [(x0 + i * step, base - v * 7) for i, v in enumerate(vals)]
        d = "M" + " L".join(f"{F(x)} {F(y)}" for x, y in pts_)
        hi = c["acc"] if theme == "dark" else "#010101"
        g = f'<path d="{d}" fill="none" stroke="{c["sub"]}" stroke-width="2" stroke-linejoin="miter"/>'
        for i in (7, 16):
            seg = pts_[i - 1:i + 2]
            g += f'<path d="M' + " L".join(f"{F(x)} {F(y)}" for x, y in seg) + f'" fill="none" stroke="{hi}" stroke-width="2.6"/>'
            if theme == "light":
                g += f'<rect x="{F(seg[0][0])}" y="{base + 10}" width="{F(seg[2][0] - seg[0][0])}" height="4" fill="#DFF140"/>'
        inner = g + T(20, 30, "News per 15 min, Munich", 13, c["ink"], 600) + MONO(20, 196, "ACTIVITY TRACE  ·  SHAPE ILLUSTRATIVE, IN THE APP: REAL COUNTS", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
        g = ""
        for i in range(1, 10):
            g += f'<line x1="{20 + i * 52}" y1="44" x2="{20 + i * 52}" y2="168" stroke="{c["line"]}" stroke-width="1"/>'
        for j in range(1, 4):
            g += f'<line x1="20" y1="{44 + j * 31}" x2="540" y2="{44 + j * 31}" stroke="{c["line"]}" stroke-width="1"/>'
        g += f'<rect x="20" y="44" width="520" height="124" fill="none" stroke="{c["line"]}"/>'
        g += f'<path d="M20 120 H220 L232 70 L246 150 L260 92 L274 150 L288 70 L300 120 H540" fill="none" stroke="{hi}" stroke-width="2.4"/>'
        inner = g + MONO(20, 196, "SCOPE GRID  ·  PANEL AND SPLASH BACKGROUND", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
    elif k == "07-gmt":
        cx, cy, r = 110, 108, 64
        g = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c["line"]}" stroke-width="14"/>'
        a0, a1 = MUC_SUNRISE_UTC / 24 * 360, MUC_SUNSET_UTC / 24 * 360
        g += f'<path d="{arc_d(cx, cy, r, a0, a1)}" fill="none" stroke="{c["ink"] if theme == "dark" else "#0032A0"}" stroke-width="14"/>'
        for hh, lab in [(0, "00"), (6, "06"), (12, "12"), (18, "18")]:
            a = math.radians(hh / 24 * 360)
            g += T(cx + (r + 24) * math.sin(a), cy - (r + 24) * math.cos(a) + 4, lab, 11, c["sub"], 500, "IBM Plex Mono", "middle")
        a = math.radians(12 / 24 * 360)
        g += (f'<line x1="{cx}" y1="{cy}" x2="{F(cx + (r - 14) * math.sin(a))}" y2="{F(cy - (r - 14) * math.cos(a))}" stroke="#E4002B" stroke-width="3"/>'
              f'<circle cx="{cx}" cy="{cy}" r="5" fill="#E4002B"/>')
        inner = (g + T(240, 70, "Munich daylight, 28 Nov 2026", 13, c["ink"], 600)
                 + MONO(240, 94, "SUNRISE 06:39Z  SUNSET 15:25Z", 11, c["sub"]) + T(240, 118, "Ring = 24 h UTC, solid = daylight", 12, c["sub"])
                 + T(240, 136, "(computed). Red hand = 12:00 UTC.", 12, c["sub"])
                 + MONO(240, 196, "DAYLIGHT BEZEL  ·  LOADING RING", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner))
        inner = ""
        for i, (a, b) in enumerate([("12:00Z", "13:00 MUNICH"), ("06:39Z", "SUNRISE MUNICH"), ("15:25Z", "SUNSET MUNICH")]):
            x = 20 + i * 178
            inner += (f'<rect x="{x}" y="66" width="164" height="70" rx="8" fill="{c["bg"]}" stroke="{c["line"]}"/>'
                      + MONO(x + 14, 98, a, 20, c["ink"], 500) + MONO(x + 14, 120, b, 10, c["sub"]))
        inner += T(20, 30, "UTC first, local second", 13, c["ink"], 600) + MONO(20, 196, "DUAL TIME STAMP", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
    elif k == "08-contact":
        R_ = 1400
        cy = 150 + R_
        g = f'<path d="{arc_d(W / 2, cy, R_, -12, 12)}" fill="none" stroke="{c["ink"]}" stroke-width="1.6"/>'
        for x, hgt in [(90, 18), (180, 30), (300, 12), (400, 40), (470, 22)]:
            y = cy - math.sqrt(R_ ** 2 - (x - W / 2) ** 2)
            g += f'<rect x="{x - 1.5}" y="{F(y - hgt)}" width="3" height="{hgt}" fill="{c["acc"] if theme == "dark" else c["ink"]}"/>'
        inner = g + T(20, 30, "Contacts in view", 13, c["ink"], 600) + MONO(20, 196, "HORIZON RULE  ·  TICKS = ITEMS, HEIGHT = COUNT", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
        inner = ""
        for i, mt in enumerate([0, 14, 30]):
            x = 20 + i * 178
            cid = uid("hd")
            inner += (f'<clipPath id="{cid}"><rect x="{x}" y="50" width="164" height="110" rx="8"/></clipPath>'
                      f'<g clip-path="url(#{cid})"><rect x="{x}" y="50" width="164" height="110" fill="#004990"/>'
                      f'<circle cx="{x + 82}" cy="{130 + 600}" r="600" fill="#118ACB"/>'
                      f'<rect x="{x + 96}" y="{130 - mt}" width="4" height="{mt + 4}" fill="#FFFFFF"/></g>')
        inner += T(20, 30, "Hull-down loader", 13, c["ink"], 600) + MONO(20, 196, "THE MAST RISES AS DATA ARRIVES", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
    elif k == "09-shells":
        g = (f'<rect x="300" y="24" width="240" height="160" fill="none" stroke="{c["ink"]}" stroke-width="2"/>'
             f'<rect x="346" y="64" width="174" height="104" fill="none" stroke="{c["ink"]}" stroke-width="2"/>'
             f'<rect x="440" y="110" width="64" height="42" fill="{c["acc"]}"/>'
             + T(312, 44, "Holding Ltd", 11, c["sub"]) + T(358, 84, "Trust", 11, c["sub"])
             + T(472, 135, "Owner", 11, "#FFFFFF", 600, anchor="middle"))
        inner = g + skeleton(c, 20, 56, 4, 220) + T(20, 30, "Shell frames", 13, c["ink"], 600) + MONO(20, 196, "FRAME WITHIN FRAME  ·  EXAMPLE LABELS", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
        boxes = [("Operating GmbH", "company"), ("Holding Ltd", "company"), ("Family trust", "legal arrangement"), ("Owner", "person")]
        g = ""
        for i, (a, b) in enumerate(boxes):
            x = 20 + i * 134
            last = i == 3
            g += (f'<rect x="{x}" y="70" width="112" height="64" fill="{c["acc"] if last else c["bg"]}" stroke="{c["acc"] if last else c["line"]}" stroke-width="1.5"/>'
                  + T(x + 9, 96, a, 11, "#FFFFFF" if last else c["ink"], 600) + T(x + 9, 116, b, 10, "#FFFFFF" if last else c["sub"]))
            if i < 3:
                g += (f'<path d="M{x + 114} 102 H{x + 132} M{x + 126} 97 L{x + 132} 102 L{x + 126} 107" fill="none" stroke="{c["ink"]}" stroke-width="1.4"/>'
                      + MONO(x + 123, 62, ["100%", "75%", "60%"][i], 9, c["sub"], anchor="middle"))
        inner = g + T(20, 30, "Ownership chain", 13, c["ink"], 600) + MONO(20, 196, "OWNED BY →  ·  EXAMPLE VALUES", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
    elif k == "10-footnote":
        red = "#D3080C"
        inner = (T(20, 30, "Reference marks", 13, c["ink"], 600)
                 + f'<text x="20" y="74" font-family="Fraunces, Georgia, serif" font-size="20" fill="{c["ink"]}">Rosneft Deutschland’s direct parent is PJSC Rosneft.'
                 + f'<tspan dy="-8" font-size="12" fill="{red}" font-family="Inter">1</tspan></text>'
                 + f'<text x="20" y="104" font-family="Fraunces, Georgia, serif" font-size="20" fill="{c["ink"]}">Rosneft’s own parent is not reported.'
                 + f'<tspan dy="-8" font-size="12" fill="{red}" font-family="Inter">2</tspan></text>'
                 + f'<line x1="20" y1="126" x2="540" y2="126" stroke="{c["line"]}"/>'
                 + T(20, 146, "1  GLEIF LEI register, relationship record, read 28 Nov 2026", 11, c["sub"])
                 + T(20, 164, "2  GLEIF: reporting exception 'NO_KNOWN_PERSON', read 28 Nov 2026", 11, c["sub"])
                 + f'<text x="20" y="146" font-size="11" fill="{red}" font-family="Inter">1</text><text x="20" y="164" font-size="11" fill="{red}" font-family="Inter">2</text>'
                 + MONO(20, 196, "FACTS FROM THE PROJECT'S OWN GLEIF PROBE", 10, c["sub"]))
        out.append(dev_panel(c, W, H, inner))
        inner = T(20, 30, "Source rule", 13, c["ink"], 600)
        for i, (a, b) in enumerate([("adsb.fi", "aircraft positions · 10 s ago"), ("GDELT GKG", "news places · 14 min ago"),
                                    ("USGS", "earthquakes · 1 min ago")]):
            y = 70 + i * 34
            inner += (f'<rect x="20" y="{y - 11}" width="3" height="14" fill="{red}"/>' + T(32, y, a, 13, c["ink"], 600)
                      + T(150, y, b, 12, c["sub"]) + f'<line x1="20" y1="{y + 12}" x2="540" y2="{y + 12}" stroke="{c["line"]}"/>')
        inner += MONO(20, 196, "EVERY LAYER: SOURCE AND AGE  ·  EXAMPLE AGES", 10, c["sub"])
        out.append(dev_panel(c, W, H, inner))
    return [svgwrap(W, H, o, "dev", f'{D["name"]} device {i + 1}') for i, o in enumerate(out)]


# ------------------------------------------------------------------ applications
def topbar(D, theme, view="Map"):
    c = D[theme]
    k = D["key"]
    W, H = 1000, 60
    b = f'<rect width="{W}" height="{H}" rx="14" fill="{c["panel"]}"/><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="13.5" fill="none" stroke="{c["line"]}"/>'
    b += mark_at(k, 16, 14, 32)
    wm, ww = wordmark(D, 12.5, 60, 36.5, c["ink"])
    b += wm
    x = 60 + ww + 18
    b += f'<line x1="{F(x)}" y1="20" x2="{F(x)}" y2="40" stroke="{c["line"]}"/>'
    b += T(x + 16, 35, view, 13, c["sub"], 500)
    b += f'<rect x="380" y="14" width="300" height="32" rx="9" fill="{c["bg"]}" stroke="{c["line"]}"/>'
    b += f'<circle cx="398" cy="30" r="5.2" fill="none" stroke="{c["sub"]}" stroke-width="1.6"/><line x1="402" y1="34" x2="406" y2="38" stroke="{c["sub"]}" stroke-width="1.6"/>'
    b += T(414, 34.5, "Search places, aircraft, ships, people", 12, c["sub"])
    # right side: device-specific
    extra = ""
    if k == "01-cocked-hat":
        tri = [(712, 37), (726, 35), (719, 23)]
        cid = uid("tb")
        ls = "".join(M._bearing(tri[j], tri[(j + 1) % 3], 1.6, c["ink"]) for j in range(3))
        extra = (f'<clipPath id="{cid}"><rect x="700" y="14" width="40" height="32" rx="6"/></clipPath><g clip-path="url(#{cid})">{ls}</g>'
                 f'<polygon points="{M.pts(tri)}" fill="{c["acc"]}"/>' + T(748, 35, "3 sources agree", 12, c["ink"], 500))
    elif k == "02-terminator":
        extra = term_band(16, W - 16, H - 5, H - 1, SUBSOLAR_LON_1200Z, dict(night=M.ESA["deep"], twi=M.ESA["blue"], day=M.ESA["paper"]), r=2, n=120)
        extra += MONO(706, 35, "NIGHT LINE · LIVE", 11, c["sub"])
    elif k == "03-quadkey":
        extra = f'<rect x="704" y="17" width="150" height="26" rx="3" fill="none" stroke="{c["acc"]}"/>' + MONO(714, 35, "QK 1202 · MUNICH", 11, c["ink"], 500)
    elif k == "04-great-circle":
        extra = (f'<path d="M706 38 C712 18 742 16 752 30" fill="none" stroke="{c["acc"]}" stroke-width="2.4" stroke-linecap="round"/>'
                 f'<circle cx="706" cy="38" r="3" fill="{c["panel"]}" stroke="{c["acc"]}" stroke-width="2"/><circle cx="752" cy="30" r="3.6" fill="{c["acc"]}"/>'
                 + T(764, 35, "12 connections", 12, c["ink"], 500))
    elif k == "05-plot":
        extra = "".join(f'<circle cx="{706 + i * 9}" cy="{36 - i * 2}" r="2.6" fill="{c["ink"]}"/>' for i in range(4))
        extra += '<polygon points="752,26 744,21 739,27 746,32" fill="#2FA3AA"/>' + T(764, 35, "live · 10 s", 12, c["ink"], 500)
    elif k == "06-w-trace":
        hi = c["acc"] if theme == "dark" else "#010101"
        extra = (f'<path d="M704 34 H722 L726 22 L731 40 L735 28 L739 40 L744 22 L748 34 H766" fill="none" stroke="{c["sub"]}" stroke-width="1.6"/>'
                 f'<path d="M722 34 L726 22 L731 40 L735 28 L739 40 L744 22 L748 34" fill="none" stroke="{hi}" stroke-width="1.8"/>'
                 + MONO(776, 35, "NEWS/15 MIN", 11, c["sub"]))
    elif k == "07-gmt":
        extra = MONO(706, 35, "12:00Z", 13, c["ink"], 500) + MONO(762, 35, "13:00 MUNICH", 11, c["sub"]) + '<circle cx="854" cy="30" r="3.4" fill="#E4002B"/>'
    elif k == "08-contact":
        extra = (f'<path d="M0 {H - 3} Q{W / 2} {H - 10} {W} {H - 3}" fill="none" stroke="{c["acc"]}" stroke-width="1.4" opacity=".9"/>'
                 + T(706, 35, "Contacts", 12, c["ink"], 500) + MONO(770, 35, "214", 12, c["sub"]))
    elif k == "09-shells":
        extra = (f'<rect x="706" y="20" width="20" height="20" fill="none" stroke="{c["ink"]}" stroke-width="1.6"/><rect x="716" y="30" width="8" height="8" fill="{c["acc"]}"/>'
                 + T(734, 35, "Holding › Trust › Owner", 12, c["ink"], 500))
    elif k == "10-footnote":
        extra = T(706, 35, "Sources", 12, c["ink"], 500) + f'<text x="756" y="30" font-family="Inter" font-size="10" fill="{"#D3080C" if theme == "light" else c["ink"]}">12</text>'
        if theme == "dark":
            extra += '<rect x="756" y="33" width="12" height="2" fill="#D3080C"/>'
    b += extra
    b += f'<rect x="{W - 96}" y="16" width="80" height="28" rx="14" fill="{c["bg"]}" stroke="{c["line"]}"/>'
    b += f'<circle cx="{W - 80}" cy="30" r="3.6" fill="#2fa36b"/>' + T(W - 70, 34.5, "Feeds", 12, c["ink"], 500)
    return svgwrap(W, H, b, "bar", f'{D["name"]} top bar, {theme}')


def cover(D):
    k = D["key"]
    c = D["light"]
    W, H = 300, 424
    dark_cover = k in ("06-w-trace", "02-terminator")
    if dark_cover:
        c = D["dark"]
    cid = uid("cv")
    b = f'<clipPath id="{cid}"><rect width="{W}" height="{H}"/></clipPath><rect width="{W}" height="{H}" fill="{c["bg"]}"/><g clip-path="url(#{cid})">'
    art = ""
    if k == "01-cocked-hat":
        P = M.rot(M.COCKED["full"]["P"], 25)
        s, ox, oy = 4.2, 196, 150
        Q = [(ox + (x - 32) * s, oy + (y - 32.5) * s) for x, y in P]
        art = "".join(M._bearing(Q[i], Q[(i + 1) % 3], 2, c["ink"]) for i in range(3)) + f'<polygon points="{M.pts(Q)}" fill="{c["acc"]}"/>'
    elif k == "02-terminator":
        art = term_band(24, W - 24, 120, 120 + (W - 48) / 2, SUBSOLAR_LON_1200Z, dict(night=M.ESA["deep"], twi=M.ESA["blue"], day=M.ESA["paper"]), r=6)
        art += MONO(24, 270, "NIGHT AT 12:00 UTC, 28 NOV 2026", 8, c["sub"])
    elif k == "03-quadkey":
        x, y, s = 24, 64, 240
        art = f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="none" stroke="{c["line"]}"/>'
        steps = ["#CCE3EA", "#99C6D4", "#66AABF", "#338DA9", "#007194", "#000000"]
        for dch, col in zip("120230", steps):
            art += f'<path d="M{F(x + s / 2)} {F(y)}V{F(y + s)}M{F(x)} {F(y + s / 2)}H{F(x + s)}" stroke="{c["line"]}"/>'
            dg = int(dch)
            s /= 2
            x += s * (dg % 2)
            y += s * (dg // 2)
            art += f'<rect x="{F(x)}" y="{F(y)}" width="{F(s)}" height="{F(s)}" fill="{col}" opacity=".9"/>'
        art += MONO(24, 318, "QK 120230 · 48.137 N 11.575 E", 8, c["sub"])
    elif k == "04-great-circle":
        art = (f'<path d="M30 250 C60 60 240 50 270 180" fill="none" stroke="{c["acc"]}" stroke-width="5" stroke-linecap="round"/>'
               f'<line x1="44" y1="246" x2="258" y2="184" stroke="{c["sub"]}" stroke-width="1.5" stroke-dasharray="5 5"/>'
               f'<circle cx="30" cy="250" r="8" fill="{c["bg"]}" stroke="{c["acc"]}" stroke-width="4"/><circle cx="270" cy="180" r="10" fill="{c["acc"]}"/>')
    elif k == "05-plot":
        art = ""
        for i in range(9):
            t = i / 8
            x = 30 + t * 200
            y = 300 - 190 * math.sin(t * math.pi / 2) ** 1.3
            art += f'<circle cx="{F(x)}" cy="{F(y)}" r="4.2" fill="{c["ink"]}"/>'
        art += '<polygon points="268,104 252,92 240,106 254,118" fill="#2FA3AA"/>'
    elif k == "06-w-trace":
        for i in range(1, 6):
            art += f'<line x1="{i * 50}" y1="0" x2="{i * 50}" y2="{H}" stroke="{c["line"]}"/>'
        for j in range(1, 9):
            art += f'<line x1="0" y1="{j * 50}" x2="{W}" y2="{j * 50}" stroke="{c["line"]}"/>'
        art += f'<path d="M0 210 H70 L86 120 L110 260 L134 160 L158 260 L182 120 L198 210 H300" fill="none" stroke="#DFF140" stroke-width="5"/>'
    elif k == "07-gmt":
        cx, cy, r = 236, 192, 96
        art = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0032A0" stroke-width="26" opacity=".18"/>'
        art += f'<path d="{arc_d(cx, cy, r, MUC_SUNRISE_UTC * 15, MUC_SUNSET_UTC * 15)}" fill="none" stroke="#0032A0" stroke-width="26"/>'
        art += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy + r - 26}" stroke="#E4002B" stroke-width="4"/><circle cx="{cx}" cy="{cy}" r="7" fill="#E4002B"/>'
        art += MONO(24, 318, "MUNICH DAYLIGHT 28 NOV 2026 · 06:39-15:25Z", 7.5, c["sub"])
    elif k == "08-contact":
        art = (f'<rect width="{W}" height="{H}" fill="#004990"/><circle cx="150" cy="{300 + 900}" r="900" fill="#118ACB"/>'
               f'<rect x="196" y="236" width="5" height="66" fill="#FFFFFF"/>')
    elif k == "09-shells":
        art = (f'<rect x="14" y="14" width="272" height="364" fill="none" stroke="{c["ink"]}" stroke-width="3"/>'
               f'<rect x="40" y="62" width="222" height="292" fill="none" stroke="{c["ink"]}" stroke-width="3"/>'
               f'<rect x="150" y="238" width="92" height="96" fill="#1D70B8"/>')
    elif k == "10-footnote":
        art = f'<line x1="24" y1="92" x2="276" y2="92" stroke="{c["line"]}"/>'
        d, w, _ = typo.text_path("fraunces-600", "W", 210)
        art += f'<path transform="translate(14 300)" d="{d}" fill="#26374A"/>'
        d1, _, _ = typo.text_path("fraunces-600", "1", 90)
        art += f'<path transform="translate(226 160)" d="{d1}" fill="#D3080C"/>'
    b += art + "</g>"
    ink = c["ink"]
    if k == "08-contact":
        b += mark_at(k, 24, 24, 26) + wordmark(D, 9, 58, 41, "#FFFFFF")[0]
        b += MONO(24, 330, "INVESTIGATE", 9, c["sub"], 500, ls=1.5)
        b += outline(D["wm"]["font"], "CASE FILE", 34, 24, 368, ink, 0.04)[0]
    else:
        b += mark_at(k, 24, 24, 26) + wordmark(D, 9, 58, 41, ink)[0]
        if k == "09-shells":
            b += T(160, 276, "Case file", 15, "#FFFFFF", 600) + T(160, 294, "Subject", 9, "#FFFFFF", 400)
            b += MONO(54, 88, "INVESTIGATE", 9, c["sub"], 500, ls=1.5)
        else:
            y0 = 366 if k not in ("03-quadkey",) else 374
            b += MONO(24, y0 - 34, "INVESTIGATE", 9, c["sub"], 500, ls=1.5)
            if k == "10-footnote":
                b += outline("fraunces-600", "Case file", 30, 24, 76, ink)[0]
            else:
                b += outline(D["wm"]["font"], "CASE FILE" if D["wm"]["text"].isupper() else "Case file", 28, 24, y0, ink,
                             D["wm"]["track"] * .6 if D["wm"]["text"].isupper() else 0)[0]
    # fields
    fy = 396
    for i, (a, val) in enumerate([("SUBJECT", "—"), ("OPENED", "28 NOV 2026"), ("SOURCES", "—")]):
        x = 24 + i * 92
        b += MONO(x, fy, a, 7, c["sub"], 500, ls=1) + MONO(x, fy + 13, val, 9, ink, 500)
    b += MONO(24, H - 6, "PRIVATE · PUBLIC SOURCES ONLY", 6.5, c["sub"], 400, ls=.8)
    return svgwrap(W, H, b, "cover", f'{D["name"]} case file cover')


def splash(D):
    k = D["key"]
    c = D["dark"]
    W, H = 480, 300
    b = f'<rect width="{W}" height="{H}" rx="14" fill="{c["bg"]}"/>'
    art = ""
    cx = W / 2
    if k == "01-cocked-hat":
        art = ""
    elif k == "02-terminator":
        art = term_band(40, W - 40, 70, 70 + (W - 80) / 2 * .62, SUBSOLAR_LON_1200Z, dict(night=M.ESA["deep"], twi=M.ESA["blue"], day=M.ESA["paper"]), r=8)
    elif k == "03-quadkey":
        x, y, s = 160, 40, 160
        art = f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="none" stroke="#007194"/>'
        for dch in "120230":
            art += f'<path d="M{F(x + s / 2)} {F(y)}V{F(y + s)}M{F(x)} {F(y + s / 2)}H{F(x + s)}" stroke="#007194"/>'
            dg = int(dch)
            s /= 2
            x += s * (dg % 2)
            y += s * (dg // 2)
        art += f'<rect x="{F(x)}" y="{F(y)}" width="{F(s)}" height="{F(s)}" fill="#FFFFFF"/>'
    elif k == "04-great-circle":
        art = (f'<line x1="176" y1="270" x2="304" y2="270" stroke="{c["sub"]}" stroke-width="1.2" stroke-dasharray="4 4"/>'
               f'<path d="M168 270 C180 242 300 242 312 270" fill="none" stroke="{c["acc"]}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="150" stroke-dashoffset="60"/>'
               f'<circle cx="168" cy="270" r="4" fill="{c["bg"]}" stroke="{c["acc"]}" stroke-width="2"/>')
    elif k == "05-plot":
        for i in range(7):
            x = 180 + i * 20
            art += (f'<circle cx="{x}" cy="266" r="3.6" fill="{c["ink"]}"/>' if i < 4 else
                    f'<circle cx="{x}" cy="266" r="3.2" fill="none" stroke="{c["sub"]}" stroke-width="1.2"/>')
    elif k == "06-w-trace":
        for i in range(1, 12):
            art += f'<line x1="{i * 40}" y1="0" x2="{i * 40}" y2="{H}" stroke="{c["line"]}"/>'
        for j in range(1, 8):
            art += f'<line x1="0" y1="{j * 40}" x2="{W}" y2="{j * 40}" stroke="{c["line"]}"/>'
        art += f'<path d="M0 268 H196 L204 250 L214 282 L224 258 L234 282 L244 250 L252 268 H{W}" fill="none" stroke="{c["acc"]}" stroke-width="2" opacity=".55"/>'
    elif k == "07-gmt":
        r = 66
        art = f'<circle cx="{cx}" cy="114" r="{r}" fill="none" stroke="#FFFFFF" stroke-width="9" opacity=".14"/>'
        art += f'<path d="{arc_d(cx, 114, r, MUC_SUNRISE_UTC * 15, MUC_SUNSET_UTC * 15)}" fill="none" stroke="#FFFFFF" stroke-width="9"/>'
    elif k == "08-contact":
        cid = uid("sp")
        art = (f'<clipPath id="{cid}"><rect width="{W}" height="{H}" rx="14"/></clipPath><g clip-path="url(#{cid})">'
               f'<rect width="{W}" height="{H}" fill="#004990"/><circle cx="{cx}" cy="{232 + 1400}" r="1400" fill="#118ACB"/>'
               f'<rect x="318" y="200" width="4" height="34" fill="#FFFFFF"/></g>')
    elif k == "09-shells":
        art = (f'<rect x="16" y="16" width="{W - 32}" height="{H - 32}" fill="none" stroke="#FFFFFF" stroke-width="1.5" opacity=".35"/>'
               f'<rect x="34" y="34" width="{W - 68}" height="{H - 68}" fill="none" stroke="#FFFFFF" stroke-width="1.5" opacity=".6"/>'
               f'<rect x="{W - 34 - 8 - 46}" y="{H - 34 - 8 - 30}" width="46" height="30" fill="#1D70B8"/>')
    elif k == "10-footnote":
        art = ""
    b += art
    if k in ("03-quadkey", "09-shells"):
        b += mark_at(k, cx - 34, 230 - 68 - 150 + 90, 68) if False else ""
    my = {"02-terminator": 196, "03-quadkey": 214, "07-gmt": 86}.get(k, 92)
    ms = 56 if k in ("02-terminator", "03-quadkey") else 68
    if k == "07-gmt":
        b += mark_at(k, cx - 26, 88, 52)
    elif k == "09-shells":
        b += mark_at(k, cx - 34, 92, 68)
    elif k == "02-terminator":
        b += mark_at(k, 40, 214, 40)
    elif k == "03-quadkey":
        b += mark_at(k, 40, 226, 40)
    elif k == "01-cocked-hat":
        P = M.rot(M.COCKED["full"]["P"], 25)
        s, ox, oy = 3.6, cx, 112
        Q = [(ox + (x - 32) * s, oy + (y - 32.5) * s) for x, y in P]
        cid = uid("sq")
        b += (f'<clipPath id="{cid}"><circle cx="{cx}" cy="112" r="74"/></clipPath><g clip-path="url(#{cid})">'
              + "".join(M._bearing(Q[i], Q[(i + 1) % 3], 3.2, c["ink"]) for i in range(3)) + "</g>"
              + f'<polygon points="{M.pts(Q)}" fill="{c["acc"]}"/>')
    elif k == "08-contact":
        pass
    else:
        b += mark_at(k, cx - ms / 2, my, ms)
    ink = "#FFFFFF" if k == "08-contact" else c["ink"]
    if k in ("02-terminator", "03-quadkey"):
        b += wordmark(D, 13, 92, 240 if k == "02-terminator" else 252, ink)[0]
        b += MONO(92, 260 if k == "02-terminator" else 272, "CONNECTING TO FEEDS", 9, c["sub"], ls=1.2)
    else:
        wy = 222 if k == "07-gmt" else (206 if k != "08-contact" else 92)
        wy2 = 112 if k == "08-contact" else wy
        b += wordmark(D, 18 if k == "08-contact" else 14, cx, wy2, ink, "middle")[0]
        b += MONO(cx, wy2 + 26, "CONNECTING TO FEEDS", 9, "#9EC6E6" if k == "08-contact" else c["sub"], anchor="middle", ls=1.2)
    return svgwrap(W, H, b, "splash", f'{D["name"]} splash screen')


# ------------------------------------------------------------------ sheet
def b64(p):
    return base64.b64encode(pathlib.Path(p).read_bytes()).decode()


def strips(D):
    k = D["key"]
    rows = []
    for bg, lab in (("dark", "Windows 11 taskbar, dark (#202020)"), ("light", "Windows 11 taskbar, light (#f3f3f3)"),
                    ("dock", "macOS Dock-like shelf")):
        imgs = "".join(
            f'<figure><img src="data:image/png;base64,{b64(ROOT / "renders" / f"{k}-{s}-{bg}.png")}" width="{s + 40}" height="{s + 24}" alt="{s} px"><figcaption>{s}</figcaption></figure>'
            for s in (16, 24, 32, 48))
        zoom = "".join(
            f'<img class="zoom" src="data:image/png;base64,{b64(ROOT / "renders" / f"{k}-{s}-{bg}.png")}" style="width:{(s + 40) * 3}px;height:{(s + 24) * 3}px" alt="{s} px, 3x">'
            for s in (16, 24))
        rows.append(f'<div class="strip"><div class="strip-l">{lab}</div><div class="strip-imgs">{imgs}</div><div class="strip-zoom">{zoom}</div></div>')
    return "".join(rows)


def palette_block(D):
    pal = D["palette"]
    bar = "".join(f'<span style="flex:{p["share"]};background:{p["hex"]}" title="{esc(p["name"])} {p["share"]}%"></span>' for p in pal)
    sw = ""
    for p in pal:
        s = SRC[p["src"]]
        sw += (f'<div class="sw"><span class="chip" style="background:{p["hex"]}"></span><div><b>{esc(p["name"])}</b>'
               f'<code>{p["hex"]}</code><small>{esc(p["role"])} · {p["share"]}%</small></div></div>')
    known = {p["hex"].upper() for p in pal} | {"#FFFFFF", "#000000"}
    derived = sorted({v.upper() for th in ("dark", "light") for kk, v in D[th].items() if v.upper() not in known})
    s = SRC[D["src"]]
    der = (f'<p class="fine">UI mixes in the mock-ups (not published colours, made by mixing the ones above with black or white): '
           + ", ".join(f'<code>{h}</code>' for h in derived) + "</p>") if derived else ""
    return (f'<div class="pbar">{bar}</div><div class="sws">{sw}</div>'
            f'<p class="fine">Source: <a href="{s[1]}">{esc(s[0])}</a>. {esc(s[2])}</p>{der}')


def type_block(D):
    wm = D["wm"]
    fam = json.loads((ROOT / "fonts" / "fonts.json").read_text())[wm["font"]]["family"]
    w = {"600": 600, "700": 700, "800": 800, "400": 400}[wm["font"].split("-")[-1].replace("x", "")]
    stretch = "font-stretch:125%;" if wm["font"].startswith("archivo-x") else ""
    return (f'<div class="type"><div class="type-name">{esc(wm["family"])} <span>{esc(wm["weight"])}, SIL Open Font License, Google Fonts</span></div>'
            f'<div class="spec" style="font-family:\'{fam}\';font-weight:{w};{stretch}">Aa Bb 0123 · ABCDEFGHIJKLM</div>'
            f'<div class="type-name">Text: Inter <span>400 / 500 / 600</span> · Numbers and time stamps: IBM Plex Mono <span>400 / 500</span></div>'
            f'<div class="spec2">Every layer shows its source and when it last updated. <span class="mono">12:00Z · 48.137 N 11.575 E</span></div></div>')


def section(D, idx):
    k = D["key"]
    top = k in TOP3
    rank = TOP3.index(k) + 1 if top else 0
    big = M.svg(k, "full")
    small = M.svg(k, "small")
    lock_l, _ = lockup_svg(D, D["light"]["ink"])
    lock_d, _ = lockup_svg(D, D["dark"]["ink"])
    devs = devices(D, "dark")
    devs_l = devices(D, "light")
    s = SRC[D["src"]]
    badge = f'<span class="pick">Top pick {rank}</span>' if top else ""
    return f"""
<section class="dir" id="d{k}">
  <header class="dh">
    <div class="dnum">{k[:2]}</div>
    <div class="dtitle"><h2>{esc(D['name'])} {badge}</h2>
      <p class="dline">{esc(D['line'])}</p>
      <p class="dstory">{esc(D['story'])}</p>
      <p class="dmeta">Palette from <b>{esc(D['agency'])}</b> · <a href="{s[1]}">source</a> · Wordmark: {esc(D['wm']['family'])}</p>
    </div>
  </header>
  <div class="g-mark">
    <div class="card markcard"><div class="lab">App icon, 64 grid (also the 1024 master)</div><div class="bigmark">{big}</div></div>
    <div class="card"><div class="lab">16 and 24 px variant</div><div class="smallmark">{small}</div><p class="fine">{esc(D['small'])}</p></div>
    <div class="card lock"><div class="lab">Lockup</div><div class="lockl" style="background:{D['light']['bg']}">{lock_l}</div><div class="lockd" style="background:{D['dark']['bg']}">{lock_d}</div></div>
  </div>
  <div class="card"><div class="lab">Taskbar and Dock test: real 1x pixels (left), 16 and 24 px zoomed 3x (right)</div>{strips(D)}</div>
  <div class="g-two">
    <div class="card"><div class="lab">Colour system: share of a typical screen</div>{palette_block(D)}</div>
    <div class="card"><div class="lab">Type</div>{type_block(D)}</div>
  </div>
  <div class="card"><div class="lab">Graphic devices</div>
    <ol class="devnotes">{''.join(f'<li>{esc(t)}</li>' for t in D['devices'])}</ol>
    <div class="g-dev">{devs[0]}{devs[1]}</div><div class="g-dev light">{devs_l[0]}{devs_l[1]}</div></div>
  <div class="card"><div class="lab">Top bar, dark and light (Map, Investigate)</div><div class="bars">{topbar(D, 'dark', 'Map')}{topbar(D, 'light', 'Investigate')}</div></div>
  <div class="g-app">
    <div class="card"><div class="lab">Investigate: printed case-file cover (A4)</div>{cover(D)}</div>
    <div class="card"><div class="lab">Splash / loading</div>{splash(D)}</div>
    <div class="card notes"><div class="lab">Honest notes</div><p><b>Why it works.</b> {esc(D['good'])}</p><p><b>Weaknesses.</b> {esc(D['weak'])}</p></div>
  </div>
</section>"""


def fontfaces():
    meta = json.loads((ROOT / "fonts" / "fonts.json").read_text())
    css = ""
    for key, m in meta.items():
        w = int(re.sub(r"\D", "", key.split("-")[-1]) or 400)
        st = "font-stretch:125%;" if key.startswith("archivo-x") else ""
        css += f"@font-face{{font-family:'{m['family']}';font-weight:{w};{st}src:url(data:font/woff2;base64,{typo.woff2_b64(key)}) format('woff2');}}\n"
    return css


CSS = r"""
:root{--bg:#f4f4f2;--fg:#151618;--sub:#5c6168;--line:#d9dad6;--card:#ffffff;--acc:#2D72D2;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1012;--fg:#eceef0;--sub:#9aa1a9;--line:#2a2d31;--card:#17191c;--acc:#4C90F0;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1012;--fg:#eceef0;--sub:#9aa1a9;--line:#2a2d31;--card:#17191c;--acc:#4C90F0;color-scheme:dark}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--acc)}
code,.mono{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:.92em}
.wrap{max-width:1760px;margin:0 auto;padding:40px 48px 80px}
.hero h1{font:600 40px/1.1 Inter;margin:0 0 8px;letter-spacing:-.01em}
.hero p{max-width:980px;color:var(--sub);margin:6px 0}
.top3{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:28px 0 12px}
.t3{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;display:grid;grid-template-columns:96px 1fr;gap:18px;align-items:start}
.t3 svg{width:96px;height:96px}
.t3 h3{margin:0 0 4px;font:600 19px Inter}
.t3 .r{font:500 11px 'IBM Plex Mono';letter-spacing:.1em;color:var(--sub)}
.t3 p{margin:6px 0 0;color:var(--sub);font-size:14px}
.idx{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 8px}
.idx a{display:flex;align-items:center;gap:8px;padding:6px 12px 6px 6px;border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--fg);background:var(--card);font-size:13px}
.idx svg{width:28px;height:28px}
.method{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:16px 0 0}
.method div{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px 22px;font-size:14px;color:var(--sub)}
.method b{color:var(--fg)}
.dir{margin-top:72px;padding-top:40px;border-top:1px solid var(--line)}
.dh{display:grid;grid-template-columns:96px 1fr;gap:20px;margin-bottom:20px}
.dnum{font:500 44px/1 'IBM Plex Mono';color:var(--sub)}
.dh h2{margin:0;font:600 32px/1.15 Inter;letter-spacing:-.01em;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.pick{font:600 12px Inter;background:var(--acc);color:#fff;border-radius:99px;padding:4px 10px;letter-spacing:.02em}
.dline{font-size:19px;line-height:1.45;margin:10px 0 6px;max-width:1100px}
.dstory{color:var(--sub);max-width:1100px;margin:0 0 6px}
.dmeta{color:var(--sub);font-size:13px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 22px;margin-top:20px;min-width:0}
.lab{font:500 11px 'IBM Plex Mono';letter-spacing:.08em;text-transform:uppercase;color:var(--sub);margin-bottom:14px}
.g-mark{display:grid;grid-template-columns:minmax(0,300px) minmax(0,260px) minmax(0,1fr);gap:20px}
.g-mark .card{margin-top:0}
.bigmark svg{width:100%;max-width:256px;height:auto;display:block;border-radius:22%;box-shadow:0 0 0 1px var(--line)}
.smallmark svg{width:128px;height:128px;display:block;border-radius:22%;box-shadow:0 0 0 1px var(--line)}
.lock{display:flex;flex-direction:column}
.lockl,.lockd{border-radius:12px;padding:22px 26px;margin-bottom:12px;border:1px solid var(--line)}
.lockl svg,.lockd svg{width:100%;max-width:520px;height:auto;display:block}
.strip{display:grid;grid-template-columns:200px auto 1fr;gap:16px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
.strip:first-of-type{border-top:0}
.strip-l{font-size:13px;color:var(--sub)}
.strip-imgs{display:flex;align-items:flex-end;gap:4px}
.strip-imgs figure{margin:0;text-align:center}
.strip-imgs img{display:block;image-rendering:pixelated}
.strip-imgs figcaption{font:10px 'IBM Plex Mono';color:var(--sub)}
.strip-zoom{display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}
.zoom{image-rendering:pixelated;display:block}
.g-two{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:20px}
.pbar{display:flex;height:22px;border-radius:6px;overflow:hidden;border:1px solid var(--line);margin-bottom:16px}
.sws{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px 16px}
.sw{display:flex;gap:12px;align-items:flex-start;font-size:13px}
.sw b{display:block;font-weight:600}
.sw code{display:block}
.sw small{display:block;color:var(--sub)}
.chip{flex:none;width:40px;height:40px;border-radius:10px;border:1px solid var(--line)}
.fine{font-size:12.5px;color:var(--sub);margin:12px 0 0}
.type-name{font-size:13px;color:var(--sub);margin:4px 0}
.type-name span{opacity:.8}
.spec{font-size:40px;line-height:1.15;margin:4px 0 16px;overflow-wrap:anywhere}
.spec2{font-size:15px;margin-top:6px}
.devnotes{margin:0 0 14px;padding-left:20px;color:var(--sub);font-size:14px}
.g-dev{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.g-dev.light{margin-top:16px}
.g-dev svg{width:100%;height:auto;display:block}
.bars svg{width:100%;max-width:1000px;height:auto;display:block;margin-bottom:12px}
.g-app{display:grid;grid-template-columns:minmax(0,340px) minmax(0,520px) minmax(0,1fr);gap:20px}
.g-app .cover{width:100%;max-width:300px;height:auto;display:block;box-shadow:0 2px 14px #0002;border:1px solid var(--line)}
.g-app .splash{width:100%;max-width:480px;height:auto;display:block}
.notes p{font-size:14px;margin:0 0 10px}
.appendix{margin-top:72px;padding-top:40px;border-top:1px solid var(--line);color:var(--sub);font-size:14px}
.appendix h2{color:var(--fg);font:600 24px Inter}
.appendix li{margin:4px 0}
@media (max-width:1500px){.g-mark{grid-template-columns:minmax(0,260px) minmax(0,220px) minmax(0,1fr)}.g-app{grid-template-columns:minmax(0,300px) minmax(0,1fr)}.g-app .notes{grid-column:1/-1}.top3{grid-template-columns:1fr}.strip{grid-template-columns:150px auto 1fr}}
@media (max-width:1100px){.g-mark,.g-two,.g-dev,.method{grid-template-columns:1fr}.strip{grid-template-columns:1fr}}
"""


def build():
    for D in DIRECTIONS:
        k = D["key"]
        (ROOT / "lockups" / f"{k}.svg").write_text(lockup_svg(D, D["light"]["ink"])[0] + "\n")
        (ROOT / "lockups" / f"{k}-dark.svg").write_text(lockup_svg(D, "#FFFFFF")[0] + "\n")
    top = ""
    for i, k in enumerate(TOP3):
        D = BY_KEY[k]
        top += (f'<a class="t3" href="#d{k}" style="text-decoration:none;color:inherit">{M.svg(k, "full")}<div><div class="r">TOP PICK {i + 1} · {k[:2]}</div>'
                f'<h3>{esc(D["name"])}</h3><p>{esc(D["line"])}</p></div></a>')
    reasons = ("<p><b>Why these three.</b> Cocked Hat turns the project's central rule (sources, and honesty about how sure we are) "
               "into geometry and has the stark one-accent temperament the owner likes. W Trace is the most legible mark at 16 px "
               "and the most 'defence tech'; its line can be real data in the app. Terminator is the calmest and the only one whose "
               "main line is a computed fact every time it is drawn. Runners-up: Shells (best fit for the Connections page) and "
               "Quadkey (the most personal: Munich's own tile address).</p>")
    idx = "".join(f'<a href="#d{D["key"]}">{M.svg(D["key"], "small")}{D["key"][:2]} {esc(D["name"])}</a>' for D in DIRECTIONS)
    secs = "".join(section(D, i) for i, D in enumerate(DIRECTIONS))
    appendix = """
<div class="appendix"><h2>How this was made, and what was dropped</h2>
<ul>
<li>Every mark is drawn on a 64-unit grid (plate corner radius 14, about the macOS/Fluent rounding); the same SVG is the 1024 master. A separate 16/24 px variant has heavier strokes and fewer parts, as Microsoft's Fluent guidance recommends below 48 px.</li>
<li>Renders are from headless Chromium at device scale 1. Windows draws a taskbar icon at 24 px at 100 % scale (16 px in title bars and context menus, 32 or 48 px at 200 %), so 16-24 px is the size that matters. On a Retina screen this page shows the 1x pixels enlarged; the real Dock would use 2x assets.</li>
<li>Wordmarks in the lockups are outlined (shaped with HarfBuzz, so kerning is applied); no font is needed to display them. All fonts are SIL OFL from Google Fonts and are embedded in this page as subsets.</li>
<li>Dropped after the small-size test: <b>Racetrack</b> (a surveillance orbit; read as a paperclip / link icon), <b>Two hemispheres</b> (read as cartoon eyes), <b>Date line</b> (the real line's jogs looked random), <b>Morse WW</b> (read as a bulleted list), <b>Null Island</b> (a crosshair). Earlier versions of Great Circle (read as a handbag), Plot (a paintbrush), GMT (a speedometer) and Cocked Hat (the App Store 'A') were redrawn.</li>
<li>Example values on device mock-ups are marked as such; the few real ones (RCH4992 capture, GLEIF relationship, Munich daylight, terminator) are labelled with their source or date.</li>
<li>Not verified here: UN Blue and ESA Deep Space could not be opened directly from this sandbox (403); both were confirmed through search excerpts of the official pages. NGA and Anduril colours come from their websites' own code, not from published brand guides; no public brand guide with colour values was found for NGA, NRO, Space Force (its Air Force instruction refused this sandbox), the Bundeswehr or the BND.</li>
</ul></div>"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>World Watch Identity</title><style>{fontfaces()}{CSS}</style></head><body><div class="wrap">
<div class="hero"><h1>World Watch: ten identity directions</h1>
<p>A private OSINT dashboard that watches the whole world at once, follows connections and ownership chains, and shows only what sources report. Each direction below is a small identity system: concept, app icon with its small-size variant, wordmark, a colour system taken from a real agency or company palette (cited), two graphic devices that come from the concept, and four applications: the taskbar/Dock icon at real size, the top bar, a printed case-file cover for the Investigate page, and the splash screen.</p>
<p>Rules kept: original marks (no agency or company shape copied), real cited colours, no orange, readable at 16-24 px, no glowing globes or eyes.</p></div>
<div class="top3">{top}</div>{reasons}
<div class="idx">{idx}</div>
{secs}{appendix}
</div></body></html>"""
    (ROOT / "sheet.html").write_text(page)
    print("sheet.html", len(page) // 1024, "KB")


if __name__ == "__main__":
    build()
