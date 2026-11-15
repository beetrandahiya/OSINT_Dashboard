"""Court records for person dossiers, from official public sources only.

- International Criminal Court: its case list (every defendant, with the court's own status: at large, in custody,
  convicted, acquitted, closed...) and its situation pages, which name people the judges issued arrest warrants
  for (Putin, Netanyahu, Akhundzada...) or the Prosecutor asked warrants for. Read once a day (feed `courts_icc`).
- England and Wales: The National Archives' Find Case Law (Open Justice Licence), asked when a dossier opens: cases
  where the person is a named party, and judgments that mention the name. Judgments only, no filings or dockets,
  and only since ~2001 for most courts.
- Wikidata: "convicted of" (P1399) and "charge" (P1595) where editors recorded them.

Matching is by name, so a common name can match someone else; the dossier shows the court's own words and a link
for every hit and says so. Nothing is scored or summarised.
"""
import html
import json
import re
import time
import unicodedata

from . import config

ICC = "https://www.icc-cpi.int"
UK = "https://caselaw.nationalarchives.gov.uk/atom.xml"
# the situations the ICC has open or has had (its own URL names); a page that fails is skipped and named in the note
SITUATIONS = ["afghanistan", "bangladesh-myanmar", "burundi", "car", "carII", "cdi", "darfur", "drc", "georgia", "kenya", "libya",
              "mali", "palestine", "philippines", "uganda", "ukraine", "venezuela", "lithuania-belarus", "nigeria"]


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def text_of(fragment: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S)
    t = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace(" ", " ")
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t)).strip()


def parse_cases(page: str) -> list[dict]:
    """One page of the ICC case list: short name, link, status as the court words it, the court's summary."""
    if is_challenge(page):
        raise RuntimeError("the ICC site answered with its bot-protection page")
    out = []
    for card in page.split('<div class="card-header">')[1:]:
        m = re.search(r'<h5[^>]*>\s*<a href="([^"]+)"[^>]*>([^<]+)</a>', card)
        if not m:
            continue
        status = re.search(r'defendant_status_button[^"]*">\s*([^<]+?)\s*</div>', card)
        about = re.search(r'<div class="aboutDefendant">(.*?)</div>', card, re.S)
        img = re.search(r'<img[^>]+src="([^"]+)"', card)
        out.append({"name": html.unescape(m.group(2)).strip(), "url": ICC + m.group(1), "status": status.group(1).strip() if status else None,
                    "text": text_of(about.group(1)) if about else "", "image": ICC + img.group(1) if img else None})
    return out


def is_challenge(page: str) -> bool:
    """The site's bot shield (Gcore) answers 200 with a cookie page instead of the content."""
    return ("Please enable cookies" in page or "uses a security service to protect itself" in page) and "aboutDefendant" not in page and "Breadcrumb" not in page


SAVED = config.DATA / "icc-situations.json"


def load_situations() -> dict:
    try:
        return json.loads(SAVED.read_text())
    except (OSError, ValueError):
        return {}


def save_situations(d: dict) -> None:
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    SAVED.write_text(json.dumps(d))


def parse_situation(page: str) -> dict:
    title = re.search(r"<title>([^<|]+)", page)
    main = re.search(r"<main.*?</main>", page, re.S)
    t = text_of(main.group(0) if main else page)
    return {"title": html.unescape(title.group(1)).strip() if title else None, "text": t[:60000]}


# ---------------------------------------------------------------- matching a person to the texts
def name_patterns(names: list[str]) -> list[re.Pattern]:
    """For each name of two words or more: first and last word within three words of each other
    ("Vladimir Vladimirovich Putin" matches "Vladimir Putin")."""
    pats = []
    for n in names:
        w = re.findall(r"[\w'-]+", fold(n))
        if len(w) < 2:
            continue
        pats.append(re.compile(r"\b" + re.escape(w[0]) + r"\b(?:\W+[\w'-]+){0,3}?\W+" + re.escape(w[-1]) + r"\b"))
    return pats


def sentences(text: str, pats: list[re.Pattern], limit=4) -> list[str]:
    out = []
    for s in re.split(r"(?<=[.;])\s+(?=[A-Z0-9“\"])|\n", text):
        if any(p.search(fold(s)) for p in pats):
            out.append(s.strip())
            if len(out) >= limit:
                break
    return out


def icc_matches(payload: dict, names: list[str]) -> dict:
    pats = name_patterns(names)
    if not pats or not payload:
        return {"cases": [], "situations": []}
    cases = []
    for c in payload.get("cases", []):
        said = sentences(c["text"], pats, 3)
        if said:
            cases.append({**{k: c[k] for k in ("name", "url", "status", "image")}, "said": said})
    sits = []
    for s in payload.get("situations", []):
        said = sentences(s["text"], pats, 4)
        if said:
            sits.append({"title": s["title"], "url": s["url"], "said": said})
    return {"cases": cases, "situations": sits}


# ---------------------------------------------------------------- England and Wales
def parse_uk_atom(xml: str) -> tuple[list[dict], int]:
    """Entries and the number of the last results page."""
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        g = lambda pat: (re.search(pat, e, re.S) or [None, None])[1]
        out.append({"title": html.unescape(g(r"<title>(.*?)</title>") or "").strip(), "url": g(r'<link href="([^"]+)" rel="alternate"/>'),
                    "court": html.unescape(g(r"<author><name>(.*?)</name>") or ""), "date": (g(r"<published>(.*?)</published>") or "")[:10],
                    "citation": html.unescape(g(r'type="ukncn">(.*?)</tna:identifier>') or "") or None})
    last = re.search(r'page=(\d+)" rel="last"', xml)
    return out, int(last.group(1)) if last else 1


def wd_claims(entity: dict, prop: str) -> list[str]:
    return [c["mainsnak"]["datavalue"]["value"]["id"] for c in entity.get("claims", {}).get(prop, [])
            if c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")]


def now() -> float:
    return time.time()
