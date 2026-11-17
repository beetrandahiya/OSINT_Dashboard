"""What a satellite is and does, and where the spy satellites are.

- Purpose per satellite from the Union of Concerned Scientists' Satellite Database (free download, one Excel file,
  7,563 active satellites with operator, users and purpose; last updated May 2023, so newer satellites are missing).
  Read with the standard library: an .xlsx file is a zip of XML.
- Photo and description from Wikidata, by catalogue number (property P377), looked up when a card opens.
- Orbits of military imaging and signals satellites: the public ones from CelesTrak (by the catalogue numbers the
  UCS list marks as military Earth observation), and the classified US ones from amateur observers
  (Mike McCants' classfd.tle, compiled from the SeeSat-L community's sightings). Those are labelled as such.
"""
import calendar
import html
import io
import json
import re
import time
import zipfile
from datetime import datetime, timedelta, timezone

from . import config

UCS_URL = "https://www.ucs.org/media/11492"
MCCANTS_URL = "https://www.mmccants.org/tles/classfd.zip"
UCS_FILE = config.DATA / "ucs-satellites.json"


def parse_ucs(raw: bytes) -> dict[int, dict]:
    z = zipfile.ZipFile(io.BytesIO(raw))
    strings = [html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
               for si in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    rows = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode("utf-8"), re.S):
        cells = {}
        for ref, attrs, v in re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<f>.*?</f>)?<v>(.*?)</v>', row, re.S):
            cells[ref] = strings[int(v)] if 't="s"' in attrs else v
        rows.append(cells)
    col = {v.strip(): k for k, v in rows[0].items()}
    get = lambda r, name: (r.get(col.get(name, "?")) or "").strip() or None
    out = {}
    for r in rows[1:]:
        try:
            norad = int(float(get(r, "NORAD Number") or "x"))
        except ValueError:
            continue
        launch = get(r, "Date of Launch")
        if launch and re.fullmatch(r"\d+(\.\d+)?", launch):          # Excel serial day
            launch = (datetime(1899, 12, 30) + timedelta(days=float(launch))).strftime("%Y-%m-%d")
        out[norad] = {"name": get(r, "Current Official Name of Satellite") or get(r, "Name of Satellite, Alternate Names"),
                      "country": get(r, "Country of Operator/Owner"), "operator": get(r, "Operator/Owner"), "users": get(r, "Users"),
                      "purpose": get(r, "Purpose"), "detail": get(r, "Detailed Purpose"), "launched": launch,
                      "contractor": get(r, "Contractor"), "mass_kg": get(r, "Launch Mass (kg.)"), "comments": get(r, "Comments")}
    return out


def code(row: dict) -> str:
    """One word for what the satellite does, from UCS's purpose and detailed purpose."""
    p, d = (row.get("purpose") or "").lower(), (row.get("detail") or "").lower()
    if "electronic intelligence" in d or "signals" in d or "sigint" in d:
        return "signals"
    if "early warning" in d:
        return "warning"
    if "radar" in d or "sar" == d:
        return "radar"
    if "meteor" in d or "meter" in d or "weather" in d:   # UCS spells it "Meterology"
        return "weather"
    if "earth observation" in p or "imaging" in d or "surveillance" in p:
        return "imaging"
    if "navigation" in p:
        return "navigation"
    if "communications" in p:
        return "comms"
    if "science" in p or "observation" in p:
        return "science"
    if "technology" in p:
        return "technology"
    return "other"


def spy(row: dict) -> bool:
    return "military" in (row.get("users") or "").lower() and code(row) in ("imaging", "radar", "signals", "warning")


def compact(ucs: dict[int, dict]) -> dict[str, list]:
    from .flags import ucs_flags
    return {str(k): [code(v), "military" in (v.get("users") or "").lower(), ucs_flags(v.get("country"))] for k, v in ucs.items()}


def save(ucs):
    UCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UCS_FILE.write_text(json.dumps(ucs))


def load() -> dict[int, dict]:
    try:
        return {int(k): v for k, v in json.loads(UCS_FILE.read_text()).items()}
    except (OSError, ValueError):
        return {}


def _exp(s: str) -> float:
    """TLE's packed exponent format: ' 12345-3' means 0.12345e-3."""
    s = s.strip()
    if not s or s in ("0", "00000-0", "00000+0", "-00000-0"):
        return 0.0
    m = re.fullmatch(r"([+-]?)(\d+)([+-]\d)", s)
    return float(f"{m.group(1)}0.{m.group(2)}e{m.group(3)}") if m else 0.0


def tle_to_omm(name: str, l1: str, l2: str) -> dict:
    """The same orbit as CelesTrak's OMM fields, so the browser handles both kinds the same way."""
    yy, day = int(l1[18:20]), float(l1[20:32])
    year = 2000 + yy if yy < 57 else 1900 + yy
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1)
    intl = l1[9:17].strip()
    return {"OBJECT_NAME": name.strip(), "OBJECT_ID": (f"{2000 + int(intl[:2]) if int(intl[:2]) < 57 else 1900 + int(intl[:2])}-{intl[2:]}" if intl[:2].isdigit() else None),
            "NORAD_CAT_ID": int(l1[2:7]), "EPOCH": epoch.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "MEAN_MOTION": float(l2[52:63]), "ECCENTRICITY": float("0." + l2[26:33].strip()), "INCLINATION": float(l2[8:16]),
            "RA_OF_ASC_NODE": float(l2[17:25]), "ARG_OF_PERICENTER": float(l2[34:42]), "MEAN_ANOMALY": float(l2[43:51]),
            "MEAN_MOTION_DOT": float(l1[33:43]), "MEAN_MOTION_DDOT": _exp(l1[44:52]), "BSTAR": _exp(l1[53:61])}


def parse_mccants(raw: bytes, max_age_days=60) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(raw))
    lines = [l.rstrip() for l in z.read(z.namelist()[0]).decode("latin-1").splitlines() if l.strip()]
    out, cut = [], time.time() - max_age_days * 86400
    for i in range(len(lines) - 2):
        if lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 ") and not lines[i].startswith(("1 ", "2 ")):
            try:
                o = tle_to_omm(lines[i], lines[i + 1], lines[i + 2])
            except (ValueError, IndexError):
                continue
            # the list abbreviates the NRO's StarShield satellites (USA 354 onwards) to fit its 14-character name field
            o["OBJECT_NAME"] = name = re.sub(r"\bStarSh$", "StarShield", o["OBJECT_NAME"])
            if re.search(r"(\s(r|rk|deb|r/b)|\sdeb.*)$", name, re.I) or not name.upper().startswith("USA"):
                continue                       # rocket stages, debris and non-US objects: only classified US payloads
            if calendar.timegm(time.strptime(o["EPOCH"][:19], "%Y-%m-%dT%H:%M:%S")) >= cut:
                out.append(o)
    return out


NUM = ("MEAN_MOTION", "ECCENTRICITY", "INCLINATION", "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY",
       "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT", "BSTAR")


def omm_from_csv_row(r: dict) -> dict:
    o = {k: r.get(k) for k in ("OBJECT_NAME", "OBJECT_ID", "EPOCH")}
    o["NORAD_CAT_ID"] = int(r["NORAD_CAT_ID"])
    for k in NUM:
        o[k] = float(r.get(k) or 0)
    return o


def parse_save_compact(raw: bytes):
    """For a child process: parse the spreadsheet, save the full rows to disk, return what the map needs."""
    ucs = parse_ucs(raw)
    save(ucs)
    return compact(ucs), len(ucs), sum(1 for v in ucs.values() if spy(v))


# ---------------------------------------------------------------- manoeuvres of spy satellites
# Each fetch adds every spy satellite's newest orbit (if its epoch is new) to a 45-day history on disk. A change
# between two consecutive orbits is called a manoeuvre only when air drag cannot explain it: drag only ever lowers
# an orbit, and slowly. Thresholds are wider for amateur-tracked orbits, which are rougher.
HISTORY = config.DATA / "orbit-history.json"
MU, RE = 398600.4418, 6378.137


def axis_km(mean_motion_rev_day: float) -> float:
    n = mean_motion_rev_day * 2 * 3.141592653589793 / 86400
    return (MU / n ** 2) ** (1 / 3)


def _epoch_ts(s: str) -> float:
    return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))


def record_history(omm: list[dict]) -> dict:
    try:
        hist = json.loads(HISTORY.read_text())
    except (OSError, ValueError):
        hist = {}
    cut = time.time() - 45 * 86400
    started = hist.pop("_started", time.time())
    for o in omm:
        try:
            t = _epoch_ts(o["EPOCH"])
            row = [t, round(axis_km(float(o["MEAN_MOTION"])), 3), round(float(o["ECCENTRICITY"]), 7), round(float(o["INCLINATION"]), 4),
                   1 if o.get("SOURCE") == "amateur observers" else 0]
        except (KeyError, ValueError, ZeroDivisionError):
            continue
        h = hist.setdefault(str(o["NORAD_CAT_ID"]), [])
        if not h or t > h[-1][0] + 60:
            h.append(row)
        hist[str(o["NORAD_CAT_ID"])] = [r for r in h if r[0] >= cut]
    hist = {k: v for k, v in hist.items() if v}
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps({**hist, "_started": started}, separators=(",", ":")))
    return {**hist, "_started": started}


# How much an orbit changes by itself between two element sets, and how rough the element sets are, depends on the
# orbit and on the time between them. Low orbits: drag only lowers them (allowed for below), the plane stays put.
# High orbits (an orbit takes more than 225 minutes: geostationary, Molniya): the Sun and Moon tilt the plane by up to
# ~0.85 degrees a year (~0.0025 a day), and the published semi-major axis wanders by a few km from the Earth's
# uneven gravity, so a fixed 0.03 degrees / 0.8 km called weeks of natural drift a burn (USA 325, 24 days apart).
def limits(axis: float, days: float, amateur: bool) -> tuple[float, float, float]:
    """(rise km, drop km, plane change degrees) that an orbit change must exceed to count as a manoeuvre."""
    high = 2 * 3.141592653589793 * (axis ** 3 / MU) ** 0.5 / 60 > 225
    if amateur:
        return 5.0, 10.0 + 1.0 * days, 0.2 + (0.0025 * days if high else 0)
    if high:
        return 3.0, 3.0, 0.03 + 0.0025 * days
    return 0.8, 3.0 + 1.0 * days, 0.03 + 0.0005 * days   # natural decay above ~300 km is well under 1 km a day


def manoeuvres(hist: dict, names: dict, since_days=30) -> list[dict]:
    out, cut = [], time.time() - since_days * 86400
    for norad, rows in hist.items():
        if not norad.isdigit():
            continue
        for a, b in zip(rows, rows[1:]):
            if b[0] < cut:
                continue
            amateur = a[4] or b[4]
            days = max((b[0] - a[0]) / 86400, 0.01)
            da = b[1] - a[1]
            di = b[3] - a[3]
            per_a, apo_a = a[1] * (1 - a[2]) - RE, a[1] * (1 + a[2]) - RE
            per_b, apo_b = b[1] * (1 - b[2]) - RE, b[1] * (1 + b[2]) - RE
            raise_km, drop_km, incl_deg = limits(a[1], days, bool(amateur))
            kinds = []
            if da > raise_km:
                kinds.append("raised")
            elif da < -drop_km:
                kinds.append("lowered")
            if abs(di) > incl_deg:
                kinds.append("plane change")
            if kinds:
                out.append({"norad": int(norad), "name": names.get(int(norad)), "kinds": kinds, "from": a[0], "to": b[0], "days": round(days, 2),
                            "perigee": [round(per_a, 1), round(per_b, 1)], "apogee": [round(apo_a, 1), round(apo_b, 1)],
                            "inclination": [a[3], b[3]], "amateur": bool(amateur),
                            "limits": [round(raise_km, 2), round(drop_km, 2), round(incl_deg, 3)]})
    out.sort(key=lambda m: -m["to"])
    return out
