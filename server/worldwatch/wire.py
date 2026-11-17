"""Answers encoded once and handed out many times.

Every page polls the same few multi-MB payloads (news ~2.5 MB, sites, cameras, world aircraft ~1 MB). Building a
JSONResponse per request meant json.dumps in the event loop (20-80 ms) plus gzip at level 9 (90-540 ms) for every
tab, every poll, although the payload changes only when its feed is fetched again. Here a payload is serialised and
compressed once, in a worker thread, and kept with a version (a hash of its bytes, so an unchanged refetch keeps the
same version). Each request then only appends its own small fields (the feed's state and the server's `now`, which
must be fresh: the page sets its clock from it) to the kept bytes. The gzip stream is continued from a copy of the
compressor that made the kept part, so the answer is one ordinary gzip stream and costs well under a millisecond.
"""
import asyncio
import hashlib
import json
import threading
import time
import zlib

from starlette.responses import Response

LEVEL = 6            # level 9 was 2-3x slower for 1-2 % smaller answers
MIN_GZIP = 2000


def dumps(obj) -> bytes:
    """Exactly what Starlette's JSONResponse would send."""
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=None, separators=(",", ":")).encode("utf-8")


class Encoded:
    """A JSON object's members, serialised and gzipped once; `body` adds per-request members at the end.

    Built lazily (`prepare`, in a thread): many feeds are only ever read by the server itself, and a kept gzip stream
    costs its compressor's state (~256 KB) plus the compressed bytes. Once the gzip part exists the plain bytes are
    dropped; the rare client that does not take gzip gets them made again from `make`."""
    __slots__ = ("version", "make", "inner", "head", "co", "empty")

    def __init__(self, version: str, make, inner: bytes | None = None):
        self.version, self.make, self.inner = version, make, inner      # inner: the members without the braces
        self.head, self.co, self.empty = b"", None, None

    def ready(self) -> bool:
        return self.empty is not None

    def prepare(self) -> "Encoded":
        if self.empty is not None:
            return self
        inner = self.inner if self.inner is not None else self.make()
        if len(inner) + 2 >= MIN_GZIP:
            co = zlib.compressobj(LEVEL, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
            self.head, self.co, self.inner = co.compress(b"{" + inner), co, None
        else:
            self.inner = inner
        self.empty = not inner
        return self

    def body(self, extra: dict | None, gzip: bool) -> bytes:
        self.prepare()
        tail = dumps(extra)[1:] if extra else b"}"
        if extra and not self.empty:
            tail = b"," + tail
        if gzip and self.co is not None:
            c = self.co.copy()                       # the kept stream continued; the copy leaves the original untouched
            return self.head + c.compress(tail) + c.flush()
        return b"{" + (self.inner if self.inner is not None else self.make()) + tail


def version_of(raw: bytes) -> str:
    return hashlib.blake2b(raw, digest_size=8).hexdigest()


def encode(obj: dict) -> Encoded:
    raw = dumps(obj)
    return Encoded(version_of(raw), lambda: dumps(obj)[1:-1], raw[1:-1]).prepare()


def encode_payload(payload, raw: bytes | None = None) -> tuple[Encoded, bytes]:
    """A feed answer's kept part, {"payload": ...}, not yet compressed, and the payload's bytes (what the database
    keeps). The version is that of the payload's bytes, so the same data fetched again keeps its version."""
    raw = dumps(payload) if raw is None else raw
    return Encoded(version_of(raw), lambda: b'"payload":' + dumps(payload)), raw


def respond(request, enc: Encoded, extra: dict | None = None, etag: str | None = None, headers: dict | None = None) -> Response:
    h = {"Cache-Control": "no-store", "Vary": "Accept-Encoding", **(headers or {})}
    if etag:
        h["ETag"] = etag
        inm = request.headers.get("if-none-match", "")
        if etag in [x.strip() for x in inm.split(",")]:
            return Response(status_code=304, headers=h)
    enc.prepare()
    gz = enc.co is not None and "gzip" in request.headers.get("accept-encoding", "")
    if gz:
        h["Content-Encoding"] = "gzip"
    return Response(enc.body(extra, gz), media_type="application/json", headers=h)


class Memo:
    """A computed answer kept until its inputs change (`key`) or it is `max_age` seconds old. One computation at a time,
    in a worker thread; requests arriving meanwhile wait for it instead of starting their own."""

    def __init__(self, max_age: float):
        self.max_age, self.key, self.at, self.value, self.enc = max_age, None, 0.0, None, None
        self._lock: asyncio.Lock | None = None

    async def get(self, key, fn, *args):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self.enc is None or key != self.key or time.time() - self.at > self.max_age:
                value = await asyncio.to_thread(fn, *args)
                enc = await asyncio.to_thread(encode, {k: v for k, v in value.items() if k != "now"})
                self.key, self.at, self.value, self.enc = key, time.time(), value, enc
            return self.enc


class Cached:
    """Memo for code that runs in threads already (news.spikes, news.leaders_today): same rule, a threading lock."""

    def __init__(self):
        self.key, self.value, self._lock = None, None, threading.Lock()

    def get(self, key, fn):
        with self._lock:
            if self.value is None or key != self.key:
                self.value, self.key = fn(), key
            return self.value
