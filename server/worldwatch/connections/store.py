"""The Connections database (data/connections.db): the ICIJ Offshore Leaks import, OpenSanctions' sanctioned
companies, and a cache of answers from the live registers (GLEIF, Wikidata). Apart from the map's database so a
re-import never touches feed data. Read with one connection per thread (SQLite is fine with that)."""
import json
import sqlite3
import threading
import time

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, fetched REAL NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
_local = threading.local()


def path():
    return config.DATA / "connections.db"


def db() -> sqlite3.Connection:
    c = getattr(_local, "c", None)
    if c is None:
        config.DATA.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(path(), timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.executescript(SCHEMA)
        _local.c = c
    return c


def cache_get(key, max_age):
    r = db().execute("SELECT fetched, body FROM cache WHERE key = ?", (key,)).fetchone()
    if r and time.time() - r["fetched"] < max_age:
        return json.loads(r["body"])
    return None


def cache_put(key, body):
    db().execute("INSERT OR REPLACE INTO cache (key, fetched, body) VALUES (?,?,?)", (key, time.time(), json.dumps(body, ensure_ascii=False)))
    db().commit()


def meta_get(key, default=None):
    try:
        r = db().execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    except sqlite3.OperationalError:
        return default
    return json.loads(r["value"]) if r else default


def meta_put(key, value):
    db().execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, json.dumps(value)))
    db().commit()


def has_table(name) -> bool:
    return db().execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None
