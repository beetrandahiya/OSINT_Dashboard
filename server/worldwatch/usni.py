"""Where the US Navy's aircraft carriers and amphibious assault ships are, from USNI News' weekly Fleet and Marine
Tracker (read through its RSS feed). USNI gives a region or a port per ship, from Navy and public reports, not
coordinates. We place each ship at the centre of that region or at that port and say so: the marker is "somewhere in
the Arabian Sea", not a position. USNI's own map graphic is shown in the card.
"""
import html
import re
import time
from email.utils import parsedate_to_datetime

FEED = "https://news.usni.org/category/fleet-tracker/feed"

# Ports first (exact places), then sea regions (rough centres, chosen by hand and labelled approximate).
PORTS = {"yokosuka": (35.29, 139.66), "sasebo": (33.16, 129.72), "white beach": (26.30, 127.91), "okinawa": (26.30, 127.91),
         "san diego": (32.68, -117.13), "north island": (32.70, -117.20), "norfolk": (36.95, -76.33), "pearl harbor": (21.35, -157.95),
         "bremerton": (47.56, -122.64), "everett": (47.98, -122.22), "guam": (13.44, 144.66), "apra": (13.44, 144.66), "bahrain": (26.20, 50.61),
         "manama": (26.20, 50.61), "rota": (36.62, -6.35), "souda bay": (35.49, 24.14), "naples": (40.84, 14.26), "phuket": (7.90, 98.40),
         "busan": (35.10, 129.04), "manila": (14.58, 120.97), "subic": (14.80, 120.28), "singapore": (1.30, 103.80), "changi": (1.30, 103.98),
         "mayport": (30.39, -81.41), "newport news": (36.98, -76.43), "duqm": (19.67, 57.70), "split": (43.50, 16.44), "limassol": (34.67, 33.04),
         "marseille": (43.30, 5.37), "toulon": (43.11, 5.92), "portsmouth": (50.80, -1.11), "oslo": (59.90, 10.74), "halifax": (44.64, -63.57)}
REGIONS = {"philippine sea": (20, 130), "south china sea": (13, 114), "east china sea": (29, 125), "sea of japan": (40, 135),
           "western pacific": (15, 140), "eastern pacific": (15, -115), "pacific ocean": (20, -150), "pacific": (20, -150), "coral sea": (-17, 155),
           "caribbean": (15, -72), "gulf of mexico": (25, -90), "western atlantic": (33, -68), "eastern atlantic": (40, -20), "north atlantic": (52, -30),
           "atlantic": (33, -45), "norwegian sea": (68, 5), "north sea": (56, 3), "baltic": (57, 19), "eastern mediterranean": (34, 30),
           "mediterranean": (36, 18), "adriatic": (42.5, 16), "ionian sea": (38, 19), "aegean": (38.5, 25), "red sea": (20, 38.5),
           "gulf of aden": (12.5, 47), "arabian sea": (16, 62), "gulf of oman": (24.5, 58.5), "persian gulf": (27, 51), "arabian gulf": (27, 51),
           "indian ocean": (-5, 75), "bay of bengal": (15, 88), "japan": (35.29, 139.66), "thailand": (7.90, 98.40), "guam": (13.44, 144.66)}
CAPITAL = re.compile(r"USS\s+([A-Z][\w.'\s]+?)\s*\((CVN|LHA|LHD)[-\u2011\u2013]\s?(\d+)\)")
STATUS = re.compile(r"\b(is in port|in port in|is operating|are operating|operating in|is in the|transit|arrived|departed|pulled into|is underway|returned|is moored|anchored|left)", re.I)


def _text(fragment: str) -> str:
    t = re.sub(r"<(h\d|p|li|figcaption)[^>]*>", "\n", fragment)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\s+([),.])", r"\1", re.sub(r"\(\s+", "(", t)).strip()


def _where(name: str):
    n = name.lower()
    for k, v in PORTS.items():
        if k in n:
            return v, k, "port"
    for k, v in REGIONS.items():
        if k in n:
            return v, k, "region"
    return None, None, None


def parse(xml: str) -> dict:
    item = re.search(r"<item>(.*?)</item>", xml, re.S).group(1)
    title = html.unescape(re.search(r"<title>(.*?)</title>", item).group(1))
    link = re.search(r"<link>(.*?)</link>", item).group(1)
    published = parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", item).group(1)).timestamp()
    content = re.search(r"<content:encoded><!\[CDATA\[(.*?)\]\]>", item, re.S).group(1)
    graphic = (re.findall(r'<img[^>]+src="([^"]+)"', content) or [None])[0]
    # cut into sections at the "In the ..." headings; strike-group headings stay with the region before them
    parts = re.split(r"<h\d[^>]*>(.*?)</h\d>", content)
    sections, region = [], None
    for i in range(1, len(parts), 2):
        head = _text(parts[i])
        if head.lower().startswith("in "):
            region = head[3:].strip()
        sections.append((region, _text(parts[i + 1]) if i + 1 < len(parts) else ""))
    ships = {}
    for region, text in sections:
        if not region:
            continue
        sentences = [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])|\n+", text) if x.strip()]
        for m in CAPITAL.finditer(text):
            hull = f"{m.group(2)}-{m.group(3)}"
            if hull in ships:
                continue
            # status sentences only (photo captions name ships too, but say where a picture was taken, not where it is)
            said = [x.strip() for x in sentences if (hull in x or m.group(1).strip() in x) and STATUS.search(x) and not re.search(r"\bphoto\b|\bdated\b", x, re.I)][:4]
            port = None
            for x in said:
                if re.search(r"\bdeparted|\bleft\b|\bunderway\b", x, re.I):
                    break                                   # it has left port: placed by its region
                pm = re.search(r"(?:in port in|pulled into|pulls into|arrived (?:in|at)|moored (?:in|at)|in port at|returned (?:\w+ )?to(?: its homeport of)?) ([A-Z][\w ,.'-]{2,60})", x)
                if pm:
                    port = pm.group(1)
                    break
            if port:
                port = re.split(r",? (?:on|Oct|Sept?|Nov|Dec|Jan|Feb|March|April|May|June|July|Aug)\b", port)[0].strip(" .,")
            at, key, kind = _where(port) if port else (None, None, None)
            if not at:
                at, key, kind = _where(region)
            ships[hull] = {"name": "USS " + m.group(1).strip(), "hull": hull, "kind": "aircraft carrier" if m.group(2) == "CVN" else "amphibious assault ship",
                           "region": region, "port": port.strip(" .,") if port else None, "lat": at[0] if at else None, "lon": at[1] if at else None,
                           "placed": kind, "said": said}
    return {"title": title, "link": link, "published": published, "graphic": graphic, "ships": list(ships.values())}
