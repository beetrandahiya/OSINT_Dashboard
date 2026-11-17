"""SQLite: a log of every fetch attempt, and the latest good data of each feed (so a restart
shows the last known state with its real age instead of an empty screen)."""
import json
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS fetches (
    id         INTEGER PRIMARY KEY,
    feed       TEXT NOT NULL,
    started    REAL NOT NULL,      -- our clock, unix seconds
    ms         INTEGER NOT NULL,   -- how long the fetch took
    ok         INTEGER NOT NULL,
    bytes      INTEGER NOT NULL,   -- bytes on the wire (compressed)
    items      INTEGER,
    data_time  REAL,               -- the source's own timestamp for the data, if it gives one
    error      TEXT
);
CREATE INDEX IF NOT EXISTS fetches_feed ON fetches (feed, started);
CREATE INDEX IF NOT EXISTS fetches_started ON fetches (started);   -- the 7-day clean-up; fetches_feed starts with feed, so it scanned the table
CREATE TABLE IF NOT EXISTS lookups (     -- answers to one-off questions (a flight's route), kept so we ask once
    key        TEXT PRIMARY KEY,
    fetched    REAL NOT NULL,
    body       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS latest (
    feed       TEXT PRIMARY KEY,
    fetched    REAL NOT NULL,
    data_time  REAL,
    items      INTEGER,
    payload    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS latest_seen (  -- the newest fetch whose payload equals the stored one (see save_latest)
    feed       TEXT PRIMARY KEY,
    fetched    REAL NOT NULL,
    data_time  REAL,
    items      INTEGER,
    version    TEXT NOT NULL
);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        config.DATA.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")    # with WAL: never corrupts; a power cut can lose the last commits only
        _conn.executescript(SCHEMA)
        if "version" not in [r[1] for r in _conn.execute("PRAGMA table_info(latest)")]:   # databases from before 2026-11-17
            _conn.execute("ALTER TABLE latest ADD COLUMN version TEXT")
            _conn.commit()
    return _conn


_pruned = 0.0


def log_fetch(feed, started, ms, ok, nbytes, items, data_time, error):
    with _lock:
        c = conn()
        c.execute("INSERT INTO fetches (feed, started, ms, ok, bytes, items, data_time, error) VALUES (?,?,?,?,?,?,?,?)",
                  (feed, started, ms, int(ok), nbytes, items, data_time, error))
        global _pruned
        if time.time() - _pruned > 600:          # every ten minutes is plenty for a 7-day limit
            _pruned = time.time()
            c.execute("DELETE FROM fetches WHERE started < ?", (started - 7 * 86400,))
        c.commit()


def save_latest(feed, fetched, data_time, items, raw: bytes, version: str):
    """Store a feed's newest good payload (`raw`: its JSON bytes). Most refetches bring back the same bytes (cables,
    sites, cameras: weekly data asked every few hours; quakes on a quiet hour): those rewrote megabytes for nothing
    (~8 MB a minute). Then only the small `latest_seen` row moves on, so a restart still shows the true age."""
    with _lock:
        c = conn()
        row = c.execute("SELECT version FROM latest WHERE feed = ?", (feed,)).fetchone()
        if not row or row[0] != version:
            c.execute("INSERT OR REPLACE INTO latest (feed, fetched, data_time, items, payload, version) VALUES (?,?,?,?,?,?)",
                      (feed, fetched, data_time, items, raw.decode("utf-8"), version))
        c.execute("INSERT OR REPLACE INTO latest_seen (feed, fetched, data_time, items, version) VALUES (?,?,?,?,?)",
                  (feed, fetched, data_time, items, version))
        c.commit()


def load_latest(feed):
    with _lock:
        row = conn().execute("SELECT fetched, data_time, items, payload, version FROM latest WHERE feed = ?", (feed,)).fetchone()
        seen = conn().execute("SELECT fetched, data_time, items, version FROM latest_seen WHERE feed = ?", (feed,)).fetchone()
    if not row:
        return None
    out = {"fetched": row[0], "data_time": row[1], "items": row[2], "payload": json.loads(row[3]), "raw": row[3], "version": row[4]}
    if seen and row[4] and seen[3] == row[4] and seen[0] > row[0]:      # a later fetch brought back the same payload
        out.update(fetched=seen[0], data_time=seen[1], items=seen[2])
    return out


def lookup_get(key, max_age):
    import time
    with _lock:
        row = conn().execute("SELECT fetched, body FROM lookups WHERE key = ?", (key,)).fetchone()
    if row and time.time() - row[0] < max_age:
        return {"fetched": row[0], "body": json.loads(row[1])}
    return None


def lookup_put(key, fetched, body):
    with _lock:
        c = conn()
        c.execute("INSERT OR REPLACE INTO lookups (key, fetched, body) VALUES (?,?,?)", (key, fetched, json.dumps(body)))
        c.commit()
