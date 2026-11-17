import math, json, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
r = math.pi / 180
def unit(lon, lat):
    return np.array([math.cos(lat*r)*math.cos(lon*r), math.cos(lat*r)*math.sin(lon*r), math.sin(lat*r)])
def sun(ts):
    d = ts/86400.0 - 10957.5            # days since J2000
    g = (357.529 + 0.98560028*d) % 360; q = (280.459 + 0.98564736*d) % 360
    L = q + 1.915*math.sin(g*r) + 0.020*math.sin(2*g*r)
    e = 23.439 - 0.00000036*d
    ra = math.atan2(math.cos(e*r)*math.sin(L*r), math.cos(L*r))/r
    dec = math.asin(math.sin(e*r)*math.sin(L*r))/r
    eot = (q - ra + 180) % 360 - 180      # degrees
    ut = (ts % 86400)/3600.0
    lon = -(ut - 12)*15 - eot
    return (lon + 180) % 360 - 180, dec
class Cam:
    """Pinhole camera. pos: lon, lat, altitude in Earth radii. look: lon, lat on the ground. F: focal length in px, (cx, cy) principal point, all in design px."""
    def __init__(s, lon, lat, alt, tlon, tlat, F, cx, cy):
        s.C = unit(lon, lat)*(1+alt); T = unit(tlon, tlat)
        f = T - s.C; f /= np.linalg.norm(f)
        up = s.C/np.linalg.norm(s.C)
        if abs(np.dot(up, f)) > 0.999: up = np.array([0, 0, 1.0])
        s.rt = np.cross(f, up); s.rt /= np.linalg.norm(s.rt); s.up = np.cross(s.rt, f); s.f = f
        s.F, s.cx, s.cy, s.alt, s.pos = F, cx, cy, alt, (lon, lat)
    def proj(s, lon, lat):
        P = unit(lon, lat); v = P - s.C; z = float(v @ s.f)
        vis = z > 0 and float(P @ (s.C - P)) > 0.02
        if z <= 1e-6: return 0, 0, False
        return s.cx + s.F*float(v @ s.rt)/z, s.cy - s.F*float(v @ s.up)/z, vis
    def rays(s, x0, y0, w, h, K):
        yy, xx = np.mgrid[0:h*K, 0:w*K].astype(np.float32)
        X = (xx/K + x0 - s.cx)/s.F; Y = -(yy/K + y0 - s.cy)/s.F
        d = s.f[None, None, :] + X[..., None]*s.rt[None, None, :] + Y[..., None]*s.up[None, None, :]
        d /= np.linalg.norm(d, axis=2, keepdims=True)
        b = d @ s.C; c = float(s.C @ s.C) - 1
        disc = b*b - c
        hit = (disc > 0) & (b < 0)
        t = -b - np.sqrt(np.clip(disc, 0, None))
        P = s.C[None, None, :] + d*t[..., None]
        miss = np.sqrt(np.clip(c + 1 - b*b, 0, None))   # closest approach of the ray to the centre
        return P, hit, miss, d
TEX = {}
def tex(name):
    if name not in TEX: TEX[name] = np.asarray(Image.open(name).convert('RGB'), dtype=np.float32)
    return TEX[name]
def sample(t, lon, lat, w=-180, e=180, s=-90, n=90):
    H, W = t.shape[:2]
    u = np.clip((lon - w)/(e - w)*(W-1), 0, W-1.001); v = np.clip((n - lat)/(n - s)*(H-1), 0, H-1.001)
    u0 = u.astype(int); v0 = v.astype(int); fu = (u-u0)[..., None]; fv = (v-v0)[..., None]
    return (t[v0, u0]*(1-fu) + t[v0, u0+1]*fu)*(1-fv) + (t[v0+1, u0]*(1-fu) + t[v0+1, u0+1]*fu)*fv
def render(cam, x0, y0, w, h, K=1.5, night=None, dim=0.66, hires=True):
    P, hit, miss, d = cam.rays(x0, y0, w, h, K)
    lat = np.arcsin(np.clip(P[..., 2], -1, 1))/r; lon = np.arctan2(P[..., 1], P[..., 0])/r
    img = sample(tex('bm8.jpg'), lon, lat)
    if hires:
        m = (lon > -14.5) & (lon < 74.5) & (lat > 20.5) & (lat < 64.5)
        if m.any():
            hi = sample(tex('bm_eu.jpg'), lon, lat, -15, 75, 20, 65)
            img = np.where(m[..., None], hi, img)
    inc = np.clip(-(np.sum(P*d, axis=2)), 0, 1)              # cosine between the view ray and the ground normal
    if night is not None:
        s = unit(*night); alt = np.arcsin(np.clip(P @ s, -1, 1))/r
        day = np.clip((alt + 12)/12, 0, 1); day = day*day*(3 - 2*day)
        li = sample(tex('lights.jpg'), lon, lat)
        img = img*(0.05 + 0.95*day[..., None]) + li*(1 - day[..., None])*np.array([1.0, 0.86, 0.62])*1.15
    img = img*dim*(0.45 + 0.55*inc[..., None]) + (1 - inc[..., None])**3*np.array([40, 80, 130.])*0.5
    glow = np.exp(-np.clip(miss - 1, 0, None)/0.012)*(~hit)
    out = np.where(hit[..., None], img, 3.0 + glow[..., None]*np.array([70, 130, 190.])*0.85)
    return np.clip(out, 0, 255).astype(np.uint8)
