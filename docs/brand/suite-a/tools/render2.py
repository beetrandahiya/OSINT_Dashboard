import sys
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between")
import render as RD, numpy as np
from cam import Cam
OUT = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between/out"
MAPCAM = Cam(19, 35, 0.42, 34, 49, 1500, 920, 450)
pass
# the other pages: the Earth's limb low on the screen, dimmed, so panels sit in space with the planet below
HCAM = Cam(40, 14, 0.9, 42, 44, 1500, 960, 830)
a = RD.render(HCAM, "photo", "space").astype(np.float32) * .55
RD.save(np.clip(a, 0, 255).astype(np.uint8), f"{OUT}/s-suite.webp")
print("ok")
