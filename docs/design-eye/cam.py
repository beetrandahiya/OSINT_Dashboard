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
    def __init__(s, lon, lat, alt, tlon, tlat, F, cx, cy, talt=0.0):
        s.C = unit(lon, lat)*(1+alt); T = unit(tlon, tlat)*(1+talt)
        f = T - s.C; f /= np.linalg.norm(f)
        up = s.C/np.linalg.norm(s.C)
        if abs(np.dot(up, f)) > 0.999: up = np.array([0, 0, 1.0])
        s.rt = np.cross(f, up); s.rt /= np.linalg.norm(s.rt); s.up = np.cross(s.rt, f); s.f = f
        s.F, s.cx, s.cy, s.alt, s.pos = F, cx, cy, alt, (lon, lat)
    def proj(s, lon, lat, h=0.0):
        P = unit(lon, lat); v = P*(1+h) - s.C; z = float(v @ s.f)
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
def outline_tex():
    import json
    from PIL import ImageDraw
    if 'outline' in TEX: return TEX['outline']
    G = json.load(open('/home/user/OSINT_Dashboard/data/countries-geo.json'))['countries']
    W, H = 8192, 4096
    im = Image.new('RGB', (W, H), (5, 11, 20)); d = ImageDraw.Draw(im)
    for lon in range(-180, 180, 15): d.line([((lon+180)/360*W, 0), ((lon+180)/360*W, H)], fill=(12, 26, 42), width=2)
    for lat in range(-75, 90, 15): d.line([(0, (90-lat)/180*H), (W, (90-lat)/180*H)], fill=(12, 26, 42), width=2)
    for c in G:
        for ring in c['rings']:
            if len(ring) > 2: d.polygon([((lo+180)/360*W, (90-la)/180*H) for lo, la in ring], fill=(13, 30, 46))
    for c in G:
        for ring in c['rings']:
            pts = [((lo+180)/360*W, (90-la)/180*H) for lo, la in ring + ring[:1]]
            seg = [pts[0]]
            for p, q in zip(pts, pts[1:]):
                if abs(p[0]-q[0]) > W/2: 
                    if len(seg) > 1: d.line(seg, fill=(92, 164, 206), width=2)
                    seg = [q]
                else: seg.append(q)
            if len(seg) > 1: d.line(seg, fill=(92, 164, 206), width=2)
    TEX['outline'] = np.asarray(im, dtype=np.float32); TEX['landmask'] = np.asarray(im, dtype=np.float32)[..., 1] > 20
    return TEX['outline']
def render(cam, x0, y0, w, h, K=1.5, night=None, dim=0.66, hires=True, ground='photo'):
    P, hit, miss, d = cam.rays(x0, y0, w, h, K)
    lat = np.arcsin(np.clip(P[..., 2], -1, 1))/r; lon = np.arctan2(P[..., 1], P[..., 0])/r
    inc = np.clip(-(np.sum(P*d, axis=2)), 0, 1)
    shade = (0.45 + 0.55*inc[..., None])
    if ground == 'photo':
        img = sample(tex('bm8.jpg'), lon, lat)
        if hires:
            m = (lon > -14.5) & (lon < 74.5) & (lat > 20.5) & (lat < 64.5)
            if m.any(): img = np.where(m[..., None], sample(tex('bm_eu.jpg'), lon, lat, -15, 75, 20, 65), img)
        if night is not None:
            s = unit(*night); alt = np.arcsin(np.clip(P @ s, -1, 1))/r
            day = np.clip((alt + 12)/12, 0, 1); day = day*day*(3 - 2*day)
            li = sample(tex('lights.jpg'), lon, lat)
            img = img*(0.05 + 0.95*day[..., None]) + li*(1 - day[..., None])*np.array([0.85, 0.93, 1.0])*1.2
        img = img*dim*shade
    elif ground == 'mono':
        img = sample(tex('bm8.jpg'), lon, lat)
        m = (lon > -14.5) & (lon < 74.5) & (lat > 20.5) & (lat < 64.5)
        if m.any(): img = np.where(m[..., None], sample(tex('bm_eu.jpg'), lon, lat, -15, 75, 20, 65), img)
        lum = (img @ np.array([0.3, 0.59, 0.11]))[..., None]
        img = (lum**1.15)*np.array([0.50, 0.62, 0.78])*0.42*shade + np.array([2, 5, 10.])
    elif ground == 'lights':
        li = sample(tex('lights.jpg'), lon, lat); lum = (sample(tex('bm8.jpg'), lon, lat) @ np.array([0.3, 0.59, 0.11]))[..., None]
        img = (li*np.array([0.82, 0.93, 1.0])*1.35 + lum*np.array([0.35, 0.5, 0.75])*0.10 + np.array([2, 4, 9.]))*(0.6 + 0.4*inc[..., None])
    elif ground == 'relief':
        t = tex('relief.jpg'); lum = sample(t, lon, lat)[..., :1]
        outline_tex(); land = sample(TEX['landmask'].astype(np.float32)[..., None], lon, lat) > 0.5
        img = np.where(land, np.clip((lum/255.0 - 0.22)/0.5, 0, 1)**1.3*np.array([150, 190, 225.])*0.8 + np.array([6, 11, 18.]), np.array([4, 9, 18.]))*shade
    elif ground in ('outline', 'dots'):
        img = sample(outline_tex(), lon, lat)*(0.55 + 0.45*inc[..., None]) if ground == 'outline' else np.broadcast_to(np.array([3, 8, 17.]), P.shape)*(0.5 + 0.5*inc[..., None])
    img = img + (1 - inc[..., None])**3*np.array([40, 80, 130.])*0.5
    glow = np.exp(-np.clip(miss - 1, 0, None)/0.012)*(~hit)
    out = np.where(hit[..., None], img, 3.0 + glow[..., None]*np.array([70, 130, 190.])*0.85)
    out = np.clip(out, 0, 255).astype(np.uint8)
    if ground == 'dots':
        from PIL import ImageDraw
        outline_tex(); lm = TEX['landmask']
        im = Image.fromarray(out); dd = ImageDraw.Draw(im); step = max(0.6, 0.6*440/max(1.0, cam.F*math.tan(math.asin(min(1.0, 1/float(np.linalg.norm(cam.C)))))))
        la = np.arange(-89, 89.5, step)
        for lt in la:
            n = max(1, int(360/step*math.cos(lt*r))); lo = -180 + 360*np.arange(n)/n
            Pp = np.stack([np.cos(lt*r)*np.cos(lo*r), np.cos(lt*r)*np.sin(lo*r), np.full(n, math.sin(lt*r))], 1)
            v = Pp - cam.C; z = v @ cam.f; vis = (z > 0) & (np.sum(Pp*(cam.C - Pp), 1) > 0.02)
            xs = (cam.cx + cam.F*(v @ cam.rt)/z - x0)*K; ys = (cam.cy - cam.F*(v @ cam.up)/z - y0)*K
            land = lm[np.clip(((90-lt)/180*4096), 0, 4095).astype(int), np.clip((lo+180)/360*8192, 0, 8191).astype(int)]
            for x, y, ok, l in zip(xs, ys, vis, land):
                if ok and 0 <= x < w*K and 0 <= y < h*K:
                    if l: dd.ellipse([x-1.2, y-1.2, x+1.2, y+1.2], fill=(96, 176, 228))
                    else: dd.point([x, y], fill=(22, 50, 88))
        out = np.asarray(im)
    return out
