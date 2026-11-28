import json, time, httpx
g = json.load(open('group.json'))
out = {}
with httpx.Client(timeout=15, headers={"User-Agent": "WorldWatch/1.0 (personal research tool)"}) as c:
    for a in g:
        h = a['hex']
        try:
            r = c.get(f"https://api.adsbdb.com/v0/aircraft/{h}")
            j = r.json() if r.status_code == 200 else None
            out[h] = {"status": r.status_code, "aircraft": (j or {}).get("response", {}).get("aircraft") if j else None}
        except Exception as e:
            out[h] = {"status": type(e).__name__}
        time.sleep(0.6)
json.dump(out, open('owners.json', 'w'), indent=1)
from collections import Counter
print(Counter(str(v.get('status')) for v in out.values()))
print(Counter(((v.get('aircraft') or {}).get('registered_owner') or '?') for v in out.values()).most_common(40))
