"""Sample palettes from real images (k-means in CIELAB) and convert FED-STD-595C chips (XYZ, illuminant C/D65) to sRGB."""
import json, numpy as np
from PIL import Image

def srgb_to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)

def xyz_to_hex(X, Y, Z):
    xyz = np.array([X, Y, Z]) / 100
    M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    lin = np.clip(M @ xyz, 0, 1)
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in c)

def kmeans(rgb, k, seed=1, it=40):
    lab = srgb_to_lab(rgb.astype(float))
    rng = np.random.default_rng(seed)
    cen = lab[rng.choice(len(lab), k, replace=False)]
    for _ in range(it):
        d = ((lab[:, None, :] - cen[None]) ** 2).sum(2)
        lab_i = d.argmin(1)
        cen = np.array([lab[lab_i == j].mean(0) if (lab_i == j).any() else cen[j] for j in range(k)])
    out = []
    for j in range(k):
        m = lab_i == j
        med = np.median(rgb[m], 0)              # median pixel of the cluster: a colour that occurs in the image
        out.append(dict(hex="#" + "".join(f"{int(v):02X}" for v in med), share=round(m.mean() * 100, 1), L=round(cen[j][0], 1)))
    return sorted(out, key=lambda c: c["L"])

res = {}
im = np.asarray(Image.open("img/s2_0926.jpg").convert("RGB")).reshape(-1, 3)
land = im[im.max(1) > 10]                          # drop the no-data wedge
res["sentinel2_munich"] = kmeans(land, 7)
# the two lakes: pixels in the lake boxes of the thumbnail (Ammersee ~x170-190,y225-275; Starnberger See ~x215-240,y250-310)
full = np.asarray(Image.open("img/s2_0926.jpg").convert("RGB"))
lake = np.concatenate([full[228:272, 174:186].reshape(-1, 3), full[258:305, 222:234].reshape(-1, 3)])
dark = lake[srgb_to_lab(lake.astype(float))[:, 0] < 30]
res["sentinel2_lakes"] = "#" + "".join(f"{int(v):02X}" for v in np.median(dark, 0))
e = np.asarray(Image.open("img/epic_1101.jpg").convert("RGB")).reshape(-1, 3)
disc = e[e.max(1) > 28]
res["epic"] = kmeans(disc, 7)
res["epic_space"] = "#" + "".join(f"{int(v):02X}" for v in np.median(e[e.max(1) <= 6], 0))
g = np.asarray(Image.open("img/corona.jpg").convert("RGB")).reshape(-1, 3)
res["corona"] = kmeans(g, 5)
chips = {}
for line in open("fs595c.txt"):
    p = line.split()
    if p and p[0].isdigit() and p[0] in {"36118", "36176", "36320", "36375", "36495", "37038", "35237", "26270", "36440", "36622", "26373"}:
        X, Y, Z = (float(v) for v in p[1].split(":")[1].split("/"))
        chips[p[0]] = dict(hex=xyz_to_hex(X, Y, Z), name=" ".join(p[4:]) or "", Y=Y)
res["fs595"] = chips
json.dump(res, open("palettes.json", "w"), indent=1)
for k, v in res.items():
    print(k, v if isinstance(v, str) else (json.dumps(v)[:600]))
