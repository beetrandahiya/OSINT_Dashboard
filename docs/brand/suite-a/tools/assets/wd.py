import json, time, httpx
UA = {"User-Agent": "WorldWatch/1.0 (personal research tool)"}
codes = ["DLH","SWR","AUA","EWG","BEL","EDW","OCN","LHX","DLA","GEC","ITY","CLH","OAW","BTI","AZA","EWL"]
q = """SELECT ?a ?aLabel ?icao ?lei ?par ?parLabel ?own ?ownLabel ?share ?hq ?hqLabel ?hqc ?dis WHERE {
 VALUES ?icao { %s } ?a wdt:P230 ?icao .
 OPTIONAL { ?a wdt:P1278 ?lei }
 OPTIONAL { ?a wdt:P749 ?par }
 OPTIONAL { ?a p:P127 ?st . ?st ps:P127 ?own . OPTIONAL { ?st pq:P1107 ?share } FILTER NOT EXISTS { ?st pq:P582 [] } }
 OPTIONAL { ?a wdt:P159 ?hq . OPTIONAL { ?hq wdt:P625 ?hqc } }
 OPTIONAL { ?a wdt:P576 ?dis }
 SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }""" % " ".join(f'"{c}"' for c in codes)
for i in range(6):
    r = httpx.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=UA, timeout=60)
    print(r.status_code)
    if r.status_code == 200: break
    time.sleep(int(r.headers.get("retry-after", "20")) + 2)
rows = r.json()["results"]["bindings"] if r.status_code == 200 else []
v = lambda b, k: b.get(k, {}).get("value")
json.dump(rows, open("wd-airlines.json", "w"), indent=1)
for b in rows:
    print(v(b,"icao"), v(b,"aLabel"), "| lei", v(b,"lei"), "| parent", v(b,"parLabel"), "| owner", v(b,"ownLabel"), v(b,"share"), "| hq", v(b,"hqLabel"), v(b,"hqc"), "| dissolved", v(b,"dis"))
