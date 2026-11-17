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
if __name__ == '__main__':
    for name in (sys.argv[1:] or V):
        v = V[name]; K = 1.5
        out = np.full((int(H*K), int(W*K), 3), 3, dtype=np.uint8)
        for cam, x, y, w, h in v['cams']:
            out[int(y*K):int(y*K)+int(h*K), int(x*K):int(x*K)+int(w*K)] = render(cam, x, y, w, h, K, night=v.get('night'))[:int(h*K), :int(w*K)]
        Image.fromarray(out).save(f'out_{name}.jpg', quality=84); Image.fromarray(out).resize((960, 540)).save(f't/{name}.jpg', quality=70); print(name)
