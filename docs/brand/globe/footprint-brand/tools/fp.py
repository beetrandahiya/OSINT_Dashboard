"""The Footprint mark (geometry unchanged from round two) with any palette."""
import sys, math
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/globe")
import geo, gmarks as G
from geo import MUC

def footprint(v, pal, plate=True):
    r = 26.5 if v == "full" else 29.0
    rho = geo.horizon_angle(G.S2_ALT)
    mx, my, _ = geo.project_pts([MUC], G.FP_CAM, G.C, G.C, r)[0]
    b = ""
    if plate:
        if pal.get("plate2"):   # top-to-bottom gradient between two brand colours
            gid = "g" + pal["plate"][1:] + pal["plate2"][1:] + v[0]
            b += (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["plate"]}"/>'
                  f'<stop offset="1" stop-color="{pal["plate2"]}"/></linearGradient></defs>'
                  f'<rect width="64" height="64" rx="{G.RT}" fill="url(#{gid})"/>')
        else:
            b += f'<rect width="64" height="64" rx="{G.RT}" fill="{pal["plate"]}"/>'
    b += G.circle(G.C, G.C, r, pal["globe"])
    if pal.get("rim"):
        b += G.circle(G.C, G.C, r - 0.6, "none", pal["rim"], 1.2 if v == "full" else 2)
    b += f'<path d="{G.cap(MUC[0], MUC[1], rho, G.FP_CAM, r)}" fill="{pal["fp"]}"/>'
    b += G.circle(mx, my, 3.6 if v == "full" else 5.2, pal["pupil"])
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{b}</svg>'
