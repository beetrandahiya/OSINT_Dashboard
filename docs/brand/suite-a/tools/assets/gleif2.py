import json, time, httpx
c = httpx.Client(timeout=30, headers={"User-Agent": "WorldWatch/1.0 (personal research tool)", "Accept": "application/vnd.api+json"})
def get(u, **p):
    for i in range(3):
        r = c.get(u, params=p)
        if r.status_code in (200, 404): return r.json() if r.status_code == 200 else None
        time.sleep(2)
    return None
out = {}
for q in ["Eurowings GmbH", "Eurowings Europe", "Eurowings Discover", "Brussels Airlines", "Edelweiss Air", "Helvetic Airways", "Air Baltic Corporation", "Italia Trasporto Aereo", "Alitalia", "SN Airholding", "Lufthansa Cargo"]:
    j = get("https://api.gleif.org/api/v1/lei-records", **{"filter[fulltext]": q, "page[size]": 5})
    rows = []
    for x in (j or {}).get("data", [])[:5]:
        e = x["attributes"]["entity"]
        lei = x["id"]
        dp = get(f"https://api.gleif.org/api/v1/lei-records/{lei}/direct-parent")
        up = get(f"https://api.gleif.org/api/v1/lei-records/{lei}/ultimate-parent")
        ex = None
        if not dp:
            r2 = get(f"https://api.gleif.org/api/v1/lei-records/{lei}/direct-parent-reporting-exception")
            ex = ((r2 or {}).get("data") or {}).get("attributes", {}).get("reason")
        rows.append({"lei": lei, "name": e["legalName"]["name"], "status": e["status"], "city": e["headquartersAddress"]["city"], "country": e["headquartersAddress"]["country"],
                     "parent": dp and (dp["data"]["id"], dp["data"]["attributes"]["entity"]["legalName"]["name"]),
                     "ultimate": up and (up["data"]["id"], up["data"]["attributes"]["entity"]["legalName"]["name"]), "exception": ex})
        time.sleep(0.3)
    out[q] = rows
    print("==", q)
    for r in rows: print("  ", r["lei"], r["name"], r["city"], r["country"], r["status"], "| parent:", r["parent"] and r["parent"][1], "| top:", r["ultimate"] and r["ultimate"][1], "| ex:", r["exception"])
json.dump(out, open("gleif-more.json", "w"), indent=1)
