"""Exact sphere geometry for the globe marks: orthographic projection, small circles, solar position."""
import math

D = math.pi / 180
MUC = (48.137, 11.575)          # Munich, the app's home point (config.py default)
R_EARTH = 6371.0


def ortho(lat, lon, lat0, lon0):
    """Orthographic projection. Returns (x, y, visible); x east, y north, unit sphere."""
    p, l, p0 = lat * D, (lon - lon0) * D, lat0 * D
    x = math.cos(p) * math.sin(l)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l)
    c = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l)
    return x, y, c >= -1e-9


def dest(lat, lon, brg, dist):
    """Point at angular distance dist (deg) and bearing brg (deg) from (lat, lon)."""
    p1, l1, b, d = lat * D, lon * D, brg * D, dist * D
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return p2 / D, ((l2 / D + 540) % 360) - 180


def small_circle(lat, lon, radius, n=360):
    return [dest(lat, lon, 360 * i / n, radius) for i in range(n + 1)]


def horizon_angle(alt_km):
    """Angular radius (deg) of the area a satellite at alt_km can see (horizon circle)."""
    return math.acos(R_EARTH / (R_EARTH + alt_km)) / D


def project_path(pts, cam, cx, cy, r, close=False):
    """Project lat/lon points with camera cam=(lat0, lon0) into an SVG path on a disc (cx, cy, r).
    Hidden stretches break the path."""
    out, pen = [], False
    for lat, lon in pts:
        x, y, vis = ortho(lat, lon, *cam)
        if not vis:
            pen = False
            continue
        X, Y = cx + x * r, cy - y * r
        out.append(("L" if pen else "M") + f"{X:.2f},{Y:.2f}")
        pen = True
    s = " ".join(out)
    return s + (" Z" if close else "")


def project_pts(pts, cam, cx, cy, r):
    res = []
    for lat, lon in pts:
        x, y, vis = ortho(lat, lon, *cam)
        res.append((cx + x * r, cy - y * r, vis))
    return res


# ---------------------------------------------------------------- sun (NOAA low-precision equations)
def sun(utc):
    """utc: datetime (naive UTC). Returns (declination deg, subsolar lat, subsolar lon)."""
    import datetime as dt
    jd = (utc - dt.datetime(2000, 1, 1, 12)).total_seconds() / 86400 + 2451545.0
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360
    g = (357.528 + 0.9856003 * n) % 360
    lam = L + 1.915 * math.sin(g * D) + 0.020 * math.sin(2 * g * D)
    eps = 23.439 - 0.0000004 * n
    decl = math.asin(math.sin(eps * D) * math.sin(lam * D)) / D
    ra = math.atan2(math.cos(eps * D) * math.sin(lam * D), math.cos(lam * D)) / D
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    lon = ((ra - gmst + 540) % 360) - 180
    return decl, decl, lon


def sun_alt(lat, lon, sublat, sublon):
    """Sun altitude (deg) at (lat, lon) for subsolar point (sublat, sublon)."""
    c = (math.sin(lat * D) * math.sin(sublat * D)
         + math.cos(lat * D) * math.cos(sublat * D) * math.cos((lon - sublon) * D))
    return 90 - math.acos(max(-1, min(1, c))) / D
