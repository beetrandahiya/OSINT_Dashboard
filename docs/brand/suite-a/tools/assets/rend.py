import sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between')
import render as RD
from cam import Cam
OUT = '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between/out'
for name, c in [("s-air", (11.2, 42.0, 0.20, 11.2, 48.5, 1450, 920, 600)), ("s-sea", (22.5, 54.8, 0.17, 22.5, 59.4, 1450, 920, 600))]:
    t = time.time(); RD.save(RD.render(Cam(*c), "photo", "space"), f"{OUT}/{name}.webp"); print(name, round(time.time() - t, 1))
