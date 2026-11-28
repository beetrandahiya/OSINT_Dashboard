import sys, json; sys.path.insert(0, 'gv')
from cam import Cam
A = json.load(open('assets/air.json')); S = json.load(open('assets/sea.json'))
pts_air = {"Brussels": (4.48, 50.90), "Duesseldorf": (6.78, 51.23), "Cologne": (6.96, 50.94), "Kloten": (8.58, 47.45), "Schwechat": (16.48, 48.14), "Villafranca": (10.85, 45.35), "MUC": (11.79, 48.35), "FRA": (8.57, 50.03)}
ac = [(r['lon'], r['lat']) for r in A['rows'] if r['lon']]
pts_sea = {"Helsinki": (24.94, 60.17), "Tallinn": (24.75, 59.44), "Mariehamn": (19.94, 60.10), "Stockholm": (18.07, 59.33), "Turku": (22.27, 60.45), "Kotka": (26.95, 60.47), "Gotland": (18.3, 57.6)}
sh = [(s['lon'], s['lat']) for s in S['ships'] if s['links']]
def report(cam, pts, extra):
    xs = []
    for k, (lo, la) in pts.items():
        x, y, v = cam.proj(lo, la); print(f"  {k:12s} {x:7.0f} {y:6.0f} {v}")
    P = [cam.proj(lo, la) for lo, la in extra]
    X = [p[0] for p in P]; Y = [p[1] for p in P]
    print("  assets x", round(min(X)), round(max(X)), "y", round(min(Y)), round(max(Y)), "inside", sum(1 for p in P if 400 < p[0] < 1440 and 70 < p[1] < 1040), "/", len(P))
for c in [(10.6, 41.8, 0.20, 10.6, 48.4, 1500, 920, 600), (10.6, 42.5, 0.19, 10.6, 48.6, 1450, 920, 580)]:
    print("AIR", c); report(Cam(*c), pts_air, ac)
for c in [(22.5, 54.8, 0.17, 22.5, 59.4, 1450, 920, 600), (22.0, 55.2, 0.16, 22.0, 59.6, 1450, 920, 580)]:
    print("SEA", c); report(Cam(*c), pts_sea, sh)
