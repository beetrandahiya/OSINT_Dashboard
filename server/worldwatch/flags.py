"""Which country a plane, ship or satellite belongs to, from the official allocations, never guessed from a name.

- Aircraft: the 24-bit transponder address is allocated to states in blocks (ICAO Annex 10, Vol. III). The table is
  read from tar1090's flags.js, which is generated from that annex. The country is the state of registry.
- Ships: the first three digits of an MMSI are the flag state's Maritime Identification Digits (ITU). The table is
  read from Wikidata (property P2979 on each country, with its ISO code P297).
- Satellites: CelesTrak's catalogue owner code per satellite (one request per satellite family), named with
  CelesTrak's own list of codes. Multinational owners are shown with each partner's flag where that is clear.
"""
import html
import json
import re
from pathlib import Path

_COUNTRIES = json.loads((Path(__file__).parent / "countries.json").read_text())   # ISO code -> [lon, lat, name]
_BY_NAME = {v[2].lower(): k for k, v in _COUNTRIES.items()}
_ALIAS = {"commonwealth of independent states (former ussr)": "RU", "cis": "RU", "people's republic of china": "CN", "prc": "CN",
          "united states": "US", "usa": "US", "united kingdom": "GB", "south korea": "KR", "republic of korea": "KR", "north korea": "KP",
          "russia": "RU", "iran": "IR", "taiwan": "TW", "vietnam": "VN", "czech republic": "CZ", "czechia": "CZ", "turkey": "TR", "türkiye": "TR",
          "bolivia": "BO", "venezuela": "VE", "laos": "LA", "syria": "SY", "moldova": "MD", "tanzania": "TZ", "ivory coast": "CI"}
# CelesTrak owner codes that are organisations: shown with the partners' flags (EU flag for European agencies)
ORG_FLAGS = {"ISS": ["US", "RU", "JP", "CA", "EU"], "ESA": ["EU"], "EUME": ["EU"], "EUTE": ["EU"], "ESRO": ["EU"], "SES": ["LU"], "IM": ["GB"],
             "AB": ["SA"], "NATO": ["NATO"], "ITSO": [], "ABS": ["HK"], "AC": ["HK"], "O3B": ["LU"], "ORB": ["US"], "GLOB": ["US"], "IRID": ["US"],
             "SPXS": ["US"], "SEAL": ["US"], "CHBZ": ["CN", "BR"], "FRIT": ["FR", "IT"], "RASC": ["RU"], "STCT": ["SG", "TW"]}


def iso(name: str) -> str | None:
    n = (name or "").strip().lower()
    return _ALIAS.get(n) or _BY_NAME.get(n)


def parse_icao(js: str) -> list[list]:
    out = []
    for start, end, country, cc in re.findall(r"start:\s*0x([0-9A-Fa-f]+),\s*end:\s*0x([0-9A-Fa-f]+),\s*country:\s*\"([^\"]+)\",\s*country_code:\s*\"(\w+)\"", js):
        out.append([int(start, 16), int(end, 16), cc.upper(), country])
    return sorted(out)


def parse_mid(rows: list[dict]) -> dict[str, list]:
    out = {}
    for x in rows:
        mid, cc, name = x["mid"]["value"], (x.get("iso", {}).get("value") or "").upper(), x["cLabel"]["value"]
        if re.fullmatch(r"\d{3}", mid) and (mid not in out or (cc and not out[mid][0])):
            out[mid] = [cc or None, name]
    return out


def parse_owner_codes(page: str) -> dict[str, list]:
    """CelesTrak's list of owner codes -> [flags, name]."""
    out = {}
    for code, name in re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", page, re.S):
        code = re.sub(r"<[^>]+>", "", code).strip()
        name = html.unescape(re.sub(r"<[^>]+>", "", name)).strip()
        if not code or not name:
            continue
        flags = ORG_FLAGS.get(code)
        if flags is None:
            cc = iso(name)
            flags = [cc] if cc else []
        out[code] = [flags, name]
    return out


def ucs_flags(country: str | None) -> list[str]:
    """UCS writes joint owners as 'USA/Japan' or 'Multinational'."""
    if not country:
        return []
    out = []
    for part in re.split(r"[/,]", country):
        cc = iso(part) or ({"esa": "EU", "europe": "EU", "eu": "EU"}.get(part.strip().lower()))
        if cc and cc not in out:
            out.append(cc)
    return out
