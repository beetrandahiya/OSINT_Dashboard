"""Maxar's Open Data programme: sharp satellite pictures (about 0.3-0.5 m) released free for major disasters
(CC BY-NC 4.0), published as a STAC catalogue of Cloud-Optimised GeoTIFFs on AWS.

There are no map tiles, only large GeoTIFF files (about 17,000 x 17,000 pixels each, in UTM). We do not decode
images: each file is cut into 512-pixel JPEG pieces inside, so we read the file's directory with one range
request, and serve any piece by fetching just its bytes and putting the file's shared JPEG tables in front.
The browser shows each piece at its four corners. No new dependency.
"""
import math
import re
import struct
import time

BASE = "https://maxar-opendata.s3.amazonaws.com/events/"
ALLOWED = re.compile(r"^https://maxar-opendata\.s3\.amazonaws\.com/events/[\w./-]+\.tif$")


# ---------- UTM to longitude/latitude (WGS 84, standard series) ----------
def utm_to_ll(x: float, y: float, zone: int, north: bool) -> tuple[float, float]:
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    x -= 500000.0
    if not north:
        y -= 10000000.0
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
         + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    c1, t1 = ep2 * math.cos(p) ** 2, math.tan(p) ** 2
    n1 = a / math.sqrt(1 - e2 * math.sin(p) ** 2)
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p) ** 2) ** 1.5
    d = x / (n1 * k0)
    lat = p - (n1 * math.tan(p) / r1) * (d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
                                         + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p)
    return math.degrees(lon) + (zone - 1) * 6 - 180 + 3, math.degrees(lat)


# ---------- reading a (Big)TIFF directory ----------
_SZ = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 11: 4, 12: 8, 16: 8, 17: 8}
_FMT = {1: "B", 2: "c", 3: "H", 4: "I", 7: "B", 12: "d", 16: "Q"}


def parse_tiff(head: bytes) -> dict:
    """The image levels (full size and overviews) of a COG: size, tile layout, piece offsets and byte counts, JPEG
    tables, and the georeference. Needs the first bytes of the file (GDAL COGs keep all directories at the start)."""
    bo = "<" if head[:2] == b"II" else ">"
    big = struct.unpack(bo + "H", head[2:4])[0] == 43
    off = struct.unpack(bo + ("Q" if big else "I"), head[8:16] if big else head[4:8])[0]

    def values(typ, count, raw_or_off):
        n = _SZ.get(typ, 1) * count
        if n <= (8 if big else 4):
            data = raw_or_off[:n]
        else:
            o = struct.unpack(bo + ("Q" if big else "I"), raw_or_off)[0]
            if o + n > len(head):
                raise ValueError("directory reaches beyond the bytes read")
            data = head[o:o + n]
        if typ == 2:
            return data.decode("latin-1")
        if typ in (5, 10):
            return [struct.unpack(bo + "II", data[i:i + 8]) for i in range(0, n, 8)]
        return list(struct.unpack(bo + _FMT.get(typ, "B") * count, data))

    levels, geo = [], {}
    while off and off < len(head):
        if big:
            cnt = struct.unpack(bo + "Q", head[off:off + 8])[0]
            ent, step, start = 20, 12, off + 8
        else:
            cnt = struct.unpack(bo + "H", head[off:off + 2])[0]
            ent, step, start = 12, 8, off + 2
        tags = {}
        for i in range(cnt):
            e = head[start + ent * i: start + ent * (i + 1)]
            tag, typ = struct.unpack(bo + "HH", e[:4])
            count = struct.unpack(bo + ("Q" if big else "I"), e[4:step])[0]
            if tag in (256, 257, 254, 259, 277, 322, 323, 324, 325, 347, 33550, 33922, 34735):
                tags[tag] = values(typ, count, e[step:])
        nxt = start + ent * cnt
        off = struct.unpack(bo + ("Q" if big else "I"), head[nxt:nxt + (8 if big else 4)])[0]
        if 33550 in tags:
            geo = {"scale": tags[33550], "tie": tags[33922], "keys": tags.get(34735, [])}
        is_mask = tags.get(254, [0])[0] & 4
        if is_mask or tags.get(259, [0])[0] != 7:                  # JPEG pieces only; the transparency mask is skipped
            continue
        levels.append({"w": tags[256][0], "h": tags[257][0], "tw": tags[322][0], "th": tags[323][0],
                       "offsets": tags[324], "counts": tags[325], "tables": bytes(tags[347]) if 347 in tags else b""})
    if not levels or not geo:
        raise ValueError("not a georeferenced JPEG GeoTIFF")
    keys = geo["keys"]
    epsg = None
    for i in range(4, len(keys), 4):
        if keys[i] in (3072, 2048):                                # ProjectedCSTypeGeoKey / GeographicTypeGeoKey
            epsg = keys[i + 3]
    sx, sy = geo["scale"][0], geo["scale"][1]
    x0, y0 = geo["tie"][3], geo["tie"][4]
    full = levels[0]

    def ll(col, row):
        x, y = x0 + col * sx, y0 - row * sy
        if epsg and 32601 <= epsg <= 32660:
            return utm_to_ll(x, y, epsg - 32600, True)
        if epsg and 32701 <= epsg <= 32760:
            return utm_to_ll(x, y, epsg - 32700, False)
        if epsg == 4326:
            return x, y
        raise ValueError(f"unsupported projection EPSG:{epsg}")
    corners = [ll(0, 0), ll(full["w"], 0), ll(full["w"], full["h"]), ll(0, full["h"])]   # NW, NE, SE, SW
    return {"levels": levels, "corners": [[round(a, 7), round(b, 7)] for a, b in corners], "epsg": epsg, "res_m": round(sx, 3)}


def public(meta: dict) -> dict:
    return {"corners": meta["corners"], "res_m": meta["res_m"], "epsg": meta["epsg"],
            "levels": [{"w": l["w"], "h": l["h"], "tw": l["tw"], "th": l["th"]} for l in meta["levels"]]}


def piece(meta: dict, level: int, x: int, y: int) -> tuple[int, int, bytes]:
    lv = meta["levels"][level]
    across = math.ceil(lv["w"] / lv["tw"])
    i = y * across + x
    return lv["offsets"][i], lv["counts"][i], lv["tables"]


def jpeg(tables: bytes, data: bytes) -> bytes:
    """A TIFF JPEG piece plus the file's shared tables -> a complete JPEG file."""
    if tables[:2] == b"\xff\xd8" and data[:2] == b"\xff\xd8":
        return b"\xff\xd8" + tables[2:-2] + data[2:]
    return data


def quiet_title(event_id: str) -> str:
    t = re.sub(r"[-_]+", " ", event_id)
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t).strip()
