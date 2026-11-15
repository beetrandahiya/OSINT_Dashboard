"""Airspace closures and conflict-zone warnings worldwide.

No free feed carries every closure in the world (NOTAM services need accounts). What is free and official:
- EASA's Conflict Zone Information Bulletins (CZIBs): which flight regions European airlines are told to avoid
  or treat with caution, and why. Each bulletin's page names the flight regions by ICAO code.
- The FAA's list of prohibitions (SFARs) and international security notices (KICZ NOTAMs) per country.
- The FAA's temporary flight restrictions (TFRs) in the United States, with their exact shapes.

Flight regions are drawn with the VATSpy boundaries (VATSIM's community data, CC BY-SA 4.0): close to the real
ones but drawn by volunteers, and a bulletin often covers only part of a region (below a flight level, west of a
longitude). The card says so and quotes the bulletin.
"""
import html
import re
import time

EASA = "https://www.easa.europa.eu"
VATSPY = "https://raw.githubusercontent.com/vatsimnetwork/vatspy-data-project/master/Boundaries.geojson"
FIR = re.compile(r"\b([A-Z]{4})\b")
NOT_CODES = {"FROM", "WITH", "THAT", "THIS", "WEST", "EAST", "NORTH", "SOUTH", "ABOVE", "BELOW", "AREA", "NONE", "ONLY",
             "LAND", "OVER", "INTO", "THEIR", "THESE", "MUST", "SHALL", "ALSO", "PART", "EASA", "CZIB", "NOTAM", "KICZ",
             "SFAR", "IRAN", "IRAQ", "MALI", "OMAN", "GULF", "FIRS", "KYIV", "LVIV", "DONU", "ODESA", "UTC", "ICAO"}


def _text(fragment: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    t = re.sub(r"<(br|/p|/li|/div|/h\d)[^>]*>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t ]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def parse_czib_list(page: str) -> list[dict]:
    rows = re.findall(r'conflict-zone-up-date">\s*([\d/]+).*?conflict-zone-revdate">\s*([\d/]*).*?conflict-zone-until">\s*([\d/]*)'
                      r'.*?cz-title">(.*?)</div><div class="czib_number">(.*?)</div>.*?cz-status-(\w+)".*?href="(/en/domains/air-operations/czibs/[^"]+)"', page, re.S)
    out = []
    for issued, revised, until, title, number, status, link in rows:
        if status != "Active":
            continue
        out.append({"title": html.unescape(title).strip(), "number": html.unescape(number).strip(), "issued": issued,
                    "revised": revised or None, "valid_until": until or None, "link": EASA + link})
    return out


def parse_czib_page(page: str) -> dict:
    t = _text(page)
    def section(start, ends):
        i = t.find(start)
        if i < 0:
            return ""
        j = min([k for k in (t.find(e, i + len(start)) for e in ends) if k > 0] or [i + 3000])
        return t[i + len(start):j].strip()
    affected = section("Affected Airspace", ["Affected Countries", "Applicability"])
    advice = section("Recommendation(s)", ["Contact us", "Get notified"])
    codes = sorted({c for c in FIR.findall(affected + " " + advice) if c not in NOT_CODES})
    level = "avoid" if re.search(r"\bnot (to )?operate\b|should not|must not|prohibit", advice, re.I) else "caution"
    return {"affected": affected[:1500], "advice": advice[:2500], "firs": codes, "level": level}


def parse_faa(page: str) -> list[dict]:
    """Per country: the prohibitions and security notices listed on the FAA's page."""
    out = []
    names = {i: html.unescape(re.sub(r"<[^>]+>", "", n)).strip() for i, n in re.findall(r'<a href="#([^"]+)">(.*?)</a>', page, re.S)}
    body = page[page.find("Alphabetical List by Country"):]
    parts = re.split(r'<a class="ck-anchor" id="([^"]+)"></a>', body)
    # parts = [before, id1, chunk1, id2, chunk2, ...]; the country name is the text just before each anchor
    for k in range(1, len(parts) - 1, 2):
        name = names.get(parts[k], parts[k])
        chunk = parts[k + 1].split("Back to top")[0]
        docs = [(html.unescape(re.sub(r"<[^>]+>", "", t)).strip(), h) for h, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)]
        docs = [(t, h if h.startswith("http") else "https://www.faa.gov" + h) for t, h in docs if t]
        if not docs or name in ("United States", "Bahamas", "Canada"):
            continue
        prohibited = any("SFAR" in t or "Prohibition" in t for t, _ in docs)
        codes = sorted({c for t, _ in docs for c in re.findall(r"\(([A-Z]{4})\)", t) if c not in NOT_CODES})
        out.append({"country": name, "level": "prohibited" if prohibited else "notice", "firs": codes,
                    "docs": [{"title": t, "url": h} for t, h in docs][:12]})
    return out


def parse_tfr_xml(xml: str) -> dict | None:
    def num(v):
        v = v.strip()
        n = float(v[:-1])
        return -n if v[-1] in "SW" else n
    polys = []
    for area in re.findall(r"<abdMergedArea>(.*?)</abdMergedArea>", xml, re.S):
        pts = [[round(num(lo), 5), round(num(la), 5)] for la, lo in re.findall(r"<geoLat>([^<]+)</geoLat>\s*<geoLong>([^<]+)</geoLong>", area)]
        if len(pts) >= 3:
            polys.append(pts + ([pts[0]] if pts[0] != pts[-1] else []))
    name = re.search(r"<txtLocalName>([^<]*)", xml)
    text = re.search(r"<txtDescrUSNS>([^<]*)", xml)
    if not polys:
        return None
    return {"name": html.unescape(name.group(1)) if name else None, "text": html.unescape(text.group(1))[:1500] if text else None,
            "polys": polys}


def fir_shapes(geojson: dict, wanted: set[str]) -> dict[str, list]:
    """Polygon rings per wanted flight region. VATSpy sometimes splits a region into sectors (ORBB-N, ORBB-S);
    the region's own feature is used when it exists, otherwise its sectors together."""
    by_id: dict[str, list] = {}
    for f in geojson.get("features", []):
        fid = f["properties"].get("id", "")
        base = fid.split("-")[0]
        if base in wanted:
            g = f["geometry"]
            rings = [p[0] for p in g["coordinates"]] if g["type"] == "MultiPolygon" else [g["coordinates"][0]]
            by_id.setdefault(fid, []).extend(rings)
    out = {}
    for code in wanted:
        if code in by_id:
            out[code] = by_id[code]
        else:
            rings = [r for fid, rs in by_id.items() if fid.split("-")[0] == code for r in rs]
            if rings:
                out[code] = rings
    # thin out the rings: the boundaries file is detailed; a point every ~0.05 degrees is plenty at world scale
    for code, rings in out.items():
        out[code] = [[[round(x, 3), round(y, 3)] for x, y in r[::max(1, len(r) // 400)]] + [[round(r[0][0], 3), round(r[0][1], 3)]] for r in rings]
    return out


def now() -> float:
    return time.time()
