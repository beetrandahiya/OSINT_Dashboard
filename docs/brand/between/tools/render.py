"""Globe renders for the 'between' directions: real photo Earth (God's eye), ink Earth (the icon at full size) and
silver Earth (the photo without colour), on black space, porcelain or night backdrops. Uses the pinhole camera and
NASA textures of the God's eye boards (gv/cam.py: Blue Marble Next Generation, Black Marble lights)."""
import sys, math, json, numpy as np
from PIL import Image, ImageDraw
GV = "/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/gv"
sys.path.insert(0, GV)
import os; os.chdir(GV)
import cam as C
from cam import Cam, sample, tex, unit, r

HEX = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
W, H = 1920, 1080
# Theatre camera of the God's eye boards, principal point moved left so Ukraine sits in the area free of the column
THEATRE = lambda w=W, h=H, cx=700, cy=430, F=1500: Cam(19, 35, 0.42, 34, 49, F, cx, cy)

_ink = {}


def ink_tex(land, ocean, coast, border):
    key = (land, ocean, coast, border)
    if key in _ink: return _ink[key]
    G = json.load(open("/home/user/OSINT_Dashboard/data/countries-geo.json"))["countries"]
    Wt, Ht = 8192, 4096
    im = Image.new("RGB", (Wt, Ht), tuple(int(v) for v in HEX(ocean))); d = ImageDraw.Draw(im)
    px = lambda lo, la: ((lo + 180) / 360 * Wt, (90 - la) / 180 * Ht)
    for c in G:
        rings = json.loads(c["rings"]) if isinstance(c["rings"], str) else c["rings"]
        for ring in rings:
            if len(ring) > 2: d.polygon([px(lo, la) for lo, la in ring], fill=tuple(int(v) for v in HEX(land)))
    for c in G:
        rings = json.loads(c["rings"]) if isinstance(c["rings"], str) else c["rings"]
        for ring in rings:
            pts = [px(lo, la) for lo, la in ring + ring[:1]]; seg = [pts[0]]
            for p, q in zip(pts, pts[1:]):
                if abs(p[0] - q[0]) > Wt / 2:
                    if len(seg) > 1: d.line(seg, fill=tuple(int(v) for v in HEX(border)), width=3)
                    seg = [q]
                else: seg.append(q)
            if len(seg) > 1: d.line(seg, fill=tuple(int(v) for v in HEX(border)), width=3)
    _ink[key] = np.asarray(im, dtype=np.float32)
    return _ink[key]


def landmask(lon, lat):
    t = ink_tex("#26262b", "#050507", "#52525b", "#3f3f46")
    return sample(t[..., :1], lon, lat) > 20


def backdrop(kind, w, h, K):
    yy, xx = np.mgrid[0:int(h * K), 0:int(w * K)].astype(np.float32)
    u, v = xx / (w * K), yy / (h * K)
    if kind == "space": return np.full((int(h * K), int(w * K), 3), 3.0, np.float32), HEX("#7dd3fc") * .55
    if kind == "porcelain":
        base = np.full(u.shape + (3,), 255.0, np.float32)
        a = (np.clip(1 - np.hypot(u - .08, v - .02) / .9, 0, 1) ** 1.6 * .8)[..., None]
        b = (np.clip(1 - np.hypot(u - .98, v - 1.0) / .9, 0, 1) ** 1.6 * .85)[..., None]
        base = base * (1 - a) + HEX("#ede9fe") * a; base = base * (1 - b) + HEX("#e0f2fe") * b
        return base, HEX("#bae6fd") * 1.0
    if kind == "night":
        base = np.broadcast_to(HEX("#09090b"), u.shape + (3,)).copy()
        a = (np.clip(1 - np.hypot(u - .08, v - .02) / .9, 0, 1) ** 1.6 * .45)[..., None]
        b = (np.clip(1 - np.hypot(u - .98, v - 1.0) / .9, 0, 1) ** 1.6 * .5)[..., None]
        base = base * (1 - a) + HEX("#2e1065") * a; base = base * (1 - b) + HEX("#082f49") * b
        return base, HEX("#7dd3fc") * .6


def render(cam, ground, back, w=W, h=H, K=1.25, sun=None):
    P, hit, miss, d = cam.rays(0, 0, w, h, K)
    lat = np.arcsin(np.clip(P[..., 2], -1, 1)) / r; lon = np.arctan2(P[..., 1], P[..., 0]) / r
    inc = np.clip(-(np.sum(P * d, axis=2)), 0, 1)
    eu = (lon > -14.5) & (lon < 74.5) & (lat > 20.5) & (lat < 64.5)
    def photo():
        img = sample(tex("bm8.jpg"), lon, lat)
        if eu.any(): img = np.where(eu[..., None], sample(tex("bm_eu.jpg"), lon, lat, -15, 75, 20, 65), img)
        return img
    if ground == "photo":
        img = photo() * .66 * (.45 + .55 * inc[..., None])
        img = img + (1 - inc[..., None]) ** 3 * np.array([40, 80, 130.]) * .5
    elif ground == "ink":
        t = ink_tex("#26262b", "#050507", "#52525b", "#3f3f46")
        img = sample(t, lon, lat)
        land = landmask(lon, lat)
        hs = sample(tex("relief.jpg"), lon, lat)[..., :1] / 255
        img = np.where(land, img * (.78 + .5 * np.clip(hs - .25, 0, .6)), img)
        img = img * (.62 + .38 * inc[..., None])
        img = img + (1 - inc[..., None]) ** 3 * HEX("#7dd3fc") * .22
    elif ground == "silver-light":
        lum = (photo() @ np.array([.3, .59, .11]))[..., None] / 255
        land = landmask(lon, lat)
        landc = 252 - (1 - np.clip(lum * 1.9, 0, 1)) * 70
        img = np.where(land, landc * np.array([.985, .99, 1.0]), HEX("#e2e8f0") * (0.98 + .02 * lum))
        img = img * (.9 + .1 * inc[..., None])
    elif ground == "silver-dark":
        lum = (photo() @ np.array([.3, .59, .11]))[..., None] / 255
        img = (lum ** 1.1) * np.array([170, 176, 186.]) * (.5 + .5 * inc[..., None]) + np.array([6, 7, 9.])
        img = img + (1 - inc[..., None]) ** 3 * HEX("#7dd3fc") * .18
    bg, glowc = backdrop(back, w, h, K)
    glow = (np.exp(-np.clip(miss - 1, 0, None) / .014) * (~hit))[..., None]
    out = np.where(hit[..., None], img, bg * (1 - glow * .9) + glowc * glow * .9)
    return np.clip(out, 0, 255).astype(np.uint8)


def save(arr, path, w=W, h=H):
    im = Image.fromarray(arr).resize((w, h), Image.LANCZOS)
    im.save(path, "WEBP", quality=86, method=6)


if __name__ == "__main__":
    import time
    for ground, back, name in [("photo", "space", "A"), ("ink", "porcelain", "B-l"), ("ink", "night", "B-d"),
                               ("silver-light", "porcelain", "C-l"), ("silver-dark", "night", "C-d")]:
        t0 = time.time(); a = render(THEATRE(), ground, back)
        save(a, f"/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between/out/g-{name}.webp")
        print(name, round(time.time() - t0, 1))
