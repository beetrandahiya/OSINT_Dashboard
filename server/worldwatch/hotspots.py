"""Hotspots: places where several independent kinds of signal coincide within a day.

No score is invented. A hotspot is simply a place where at least three different kinds of signal (protests or fighting
in the news, a news spike, a navy warning, a US flight restriction, GPS interference, an orbiting military aircraft,
a strong earthquake, a GDACS orange/red alert, a front-line change, an internet outage) fall within RADIUS_KM of each
other, at least two of them tied to a point (country-wide signals such as an outage only add to a point hotspot).
Only security signals count towards the three; earthquakes and disasters are listed alongside as context, because a
quake beside a clash is chance. A country-wide internet outage counts only for a hotspot inside that same country.
Flight restrictions count only when new (started within two days, lasting a week or less): long-standing ones around
bases are not news. Being near each other does not prove the signals are related; the card says so.
The card lists every signal with its source, so each one can be checked.
"""
import math
import re
import time
from datetime import datetime, timezone

from . import geo

RADIUS_KM = 250
CONTEXT = {"quake", "disaster"}
WINDOW_S = 24 * 3600
FAMILIES = {
    "unrest": "Protests or fighting reported (GDELT, 2+ outlets)",
    "spike": "Sudden jump in news reports (GDELT)",
    "navwarn": "Navy warning in force (NAVAREA)",
    "tfr": "US temporary flight restriction",
    "gps": "GPS interference, last hour (from aircraft reports)",
    "orbit": "Military aircraft circling",
    "quake": "Earthquake of magnitude 5 or more (USGS)",
    "disaster": "GDACS orange or red alert",
    "front": "Front-line change (DeepState)",
    "outage": "Internet outage in the country (IODA / Cloudflare)",
}


def _km(a, b):
    r = math.pi / 180
    d = math.sin((b[1] - a[1]) * r / 2) ** 2 + math.cos(a[1] * r) * math.cos(b[1] * r) * math.sin((b[0] - a[0]) * r / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(d)))


def _centre(rings):
    pts = [p for ring in rings for p in ring]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None


def signals(states: dict, spikes: list, orbits: list, now: float) -> list[dict]:
    p = lambda name: (states.get(name).payload if states.get(name) else None) or {}
    out = []
    def add(fam, title, lon, lat, t, layer=None, id_=None, scope="point", cc=None):
        if lon is None or lat is None:
            return
        out.append({"fam": fam, "title": title, "lon": float(lon), "lat": float(lat), "time": t, "layer": layer, "id": id_, "scope": scope, "cc": cc})
    for g in p("unrest").get("groups", []):
        if g.get("outlets", 0) >= 2 and now - (g.get("last") or 0) < WINDOW_S:
            add("unrest", f"{g['cat'].capitalize()} in {g['place'].split(',')[0]}, {g['outlets']} outlets", g["lon"], g["lat"], g["last"], "unrest", g["id"], cc=g.get("country"))
    for s in spikes:
        a = (s.get("articles") or [{}])[0]
        add("spike", f"News jump in {s['place'].split(',')[0]}: {a.get('title', '')[:90]}", s.get("lon"), s.get("lat"), s.get("first") or s.get("last") or now, "spikes", s.get("id"))
    for w in p("navwarn").get("warnings", []):
        add("navwarn", f"{w.get('kind', '').capitalize()} warning {w.get('ref', '')} ({w.get('area', '')})", w.get("lon"), w.get("lat"), now, "navwarn", w["id"])
    for t in p("airspace").get("tfrs", []):
        c = _centre(t.get("polys") or [])
        m = re.match(r"\s*(\d{6})(?:-(\d{2,6}))?", t.get("name") or "")
        fresh = False
        if m:
            try:
                start = datetime.strptime(m.group(1), "%y%m%d").replace(tzinfo=timezone.utc).timestamp()
                e = m.group(2) or m.group(1)
                end = datetime.strptime((m.group(1)[:6 - len(e)] + e) if len(e) < 6 else e, "%y%m%d").replace(tzinfo=timezone.utc).timestamp()
                fresh = now - 2 * 86400 <= start <= now + 86400 and end - start <= 7 * 86400
            except ValueError:
                pass
        if c and fresh and t.get("type") in ("SECURITY", "SPACE OPERATIONS", "HAZARDS", "SPECIAL"):
            add("tfr", f"{t.get('type', '').title()} flight restriction: {(t.get('name') or t.get('where') or '').strip()[:80]}", c[0], c[1], now, "airspace", t["id"])
    for f in p("gps_live").get("features", []):
        pr = f.get("properties", {})
        if pr.get("level") == "high" and pr.get("bad", 0) >= 3:
            c = _centre(f["geometry"]["coordinates"])
            if c:
                add("gps", f"GPS interference: {pr['bad']} of {pr['bad'] + pr.get('good', 0)} aircraft with poor accuracy", c[0], c[1], now, "gpslive", pr.get("id"))
    for o in orbits:
        add("orbit", f"{o.get('flight') or o.get('reg') or o.get('hex')} ({o.get('type') or '?'}) circling" + (", a surveillance type" if o.get("kind") == "isr" else ""),
            o.get("lon"), o.get("lat"), now, "orbits", "orbit:" + o["hex"])
    for q in p("quakes").get("quakes", []):
        if (q.get("mag") or 0) >= 5 and now - q["time"] < WINDOW_S:
            add("quake", f"M{q['mag']:.1f} earthquake, {q.get('place', '')}", q["lon"], q["lat"], q["time"], "quakes", q["id"])
    for e in p("gdacs").get("events", []):
        if e.get("level") in ("Orange", "Red") and e.get("code") != "DR":     # droughts span half a continent
            add("disaster", f"GDACS {e['level'].lower()} alert: {e.get('title') or e.get('name')}", e.get("lon"), e.get("lat"), e.get("modified") or now, "hazards", e["id"])
    for c in p("front_ukraine").get("changes", []):
        if now - c["time"] < 2 * WINDOW_S:            # same id as frontline.js keyOf.c
            add("front", c["text"][:110], c.get("lon"), c.get("lat"), c["time"], "front", f"front:c{c['id']}|{c.get('place')}")
    for e in p("outages").get("events", []):
        if e["start"] + e["duration_s"] > now - 900:
            add("outage", f"Internet outage signal, {e['where']} (IODA)", e.get("lon"), e.get("lat"), e["start"], "outages", e["id"], scope="country", cc=e.get("code"))
    return out


def find(sigs: list[dict]) -> list[dict]:
    pts = [s for s in sigs if s["scope"] == "point"]
    used, spots = set(), []
    # seed from the signal with the most different kinds of neighbours, then take everything near it
    def near(s):
        return [j for j, t in enumerate(pts) if _km((s["lon"], s["lat"]), (t["lon"], t["lat"])) <= RADIUS_KM]
    order = sorted(range(len(pts)), key=lambda i: -len({pts[j]["fam"] for j in near(pts[i])} - CONTEXT))
    for i in order:
        if i in used:
            continue
        group = [j for j in near(pts[i]) if j not in used]
        fams = {pts[j]["fam"] for j in group} - CONTEXT
        if len(fams) < 2:
            continue
        members = [pts[j] for j in group]
        core = [m for m in members if m["fam"] not in CONTEXT]
        lon = sum(m["lon"] for m in core) / len(core)
        lat = sum(m["lat"] for m in core) / len(core)
        try:
            iso = geo.where(lon, lat)
        except Exception:
            iso = None
        extra = [s for s in sigs if s["scope"] == "country" and s["fam"] not in fams and iso and (s.get("cc") or "").upper() == iso]
        allfams = fams | {s["fam"] for s in extra}
        if len(allfams) < 3:
            continue
        used.update(group)
        # id from the oldest counted signal, not the list position: reloads every 5 minutes reorder the list, and an
        # open card must not silently become another hotspot
        seed = min(core, key=lambda m: (m["time"] or 0, m["fam"], str(m["id"] or m["title"])))
        spots.append({"id": "hot:" + seed["fam"] + ":" + str(seed["id"] or f"{seed['lon']:.2f},{seed['lat']:.2f}"), "lon": round(lon, 3), "lat": round(lat, 3), "country": iso, "families": sorted(allfams), "kinds": len(allfams),
                      "context": sorted({m["fam"] for m in members} & CONTEXT),
                      "signals": sorted(members + extra, key=lambda m: (m["fam"], -(m["time"] or 0))),
                      "first": min(m["time"] or 0 for m in members), "last": max(m["time"] or 0 for m in members)})
    return sorted(spots, key=lambda s: (-s["kinds"], -len(s["signals"])))


def compute(states: dict, spikes: list, orbits: list) -> dict:
    now = time.time()
    sigs = signals(states, spikes, orbits, now)
    counts = {}
    for s in sigs:
        counts[s["fam"]] = counts.get(s["fam"], 0) + 1
    return {"hotspots": find(sigs), "signals_seen": counts, "families": FAMILIES, "radius_km": RADIUS_KM, "window_h": WINDOW_S // 3600, "now": now}
