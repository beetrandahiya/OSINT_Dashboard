"""Public cameras: only cameras their operators publish openly for everyone (road and traffic authorities), never
private or unsecured cameras. Camera lists are read once a day; the picture is fetched when a card opens.

Sources (all without a key):
- London: Transport for London JamCams (open data, "Powered by TfL Open Data"); a still and a short video clip.
- New York City: NYC DOT traffic cameras (webcams.nyctmc.org).
- California: Caltrans CCTV, one list per district (12); still image, and a live stream (HLS, plays in Safari).
- Singapore: Land Transport Authority traffic images via data.gov.sg (Singapore Open Data Licence).
- Hong Kong: Transport Department traffic snapshots (DATA.GOV.HK).
- Finland: Fintraffic road weather cameras via Digitraffic (CC BY 4.0), several views per station.
"""
import html
import re

SOURCES = {
    "tfl": ("Transport for London", "https://tfl.gov.uk/traffic/status/"),
    "nyc": ("NYC DOT", "https://webcams.nyctmc.org"),
    "caltrans": ("Caltrans", "https://cwwp2.dot.ca.gov"),
    "sg": ("Land Transport Authority, Singapore", "https://data.gov.sg"),
    "hk": ("Transport Department, Hong Kong", "https://data.gov.hk"),
    "fi": ("Fintraffic (Digitraffic)", "https://www.digitraffic.fi"),
}
IMAGE_HOSTS = re.compile(r"^https://(s3-eu-west-1\.amazonaws\.com/jamcams\.tfl\.gov\.uk/|webcams\.nyctmc\.org/api/cameras/|cwwp2\.dot\.ca\.gov/data/"
                         r"|images\.data\.gov\.sg/api/traffic-images/|tdcctv\.data\.one\.gov\.hk/|weathercam\.digitraffic\.fi/)[\w./%-]+$")


def tfl(d: list) -> list:
    out = []
    for x in d:
        p = {a["key"]: a["value"] for a in x.get("additionalProperties", [])}
        if p.get("available") == "false" or not p.get("imageUrl"):
            continue
        out.append({"id": "tfl:" + x["id"], "src": "tfl", "name": x.get("commonName"), "lat": x["lat"], "lon": x["lon"],
                    "img": [p["imageUrl"]], "video": p.get("videoUrl"), "view": (p.get("view") or "").replace("\\/", "/") or None})
    return out


def nyc(d: list) -> list:
    return [{"id": "nyc:" + x["id"], "src": "nyc", "name": x.get("name"), "lat": x["latitude"], "lon": x["longitude"], "img": [x["imageUrl"]],
             "area": x.get("area")} for x in d if str(x.get("isOnline")).lower() == "true" and x.get("imageUrl")]


def caltrans(d: dict) -> list:
    out = []
    for row in d.get("data", []):
        c = row.get("cctv", {})
        if str(c.get("inService")).lower() != "true":
            continue
        loc, im = c.get("location", {}), c.get("imageData", {})
        url = (im.get("static") or {}).get("currentImageURL")
        try:
            lat, lon = float(loc["latitude"]), float(loc["longitude"])
        except (KeyError, ValueError, TypeError):
            continue
        if not url:
            continue
        out.append({"id": f"ca:{loc.get('district')}:{c.get('index')}", "src": "caltrans", "name": loc.get("locationName"), "lat": lat, "lon": lon,
                    "img": [url], "video": im.get("streamingVideoURL") or None, "view": loc.get("direction"), "area": loc.get("nearbyPlace")})
    return out


def singapore(d: dict) -> list:
    items = d.get("items") or [{}]
    return [{"id": "sg:" + c["camera_id"], "src": "sg", "name": f"Camera {c['camera_id']}", "lat": c["location"]["latitude"], "lon": c["location"]["longitude"],
             "img": [c["image"]], "taken": c.get("timestamp")} for c in items[0].get("cameras", [])]


def hongkong(xml: str) -> list:
    out = []
    for block in re.findall(r"<image>(.*?)</image>", xml, re.S):
        g = lambda t: html.unescape((re.search(rf"<{t}>(.*?)</{t}>", block, re.S) or [None, ""])[1]).strip()
        try:
            out.append({"id": "hk:" + g("key"), "src": "hk", "name": g("description"), "lat": float(g("latitude")), "lon": float(g("longitude")),
                        "img": [g("url")], "area": g("district")})
        except ValueError:
            continue
    return out


def finland(d: dict) -> list:
    out = []
    for f in d.get("features", []):
        p = f.get("properties", {})
        presets = [x["id"] for x in p.get("presets", []) if x.get("inCollection")]
        if p.get("collectionStatus") != "GATHERING" or not presets:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        out.append({"id": "fi:" + p["id"], "src": "fi", "name": (p.get("name") or "").replace("_", " "), "lat": lat, "lon": lon,
                    "img": [f"https://weathercam.digitraffic.fi/{x}.jpg" for x in presets]})
    return out
