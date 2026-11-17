"""Runs every feed on its own timer and keeps an honest record of what happened.

A feed is in exactly one state:
  waiting  not fetched yet in this run (older saved data, if any, is shown with its real age)
  ok       the last fetch worked and the data is as fresh as this source can be
  late     the last fetch worked but the source's own timestamp is older than it should be
  failing  the last fetch failed; the last good data stays, with its age
"""
import asyncio
import random
import time

import httpx

from . import config, db
from .feeds import FEEDS, Feed, Fetcher


class FeedState:
    def __init__(self, feed: Feed):
        self.feed = feed
        self.payload = None
        self.fetched: float | None = None      # last good fetch, our clock
        self.from_disk = False                 # the data shown was saved by an earlier run
        self.data_time: float | None = None
        self.data_label: str | None = None
        self.items: int | None = None
        self.note: str | None = None
        self.tried: float | None = None        # last attempt, good or bad
        self.error: str | None = None
        self.ok_count = 0
        self.fail_count = 0
        self.fails_in_a_row = 0
        self.last_ms: int | None = None
        self.last_bytes: int | None = None
        self.total_bytes = 0
        self.next_at: float | None = None

    def state(self, now: float) -> str:
        if self.feed.fetch is None and self.error is None:
            return "ok"                      # on-request feeds are fine while nobody asks
        if self.tried is None:
            return "waiting"
        if self.error:
            return "failing"
        f = self.feed
        if f.stale_after and self.data_time and now - self.data_time > f.stale_after:
            return "late"
        return "ok"

    def public(self, now: float) -> dict:
        f = self.feed
        return {
            "name": f.name, "layer": f.layer, "source": f.source, "home": f.home, "interval": f.interval,
            "limit_note": f.limit_note, "state": self.state(now), "fetched": self.fetched, "from_disk": self.from_disk,
            "data_time": self.data_time, "data_label": self.data_label, "items": self.items, "note": self.note,
            "tried": self.tried, "error": self.error, "ok_count": self.ok_count, "fail_count": self.fail_count,
            "last_ms": self.last_ms, "last_bytes": self.last_bytes, "total_bytes": self.total_bytes, "next_at": self.next_at,
        }


class Collector:
    def __init__(self):
        self.started = time.time()
        self.states = {f.name: FeedState(f) for f in FEEDS}
        self._tasks: list[asyncio.Task] = []
        self._client: httpx.AsyncClient | None = None
        self.clock_diffs: list[float] = []
        self.trails: dict[str, list] = {}     # aircraft hex -> [(time, lon, lat, alt m), ...] as we received them (see _remember)
        self._full: dict[str, float] = {}     # hex -> when the military / Munich feed last had it (those trails are kept whole)
        self._pruned = 0.0

    async def start(self):
        for st in self.states.values():      # show what an earlier run saved, clearly marked
            saved = db.load_latest(st.feed.name) if st.feed.fetch else None
            if saved:
                st.payload, st.fetched, st.data_time, st.items, st.from_disk = saved["payload"], saved["fetched"], saved["data_time"], saved["items"], True
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10), follow_redirects=True,
                                         headers={"User-Agent": config.USER_AGENT, "Accept-Encoding": "gzip"})
        for i, st in enumerate(s for s in self.states.values() if s.feed.fetch):
            self._tasks.append(asyncio.create_task(self._run(st, first_delay=i * 0.6)))

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._client:
            await self._client.aclose()

    async def _run(self, st: FeedState, first_delay: float):
        st.next_at = time.time() + first_delay
        await asyncio.sleep(first_delay)
        while True:
            wait = await self._once(st)
            st.next_at = time.time() + wait
            await asyncio.sleep(wait)

    async def _once(self, st: FeedState) -> float:
        feed, f = st.feed, Fetcher(self._client)
        started, t0 = time.time(), time.perf_counter()
        try:
            res = await feed.fetch(feed, f)
            self.clock_diffs = (self.clock_diffs + f.clock_diffs)[-40:]
        except asyncio.CancelledError:
            raise
        except Exception as e:
            ms = int((time.perf_counter() - t0) * 1000)
            st.tried, st.last_ms, st.last_bytes = started, ms, f.wire_bytes
            st.total_bytes += f.wire_bytes
            st.fail_count += 1
            st.fails_in_a_row += 1
            st.error = _describe(e)
            await asyncio.to_thread(db.log_fetch, feed.name, started, ms, False, f.wire_bytes, None, None, st.error)
            # back off, doubling up to the normal interval (or 10 minutes for the fast feeds)
            backoff = min(max(feed.interval, 600), feed.min_retry * 2 ** (st.fails_in_a_row - 1))
            return max(feed.min_retry, backoff) * random.uniform(0.9, 1.1)
        ms = int((time.perf_counter() - t0) * 1000)
        st.tried = st.fetched = started
        st.from_disk = False
        st.payload, st.items, st.data_time, st.data_label, st.note = res.payload, res.items, res.data_time, res.data_label, res.note
        st.error, st.fails_in_a_row = None, 0
        st.ok_count += 1
        if feed.name in ("aircraft_near", "aircraft_military") and res.data_time:
            self._remember(res.payload["aircraft"], res.data_time)
        st.last_ms, st.last_bytes = ms, f.wire_bytes
        st.total_bytes += f.wire_bytes
        await asyncio.to_thread(db.log_fetch, feed.name, started, ms, True, f.wire_bytes, res.items, res.data_time, None)
        await asyncio.to_thread(db.save_latest, feed.name, started, res.data_time, res.items, res.payload)
        return feed.interval * random.uniform(0.97, 1.03)

    # Trails are for two things: the selected aircraft's path when OpenSky has none (`/api/track`), and orbit / tanker
    # detection (patterns.py), which reads the military and Munich feeds. Those two feeds keep every position (4 s
    # apart at most) for 3 hours. The live area feed (whatever part of the map a page is zoomed in on, every ~5 s, often
    # hundreds of aircraft) only adds one point per 30 s per aircraft, for an hour, so a page left open on a busy
    # region cannot fill the memory: it had grown by ~100 MB per watched region.
    FULL_KEEP, AREA_KEEP, AREA_STEP = 3 * 3600, 3600, 30
    FULL_CAP, AREA_CAP, MAX_TRAILS = 2700, 120, 12000      # points per aircraft (3 h at 4 s; 1 h at 30 s), aircraft kept

    def _remember(self, aircraft: list[dict], data_time: float, area: bool = False):
        """Keep the positions we were really given, so a selected aircraft can show where it has been."""
        full = self._full
        for a in aircraft:
            hex_, lon, lat = a.get("hex"), a.get("lon"), a.get("lat")
            if not hex_ or lon is None or lat is None:
                continue
            t = data_time - (a.get("seen_pos_s") or 0)
            if not area:
                full[hex_] = data_time
            thin = area and data_time - full.get(hex_, 0) > 600
            tr = self.trails.get(hex_)
            if tr is None:
                tr = self.trails[hex_] = []
            if not tr or (t > tr[-1][0] + (self.AREA_STEP if thin else 4) and (lon, lat) != (tr[-1][1], tr[-1][2])):
                alt = a.get("alt_ft")
                tr.append((round(t, 1), lon, lat, 0 if alt == "ground" else round(alt * 0.3048) if isinstance(alt, (int, float)) else None))
                cap = self.FULL_CAP if hex_ in full else self.AREA_CAP
                if len(tr) > cap + 50:                       # trimmed in steps, not one pop(0) per point
                    del tr[:len(tr) - cap]
        now = time.time()
        if now - self._pruned > 60:          # once a minute, not on every answer
            self._pruned = now
            self._prune(now)

    def _prune(self, now: float):
        full = self._full
        for hex_ in [h for h, t in full.items() if now - t > self.FULL_KEEP]:
            del full[hex_]
        for hex_, tr in list(self.trails.items()):
            old = now - (self.FULL_KEEP if hex_ in full else self.AREA_KEEP)
            if tr and tr[0][0] < old:
                i = next((i for i, p in enumerate(tr) if p[0] >= old), len(tr))
                del tr[:i]
            if not tr:
                del self.trails[hex_]
        if len(self.trails) > self.MAX_TRAILS:              # hard cap: drop the aircraft heard from longest ago, area-only first
            order = sorted(self.trails, key=lambda h: (h in full, self.trails[h][-1][0]))
            for hex_ in order[:len(self.trails) - self.MAX_TRAILS]:
                del self.trails[hex_]

    def status(self) -> dict:
        now = time.time()
        d = sorted(self.clock_diffs)
        # Date headers only have whole seconds, so this is good to about a second.
        clock = {"offset_s": round(d[len(d) // 2], 1), "samples": len(d)} if d else None
        return {"now": now, "started": self.started, "clock": clock, "feeds": [s.public(now) for s in self.states.values()]}


def _describe(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        body = e.response.text[:140].replace("\n", " ").strip()
        return f"HTTP {e.response.status_code} from {e.request.url.host}" + (f": {body}" if body else "")
    if isinstance(e, httpx.TimeoutException):
        return f"timed out ({type(e).__name__})"
    if isinstance(e, httpx.HTTPError):
        return f"network error ({type(e).__name__}): {e}"[:200]
    return f"could not read the answer ({type(e).__name__}): {e}"[:200]
