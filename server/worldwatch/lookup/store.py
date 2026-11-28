"""Lookup results live in their own file, data/lookup.db, apart from the map's data.

Everything belongs to a case (a subject). A case starts only with its consent record: the owner himself
(self-test), or a person who agreed, with who agreed, when, how and to what. Deleting a case deletes
everything tied to it: identifiers, findings, page reads, leads, picture fingerprints, uploaded pictures and
the cache entries a typed name created. Deleted rows are overwritten on disk (secure_delete) and the file is
compacted afterwards, so nothing of a deleted case lingers in the database file.
"""
import json
import re
import sqlite3
import threading
import time
from pathlib import Path

from .. import config

_lock = threading.RLock()
_conn = None
KINDS = {"username": "Username", "email": "Email address", "name": "Full name", "phone": "Phone number", "domain": "Domain",
         "github": "GitHub account", "picture": "Picture file"}
HOW = {"self": "self-test (the owner)", "written": "written consent", "verbal": "verbal consent"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY, label TEXT NOT NULL, created REAL NOT NULL, is_self INTEGER NOT NULL DEFAULT 0,
    consent_by TEXT, consent_at TEXT, consent_how TEXT, consent_scope TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS identifiers (id INTEGER PRIMARY KEY, subject INTEGER NOT NULL DEFAULT 1, kind TEXT NOT NULL, value TEXT NOT NULL,
    added REAL NOT NULL, source TEXT NOT NULL DEFAULT 'seed', hop INTEGER NOT NULL DEFAULT 0, lead INTEGER, detail TEXT, scanned REAL,
    UNIQUE (subject, kind, value));
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY, identifier INTEGER NOT NULL, tool TEXT NOT NULL, kind TEXT NOT NULL, key TEXT NOT NULL,
    title TEXT NOT NULL, url TEXT, detail TEXT NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL,
    not_me INTEGER NOT NULL DEFAULT 0, subject INTEGER NOT NULL DEFAULT 1, confirmed INTEGER NOT NULL DEFAULT 0, UNIQUE (identifier, tool, key));
CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, started REAL NOT NULL, finished REAL, summary TEXT, subject INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS pages (finding INTEGER PRIMARY KEY, read REAL NOT NULL, body TEXT NOT NULL, subject INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, subject INTEGER NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL, norm TEXT NOT NULL,
    strength TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'new', hop INTEGER NOT NULL, evidence TEXT NOT NULL, created REAL NOT NULL, decided REAL,
    UNIQUE (subject, kind, norm));
CREATE TABLE IF NOT EXISTS fingerprints (id INTEGER PRIMARY KEY, subject INTEGER NOT NULL, url TEXT NOT NULL, hash TEXT NOT NULL,
    location_meta INTEGER NOT NULL DEFAULT 0, added REAL NOT NULL, UNIQUE (subject, url));
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, fetched REAL NOT NULL, body TEXT NOT NULL);
"""
INDEXES = """
CREATE INDEX IF NOT EXISTS findings_subject ON findings (subject);
CREATE INDEX IF NOT EXISTS identifiers_subject ON identifiers (subject);
CREATE INDEX IF NOT EXISTS leads_subject ON leads (subject);
"""


def version() -> int:
    """Changes whenever this process writes to the database (one connection: its running count of changed rows)."""
    return db().total_changes


def images_dir() -> Path:
    return config.DATA / "lookup-images"


def _cols(c, table):
    return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}


def _migrate(c):
    """The database from before cases had one unnamed subject (the owner). Its rows become case 1, "Me (self-test)"."""
    if "subject" not in _cols(c, "identifiers"):
        c.execute("""INSERT OR IGNORE INTO subjects (id, label, created, is_self, consent_by, consent_at, consent_how, consent_scope, note)
                     VALUES (1, 'Me (self-test)', ?, 1, 'the owner', ?, 'self', 'my own public footprint',
                     'Made from the lookup results that existed before cases were added.')""", (time.time(), time.strftime("%Y-%m-%d")))
        c.executescript("""
            ALTER TABLE identifiers RENAME TO identifiers_old;
            CREATE TABLE identifiers (id INTEGER PRIMARY KEY, subject INTEGER NOT NULL DEFAULT 1, kind TEXT NOT NULL, value TEXT NOT NULL,
                added REAL NOT NULL, source TEXT NOT NULL DEFAULT 'seed', hop INTEGER NOT NULL DEFAULT 0, lead INTEGER, detail TEXT, scanned REAL,
                UNIQUE (subject, kind, value));
            INSERT INTO identifiers (id, subject, kind, value, added) SELECT id, 1, kind, value, added FROM identifiers_old;
            DROP TABLE identifiers_old;
        """)
    for table, col, decl in (("findings", "subject", "INTEGER NOT NULL DEFAULT 1"), ("findings", "confirmed", "INTEGER NOT NULL DEFAULT 0"),
                             ("scans", "subject", "INTEGER NOT NULL DEFAULT 1"), ("pages", "subject", "INTEGER NOT NULL DEFAULT 1")):
        if col not in _cols(c, table):
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    c.commit()


def db():
    global _conn
    with _lock:
        if _conn is None:
            config.DATA.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(config.DATA / "lookup.db", timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA secure_delete = ON")          # deleted rows are overwritten, not just unlinked
            conn.executescript(SCHEMA)
            _migrate(conn)
            conn.executescript(INDEXES)
            _conn = conn
    return _conn


# ---- cases ----

def consent_ok(s) -> bool:
    """A case may be scanned only with a complete consent record: self-test, or who agreed, when, how and to what."""
    if not s:
        return False
    if s["is_self"] and s["consent_how"] == "self":
        return True
    return bool(s["consent_how"] in ("written", "verbal") and (s["consent_by"] or "").strip() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["consent_at"] or "")
                and (s["consent_scope"] or "").strip())


def subjects():
    with _lock:
        rows = [dict(r) for r in db().execute("""SELECT s.*,
            (SELECT COUNT(*) FROM identifiers i WHERE i.subject = s.id) AS n_identifiers,
            (SELECT COUNT(*) FROM findings f WHERE f.subject = s.id) AS n_findings,
            (SELECT COUNT(*) FROM findings f WHERE f.subject = s.id AND f.confirmed = 1) AS n_confirmed,
            (SELECT COUNT(*) FROM leads l WHERE l.subject = s.id AND l.state = 'new') AS n_leads
            FROM subjects s ORDER BY s.is_self DESC, s.created""")]
    for r in rows:
        r["consent_ok"] = consent_ok(r)
    return rows


def subject(sid):
    with _lock:
        r = db().execute("SELECT * FROM subjects WHERE id = ?", (sid,)).fetchone()
    if not r:
        return None
    r = dict(r)
    r["consent_ok"] = consent_ok(r)
    return r


def add_subject(label, is_self, consent_by, consent_at, consent_how, consent_scope, note):
    with _lock:
        c = db()
        if is_self and c.execute("SELECT 1 FROM subjects WHERE is_self = 1").fetchone():
            raise ValueError("There is already a self-test case.")
        cur = c.execute("""INSERT INTO subjects (label, created, is_self, consent_by, consent_at, consent_how, consent_scope, note)
                           VALUES (?,?,?,?,?,?,?,?)""", (label, time.time(), int(bool(is_self)), consent_by, consent_at, consent_how, consent_scope, note))
        c.commit()
        return cur.lastrowid


def update_subject(sid, label=None, note=None):
    with _lock:
        if label is not None:
            db().execute("UPDATE subjects SET label = ? WHERE id = ?", (label, sid))
        if note is not None:
            db().execute("UPDATE subjects SET note = ? WHERE id = ?", (note, sid))
        db().commit()


def _picture_files(c, where, args):
    return {r[0] for r in c.execute(f"SELECT value FROM identifiers WHERE kind = 'picture' AND {where}", args)}


def _drop_unused_pictures(c, files):
    """Remove uploaded pictures that no identifier of any case refers to any more."""
    for name in files:
        if not c.execute("SELECT 1 FROM identifiers WHERE kind = 'picture' AND value = ?", (name,)).fetchone():
            p = images_dir() / name
            if re.fullmatch(r"[0-9a-f]{64}\.(jpg|png|gif|webp)", name) and p.exists():
                p.unlink()


def delete_subject(sid):
    _cache_table()
    with _lock:
        c = db()
        _forget_names(c, [r[0] for r in c.execute("SELECT value FROM identifiers WHERE subject = ? AND kind = 'name'", (sid,))])
        files = _picture_files(c, "subject = ?", (sid,))
        c.execute("DELETE FROM pages WHERE subject = ? OR finding IN (SELECT id FROM findings WHERE subject = ?)", (sid, sid))
        for t in ("findings", "leads", "fingerprints", "identifiers", "scans"):
            c.execute(f"DELETE FROM {t} WHERE subject = ?", (sid,))
        c.execute("DELETE FROM subjects WHERE id = ?", (sid,))
        c.commit()
        _drop_unused_pictures(c, files)
        c.execute("VACUUM")


# ---- identifiers ----

def identifiers(sid):
    with _lock:
        rows = [dict(r) for r in db().execute("SELECT * FROM identifiers WHERE subject = ? ORDER BY added", (sid,))]
    for r in rows:
        r["detail"] = json.loads(r["detail"]) if r["detail"] else {}
    return rows


def identifier(ident_id):
    with _lock:
        r = db().execute("SELECT * FROM identifiers WHERE id = ?", (ident_id,)).fetchone()
    return dict(r) if r else None


def add_identifier(sid, kind, value, source="seed", hop=0, lead=None, detail=None):
    """The new identifier's id, or None when the case already has it."""
    with _lock:
        cur = db().execute("INSERT OR IGNORE INTO identifiers (subject, kind, value, added, source, hop, lead, detail) VALUES (?,?,?,?,?,?,?,?)",
                           (sid, kind, value, time.time(), source, hop, lead, json.dumps(detail) if detail else None))
        db().commit()
        return cur.lastrowid if cur.rowcount > 0 else None


def identifier_exists(ident_id) -> bool:
    with _lock:
        return db().execute("SELECT 1 FROM identifiers WHERE id = ?", (ident_id,)).fetchone() is not None


def mark_scanned(ident_ids, when):
    with _lock:
        db().executemany("UPDATE identifiers SET scanned = ? WHERE id = ?", [(when, i) for i in ident_ids])
        db().commit()


def _forget_names(c, names):
    """What the page cached because of a full name you typed: the Wikidata name search (its key holds the name
    itself) and the public-figure records it led to (profile, court records). Those records describe public
    people, not the subject, but they exist only because of the name, so they go with it."""
    from .. import courts
    for name in names:
        key = "search:" + name.lower()
        row = c.execute("SELECT body FROM cache WHERE key = ?", (key,)).fetchone()
        for hit in (json.loads(row[0]) if row else []):
            qid = hit.get("qid") if isinstance(hit, dict) else None
            if qid:
                c.execute("DELETE FROM cache WHERE key GLOB ? OR key GLOB ?", ("profile*:" + qid, "wdent*:" + qid))
                if hit.get("name"):
                    c.execute("DELETE FROM cache WHERE key = ?", ("ukcase2:" + courts.fold(hit["name"]),))
        c.execute("DELETE FROM cache WHERE key = ?", (key,))


def remove_identifier(ident_id):
    _cache_table()
    with _lock:
        c = db()
        row = c.execute("SELECT * FROM identifiers WHERE id = ?", (ident_id,)).fetchone()
        if not row:
            return
        if row["kind"] == "name":
            _forget_names(c, [row["value"]])
        if row["lead"]:            # a followed or approved lead that is removed again is not proposed again
            c.execute("UPDATE leads SET state = 'rejected', decided = ? WHERE id = ?", (time.time(), row["lead"]))
        files = {row["value"]} if row["kind"] == "picture" else set()
        if files:
            c.execute("DELETE FROM fingerprints WHERE subject = ? AND url = ?", (row["subject"], "picture:" + row["value"]))
        c.execute("DELETE FROM pages WHERE finding IN (SELECT id FROM findings WHERE identifier = ?)", (ident_id,))
        c.execute("DELETE FROM findings WHERE identifier = ?", (ident_id,))
        c.execute("DELETE FROM identifiers WHERE id = ?", (ident_id,))
        c.commit()
        _drop_unused_pictures(c, files)


# ---- findings ----

def norm_url(u) -> str:
    """The same page under small spelling differences; must match norm() in lookup.js, which joins findings into one dot."""
    return re.sub(r"[/?#]+$", "", re.sub(r"^https?://(www\.)?", "", (u or "").lower()))


def save_findings(ident_id, tool_names, found, now):
    """Store what a scan found for one identifier. A finding that no longer shows up is removed (for the
    tools that ran), unless it was marked 'not me' or 'confirmed': the mark is kept so it stays hidden or
    confirmed if it returns. A page marked either way stays so when another tool or identifier of the same
    case finds it later: the new row starts out with the same mark."""
    with _lock:
        c = db()
        row = c.execute("SELECT subject FROM identifiers WHERE id = ?", (ident_id,)).fetchone()
        if not row:
            return
        sid = row[0]
        marks = {}
        for u, nm, cf in c.execute("SELECT url, not_me, confirmed FROM findings WHERE subject = ? AND (not_me = 1 OR confirmed = 1) AND url IS NOT NULL", (sid,)):
            marks[norm_url(u)] = (nm, cf)
        for f in found:
            nm, cf = marks.get(norm_url(f.get("url")), (0, 0)) if f.get("url") and f["kind"] in ("account", "profile", "website") else (0, 0)
            # only for new rows: the update leaves the marks alone
            c.execute("""INSERT INTO findings (identifier, subject, tool, kind, key, title, url, detail, first_seen, last_seen, not_me, confirmed) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT (identifier, tool, key) DO UPDATE SET title = excluded.title, url = excluded.url, detail = excluded.detail, kind = excluded.kind, last_seen = excluded.last_seen""",
                      (ident_id, sid, f["tool"], f["kind"], f["key"], f["title"], f.get("url"), json.dumps(f.get("detail") or {}), now, now, nm, cf))
        for tool in tool_names:
            gone = "SELECT id FROM findings WHERE identifier = ? AND tool = ? AND last_seen < ? AND not_me = 0 AND confirmed = 0"
            # the page read goes with its finding: SQLite hands a freed id to the next new finding, which would inherit it
            c.execute(f"DELETE FROM pages WHERE finding IN ({gone})", (ident_id, tool, now))
            c.execute(gone.replace("SELECT id", "DELETE"), (ident_id, tool, now))
        c.commit()


def findings(sid, with_private=False):
    """Findings of one case, with what their page showed. The page reader's raw link lists stay on the server
    (pivot reads them) unless with_private is set; the page shows what it needs."""
    with _lock:
        rows = [dict(r) for r in db().execute("""SELECT f.*, p.body AS page_body, p.read AS page_read FROM findings f LEFT JOIN pages p ON p.finding = f.id
                                                 WHERE f.subject = ? ORDER BY f.first_seen""", (sid,))]
    for r in rows:
        r["detail"] = json.loads(r["detail"])
        body = json.loads(r.pop("page_body")) if r.get("page_body") else {}
        r["page"], r["archive"], r["history"] = body.get("page"), body.get("archive"), body.get("history")
        if r["page"] and not with_private:
            r["page"] = {k: v for k, v in r["page"].items() if k not in ("links", "rel_me")}
    return rows


def pages_to_read(sid, max_age=7 * 86400):
    """Findings with a web address whose page was never read, or not for a week."""
    with _lock:
        rows = db().execute("""SELECT f.id, f.url FROM findings f LEFT JOIN pages p ON p.finding = f.id
                               WHERE f.subject = ? AND f.url LIKE 'http%' AND f.not_me = 0 AND f.kind IN ('account','profile','code','registered','mention','website','record')
                               AND (p.read IS NULL OR p.read < ?)""", (sid, time.time() - max_age)).fetchall()
    return [{"id": r[0], "url": r[1]} for r in rows]


def save_pages(sid, results):
    with _lock:
        c = db()
        for fid, body in results.items():
            old = c.execute("SELECT body FROM pages WHERE finding = ?", (fid,)).fetchone()
            if old and "history" in (prev := json.loads(old[0])) and "history" not in body:
                body = {**body, "history": prev["history"]}          # the archive history survives a fresh page read
            c.execute("INSERT OR REPLACE INTO pages (finding, subject, read, body) VALUES (?,?,?,?)", (fid, sid, time.time(), json.dumps(body)))
        c.commit()


def save_history(sid, fid, history):
    with _lock:
        c = db()
        old = c.execute("SELECT read, body FROM pages WHERE finding = ?", (fid,)).fetchone()
        body = json.loads(old[1]) if old else {}
        body["history"] = history
        c.execute("INSERT OR REPLACE INTO pages (finding, subject, read, body) VALUES (?,?,?,?)", (fid, sid, old[0] if old else 0, json.dumps(body)))
        c.commit()


def mark(sid, finding_ids, not_me=None, confirmed=None):
    """'Not me' and 'Confirmed' exclude each other: setting one clears the other."""
    with _lock:
        c = db()
        for fid in finding_ids:
            if not_me is not None:
                c.execute("UPDATE findings SET not_me = ?, confirmed = CASE WHEN ? THEN 0 ELSE confirmed END WHERE id = ? AND subject = ?", (int(not_me), int(not_me), fid, sid))
            if confirmed is not None:
                c.execute("UPDATE findings SET confirmed = ?, not_me = CASE WHEN ? THEN 0 ELSE not_me END WHERE id = ? AND subject = ?", (int(confirmed), int(confirmed), fid, sid))
        c.commit()


def image_urls(sid) -> set:
    """Every picture address the case's findings name: the only addresses the picture proxy fetches."""
    out = set()
    for f in findings(sid):
        for v in (f["detail"].get("image"), f["detail"].get("photo"), (f.get("page") or {}).get("image")):
            if isinstance(v, str) and v.startswith(("https://", "http://")):
                out.add(v)
    return out


# ---- scans ----

def scan_started(sid):
    with _lock:
        cur = db().execute("INSERT INTO scans (subject, started) VALUES (?,?)", (sid, time.time()))
        db().commit()
        return cur.lastrowid


def scan_finished(scan_id, summary):
    with _lock:
        db().execute("UPDATE scans SET finished = ?, summary = ? WHERE id = ?", (time.time(), json.dumps(summary), scan_id))
        db().commit()


def last_scan(sid):
    with _lock:
        r = db().execute("SELECT * FROM scans WHERE subject = ? AND finished IS NOT NULL ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
    return r and {"started": r["started"], "finished": r["finished"], "summary": json.loads(r["summary"] or "{}")}


def checks_run(sid) -> dict:
    """For each check, when the newest finished scan that ran it started, and the problems that scan reported:
    so the dossier can tell "checked, nothing found" from "not checked"."""
    out = {}
    with _lock:
        rows = db().execute("SELECT started, summary FROM scans WHERE subject = ? AND finished IS NOT NULL ORDER BY id", (sid,)).fetchall()
    for started, summary in rows:
        sm = json.loads(summary or "{}")
        for c in sm.get("checks") or []:
            out[c] = {"started": started, "problems": sm.get("problems") or []}
    return out


# ---- leads ----

def lead_norm(kind, value) -> str:
    v = re.sub(r"\s+", " ", (value or "").strip().lower())
    return v[4:] if kind == "domain" and v.startswith("www.") else v


def leads(sid):
    with _lock:
        rows = [dict(r) for r in db().execute("SELECT * FROM leads WHERE subject = ? ORDER BY (strength = 'strong') DESC, hop, created", (sid,))]
    for r in rows:
        r["evidence"] = json.loads(r["evidence"])
    return rows


def upsert_leads(sid, derived):
    """Store the leads the pivot engine derived. A new lead appears; one that is no longer derived and was never
    decided disappears; a decided one (followed, approved, rejected) keeps its state for good, so a rejected lead
    is never proposed again, only its evidence is refreshed."""
    now = time.time()
    with _lock:
        c = db()
        keep = set()
        for d in derived:
            n = lead_norm(d["kind"], d["value"])
            keep.add((d["kind"], n))
            row = c.execute("SELECT id, state, strength FROM leads WHERE subject = ? AND kind = ? AND norm = ?", (sid, d["kind"], n)).fetchone()
            if row:
                strength = d["strength"] if row["state"] == "new" else row["strength"]
                c.execute("UPDATE leads SET evidence = ?, strength = ?, hop = MIN(hop, ?) WHERE id = ?", (json.dumps(d["evidence"]), strength, d["hop"], row["id"]))
            else:
                c.execute("INSERT INTO leads (subject, kind, value, norm, strength, state, hop, evidence, created) VALUES (?,?,?,?,?,?,?,?,?)",
                          (sid, d["kind"], d["value"], n, d["strength"], "new", d["hop"], json.dumps(d["evidence"]), now))
        for r in c.execute("SELECT id, kind, norm FROM leads WHERE subject = ? AND state = 'new'", (sid,)).fetchall():
            if (r["kind"], r["norm"]) not in keep:
                c.execute("DELETE FROM leads WHERE id = ?", (r["id"],))
        c.commit()


def lead(sid, lead_id):
    with _lock:
        r = db().execute("SELECT * FROM leads WHERE id = ? AND subject = ?", (lead_id, sid)).fetchone()
    return dict(r) if r else None


def set_lead_state(sid, lead_id, state):
    with _lock:
        db().execute("UPDATE leads SET state = ?, decided = ? WHERE id = ? AND subject = ?", (state, None if state == "new" else time.time(), lead_id, sid))
        db().commit()


def strong_to_follow(sid, max_hop=2):
    with _lock:
        return [dict(r) for r in db().execute("SELECT * FROM leads WHERE subject = ? AND state = 'new' AND strength = 'strong' AND hop <= ? ORDER BY hop, created",
                                              (sid, max_hop))]


# ---- picture fingerprints (64-bit difference hashes computed in the browser; picture-copy matching, not face recognition) ----

def fingerprints(sid) -> dict:
    with _lock:
        return {r["url"]: {"hash": r["hash"], "location_meta": bool(r["location_meta"])}
                for r in db().execute("SELECT url, hash, location_meta FROM fingerprints WHERE subject = ?", (sid,))}


def save_fingerprints(sid, items):
    with _lock:
        c = db()
        for it in items:
            c.execute("INSERT OR REPLACE INTO fingerprints (subject, url, hash, location_meta, added) VALUES (?,?,?,?,?)",
                      (sid, it["url"], it["hash"], int(bool(it.get("location_meta"))), time.time()))
        c.commit()


def wipe():
    """Delete every case and everything in it, uploaded pictures included."""
    _cache_table()
    with _lock:
        c = db()
        _forget_names(c, [r[0] for r in c.execute("SELECT value FROM identifiers WHERE kind = 'name'")])
        files = _picture_files(c, "1", ())
        for t in ("pages", "findings", "leads", "fingerprints", "identifiers", "scans", "subjects"):
            c.execute(f"DELETE FROM {t}")
        c.commit()
        _drop_unused_pictures(c, files)
        c.execute("VACUUM")


# ---- public-figure profiles: a cache, since Wikidata is slow. Not personal data; separate from findings. ----

def _cache_table():
    db()                           # the cache table is part of the schema


def cache_get(key, max_age):
    _cache_table()
    with _lock:
        row = db().execute("SELECT fetched, body FROM cache WHERE key = ?", (key,)).fetchone()
    if row and time.time() - row[0] < max_age:
        return {"fetched": row[0], "body": json.loads(row[1])}
    return None


def cache_put(key, body):
    _cache_table()
    with _lock:
        db().execute("INSERT OR REPLACE INTO cache (key, fetched, body) VALUES (?,?,?)", (key, time.time(), json.dumps(body)))
        db().commit()
