"""Join the live aircraft and ships to companies, exactly as the app would. Inputs fetched 28 Nov 2026 ~15:22-15:30 UTC."""
import json, re, time
g = lambda b, k: b.get(k, {}).get('value')
qid = lambda u: u.rsplit('/', 1)[1] if u else None
near = json.load(open('near.json')); NOW = near['now'] / 1000
AC = near['ac']; OW = json.load(open('owners.json')); HX = json.load(open('hexdb.json'))
for h, v in HX.items():                 # hexdb.io where adsbdb did not know the aircraft (as the app does)
    b = v.get('body')
    if b and b.get('RegisteredOwners'):
        OW[h] = {'status': 200, 'src': 'hexdb.io', 'aircraft': {'registered_owner': b['RegisteredOwners'], 'registered_owner_operator_flag_code': b.get('OperatorFlagCode'),
                 'registration': b.get('Registration'), 'manufacturer': b.get('Manufacturer'), 'type': b.get('Type'), 'registered_owner_country_iso_name': None}}
WDA = json.load(open('wd-airlines.json')); GL = json.load(open('gleif-lh.json'))
# --- companies (Wikidata airline items by ICAO designator P230), skipping dissolved ones
items = {}
for b in WDA:
    if g(b, 'dis'): continue
    q = qid(g(b, 'a')); it = items.setdefault(q, dict(qid=q, name=g(b, 'aLabel'), icao=set(), lei=g(b, 'lei'), parents=set(), owners=set(), hq=None, hqname=None))
    it['icao'].add(g(b, 'icao'))
    if g(b, 'par'): it['parents'].add((qid(g(b, 'par')), g(b, 'parLabel')))
    if g(b, 'own'): it['owners'].add((qid(g(b, 'own')), g(b, 'ownLabel')))
    if g(b, 'hqc') and not it['hq']:
        lo, la = map(float, re.findall(r'[-\d.]+', g(b, 'hqc'))); it['hq'] = (lo, la); it['hqname'] = g(b, 'hqLabel')
TOP = {'Q9325', 'Q62589018'}            # Lufthansa (airline item, carries Deutsche Lufthansa AG's LEI) and Lufthansa Group
def in_group(q, seen=()):
    if q in TOP: return True
    it = items.get(q)
    if not it or q in seen: return False
    return any(in_group(p, seen + (q,)) for p, _ in it['parents'] | it['owners'])
gleif_leis = {GL['parent']['id']} | {k['lei'] for k in GL['children']}
for q, it in items.items():
    it['group'] = in_group(q) or (it['lei'] in gleif_leis)
    it['via'] = sorted({lab for _, lab in it['parents'] | it['owners']})
by_icao = {}
for it in items.values():
    for c in it['icao']: by_icao.setdefault(c, []).append(it)
for c, lst in by_icao.items():          # several items share a code (a brand beside the company): keep the one with an LEI
    if len(lst) > 1 and sum(1 for it in lst if it['lei']) == 1: by_icao[c] = [it for it in lst if it['lei']]
norm = lambda s: re.sub(r'\b(ltd|limited|ag|gmbh|s\.?p\.?a\.?|aktiengesellschaft|plc|sa|nv|oy|ab)\b', '', re.sub(r'\(.*?\)', '', (s or '').lower())).replace('.', ' ').split()
by_name = {}
for it in items.values(): by_name.setdefault(' '.join(norm(it['name'])), []).append(it)
def company_for_owner(a):
    if not a: return None, None
    c = a.get('registered_owner_operator_flag_code')
    if c and len(by_icao.get(c, [])) == 1: return by_icao[c][0], 'owner code ' + c
    n = ' '.join(norm(a.get('registered_owner')))
    if n and len(by_name.get(n, [])) == 1: return by_name[n][0], 'owner name'
    return None, None
rows = []
for a in AC:
    cs = (a.get('flight') or '').strip(); m = re.fullmatch(r'([A-Z]{3})\d[0-9A-Z]*', cs)
    ops = by_icao.get(m.group(1), []) if m else []
    op = ops[0] if len(ops) == 1 else None
    rec = OW.get(a['hex'])
    if not op and not rec: continue
    ow = (rec or {}).get('aircraft')
    oc, how = company_for_owner(ow)
    rows.append(dict(hex=a['hex'], cs=cs, reg=a.get('r'), type=a.get('t'), lat=a.get('lat'), lon=a.get('lon'), alt=a.get('alt_baro'), gs=a.get('gs'), trk=a.get('track'),
                     seen=a.get('seen_pos'), op=op and op['qid'], op_group=bool(op and op['group']), owner=ow and ow.get('registered_owner'), owner_country=ow and ow.get('registered_owner_country_iso_name'),
                     owner_q=oc and oc['qid'], owner_group=bool(oc and oc['group']), how=how, src=(rec or {}).get('src', 'adsbdb') if ow else None, model=ow and f"{ow.get('manufacturer')} {ow.get('type')}"))
cos = {q: dict(qid=q, name=it['name'], icao=sorted(it['icao']), lei=it['lei'], group=it['group'], via=it['via'], hq=it['hq'], hqname=it['hqname']) for q, it in items.items()}
json.dump(dict(now=NOW, total=len(AC), rows=rows, companies=cos, gleif_children=len({k['lei'] for k in GL['children']})), open('air.json', 'w'), indent=1)
from collections import Counter
print("now", time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(NOW)), "aircraft", len(AC), "considered", len(rows))
print("group companies", sorted((c['name'], c['group']) for c in cos.values()))
cat = Counter()
for r in rows:
    k = ('flies as group' if r['op_group'] else 'flies as other') + ' / ' + ('owner group' if r['owner_group'] else 'owner other' if r['owner'] else 'owner unknown')
    cat[k] += 1
print(cat)
print(Counter((cos[r['owner_q']]['name'] if r['owner_q'] else r['owner'] or '?', r['how']) for r in rows if r['op_group'] or r['owner_group']).most_common())
print([ (r['cs'], r['owner']) for r in rows if r['op_group'] and r['owner'] and not r['owner_group']])
