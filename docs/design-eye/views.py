import sys, json, math, numpy as np
from PIL import Image
from cam import *
CAP = 1794909671
SUN = sun(CAP); print('subsolar', SUN)
GEO = 35786/6371
def geo_cam(lon, lat, R, cx, cy): return Cam(lon, lat, GEO, lon, lat, R/math.tan(math.asin(1/(1+GEO))), cx, cy)
V = {}
W, H = 1920, 1080
V['whole'] = dict(cams=[(geo_cam(42, 25, 440, 920, 522), 0, 0, W, H)])
V['horizon'] = dict(cams=[(Cam(40, 14, 0.9, 42, 44, 1500, 960, 500), 0, 0, W, H)])
V['theatre'] = dict(cams=[(Cam(19, 35, 0.42, 34, 49, 1500, 960, 420), 0, 0, W, H)])
V['dusk'] = dict(cams=[(geo_cam(112, 22, 440, 1180, 522), 0, 0, W, H)], night=SUN)
V['sides'] = dict(cams=[(geo_cam(-100, 20, 372, 492, 470), 0, 0, 960, H), (geo_cam(75, 20, 372, 1428, 470), 960, 0, 960, H)])
def near(lon, lat, alt, F, x, y, w, h): return (Cam(lon, lat, alt, lon, lat, F, x + w/2, y + h/2), x, y, w, h)
TW, TH = 700, 440
V['wall'] = dict(cams=[near(16, 50, 0.55, 800, 24, 76, TW, TH), near(46, 29, 0.55, 800, 736, 76, TW, TH), near(118, 28, 0.75, 800, 24, 528, TW, TH), near(-96, 37, 0.75, 800, 736, 528, TW, TH)])
V['front'] = dict(cams=[(Cam(35.2, 48.3, 0.16, 35.2, 48.3, 2000, 720, 540), 0, 0, W, H)])
V['polar'] = dict(cams=[(Cam(30, 74, 2.4, 30, 74, 470/math.tan(math.asin(1/3.4)), 960, 530), 0, 0, W, H)])
V['low'] = dict(cams=[(Cam(27, 33.5, 0.066, 44, 34, 1250, 960, 360), 0, 0, W, H)])
def dest(lon, lat, brg, dkm):
    d = dkm/6371; p1 = lat*r; l1 = lon*r; b = brg*r
    p2 = math.asin(math.sin(p1)*math.cos(d) + math.cos(p1)*math.sin(d)*math.cos(b))
    return (l1 + math.atan2(math.sin(b)*math.sin(d)*math.cos(p1), math.cos(d) - math.sin(p1)*math.sin(p2)))/r, p2/r
AC = dict(lon=35.54, lat=39.30, hdg=110, alt_km=41025*0.3048/1000)
_b = dest(AC['lon'], AC['lat'], 290, 520); _a = dest(AC['lon'], AC['lat'], 110, 250)
V['chase'] = dict(cams=[(Cam(_b[0], _b[1], 260/6371, _a[0], _a[1], 1500, 760, 470), 0, 0, W, H)])
V['whole_lights'] = dict(cams=V['whole']['cams'], ground='lights')
V['theatre_outline'] = dict(cams=V['theatre']['cams'], ground='outline')
V['horizon_mono'] = dict(cams=V['horizon']['cams'], ground='mono')
GT = [(24 + (i % 3)*632, 84 + (i//3)*452, 620, 440) for i in range(6)]
GN = ['photo', 'mono', 'lights', 'outline', 'dots', 'relief']
V['grounds'] = dict(cams=[(geo_cam(42, 25, 196, x + 310, y + 222), x, y, w, h) for x, y, w, h in GT], grounds=GN)
if __name__ == '__main__':
    for name in sys.argv[1:]:
        v = V[name]; K = 1.5
        out = np.full((int(H*K), int(W*K), 3), 3, dtype=np.uint8)
        for n, (cam, x, y, w, h) in enumerate(v['cams']):
            g = v['grounds'][n] if 'grounds' in v else v.get('ground', 'photo')
            out[int(y*K):int(y*K)+int(h*K), int(x*K):int(x*K)+int(w*K)] = render(cam, x, y, w, h, K, night=v.get('night'), ground=g)[:int(h*K), :int(w*K)]
        Image.fromarray(out).save(f'out_{name}.jpg', quality=84); Image.fromarray(out).resize((960, 540)).save(f't/{name}.jpg', quality=72); print(name)
