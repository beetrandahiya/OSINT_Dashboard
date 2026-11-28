"""Footprint, Anduril parts (black globe, white footprint, black pupil) on a soft lavender-to-blue 3D tile.
Tile colours are Tailwind CSS v3.4.17 palette values (src/public/colors.js)."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/globe")
import geo, gmarks as G
from geo import MUC

TW = {"violet-50": "#F5F3FF", "violet-100": "#EDE9FE", "violet-200": "#DDD6FE", "violet-300": "#C4B5FD",
      "indigo-100": "#E0E7FF", "indigo-200": "#C7D2FE", "indigo-300": "#A5B4FC",
      "blue-100": "#DBEAFE", "blue-200": "#BFDBFE", "sky-50": "#F0F9FF", "sky-100": "#E0F2FE", "sky-200": "#BAE6FD"}
BLACK, WHITE = "#010101", "#FFFFFF"   # Anduril black, white

VARIANTS = {
    "soft": dict(stops=[(0, "violet-100"), (1, "sky-100")], dir=(0, 0, 1, 1), hi=.35, shade="indigo-200", sphere=True),
    "lavender-blue": dict(stops=[(0, "violet-200"), (1, "sky-200")], dir=(0, 0, 1, 1), hi=.35, shade="indigo-300", sphere=True),
    "mesh": dict(stops=None, dir=None, hi=.3, shade="indigo-300", sphere=True),
    "vertical": dict(stops=[(0, "violet-200"), (1, "blue-100")], dir=(0, 0, 0, 1), hi=.3, shade="indigo-200", sphere=True),
    "lavender-blue-flat": dict(stops=[(0, "violet-200"), (1, "sky-200")], dir=(0, 0, 1, 1), hi=.35, shade="indigo-300", sphere=False),
}


def tile(v, uid, size):
    t = VARIANTS[v]
    d = "<defs>"
    if t["stops"]:
        x1, y1, x2, y2 = t["dir"]
        d += f'<linearGradient id="b{uid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">' + "".join(
            f'<stop offset="{o}" stop-color="{TW[c]}"/>' for o, c in t["stops"]) + "</linearGradient>"
        base = f'<rect width="64" height="64" rx="{G.RT}" fill="url(#b{uid})"/>'
    else:   # two soft colour pools on white: lavender top-left, light blue bottom-right
        d += (f'<radialGradient id="p{uid}" cx=".18" cy=".12" r=".85"><stop offset="0" stop-color="{TW["violet-300"]}"/>'
              f'<stop offset="1" stop-color="{TW["violet-300"]}" stop-opacity="0"/></radialGradient>'
              f'<radialGradient id="q{uid}" cx=".9" cy=".95" r=".9"><stop offset="0" stop-color="{TW["sky-200"]}"/>'
              f'<stop offset="1" stop-color="{TW["sky-200"]}" stop-opacity="0"/></radialGradient>')
        base = (f'<rect width="64" height="64" rx="{G.RT}" fill="{TW["indigo-100"]}"/>'
                f'<rect width="64" height="64" rx="{G.RT}" fill="url(#p{uid})"/><rect width="64" height="64" rx="{G.RT}" fill="url(#q{uid})"/>')
    # soft light from the top left and a little shade at the bottom edge: the 3D part
    d += (f'<radialGradient id="h{uid}" cx=".5" cy="0" r=".8"><stop offset="0" stop-color="#FFFFFF" stop-opacity="{t["hi"]}"/>'
          f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
          f'<linearGradient id="s{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="{TW[t["shade"]]}" stop-opacity="0"/>'
          f'<stop offset="1" stop-color="{TW[t["shade"]]}" stop-opacity=".55"/></linearGradient>')
    over = (f'<rect width="64" height="64" rx="{G.RT}" fill="url(#h{uid})"/><rect width="64" height="64" rx="{G.RT}" fill="url(#s{uid})"/>'
            f'<rect x=".5" y=".5" width="63" height="63" rx="{G.RT - .5}" fill="none" stroke="#FFFFFF" stroke-opacity=".7" stroke-width="1"/>')
    return d, base + over


def footprint(v, size="full", uid="u"):
    t = VARIANTS[v]
    r = 26.5 if size == "full" else 29.0
    rho = geo.horizon_angle(G.S2_ALT)
    mx, my, _ = geo.project_pts([MUC], G.FP_CAM, G.C, G.C, r)[0]
    defs, tl = tile(v, uid + size[0], size)
    body = tl
    if t["sphere"] and size == "full":
        # contact shadow under the globe and a faint sheen on it, so the Earth sits on the tile as a ball
        defs += (f'<radialGradient id="sh{uid}" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{TW["indigo-300"]}" stop-opacity=".55"/>'
                 f'<stop offset="1" stop-color="{TW["indigo-300"]}" stop-opacity="0"/></radialGradient>'
                 f'<radialGradient id="g{uid}" cx=".34" cy=".26" r=".8"><stop offset="0" stop-color="#2A2A33"/>'
                 f'<stop offset=".55" stop-color="{BLACK}"/></radialGradient>')
        body += f'<ellipse cx="{G.C + 1.5}" cy="{G.C + r * .82}" rx="{r * .95}" ry="{r * .32}" fill="url(#sh{uid})"/>'
        body += G.circle(G.C, G.C, r, f"url(#g{uid})")
    else:
        body += G.circle(G.C, G.C, r, BLACK)
    body += f'<path d="{G.cap(MUC[0], MUC[1], rho, G.FP_CAM, r)}" fill="{WHITE}"/>'
    body += G.circle(mx, my, 3.6 if size == "full" else 5.2, BLACK)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{defs}</defs>{body}</svg>'
