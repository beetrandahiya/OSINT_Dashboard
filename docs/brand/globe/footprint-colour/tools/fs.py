"""FED-STD-595C chips: XYZ (illuminant C) -> Bradford adaptation to D65 -> sRGB."""
import numpy as np, json
B = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
wC, w65 = np.array([0.98074, 1.0, 1.18232]), np.array([0.95047, 1.0, 1.08883])
A = np.linalg.inv(B) @ np.diag((B @ w65) / (B @ wC)) @ B
M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
def hexof(X, Y, Z):
    lin = np.clip(M @ (A @ (np.array([X, Y, Z]) / 100)), 0, 1)
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in c)
out = {}
for line in open("fs595c.txt"):
    p = line.split()
    if p and p[0].isdigit() and p[0] in {"36118", "36176", "36320", "36375", "36495", "37038", "35237", "26270", "36440", "26373", "36622", "36081", "36231", "36251", "36270"}:
        X, Y, Z = (float(v) for v in p[1].split(":")[1].split("/"))
        out[p[0]] = dict(hex=hexof(X, Y, Z), name=" ".join(p[4:]), Y=Y)
for k, v in sorted(out.items()): print(k, v)
d = json.load(open("palettes.json")); d["fs595"] = out; json.dump(d, open("palettes.json", "w"), indent=1)
