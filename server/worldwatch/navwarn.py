"""Navigational warnings at sea that say something is happening: weapons firing, missile and rocket launches and
their debris zones, military exercises, piracy and attacks, GPS jamming. Lights, buoys and wind-farm notices
are left out (they are most of the traffic and none of the news).

Sources: the US National Geospatial-Intelligence Agency's broadcast warnings (NAVAREA IV and XII and the
worldwide HYDROLANT / HYDROPAC series, which relay other countries' notices too), and the UK Hydrographic
Office's NAVAREA I page (north-east Atlantic). Both are official.

Shapes are drawn only where the text states them: "WITHIN n MILES OF <point>" becomes a circle, "AREA BOUND BY
<points>" a polygon. Anything else is marked at the points the text names. Nothing is guessed.
"""
import calendar
import html
import math
import re

KINDS = [  # (kind, words) checked in order; the first match wins
    ("rocket", r"ROCKET|SPACE DEBRIS|SPACE VEHICLE|SPACECRAFT|LAUNCH VEHICLE|BOOSTER|RE-?ENTRY"),
    ("missile", r"MISSILE"),
    ("weapons", r"FIRING|GUNNERY|LIVE WEAPONS|EXPLOSIVE|ORDNANCE|DEMOLITION|BOMBING|\bMINE(S|FIELDS?)?\b|TORPEDO"),
    ("exercise", r"MILITARY EXERCISE|NAVAL EXERCISE|EXERCISE|NAVAL OPERATIONS|MILITARY OPERATIONS|SUBMARINE"),
    ("security", r"PIRACY|PIRATE|ARMED ROBBERY|ATTACK|HIJACK|SECURITY|DRONE|UNMANNED AERIAL|UAV|HOSTILE"),
    ("gnss", r"GNSS|GPS|JAMMING|INTERFERENCE|SPOOFING"),
]
KIND_NAMES = {"rocket": "Rocket or space debris", "missile": "Missile firing", "weapons": "Weapons firing or explosives",
              "exercise": "Military exercise", "security": "Security threat", "gnss": "GPS / GNSS interference"}

# 57-27N 008-16W, 57-11.5N 001-52.6E, 12-34.56S 123-45.67E
COORD = re.compile(r"(\d{1,2})-(\d{1,2}(?:\.\d+)?)\s*([NS])\s+(\d{1,3})-(\d{1,2}(?:\.\d+)?)\s*([EW])")


def _pt(m) -> tuple[float, float]:
    lat = int(m.group(1)) + float(m.group(2)) / 60
    lon = int(m.group(4)) + float(m.group(5)) / 60
    return (-lon if m.group(6) == "W" else lon, -lat if m.group(3) == "S" else lat)


def kind_of(text: str) -> str | None:
    up = text.upper()
    for kind, words in KINDS:
        if re.search(words, up):
            return kind
    return None


def _circle(lon, lat, nm, n=48):
    r = nm * 1852 / 6371000
    out = []
    for i in range(n + 1):
        b = 2 * math.pi * i / n
        la = math.asin(math.sin(math.radians(lat)) * math.cos(r) + math.cos(math.radians(lat)) * math.sin(r) * math.cos(b))
        lo = math.radians(lon) + math.atan2(math.sin(b) * math.sin(r) * math.cos(math.radians(lat)), math.cos(r) - math.sin(math.radians(lat)) * math.sin(la))
        out.append([round(math.degrees(lo), 4), round(math.degrees(la), 4)])
    return out


def shapes(text: str) -> tuple[list[dict], str]:
    """GeoJSON geometries the text states, and how they were read ('areas', 'circles' or 'points')."""
    up = " ".join(text.upper().split())
    geoms, how = [], set()
    # circles: WITHIN 26 MILES OF 57-27N 008-16W  (also "RADIUS 5 MILES CENTERED ON")
    for m in re.finditer(r"(?:WITHIN|RADIUS(?: OF)?)\s+(\d+(?:\.\d+)?)\s*(?:NAUTICAL\s+)?(?:MILES?|NM|NMI)\s+(?:OF|CENT(?:ER|RE)D?\s+(?:ON|AT))\s+", up):
        c = COORD.match(up, m.end())
        if c:
            lon, lat = _pt(c)
            geoms.append({"type": "Polygon", "coordinates": [_circle(lon, lat, float(m.group(1)))]})
            how.add("circles")
    # polygons: AREA(S) BOUND(ED) BY p1, p2, p3 ... (one run of coordinates separated by commas, AND, spaces)
    for m in re.finditer(r"BOUND(?:ED)?\s+BY\s+", up):
        pts, pos = [], m.end()
        while True:
            c = COORD.match(up, pos)
            if not c:
                break
            pts.append(list(_pt(c)))
            pos = c.end()
            sep = re.match(r"\s*(?:,|AND|;)?\s*(?:[A-Z]\.\s+)?", up[pos:])
            pos += sep.end() if sep else 0
        if len(pts) >= 3:
            geoms.append({"type": "Polygon", "coordinates": [pts + [pts[0]]]})
            how.add("areas")
    if not geoms:
        pts = [list(_pt(c)) for c in COORD.finditer(up)]
        if pts:
            geoms.append({"type": "MultiPoint", "coordinates": pts[:60]})
            how.add("points")
    return geoms, "+".join(sorted(how))


def centre(geoms) -> tuple[float, float] | None:
    pts = []
    for g in geoms:
        if g["type"] == "Polygon":
            pts += g["coordinates"][0][:-1]
        else:
            pts += g["coordinates"]
    if not pts:
        return None
    # mean of unit vectors, so areas across the date line come out right
    x = sum(math.cos(math.radians(p[1])) * math.cos(math.radians(p[0])) for p in pts)
    y = sum(math.cos(math.radians(p[1])) * math.sin(math.radians(p[0])) for p in pts)
    z = sum(math.sin(math.radians(p[1])) for p in pts)
    return (round(math.degrees(math.atan2(y, x)), 4), round(math.degrees(math.atan2(z, math.hypot(x, y))), 4))


_MON = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


def issued_time(s: str | None) -> float | None:
    """A date-time group ("121631 UTC Nov 26", "181200Z NOV 2026") as unix seconds; None if it does not parse.
    List rows sort by it: the fetch time would make every warning "newest" on every fetch."""
    m = re.search(r"(\d{2})(\d{2})(\d{2})\s*(?:Z|UTC)?\s+([A-Za-z]{3})\w*\s+(\d{2,4})", s or "")
    if not m or m.group(4).upper() not in _MON:
        return None
    y = int(m.group(5)); y += 2000 if y < 100 else 0
    try:
        return calendar.timegm((y, _MON[m.group(4).upper()], int(m.group(1)), int(m.group(2)), int(m.group(3)), 0))
    except (ValueError, OverflowError):
        return None


def warning(source: str, ref: str, issued: str | None, area: str | None, text: str, link: str) -> dict | None:
    kind = kind_of(text)
    if not kind:
        return None
    geoms, how = shapes(text)
    c = centre(geoms)
    return {"id": f"{source}:{ref}", "source": source, "ref": ref, "issued": issued, "issued_t": issued_time(issued), "area": area, "kind": kind,
            "text": text.strip(), "geoms": geoms, "how": how, "lon": c[0] if c else None, "lat": c[1] if c else None, "link": link}


def parse_ukho(page: str) -> list[dict]:
    out = []
    rows = re.findall(r'id="Reference_(\d+)"[^>]*>\s*(.*?)\s*</td>.*?id="DateTimeGroupRnwFormat_\1"[^>]*>\s*(.*?)\s*</td>'
                      r'.*?id="Details_Description_\1"[^>]*>(.*?)</pre>', page, re.S)
    for _, ref, dtg, body in rows:
        text = html.unescape(re.sub(r"<[^>]+>", "", body)).strip()
        w = warning("UKHO", html.unescape(ref).strip(), dtg.strip(), "NAVAREA I (UK)", text, "https://msi.admiralty.co.uk/RadioNavigationalWarnings")
        if w:
            out.append(w)
    return out


def parse_nga(data) -> list[dict]:
    items = data.get("broadcast-warn") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError(f"unexpected answer from NGA (keys: {list(data)[:6] if isinstance(data, dict) else type(data).__name__})")
    area_names = {"4": "NAVAREA IV", "12": "NAVAREA XII", "A": "HYDROLANT", "P": "HYDROPAC", "C": "HYDROARC"}
    out = []
    for it in items:
        if not isinstance(it, dict) or not it.get("text"):
            continue
        area = area_names.get(str(it.get("navArea")), str(it.get("navArea") or ""))
        ref = f"{area} {it.get('msgNumber')}/{str(it.get('msgYear', ''))[-2:]}"
        w = warning("NGA", ref, it.get("issueDate"), area + (f" · {it['subregion']}" if it.get("subregion") else ""),
                    it["text"], "https://msi.nga.mil/NavWarnings")
        if w:
            w["authority"] = it.get("authority")
            out.append(w)
    return out
