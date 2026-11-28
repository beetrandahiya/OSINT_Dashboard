"""World Watch globe marks on a 64-unit grid.

mark(key, variant, uid, mode) -> SVG markup (viewBox 0 0 64 64).
variant: "full" (32 px and up) or "small" (16 and 24 px).
mode: "icon" (with its plate), "on-dark" or "on-light" (no plate, for lockups and the top bar).
Every shape is computed from a real fact; the facts are in FACTS and in the page's text.
"""
import json, math, functools
import geo
from geo import MUC, ortho, project_pts, small_circle

RT = 14  # plate corner radius on the 64 grid
C = 32.0


def F(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def wrap(inner, uid, plate=None):
    if plate is None:
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{inner}</svg>'
    # every mark stays clear of the rounded corners, so the plate needs no clipping
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            f'<rect width="64" height="64" rx="{RT}" fill="{plate}"/>{inner}</svg>')


def circle(cx, cy, r, fill="none", stroke=None, sw=0):
    s = f' stroke="{stroke}" stroke-width="{F(sw)}"' if stroke else ""
    return f'<circle cx="{F(cx)}" cy="{F(cy)}" r="{F(r)}" fill="{fill}"{s}/>'


def onlimb(pts, cam, r, cx=C, cy=C):
    """Project lat/lon points; hidden ones are pushed onto the limb (traces the limb arc for filled areas)."""
    out = []
    for i, (la, lo) in enumerate(pts):
        x, y, vis = ortho(la, lo, *cam)
        if not vis:
            m = math.hypot(x, y) or 1
            x, y = x / m, y / m
        out.append(("M" if i == 0 else "L") + f"{cx + x * r:.2f},{cy - y * r:.2f}")
    return " ".join(out) + " Z"


def slerp(a, b, n=80):
    D = geo.D
    v = lambda p: (math.cos(p[0] * D) * math.cos(p[1] * D), math.cos(p[0] * D) * math.sin(p[1] * D), math.sin(p[0] * D))
    A, B = v(a), v(b)
    w = math.acos(max(-1, min(1, sum(x * y for x, y in zip(A, B)))))
    pts = []
    for i in range(n + 1):
        t = i / n
        s1, s2 = math.sin((1 - t) * w) / math.sin(w), math.sin(t * w) / math.sin(w)
        x, y, z = (s1 * A[k] + s2 * B[k] for k in range(3))
        pts.append((math.asin(z) / D, math.atan2(y, x) / D))
    return pts


# =============================================================== 1 OKO: the Molniya orbit, true scale
RE = 6371.0
MOL_PERIGEE, MOL_APOGEE = 600.0, 39700.0          # km above the surface (typical Molniya orbit)
_rp, _ra = RE + MOL_PERIGEE, RE + MOL_APOGEE
MOL_A = (_rp + _ra) / 2
MOL_E = (_ra - _rp) / (_ra + _rp)
MOL_B = MOL_A * math.sqrt(1 - MOL_E ** 2)
MOL_PERIOD_H = 2 * math.pi * math.sqrt(MOL_A ** 3 / 398600.4418) / 3600


def molniya_times(n):
    """Positions (x from the ellipse centre, y) at n equal time steps (Kepler's equation)."""
    out = []
    for k in range(n):
        M = 2 * math.pi * k / n
        E = M
        for _ in range(50):
            E -= (E - MOL_E * math.sin(E) - M) / (1 - MOL_E * math.cos(E))
        out.append((MOL_A * math.cos(E), MOL_B * math.sin(E)))
    return out


OKO_PAL = {"icon": dict(plate="#004990", ring="#FFFFFF", earth="#FFFFFF", tick="#118ACB"),
           "on-dark": dict(plate=None, ring="#FFFFFF", earth="#FFFFFF", tick="#118ACB"),
           "on-light": dict(plate=None, ring="#004990", earth="#004990", tick="#118ACB")}


def m_oko(v, uid, mode="icon", ticks=False):
    p = OKO_PAL[mode]
    span = 52.0 if v == "full" else 56.0
    s = span / (2 * MOL_A)
    A, B, c, R = MOL_A * s, MOL_B * s, MOL_A * MOL_E * s, RE * s
    sw = 2.0 if v == "full" else 4.0
    ex = C - c                       # Earth at the focus, left of centre
    body = ""
    if ticks and v == "full":
        for x, y in molniya_times(24):
            body += circle(C - x * s, C - y * s, 1.15, p["ring"])  # perigee on the Earth's side
    else:
        body += f'<ellipse cx="{C}" cy="{C}" rx="{F(A - sw / 2)}" ry="{F(B - sw / 2)}" fill="none" stroke="{p["ring"]}" stroke-width="{F(sw)}"/>'
    body += circle(ex, C, R, p["earth"])
    return wrap(body, uid, p["plate"])


# =============================================================== 2 FOOTPRINT: what Sentinel-2 sees above Munich
S2_ALT = 786.0
FP_CAM = (20.0, -10.0)
FP_PAL = {"icon": dict(plate="#111418", globe="#F6F7F9", fp="#2D72D2", pupil="#111418", rim=None),
          "on-dark": dict(plate=None, globe="#F6F7F9", fp="#4C90F0", pupil="#111418", rim=None),
          "on-light": dict(plate=None, globe="#111418", fp="#2D72D2", pupil="#F6F7F9", rim=None)}


def cap(lat, lon, rho, cam, r):
    return onlimb(small_circle(lat, lon, rho, 720), cam, r)


def m_footprint(v, uid, mode="icon"):
    p = FP_PAL[mode]
    r = 26.5 if v == "full" else 29.0
    rho = geo.horizon_angle(S2_ALT)
    mx, my, _ = project_pts([MUC], FP_CAM, C, C, r)[0]
    body = circle(C, C, r, p["globe"]) + f'<path d="{cap(MUC[0], MUC[1], rho, FP_CAM, r)}" fill="{p["fp"]}"/>'
    body += circle(mx, my, 3.6 if v == "full" else 5.2, p["pupil"])
    return wrap(body, uid, p["plate"])


# =============================================================== 3 UNROLLED: the globe becomes the web map at Greenwich
UN_PAL = {"icon": dict(plate="#0D2F4B", paper="#F0F0F0", ink="#0D2F4B", acc="#2FA3AA"),
          "on-dark": dict(plate=None, paper="#F0F0F0", ink=None, acc="#2FA3AA"),
          "on-light": dict(plate=None, paper="#0D2F4B", ink=None, acc="#2FA3AA")}


def m_unrolled(v, uid, mode="icon", gap=None):
    p = UN_PAL[mode]
    gap = gap or p["plate"] or "#000"     # lines are drawn in the colour behind the mark (no masks: Safari-safe in <use>)
    r = 25.0 if v == "full" else 27.0
    x0, top, bot = C, C - r, C + r
    t = r / 2
    g = 1.5 if v == "full" else 2.6
    sw = 1.8 if v == "full" else 3.0
    mer = [30, 60] if v == "full" else [45]
    body = f'<path d="M{F(x0 - g / 2)},{top} A{r},{r} 0 0 0 {F(x0 - g / 2)},{bot} Z" fill="{p["paper"]}"/>'
    body += f'<line x1="{x0 - r - 1}" y1="{C}" x2="{x0}" y2="{C}" stroke="{gap}" stroke-width="{F(sw)}"/>'
    for s in mer:
        e = r * math.sin(s * geo.D)
        body += f'<path d="M{x0},{top - 1} A{F(e)},{r + 1} 0 0 0 {x0},{bot + 1}" fill="none" stroke="{gap}" stroke-width="{F(sw)}"/>'
    # web-map tiles: zoom 2 is 4 x 4 tiles; the eastern half is columns 2 and 3. Munich is tile 2/2/1.
    for col in range(2):
        for row in range(4):
            X, Y = x0 + col * t + g / 2, top + row * t + g / 2
            fill = p["acc"] if (col == 0 and row == 1) else p["paper"]
            body += f'<rect x="{F(X)}" y="{F(Y)}" width="{F(t - g)}" height="{F(t - g)}" fill="{fill}"/>'
    return wrap(body, uid, p["plate"])


# =============================================================== 4 ABOVE HOME: the hemisphere seen from straight above Munich
LAND_JSON = "/home/user/OSINT_Dashboard/data/countries-geo.json"
AH_PAL = {"icon": dict(plate="#007194", globe="#FFFFFF", land="#007194", home="#000000"),
          "on-dark": dict(plate=None, globe="#CCE3EA", land="#007194", home="#000000"),
          "on-light": dict(plate=None, globe="#CCE3EA", land="#007194", home="#000000")}


@functools.lru_cache(None)
def _land():
    import shapely
    from shapely.geometry import Polygon
    d = json.load(open(LAND_JSON))
    polys = []
    for c in d["countries"]:
        for ring in c["rings"]:
            if len(ring) >= 4:
                q = Polygon(ring)
                polys.append(q if q.is_valid else q.buffer(0))
    return shapely.union_all(polys)


@functools.lru_cache(None)
def _hemi_land_paths(r, tol):
    """Land of the hemisphere centred on Munich, clipped at the horizon in lon/lat, projected, simplified."""
    import shapely
    from shapely.geometry import Polygon
    from shapely.ops import transform
    p0, l0 = MUC[0] * geo.D, MUC[1]
    edge = []
    for i in range(721):
        lon = -180 + i * 0.5
        lat = math.degrees(math.atan(-math.cos((lon - l0) * geo.D) / math.tan(p0)))
        edge.append((lon, lat))
    hemi = Polygon(edge + [(180, 90), (-180, 90)])
    land = _land().intersection(hemi)
    def proj(x, y, z=None):
        X, Y, _ = ortho(y, x, *MUC)
        return C + X * r, C - Y * r
    # densify long straight edges first so the horizon follows the limb
    land = shapely.segmentize(land, 0.5)
    pl = transform(proj, land).simplify(tol, preserve_topology=False)
    out = []
    geoms = getattr(pl, "geoms", [pl])
    for g in geoms:
        if g.is_empty or g.area < (0.6 if tol > 0.4 else 0.25):
            continue
        for ring in [g.exterior] + list(g.interiors):
            cs = list(ring.coords)
            out.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in cs) + " Z")
    return " ".join(out)


def m_above(v, uid, mode="icon"):
    p = AH_PAL[mode]
    r = 26.5 if v == "full" else 28.5
    d = _hemi_land_paths(r, 0.25 if v == "full" else 0.9)
    body = circle(C, C, r, p["globe"]) + f'<path d="{d}" fill="{p["land"]}" fill-rule="evenodd"/>'
    body += circle(C, C, 2.2 if v == "full" else 3.4, p["home"], "#FFFFFF", 1.0 if v == "full" else 1.4)
    return wrap(body, uid, p["plate"])


# =============================================================== 5 OCTANT: a triangle with three right angles (Munich's)
OC_CAM = (35.264, 45.0)
OC_PAL = {"icon": dict(plate="#00205B", globe="#FFFFFF", tri="#0079C0", mark="#FFFFFF"),
          "on-dark": dict(plate=None, globe="#FFFFFF", tri="#0079C0", mark="#FFFFFF"),
          "on-light": dict(plate=None, globe="#00205B", tri="#FFFFFF", mark="#00205B")}


def m_octant(v, uid, mode="icon"):
    p = OC_PAL[mode]
    r = 26.5 if v == "full" else 29.0
    A, B, Cc = (90, 0), (0, 0), (0, 90)
    d = onlimb(slerp(A, B) + slerp(B, Cc) + slerp(Cc, A), OC_CAM, r)
    body = circle(C, C, r, p["globe"]) + f'<path d="{d}" fill="{p["tri"]}"/>'
    return wrap(body, uid, p["plate"])


# =============================================================== 6 LUNE: home's hour, Central European Time (7.5 E to 22.5 E)
LU_PAL = {"icon": dict(plate="#252525", globe="#007EB1", lune="#EDF1F2"),
          "on-dark": dict(plate=None, globe="#007EB1", lune="#EDF1F2"),
          "on-light": dict(plate=None, globe="#007EB1", lune="#FFFFFF")}


def m_lune(v, uid, mode="icon"):
    p = LU_PAL[mode]
    cam = (0.0, 15.0)
    r = 26.5 if v == "full" else 29.0
    pts = [(-90 + i, 7.5) for i in range(181)] + [(90 - i, 22.5) for i in range(181)]
    body = circle(C, C, r, p["globe"]) + f'<path d="{onlimb(pts, cam, r)}" fill="{p["lune"]}"/>'
    return wrap(body, uid, p["plate"])


MARKS = {"oko": m_oko, "footprint": m_footprint, "unrolled": m_unrolled, "above": m_above,
         "octant": m_octant, "lune": m_lune}


def mark(key, variant="full", uid="x", mode="icon", gap=None):
    if key == "unrolled":
        return m_unrolled(variant, uid, mode, gap)
    return MARKS[key](variant, uid, mode)


def inner(svg):
    """The markup inside a mark's <svg>, for <symbol> sprites."""
    return svg[svg.index(">") + 1: svg.rindex("</svg>")]
