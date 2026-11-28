"""Footprint icon, rendered: a glossy black globe with the white Sentinel-2 footprint around Munich, on an
almost-white porcelain tile (light) or a near-black one (dark twin). Pure numpy, no dependencies but numpy + PIL-free
PNG writer. Geometry is the same as the vector mark (gmarks.py): 64-unit grid, globe r 26.5 centred, camera 20N 10W,
786 km horizon cap (27.1 deg) around Munich, pupil r 3.6 at Munich's projected point. Colours: Tailwind CSS v3.4.17."""
import math, struct, zlib, sys
import numpy as np
sys.path.insert(0, "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/globe")
import geo, gmarks as G
from geo import MUC

TW = {"white": "#ffffff", "violet-50": "#f5f3ff", "violet-100": "#ede9fe", "violet-200": "#ddd6fe",
      "sky-50": "#f0f9ff", "sky-100": "#e0f2fe", "indigo-50": "#eef2ff", "indigo-950": "#1e1b4b",
      "slate-950": "#020617", "zinc-950": "#09090b", "zinc-900": "#18181b", "zinc-100": "#f4f4f5", "zinc-200": "#e4e4e7",
      "violet-950": "#2e1065", "sky-950": "#082f49", "black": "#010101"}


def lin(h):
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def nrm(v):
    v = np.array(v, dtype=np.float32); return v / np.linalg.norm(v)


def erf(x):  # Abramowitz-Stegun 7.1.26
    s = np.sign(x); x = np.abs(x); t = 1 / (1 + 0.3275911 * x)
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


THEMES = {
    # pools: (colour, cx, cy, radius, strength) in tile fractions; whispers of Tailwind's 50/100 steps on white
    "light": dict(base="white", pools=[("violet-100", .12, .08, 1.0, .75), ("sky-100", .95, 1.0, 1.0, .85)],
                  globe="black", cap="white", pupil="black", shadow="indigo-950", shadow_a=.24, rim_env="violet-50", bevel_col="violet-200"),
    "light-palest": dict(base="white", pools=[("violet-100", .12, .08, 1.0, 1.0), ("sky-100", .95, 1.0, 1.0, 1.0)],
                         globe="black", cap="white", pupil="black", shadow="indigo-950", shadow_a=.30, rim_env="violet-50"),
    "light-white": dict(base="white", pools=[("violet-50", .12, .08, 1.0, 1.0), ("sky-50", .95, 1.0, 1.0, 1.0)],
                        globe="black", cap="white", pupil="black", shadow="indigo-950", shadow_a=.30, rim_env="white"),
    "dark": dict(base="zinc-950", pools=[("violet-950", .12, .08, 1.0, .32), ("sky-950", .95, 1.0, 1.0, .4)],
                 globe="zinc-100", cap="black", pupil="zinc-100", shadow="black", shadow_a=.55, rim_env="zinc-900",
                 bevel_col="black", bevel_k=.6, bevel_spec=.3, atm=.25, atm_col="white"),
    "dark-planet": dict(base="zinc-900", pools=[("violet-950", .12, .08, 1.0, .35), ("sky-950", .95, 1.0, 1.0, .45)],
                 globe="black", cap="zinc-100", pupil="black", shadow="black", shadow_a=.6, tight=.3, rim_env="zinc-900",
                 bevel_col="black", bevel_k=.6, bevel_spec=.3, atm=.7, atm_w=1.0, atm_col="sky-100", sheen=.05),
}


def render(theme="light", out=1024, ss=3, R=26.5, pupil=3.6, bevel=1.6):
    T = THEMES[theme]; N = out * ss; s = N / 64.0
    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    x = (xs + .5) / s; y = (ys + .5) / s                    # 64-grid units, y down
    # ---- tile: rounded rect, signed distance, bevel height field
    qx = np.abs(x - 32) - (32 - G.RT); qy = np.abs(y - 32) - (32 - G.RT)
    d = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - G.RT
    cov = np.clip(.5 - d * s, 0, 1)                           # coverage (supersampled later)
    t = np.clip(-d / bevel, 0, 1); h = bevel * (1 - (1 - t) ** 2)
    gy, gx = np.gradient(h, 1 / s)
    n = np.stack([-gx, -gy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = nrm([-.38, -.72, .58]); V = np.array([0, 0, 1], np.float32); H = nrm(L + V)
    base = np.broadcast_to(lin(TW[T["base"]]), (N, N, 3)).copy()
    for col, cx, cy, r, a in T["pools"]:
        w = (a * np.clip(1 - np.hypot(x / 64 - cx, y / 64 - cy) / r, 0, 1) ** 1.6)[..., None]
        base = base * (1 - w) + lin(TW[col]) * w
    # soft top light: the upper face is a touch brighter than the lower
    base *= (1.02 - .045 * (y / 64))[..., None]
    nl = np.clip(n @ L, 0, 1); flat = float(L[2])
    # bevel: edges turned away from the light take on a tint (not grey), edges facing it catch a thin highlight
    kshade = (np.clip(flat - nl, 0, 1) * T.get("bevel_k", .55))[..., None]
    tile = base * (1 - kshade) + lin(TW[T.get("bevel_col", "violet-200")]) * kshade
    spec = np.clip((np.clip(n @ H, 0, 1) ** 40 - float(H[2]) ** 40), 0, 1) * T.get("bevel_spec", .9)
    tile = tile + spec[..., None]
    # ---- contact shadow of the globe on the tile (blurred disc, analytic), cast down from the light
    dist = np.hypot(x - 32 - .5, y - 32 - 2.4)
    soft = .5 * (1 - erf((dist - R * .985) / (2.6 * math.sqrt(2))))
    dist2 = np.hypot(x - 32 - .15, y - 32 - .9)
    tight = .5 * (1 - erf((dist2 - R * .995) / (.9 * math.sqrt(2))))
    sh = np.clip(T["shadow_a"] * soft + T.get("tight", .14) * tight, 0, .75)[..., None]
    tile = tile * (1 - sh) + lin(TW[T["shadow"]]) * sh
    img = tile
    # ---- globe: orthographic sphere seen from FP_CAM
    nx = (x - 32) / R; ny = (y - 32) / R; rr = nx * nx + ny * ny; inside = rr < 1
    nz = np.sqrt(np.clip(1 - rr, 0, 1))
    lat0, lon0 = map(math.radians, G.FP_CAM)
    X, Y = nx, -ny; rho = np.sqrt(np.clip(rr, 1e-12, 1)); c = np.arcsin(np.clip(rho, 0, 1))
    lat = np.arcsin(np.clip(np.cos(c) * math.sin(lat0) + Y * np.sin(c) * math.cos(lat0) / rho, -1, 1))
    lon = lon0 + np.arctan2(X * np.sin(c), rho * np.cos(c) * math.cos(lat0) - Y * np.sin(c) * math.sin(lat0))
    pm, lm = map(math.radians, MUC)
    cosd = np.sin(lat) * math.sin(pm) + np.cos(lat) * math.cos(pm) * np.cos(lon - lm)
    capr = math.radians(geo.horizon_angle(G.S2_ALT))
    incap = cosd > math.cos(capr)
    mx, my, _ = geo.project_pts([MUC], G.FP_CAM, G.C, G.C, R)[0]
    inpup = np.hypot(x - mx, y - my) < pupil
    alb = np.broadcast_to(lin(TW[T["globe"]]), (N, N, 3)).copy()
    alb[incap] = lin(TW[T["cap"]]); alb[inpup] = lin(TW[T["pupil"]])
    N3 = np.stack([nx, ny, nz], -1)
    ndl = np.clip(N3 @ L, 0, 1)
    tilec = lin(TW[T["rim_env"]])
    bounce = (smooth(-.2, 1, ny) * .16)[..., None] * tilec          # light bounced up from the tile
    k = T.get("lambert", (.70, .36))
    diff = alb * ((k[0] + k[1] * ndl)[..., None] + bounce)
    # matte sheen on the dark body (strongest towards the light), like the earlier #2A2A33 sheen
    sheen = (T.get("sheen", .030) * ndl ** 2.2)[..., None] * lin(TW[T.get("sheen_col", "zinc-200")])
    dark = ~(incap | inpup) if T["globe"] == "black" else (incap | inpup)
    diff = diff + np.where(dark[..., None], sheen, 0)
    # atmosphere: a thin glow just inside the limb, brightest on the sunlit side
    edge = (1 - np.sqrt(np.clip(rr, 0, 1))) * R                       # distance from the limb in grid units
    dot2 = (nx * L[0] + ny * L[1]) / np.maximum(np.sqrt(rr), 1e-6) / math.hypot(L[0], L[1])
    side = .12 + .88 * smooth(-.75, 1.0, dot2)
    atm = (T.get("atm", .55) * np.exp(-edge / T.get("atm_w", .9)) * side)[..., None]
    globe = diff * (1 - atm) + lin(TW[T.get("atm_col", "sky-100")]) * atm
    # limb antialias via supersampling; the edge itself gets the tile's rim colour mixed in by the coverage
    gm = inside[..., None]
    img = np.where(gm, globe, img)
    # ---- downsample (box) in linear light, then sRGB
    def down(a):
        return a.reshape(out, ss, out, ss, *a.shape[2:]).mean((1, 3))
    rgb = down(img * cov[..., None]); a = down(cov)
    rgb = np.where(a[..., None] > 0, rgb / np.maximum(a[..., None], 1e-6), 0)
    px = (np.concatenate([srgb(rgb), a[..., None]], -1) * 255 + .5).astype(np.uint8)
    return px


def png(px, path):
    h, w, ch = px.shape
    raw = b"".join(b"\x00" + px[i].tobytes() for i in range(h))
    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    import time
    for th in sys.argv[1:] or ["light", "dark"]:
        t0 = time.time(); px = render(th, 512, 3); png(px, f"out/r-{th}-512.png"); print(th, round(time.time() - t0, 1), "s")


def flat_svg(theme="light", uid="f"):
    """Small-size mark (16-32 px): the 'small' geometry (r 29, pupil 5.2), flat colours, a faint tile edge."""
    T = THEMES[theme]; r = 29.0
    rho = geo.horizon_angle(G.S2_ALT)
    mx, my, _ = geo.project_pts([MUC], G.FP_CAM, G.C, G.C, r)[0]
    c0, c1 = T["pools"][0][0], T["pools"][1][0]
    if theme.startswith("light"):
        a, b, edge = "#ffffff", TW[c1], "#1e1b4b"
        g = f'<linearGradient id="t{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{TW[c0]}"/><stop offset=".45" stop-color="#ffffff"/><stop offset="1" stop-color="{TW[c1]}"/></linearGradient>'
        ea = .14
    else:
        g = f'<linearGradient id="t{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1c1630"/><stop offset=".5" stop-color="{TW[T["base"]]}"/><stop offset="1" stop-color="#0d1c28"/></linearGradient>'
        edge, ea = "#ffffff", .16
    body = (f'<rect width="64" height="64" rx="{G.RT}" fill="url(#t{uid})"/>'
            f'<rect x=".75" y=".75" width="62.5" height="62.5" rx="{G.RT - .75}" fill="none" stroke="{edge}" stroke-opacity="{ea}" stroke-width="1.5"/>')
    if theme == "dark-planet":
        body += G.circle(G.C, G.C, r + .6, TW["sky-100"])
    body += G.circle(G.C, G.C, r, TW[T["globe"]])
    body += f'<path d="{G.cap(MUC[0], MUC[1], rho, G.FP_CAM, r)}" fill="{TW[T["cap"]]}"/>'
    body += G.circle(mx, my, 5.2, TW[T["pupil"]])
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs>{g}</defs>{body}</svg>'
