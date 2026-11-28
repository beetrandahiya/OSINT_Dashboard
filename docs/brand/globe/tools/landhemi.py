"""Land share of the hemisphere centred on a point, from Natural Earth admin-0 outlines (the app's countries-geo.json)."""
import json, math, sys
import numpy as np
import shapely
from shapely.geometry import Polygon
d = json.load(open('/home/user/OSINT_Dashboard/data/countries-geo.json'))
polys = []
for c in d['countries']:
    for ring in c['rings']:
        if len(ring) >= 4:
            p = Polygon(ring)
            if not p.is_valid: p = p.buffer(0)
            polys.append(p)
land = shapely.union_all(polys)
shapely.prepare(land)
# Fibonacci sphere sample
N = 400000
i = np.arange(N) + 0.5
lat = np.degrees(np.arcsin(1 - 2 * i / N))
lon = (np.degrees(np.pi * (1 + 5 ** 0.5) * i) % 360) - 180
isl = shapely.contains_xy(land, lon, lat)
print("land share of the whole Earth:", round(isl.mean() * 100, 1), "%")
np.save("land_sample.npy", np.stack([lat, lon, isl.astype(float)]))
def share(lat0, lon0):
    D = math.pi / 180
    c = np.sin(lat0 * D) * np.sin(lat * D) + np.cos(lat0 * D) * np.cos(lat * D) * np.cos((lon - lon0) * D)
    h = c >= 0
    return isl[h].mean() * 100, isl[h].sum() / isl.sum() * 100
for name, p in [("Munich", (48.137, 11.575)), ("Nantes (land hemisphere, textbook)", (47.217, -1.533))]:
    s, frac = share(*p)
    print(f"{name}: hemisphere {s:.1f} % land, holds {frac:.1f} % of all land")
# search the best centre on a 1-degree grid near Europe
best = max(((share(la, lo)[0], la, lo) for la in range(30, 66, 1) for lo in range(-20, 30, 1)))
print("best centre (1 deg grid, 30-65N 20W-30E):", best)
