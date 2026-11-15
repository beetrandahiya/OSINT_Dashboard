"""Patterns in military flights, worked out from positions this server received (the military feed every 5 minutes,
plus the Munich feed every 20 s), kept 3 hours (`Collector.trails`). Derived, and labelled as derived.

- Orbit: an aircraft that keeps turning in the same area. Over the last 2 hours its heading changes add up to at
  least one and a half full turns (540 degrees) while every position stays within 120 km of their centre. That is
  how surveillance, airborne-warning, drone and tanker tracks look (racetracks and circles). Holding before landing
  looks the same; the card shows the type and the path so it can be judged.
- Tanker: a military aircraft of a type that is a tanker (KC-135 "K35R"/"K35E", KC-10, Il-78, KE-3) or is mostly a
  tanker in air-force use (KC-46/KC-767 "B762", A330 MRTT "A332", A310 MRTT "A310", KC-390 "E390"). The A330 and
  767 types also exist as government transports; the card says so.
Aircraft in the VIP list (plane-alert-db: government and head-of-state planes) are never counted as tankers.
Samples 30 seconds apart.
"""
import math

R = 6371.0
# what the type code stands for, for the card (ICAO type designators as adsb.lol reports them)
ISR = {"R135": "RC-135 signals-intelligence aircraft", "E3TF": "E-3 Sentry airborne warning (AWACS)", "E3CF": "E-3 Sentry airborne warning (AWACS)",
       "E737": "E-7 Wedgetail airborne warning", "P8": "P-8 Poseidon maritime patrol / anti-submarine", "P3": "P-3 Orion maritime patrol",
       "ATL2": "Atlantique 2 maritime patrol", "GLHK": "RQ-4 Global Hawk surveillance drone", "Q4": "MQ-4C Triton surveillance drone",
       "Q9": "MQ-9 Reaper / SkyGuardian drone", "U2": "U-2 high-altitude reconnaissance", "E2": "E-2 Hawkeye airborne warning",
       "A50": "A-50 airborne warning", "IL20": "Il-20 reconnaissance", "IL38": "Il-38 maritime patrol", "TU42": "Tu-142 maritime patrol",
       "E6": "E-6B Mercury (nuclear command relay)", "C2": "C-2 / airborne warning", "SB20": "Saab 2000 Erieye airborne warning",
       "GL5T": "Global 5000/6000 (some are surveillance platforms, e.g. GlobalEye)", "CL60": "Challenger 600 series (some are surveillance platforms)"}
TANKER = {"K35R": "KC-135R Stratotanker", "K35E": "KC-135E Stratotanker", "KC10": "KC-10 Extender", "DC10": "KC-10 / DC-10 tanker",
          "IL78": "Il-78 tanker", "B703": "KE-3 / Boeing 707 tanker", "B762": "KC-46 Pegasus or KC-767 tanker (the type is also a transport)",
          "A332": "A330 MRTT tanker-transport (KC-30, Voyager, Phénix; some are government transports)",
          "A310": "A310 MRTT tanker-transport", "E390": "KC-390 tanker-transport"}


def _dist(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(a)))


def _bearing(lon1, lat1, lon2, lat2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    return math.degrees(math.atan2(math.sin(dl) * math.cos(p2), math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)))


def orbit(trail: list, now: float, window=2 * 3600, max_radius=120, min_turn=540):
    pts = [p for p in trail if p[0] >= now - window]
    if len(pts) < 6 or pts[-1][0] - pts[0][0] < 30 * 60 or now - pts[-1][0] > 20 * 60:
        return None
    clon = sum(p[1] for p in pts) / len(pts)
    clat = sum(p[2] for p in pts) / len(pts)
    radius = max(_dist(clon, clat, p[1], p[2]) for p in pts)
    if radius > max_radius:
        return None
    turn, last_b = 0.0, None
    for a, b in zip(pts, pts[1:]):
        if _dist(a[1], a[2], b[1], b[2]) < 1.0:
            continue                                   # no movement worth a heading
        br = _bearing(a[1], a[2], b[1], b[2])
        if last_b is not None:
            turn += (br - last_b + 540) % 360 - 180
        last_b = br
    if abs(turn) < min_turn:
        return None
    # time on station: from the oldest position (within the 3 h we keep) that is still near this centre
    since = pts[-1][0]
    for p in reversed(trail):
        if _dist(clon, clat, p[1], p[2]) > max_radius * 1.3:
            break
        since = p[0]
    return {"lon": round(clon, 4), "lat": round(clat, 4), "radius_km": round(radius, 1), "turns": round(abs(turn) / 360, 1),
            "since": since, "points": len(pts), "path": [[round(p[1], 4), round(p[2], 4)] for p in pts]}


def analyse(trails: dict, military: list[dict], now: float, vip: dict | None = None) -> dict:
    vip = vip or {}
    by_hex = {a["hex"]: a for a in military}
    orbits, tankers = [], []
    for hex_, a in by_hex.items():
        t = a.get("type")
        if t in TANKER and a.get("alt_ft") != "ground" and hex_ not in vip:   # government A330s and 767s are in the VIP list
            tankers.append({**_brief(a), "role": TANKER[t]})
        tr = trails.get(hex_)
        if tr and a.get("alt_ft") != "ground":
            o = orbit(tr, now)
            if o:
                orbits.append({**_brief(a), **o, "role": ISR.get(t) or TANKER.get(t), "kind": "isr" if t in ISR else "tanker" if t in TANKER else "other"})
    return {"orbits": orbits, "tankers": tankers, "now": now}


def _brief(a: dict) -> dict:
    return {k: a.get(k) for k in ("hex", "flight", "reg", "type", "lon", "lat", "alt_ft", "gs_kt", "track")}
