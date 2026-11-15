"""Internet routing incidents and outage notes from Cloudflare Radar (free API token in data/cloudflare-token.txt;
data CC BY-NC 4.0, private use with credit).

- BGP hijacks: a network announcing address blocks that belong to another network. Cloudflare scores each event by
  the evidence it found (tags such as "RPKI says the new origin is invalid", "the routing registry says so"); the
  score is the sum of those tag scores. We keep the last 24 hours, every score, and list 10 and above.
- Route leaks: a network passing on routes it should not (often by mistake). About 400 a day; we keep the 40 that
  involve the most address blocks and cross a border.
- Outage annotations: Cloudflare's own written notes on outages, with a cause (power outage, military action, cable
  cut, government-directed shutdown...) and the countries / regions / networks affected.
"""
import time
from datetime import datetime, timezone

API = "https://api.cloudflare.com/client/v4/radar/"
TAG_WORDS = {"rpki_new_origin_invalid": "RPKI (the signed record of who may announce these addresses) says the new origin is not allowed",
             "rpki_old_origin_valid": "RPKI says the previous origin was the allowed one",
             "irr_new_origin_invalid": "the routing registries (IRR) do not list the new origin",
             "irr_old_origin_valid": "the routing registries list the previous origin",
             "sibling_asn": "the two networks look related (same organisation)", "dps_asn": "the new origin is a DDoS-protection service"}
CAUSE = {"POWER_OUTAGE": "power outage", "MILITARY_ACTION": "military action", "CABLE_CUT": "cable cut", "GOVERNMENT_DIRECTED": "ordered by a government",
         "TECHNICAL_PROBLEM": "technical problem", "MAINTENANCE": "maintenance", "NATURAL_DISASTER": "natural disaster", "WEATHER": "weather",
         "FIRE": "fire", "CYBERATTACK": "cyberattack", "UNKNOWN": "cause not known"}


def ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except ValueError:
        return None


def hijacks(result: dict, places: dict) -> list[dict]:
    orgs = {a["asn"]: a for a in result.get("asn_info", [])}
    out = []
    for e in result.get("events", []):
        def net(asn):
            a = orgs.get(asn, {})
            return {"asn": asn, "org": a.get("org_name"), "cc": a.get("country_code")}
        hc = e.get("hijacker_country")
        victims = [net(a) for a in e.get("victim_asns", [])]
        vcc = [c for c in e.get("victim_countries", []) if c]
        out.append({"id": e["id"], "start": ts(e.get("min_hijack_ts")), "last": ts(e.get("max_hijack_ts")), "duration_s": e.get("duration"),
                    "ongoing": bool(e.get("on_going_count")), "stale": e.get("is_stale"), "score": e.get("confidence_score"),
                    "evidence": [TAG_WORDS.get(t["name"], t["name"]) for t in e.get("tags", []) if t.get("score", 0) > 0],
                    "hijacker": {**net(e.get("hijacker_asn")), "cc": hc, "at": places.get(hc)}, "victims": victims,
                    "victim_countries": [{"cc": c, "at": places.get(c)} for c in dict.fromkeys(vcc)],
                    "prefixes": e.get("prefixes", [])[:8], "prefix_count": len(e.get("prefixes", [])), "seen_by_peers": e.get("peer_ip_count"),
                    "messages": e.get("hijack_msgs_count")})
    return out


def leaks(result: dict, places: dict, keep=40) -> list[dict]:
    orgs = {a["asn"]: a for a in result.get("asn_info", [])}
    out = []
    for e in result.get("events", []):
        cs = [c for c in dict.fromkeys(e.get("countries", [])) if c]
        if len(cs) < 2:
            continue
        out.append({"id": e["id"], "start": ts(e.get("min_ts")), "last": ts(e.get("max_ts")), "finished": e.get("finished"),
                    "leaker": {"asn": e.get("leak_asn"), "org": orgs.get(e.get("leak_asn"), {}).get("org_name")},
                    "path": [{"asn": a, "org": orgs.get(a, {}).get("org_name"), "cc": orgs.get(a, {}).get("country_code")} for a in e.get("leak_seg", [])],
                    "countries": [{"cc": c, "at": places.get(c)} for c in cs], "prefixes": e.get("prefix_count"), "origins": e.get("origin_count")})
    out.sort(key=lambda x: -(x["prefixes"] or 0))
    return out[:keep]


def outages(result: dict, places: dict, since: float) -> list[dict]:
    out = []
    for a in result.get("annotations", []):
        start, end = ts(a.get("startDate")), ts(a.get("endDate"))
        if (end or time.time()) < since:
            continue
        o = a.get("outage") or {}
        regions = [x.get("entityName") for x in a.get("entities", []) if x.get("entityType") == "GEOLOCATION"]
        countries = [{"cc": l["code"], "name": l.get("name"), "at": places.get(l["code"])} for l in a.get("locationsDetails", []) if l.get("code")]
        out.append({"id": a["id"], "text": a.get("description"), "cause": CAUSE.get(o.get("outageCause"), (o.get("outageCause") or "").lower().replace("_", " ") or None),
                    "cause_code": o.get("outageCause"), "scope": (o.get("outageType") or "").lower() or None, "start": start, "end": end,
                    "countries": countries, "regions": regions, "networks": [f'{x.get("name") or ""} (AS{x.get("asn")})'.strip() for x in a.get("asnsDetails", [])][:6],
                    "link": a.get("linkedUrl")})
    out.sort(key=lambda x: -(x["start"] or 0))
    return out
