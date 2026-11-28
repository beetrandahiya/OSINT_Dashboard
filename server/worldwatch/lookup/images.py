"""Pictures in a case: picture files the owner uploads as a seed, and the profile pictures found accounts show.

What happens with them, and what never does:
- A picture is compared only as a file: a 64-bit difference hash (computed in the browser) says whether two
  files are the same picture, resized or recompressed. That is picture-copy matching. There is no face
  recognition here, no face-search engine is asked or linked, and nothing guesses who is in a picture.
- Location metadata (GPS EXIF) is only detected, never read: a picture that carries it is reported as
  "carries location metadata". The coordinates are not parsed, stored, shown or put on a map.
- Found pictures are fetched by this server only from addresses the case's own findings name (not an open
  proxy), only from public internet addresses (each redirect checked), only real image files, no SVG.
"""
import hashlib
import re
import struct
from urllib.parse import urljoin

import httpx

from . import enrich, store

MAX_UPLOAD = 5_000_000
MAX_FETCH = 3_000_000
TYPES = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}


def sniff(data: bytes) -> str | None:
    """The image type from the file's first bytes (never from its name or a header someone sent)."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _tiff_has_gps(t: bytes) -> bool:
    """Does this EXIF (TIFF) block have a GPS directory with entries? Only the directory's presence and size are
    read: no coordinate is decoded."""
    if len(t) < 8 or t[:2] not in (b"II", b"MM"):
        return False
    e = "<" if t[:2] == b"II" else ">"
    try:
        if struct.unpack(e + "H", t[2:4])[0] != 42:
            return False
        off = struct.unpack(e + "I", t[4:8])[0]
        n = struct.unpack(e + "H", t[off:off + 2])[0]
        for i in range(min(n, 512)):
            p = off + 2 + 12 * i
            tag = struct.unpack(e + "H", t[p:p + 2])[0]
            if tag == 0x8825:                                  # GPSInfo: a pointer to the GPS directory
                gps = struct.unpack(e + "I", t[p + 8:p + 12])[0]
                return struct.unpack(e + "H", t[gps:gps + 2])[0] > 0
    except (struct.error, IndexError):
        return False
    return False


def location_meta(data: bytes) -> bool:
    """True when the file carries location metadata (EXIF GPS directory, or GPS fields in XMP)."""
    kind = sniff(data)
    if kind == "jpg":
        i = 2
        while i + 4 <= len(data) and data[i] == 0xFF:
            marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            seg = data[i + 4:i + 2 + size]
            if marker == 0xE1 and seg[:6] == b"Exif\x00\x00" and _tiff_has_gps(seg[6:]):
                return True
            if marker == 0xE1 and seg.startswith(b"http://ns.adobe.com/xap/") and re.search(rb"GPS(Latitude|Longitude)", seg):
                return True
            if marker in (0xDA, 0xD9):                         # image data starts: no more metadata segments
                break
            i += 2 + size
        return False
    if kind == "png":
        i = 8
        while i + 8 <= len(data):
            size, ctype = struct.unpack(">I", data[i:i + 4])[0], data[i + 4:i + 8]
            body = data[i + 8:i + 8 + size]
            if ctype == b"eXIf" and _tiff_has_gps(body):
                return True
            if ctype == b"iTXt" and b"XML:com.adobe.xmp" in body[:40] and re.search(rb"GPS(Latitude|Longitude)", body):
                return True
            if ctype == b"IDAT":
                break
            i += 12 + size
        return False
    if kind == "webp":
        i = 12
        while i + 8 <= len(data):
            ctype, size = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
            body = data[i + 8:i + 8 + size]
            if ctype == b"EXIF" and _tiff_has_gps(body[6:] if body[:6] == b"Exif\x00\x00" else body):
                return True
            if ctype == b"XMP " and re.search(rb"GPS(Latitude|Longitude)", body):
                return True
            i += 8 + size + (size & 1)
        return False
    return False


def save_upload(data: bytes) -> dict:
    """Keep an uploaded seed picture as lookup-images/<sha256>.<ext>. Raises ValueError with the reason."""
    if len(data) > MAX_UPLOAD:
        raise ValueError(f"The picture is larger than {MAX_UPLOAD // 1_000_000} MB.")
    kind = sniff(data)
    if not kind:
        raise ValueError("That is not a JPEG, PNG, GIF or WebP picture.")
    name = hashlib.sha256(data).hexdigest() + "." + kind
    d = store.images_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    if not p.exists():
        p.write_bytes(data)
    return {"file": name, "bytes": len(data), "type": TYPES[kind], "location_meta": location_meta(data)}


def read_upload(name: str):
    if not re.fullmatch(r"[0-9a-f]{64}\.(jpg|png|gif|webp)", name or ""):
        return None
    p = store.images_dir() / name
    return (p.read_bytes(), TYPES[name.rsplit(".", 1)[1]]) if p.exists() else None


async def fetch(url: str):
    """(bytes, media type, has location metadata) of a found profile picture, or raise ValueError."""
    async with httpx.AsyncClient(timeout=12, follow_redirects=False, headers={"User-Agent": enrich.BROWSER}) as c:
        for _ in range(5):
            try:
                await enrich.check_url(url)
            except enrich.Refused as e:
                raise ValueError(str(e))
            async with c.stream("GET", url) as r:
                if not enrich._peer_ok(r, url):
                    raise ValueError("it connected to a private or local network address")
                if r.is_redirect and r.headers.get("location"):
                    url = urljoin(url, r.headers["location"])
                    continue
                if r.status_code != 200:
                    raise ValueError(f"answered {r.status_code}")
                body = b""
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_FETCH:
                        raise ValueError("larger than 3 MB")
                kind = sniff(body)
                if not kind:
                    raise ValueError("not a JPEG, PNG, GIF or WebP picture")
                return body, TYPES[kind], location_meta(body)
    raise ValueError("too many redirects")
