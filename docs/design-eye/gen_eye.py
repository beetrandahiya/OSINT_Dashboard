import json, math, html
from views import V, SUN, CAP, GEO
from cam import unit, r
import numpy as np
D = '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/dd/'
OUT = '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/dc/project/'
IT = json.load(open(D + 'out/markers.json'))['items']
FR = json.load(open(D + 'front_ukraine.json'))['payload']
IMG = dict(whole='897b808cc9cfb4d4b27565602d27ebcf', horizon='283a475d8bcb273526c7ace06fdc1047', theatre='63f8c8ae66fe9d0ed5ce885a6fdbb26a', dusk='8c0b1938e41e6933c927ee35f5b09463',
           sides='2e12c1500d08c39927a200cfe12e43e1', wall='98d1bf3e81097551f7c327da03e3c66c', front='62d113b30b3eaf2ccffd62776dbe80ed')
NAMES = [('whole', 'Whole Earth'), ('horizon', 'Horizon'), ('theatre', 'Theatre'), ('dusk', 'Day and night'), ('sides', 'Two sides'), ('wall', 'Wall of four'), ('front', 'Look down')]
E = html.escape
SG = "font-family: 'Space Grotesk', sans-serif"
G = 'background: rgba(10,14,18,0.68); border: 1px solid rgba(255,255,255,0.14)'
MUT = '#c9d1d6'
def age(t):
    s = CAP - t
    if s < 5400: return f"{max(1, round(s/60))} min"
    if s < 172800: return f"{s/3600:.0f} h" if s >= 36000 else f"{s/3600:.1f} h"
    return f"{s/86400:.1f} d"
def km(x): return f"{round(x):,}"
# ---------- markers ----------
def inr(x, y, rect, m=4): return rect[0] + m <= x <= rect[0] + rect[2] - m and rect[1] + m <= y <= rect[1] + rect[3] - m
TOP = (0, 0, 1920, 68)
def seen(view, kind, hide=()):
    hide = list(hide) + [TOP]
    """items of a kind that are on the visible side and inside a camera's rectangle, not under a panel"""
    out = []
    for cam, x0, y0, w, h in V[view]['cams']:
        for i in IT[kind]:
            x, y, vis = cam.proj(i['lon'], i['lat'])
            if vis and inr(x, y, (x0, y0, w, h)) and not any(inr(x, y, hr, -2) for hr in hide): out.append((i, x, y, cam))
    return out
def markers(view, hide=(), names=True, kinds=('mil', 'front', 'quakes', 'launches', 'ships', 'outages', 'unrest', 'leaders'), occupied=False, big=False):
    s = []; S = 1.25
    if occupied:
        cam = V[view]['cams'][0][0]
        for a in FR['areas']:
            for ring in a['rings']:
                step = max(1, len(ring)//(160 if big else 40))
                pts = [cam.proj(lo, la) for lo, la in ring[::step]]
                if len(pts) > 2 and all(p[2] for p in pts) and any(0 < p[0] < 1920 and 0 < p[1] < 1080 for p in pts):
                    d = 'M' + ' L'.join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts) + ' Z'
                    col = '#ff5c3c' if a.get('kind') == 'occupied' else '#ffb08a'
                    s.append(f'<path d="{d}" fill="{col}" fill-opacity="{0.26 if a.get("kind") == "occupied" else 0.16}" stroke="{col}" stroke-opacity="0.85" stroke-width="{1.2 if big else 0.7}"></path>')
    if 'mil' in kinds:
        for i, x, y, cam in seen(view, 'mil', hide):
            t = (i['track'] or 0)*r; x2, y2, _ = cam.proj(i['lon'] + 0.2*math.sin(t)/max(0.2, math.cos(i['lat']*r)), i['lat'] + 0.2*math.cos(t))
            ang = math.degrees(math.atan2(x2 - x, -(y2 - y)))
            s.append(f'<path d="M0 -6 L4 5 L0 2.6 L-4 5 Z" fill="#ffffff" fill-opacity="0.92" transform="translate({x:.1f} {y:.1f}) rotate({ang:.0f}) scale({S})"></path>')
    if 'front' in kinds:
        for c in FR['changes'][-8:]:
            for cam, x0, y0, w, h in V[view]['cams']:
                x, y, vis = cam.proj(c['lon'], c['lat'])
                if vis and inr(x, y, (x0, y0, w, h)) and not any(inr(x, y, hr, -2) for hr in list(hide) + [TOP]):
                    s.append(f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" fill="none" stroke="#ffffff" stroke-width="1.5"></rect>')
    if 'quakes' in kinds:
        for i, x, y, cam in seen(view, 'quakes', hide):
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3 + (i["mag"] - 4.5)*3.2:.1f}" fill="none" stroke="#ffffff" stroke-width="1.5"></circle>')
    if 'launches' in kinds:
        for i, x, y, cam in seen(view, 'launches', hide):
            s.append(f'<path d="M0 -7 L6 5 L-6 5 Z" fill="#9fd8ff" stroke="#06202e" stroke-width="1" transform="translate({x:.1f} {y:.1f})"></path>')
    if 'ships' in kinds:
        done = set()
        for i, x, y, cam in seen(view, 'ships', hide):
            k = (round(x), round(y))
            if k in done: continue
            done.add(k)
            dash = ' stroke-dasharray="3 3"' if i['placed'] == 'region' else ''
            s.append(f'<path d="M0 -7 L7 0 L0 7 L-7 0 Z" fill="#ffcf8a" stroke="#2a1c05" stroke-width="1" transform="translate({x:.1f} {y:.1f})"></path><circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="none" stroke="#ffcf8a" stroke-width="1"{dash}></circle>')
    if 'outages' in kinds:
        for i, x, y, cam in seen(view, 'outages', hide):
            s.append(f'<rect x="{x-11:.1f}" y="{y-8:.1f}" width="22" height="16" rx="3" fill="rgba(10,14,18,0.7)" stroke="#c9d1d6" stroke-width="1"></rect><text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" fill="#f2f4f6" font-family="Inter, sans-serif" font-size="10" font-weight="600">{i["code"]}</text>')
    if 'unrest' in kinds:
        for i, x, y, cam in seen(view, 'unrest', hide):
            rad = 4.5 + math.sqrt(i['outlets'])*1.6
            if i['cat'] == 'protest': s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="none" stroke="#ffe08a" stroke-width="2.2"></circle>')
            else: s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="#ff7a3c" fill-opacity="0.9" stroke="#1a0d05" stroke-width="1"></circle>')
    if 'leaders' in kinds and names:
        for i, x, y, cam in seen(view, 'leaders', hide):
            end = x > cam.cx + 200
            s.append(f'<text x="{x + (-13 if end else 13):.1f}" y="{y+4:.1f}" text-anchor="{"end" if end else "start"}" fill="#ffffff" font-family="Inter, sans-serif" font-size="12" font-weight="500" stroke="#000000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">{E(i["name"])}</text>')
    return '<svg width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-label="Real items from the capture at their positions in this view" style="position: absolute; left: 0; top: 0">' + ''.join(s) + '</svg>'
# ---------- parts ----------
def panel(x, y, w, h, inner, label, pad=14, gap=8, extra=''):
    return f'<section aria-label="{label}" style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; box-sizing: border-box; padding: {pad}px; border-radius: 22px; {G}; display: flex; flex-direction: column; gap: {gap}px; overflow: hidden; {extra}">{inner}</section>'
def hd(t, sub='', size=15):
    return f'<div style="display: flex; justify-content: space-between; align-items: baseline; gap: 10px; min-height: 22px"><span style="{SG}; font-weight: 600; font-size: {size}px; white-space: nowrap">{t}</span><span style="font-size: 12px; color: {MUT}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{sub}</span></div>'
def row(cells, widths, head=False, h=26):
    o = f'<div style="display: flex; align-items: center; height: {h}px; gap: 10px; {"color: " + MUT + "; font-size: 11px" if head else "border-top: 1px solid rgba(255,255,255,0.08)"}">'
    for (t, st), w in zip(cells, widths):
        o += f'<span style="{"flex: 1; min-width: 0" if w is None else "width: " + str(w) + "px; flex: none"}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; {st}">{t}</span>'
    return o + '</div>'
B = f"{SG}; font-weight: 600"
R = "text-align: right"
M = f"color: {MUT}"
def rule(): return '<div style="height: 1px; flex: none; background: rgba(255,255,255,0.1)"></div>'
def note(t): return f'<div style="font-size: 12px; color: {MUT}; line-height: 1.4">{t}</div>'
C = {'ok': '#7be0a0', 'late': '#ffcf8a', 'fail': '#ff8f7a', 'off': '#9aa3a9'}
def tile(label, val, state, nt, h=50):
    c = C[state]
    dot = f'<span style="width: 8px; height: 8px; border-radius: 999px; flex: none; margin-top: 5px; box-sizing: border-box; {"background: " + c if state != "off" else "border: 1px dashed " + c}"></span>'
    bd = 'rgba(255,255,255,0.12)' if state in ('ok', 'off') else c + '88'
    return (f'<div style="height: {h}px; box-sizing: border-box; padding: 6px 10px; border-radius: 12px; border: 1px {"dashed" if state == "off" else "solid"} {bd}; background: rgba(255,255,255,0.06); display: flex; gap: 8px">{dot}'
            f'<div style="flex: 1; min-width: 0"><div style="font-size: 12px; color: {MUT}; white-space: nowrap">{label}</div><div style="{SG}; font-weight: 600; font-size: 16px; line-height: 1.2; white-space: nowrap">{val}</div></div>'
            f'<div style="font-size: 12px; color: {c if state != "ok" else MUT}; text-align: right; white-space: nowrap; align-self: center">{nt}</div></div>')
TILES = [("Military aircraft", "120", "ok", "adsb.fi · 12 s"), ("Protests, clashes", "14", "ok", "GDELT · 1 min"), ("Leaders in the news", "17", "ok", "GDELT · 57 min"), ("Earthquakes, 24 h", "168", "ok", "USGS · 1 min"),
         ("Internet outages", "5", "ok", "IODA · 22 s"), ("Front, occupied", "116,892 km²", "ok", "1 d 14 h"), ("Navy warnings", "1", "ok", "UKHO · 40 s"), ("Launches listed", "20", "ok", "LL2 · 43 s"),
         ("US carriers", "8", "late", "late · 22 d"), ("Court records", "none", "fail", "ICC failing"), ("World ships", "none", "off", "no key"), ("Internet hijacks", "none", "off", "no key"),
         ("Windy cameras", "none", "off", "no key"), ("Hotspots", "0", "ok", "none now")]
def tiles(): return '<div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 7px">' + ''.join(tile(*t) for t in TILES) + '</div>' + note('Dot: green current, amber late, red failing, dashed needs a key that is not set up. 40 of 45 feeds current.')
LAUNCH = [("18 Nov 22:50", "Long March 2D · Taiyuan", "go"), ("19 Nov 03:00", "Falcon 9, USSF-317 · Vandenberg", "go"), ("20 Nov 11:00", "Long March 8A, SatNet · Wenchang", "to confirm"), ("21 Nov 12:30", "Falcon 9, NROL-136 · Vandenberg", "go")]
def launches(): return hd("Coming up", "Launch Library 2, UTC") + '<div>' + ''.join(row([(d, "color: #9fd8ff"), (n, ""), (g, M + "; " + R)], [96, None, 74]) for d, n, g in LAUNCH) + '</div>'
def quakes(n=4):
    q = sorted(IT['quakes'], key=lambda q: -q['mag'])[:n]
    return hd("Earthquakes M4.5+", "USGS · age") + '<div>' + ''.join(row([(f"M{i['mag']:.1f}", B), (E(i['place'].split(' of ', 1)[-1]), ""), (age(i['time']), M + "; " + R)], [44, None, 50]) for i in q) + '</div>'
def kc(k): return "#ffe08a" if k == "protest" else "#ffb08a"
def unrest_rows(items, widths=(104, None, 30, 76), h=26):
    return ''.join(row([(E(i['place']), B), (f'<span style="color: {kc(i["cat"])}">{i["cat"]}</span> · {E(i["action"])}', "color: #e6eaed"), (str(i['outlets']), B + "; " + R), (age(i['last']), M + "; " + R)], widths, False, h) for i in items)
def unrest_head(widths=(104, None, 30, 76)): return row([("Place", ""), ("Coded as (GDELT, machine-coded, not verified)", ""), ("Out", R), ("Age", R)], widths, True, 20)
def topbar(sub):
    nav = ''.join(f'<a href="#{n.lower()}" style="padding: 11px 13px; border-radius: 999px; text-decoration: none; {"background: #f2f4f6; color: #0a0e12" if i == 0 else ""}">{n}</a>' for i, n in enumerate(['Overview', 'Conflict', 'Air', 'Sea', 'Space', 'Networks', 'Earth', 'Munich']))
    return (f'<div style="position: absolute; left: 28px; top: 12px"><div style="display: flex; align-items: baseline; gap: 12px"><span style="{SG}; font-weight: 700; font-size: 22px; letter-spacing: -0.01em">World Watch</span><span style="{SG}; font-weight: 500; font-size: 15px; color: #ffcf8a">{sub}</span></div><div style="color: {MUT}; font-size: 12px">Frozen capture 17 Nov 2026, 10:01 UTC</div></div>'
            f'<nav aria-label="Views" style="position: absolute; left: 640px; top: 14px; height: 48px; box-sizing: border-box; padding: 0 6px; border-radius: 999px; {G}; display: flex; align-items: center; gap: 2px; {SG}; font-weight: 500; font-size: 14px">{nav}</nav>'
            f'<div style="position: absolute; right: 24px; top: 14px; display: flex; gap: 8px; align-items: center"><div style="padding: 0 14px; height: 48px; display: flex; align-items: center; border-radius: 999px; {G}; font-size: 13px">40 of 45 feeds current · 1 late · 1 failing · 3 not set up</div>'
            f'<button type="button" aria-label="Layers" style="height: 48px; padding: 0 16px; border-radius: 999px; {G}; color: #f2f4f6; font: 500 14px \'Space Grotesk\', sans-serif">Layers</button>'
            f'<button type="button" aria-label="Settings" style="width: 48px; height: 48px; border-radius: 999px; {G}; color: #f2f4f6; display: grid; place-items: center"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3.2"></circle><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"></path></svg></button></div>')
def picker(cur, x, y, vertical=False):
    tw, th = (128, 62) if vertical else (128, 72)
    its = ''
    for k, n in NAMES:
        on = k == cur
        its += (f'<a href="#{k}" aria-current="{"true" if on else "false"}" style="display: flex; flex-direction: column; gap: 4px; text-decoration: none; color: {"#ffffff" if on else MUT}; font-size: 12px; font-weight: {600 if on else 400}">'
                f'<img src="/_blob/{IMG[k]}" alt="" style="width: {tw}px; height: {th}px; object-fit: cover; border-radius: 10px; border: {"2px solid #ffcf8a" if on else "1px solid rgba(255,255,255,0.18)"}; box-sizing: border-box; display: block">{n}</a>')
    if vertical: return f'<nav aria-label="Views of the globe" style="position: absolute; left: {x}px; top: {y}px; width: 152px; box-sizing: border-box; padding: 12px; border-radius: 22px; {G}; display: flex; flex-direction: column; gap: 9px">{its}</nav>'
    return f'<nav aria-label="Views of the globe" style="position: absolute; left: {x}px; top: {y}px; height: 118px; box-sizing: border-box; padding: 12px 14px; border-radius: 22px; {G}; display: flex; gap: 10px">{its}</nav>'
def campill(x, y, text, right=False):
    pos = f'right: {x}px' if right else f'left: {x}px'
    return f'<div style="position: absolute; {pos}; top: {y}px; padding: 8px 14px; border-radius: 999px; {G}; font-size: 13px; color: {MUT}; white-space: nowrap">{text}</div>'
def legend(x, y, kinds, w=None):
    L = {'mil': ('<svg width="10" height="12" viewBox="-5 -6 10 12" aria-hidden="true"><path d="M0 -6 L4 5 L0 2.6 L-4 5 Z" fill="#ffffff"></path></svg>', 'Military aircraft'),
         'clash': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="#ff7a3c"></circle></svg>', 'Clash, attack'),
         'protest': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.2" fill="none" stroke="#ffe08a" stroke-width="2"></circle></svg>', 'Protest'),
         'front': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="2" width="8" height="8" fill="none" stroke="#ffffff" stroke-width="1.5"></rect></svg>', 'Front-line change'),
         'occ': ('<svg width="14" height="12" viewBox="0 0 14 12" aria-hidden="true"><rect x="1" y="1" width="12" height="10" fill="#ff5c3c" fill-opacity="0.35" stroke="#ff5c3c"></rect></svg>', 'Occupied (DeepState)'),
         'ship': ('<svg width="14" height="14" viewBox="-7 -7 14 14" aria-hidden="true"><path d="M0 -6 L6 0 L0 6 L-6 0 Z" fill="#ffcf8a"></path></svg>', 'US carrier or amphib (22 d old)'),
         'quake': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.5" fill="none" stroke="#ffffff" stroke-width="1.5"></circle></svg>', 'Quake M4.5+'),
         'launch': ('<svg width="12" height="12" viewBox="-6 -7 12 13" aria-hidden="true"><path d="M0 -6 L5 5 L-5 5 Z" fill="#9fd8ff"></path></svg>', 'Launch pad, next 4 days'),
         'outage': ('<svg width="18" height="12" viewBox="0 0 18 12" aria-hidden="true"><rect x="1" y="1" width="16" height="10" rx="2" fill="none" stroke="#c9d1d6"></rect></svg>', 'Internet outage'),
         'name': ('', 'Name: leader placed by the news')}
    return f'<div aria-label="What the marks mean" style="position: absolute; left: {x}px; top: {y}px; {"width: " + str(w) + "px; " if w else ""}display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; color: {MUT}">' + ''.join(f'<span style="display: flex; gap: 6px; align-items: center; white-space: nowrap">{L[k][0]}{L[k][1]}</span>' for k in kinds) + '</div>'
def page(name, title, img, body, alt):
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap">
<style>
body{{margin:0}}
a{{color:#ffffff}}a:hover{{color:#ffcf8a}}
</style>
</helmet>
<div style="position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #030303; color: #f2f4f6; font-family: Inter, system-ui, sans-serif; font-size: 13px; line-height: 1.4">
<img src="/_blob/{IMG[img]}" alt="{alt}" style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px">
{body}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1920,"height":1080}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
'''
    assert doc.count('<div') == doc.count('</div>') and doc.count('<span') == doc.count('</span>') and doc.count('<section') == doc.count('</section>'), name
    assert '{{' not in body, name
    open(OUT + name, 'w').write(doc); print(name, len(doc))
UN = IT['unrest']; LD = IT['leaders']
OTHER = [("Front, Ukraine", "+27 km² since 8 Nov · newest advance near Vilne", "DeepState · 1 d 14 h", ""), ("Arabian Sea", "2 US carriers, 1 amphib, placed by region", "USNI · 22 d, late", "color: #ffcf8a"),
         ("Hebrides", "live weapons firing, 17 to 20 Nov, within 26 NM", "UKHO", ""), ("Outages", "Gibraltar, Eq. Guinea, Seychelles, Serbia, Cook Is.", "IODA · 22 s", "")]
def other_rows(): return ''.join(row([(p, B), (t, "color: #e6eaed"), (src, R + "; font-size: 12px; " + (st or M))], [104, None, 118]) for p, t, src, st in OTHER)
def leader_rows(items): return ''.join(row([(E(i['name']), B), (E(i['place']), "color: #e6eaed"), (str(i['outlets']), B + "; " + R)], [None, 130, 30]) for i in items)

# ===== 1 Whole Earth =====
left = panel(24, 84, 432, 598, hd("Signals", "14 places · no hotspot now") + unrest_head((96, None, 28, 62)) + '<div>' + unrest_rows(UN, (96, None, 28, 62)) + '</div>' + '<div>' + other_rows() + '</div>', "Signals", gap=5)
left2 = panel(24, 690, 432, 248, hd("Leaders in the news", "place · outlets, last 6 h") + '<div>' + leader_rows(LD[:7]) + '</div>', "Leaders the news placed", gap=4)
right = panel(1436, 84, 460, 860, hd("Layers and feeds", "count · source · age at capture") + tiles() + rule() + launches() + quakes(5) + note('Ground: NASA Blue Marble. Ages are measured from the frozen capture.'), "Layers, feeds, launches, earthquakes")
hide = [(24, 84, 432, 860), (1436, 84, 460, 860), (470, 950, 980, 130)]
body = (markers('whole', hide) + topbar('Whole Earth') + left + left2 + right + picker('whole', 470, 950)
        + campill(24, 946, 'Seen from 35,786 km above 25° N 42° E')
        + legend(28, 990, ['mil', 'clash', 'protest', 'ship', 'quake', 'launch', 'outage', 'name'], 430))
page('EyeWhole.dc.html', 'Eye, whole Earth', 'whole', body, 'The whole Earth disc from geostationary distance, centred on the Middle East')

# ===== 2 Theatre =====
cam = V['theatre']['cams'][0][0]
hide = [(24, 84, 152, 700), (24, 800, 1872, 256), (1556, 84, 340, 190)]
def inview(kind): return [i for i, x, y, c in seen('theatre', kind, hide)]
u = inview('unrest'); l = inview('leaders'); m = inview('mil')
from collections import Counter
types = Counter((a['type'] or 'unknown') for a in m).most_common(6)
fr = []
for c in reversed(FR['changes']):
    if c['text'] not in [f['text'] for f in fr]: fr.append(c)
cw = 364
def card(i, inner, label): return panel(24 + i*(cw + 13), 800, cw, 256, inner, label, gap=4)
cards = (card(0, hd("Clashes and protests", f"{len(u)} in this view") + row([("Place", ""), ("Coded as", ""), ("Out", R), ("Age", R)], (84, None, 26, 56), True, 18) + '<div>' + unrest_rows(u[:7], (84, None, 26, 56), 25) + '</div>', "Clashes and protests in this view")
         + card(1, hd("Front line, Ukraine", "DeepState · 1 d 14 h") + f'<div style="{SG}; font-weight: 600; font-size: 22px; line-height: 1.1">116,892 km² <span style="font-size: 13px; font-weight: 400; color: {MUT}">occupied · +27 km² since 8 Nov</span></div>' + '<div>' + ''.join(row([(E(c['text'].replace('The enemy has advanced ', 'Advance ').replace('The enemy advanced ', 'Advance ')), ""), (age(c['time']), M + "; " + R)], [None, 46], False, 25) for c in fr[:6]) + '</div>', "Front line")
         + card(2, hd("Military aircraft", f"{len(m)} in this view, of 120") + row([("Type code", ""), ("Aircraft", R)], (None, 60), True, 18) + '<div>' + ''.join(row([(E(t), B), (str(n), R)], [None, 60], False, 25) for t, n in types) + '</div>' + note('Type codes as broadcast · adsb.fi, 12 s'), "Military aircraft in this view")
         + card(3, hd("Leaders placed here", "GDELT, last 6 h") + row([("Leader", ""), ("Where the news put them", ""), ("Out", R)], (None, 130, 30), True, 18) + '<div>' + leader_rows(l[:7]) + '</div>', "Leaders the news placed in this view")
         + card(4, hd("Also in this view", "") + '<div>' + ''.join(row([(a, B), (b, "color: #e6eaed")], [84, None], False, 25) for a, b in [("Outage", "Serbia, routing signal, 4.9 d · IODA"), ("Outage", "Gibraltar, routing signal, 11.9 d · IODA"), ("Hotspots", "none: no place has 3 kinds of signal"), ("Carriers", "none in view · USNI is 22 d old"), ("Not set up", "world ships, hijacks, Windy cameras")]) + '</div>' + note('The list follows the camera: turn or zoom and it changes.'), "Other items in this view"))
alt_km = cam.alt*6371
brg = (math.degrees(math.atan2(math.sin((34-19)*r)*math.cos(49*r), math.cos(35*r)*math.sin(49*r) - math.sin(35*r)*math.cos(49*r)*math.cos((34-19)*r))) + 360) % 360
camp = panel(1556, 84, 340, 190, hd("Camera", "this view") + '<div>' + ''.join(row([(a, M), (b, B + "; " + R)], [110, None], False, 27) for a, b in [("Above", "35° N 19° E"), ("Height", f"{km(alt_km)} km"), ("Looking at", "49° N 34° E"), ("Bearing", f"{brg:.0f}° (north-east)")]) + '</div>', "Camera position", gap=4)
body = markers('theatre', hide, occupied=True) + topbar('Theatre: Europe and the Black Sea') + picker('theatre', 24, 84, True) + camp + cards + legend(196, 92, ['mil', 'clash', 'occ', 'front', 'outage', 'name'])
page('EyeTheatre.dc.html', 'Eye, theatre', 'theatre', body, 'Europe and the Black Sea seen at an angle from above the central Mediterranean, the horizon near the top')

# ===== 3 Day and night =====
s = unit(*SUN)
def sunalt(lon, lat): return math.degrees(math.asin(float(unit(lon, lat) @ s)))
def phase(a): return ('day', '#ffe9a8') if a > 0 else (('dusk', '#ffb08a') if a > -12 else ('night', '#9fb8ff'))
hide = [(24, 84, 680, 972), (1576, 84, 320, 300), (760, 950, 1000, 130)]
rowsd = []
for i, x, y, c in seen('dusk', 'unrest', hide): rowsd.append((i['lon'], i['lat'], i['cat'].capitalize(), E(i['place']), f"{i['outlets']} outlets · {age(i['last'])}", 'GDELT'))
for i, x, y, c in seen('dusk', 'leaders', hide): rowsd.append((i['lon'], i['lat'], 'Leader', E(i['place']), f"{E(i['name'])} · {i['outlets']} outlets", 'GDELT'))
for i, x, y, c in seen('dusk', 'ships', hide): rowsd.append((i['lon'], i['lat'], 'US ship', E((i['port'] or i['region']).replace('the ', '')), f"{E(i['name'].replace('USS ', ''))} {i['hull']} · by {i['placed']}", 'USNI, late'))
for i, x, y, c in seen('dusk', 'quakes', hide): rowsd.append((i['lon'], i['lat'], 'Quake', E(i['place'].split(' of ', 1)[-1]), f"M{i['mag']:.1f} · {age(i['time'])} ago", 'USGS'))
for i, x, y, c in seen('dusk', 'launches', hide): rowsd.append((i['lon'], i['lat'], 'Launch', E(i['site'].split(' ')[0]), E(i['name'].split(' | ')[0]) + ' · ' + i['net'][8:10] + ' Nov ' + i['net'][11:16], 'LL2'))
rowsd.sort(key=lambda t: sunalt(t[0], t[1]))
Wd = (64, 132, None, 78, 86)
tbl = row([("Kind", ""), ("Place", ""), ("What", ""), ("Source", ""), ("Sun there", R)], Wd, True, 20) + '<div>' + ''.join(row([(k, M), (p, B), (w, "color: #e6eaed"), (src, M + "; font-size: 12px"), (f'<span style="color: {phase(sunalt(lo, la))[1]}">{phase(sunalt(lo, la))[0]}</span> {sunalt(lo, la):+.0f}°', R)], Wd, False, 27) for lo, la, k, p, w, src in rowsd[:24]) + '</div>'
def big(label, val, sub): return f'<div style="flex: 1; box-sizing: border-box; padding: 9px 12px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.12); background: rgba(255,255,255,0.06)"><div style="font-size: 12px; color: {MUT}">{label}</div><div style="{SG}; font-weight: 600; font-size: 20px; white-space: nowrap">{val}</div><div style="font-size: 12px; color: {MUT}; white-space: nowrap">{sub}</div></div>'
left = panel(24, 84, 680, 972, hd("Day and night", "computed for 17 Nov 2026, 10:01 UTC", 17)
             + '<div style="display: flex; gap: 8px">' + big("Sun overhead at", f"{abs(SUN[1]):.1f}° S {SUN[0]:.1f}° E", "over southern Africa") + big("On this side", f"{len(rowsd)} items", "24 listed, night first") + big("Shading", "0° to −12°", "sun height, twilight") + '</div>'
             + hd("On this side of the Earth, from night to day", "sun height at each place") + tbl
             + note('Sun height is geometry worked out from the date and time, not a measurement. US ship positions are from the USNI tracker of 26 Oct (22 days old); region placements are approximate.'), "Day and night", gap=7)
rp = panel(1576, 84, 320, 300, hd("What is drawn", "") + note('<b style="color: #f2f4f6">Day side:</b> NASA Blue Marble, a cloud-free composite, not today\'s weather.') + note('<b style="color: #f2f4f6">Night side:</b> NASA Black Marble city lights, a composite of past years. It shows where lights are, not tonight\'s sky.') + note('<b style="color: #f2f4f6">The edge:</b> fades from sunset to the end of nautical twilight, placed for the capture time.') + note('Marks are at their real places on both sides.'), "What is drawn", gap=9)
body = markers('dusk', hide) + topbar('Day and night') + left + rp + picker('dusk', 760, 950) + campill(1576, 396, 'Seen from 35,786 km above 22° N 112° E')
page('EyeDusk.dc.html', 'Eye, day and night', 'dusk', body, 'The Earth disc centred on South-East Asia with the evening edge crossing it: India in daylight, China and Japan at night with city lights')

# ===== 4 Two sides =====
hide = [(24, 868, 1872, 188), (884, 150, 152, 700)]
REG = [("The Americas", "1 clash · 2 US ships · 2 leaders · 3 quakes", [("Washington", "clash · conventional military force · 8 outlets · 16 min", "GDELT"), ("US ships", "Reagan left San Diego · Eisenhower left Norfolk", "USNI, late"), ("Leaders", "Trump, Washington (60) · Carney, Ottawa (5)", "GDELT"), ("Quakes", "M5.4, M4.8, M4.7 off Changuillo, Peru · 15 to 18 h", "USGS"), ("Launches", "Vandenberg: Falcon 9 on 19 and 21 Nov", "LL2")]),
       ("Europe and Russia", "5 clashes · front · 1 navy warning · 5 leaders", [("Kyiv", "clash · conventional military force · 7 outlets · 1 min", "GDELT"), ("Moscow", "clash · conventional military force · 5 outlets · 1 min", "GDELT"), ("Front", "116,892 km² occupied, +27 km² since 8 Nov", "DeepState"), ("Hebrides", "live weapons firing, 17 to 20 Nov", "UKHO"), ("Leaders", "Putin (27) · Burnham (4) · Tusk (3) · Zelenskyy (3) · Sánchez (2)", "GDELT")]),
       ("Middle East and Africa", "3 clashes · 3 US ships · 6 leaders · 1 quake", [("Gaza", "clash · conventional military force · 5 outlets · 16 min", "GDELT"), ("Tehran", "clash · aerial weapons · 3 outlets · 1 min", "GDELT"), ("Arabian Sea", "George Washington, Bush, Boxer, placed by region", "USNI, late"), ("Leaders", "Netanyahu (5) · Tinubu (3) · Aliyev, Ruto, Ramaphosa, Kagame (2)", "GDELT"), ("Quake", "M4.8 north of Caluula, Somalia · 20.5 h", "USGS")]),
       ("Asia and the Pacific", "5 places · 3 US ships · 4 leaders · 7 quakes", [("Manila", "protest · demonstration or rally · 4 outlets · 2.5 h", "GDELT"), ("New Delhi", "clash · artillery and tanks · 2 outlets · 1 min", "GDELT"), ("US ships", "Makin Island, Tripoli (Sasebo), Roosevelt (Philippine Sea)", "USNI, late"), ("Leaders", "Anwar (9) · Modi (4) · Khurelsukh (4) · Takaichi (2)", "GDELT"), ("Quakes", "M6.6 off Tual, Indonesia · 12.8 h · 6 more", "USGS")])]
cols = ''
for n, (t, sub, rws) in enumerate(REG):
    cols += panel(24 + n*471, 868, 459, 188, hd(t, sub) + '<div>' + ''.join(row([(a, B), (b, "color: #e6eaed"), (c, R + "; font-size: 12px; " + ("color: #ffcf8a" if 'late' in c else M))], [84, None, 74], False, 26) for a, b, c in rws) + '</div>', t, pad=12, gap=3)
cap1 = campill(190, 84, 'The Americas · centred 20° N 100° W · from 35,786 km'); cap2 = campill(1100, 84, 'Europe, Africa, Asia · centred 20° N 75° E · from 35,786 km')
body = markers('sides', hide) + topbar('Two sides') + cap1 + cap2 + picker('sides', 884, 150, True) + cols
page('EyeSides.dc.html', 'Eye, two sides', 'sides', body, 'Two Earth discs side by side: the Americas on the left, Europe, Africa and Asia on the right')

# ===== 5 Wall of four =====
WN = [("Europe", 16, 50), ("Middle East", 46, 29), ("East Asia", 118, 28), ("North America", -96, 37)]
ov = ''
for (cam, x, y, w, h), (nm, lo, la) in zip(V['wall']['cams'], WN):
    rect = (x, y, w, h); cnt = {}
    for k in ('mil', 'unrest', 'leaders', 'ships', 'quakes', 'launches'):
        cnt[k] = [i for i in IT[k] if (lambda p: p[2] and inr(p[0], p[1], rect))(cam.proj(i['lon'], i['lat']))]
    top = sorted(cnt['unrest'], key=lambda i: -i['outlets'])[:1]
    line = (f"{E(top[0]['place'])}: {top[0]['cat']}, {top[0]['outlets']} outlets, {age(top[0]['last'])}" if top else "no clash or protest with 2+ outlets here")
    chips = ''.join(f'<span style="white-space: nowrap"><b style="{SG}; font-size: 15px; color: #f2f4f6">{len(cnt[k])}</b> {lab}</span>' for k, lab in [('mil', 'military aircraft'), ('unrest', 'clashes, protests'), ('leaders', 'leaders'), ('ships', 'US ships')])
    ov += (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; box-sizing: border-box; border: 1px solid rgba(255,255,255,0.16); border-radius: 18px"></div>'
           f'<div style="position: absolute; left: {x+12}px; top: {y+12}px; padding: 6px 12px; border-radius: 999px; {G}; display: flex; gap: 10px; align-items: baseline"><span style="{SG}; font-weight: 600; font-size: 15px">{nm}</span><span style="font-size: 12px; color: {MUT}">above {abs(la)}° {"N" if la >= 0 else "S"} {abs(lo)}° {"E" if lo >= 0 else "W"} · {km(cam.alt*6371)} km up</span></div>'
           f'<div style="position: absolute; left: {x+12}px; top: {y+h-64}px; width: {w-24}px; height: 52px; box-sizing: border-box; padding: 6px 14px; border-radius: 16px; {G}; font-size: 12px; color: {MUT}"><div style="display: flex; gap: 18px; align-items: baseline">{chips}</div><div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #e6eaed">{line}</div></div>')
right = panel(1448, 76, 448, 980, hd("Layers and feeds", "count · source · age at capture") + tiles() + rule() + launches() + quakes(4) + rule() + hd("Signals", "top of 14") + '<div>' + unrest_rows(UN[:5], (92, None, 26, 60)) + '</div>', "Layers, feeds, launches, earthquakes, signals", gap=7)
hide = [(36, 76+440-64, 676, 52), (748, 76+440-64, 676, 52), (36, 528+440-64, 676, 52), (748, 528+440-64, 676, 52)]
body = markers('wall', hide) + ov + topbar('Wall of four').replace('left: 640px; top: 14px', 'left: 640px; top: 14px; transform: scale(0.9); transform-origin: left center') + right + legend(28, 990, ['mil', 'clash', 'protest', 'ship', 'quake', 'launch', 'outage', 'name'], 1400) + campill(28, 1024, 'Four fixed looks straight down. Click a tile to make it the main view; the counts are what falls inside each frame.')
page('EyeWall.dc.html', 'Eye, wall of four', 'wall', body, 'Four views straight down: Europe, the Middle East, East Asia and North America')

# ===== 6 Look down: front line =====
cam = V['front']['cams'][0][0]
hide = [(24, 84, 152, 700), (1404, 84, 492, 972)]
u = [i for i, x, y, c in seen('front', 'unrest', hide)]; m = [i for i, x, y, c in seen('front', 'mil', hide)]; l = [i for i, x, y, c in seen('front', 'leaders', hide)]
lab = ''
for c in fr[:4]:
    x, y, vis = cam.proj(c['lon'], c['lat'])
    if vis: lab += f'<text x="{x+10:.0f}" y="{y+4:.0f}" fill="#ffffff" font-family="Inter, sans-serif" font-size="12" stroke="#000000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">{E(c["place"])}</text>'
for i in u:
    x, y, vis = cam.proj(i['lon'], i['lat']); lab += f'<text x="{x+14:.0f}" y="{y+4:.0f}" fill="#ffffff" font-family="Inter, sans-serif" font-size="13" font-weight="600" stroke="#000000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">{E(i["place"])} {i["outlets"]}</text>'
labs = '<svg width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true" style="position: absolute; left: 0; top: 0">' + lab + f'<circle cx="{cam.cx}" cy="{cam.cy}" r="150" fill="none" stroke="#ffcf8a" stroke-opacity="0.7" stroke-width="1.2" stroke-dasharray="2 7"></circle><path d="M{cam.cx-170} {cam.cy} h40 M{cam.cx+130} {cam.cy} h40 M{cam.cx} {cam.cy-170} v40 M{cam.cx} {cam.cy+130} v40" stroke="#ffcf8a" stroke-width="1.4"></path></svg>'
def act(t): return f'<button type="button" style="flex: 1; height: 44px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.22); background: rgba(255,255,255,0.06); color: #f2f4f6; font: 500 14px \'Space Grotesk\', sans-serif">{t}</button>'
sheet = panel(1404, 84, 492, 972,
    f'<div style="font-size: 12px; color: #ffb08a; font-weight: 500">Front line · Ukraine · selected</div><div style="{SG}; font-weight: 700; font-size: 34px; line-height: 1.05; letter-spacing: -0.01em">116,892 km²</div><div style="color: {MUT}">occupied, by DeepState\'s map · an assessment by a Ukrainian open-source team, hours to a day behind</div>'
    + '<div style="display: flex; gap: 8px">' + big("Since 8 Nov", "+27 km²", "was 116,865 km²") + big("Newest update", "1 d 14 h", "before the capture") + big("In this view", f"{len(m)} aircraft", f"{len(u)} clash places") + '</div>'
    + '<div style="display: flex; gap: 8px">' + act("Country dossier") + act("Spy passes") + act("Photographed by") + '</div>'
    + rule() + hd("Changes DeepState logged", "newest first · age") + '<div>' + ''.join(row([(E(c['text']), "color: #e6eaed"), (age(c['time']), M + "; " + R)], [None, 50], False, 28) for c in fr[:8]) + '</div>'
    + rule() + hd("Also in this view", "") + '<div>' + unrest_rows(u, (92, None, 26, 60), 28) + ''.join(row([(E(i['name']), B), (f"placed in {E(i['place'])} by {i['outlets']} outlets", "color: #e6eaed"), ("GDELT", M + "; " + R)], [150, None, 50], False, 28) for i in l) + '</div>'
    + note('Clashes are GDELT\'s machine coding of news reports, not verified.')
    + f'<div style="margin-top: auto; font-size: 12px; color: {MUT}">Ground: NASA Blue Marble, about 500 m per pixel here; the app\'s sharp photo layer would replace it at this zoom.</div>', "Front line, Ukraine", gap=10, pad=18)
body = markers('front', hide, names=False, occupied=True, big=True) + labs + topbar('Look down: eastern Ukraine') + picker('front', 24, 84, True) + sheet + campill(196, 92, f'Looking straight down from {km(cam.alt*6371)} km above 48.3° N 35.2° E') + legend(196, 140, ['occ', 'front', 'clash', 'mil'])
page('EyeFront.dc.html', 'Eye, look down', 'front', body, 'Eastern Ukraine and the Sea of Azov seen straight down')

# ===== 7 Search over the horizon =====
hide = [(520, 150, 880, 640)]
def res(kind, title, sub, right, on=False):
    return (f'<div style="display: flex; align-items: center; gap: 14px; height: 56px; padding: 0 14px; border-radius: 14px; {"background: rgba(255,255,255,0.12); border: 1px solid rgba(255,207,138,0.5)" if on else "border: 1px solid transparent"}">'
            f'<span style="width: 92px; flex: none; font-size: 12px; color: {MUT}">{kind}</span><div style="flex: 1; min-width: 0"><div style="{SG}; font-weight: 600; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{title}</div><div style="font-size: 12px; color: {MUT}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{sub}</div></div><span style="font-size: 12px; color: {MUT}; white-space: nowrap">{right}</span></div>')
def grp(t): return f'<div style="font-size: 12px; color: {MUT}; padding: 6px 14px 0">{t}</div>'
pal = panel(520, 150, 880, 640,
    f'<div style="display: flex; align-items: center; gap: 12px; height: 60px; padding: 0 16px; border-radius: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.22)"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="9" cy="9" r="6"></circle><path d="M14 14 L18 18"></path></svg><span style="{SG}; font-size: 22px; font-weight: 500">ukr</span><span style="width: 2px; height: 26px; background: #ffcf8a"></span><span style="margin-left: auto; font-size: 12px; color: {MUT}">country, person, place or callsign</span></div>'
    + grp('Country') + res('Country', 'Ukraine', 'Open the country dossier: travel advice, right now, news places, from above', 'Enter', True)
    + grp('On the map now · from the capture') + res('Clash', 'Kyiv', 'use of conventional military force · 7 outlets · GDELT, not verified', '1 min') + res('Clash', 'Kharkiv', 'use of conventional military force · 2 outlets · GDELT, not verified', '1.8 h') + res('Attack', 'Cherkasy', 'physical assault · 2 outlets · GDELT, not verified', '16 min')
    + res('Front line', 'Front line, Ukraine', '116,892 km² occupied · +27 km² since 8 Nov · DeepState', '1 d 14 h') + res('Leader', 'Volodymyr Zelenskyy', 'placed in Crimea by 3 outlets in the last 6 h · where the news put him, not a position', 'GDELT')
    + grp('People · Wikidata') + f'<div style="padding: 4px 14px; font-size: 13px; color: {MUT}">Asked when you stop typing. Not part of this frozen capture, so nothing is listed here.</div>'
    + f'<div style="margin-top: auto; display: flex; gap: 18px; font-size: 12px; color: {MUT}; padding: 0 14px"><span>↑ ↓ move</span><span>Enter open</span><span>Tab fly there without opening</span><span>Esc close</span></div>', "Search", gap=4, pad=16, extra='background: rgba(10,14,18,0.82);')
body = markers('horizon', hide) + '<div style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; background: rgba(0,0,0,0.35)"></div>' + topbar('Search') + pal + picker('horizon', 470, 950)
page('EyeSearch.dc.html', 'Eye, search', 'horizon', body, 'The Earth with the horizon across the upper part, the Middle East in the middle')
print('theatre in view', len(u), 'dusk rows', len(rowsd))
