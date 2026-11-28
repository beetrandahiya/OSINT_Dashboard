"""Sanctioned companies and organisations, from OpenSanctions' sanctions file (the same weekly download the map's
sanctioned-ships layer reads; free for non-commercial use, CC BY-NC 4.0). Kept in data/connections.db so any entity
in an ownership chain can be flagged.

A match on an LEI code is a match. A match on the exact name (letters and digits only, case-folded) is shown as
"same name", which may be someone else: the page says so."""
import csv
import json
import re
import sqlite3

from . import store

LEI = re.compile(r"\b[0-9A-Z]{18}[0-9]{2}\b")
KEEP = {"Company", "Organization", "LegalEntity", "PublicBody"}


def norm(s):
    return re.sub(r"[^0-9a-z]+", "", (s or "").lower())


def build_from_csv(path: str) -> int:
    """Read the targets file row by row and replace the table. Runs in the helper process."""
    c = sqlite3.connect(store.path())
    c.executescript("""
      DROP TABLE IF EXISTS sanc; DROP TABLE IF EXISTS sanc_names;
      CREATE TABLE sanc (id TEXT PRIMARY KEY, schema TEXT, name TEXT, aliases TEXT, countries TEXT, identifiers TEXT,
                         sanctions TEXT, datasets TEXT, first_seen TEXT, last_change TEXT);
      CREATE TABLE sanc_names (key TEXT, id TEXT);
      CREATE VIRTUAL TABLE IF NOT EXISTS sanc_fts USING fts5(name, id UNINDEXED, tokenize='unicode61 remove_diacritics 2');
      DELETE FROM sanc_fts;
    """)
    n, batch, keys, fts = 0, [], [], []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("schema") not in KEEP:
                continue
            batch.append((r.get("id"), r.get("schema"), r.get("name"), r.get("aliases"), r.get("countries"), r.get("identifiers"),
                          (r.get("sanctions") or "")[:600], r.get("dataset"), r.get("first_seen"), r.get("last_change")))
            for nm in [r.get("name")] + (r.get("aliases") or "").split(";")[:6]:
                if nm and len(norm(nm)) >= 4:
                    keys.append((norm(nm), r.get("id")))
            fts.append((" ".join(x for x in [r.get("name"), (r.get("aliases") or "").replace(";", " ")[:300]] if x), r.get("id")))
            if len(batch) >= 2000:
                c.executemany("INSERT OR REPLACE INTO sanc VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
                c.executemany("INSERT INTO sanc_names VALUES (?,?)", keys); c.executemany("INSERT INTO sanc_fts (name, id) VALUES (?,?)", fts)
                n += len(batch); batch, keys, fts = [], [], []
    c.executemany("INSERT OR REPLACE INTO sanc VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
    c.executemany("INSERT INTO sanc_names VALUES (?,?)", keys); c.executemany("INSERT INTO sanc_fts (name, id) VALUES (?,?)", fts)
    c.execute("CREATE INDEX IF NOT EXISTS sanc_key ON sanc_names(key)")
    c.commit(); c.close()
    return n + len(batch)


def _titles():
    from ..lookup import store as lstore
    return (lstore.cache_get("os-datasets", 60 * 86400) or {}).get("body") or {}


def _row(r, how):
    t = _titles()
    lists = [d for d in (r["datasets"] or "").split(";") if d]
    return {"ref": "os:" + r["id"], "id": r["id"], "name": r["name"], "countries": r["countries"], "match": how,
            "lists": [(t.get(d) or {}).get("title", d) if isinstance(t.get(d), dict) else (t.get(d) or d) for d in lists][:8],
            "sanctions": r["sanctions"], "url": "https://www.opensanctions.org/entities/" + r["id"], "since": (r["first_seen"] or "")[:10]}


def ready() -> bool:
    try:
        return store.has_table("sanc")
    except sqlite3.Error:
        return False


def get(sid):
    if not ready():
        return None
    r = store.db().execute("SELECT * FROM sanc WHERE id = ?", (sid,)).fetchone()
    return dict(r) if r else None


def match(leis, name, country=None) -> list:
    if not ready():
        return []
    db, out, seen = store.db(), [], set()
    for lei in leis or []:
        for r in db.execute("SELECT * FROM sanc WHERE identifiers LIKE ?", (f"%{lei}%",)):
            if r["id"] not in seen:
                seen.add(r["id"]); out.append(_row(r, "LEI " + lei))
    k = norm(name)
    if len(k) >= 4:
        for r in db.execute("SELECT s.* FROM sanc_names n JOIN sanc s ON s.id = n.id WHERE n.key = ? LIMIT 10", (k,)):
            if r["id"] not in seen:
                seen.add(r["id"]); out.append(_row(r, "same name (may be someone else)"))
    return out


def search(q, limit=15) -> list:
    if not ready():
        return []
    words = [w for w in re.findall(r"\w+", q, re.UNICODE) if len(w) > 1][:6]
    if not words:
        return []
    rows = store.db().execute("SELECT s.* FROM sanc_fts f JOIN sanc s ON s.id = f.id WHERE sanc_fts MATCH ? ORDER BY rank LIMIT ?",
                              (" ".join(f'"{w}"*' for w in words), limit)).fetchall()
    return [_row(r, "name search") for r in rows]


def leis_of(row) -> list:
    return sorted(set(LEI.findall((row or {}).get("identifiers") or "")))
