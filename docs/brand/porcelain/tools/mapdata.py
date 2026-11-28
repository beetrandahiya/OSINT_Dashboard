"""Real data for the app mock-up: the latest stored payloads in data/worldwatch.db (capture ~28 Nov 2026 03:08 UTC),
projected in Web Mercator onto a 1440 x 900 board. Country outlines: Natural Earth 1:50m via data/countries-geo.json."""
import json, math, sqlite3, datetime
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
DB = "/home/user/OSINT_Dashboard/data/worldwatch.db"
GEO = "/home/user/OSINT_Dashboard/data/countries-geo.json"
W, H = 1440, 900


def payload(f):
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    r = db.execute("select payload, fetched from latest where feed=?", (f,)).fetchone()
    return json.loads(r[0]), r[1]


class View:
    """Web Mercator view: centre lon/lat and zoom (MapLibre-style, 512 px tiles)."""
    def __init__(self, lon, lat, zoom, w=W, h=H):
        self.w, self.h = w, h; self.s = 512 * 2 ** zoom
        self.cx, self.cy = self._m(lon, lat)
    def _m(self, lon, lat):
        lat = max(-85, min(85, lat))
        x = (lon + 180) / 360 * self.s
        y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * self.s
        return x, y
    def px(self, lon, lat):
        x, y = self._m(lon, lat); return x - self.cx + self.w / 2, y - self.cy + self.h / 2
    def inside(self, lon, lat, pad=0):
        x, y = self.px(lon, lat); return -pad <= x <= self.w + pad and -pad <= y <= self.h + pad


def countries(view, tol=0.6):
    d = json.load(open(GEO))["countries"]
    clip = box(-20, -20, view.w + 20, view.h + 20)
    out = []
    for c in d:
        rings = json.loads(c["rings"]) if isinstance(c["rings"], str) else c["rings"]
        polys = []
        for ring in rings:
            pts = [view.px(lon, lat) for lon, lat in ring]
            if len(pts) < 4: continue
            p = Polygon(pts)
            if not p.is_valid: p = p.buffer(0)
            if p.is_empty or not p.intersects(clip): continue
            polys.append(p.intersection(clip))
        if not polys: continue
        g = unary_union(polys).simplify(tol)
        if g.is_empty: continue
        out.append((c["iso"], c["name"], g))
    return out


def path(g):
    parts = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    s = []
    for p in parts:
        if p.geom_type != "Polygon": continue
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords)
            s.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in cs[:-1]) + "Z")
    return "".join(s)


def when(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.UTC)
