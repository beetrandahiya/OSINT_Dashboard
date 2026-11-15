"""The front line in Ukraine, from DeepState (deepstatemap.live), a Ukrainian OSINT team that maps the war daily
from geolocated footage and official statements. It is one side's open-source assessment, published with a delay
of hours to a day; the card says so.

What we keep from their map file, by the tag each feature carries ("geoJSON.status.occupied" and so on):
- areas: occupied, unknown status (contested), Crimea, the "CADR and CALR" (occupied parts of Donetsk and Luhansk
  since 2014), Tuzla Island, plus the other Russian-held territories they draw (Transnistria, Abkhazia, Tskhinvali).
  Their file also contains political statements drawn as polygons ("East Prussia temporarily occupied", Karelia,
  the Kurils...): those are left out. Liberated areas (2022) are left out too.
- points: Russian unit positions (their "enemy" markers, named), attack directions, airfields and headquarters with
  their notes.
- the change log: every update's English note with the map links in it ("The enemy advanced near Rusyn Yar"),
  placed at the link's coordinates.
The occupied area is summed on a sphere and compared with the update nearest to seven days earlier.
"""
import html
import math
import re
from datetime import datetime

BASE = "https://deepstatemap.live/api/history/"
KEEP_AREAS = {"status.occupied": "occupied", "status.unknown": "contested", "territories.crimea": "occupied",
              "territories.ordlo": "occupied", "territories.tuzla": "occupied", "territories.transnistria": "held",
              "territories.abkhazia": "held", "territories.tskhinvali-district": "held"}
POINT_KINDS = {"enemy": "unit", "arrow": "attack", "airport": "airfield", "headquarter": "hq"}
R = 6371.0088


def _tag(name: str) -> str:
    m = re.search(r"geoJSON\.([\w.-]+)", name or "")
    return m.group(1) if m else ""


def _english(s: str) -> str:
    """Their texts are "Ukrainian /// English /// key"; take the English part."""
    s = html.unescape(re.sub(r"<br\s*/?>", "\n", s or "")).replace(" ", " ")
    parts = [p.strip() for p in s.split("///")]
    eng = parts[1] if len(parts) >= 2 else parts[0]
    eng = re.sub(r"\{icon=[^}]*\}|geoJSON\.[\w.#-]+", "", eng)
    return re.sub(r"<[^>]+>", "", re.sub(r"\s+", " ", eng)).strip(" .")


def ring_area(ring) -> float:
    """Area of a lon/lat ring on a sphere, km² (the standard line-integral formula)."""
    a = 0.0
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:] + ring[:1]):
        a += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(a) * R * R / 2


def parse(geo: dict) -> dict:
    areas, points = [], []
    occupied_km2 = 0.0
    for f in geo.get("features", []):
        p, g = f.get("properties", {}), f.get("geometry") or {}
        tag = _tag(p.get("name", ""))
        if g.get("type") == "Polygon":
            kind = KEEP_AREAS.get(tag)
            if not kind:
                continue
            rings = [[[round(x, 4), round(y, 4)] for x, y, *_ in r] for r in g["coordinates"]]
            if kind == "occupied" and tag != "territories.tuzla":
                occupied_km2 += ring_area(rings[0]) - sum(ring_area(r) for r in rings[1:])
            areas.append({"kind": kind, "name": _english(p.get("name")), "tag": tag, "rings": rings})
        elif g.get("type") == "Point":
            icon = re.search(r"\{icon=([a-z]+)", p.get("description") or "")
            kind = POINT_KINDS.get(icon.group(1)) if icon else None
            if not kind:
                continue
            lon, lat = g["coordinates"][:2]
            note = _english(p.get("description")) if kind in ("airfield", "hq", "unit") else ""
            points.append({"kind": kind, "name": _english(p.get("name")) if kind != "attack" else "Direction of attack",
                           "note": note[:600] or None, "lon": round(lon, 5), "lat": round(lat, 5)})
    return {"areas": areas, "points": points, "occupied_km2": round(occupied_km2)}


def changes(history: list[dict], since: float) -> list[dict]:
    """The change log since a time: each English note, with one entry per place it links to."""
    out = []
    for h in history:
        try:
            t = datetime.fromisoformat(h["createdAt"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError):
            continue
        if t < since:
            continue
        text = h.get("descriptionEn") or ""
        plain = re.sub(r"<[^>]+>", "", html.unescape(text)).strip()
        for zoom, lat, lon, place in re.findall(r'href="[^"]*#(\d+)/(-?[\d.]+)/(-?[\d.]+)"[^>]*>(.*?)</a>', text):
            out.append({"id": h["id"], "time": t, "text": plain, "place": re.sub(r"<[^>]+>", "", place),
                        "lat": round(float(lat), 5), "lon": round(float(lon), 5),
                        "advance": bool(re.search(r"\badvanc|\bcaptur|\boccup", plain, re.I)),
                        "ukr": bool(re.search(r"\bliberat|\bDefense Forces|\bUkrainian forces", plain, re.I))})
    return out


def update_time(h: dict) -> float | None:
    try:
        return datetime.fromisoformat(h["createdAt"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError, TypeError):
        return None
