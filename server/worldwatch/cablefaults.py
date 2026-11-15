"""Undersea cables with a reported problem. There is no free feed of cable faults, so we read news: SubTel Forum's
"Cable Faults & Maintenance" category (its RSS, about one or two items a week) and the English headlines of our
6-hour GDELT window that say "cable" with a fault word. A cable is marked when a headline names it, matched to
TeleGeography's cable list by whole name, acronym ("AAE-1") or distinctive core ("Kumul"); geographic words alone
("Baltic", "Atlantic") never count. The newest headline decides the state: restored, or a fault / repair.
"""
import html
import re
from email.utils import parsedate_to_datetime

RSS = "https://subtelforum.com/category/cable-faults-maintenance/feed/"
FAULT = re.compile(r"\b(cut|cuts|damage[ds]?|fault[s]?|repair[s]?|repaired|break|broken|sever(ed)?|outage[s]?|disrupt\w*|slowdown|anchor|sabotage\w*|restor\w*|down)\b", re.I)
RESTORED = re.compile(r"\b(restor\w*|repaired|back online|resum\w*)\b", re.I)
GENERIC = {"cable", "cables", "system", "systems", "submarine", "subsea", "network", "domestic", "fiber", "fibre", "optic", "express", "link", "the", "and", "of"}
GEO = {"atlantic", "pacific", "baltic", "baltica", "indian", "ocean", "sea", "north", "south", "east", "west", "asia", "africa", "europe", "america",
       "gulf", "arctic", "red", "mediterranean", "caribbean", "trans", "global", "india", "china", "japan", "korea", "australia", "singapore"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def aliases(cables: list[dict]) -> dict[str, list[str]]:
    """normalised alias -> cable ids; under the key "_exact", one-word names kept in their own spelling ("FASTER",
    "Kumul"), which must appear exactly like that, so the word "Faster" in a headline is not the FASTER cable"""
    out: dict[str, set] = {}
    exact: set[str] = set()
    for c in cables:
        name, cid = c["name"], c["id"]
        names = set()
        for part in name.split("/"):
            part = part.strip()
            names.add(part)
            m = re.search(r"\(([^)]+)\)", part)
            if m:
                names.add(m.group(1))
                names.add(part[:m.start()].strip())
            # "EAC-C2C": two acronyms joined by a hyphen
            ac = re.fullmatch(r"([A-Z0-9]{3,})-([A-Z0-9]{3,})", part)
            if ac:
                names.update(ac.groups())
            core = [w for w in re.findall(r"[\w'-]+", re.sub(r"\([^)]*\)", "", part)) if w.lower() not in GENERIC]
            if len(core) == 1 and core[0].lower() not in GEO and len(core[0]) >= 4:
                names.add(core[0])
        for n in names:
            k = _norm(n)
            if len(k) >= 3 and k not in GEO and not k.isdigit():
                out.setdefault(k, set()).add(cid)
                if n.strip().isalpha():
                    exact.add(n.strip())
    table = {k: sorted(v) for k, v in out.items()}
    table["_exact"] = sorted(exact)
    return table


def match(text: str, table: dict) -> set[str]:
    words = re.findall(r"[\w'-]+", text)
    exact = set(table.get("_exact", ()))
    hits = set()
    for i in range(len(words)):
        for n in range(1, 6):
            if i + n > len(words):
                break
            k = _norm("".join(words[i:i + n]))
            if n == 1 and words[i].isalpha() and words[i] not in exact:
                continue                                  # a plain word must be spelled exactly like the cable's name
            if k in table and k != "_exact":
                hits.update(table[k])
    return hits


def parse_rss(xml: str) -> list[dict]:
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        g = lambda tag: html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", (re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1])).strip()
        try:
            t = parsedate_to_datetime(g("pubDate")).timestamp()
        except (TypeError, ValueError):
            continue
        desc = re.sub(r"<[^>]+>", " ", g("description"))
        out.append({"title": g("title"), "url": g("link"), "time": t, "text": re.sub(r"\s+", " ", desc)[:400], "source": "SubTel Forum"})
    return out


def flag(items: list[dict], cables: list[dict]) -> dict:
    """cable id -> {state, items}"""
    table = aliases(cables)
    names = {c["id"]: c["name"] for c in cables}
    found: dict[str, list] = {}
    for it in items:
        head = it["title"] + " " + it.get("text", "")
        if not FAULT.search(head):
            continue
        for cid in match(it["title"], table) | (match(it.get("text", ""), table) if it.get("source") == "SubTel Forum" else set()):
            found.setdefault(cid, []).append(it)
    out = {}
    for cid, its in found.items():
        its.sort(key=lambda x: -x["time"])
        out[cid] = {"name": names.get(cid), "state": "restored" if RESTORED.search(its[0]["title"]) else "problem", "items": its[:6]}
    return out
