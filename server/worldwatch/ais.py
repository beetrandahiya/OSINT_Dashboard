"""Ships worldwide from aisstream.io, a free service that relays AIS radio messages from volunteer receivers.

It is a live stream (a websocket), not a file to fetch, so it runs as its own background task: one connection
for the whole world, kept open, reconnecting after a pause if it drops. Every position report updates that
ship's entry; ships not heard from for 30 minutes are dropped. The key comes from data/aisstream-key.txt or
WW_AISSTREAM_KEY and is sent only to aisstream.io. aisstream.io does not allow browsers to connect directly,
which is why this lives on the server.

Coverage depends on where volunteers run receivers: dense along coasts and busy shipping lanes, thin or
empty in the open ocean (satellite AIS is a paid product).
"""
import asyncio
import json
import math
from array import array
import os
import time

from . import config

URL = "wss://stream.aisstream.io/v0/stream"
KEEP = 7200            # seconds a ship stays listed after its last position (moored ships report every few minutes, but
                       # volunteer receivers come and go; two hours keeps the map steadier, and each ship shows its age)
TRAIL_POINTS = 30      # positions kept per ship for its path: compact float arrays, at least 1 km or 15 minutes apart
MAX_SHIPS = 60000      # hard cap, so a flood of messages cannot eat the memory budget

TYPES = {30: "Fishing vessel", 31: "Tug", 32: "Tug", 33: "Dredger", 35: "Military vessel", 36: "Sailing vessel", 37: "Pleasure craft",
         50: "Pilot vessel", 51: "Search and rescue vessel", 52: "Tug", 53: "Port tender", 55: "Law enforcement vessel", 58: "Medical transport"}


def kind(code):
    if not code:
        return None
    return TYPES.get(code) or {4: "High-speed craft", 6: "Passenger ship", 7: "Cargo ship", 8: "Tanker"}.get(code // 10)


def key() -> str | None:
    if os.environ.get("WW_AISSTREAM_KEY"):
        return os.environ["WW_AISSTREAM_KEY"].strip()
    f = config.DATA / "aisstream-key.txt"
    return (f.read_text().strip() or None) if f.exists() else None


class Stream:
    def __init__(self):
        # mmsi -> [lon, lat, speed_kn, course, heading, status, time]   (lists, not dicts: tens of thousands of these)
        self.pos: dict[int, list] = {}
        # mmsi -> [name, type code, destination, callsign, imo, draught]
        self.static: dict[int, list] = {}
        # mmsi -> array('f', [lon, lat, minutes since start, ...]): the ship's recent path
        self.trails: dict[int, array] = {}
        self.t0 = time.time()
        self.state = "off"            # off | connecting | live | failing
        self.error = None
        self.connected_at = None
        self.messages = 0
        self.last_message = None
        self._task = None

    def start(self):
        if key() and not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _run(self):
        import websockets
        pause = 5
        while True:
            k = key()
            if not k:
                self.state, self.error = "off", None
                await asyncio.sleep(60)
                continue
            self.state, self.connected_at = "connecting", None
            try:
                async with websockets.connect(URL, open_timeout=20, ping_interval=30, max_size=2 ** 20) as ws:
                    # aisstream wants the subscription within 3 seconds of connecting
                    await ws.send(json.dumps({"APIKey": k, "BoundingBoxes": [[[-90, -180], [90, 180]]],
                                              "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport", "ShipStaticData"]}))
                    self.state, self.error, self.connected_at, pause = "live", None, time.time(), 5
                    last_prune = time.time()
                    async for raw in ws:
                        self._take(raw)
                        if time.time() - last_prune > 60:
                            self._prune()
                            last_prune = time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                text = str(e)
                self.state = "failing"
                quick = self.connected_at and time.time() - self.connected_at < 15 and self.messages == 0
                if "401" in text or "nauthor" in text or "API Key" in text or quick:
                    # aisstream does not send an error for a bad key: it accepts the connection, then drops it
                    self.error = "aisstream.io closed the connection right after the key was sent; the key is probably wrong"
                else:
                    self.error = f"{type(e).__name__}: {text[:120]}"
            await asyncio.sleep(pause)
            pause = min(300, pause * 2)          # back off up to five minutes

    def _take(self, raw):
        try:
            m = json.loads(raw)
        except ValueError:
            return
        if "error" in m:                          # aisstream reports a bad key or subscription this way
            raise RuntimeError(m["error"])
        kind_ = m.get("MessageType")
        meta, body = m.get("MetaData") or {}, (m.get("Message") or {}).get(kind_) or {}
        mmsi = meta.get("MMSI") or body.get("UserID")
        if not mmsi:
            return
        self.messages += 1
        self.last_message = time.time()
        if kind_ in ("PositionReport", "StandardClassBPositionReport"):
            lat, lon = body.get("Latitude", meta.get("latitude")), body.get("Longitude", meta.get("longitude"))
            if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
                return                            # 91/181 mean "not available" in AIS
            heading = body.get("TrueHeading")
            course = body.get("Cog")
            self.pos[mmsi] = [round(lon, 5), round(lat, 5), body.get("Sog"), course if course is not None and course < 360 else None,
                              heading if heading is not None and heading < 360 else None, body.get("NavigationalStatus"), time.time()]
            self._trail(mmsi, lon, lat)
            if mmsi not in self.static and meta.get("ShipName"):
                self.static[mmsi] = [meta["ShipName"].strip() or None, None, None, None, None, None]
            if len(self.pos) > MAX_SHIPS:
                self._prune(force=True)
        elif kind_ == "ShipStaticData":
            dims = body.get("Dimension") or {}
            self.static[mmsi] = [(body.get("Name") or meta.get("ShipName") or "").strip() or None, body.get("Type"),
                                 (body.get("Destination") or "").strip() or None, (body.get("CallSign") or "").strip() or None,
                                 body.get("ImoNumber") or None, body.get("MaximumStaticDraught") or None]
            if dims:
                self.static[mmsi].append((dims.get("A") or 0) + (dims.get("B") or 0) or None)

    def _trail(self, mmsi, lon, lat):
        tr = self.trails.get(mmsi)
        mins = (time.time() - self.t0) / 60
        if tr is not None and len(tr) >= 3:
            dx = (lon - tr[-3]) * math.cos(math.radians(lat)) * 111.2
            dy = (lat - tr[-2]) * 111.2
            if dx * dx + dy * dy < 1.0 and mins - tr[-1] < 15:
                return
        if tr is None:
            tr = self.trails[mmsi] = array("f")
        tr.extend((lon, lat, mins))
        if len(tr) > TRAIL_POINTS * 3:
            del tr[:3]

    def trail(self, mmsi: int) -> list:
        tr = self.trails.get(mmsi)
        if not tr:
            return []
        return [[round(tr[i], 5), round(tr[i + 1], 5), round(self.t0 + tr[i + 2] * 60)] for i in range(0, len(tr), 3)]

    def _prune(self, force=False):
        cut = time.time() - KEEP
        for k in [k for k, v in self.pos.items() if v[6] < cut]:
            del self.pos[k]
        if force and len(self.pos) > MAX_SHIPS:  # still too many: drop the oldest tenth
            for k, _ in sorted(self.pos.items(), key=lambda kv: kv[1][6])[: len(self.pos) // 10]:
                del self.pos[k]
        for k in [k for k in self.static if k not in self.pos]:
            del self.static[k]
        for k in [k for k in self.trails if k not in self.pos]:
            del self.trails[k]

    def ships(self):
        out, cut = [], time.time() - KEEP
        for mmsi, p in self.pos.items():
            if p[6] < cut:
                continue
            st = self.static.get(mmsi) or [None] * 6
            out.append({"mmsi": mmsi, "lon": p[0], "lat": p[1], "speed_kn": p[2], "course": p[3], "heading": p[4], "status": p[5], "time": p[6],
                        "name": st[0], "kind": kind(st[1]), "destination": st[2], "callsign": st[3], "imo": st[4],
                        "draught_m": st[5], "length_m": st[6] if len(st) > 6 else None, "source": "aisstream.io"})
        return out

    def status(self):
        return {"state": self.state, "error": self.error, "ships": len(self.pos), "messages": self.messages,
                "connected_at": self.connected_at, "last_message": self.last_message, "key": bool(key())}


stream = Stream()
