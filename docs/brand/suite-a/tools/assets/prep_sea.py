import json, re, time
g = lambda b, k: b.get(k, {}).get('value')
qid = lambda u: u.rsplit('/', 1)[1] if u and '/entity/Q' in u else None
V = json.load(open('dt-vessels.json')); L = json.load(open('dt-loc.json')); W = json.load(open('wd-ships.json')); CO = json.load(open('wd-shipcos.json'))
GS = json.load(open('gleif-ships.json'))
NOW = L['dataUpdatedTime']
loc = {f['mmsi']: f for f in L['features']}
byimo = {}
for b in W:
    i = g(b, 'imo'); s = byimo.setdefault(i, dict(qid=qid(g(b, 's')), name=g(b, 'sLabel'), own=set(), op=set()))
    if qid(g(b, 'own')): s['own'].add(qid(g(b, 'own')))
    if qid(g(b, 'op')): s['op'].add(qid(g(b, 'op')))
cos = {}
for b in CO:
    q = qid(g(b, 'c')); c = cos.setdefault(q, dict(qid=q, name=g(b, 'cLabel'), lei=g(b, 'lei'), hq=None, hqname=g(b, 'hqLabel'), parent=g(b, 'parLabel')))
    if g(b, 'hqc') and not c['hq']: c['hq'] = list(map(float, re.findall(r'[-\d.]+', g(b, 'hqc'))))
for c in cos.values():
    if re.fullmatch(r'Q\d+', c['name'] or ''): c['name'] = None
ships = []
tsnow = time.time() * 1000
for v in V:
    f = loc.get(v['mmsi'])
    if not f: continue
    age = (tsnow - f['properties']['timestampExternal']) / 60000
    w = byimo.get(str(v.get('imo')))
    links = []
    if w:
        for q in sorted(w['own']): links.append(('owner', q))
        for q in sorted(w['op'] - w['own']): links.append(('operator', q))
        links = [(k, q) for k, q in links if cos.get(q, {}).get('name')]
    lo, la = f['geometry']['coordinates']
    ships.append(dict(mmsi=v['mmsi'], imo=v.get('imo'), name=v['name'], type=v['shipType'], lon=lo, lat=la, sog=f['properties']['sog'], cog=f['properties']['cog'], hdg=f['properties']['heading'],
                      age=round(age, 1), wd=w and w['qid'], links=links))
fresh = [s for s in ships if s['age'] <= 60]
print("positions", len(L['features']), "vessels", len(V), "with position", len(ships), "fresh <=60 min", len(fresh))
imo = [s for s in ships if s['imo'] and len(str(s['imo'])) == 7]
print("with IMO", len(imo), "in Wikidata", sum(1 for s in imo if s['wd']), "linked to a company", sum(1 for s in imo if s['links']))
print("fresh linked", sum(1 for s in fresh if s['links']))
from collections import Counter
print(Counter(cos[q]['name'] for s in ships for k, q in s['links']).most_common(20))
json.dump(dict(now=tsnow / 1000, data_time=NOW, ships=ships, companies=cos, gleif=GS), open('sea.json', 'w'), indent=1)
