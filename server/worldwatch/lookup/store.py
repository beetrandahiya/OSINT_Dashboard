"""Lookup results live in their own file, data/lookup.db, apart from the map's data. For now there is one
subject, the owner himself. Deleting the subject deletes everything about it."""
import json
import sqlite3
import threading
import time

from .. import config

_lock = threading.Lock()
_conn = None
KINDS = {"username": "Username", "email": "Email address", "name": "Full name", "phone": "Phone number", "domain": "Domain", "github": "GitHub account"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS identifiers (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, value TEXT NOT NULL, added REAL NOT NULL, UNIQUE (kind, value));
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY, identifier INTEGER NOT NULL, tool TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL,
    title TEXT NOT NULL, url TEXT, detail TEXT NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
    not_me INTEGER NOT NULL DEFAULT 0, UNIQUE (identifier, tool, key));
CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, started REAL NOT NULL, finished REAL, summary TEXT);
CREATE TABLE IF NOT EXISTS pages (finding INTEGER PRIMARY KEY, read REAL NOT NULL, body TEXT NOT NULL);
"""


def db():
    global _conn
    if _conn is None:
        config.DATA.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DATA / "lookup.db", timeout=30, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def identifiers():
    with _lock:
        return [dict(r) for r in db().execute("SELECT * FROM identifiers ORDER BY added")]


def add_identifier(kind, value):
    with _lock:
        db().execute("INSERT OR IGNORE INTO identifiers (kind, value, added) VALUES (?,?,?)", (kind, value, time.time()))
        db().commit()


def remove_identifier(ident_id):
    with _lock:
        db().execute("DELETE FROM pages WHERE finding IN (SELECT id FROM findings WHERE identifier = ?)", (ident_id,))
        db().execute("DELETE FROM findings WHERE identifier = ?", (ident_id,))
        db().execute("DELETE FROM identifiers WHERE id = ?", (ident_id,))
        db().commit()


def save_findings(ident_id, tool_names, found, now):
    """Store what a scan found for one identifier. A finding that no longer shows up is removed (for the
    tools that ran), except its 'not me' mark, which is kept so it stays hidden if it returns."""
    with _lock:
        c = db()
        for f in found:
            c.execute("""INSERT INTO findings (identifier, tool, kind, key, title, url, detail, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?)
                         ON CONFLICT (identifier, tool, key) DO UPDATE SET title = excluded.title, url = excluded.url, detail = excluded.detail, kind = excluded.kind, last_seen = excluded.last_seen""",
                      (ident_id, f["tool"], f["kind"], f["key"], f["title"], f.get("url"), json.dumps(f.get("detail") or {}), now, now))
        for tool in tool_names:
            c.execute("DELETE FROM findings WHERE identifier = ? AND tool = ? AND last_seen < ? AND not_me = 0", (ident_id, tool, now))
        c.commit()


def findings():
    with _lock:
        rows = [dict(r) for r in db().execute("SELECT f.*, p.body AS page_body, p.read AS page_read FROM findings f LEFT JOIN pages p ON p.finding = f.id ORDER BY f.first_seen")]
    for r in rows:
        r["detail"] = json.loads(r["detail"])
        body = json.loads(r.pop("page_body")) if r.get("page_body") else {}
        r["page"], r["archive"] = body.get("page"), body.get("archive")
    return rows


def pages_to_read(max_age=7 * 86400):
    """Findings with a web address whose page was never read, or not for a week."""
    with _lock:
        rows = db().execute("""SELECT f.id, f.url FROM findings f LEFT JOIN pages p ON p.finding = f.id
                               WHERE f.url LIKE 'http%' AND f.not_me = 0 AND f.kind IN ('account','profile','code','registered','mention')
                               AND (p.read IS NULL OR p.read < ?)""", (__import__("time").time() - max_age,)).fetchall()
    return [{"id": r[0], "url": r[1]} for r in rows]


def save_pages(results):
    import time as t
    with _lock:
        c = db()
        for fid, body in results.items():
            c.execute("INSERT OR REPLACE INTO pages (finding, read, body) VALUES (?,?,?)", (fid, t.time(), json.dumps(body)))
        c.commit()


def mark(finding_id, not_me):
    with _lock:
        db().execute("UPDATE findings SET not_me = ? WHERE id = ?", (int(bool(not_me)), finding_id))
        db().commit()


def scan_started():
    with _lock:
        cur = db().execute("INSERT INTO scans (started) VALUES (?)", (time.time(),))
        db().commit()
        return cur.lastrowid


def scan_finished(scan_id, summary):
    with _lock:
        db().execute("UPDATE scans SET finished = ?, summary = ? WHERE id = ?", (time.time(), json.dumps(summary), scan_id))
        db().commit()


def last_scan():
    with _lock:
        r = db().execute("SELECT * FROM scans WHERE finished IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    return r and {"started": r["started"], "finished": r["finished"], "summary": json.loads(r["summary"] or "{}")}


def wipe():
    with _lock:
        for t in ("pages", "findings", "identifiers", "scans"):
            db().execute(f"DELETE FROM {t}")
        db().commit()
        db().execute("VACUUM")


# ---- public-figure profiles: a cache, since Wikidata is slow. Not personal data; separate from findings. ----
import time as _time


def _cache_table():
    with _lock:
        db().execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, fetched REAL NOT NULL, body TEXT NOT NULL)")
        db().commit()


def cache_get(key, max_age):
    _cache_table()
    with _lock:
        row = db().execute("SELECT fetched, body FROM cache WHERE key = ?", (key,)).fetchone()
    if row and _time.time() - row[0] < max_age:
        return {"fetched": row[0], "body": json.loads(row[1])}
    return None


def cache_put(key, body):
    _cache_table()
    with _lock:
        db().execute("INSERT OR REPLACE INTO cache (key, fetched, body) VALUES (?,?,?)", (key, _time.time(), json.dumps(body)))
        db().commit()
