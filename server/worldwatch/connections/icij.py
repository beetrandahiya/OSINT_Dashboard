"""ICIJ Offshore Leaks (Panama, Paradise, Pandora Papers, Offshore Leaks, Bahamas Leaks): the public bulk download
(https://offshoreleaks.icij.org, ODbL; ICIJ asks to be credited and says the data must not be used to identify
private individuals' contact details). Imported once into data/icij.db, replaced whole when ICIJ publishes a new file.

What is kept and what is not (boundaries):
- Companies, foundations, trusts ("entities"), intermediaries (law firms, agents) and other organisations: kept,
  searchable by name.
- Officers (shareholders, directors, beneficiaries): kept as nodes linked to the companies, so ownership can be
  followed. Only officers whose name reads as an organisation (Ltd, Inc, Trust, Bank...) are searchable; a private
  person's name is never searchable on its own, it only appears as a link from a company.
- Addresses: not kept (no residential addresses, no "registered address" links); a company's own registered office
  text from the entities table is kept, as ICIJ shows it on the company's page.
"""
import csv
import io
import re
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from .. import config

URL = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"
KIND = {"entity": 1, "officer": 2, "intermediary": 3, "other": 4}
KIND_NAME = {v: k for k, v in KIND.items()}
ORG = re.compile(r"\b(LTD|LIMITED|INC|INCORPORATED|CORP|CORPORATION|COMPANY|CO\.?|LLC|L\.L\.C|LLP|LP|PLC|S\.?A\.?|S\.?A\.?S|S\.?L|SPA|S\.?P\.?A|"
                 r"GMBH|AG|KG|BV|B\.V|NV|N\.V|AB|AS|A/S|OY|SARL|SRL|SE|PTE|PTY|BHD|SDN|HOLDINGS?|GROUP|TRUST|TRUSTEES?|FOUNDATION|"
                 r"STIFTUNG|ANSTALT|ESTABLISHMENT|BANK|BANQUE|NOMINEES?|INVESTMENTS?|CAPITAL|PARTNERS|VENTURES|ENTERPRISES?|"
                 r"INTERNATIONAL|MANAGEMENT|SERVICES|FUND|ASSOCIATES|CORPORATE|SECRETARIES|DIRECTORS|OVERSEAS|TRADING)\b", re.I)


def db_path() -> Path:
    return config.DATA / "icij.db"


def _date(s):
    s = (s or "").strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.title() if "%b" in fmt else s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s or None


def import_zip(zip_path: str) -> dict:
    """Build data/icij.db.new from the zip, then move it over data/icij.db. Runs in the helper process."""
    out = db_path().with_suffix(".db.new")
    out.unlink(missing_ok=True)
    c = sqlite3.connect(out)
    c.executescript("""
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
      CREATE TABLE node (id INTEGER PRIMARY KEY, kind INTEGER, name TEXT, jur TEXT, countries TEXT, source TEXT,
                         inc TEXT, gone TEXT, status TEXT, ctype TEXT, provider TEXT, addr TEXT);
      CREATE TABLE rel (a INTEGER, b INTEGER, type TEXT, link TEXT, start TEXT, end TEXT, source TEXT);
      CREATE VIRTUAL TABLE names USING fts5(name, id UNINDEXED, tokenize='unicode61 remove_diacritics 2');
    """)
    counts = {}
    z = zipfile.ZipFile(zip_path)
    generated = next((n[13:21] for n in z.namelist() if n.startswith("GENERATED_ON_")), None)

    def rows(name):
        with z.open(name) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", newline=""))

    def load(name, kind, conv):
        batch, fts, n = [], [], 0
        for r in rows(name):
            try:
                nid = int(r["node_id"])
            except (ValueError, KeyError):
                continue
            rec = conv(r)
            batch.append((nid, kind, *rec))
            nm = rec[0] or ""
            if nm and (kind != KIND["officer"] or ORG.search(nm)):
                fts.append((nm, nid))
            if len(batch) >= 5000:
                c.executemany("INSERT OR IGNORE INTO node VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                c.executemany("INSERT INTO names (name, id) VALUES (?,?)", fts)
                n += len(batch); batch, fts = [], []
        c.executemany("INSERT OR IGNORE INTO node VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        c.executemany("INSERT INTO names (name, id) VALUES (?,?)", fts)
        counts[name] = n + len(batch)

    load("nodes-entities.csv", KIND["entity"], lambda r: (
        r.get("name"), r.get("jurisdiction_description") or r.get("jurisdiction"), r.get("countries"), r.get("sourceID"),
        _date(r.get("incorporation_date")), _date(r.get("inactivation_date") or r.get("struck_off_date") or r.get("dorm_date")),
        r.get("status"), r.get("company_type"), r.get("service_provider"), r.get("address")))
    load("nodes-officers.csv", KIND["officer"], lambda r: (r.get("name"), None, r.get("countries"), r.get("sourceID"), None, None, None, None, None, None))
    load("nodes-intermediaries.csv", KIND["intermediary"], lambda r: (r.get("name"), None, r.get("countries"), r.get("sourceID"), None, None, r.get("status"), None, None, None))
    load("nodes-others.csv", KIND["other"], lambda r: (
        r.get("name"), r.get("jurisdiction_description") or r.get("jurisdiction"), r.get("countries"), r.get("sourceID"),
        _date(r.get("incorporation_date")), _date(r.get("closed_date") or r.get("struck_off_date")), None, r.get("type"), None, None))
    batch, n = [], 0
    for r in rows("relationships.csv"):
        if r.get("rel_type") == "registered_address":
            continue                                    # addresses are not kept (see above)
        try:
            batch.append((int(r["node_id_start"]), int(r["node_id_end"]), r.get("rel_type"), r.get("link"),
                          _date(r.get("start_date")), _date(r.get("end_date")), r.get("sourceID")))
        except (ValueError, KeyError):
            continue
        if len(batch) >= 10000:
            c.executemany("INSERT INTO rel VALUES (?,?,?,?,?,?,?)", batch); n += len(batch); batch = []
    c.executemany("INSERT INTO rel VALUES (?,?,?,?,?,?,?)", batch)
    counts["relationships.csv"] = n + len(batch)
    # links whose ends are not in the tables (address nodes) are useless here
    c.execute("DELETE FROM rel WHERE a NOT IN (SELECT id FROM node) OR b NOT IN (SELECT id FROM node)")
    c.executescript("CREATE INDEX rel_a ON rel(a); CREATE INDEX rel_b ON rel(b);")
    c.execute("CREATE TABLE info (key TEXT PRIMARY KEY, value TEXT)")
    c.executemany("INSERT INTO info VALUES (?,?)", [("generated", generated or ""), ("rels", str(c.execute("SELECT count(*) FROM rel").fetchone()[0]))])
    c.commit(); c.execute("VACUUM"); c.close()
    out.replace(db_path())
    return {"generated": generated, "counts": counts}
