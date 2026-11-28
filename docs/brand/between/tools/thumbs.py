import sys, math
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between")
import render as RD
from cam import Cam
GEO = 35786 / 6371
def geo_cam(lon, lat, R, cx, cy): return Cam(lon, lat, GEO, lon, lat, R / math.tan(math.asin(1 / (1 + GEO))), cx, cy)
s = .1
CAMS = [geo_cam(42, 25, 44, 96, 54), Cam(19, 35, .42, 34, 49, 150, 96, 43), geo_cam(112, 22, 44, 96, 54),
        Cam(35.2, 48.3, .16, 35.2, 48.3, 200, 96, 54), Cam(30, 74, 2.4, 30, 74, 47 / math.tan(math.asin(1 / 3.4)), 96, 53),
        Cam(27, 33.5, .066, 44, 34, 125, 96, 36)]
OUT = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between/out"
for ground, back, name in [("photo", "space", "A"), ("ink", "porcelain", "B-l"), ("ink", "night", "B-d"), ("silver-light", "porcelain", "C-l"), ("silver-dark", "night", "C-d")]:
    for i, c in enumerate(CAMS):
        RD.save(RD.render(c, ground, back, 192, 108, K=1.5), f"{OUT}/t-{name}-{i}.webp", 192, 108)
    print(name)
