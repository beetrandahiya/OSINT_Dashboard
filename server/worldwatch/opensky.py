"""OpenSky Network's worldwide snapshot, cut down to what the map shows. Runs in the helper process (helper.py):
the answer is ~10,000 aircraft as lists of 17 values, several times bigger decoded than the part kept, so it is
decoded there and only the result comes back. Imports nothing heavy, so the helper starts fast."""
import json


def opensky_aircraft(raw: bytes) -> tuple[list[dict], float]:
    """/api/states/all -> (aircraft with a position, OpenSky's own time of the snapshot)."""
    d = json.loads(raw)
    ac = [{"hex": s[0], "flight": (s[1] or "").strip() or None, "lon": s[5], "lat": s[6],
           "alt_m": s[7], "on_ground": s[8], "gs_ms": s[9], "track": s[10], "last_contact": s[4]}
          for s in d.get("states") or [] if s[5] is not None and s[6] is not None]
    return ac, float(d["time"])
