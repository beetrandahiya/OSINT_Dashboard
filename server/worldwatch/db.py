"""SQLite: a log of every fetch attempt, and the latest good data of each feed (so a restart
shows the last known state with its real age instead of an empty screen)."""
import json
import sqlite3
import threading

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
CREATE TABLE IF NOT EXISTS latest (
    feed       TEXT PRIMARY KEY,
    fetched    REAL NOT NULL,
    data_time  REAL,
    items      INTEGER,
    payload    TEXT NOT NULL
);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        config.DATA.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
    return _conn


def log_fetch(feed, started, ms, ok, nbytes, items, data_time, error):
    with _lock:
        c = conn()
        c.execute("INSERT INTO fetches (feed, started, ms, ok, bytes, items, data_time, error) VALUES (?,?,?,?,?,?,?,?)",
                  (feed, started, ms, int(ok), nbytes, items, data_time, error))
        c.execute("DELETE FROM fetches WHERE started < ?", (started - 7 * 86400,))
        c.commit()


def save_latest(feed, fetched, data_time, items, payload):
    with _lock:
        c = conn()
        c.execute("INSERT OR REPLACE INTO latest (feed, fetched, data_time, items, payload) VALUES (?,?,?,?,?)",
                  (feed, fetched, data_time, items, json.dumps(payload, separators=(",", ":"))))
        c.commit()


def load_latest(feed):
    with _lock:
        row = conn().execute("SELECT fetched, data_time, items, payload FROM latest WHERE feed = ?", (feed,)).fetchone()
    if not row:
        return None
    return {"fetched": row[0], "data_time": row[1], "items": row[2], "payload": json.loads(row[3])}
