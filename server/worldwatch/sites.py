"""Military bases and nuclear sites, from open data only. Refreshed weekly; every site carries its source.

Military bases:
- Wikidata (CC0): items of a whitelist of base classes (air bases, RAF stations, naval and submarine bases, missile
  bases and launch facilities, military radar and listening stations, forward operating bases, spaceports...), with
  country and operator, so a US base in Germany says "United States Air Force". Never the whole subclass tree of
  "military installation": that pulls in gendarmerie barracks, Roman forts and bird hides. Closed bases are left out.
- OpenStreetMap (ODbL, © OpenStreetMap contributors) via QLever, the University of Freiburg's SPARQL copy of the
  planet (about two months behind): military=base|airfield|naval_base|radar|launchpad|ammunition. Objects whose
  wikidata tag is already in the Wikidata set are merged into that item.
- US DoD MIRTA (public domain): installations in the 50 states, Puerto Rico and Guam (not overseas); points within
  3 km of one we already have are merged.

Nuclear:
- Power: Global Energy Monitor's Global Nuclear Power Tracker (CC BY 4.0), the file its public map loads, grouped
  from units into plants, with status and whether the location is exact.
- Research reactors, enrichment, reprocessing, waste, mines and other facilities: Wikidata's nuclear-facility tree.
- Test sites: a fixed list of Wikidata items (namesakes exist: Malden Island in Maine, several Kiritimati), with
  OpenStreetMap's individual explosion points shown only within 60 km of one of them (vandal points exist elsewhere).
- Nuclear-weapons storage and production sites: there is no open dataset; only what Wikidata and OSM name.
"""
import csv
import io
import json
import math
import re

WDQS = "https://query.wikidata.org/sparql"
QLEVER = "https://qlever.dev/api/osm-planet"
MIRTA = ("https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/MIRTA_Points_A_view/FeatureServer/0/query"
         "?where=1%3D1&outFields=siteName,featureName,siteOperationalStatus,siteReportingComponent,stateNameCode,isJointBase&f=geojson&resultRecordCount=2000")
GEM_CONFIG = "https://globalenergymonitor.github.io/interim-maps/trackers/gnpt/config.js"

# Wikidata class -> our kind
WD_CLASSES = {"Q695850": "air", "Q7373622": "air", "Q1428515": "air", "Q6981985": "air",
              "Q1324633": "naval", "Q7619063": "naval", "Q331367": "naval", "Q1745026": "naval", "Q55624858": "naval", "Q452020": "naval",
              "Q245016": "base", "Q2886620": "base", "Q136644356": "base", "Q141804315": "base", "Q85881832": "base", "Q2604714": "base", "Q136558797": "base",
              "Q133288241": "radar", "Q89578131": "radar", "Q6646468": "sigint",
              "Q21193688": "missile", "Q853409": "missile", "Q194188": "space", "Q1778846": "training"}
WD_BASES = """SELECT ?i (SAMPLE(?name) AS ?n) (SAMPLE(?c) AS ?coord) (GROUP_CONCAT(DISTINCT ?t;separator="|") AS ?types)
 (GROUP_CONCAT(DISTINCT ?cc;separator="|") AS ?country) (GROUP_CONCAT(DISTINCT ?opl;separator="|") AS ?operators) (SAMPLE(?end) AS ?ended) WHERE {
 VALUES ?t { %s }
 ?i wdt:P31 ?t ; wdt:P625 ?c .
 OPTIONAL{ ?i rdfs:label ?name FILTER(lang(?name) IN ("en","mul")) }
 OPTIONAL{ ?i wdt:P17/wdt:P297 ?cc }
 OPTIONAL{ ?i wdt:P137 ?op . ?op rdfs:label ?opl FILTER(lang(?opl)="en") }
 OPTIONAL{ ?i wdt:P576|wdt:P3999 ?end }
} GROUP BY ?i""" % " ".join("wd:" + q for q in WD_CLASSES)
MILITARY_WORDS = re.compile(r"air force|army|navy|naval|military|defen[cs]e|space force|early.warning|missile|aerospace forces|PLA|marine|NORAD|RAF", re.I)

OSM_MIL = """PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
SELECT ?o ?v ?name ?op ?wd (geof:centroid(?w) AS ?c) WHERE {
 ?o osmkey:military ?v . VALUES ?v {"base" "airfield" "naval_base" "radar" "launchpad" "ammunition" "nuclear_explosion_site"}
 OPTIONAL{?o osmkey:name ?name} OPTIONAL{?o osmkey:operator ?op} OPTIONAL{?o osmkey:wikidata ?wd}
 ?o geo:hasGeometry/geo:asWKT ?w }"""
OSM_KIND = {"base": "base", "airfield": "air", "naval_base": "naval", "radar": "radar", "launchpad": "space", "ammunition": "ammo"}

WD_NUCLEAR = """SELECT ?i (SAMPLE(?l) AS ?label) (SAMPLE(?c) AS ?coord) (GROUP_CONCAT(DISTINCT ?tl;separator="|") AS ?types)
 (GROUP_CONCAT(DISTINCT ?cc;separator="|") AS ?country) (GROUP_CONCAT(DISTINCT ?opl;separator="|") AS ?operators) WHERE {
 { ?i wdt:P31 ?type . ?type wdt:P279* wd:Q1739545 } UNION { ?i wdt:P31 ?type . ?type wdt:P279* wd:Q28599311 }
 ?i wdt:P625 ?c . ?type rdfs:label ?tl FILTER(lang(?tl)="en")
 OPTIONAL{ ?i rdfs:label ?l FILTER(lang(?l) IN ("en","mul")) }
 OPTIONAL{ ?i wdt:P17/wdt:P297 ?cc }
 OPTIONAL{ ?i wdt:P137 ?op . ?op rdfs:label ?opl FILTER(lang(?opl)="en") }
} GROUP BY ?i"""

# Nuclear test sites: Wikidata items and the coordinates Wikidata holds for them (read 2026-11-15). Country by the
# state that tested there.
TEST_SITES = [
    ("Q757666", "Semipalatinsk Test Site", "USSR", 78.9956, 50.0278), ("Q4156573", "Degelen Mountain", "USSR", 78.1181, 49.8078),
    ("Q1344605", "Nevada National Security Site", "United States", -116.05, 37.1167), ("Q11703929", "Novaya Zemlya Test Site", "USSR / Russia", None, None),
    ("Q319412", "Lop Nur", "China", 90.5833, 40.1667), ("Q1726774", "Malan (21st Test and Training Base)", "China", 88.712, 41.5448),
    ("Q5306661", "Punggye-ri Nuclear Test Site", "North Korea", 129.0872, 41.2778), ("Q1779576", "Pokhran Test Range", "India", 71.9208, 26.9194),
    ("Q3270072", "Pokhran-II", "India", 71.7222, 27.0789), ("Q7294662", "Ras Koh Hills (Chagai-I)", "Pakistan", 65.1950, 28.8285),
    ("Q5066829", "Chagai-II (Kharan)", "Pakistan", 63.86, 28.43), ("Q318446", "Moruroa", "France", -138.9167, -21.8333),
    ("Q506815", "Fangataufa", "France", -138.75, -22.25), ("Q255890", "Maralinga", "United Kingdom", 131.583, -30.15),
    ("Q14935706", "Emu Field", "United Kingdom", 132.3714, -28.6983), ("Q1268314", "Montebello Islands", "United Kingdom", 115.5167, -20.4667),
    ("Q582905", "Reggane", "France", 0.1667, 26.7), ("Q3149614", "In Ekker", "France", 5.0819, 24.0206),
    ("Q152225", "Bikini Atoll", "United States", 165.4, 11.6), ("Q649190", "Enewetak Atoll", "United States", 162.3333, 11.5),
    ("Q193331", "Kiritimati (Christmas Island)", "United Kingdom, United States", -157.4, 1.85), ("Q532590", "Malden Island", "United Kingdom", -154.9333, -4.0167),
    ("Q131008", "Johnston Atoll", "United States", -169.534, 16.728), ("Q460282", "Amchitka", "United States", 178.983, 51.542),
    ("Q2214815", "Salmon Site", "United States", -89.57, 31.142), ("Q2307093", "Totskoye range", "USSR", 52.817, 52.547),
    ("Q753201", "Kapustin Yar", "USSR", 46.295, 48.566), ("Q782082", "Sary Shagan", "USSR", 72.867, 46.383),
]
NOVAYA_BOX = (50, 70, 60, 77)        # lon0, lat0, lon1, lat1: where OSM's Novaya Zemlya explosion points lie


def km(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(min(1, math.sqrt(a)))


def _point(wkt: str):
    m = re.search(r"POINT\(\s*(-?[\d.e+-]+)\s+(-?[\d.e+-]+)", wkt or "", re.I)
    return (round(float(m.group(1)), 5), round(float(m.group(2)), 5)) if m else None


def _qid(uri: str) -> str:
    return (uri or "").rsplit("/", 1)[-1]


def _csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------- military
def merge_military(wd_csv: str, osm_csv: str, mirta: dict) -> dict:
    """-> {"sites": [[lon, lat, kind, name, source, ref, country, operator]], "counts": {...}}"""
    sites, by_qid, dropped_closed = [], {}, 0
    for r in _csv(wd_csv):
        pt = _point(r.get("coord"))
        if not pt:
            continue
        if r.get("ended"):
            dropped_closed += 1
            continue
        types = [_qid(t) for t in (r.get("types") or "").split("|")]
        kinds = [WD_CLASSES[t] for t in types if t in WD_CLASSES]
        kind = next((k for k in ("missile", "sigint", "naval", "air", "radar", "space", "base", "training") if k in kinds), "base")
        name, ops = r.get("n") or "", r.get("operators") or ""
        if kind == "radar" and "Q133288241" not in types and not MILITARY_WORDS.search(name + " " + ops):
            continue                                    # "radar station" also covers weather radars
        q = _qid(r["i"])
        by_qid[q] = len(sites)
        sites.append([pt[0], pt[1], kind, name or q, "wikidata", q, (r.get("country") or "").split("|")[0] or None, ops.replace("|", ", ") or None])
    n_wd = len(sites)
    explosions, merged = [], 0
    for r in _csv(osm_csv):
        pt = _point(r.get("c"))
        if not pt:
            continue
        if r.get("v") == "nuclear_explosion_site":
            explosions.append([pt[0], pt[1], r.get("name") or None, r["o"].split("openstreetmap.org/")[-1]])
            continue
        if r.get("v") not in OSM_KIND:
            continue
        wd = (r.get("wd") or "").strip()
        if wd in by_qid:
            s = sites[by_qid[wd]]
            if len(s) < 9:
                s.append(r["o"].split("openstreetmap.org/")[-1])       # the OSM object, for a second link
            merged += 1
            continue
        if not r.get("name") and r.get("v") in ("ammunition", "radar"):
            continue                                    # thousands of unnamed bunkers-of-sorts add only noise
        sites.append([pt[0], pt[1], OSM_KIND.get(r["v"], "base"), r.get("name") or None, "osm", r["o"].split("openstreetmap.org/")[-1], None, r.get("op") or None])
    n_osm = len(sites) - n_wd
    # MIRTA: US installations; merged when one we already have is within 3 km
    grid = {}
    for i, s in enumerate(sites):
        grid.setdefault((round(s[0]), round(s[1])), []).append(i)
    added_mirta = 0
    comp = {"usa": "US Army", "usaf": "US Air Force", "usn": "US Navy", "usmc": "US Marine Corps", "ussf": "US Space Force", "armynationalguard": "Army National Guard",
            "airnationalguard": "Air National Guard", "whs": "Washington Headquarters Services"}
    for f in (mirta or {}).get("features", []):
        p, g = f.get("properties", {}), f.get("geometry") or {}
        if p.get("siteOperationalStatus") not in ("act", None) or g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        near = any(km(lon, lat, sites[j][0], sites[j][1]) < 3 for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in grid.get((round(lon) + dx, round(lat) + dy), []))
        if near:
            continue
        c = (p.get("siteReportingComponent") or "").lower().replace(" ", "")
        sites.append([round(lon, 5), round(lat, 5), "base", p.get("siteName") or p.get("featureName"), "mirta", p.get("featureName"), "US", comp.get(c, c.upper() or None)])
        added_mirta += 1
    return {"sites": sites, "explosions": explosions,
            "counts": {"wikidata": n_wd, "osm": n_osm, "osm_merged": merged, "mirta": added_mirta, "closed_left_out": dropped_closed}}


# ---------------------------------------------------------------- nuclear
def gem_plants(geo: dict) -> list[dict]:
    plants = {}
    for f in geo.get("features", []):
        p = f.get("properties", {})
        st = (p.get("status") or "").lower()
        if st in ("cancelled", "shelved"):
            continue
        g = plants.setdefault(p.get("project-id") or p.get("name"), {
            "name": p.get("name"), "lon": round(p.get("Longitude") or f["geometry"]["coordinates"][0], 5), "lat": round(p.get("Latitude") or f["geometry"]["coordinates"][1], 5),
            "country": p.get("all-countries") or p.get("country-area1"), "exact": p.get("location-accuracy") == "exact", "url": p.get("url"),
            "owner": p.get("owner") or None, "operator": p.get("operator") or None, "units": {}, "mw": {}, "types": set()})
        g["units"][st] = g["units"].get(st, 0) + 1
        try:
            g["mw"][st] = g["mw"].get(st, 0) + float(p.get("capacity") or 0)
        except (TypeError, ValueError):
            pass
        if p.get("reactor-type") and p["reactor-type"] != "unknown":
            g["types"].add(p["reactor-type"])
    out = []
    for g in plants.values():
        g["types"] = sorted(g["types"])
        order = ["operating", "construction", "pre-construction", "announced", "mothballed", "retired"]
        g["status"] = next((s for s in order if s in g["units"]), next(iter(g["units"]), "unknown"))
        out.append(g)
    return out


NUC_KIND = [("research reactor", "research"), ("enrichment", "fuel"), ("reprocessing", "fuel"), ("conversion", "fuel"), ("fuel", "fuel"),
            ("uranium mine", "mine"), ("mine", "mine"), ("waste", "waste"), ("repository", "waste"), ("test site", "test"),
            ("weapon", "weapons"), ("power", "power")]


def wd_nuclear(text: str) -> list[dict]:
    out = []
    for r in _csv(text):
        pt = _point(r.get("coord"))
        if not pt:
            continue
        types = (r.get("types") or "").lower()
        kind = next((k for w, k in NUC_KIND if w in types), "facility")
        if kind == "power":
            continue                                    # GEM's tracker has the power plants, per unit and current
        out.append({"lon": pt[0], "lat": pt[1], "kind": kind, "name": r.get("label") or _qid(r["i"]), "qid": _qid(r["i"]),
                    "types": (r.get("types") or "").replace("|", ", "), "country": (r.get("country") or "").split("|")[0] or None,
                    "operator": (r.get("operators") or "").replace("|", ", ") or None})
    return out


def test_sites(explosions: list) -> tuple[list[dict], list]:
    """The fixed list, with OSM explosion points kept only near a site (or inside the Novaya Zemlya box)."""
    sites = [{"qid": q, "name": n, "by": c, "lon": lon, "lat": lat} for q, n, c, lon, lat in TEST_SITES]
    kept = []
    for e in explosions:
        lon, lat = e[0], e[1]
        best = min((s for s in sites if s["lon"] is not None), key=lambda s: km(lon, lat, s["lon"], s["lat"]))
        if km(lon, lat, best["lon"], best["lat"]) <= 60:
            kept.append(e + [best["qid"]])
        elif NOVAYA_BOX[0] <= lon <= NOVAYA_BOX[2] and NOVAYA_BOX[1] <= lat <= NOVAYA_BOX[3]:
            kept.append(e + ["Q11703929"])
    nz = [e for e in kept if e[-1] == "Q11703929"]
    for s in sites:
        if s["qid"] == "Q11703929" and nz:              # Wikidata has no point for it: the centre of OSM's explosion points
            s["lon"] = round(sum(e[0] for e in nz) / len(nz), 4)
            s["lat"] = round(sum(e[1] for e in nz) / len(nz), 4)
            s["from_osm"] = True
        s["explosions"] = sum(1 for e in kept if e[-1] == s["qid"])
    return [s for s in sites if s["lon"] is not None], kept


def gem_url(config_js: str) -> str | None:
    m = re.search(r"https://[^\"']+gnpt_map[^\"']+\.geojson", config_js)
    return m.group(0) if m else None


def build(parts: dict) -> dict:
    """For a child process: everything from the raw answers."""
    mil = merge_military(parts.get("wd_bases") or "", parts.get("osm") or "", parts.get("mirta") or {})
    tests, explosions = test_sites(mil.pop("explosions"))
    return {"military": mil["sites"], "military_counts": mil["counts"],
            "plants": gem_plants(parts.get("gem") or {}), "facilities": wd_nuclear(parts.get("wd_nuclear") or ""),
            "tests": tests, "explosions": explosions}
