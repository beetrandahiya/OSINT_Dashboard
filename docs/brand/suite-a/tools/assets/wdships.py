import json, time, httpx
UA = {"User-Agent": "WorldWatch/1.0 (personal research tool)"}
v = json.load(open('dt-vessels.json'))
imos = sorted({str(x['imo']) for x in v if x.get('imo') and len(str(x['imo'])) == 7})
print(len(imos), "IMOs")
def sparql(q):
    for i in range(6):
        r = httpx.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"}, headers=UA, timeout=90)
        if r.status_code == 200: return r.json()["results"]["bindings"]
        print(r.status_code); time.sleep(int(r.headers.get("retry-after", "20")) + 2)
    return []
rows = []
for i in range(0, len(imos), 300):
    vals = " ".join(f'"{x}"' for x in imos[i:i+300])
    rows += sparql("""SELECT ?s ?sLabel ?imo ?own ?ownLabel ?op ?opLabel ?opLei ?ownLei WHERE { VALUES ?imo { %s } ?s wdt:P458 ?imo .
      OPTIONAL { ?s wdt:P127 ?own . OPTIONAL { ?own wdt:P1278 ?ownLei } } OPTIONAL { ?s wdt:P137 ?op . OPTIONAL { ?op wdt:P1278 ?opLei } }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }""" % vals)
    time.sleep(2)
json.dump(rows, open('wd-ships.json', 'w'), indent=1)
g = lambda b, k: b.get(k, {}).get('value')
print(len(rows), "rows")
from collections import Counter
print(Counter(g(b,'ownLabel') or g(b,'opLabel') or '-' for b in rows).most_common(30))
grp = Counter()
for b in rows: grp[(g(b,'ownLabel'), g(b,'opLabel'))] += 1
for k, n in grp.most_common(40): print(n, k)
# Lufthansa group check too
lh = sparql("""SELECT ?p ?pLabel ?v ?vLabel WHERE { wd:Q62589018 ?p ?v . FILTER(?p IN (wdt:P31, wdt:P1278, wdt:P159, wdt:P355, wdt:P749, wdt:P127, wdt:P1830)) SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }""")
json.dump(lh, open('wd-lhgroup.json','w'), indent=1)
for b in lh: print("LHG", g(b,'p').rsplit('/',1)[1], g(b,'vLabel') or g(b,'v'))
