"""Official travel advice per country, for the country dossier.

- US State Department travel advisories (RSS, https://travel.state.gov/_res/rss/TAsTWs.xml): four levels,
  1 "Exercise Normal Precautions" to 4 "Do Not Travel", with the date each advisory was last issued.
  Each item names its country by a link code (mostly ISO alpha-3) and a "Country-Tag" in FIPS 10-4.
- German Foreign Office (Auswaertiges Amt) open data (https://www.auswaertiges-amt.de/opendata/travelwarning):
  per country whether a travel warning (Reisewarnung) or a partial one is in force, and "situation" warnings,
  with the date the advice was last changed. ISO alpha-2 codes.
Nothing is scored or combined: each office's own words and level are shown as they publish them.
"""
import html
import re
from email.utils import parsedate_to_datetime

from . import geo

US_URL = "https://travel.state.gov/_res/rss/TAsTWs.xml"
DE_URL = "https://www.auswaertiges-amt.de/opendata/travelwarning"
_US_SPECIAL = {"XGZ": "PS", "XWB": "PS", "XKS": "XK", "XQX": "NL", "BES": "NL", "GLP": "FR", "MTQ": "FR", "GUF": "FR"}


def parse_us(xml: str) -> dict:
    out = {}
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        title = html.unescape(re.search(r"<title>(.*?)</title>", it, re.S).group(1).strip())
        link = (re.search(r"<link>(.*?)</link>", it, re.S) or [None, ""])[1].strip()
        m = re.search(r"Level (\d)", title)
        if not m:
            continue
        code = re.search(r"destination\.(\w+)\.html", link)
        code = code.group(1).upper() if code else None
        tag = re.search(r'domain="Country-Tag">(\w+)<', it)
        iso = _US_SPECIAL.get(code) or geo.by_iso3(code) or (geo.by_fips(tag.group(1)) if tag else None) or geo.by_name(title.split(" - ")[0])
        if not iso:
            continue
        try:
            issued = parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", it).group(1).strip() + " 00:00:00 +0000").timestamp()
        except Exception:
            issued = None
        entry = {"area": title.split(" - ")[0].strip(), "level": int(m.group(1)), "title": title, "link": link, "issued": issued}
        out.setdefault(iso, []).append(entry)
    for v in out.values():
        v.sort(key=lambda e: -e["level"])
    return out


def parse_de(d: dict) -> dict:
    out = {}
    for k, v in (d.get("response") or {}).items():
        if not isinstance(v, dict) or not v.get("countryCode"):
            continue
        iso = v["countryCode"].upper()
        kinds = [label for key, label in (("warning", "travel warning (Reisewarnung) for the whole country"),
                                          ("partialWarning", "travel warning for parts of the country"),
                                          ("situationWarning", "warning because of the current situation"),
                                          ("situationPartWarning", "warning for parts, because of the current situation")) if v.get(key)]
        out.setdefault(iso, []).append({"id": k, "title": v.get("title"), "name": v.get("countryName"), "kinds": kinds,
                                        "changed": v.get("lastModified"), "effective": v.get("effective"),
                                        "link": f"https://www.auswaertiges-amt.de/opendata/travelwarning/{k}"})
    return out
