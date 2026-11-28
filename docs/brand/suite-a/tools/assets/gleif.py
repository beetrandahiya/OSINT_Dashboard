import json, time, httpx
c = httpx.Client(timeout=30, headers={"User-Agent": "WorldWatch/1.0 (personal research tool)", "Accept": "application/vnd.api+json"})
def get(u, **p):
    for i in range(3):
        r = c.get(u, params=p)
        if r.status_code == 200: return r.json()
        time.sleep(2)
    print("fail", u, r.status_code); return None
r = get("https://api.gleif.org/api/v1/lei-records", **{"filter[entity.legalName]": "Deutsche Lufthansa Aktiengesellschaft"})
recs = r["data"]
if not recs:
    r = get("https://api.gleif.org/api/v1/fuzzycompletions", field="entity.legalName", q="Deutsche Lufthansa")
    print(json.dumps(r)[:1500])
for x in recs: print(x["id"], x["attributes"]["entity"]["legalName"]["name"], x["attributes"]["entity"]["headquartersAddress"]["city"])
lei = recs[0]["id"]
kids = []
for kind in ("direct-children", "ultimate-children"):
    page = 1
    while True:
        j = get(f"https://api.gleif.org/api/v1/lei-records/{lei}/{kind}", **{"page[size]": 200, "page[number]": page})
        if not j: break
        for x in j["data"]:
            e = x["attributes"]["entity"]
            kids.append({"rel": kind, "lei": x["id"], "name": e["legalName"]["name"], "status": e["status"],
                         "city": e["headquartersAddress"]["city"], "country": e["headquartersAddress"]["country"],
                         "lcity": e["legalAddress"]["city"], "lcountry": e["legalAddress"]["country"]})
        if j["meta"]["pagination"]["lastPage"] <= page: break
        page += 1
print(len(kids))
json.dump({"parent": recs[0], "children": kids}, open("gleif-lh.json", "w"), indent=1)
for k in kids: print(k["rel"][:6], k["lei"], k["name"], "|", k["city"], k["country"], k["status"])
