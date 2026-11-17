"""Lookup results live in their own file, data/lookup.db, apart from the map's data. For now there is one
subject, the owner himself. Deleting the subject deletes everything about it."""
import json
import re
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
        cur = db().execute("INSERT OR IGNORE INTO identifiers (kind, value, added) VALUES (?,?,?)", (kind, value, time.time()))
        db().commit()
        return cur.rowcount > 0


def identifier_exists(ident_id) -> bool:
    with _lock:
        return db().execute("SELECT 1 FROM identifiers WHERE id = ?", (ident_id,)).fetchone() is not None


def _forget_names(c, names):
    """What the page cached because of a full name you typed: the Wikidata name search (its key holds the name
    itself) and the public-figure records it led to (profile, court records). Those records describe public
    people, not you, but they exist only because of your name, so they go with it."""
    from .. import courts
    for name in names:
        key = "search:" + name.lower()
        row = c.execute("SELECT body FROM cache WHERE key = ?", (key,)).fetchone()
        for hit in (json.loads(row[0]) if row else []):
            qid = hit.get("qid") if isinstance(hit, dict) else None
            if qid:
                c.execute("DELETE FROM cache WHERE key GLOB ? OR key = ?", ("profile*:" + qid, "wdent:" + qid))
                if hit.get("name"):
                    c.execute("DELETE FROM cache WHERE key = ?", ("ukcase2:" + courts.fold(hit["name"]),))
        c.execute("DELETE FROM cache WHERE key = ?", (key,))


def remove_identifier(ident_id):
    _cache_table()
    with _lock:
        c = db()
        row = c.execute("SELECT kind, value FROM identifiers WHERE id = ?", (ident_id,)).fetchone()
        if row and row["kind"] == "name":
            _forget_names(c, [row["value"]])
        c.execute("DELETE FROM pages WHERE finding IN (SELECT id FROM findings WHERE identifier = ?)", (ident_id,))
        c.execute("DELETE FROM findings WHERE identifier = ?", (ident_id,))
        c.execute("DELETE FROM identifiers WHERE id = ?", (ident_id,))
        c.commit()


def norm_url(u) -> str:
    """The same page under small spelling differences; must match norm() in lookup.js, which joins findings into one dot."""
    return re.sub(r"[/?#]+$", "", re.sub(r"^https?://(www\.)?", "", (u or "").lower()))


def save_findings(ident_id, tool_names, found, now):
    """Store what a scan found for one identifier. A finding that no longer shows up is removed (for the
    tools that ran), except its 'not me' mark, which is kept so it stays hidden if it returns. A page you
    marked 'not me' stays so when another tool finds it later: the new row starts out marked."""
    with _lock:
        c = db()
        hidden = {norm_url(r[0]) for r in c.execute("SELECT url FROM findings WHERE identifier = ? AND not_me = 1 AND url IS NOT NULL", (ident_id,))}
        for f in found:
            nm = int(bool(f.get("url")) and f["kind"] == "account" and norm_url(f["url"]) in hidden)   # only for new rows: the update leaves not_me alone
            c.execute("""INSERT INTO findings (identifier, tool, kind, key, title, url, detail, first_seen, last_seen, not_me) VALUES (?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT (identifier, tool, key) DO UPDATE SET title = excluded.title, url = excluded.url, detail = excluded.detail, kind = excluded.kind, last_seen = excluded.last_seen""",
                      (ident_id, f["tool"], f["kind"], f["key"], f["title"], f.get("url"), json.dumps(f.get("detail") or {}), now, now, nm))
        for tool in tool_names:
            gone = "SELECT id FROM findings WHERE identifier = ? AND tool = ? AND last_seen < ? AND not_me = 0"
            # the page read goes with its finding: SQLite hands a freed id to the next new finding, which would inherit it
            c.execute(f"DELETE FROM pages WHERE finding IN ({gone})", (ident_id, tool, now))
            c.execute(gone.replace("SELECT id", "DELETE"), (ident_id, tool, now))
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
    _cache_table()
    with _lock:
        c = db()
        _forget_names(c, [r[0] for r in c.execute("SELECT value FROM identifiers WHERE kind = 'name'")])
        for t in ("pages", "findings", "identifiers", "scans"):
            c.execute(f"DELETE FROM {t}")
        c.commit()
        c.execute("VACUUM")


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
