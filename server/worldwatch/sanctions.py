"""Sanctioned and shadow-fleet ships, and sanctioned aircraft, from OpenSanctions' bulk files (free for
non-commercial use, no key; CC BY-NC 4.0), matched against the ships and aircraft our feeds see right now.

- Ships: the "maritime" collection (5 MB CSV, ~21,000 vessels). Kept: vessels tagged "sanction" (on a sanctions
  list) or "mare.shadow" (listed as part of a shadow fleet). Port-state detentions alone are left out. Matched by IMO
  number (the hull's lifelong number) first, MMSI (the radio number, can be reassigned) second.
- Aircraft: the "Airplane" entities of the full sanctions file (79 MB CSV, read row by row, ~340 aircraft). They are
  listed by registration and serial number. Registrations are matched against aircraft feeds that report them
  (adsb.fi / adsb.lol), and turned into transponder addresses with hexdb.io where it knows them, so the worldwide
  OpenSky feed (addresses only) can be matched too.
"""
import csv
import io
import re

MARITIME = "https://data.opensanctions.org/datasets/latest/maritime/maritime.csv"
TARGETS = "https://data.opensanctions.org/datasets/latest/sanctions/targets.simple.csv"
RISK_WORDS = {"sanction": "on a sanctions list", "mare.shadow": "listed as part of a shadow fleet", "mare.detained": "detained by a port state",
              "poi": "person or entity of interest", "reg.warn": "regulator's warning", "sanction.linked": "linked to a sanctioned party"}
REG = re.compile(r"^(?=.*[A-Z])[A-Z0-9]{1,2}-?[A-Z0-9]{2,5}$")


def norm_reg(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def parse_maritime(text: str) -> dict:
    by_imo, by_mmsi = {}, {}
    for r in csv.DictReader(io.StringIO(text)):
        if r.get("type") != "VESSEL":
            continue
        risk = [t for t in (r.get("risk") or "").split(";") if t]
        if not ({"sanction", "mare.shadow"} & set(risk)):
            continue
        rec = [r.get("caption"), risk, [d for d in (r.get("datasets") or "").split(";") if d], r.get("url"), (r.get("flag") or "").upper() or None]
        imo = re.sub(r"\D", "", r.get("imo") or "")
        if imo:
            by_imo[imo] = rec
        for m in (r.get("mmsi") or "").split(";"):
            m = re.sub(r"\D", "", m)
            if len(m) == 9:
                by_mmsi[m] = rec
    return {"imo": by_imo, "mmsi": by_mmsi}


def parse_planes(lines) -> list[dict]:
    """From the targets file, row by row (the file is large): only aircraft."""
    out = []
    for r in csv.DictReader(lines):
        if r.get("schema") != "Airplane":
            continue
        tokens = {norm_reg(t) for f in ("name", "aliases", "identifiers") for t in (r.get(f) or "").split(";")}
        regs = sorted({t for t in (r.get(f) or "" for f in ("name", "aliases", "identifiers")) for t in t.split(";") if REG.match(t.strip().upper())})
        out.append({"id": r.get("id"), "name": r.get("name"), "regs": regs, "tokens": sorted(t for t in tokens if len(t) >= 4 and re.search(r"[A-Z]", t)),
                    "sanctions": (r.get("sanctions") or "")[:400], "lists": [d for d in (r.get("dataset") or "").split(";") if d][:8],
                    "countries": r.get("countries") or None, "url": "https://www.opensanctions.org/entities/" + (r.get("id") or "")})
    return out


def match_ships(ships: list[dict], lists: dict) -> list[dict]:
    out = []
    for s in ships:
        imo = str(s.get("imo") or "").strip()
        rec, by = (lists["imo"].get(imo), "IMO") if imo and imo != "0" else (None, None)
        if not rec:
            rec, by = lists["mmsi"].get(str(s.get("mmsi"))), "MMSI"
        if rec:
            out.append({"kind": "ship", "id": "sship:" + str(s["mmsi"]), "mmsi": s["mmsi"], "imo": imo or None, "name": s.get("name") or rec[0], "listed_as": rec[0],
                        "lat": s["lat"], "lon": s["lon"], "time": s.get("time"), "speed_kn": s.get("speed_kn"), "destination": s.get("destination"),
                        "ship_kind": s.get("kind"), "risk": rec[1], "lists": rec[2], "url": rec[3], "flag_listed": rec[4], "matched_by": by})
    return out


def match_planes(aircraft: list[dict], planes: list[dict], hexes: dict) -> list[dict]:
    """aircraft: positions with hex (+ reg when the feed has it); hexes: registration -> address from hexdb.io."""
    by_token, by_hex = {}, {}
    for p in planes:
        for t in p["tokens"]:
            by_token.setdefault(t, p)
        for r in p["regs"]:
            h = hexes.get(norm_reg(r))
            if h:
                by_hex[h.lower()] = (p, r)
    out, seen = [], set()
    for a in aircraft:
        hit, by = None, None
        if a.get("reg") and norm_reg(a["reg"]) in by_token:
            hit, by = by_token[norm_reg(a["reg"])], f"registration {a['reg']}"
        elif (a.get("hex") or "").lower() in by_hex:
            hit, r = by_hex[a["hex"].lower()]
            by = f"transponder address of {r} (hexdb.io)"
        if hit and a["hex"] not in seen:
            seen.add(a["hex"])
            out.append({"kind": "aircraft", "id": "splane:" + a["hex"], "hex": a["hex"], "name": a.get("flight") or a.get("reg") or hit["name"], "listed_as": hit["name"],
                        "reg": a.get("reg"), "lat": a["lat"], "lon": a["lon"], "time": a.get("time"), "alt_ft": a.get("alt_ft"), "type": a.get("type"),
                        "sanctions": hit["sanctions"], "lists": hit["lists"], "url": hit["url"], "matched_by": by})
    return out
