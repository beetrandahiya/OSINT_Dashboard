"""Dossiers: a country, or a public figure's live signals, put together from what our own feeds hold right now.

Nothing here invents a number. Every section is a count or a list of items from one named feed, with that
feed's age, so the page can say where each line comes from. Countries are matched to feed items in three ways,
always the one the source itself supports:
- by code: GDELT events carry a FIPS country code, IODA an ISO code, flight regions an ICAO prefix;
- by outline: positions (aircraft, ships, news places, quakes) are tested against Natural Earth's outline,
  with a short margin for coastal cities (see geo.py);
- by name: GDACS lists country names, FAA and EASA name countries in their titles.
There is no history store yet, so nothing here can say what changed since yesterday.
"""
import asyncio
import math
import re
import time

import httpx
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import config, courts, db, geo, navwarn
from . import news as news_window
from .ais import stream as ais_stream
from .lookup import store

WDQS = "https://query.wikidata.org/sparql"
_FACT_PROPS = {"P36": "capital", "P1082": "population", "P122": "government", "P35": "head_of_state", "P6": "head_of_government",
               "P37": "languages", "P38": "currency", "P2046": "area", "P2131": "gdp", "P463": "member_of"}
# Tags in plane-alert-db that stand for an office rather than a name
_OFFICE_TAGS = {"POTUS": "President of the United States", "Air Force One": "President of the United States",
                "VPOTUS": "Vice President of the United States", "Air Force Two": "Vice President of the United States"}


def _wm_headers() -> dict:
    who = config.contact()
    return {"User-Agent": f"WorldWatch/0.1 (personal non-commercial dashboard{'; ' + who if who else ''})", "Accept": "application/sparql-results+json"}


def _feed(collector, name: str):
    """A feed's payload plus what the page needs to say about its age."""
    st = collector.states.get(name)
    if not st:
        return None, {"feed": name, "state": "missing"}
    pub = st.public(time.time())
    return st.payload, {"feed": name, "layer": pub["layer"], "source": pub["source"], "state": pub["state"], "fetched": pub["fetched"],
                        "data_time": pub["data_time"], "data_label": pub["data_label"], "error": pub["error"]}


# ---------------------------------------------------------------- Wikidata facts about a country (cached 30 days)
async def _facts(qid: str) -> tuple[dict | None, str | None, float | None]:
    key = "country-facts:" + qid
    hit = await asyncio.to_thread(db.lookup_get, key, 30 * 86400)
    if hit:
        return hit["body"], None, hit["fetched"]
    values = " ".join("p:" + p for p in _FACT_PROPS)
    q = f"""SELECT ?prop ?v ?vLabel ?t ?start ?end ?coord ?unitLabel WHERE {{
      VALUES ?prop {{ {values} }}
      wd:{qid} ?prop ?st. ?st ?ps ?v. FILTER(STRSTARTS(STR(?ps),"http://www.wikidata.org/prop/statement/P"))
      ?st wikibase:rank ?rank. FILTER(?rank != wikibase:DeprecatedRank)
      OPTIONAL {{ ?st pq:P585 ?t }} OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
      OPTIONAL {{ ?v wdt:P625 ?coord. FILTER(?prop = p:P36) }}
      OPTIONAL {{ ?st ?psv ?vn. FILTER(STRSTARTS(STR(?psv),"http://www.wikidata.org/prop/statement/value/P")) ?vn wikibase:quantityUnit ?unit }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
    try:
        async with httpx.AsyncClient(timeout=30, headers=_wm_headers()) as c:
            for attempt in range(2):
                r = await c.get(WDQS, params={"query": q})
                if r.status_code == 429 and attempt == 0:
                    await asyncio.sleep(min(10.0, float(r.headers.get("Retry-After", 5))))
                    continue
                break
        if r.status_code != 200:
            raise httpx.HTTPError(f"the query service answered {r.status_code}")
        rows = r.json()["results"]["bindings"]
    except (httpx.HTTPError, ValueError, KeyError) as e:
        # The query service is often throttled; the item's own JSON comes from the regular site, which is not.
        try:
            out = await _facts_entity(qid)
        except (httpx.HTTPError, ValueError, KeyError) as e2:
            return None, f"Wikidata could not be asked ({e}; then {type(e2).__name__})", None
        await asyncio.to_thread(db.lookup_put, key, time.time(), out)
        return out, None, time.time()
    v = lambda x, k: x.get(k, {}).get("value")
    qid_of = lambda u: u.rsplit("/", 1)[-1] if u and u.startswith("http://www.wikidata.org/entity/") else None
    out: dict = {k: [] for k in _FACT_PROPS.values()}
    for x in rows:
        kind = _FACT_PROPS.get(v(x, "prop").rsplit("/", 1)[-1])
        if not kind or v(x, "end"):                                  # only what is current (no end date)
            continue
        rec = {"value": v(x, "v"), "label": v(x, "vLabel"), "qid": qid_of(v(x, "v")), "date": (v(x, "t") or "")[:10] or None,
               "since": (v(x, "start") or "")[:10] or None, "unit": v(x, "unitLabel")}
        if v(x, "coord"):
            try:
                lon, lat = map(float, v(x, "coord").removeprefix("Point(").removesuffix(")").split())
                rec["lon"], rec["lat"] = lon, lat
            except ValueError:
                pass
        if rec not in out[kind]:
            out[kind].append(rec)
    for kind in ("population", "gdp", "area"):                       # one figure: the newest dated one
        recs = sorted(out[kind], key=lambda r: r["date"] or "", reverse=True)
        out[kind] = recs[0] if recs else None
    for kind in ("capital", "head_of_state", "head_of_government", "government", "languages", "currency", "member_of"):
        seen, keep = set(), []
        for r in out[kind]:
            if r["value"] not in seen and r["qid"]:
                seen.add(r["value"])
                keep.append(r)
        out[kind] = keep
    await asyncio.to_thread(db.lookup_put, key, time.time(), out)
    return out, None, time.time()


async def _facts_entity(qid: str) -> dict:
    """The same facts read from the item's JSON (Special:EntityData) plus one call for labels and the capital's position."""
    async with httpx.AsyncClient(timeout=30, headers=_wm_headers(), follow_redirects=True) as c:
        r = await c.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
        r.raise_for_status()
        claims = r.json()["entities"][qid]["claims"]
        out, need = {}, set()
        qual = lambda st, p: (((st.get("qualifiers") or {}).get(p) or [{}])[0].get("datavalue") or {}).get("value")
        for pid, kind in _FACT_PROPS.items():
            recs = []
            for st in claims.get(pid, []):
                if st.get("rank") == "deprecated" or qual(st, "P582"):
                    continue
                v = (st.get("mainsnak", {}).get("datavalue") or {}).get("value")
                t = ((qual(st, "P585") or {}).get("time") or "").lstrip("+")[:10] or None
                since = ((qual(st, "P580") or {}).get("time") or "").lstrip("+")[:10] or None
                if isinstance(v, dict) and "id" in v:
                    recs.append({"value": v["id"], "label": None, "qid": v["id"], "date": t, "since": since, "unit": None, "rank": st.get("rank")})
                    need.add(v["id"])
                elif isinstance(v, dict) and "amount" in v:
                    unit = v.get("unit", "").rsplit("/", 1)[-1]
                    recs.append({"value": v["amount"].lstrip("+"), "label": None, "qid": None, "date": t, "since": since, "unit": unit, "rank": st.get("rank")})
                    if unit.startswith("Q"):
                        need.add(unit)
            out[kind] = recs
        labels, coords = {}, {}
        ids = sorted(need)
        for i in range(0, len(ids), 50):
            r = await c.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]),
                                                                       "props": "labels|claims", "languages": "en", "format": "json"})
            r.raise_for_status()
            for q, e in r.json().get("entities", {}).items():
                labels[q] = ((e.get("labels") or {}).get("en") or {}).get("value")
                pt = ((((e.get("claims") or {}).get("P625") or [{}])[0].get("mainsnak") or {}).get("datavalue") or {}).get("value")
                if isinstance(pt, dict) and "latitude" in pt:
                    coords[q] = (pt["longitude"], pt["latitude"])
    for kind, recs in out.items():
        for rec in recs:
            if rec["qid"]:
                rec["label"] = labels.get(rec["qid"]) or rec["qid"]
            if rec["unit"] and rec["unit"].startswith("Q"):
                rec["unit"] = labels.get(rec["unit"]) or rec["unit"]
            elif rec["unit"] == "1":
                rec["unit"] = None
            if kind == "capital" and rec["qid"] in coords:
                rec["lon"], rec["lat"] = coords[rec["qid"]]
    for kind in ("population", "gdp", "area"):
        recs = sorted(out[kind], key=lambda r: (r["rank"] == "preferred", r["date"] or ""), reverse=True)
        out[kind] = recs[0] if recs else None
    for kind in ("capital", "head_of_state", "head_of_government", "government", "languages", "currency", "member_of"):
        out[kind] = [r for r in out[kind] if r["qid"]]
    out["via"] = "the item's own data (the query service was busy)"
    return out


# ---------------------------------------------------------------- aircraft positions across our feeds
def _positions(collector) -> dict[str, dict]:
    """Newest known position per transponder address across every aircraft feed we hold."""
    out = {}
    for name in ("aircraft_world", "aircraft_military", "aircraft_near"):
        p, meta = _feed(collector, name)
        for a in (p or {}).get("aircraft", []):
            if a.get("lat") is None:
                continue
            t = a.get("last_contact") or ((meta["data_time"] or 0) - (a.get("seen_pos_s") or 0))
            ground = a.get("on_ground") if "on_ground" in a else a.get("alt_ft") == "ground"
            old = out.get(a["hex"])
            if not old or t > old["time"]:
                alt = a.get("alt_ft") if isinstance(a.get("alt_ft"), (int, float)) else (round(a["alt_m"] * 3.281) if a.get("alt_m") is not None else None)
                out[a["hex"]] = {"hex": a["hex"], "lat": a["lat"], "lon": a["lon"], "time": t, "ground": bool(ground), "alt_ft": alt,
                                 "flight": a.get("flight"), "military": a.get("military", name == "aircraft_military"), "feed": name}
    return out


def _flag_of(collector, hex_: str) -> str | None:
    """Country of registration from the ICAO address block (feed "flags")."""
    p, _ = _feed(collector, "flags")
    rows = (p or {}).get("icao") or []
    try:
        n = int(hex_, 16)
    except ValueError:
        return None
    lo, hi = 0, len(rows) - 1
    while lo <= hi:
        m = (lo + hi) // 2
        if n < rows[m][0]:
            hi = m - 1
        elif n > rows[m][1]:
            lo = m + 1
        else:
            return rows[m][2]
    return None


# ---------------------------------------------------------------- country dossier
def _in(iso: str, place: str, lon, lat) -> bool:
    """A GDELT place in the country: inside the outline or within 25 km of it, unless the place's own last part
    names another country ("Tulcea, Tulcea, Romania" is 5 km from Ukraine and stays Romanian)."""
    named = geo.by_name((place or "").split(",")[-1])
    return (named is None or named == iso) and geo.around(iso, lon, lat, 25)


def _airspace_for(iso: str, payload) -> list[dict]:
    out = []
    for z in (payload or {}).get("zones", []):
        firs = [f for f in z.get("firs", []) if geo.by_icao(f) == iso]
        named = geo.by_name(re.sub(r"^Airspace of (the )?", "", (z.get("country") or z.get("title") or "")).split(" – ")[0].strip()) == iso
        if firs or named:
            out.append({"id": z["id"], "source": z["source"], "title": z.get("title"), "level": z.get("level"), "number": z.get("number"),
                        "issued": z.get("issued"), "revised": z.get("revised"), "valid_until": z.get("valid_until"), "affected": z.get("affected"),
                        "link": z.get("link"), "firs": firs or z.get("firs", []), "pick": ("FIR:" + next(iter(z.get("shapes") or {}), "")) if z.get("shapes") else None,
                        "docs": [d["title"] for d in z.get("docs", [])][:3]})
    return out


def country(collector, iso: str) -> dict:
    """Everything our feeds hold about one country right now (the slow Wikidata part is added by the route)."""
    c = geo.C[iso]
    fips = set(c["fips"])
    now = time.time()
    feeds, out = {}, {}

    # travel advice
    p, feeds["travel_advice"] = _feed(collector, "travel_advice")
    out["travel"] = {"us": (p or {}).get("us", {}).get(iso, []), "de": (p or {}).get("de", {}).get(iso, [])}

    # protests and clashes (GDELT codes countries in FIPS)
    p, feeds["unrest"] = _feed(collector, "unrest")
    groups = [g for g in (p or {}).get("groups", []) if g.get("country") in fips]
    groups.sort(key=lambda g: -g["outlets"])
    cats = {}
    for g in groups:
        k = cats.setdefault(g["cat"], {"groups": 0, "two_plus": 0})
        k["groups"] += 1
        k["two_plus"] += g["outlets"] >= 2
    out["unrest"] = {"total": len(groups), "two_plus": sum(g["outlets"] >= 2 for g in groups), "by_kind": cats,
                     "top": [{"id": g["id"], "layer": "unrest" if g["outlets"] >= 2 else "unrest1", "place": g["place"], "cat": g["cat"], "action": g["action"],
                              "outlets": g["outlets"], "last": g["last"], "title": next((a["title"] for a in g.get("articles", []) if a.get("title")), None)}
                             for g in groups[:10]]}

    # airspace
    p, feeds["airspace"] = _feed(collector, "airspace")
    out["airspace"] = _airspace_for(iso, p)
    tfrs = (p or {}).get("tfrs", []) if iso == "US" else []
    out["tfrs"] = {"total": len(tfrs), "kinds": sorted({t.get("type") or "?" for t in tfrs}),
                   "top": [{"id": t["id"], "type": t.get("type"), "where": t.get("where")} for t in tfrs[:6]]}

    # navy warnings within 300 km of the coast
    p, feeds["navwarn"] = _feed(collector, "navwarn")
    nw = []
    for w in (p or {}).get("warnings", []):
        ctr = navwarn.centre(w.get("geoms") or [])
        d = geo.near(iso, ctr[0], ctr[1], 300) if ctr else None
        if d is not None:
            nw.append({"id": w["id"], "ref": w.get("ref"), "kind": w.get("kind"), "area": w.get("area"), "km": round(d), "text": (w.get("text") or "")[:220]})
    out["navwarn"] = {"items": nw, "sources": (p or {}).get("sources", []), "problems": (p or {}).get("problems", [])}

    # internet outages
    p, feeds["outages"] = _feed(collector, "outages")
    out["outages"] = [{"id": e["id"], "start": e["start"], "duration_s": e["duration_s"], "signal": e["signal"]}
                      for e in (p or {}).get("events", []) if e.get("code") == iso]

    # earthquakes inside or within 100 km
    p, feeds["quakes"] = _feed(collector, "quakes")
    qs = []
    for q in (p or {}).get("quakes", []):
        d = geo.near(iso, q["lon"], q["lat"], 100)
        if d is not None:
            qs.append({"id": q["id"], "mag": q["mag"], "place": q["place"], "time": q["time"], "km": round(d), "depth_km": q.get("depth_km")})
    qs.sort(key=lambda q: -(q["mag"] or 0))
    out["quakes"] = {"total": len(qs), "top": qs[:8]}

    # disasters: GDACS by country name, EONET by position
    hz = []
    p, feeds["gdacs"] = _feed(collector, "gdacs")
    for e in (p or {}).get("events", []):
        names = [n.strip() for n in (e.get("countries") or "").split(",") if n.strip()]
        if any(geo.by_name(n) == iso for n in names) or geo.around(iso, e["lon"], e["lat"], 50):
            hz.append({"id": e["id"], "kind": e["kind"], "level": e.get("level"), "name": e["name"], "severity": e.get("severity"), "source": "GDACS"})
    p, feeds["eonet"] = _feed(collector, "eonet")
    for e in (p or {}).get("events", []):
        if geo.around(iso, e["lon"], e["lat"], 50):
            hz.append({"id": e["id"], "kind": e["kind"], "level": None, "name": e["name"], "severity": e.get("severity"), "source": "NASA EONET"})
    out["hazards"] = hz

    # aircraft over the country: VIP / government / doomsday by name in plane-alert-db, and the military count
    vip, feeds["vip_aircraft"] = _feed(collector, "vip_aircraft")
    vip = (vip or {}).get("aircraft", {})
    for n in ("aircraft_world", "aircraft_military"):
        feeds[n] = _feed(collector, n)[1]
    pos = _positions(collector)
    over, mil = [], []
    for h, a in pos.items():
        if not geo.contains(iso, a["lon"], a["lat"]):
            continue
        if h in vip:
            v = vip[h]
            over.append({**a, "reg": v.get("reg"), "operator": v.get("operator"), "type": v.get("type"), "category": v.get("category"), "tags": v.get("tags"),
                         "layer": "doomsday" if v.get("category") == "Doomsday" else "vip"})
        elif a["military"]:
            mil.append(a)
    over.sort(key=lambda a: (a["ground"], -a["time"]))
    out["aircraft"] = {"vip": over[:20], "vip_total": len(over), "military": len(mil), "military_airborne": sum(not a["ground"] for a in mil),
                       "military_top": sorted(mil, key=lambda a: -a["time"])[:8]}

    # warships: AIS type 35 within 200 km, and USNI's carriers within 600 km (USNI places them only approximately)
    sp, feeds["ships"] = _feed(collector, "ships")
    ships = {s["mmsi"]: s for s in (sp or {}).get("ships", [])}
    for s in ais_stream.ships():
        if s["mmsi"] not in ships or s["time"] > ships[s["mmsi"]]["time"]:
            ships[s["mmsi"]] = s
    ws = []
    for s in ships.values():
        if s.get("kind") == "Military vessel":
            d = geo.near(iso, s["lon"], s["lat"], 200)
            if d is not None:
                ws.append({"id": "ship:" + str(s["mmsi"]), "name": s.get("name"), "km": round(d), "time": s["time"], "speed_kn": s.get("speed_kn")})
    up, feeds["usni_fleet"] = _feed(collector, "usni_fleet")
    carriers = []
    for s in (up or {}).get("ships", []):
        if s.get("lat") is None:
            continue
        d = geo.near(iso, s["lon"], s["lat"], 600)
        if d is not None:
            carriers.append({"id": "usni:" + s["hull"], "name": s["name"], "hull": s["hull"], "kind": s["kind"], "region": s.get("region"),
                             "port": s.get("port"), "placed": s.get("placed"), "km": round(d)})
    out["ships"] = {"warships": ws[:15], "warships_total": len(ws), "carriers": carriers, "ais_world": ais_stream.status().get("state"),
                    "usni_title": (up or {}).get("title"), "usni_published": (up or {}).get("published")}

    # leaders the news placed inside the country in the last 6 hours
    lh = store.cache_get("leaders", 30 * 86400)
    today = news_window.leaders_today(lh["body"]) if lh else []
    out["leaders_today"] = [{"qid": t["qid"], "name": t["name"], "role": t["role"], "country": t["country"], "place": t["place"]["place"],
                             "outlets": t["place"]["outlets"], "headlines": t["place"]["headlines"], "abroad": t["abroad"]}
                            for t in today if _in(iso, t["place"]["place"], t["place"]["lon"], t["place"]["lat"])]
    feeds["leaders_today"] = {"feed": "news", "layer": "Leaders today", "source": "GDELT + Wikidata leaders list", "state": "ok" if lh else "waiting",
                              "fetched": lh and lh["fetched"], "data_time": news_window.english.newest(), "data_label": None, "error": None}

    # Maxar disaster imagery whose area centre lies in or near the country
    mp, feeds["maxar_events"] = _feed(collector, "maxar_events")
    mx = []
    for e in (mp or {}).get("events", []):
        b = e.get("bbox")
        others = geo.named(e["title"]) - {iso}
        if b and b[0] is not None and geo.contains(iso, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2) and (not others or iso in geo.named(e["title"])):
            mx.append({"id": "mx:" + e["id"], "title": e["title"], "start": e.get("start"), "end": e.get("end"), "acquisitions": e.get("acquisitions")})
    out["maxar"] = mx

    # news places in the country, English and translated windows together
    places, outlets_total = {}, 0
    for name in ("news", "news_translated"):
        p, feeds[name] = _feed(collector, name)
        for pl in (p or {}).get("places", []):
            if not _in(iso, pl["place"], pl["lon"], pl["lat"]):
                continue
            k = places.setdefault(pl["place"], {"place": pl["place"], "lat": pl["lat"], "lon": pl["lon"], "outlets": 0, "last": 0, "articles": []})
            k["outlets"] += pl["outlets"]
            k["last"] = max(k["last"], pl["last"])
            k["articles"] += pl["articles"][:3]
            outlets_total += pl["outlets"]
    top = sorted(places.values(), key=lambda p: -p["outlets"])[:10]
    for p in top:
        p["articles"] = sorted(p["articles"], key=lambda a: (a.get("lang") != "eng" and not a.get("translated"), -(a.get("image") is not None), -a["time"]))[:3]
    out["news"] = {"places": len(places), "outlets": outlets_total, "top": top}

    out["feeds"] = feeds
    out["geo"] = geo.public(iso)
    out["now"] = now
    return out


async def countries(request):
    if not await geo.ensure():
        return JSONResponse({"error": "the country table could not be built (Natural Earth or VATSpy did not answer)"}, status_code=502)
    return JSONResponse({"countries": geo.listing()}, headers={"Cache-Control": "private, max-age=86400"})


def make_routes(collector):
    async def country_route(request):
        if not await geo.ensure():
            return JSONResponse({"error": "the country table could not be built (Natural Earth or VATSpy did not answer)"}, status_code=502)
        q = request.query_params
        iso = (q.get("cc") or "").upper() or geo.by_fips(q.get("fips")) or geo.by_icao(q.get("icao")) or geo.by_name(q.get("name")) or geo.by_qid(q.get("qid"))
        if iso not in geo.C and q.get("lat") and q.get("lon"):
            try:
                iso = geo.where(float(q["lon"]), float(q["lat"]))
            except ValueError:
                pass
        if iso not in geo.C:
            return JSONResponse({"error": "no such country in the table", "asked": dict(q)}, status_code=404)
        body = await asyncio.to_thread(country, collector, iso)
        c = geo.C[iso]
        facts, problem, fetched = (await _facts(c["qid"])) if c.get("qid") else (None, "no Wikidata id for this country", None)
        body.update(iso=iso, name=c["name"], qid=c.get("qid"), facts=facts, facts_problem=problem, facts_fetched=fetched)
        if not facts:          # heads of state and government from the cached leaders list, which is also Wikidata's
            lh = store.cache_get("leaders", 30 * 86400)
            body["heads"] = [{"qid": l["qid"], "label": l["name"], "role": l["role"]} for l in (lh or {}).get("body", []) if geo.by_name(l["country"]) == iso]
        return JSONResponse(body, headers={"Cache-Control": "no-store"})

    async def person_route(request):
        qid = request.path_params["qid"]
        if not re.fullmatch(r"Q\d{1,12}", qid):
            return JSONResponse({"error": "not a Wikidata id"}, status_code=400)
        await geo.ensure()
        return JSONResponse(await asyncio.to_thread(person, collector, qid, request.query_params.get("name")), headers={"Cache-Control": "no-store"})

    async def courts_route(request):
        qid = request.path_params["qid"]
        if not re.fullmatch(r"Q\d{1,12}", qid):
            return JSONResponse({"error": "not a Wikidata id"}, status_code=400)
        return JSONResponse(await court_records(collector, qid, request.query_params.get("name") or ""), headers={"Cache-Control": "no-store"})

    return [Route("/api/dossier/courts/{qid}", courts_route), Route("/api/dossier/countries", countries), Route("/api/dossier/country", country_route), Route("/api/dossier/person/{qid}", person_route)]


# ---------------------------------------------------------------- live signals for a person
def _once(arts: list[dict]) -> list[dict]:
    """Copies of one agency story (same headline at many outlets) shown once, the first in the given order."""
    seen, out = set(), []
    for a in arts:
        k = news_window._headline(a["title"])
        if k not in seen:
            seen.add(k)
            out.append(a)
    return out


def person(collector, qid: str, name_hint: str | None) -> dict:
    prof = (store.cache_get("profile3:" + qid, 7 * 86400) or {}).get("body") or {}
    name = prof.get("name") or name_hint or ""
    key = news_window._norm(name)
    surname = key.split()[-1] if key else ""
    lh = store.cache_get("leaders", 30 * 86400)
    leaders = (lh or {}).get("body") or []
    mine = [l for l in leaders if l["qid"] == qid]
    isos = [geo.by_name(l["country"]) for l in mine] + [c.get("iso") for c in prof.get("citizenship", [])]
    isos = [i for i in dict.fromkeys(isos) if i]
    home = isos[0] if isos else None
    feeds, out = {}, {"qid": qid, "name": name, "countries": isos, "home": home}

    # in the news: articles whose GKG person list names them (both 6-hour windows)
    outlets, places, arts = set(), {}, {}
    if len(key.split()) >= 2:
        for win in (news_window.english, news_window.translated):
            for published, row in win.articles():
                if len(row) < 9 or not row[8] or key not in {news_window._norm(p) for p in row[8].split(";") if p}:
                    continue
                outlets.add(row[3])
                pl = places.setdefault(row[0], {"place": row[0], "outlets": set(), "lat": row[1], "lon": row[2]})
                pl["outlets"].add(row[3])
                old = arts.get(row[3])
                if not old or published > old["time"]:
                    arts[row[3]] = {"outlet": row[3], "title": row[4], "url": row[5], "lang": row[6], "image": row[7], "place": row[0], "time": published}
    top_places = sorted(({"place": p["place"], "outlets": len(p["outlets"])} for p in places.values()), key=lambda p: -p["outlets"])[:5]
    # articles that name them in the headline first: GDELT also lists people mentioned once deep in a story
    in_title = lambda a: surname and surname in news_window._norm(a["title"])
    out["news"] = {"outlets": len(outlets), "places": top_places,
                   "articles": _once(sorted((a for a in arts.values() if in_title(a)), key=lambda a: (a["lang"] != "eng", -(a["image"] is not None), -a["time"])))[:6],
                   "in_headline": sum(1 for a in arts.values() if in_title(a)),
                   "window_h": news_window.WINDOW // 3600, "newest": news_window.english.newest(), "single_name": len(key.split()) < 2}
    feeds["news"] = _feed(collector, "news")[1]

    # where the news placed them (only heads of state and government are on that list)
    t = next((x for x in news_window.leaders_today(leaders) if x["qid"] == qid), None) if mine else None
    out["reported_at"] = t and {"place": t["place"]["place"], "outlets": t["place"]["outlets"], "headlines": t["place"]["headlines"],
                                "abroad": t["abroad"], "also": [p["place"] for p in t["places"][1:4]]}
    out["is_leader"] = bool(mine)

    # aircraft listed with their name (or their office) in plane-alert-db
    vip, feeds["vip_aircraft"] = _feed(collector, "vip_aircraft")
    vip = (vip or {}).get("aircraft", {})
    surname = key.split()[-1] if key else ""
    offices = {r.get("name") for r in prof.get("current_roles", [])}
    matched = []
    for h, v in vip.items():
        why = None
        for tag in [*(v.get("tags") or []), v.get("operator") or ""]:
            n = news_window._norm(tag)
            if key and n == key:
                why = f"listed with the tag \"{tag}\"" if tag != v.get("operator") else f"listed with \"{tag}\" as operator"
            elif surname and len(surname) > 3 and n == surname and home and _flag_of(collector, h) == home:
                why = f"tagged \"{tag}\" and registered in the same country"
            elif tag in _OFFICE_TAGS and _OFFICE_TAGS[tag] in offices:
                why = f"tagged \"{tag}\", the office this person holds"
            if why:
                break
        if why:
            matched.append({"hex": h, "reg": v.get("reg"), "type": v.get("type"), "operator": v.get("operator"), "category": v.get("category"), "why": why})
    pos = _positions(collector) if matched else {}
    for m in matched:
        a = pos.get(m["hex"])
        m["seen"] = a and {"lat": a["lat"], "lon": a["lon"], "time": a["time"], "ground": a["ground"], "alt_ft": a["alt_ft"], "flight": a["flight"],
                           "over": geo.where(a["lon"], a["lat"]), "feed": a["feed"]}
        m["layer"] = "doomsday" if m["category"] == "Doomsday" else "vip"
    matched.sort(key=lambda m: (m["seen"] is None, m["seen"] and m["seen"]["ground"]))
    out["aircraft"] = matched
    for n in ("aircraft_world", "aircraft_military"):
        feeds[n] = _feed(collector, n)[1]

    # their country right now
    if home:
        p, feeds["unrest"] = _feed(collector, "unrest")
        fips = set(geo.C[home]["fips"])
        gs = [g for g in (p or {}).get("groups", []) if g.get("country") in fips]
        out["unrest"] = {"total": len(gs), "two_plus": sum(g["outlets"] >= 2 for g in gs), "violent": sum(g["cat"] != "protest" for g in gs)}
        p, feeds["airspace"] = _feed(collector, "airspace")
        out["airspace"] = [{"source": z["source"], "title": z["title"], "level": z["level"], "number": z.get("number")} for z in _airspace_for(home, p)]
        p, feeds["travel_advice"] = _feed(collector, "travel_advice")
        out["travel_us"] = ((p or {}).get("us", {}).get(home) or [None])[0]
        out["country_name"] = geo.C[home]["name"]
    out["feeds"] = feeds
    out["now"] = time.time()
    return out


# ---------------------------------------------------------------- court records for a person
async def _wd_entity(client, qid: str) -> dict:
    hit = store.cache_get("wdent:" + qid, 30 * 86400)
    if hit:
        return hit["body"]
    r = await client.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": qid, "props": "labels|aliases|claims",
                                                                        "languages": "en", "format": "json"}, headers=_wm_headers())
    r.raise_for_status()
    e = r.json()["entities"][qid]
    body = {"label": e.get("labels", {}).get("en", {}).get("value"), "aliases": [a["value"] for a in e.get("aliases", {}).get("en", [])],
            "convicted": courts.wd_claims(e, "P1399"), "charged": courts.wd_claims(e, "P1595")}
    ids = body["convicted"] + body["charged"]
    if ids:
        r = await client.get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": "|".join(ids[:50]), "props": "labels",
                                                                            "languages": "en", "format": "json"}, headers=_wm_headers())
        lab = {k: v.get("labels", {}).get("en", {}).get("value") for k, v in r.json().get("entities", {}).items()}
        body["convicted"] = [lab.get(i) for i in body["convicted"] if lab.get(i)]
        body["charged"] = [lab.get(i) for i in body["charged"] if lab.get(i)]
    store.cache_put("wdent:" + qid, body)
    return body


async def _uk(client, name: str, names: list[str]) -> dict:
    """England and Wales judgments: as a named party, and mentioning the name (quoted). Cached a day."""
    key = "ukcase2:" + courts.fold(name)
    hit = store.cache_get(key, 86400)
    if hit:
        return {**hit["body"], "fetched": hit["fetched"]}
    ua = {"User-Agent": _wm_headers()["User-Agent"]}
    r = await client.get(courts.UK, params={"party": name, "per_page": 50, "order": "-date"}, headers=ua)
    r.raise_for_status()
    party, _ = courts.parse_uk_atom(r.text)
    r = await client.get(courts.UK, params={"query": f'"{name}"', "per_page": 10, "order": "-date"}, headers=ua)
    r.raise_for_status()
    mention, last = courts.parse_uk_atom(r.text)
    total = len(mention)
    if last > 1:
        r2 = await client.get(courts.UK, params={"query": f'"{name}"', "per_page": 10, "order": "-date", "page": last}, headers=ua)
        total = (last - 1) * 10 + len(courts.parse_uk_atom(r2.text)[0]) if r2.status_code == 200 else last * 10
    party_urls = {p["url"] for p in party}
    # the party filter also matches the surname alone ("Crow v Johnson" for Boris Johnson): a title must carry the
    # first and last name to count as theirs; the rest is listed apart as "same surname, may be someone else"
    pats = courts.name_patterns(names)
    named = [p for p in party if any(x.search(courts.fold(p["title"])) for x in pats)]
    other = [p for p in party if p not in named]
    body = {"party": named[:25], "party_total": len(named), "surname_only": other[:8], "surname_total": len(other),
            "mention": [m for m in mention if m["url"] not in party_urls][:6], "mention_total": total}
    store.cache_put(key, body)
    return {**body, "fetched": time.time()}


async def court_records(collector, qid: str, name_hint: str) -> dict:
    out, problems = {"qid": qid}, []
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        try:
            ent = await _wd_entity(client, qid)
        except Exception as e:
            ent = {"label": name_hint, "aliases": [], "convicted": [], "charged": []}
            problems.append("Wikidata " + ("is limiting requests (429)" if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429 else f"failed ({type(e).__name__})") + ": other names and recorded convictions not read")
        name = ent.get("label") or name_hint
        names = [n for n in dict.fromkeys([name, name_hint, *ent.get("aliases", [])]) if n]
        out.update(name=name, names=names, wikidata={"convicted": ent.get("convicted", []), "charged": ent.get("charged", [])})
        payload, out["icc_feed"] = _feed(collector, "courts_icc")
        out["icc"] = courts.icc_matches(payload or {}, names) if payload else None
        if not payload:
            problems.append("the ICC list has not been read yet by this server")
        if len(name.split()) >= 2:
            try:
                out["uk"] = await _uk(client, name, names)
            except Exception as e:
                out["uk"] = None
                problems.append(f"UK Find Case Law ({type(e).__name__})")
        else:
            out["uk"] = None
            problems.append("a one-word name cannot be searched safely in UK judgments")
    out["problems"] = problems
    return out
