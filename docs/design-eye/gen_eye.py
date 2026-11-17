import json, math, html
from views import V, SUN, CAP, GEO
from cam import unit, r
import numpy as np
D = '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/dd/'
OUT = '/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/dc/project/'
IT = json.load(open(D + 'out/markers.json'))['items']
FR = json.load(open(D + 'front_ukraine.json'))['payload']
IMG = dict(whole='897b808cc9cfb4d4b27565602d27ebcf', horizon='283a475d8bcb273526c7ace06fdc1047', theatre='63f8c8ae66fe9d0ed5ce885a6fdbb26a', dusk='51b1e5f84408a08c35d97773c404f5a5',
           sides='2e12c1500d08c39927a200cfe12e43e1', wall='98d1bf3e81097551f7c327da03e3c66c', front='62d113b30b3eaf2ccffd62776dbe80ed', polar='db4ff5b8144a0ad5e3004814040bc30e', low='8246cbb27adfc6d11c4d0955388fc96c', chase='342eb94e22cdb34ced0376f98b93b5ec',
           whole_lights='9b0e27962e222f6b451f5ae5a093f99f', theatre_outline='e3b35d0f6e83ebe372d6bbc9ea204374', horizon_mono='04c3705ce62781467d6f7cddda162d39', grounds='51e8be19e0ec3703bb44e291f911fd5e', flat='0968e5dcab29d571c2dad1b6c436d042')
NAMES = [('whole', 'Whole Earth'), ('horizon', 'Horizon'), ('theatre', 'Theatre'), ('dusk', 'Day and night'), ('sides', 'Two sides'), ('wall', 'Wall of four'), ('front', 'Look down')]
MORE = [('polar', 'Over the pole'), ('low', 'Low orbit'), ('chase', 'Chase'), ('flat', 'Flat map')]
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
                    col = '#ff3b5c' if a.get('kind') == 'occupied' else '#ff8fa3'
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
            s.append(f'<path d="M0 -7 L6 5 L-6 5 Z" fill="#b9a2ff" stroke="#120a2e" stroke-width="1" transform="translate({x:.1f} {y:.1f})"></path>')
    if 'ships' in kinds:
        done = set()
        for i, x, y, cam in seen(view, 'ships', hide):
            k = (round(x), round(y))
            if k in done: continue
            done.add(k)
            dash = ' stroke-dasharray="3 3"' if i['placed'] == 'region' else ''
            s.append(f'<path d="M0 -7 L7 0 L0 7 L-7 0 Z" fill="#5fe3ff" stroke="#04202a" stroke-width="1" transform="translate({x:.1f} {y:.1f})"></path><circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="none" stroke="#5fe3ff" stroke-width="1"{dash}></circle>')
    if 'outages' in kinds:
        for i, x, y, cam in seen(view, 'outages', hide):
            s.append(f'<rect x="{x-11:.1f}" y="{y-8:.1f}" width="22" height="16" rx="3" fill="rgba(10,14,18,0.7)" stroke="#c9d1d6" stroke-width="1"></rect><text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" fill="#f2f4f6" font-family="Inter, sans-serif" font-size="10" font-weight="600">{i["code"]}</text>')
    if 'unrest' in kinds:
        for i, x, y, cam in seen(view, 'unrest', hide):
            rad = 4.5 + math.sqrt(i['outlets'])*1.6
            if i['cat'] == 'protest': s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="none" stroke="#ffc2cd" stroke-width="2.2"></circle>')
            else: s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="#ff3b5c" fill-opacity="0.9" stroke="#2a0510" stroke-width="1"></circle>')
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
C = {'ok': '#7be0a0', 'late': '#ffe066', 'fail': '#ff6b6b', 'off': '#9aa3a9'}
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
def launches(): return hd("Coming up", "Launch Library 2, UTC") + '<div>' + ''.join(row([(d, "color: #c8b8ff"), (n, ""), (g, M + "; " + R)], [96, None, 74]) for d, n, g in LAUNCH) + '</div>'
def quakes(n=4):
    q = sorted(IT['quakes'], key=lambda q: -q['mag'])[:n]
    return hd("Earthquakes M4.5+", "USGS · age") + '<div>' + ''.join(row([(f"M{i['mag']:.1f}", B), (E(i['place'].split(' of ', 1)[-1]), ""), (age(i['time']), M + "; " + R)], [44, None, 50]) for i in q) + '</div>'
def kc(k): return "#ffc2cd" if k == "protest" else "#ff8fa3"
def unrest_rows(items, widths=(104, None, 30, 76), h=26):
    return ''.join(row([(E(i['place']), B), (f'<span style="color: {kc(i["cat"])}">{i["cat"]}</span> · {E(i["action"])}', "color: #e6eaed"), (str(i['outlets']), B + "; " + R), (age(i['last']), M + "; " + R)], widths, False, h) for i in items)
def unrest_head(widths=(104, None, 30, 76)): return row([("Place", ""), ("Coded as (GDELT, machine-coded, not verified)", ""), ("Out", R), ("Age", R)], widths, True, 20)
def topbar(sub):
    nav = ''.join(f'<a href="#{n.lower()}" style="padding: 11px 13px; border-radius: 999px; text-decoration: none; {"background: #f2f4f6; color: #0a0e12" if i == 0 else ""}">{n}</a>' for i, n in enumerate(['Overview', 'Conflict', 'Air', 'Sea', 'Space', 'Networks', 'Earth', 'Munich']))
    return (f'<div style="position: absolute; left: 28px; top: 12px"><div style="display: flex; align-items: baseline; gap: 12px"><span style="{SG}; font-weight: 700; font-size: 22px; letter-spacing: -0.01em">World Watch</span><span style="{SG}; font-weight: 500; font-size: 15px; color: #8fdcff">{sub}</span></div><div style="color: {MUT}; font-size: 12px">Frozen capture 17 Nov 2026, 10:01 UTC</div></div>'
            f'<nav aria-label="Views" style="position: absolute; left: 640px; top: 14px; height: 48px; box-sizing: border-box; padding: 0 6px; border-radius: 999px; {G}; display: flex; align-items: center; gap: 2px; {SG}; font-weight: 500; font-size: 14px">{nav}</nav>'
            f'<div style="position: absolute; right: 24px; top: 14px; display: flex; gap: 8px; align-items: center"><div style="padding: 0 14px; height: 48px; display: flex; align-items: center; border-radius: 999px; {G}; font-size: 13px">40 of 45 feeds current · 1 late · 1 failing · 3 not set up</div>'
            f'<button type="button" aria-label="Layers" style="height: 48px; padding: 0 16px; border-radius: 999px; {G}; color: #f2f4f6; font: 500 14px \'Space Grotesk\', sans-serif">Layers</button>'
            f'<button type="button" aria-label="Settings" style="width: 48px; height: 48px; border-radius: 999px; {G}; color: #f2f4f6; display: grid; place-items: center"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3.2"></circle><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"></path></svg></button></div>')
def picker(cur, x, y, vertical=False, full=False):
    tw, th = (128, 62) if vertical else (128, 72)
    its = ''
    for k, n in (NAMES + MORE if full else NAMES):
        on = k == cur
        its += (f'<a href="#{k}" aria-current="{"true" if on else "false"}" style="display: flex; flex-direction: column; gap: 4px; text-decoration: none; color: {"#ffffff" if on else MUT}; font-size: 12px; font-weight: {600 if on else 400}">'
                f'<img src="/_blob/{IMG[k]}" alt="" style="width: {tw}px; height: {th}px; object-fit: cover; border-radius: 10px; border: {"2px solid #8fdcff" if on else "1px solid rgba(255,255,255,0.18)"}; box-sizing: border-box; display: block">{n}</a>')
    if not full and not vertical: its += f'<a href="#more" style="display: flex; flex-direction: column; justify-content: center; align-items: center; width: 64px; height: {th}px; border-radius: 10px; border: 1px dashed rgba(255,255,255,0.3); text-decoration: none; color: {MUT}; font-size: 12px; text-align: center">4 more</a>'
    if vertical: return f'<nav aria-label="Views of the globe" style="position: absolute; left: {x}px; top: {y}px; width: 152px; box-sizing: border-box; padding: 12px; border-radius: 22px; {G}; display: flex; flex-direction: column; gap: 9px">{its}</nav>'
    return f'<nav aria-label="Views of the globe" style="position: absolute; left: {x}px; top: {y}px; height: 118px; box-sizing: border-box; padding: 12px 14px; border-radius: 22px; {G}; display: flex; gap: 10px">{its}</nav>'
def campill(x, y, text, right=False):
    pos = f'right: {x}px' if right else f'left: {x}px'
    return f'<div style="position: absolute; {pos}; top: {y}px; padding: 8px 14px; border-radius: 999px; {G}; font-size: 13px; color: {MUT}; white-space: nowrap">{text}</div>'
def legend(x, y, kinds, w=None):
    L = {'mil': ('<svg width="10" height="12" viewBox="-5 -6 10 12" aria-hidden="true"><path d="M0 -6 L4 5 L0 2.6 L-4 5 Z" fill="#ffffff"></path></svg>', 'Military aircraft'),
         'clash': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="#ff3b5c"></circle></svg>', 'Clash, attack'),
         'protest': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.2" fill="none" stroke="#ffc2cd" stroke-width="2"></circle></svg>', 'Protest'),
         'front': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="2" width="8" height="8" fill="none" stroke="#ffffff" stroke-width="1.5"></rect></svg>', 'Front-line change'),
         'occ': ('<svg width="14" height="12" viewBox="0 0 14 12" aria-hidden="true"><rect x="1" y="1" width="12" height="10" fill="#ff3b5c" fill-opacity="0.35" stroke="#ff3b5c"></rect></svg>', 'Occupied (DeepState)'),
         'ship': ('<svg width="14" height="14" viewBox="-7 -7 14 14" aria-hidden="true"><path d="M0 -6 L6 0 L0 6 L-6 0 Z" fill="#5fe3ff"></path></svg>', 'US carrier or amphib (22 d old)'),
         'quake': ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.5" fill="none" stroke="#ffffff" stroke-width="1.5"></circle></svg>', 'Quake M4.5+'),
         'launch': ('<svg width="12" height="12" viewBox="-6 -7 12 13" aria-hidden="true"><path d="M0 -6 L5 5 L-5 5 Z" fill="#b9a2ff"></path></svg>', 'Launch pad, next 4 days'),
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
a{{color:#ffffff}}a:hover{{color:#8fdcff}}
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
OTHER = [("Front, Ukraine", "+27 km² since 8 Nov · newest advance near Vilne", "DeepState · 1 d 14 h", ""), ("Arabian Sea", "2 US carriers, 1 amphib, placed by region", "USNI · 22 d, late", "color: #ffe066"),
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
def phase(a): return ('day', '#fff0b8') if a > 0 else (('dusk', '#c9a8ff') if a > -12 else ('night', '#8fb0ff'))
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
    cols += panel(24 + n*471, 868, 459, 188, hd(t, sub) + '<div>' + ''.join(row([(a, B), (b, "color: #e6eaed"), (c, R + "; font-size: 12px; " + ("color: #ffe066" if 'late' in c else M))], [84, None, 74], False, 26) for a, b, c in rws) + '</div>', t, pad=12, gap=3)
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
labs = '<svg width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true" style="position: absolute; left: 0; top: 0">' + lab + f'<circle cx="{cam.cx}" cy="{cam.cy}" r="150" fill="none" stroke="#8fdcff" stroke-opacity="0.7" stroke-width="1.2" stroke-dasharray="2 7"></circle><path d="M{cam.cx-170} {cam.cy} h40 M{cam.cx+130} {cam.cy} h40 M{cam.cx} {cam.cy-170} v40 M{cam.cx} {cam.cy+130} v40" stroke="#8fdcff" stroke-width="1.4"></path></svg>'
def act(t): return f'<button type="button" style="flex: 1; height: 44px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.22); background: rgba(255,255,255,0.06); color: #f2f4f6; font: 500 14px \'Space Grotesk\', sans-serif">{t}</button>'
sheet = panel(1404, 84, 492, 972,
    f'<div style="font-size: 12px; color: #ff8fa3; font-weight: 500">Front line · Ukraine · selected</div><div style="{SG}; font-weight: 700; font-size: 34px; line-height: 1.05; letter-spacing: -0.01em">116,892 km²</div><div style="color: {MUT}">occupied, by DeepState\'s map · an assessment by a Ukrainian open-source team, hours to a day behind</div>'
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
    return (f'<div style="display: flex; align-items: center; gap: 14px; height: 56px; padding: 0 14px; border-radius: 14px; {"background: rgba(255,255,255,0.12); border: 1px solid rgba(143,220,255,0.6)" if on else "border: 1px solid transparent"}">'
            f'<span style="width: 92px; flex: none; font-size: 12px; color: {MUT}">{kind}</span><div style="flex: 1; min-width: 0"><div style="{SG}; font-weight: 600; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{title}</div><div style="font-size: 12px; color: {MUT}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{sub}</div></div><span style="font-size: 12px; color: {MUT}; white-space: nowrap">{right}</span></div>')
def grp(t): return f'<div style="font-size: 12px; color: {MUT}; padding: 6px 14px 0">{t}</div>'
pal = panel(520, 150, 880, 640,
    f'<div style="display: flex; align-items: center; gap: 12px; height: 60px; padding: 0 16px; border-radius: 16px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.22)"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="9" cy="9" r="6"></circle><path d="M14 14 L18 18"></path></svg><span style="{SG}; font-size: 22px; font-weight: 500">ukr</span><span style="width: 2px; height: 26px; background: #8fdcff"></span><span style="margin-left: auto; font-size: 12px; color: {MUT}">country, person, place or callsign</span></div>'
    + grp('Country') + res('Country', 'Ukraine', 'Open the country dossier: travel advice, right now, news places, from above', 'Enter', True)
    + grp('On the map now · from the capture') + res('Clash', 'Kyiv', 'use of conventional military force · 7 outlets · GDELT, not verified', '1 min') + res('Clash', 'Kharkiv', 'use of conventional military force · 2 outlets · GDELT, not verified', '1.8 h') + res('Attack', 'Cherkasy', 'physical assault · 2 outlets · GDELT, not verified', '16 min')
    + res('Front line', 'Front line, Ukraine', '116,892 km² occupied · +27 km² since 8 Nov · DeepState', '1 d 14 h') + res('Leader', 'Volodymyr Zelenskyy', 'placed in Crimea by 3 outlets in the last 6 h · where the news put him, not a position', 'GDELT')
    + grp('People · Wikidata') + f'<div style="padding: 4px 14px; font-size: 13px; color: {MUT}">Asked when you stop typing. Not part of this frozen capture, so nothing is listed here.</div>'
    + f'<div style="margin-top: auto; display: flex; gap: 18px; font-size: 12px; color: {MUT}; padding: 0 14px"><span>↑ ↓ move</span><span>Enter open</span><span>Tab fly there without opening</span><span>Esc close</span></div>', "Search", gap=4, pad=16, extra='background: rgba(10,14,18,0.82);')
body = markers('horizon', hide) + '<div style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; background: rgba(0,0,0,0.35)"></div>' + topbar('Search') + pal + picker('horizon', 470, 950)
page('EyeSearch.dc.html', 'Eye, search', 'horizon', body, 'The Earth with the horizon across the upper part, the Middle East in the middle')

# ================= second round: grounds and more views =================
from views import AC
GROUNDS = [('photo', 'Photo'), ('mono', 'Mono'), ('lights', 'Night lights'), ('outline', 'Outline'), ('dots', 'Points'), ('relief', 'Relief')]
def groundpill(x, y, cur):
    its = ''.join(f'<a href="#{k}" style="padding: 8px 12px; border-radius: 999px; text-decoration: none; font-size: 13px; {"background: #f2f4f6; color: #0a0e12; font-weight: 600" if k == cur else "color: " + MUT}">{n}</a>' for k, n in GROUNDS)
    return f'<nav aria-label="Ground" style="position: absolute; left: {x}px; top: {y}px; height: 44px; box-sizing: border-box; padding: 0 6px 0 14px; border-radius: 999px; {G}; display: flex; align-items: center; gap: 2px"><span style="font-size: 12px; color: {MUT}; margin-right: 6px">Ground</span>{its}</nav>'
def inview(view, kind, hide): return [i for i, x, y, c in seen(view, kind, hide)]
class Flat:
    cx = 960
    def proj(s, lon, lat, h=0): return (lon + 180)/360*1920, 76 + (78 - lat)/136*725, -58 < lat < 78
V['flat'] = dict(cams=[(Flat(), 0, 76, 1920, 725)])
for k, src in [('whole_lights', 'whole'), ('theatre_outline', 'theatre'), ('horizon_mono', 'horizon')]: V[k] = V[src]

# ===== 8 Grounds =====
GI = [('Photo', 'NASA Blue Marble, a cloud-free composite. The look so far.'), ('Mono', 'The same photo with the colour taken out. Marks stand out most.'), ('Night lights', 'NASA Black Marble, a composite of past years, not tonight.'),
      ('Outline', 'Country outlines only (Natural Earth). The lightest to draw.'), ('Points', 'Land as points of light (Natural Earth), as in look 6.'), ('Relief', 'Terrain shading from NASA ASTER elevation, no colour.')]
ov = ''
for (cam, x, y, w, h), (n, d) in zip(V['grounds']['cams'], GI):
    ov += (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; box-sizing: border-box; border: 1px solid rgba(255,255,255,0.16); border-radius: 18px"></div>'
           f'<div style="position: absolute; left: {x+14}px; top: {y+12}px; {SG}; font-weight: 600; font-size: 18px">{n}</div>'
           f'<div style="position: absolute; left: {x+14}px; top: {y+h-34}px; width: {w-28}px; font-size: 12px; color: {MUT}">{d}</div>')
body = (markers('grounds', [], names=False, kinds=('mil', 'quakes', 'launches', 'ships', 'unrest')) + ov + topbar('Choose the ground')
        + legend(28, 1000, ['mil', 'clash', 'protest', 'ship', 'quake', 'launch'], 900)
        + campill(28, 1034, 'The same view and the same marks on six grounds. The ground is a setting; it can differ per view.')
        + f'<div style="position: absolute; left: 980px; top: 996px; width: 912px; font-size: 12px; color: {MUT}; line-height: 1.45">New colours, no orange: clashes and the occupied area in rose red, ships in aqua, launches in violet, aircraft and quakes white. Late feeds are yellow, failing feeds red, the selection is ice blue.</div>')
page('EyeGrounds.dc.html', 'Eye, grounds', 'grounds', body, 'Six small globes showing the same view on six grounds: photo, mono, night lights, outline, points of light, relief')

# ===== 9 Night lights, ambient layout =====
def bigcard(label, val, sub, state='ok'):
    c = C[state]
    return (f'<div style="box-sizing: border-box; height: 132px; padding: 14px 16px; border-radius: 20px; {G}; {"border-color: " + c + "88;" if state != "ok" else ""} display: flex; flex-direction: column; justify-content: space-between">'
            f'<div style="font-size: 13px; color: {MUT}">{label}</div><div style="{SG}; font-weight: 700; font-size: 40px; line-height: 1; letter-spacing: -0.02em; white-space: nowrap">{val}</div><div style="font-size: 12px; color: {c if state != "ok" else MUT}; white-space: nowrap">{sub}</div></div>')
lc = [("Military aircraft airborne", "120", "of 132 · adsb.fi · 12 s"), ("Clash and protest places", "14", "2+ outlets, of 122 · GDELT · 1 min"), ("Leaders placed by the news", "17", "last 6 h · GDELT · 57 min"), ("Earthquakes, 24 h", "168", "largest M6.6 · USGS · 1 min"), ("Internet outages ongoing", "5", "routing signal · IODA · 22 s"), ("Occupied, Ukraine", "116,892 <span style=\"font-size: 18px\">km²</span>", "+27 km² since 8 Nov · DeepState · 1 d 14 h")]
left = f'<div aria-label="Counts" style="position: absolute; left: 24px; top: 84px; width: 330px; display: flex; flex-direction: column; gap: 10px">' + ''.join(bigcard(*c) for c in lc) + '</div>'
rc = (bigcard("Hotspots", "0", "no place has 3 kinds of signal in 24 h") + bigcard("US carriers and amphibs", "8", "USNI tracker of 26 Oct · late, 22 d", 'late') + bigcard("Court records", "none", "ICC feed failing", 'fail'))
right = f'<div aria-label="Status" style="position: absolute; left: 1566px; top: 84px; width: 330px; display: flex; flex-direction: column; gap: 10px">' + rc + '</div>' + panel(1566, 510, 330, 418, hd("Coming up", "UTC") + '<div>' + ''.join(row([(d, "color: #c8b8ff"), (g, M + "; " + R)], [None, 80], False, 22) + f'<div style="height: 26px; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{n}</div>' for d, n, g in LAUNCH) + '</div>' + rule() + note('Not set up (no key): world ships, internet hijacks, Windy cameras.'), "Coming up", gap=6)
hide = [(24, 84, 330, 850), (1566, 84, 330, 850), (372, 950, 1070, 130)]
body = markers('whole_lights', hide) + topbar('Whole Earth · night lights') + left + right + picker('whole', 372, 950) + groundpill(1444, 986, 'lights') + campill(24, 1010, 'Ambient layout: big numbers only')
page('EyeLights.dc.html', 'Eye, night lights', 'whole_lights', body, 'The whole Earth disc drawn as city lights on a dark blue ground')

# ===== 10 Outline, one tall panel =====
hide = [(24, 84, 152, 700), (1476, 84, 420, 972)]
u = inview('theatre_outline', 'unrest', hide); l = inview('theatre_outline', 'leaders', hide); m = inview('theatre_outline', 'mil', hide)
types = Counter((a['type'] or 'unknown') for a in m).most_common(5)
tall = panel(1476, 84, 420, 972, hd("In this view", "follows the camera", 17)
    + '<div style="display: flex; gap: 8px">' + big("Aircraft", str(len(m)), "military, of 120") + big("Clash places", str(len(u)), "2+ outlets") + big("Leaders", str(len(l)), "placed here") + '</div>'
    + hd("Clashes and protests", "GDELT, not verified") + row([("Place", ""), ("Coded as", ""), ("Out", R), ("Age", R)], (88, None, 26, 56), True, 18) + '<div>' + unrest_rows(u[:6], (88, None, 26, 56)) + '</div>'
    + rule() + hd("Front line, Ukraine", "DeepState · 1 d 14 h") + f'<div style="{SG}; font-weight: 600; font-size: 22px; line-height: 1.1">116,892 km² <span style="font-size: 13px; font-weight: 400; color: {MUT}">occupied · +27 km² since 8 Nov</span></div>' + '<div>' + ''.join(row([(E(c['text'].replace('The enemy has advanced ', 'Advance ').replace('The enemy advanced ', 'Advance ')), ""), (age(c['time']), M + "; " + R)], [None, 46]) for c in fr[:4]) + '</div>'
    + rule() + hd("Leaders placed here", "outlets, last 6 h") + '<div>' + leader_rows(l[:5]) + '</div>'
    + rule() + hd("Military aircraft by type code", "adsb.fi · 12 s") + '<div>' + ''.join(row([(E(t), B), (str(n), R)], [None, 60]) for t, n in types) + '</div>', "In this view", gap=7, pad=16)
body = markers('theatre_outline', hide, occupied=True) + topbar('Theatre · outline') + picker('theatre', 24, 84, True) + tall + groundpill(196, 84, 'outline') + legend(196, 140, ['mil', 'clash', 'occ', 'front', 'outage', 'name'])
page('EyeOutline.dc.html', 'Eye, outline', 'theatre_outline', body, 'Europe and the Black Sea at an angle, drawn as country outlines on a dark globe')

# ===== 11 Mono with a 24-hour strip =====
hide = [(24, 868, 1872, 188)]
X0, X1 = 150, 1560
def tx(t): return X0 + (1 - (CAP - t)/86400)*(X1 - X0)
tl = ''
for hh in range(0, 25, 3):
    x = X0 + hh/24*(X1 - X0); t = CAP - (24 - hh)*3600
    import time as _t
    tl += f'<line x1="{x:.0f}" y1="34" x2="{x:.0f}" y2="150" stroke="rgba(255,255,255,0.10)"></line><text x="{x:.0f}" y="166" text-anchor="middle" fill="{MUT}" font-size="11" font-family="Inter, sans-serif">{_t.strftime("%H:%M", _t.gmtime(t))}</text>'
stack = {}
for i in sorted(IT['unrest'], key=lambda i: -i['outlets']):
    x = round(tx(i['last'])); n = stack.get(x, 0); stack[x] = n + 1
    rad = 4.5 + math.sqrt(i['outlets'])*1.6; y = 62 - n*0
    cxm = x - n*15
    tl += (f'<circle cx="{cxm}" cy="62" r="{rad:.1f}" fill="none" stroke="#ffc2cd" stroke-width="2.2"></circle>' if i['cat'] == 'protest' else f'<circle cx="{cxm}" cy="62" r="{rad:.1f}" fill="#ff3b5c" fill-opacity="0.9" stroke="#2a0510"></circle>')
for q in IT['quakes']:
    x = tx(q['time']); tl += f'<circle cx="{x:.0f}" cy="118" r="{3 + (q["mag"] - 4.5)*3.2:.1f}" fill="none" stroke="#ffffff" stroke-width="1.5"></circle>'
    if q['mag'] >= 5: tl += f'<text x="{x:.0f}" y="{96 if q["mag"] < 6 else 92}" text-anchor="middle" fill="#f2f4f6" font-size="11" font-family="Inter, sans-serif">M{q["mag"]:.1f} {E(q["place"].split(", ")[-1])}</text>'
tl += f'<line x1="{X1}" y1="26" x2="{X1}" y2="152" stroke="#8fdcff" stroke-width="2"></line><text x="{X1-6}" y="36" text-anchor="end" fill="#8fdcff" font-size="11" font-weight="600" font-family="Inter, sans-serif">NOW 10:01</text>'
tl += f'<text x="12" y="66" fill="{MUT}" font-size="12" font-family="Inter, sans-serif">Clashes, protests</text><text x="12" y="122" fill="{MUT}" font-size="12" font-family="Inter, sans-serif">Quakes M4.5+</text>'
tl += f'<rect x="{X0}" y="44" width="{tx(CAP - 3.75*3600) - X0:.0f}" height="36" fill="none" stroke="rgba(255,255,255,0.2)" stroke-dasharray="4 5"></rect><text x="{X0+10}" y="66" fill="{MUT}" font-size="11" font-family="Inter, sans-serif">no event files loaded before 06:15 yet (16 of 96 files of the window)</text>'
strip = panel(24, 868, 1872, 188, f'<svg width="1560" height="170" viewBox="0 0 1570 170" role="img" aria-label="The last 24 hours: clashes and protests at the time of their newest report, earthquakes at their time" style="position: absolute; left: 14px; top: 10px">{tl}</svg>'
    + f'<div style="position: absolute; left: 1610px; top: 14px; width: 248px; display: flex; flex-direction: column; gap: 3px"><div style="{SG}; font-weight: 600; font-size: 15px">Next</div>' + ''.join(f'<div style="font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><span style="color: #c8b8ff">{d}</span> · {n.split(" · ")[0]}</div>' for d, n, g in LAUNCH) + note('Marks stand at the time of the newest report. Numbers of outlets set the size.') + '</div>', "Last 24 hours", extra='position: absolute;')
body = markers('horizon_mono', hide) + topbar('Horizon · mono') + strip + picker('horizon', 24, 84, True) + groundpill(196, 84, 'mono') + legend(196, 140, ['mil', 'clash', 'protest', 'ship', 'quake', 'outage', 'name'])
page('EyeMono.dc.html', 'Eye, mono', 'horizon_mono', body, 'The Earth with the horizon across the upper part, without colour')

# ===== 12 Over the pole =====
hide = [(1476, 84, 420, 846), (187, 950, 1546, 130)]
u = inview('polar', 'unrest', hide); l = inview('polar', 'leaders', hide); m = inview('polar', 'mil', hide); sh = inview('polar', 'ships', hide)
seg = ''.join(f'<span style="flex: 1; text-align: center; padding: 9px 0; border-radius: 999px; font-size: 13px; {"background: #f2f4f6; color: #0a0e12; font-weight: 600" if n == "Signals" else "color: " + MUT}">{n}</span>' for n in ['Signals', 'Layers', 'Coming up'])
rp = panel(1476, 84, 420, 846, f'<div role="tablist" style="display: flex; padding: 4px; border-radius: 999px; background: rgba(255,255,255,0.07)">{seg}</div>'
    + '<div style="display: flex; gap: 8px">' + big("Aircraft", str(len(m)), "military, in view") + big("Places", str(len(u)), "clash or protest") + big("Leaders", str(len(l)), "placed here") + '</div>'
    + hd("Clashes and protests", "GDELT, not verified") + row([("Place", ""), ("Coded as", ""), ("Out", R), ("Age", R)], (88, None, 26, 56), True, 18) + '<div>' + unrest_rows(u[:10], (88, None, 26, 56)) + '</div>'
    + rule() + hd("Leaders placed here", "outlets, last 6 h") + '<div>' + leader_rows(l[:9]) + '</div>'
    + note('One panel with three tabs instead of two columns: the globe keeps the left two thirds of the screen.'), "Signals in this view", gap=8, pad=16)
body = markers('polar', hide) + topbar('Over the pole') + rp + picker('polar', 187, 950, full=True) + campill(24, 84, f'Looking straight down from {km(2.4*6371)} km above 74° N 30° E') + legend(24, 132, ['mil', 'clash', 'protest', 'ship', 'quake', 'launch', 'outage', 'name'], 330)
page('EyePolar.dc.html', 'Eye, over the pole', 'polar', body, 'The Earth seen from above the Arctic: Europe at the bottom, Russia to the right, North America to the upper left')

# ===== 13 Low orbit =====
hide = [(24, 896, 1872, 160), (187, 138, 1546, 118)]
u = inview('low', 'unrest', hide); l = inview('low', 'leaders', hide); m = inview('low', 'mil', hide)
def cell(t, inner, w): return f'<div style="width: {w}px; flex: none; box-sizing: border-box; padding: 0 18px; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; gap: 3px"><div style="font-size: 12px; color: {MUT}">{t}</div>{inner}</div>'
lt = panel(24, 896, 1872, 160, '<div style="display: flex; height: 100%">'
    + cell('Camera', f'<div style="{SG}; font-weight: 600; font-size: 22px">420 km up</div><div style="font-size: 13px">above 33.5° N 27° E, looking east</div><div style="font-size: 12px; color: {MUT}">the height of the space station</div>', 300).replace('border-left: 1px solid rgba(255,255,255,0.1); ', '')
    + cell('Clashes in this view', ''.join(f'<div style="font-size: 13px; white-space: nowrap"><b style="{SG}">{E(i["place"])}</b> · {i["outlets"]} outlets · {age(i["last"])} · <span style="color: {MUT}">{E(i["action"])}</span></div>' for i in u[:4]) or '<div>none</div>', 560)
    + cell('Leaders placed here', ''.join(f'<div style="font-size: 13px; white-space: nowrap"><b style="{SG}">{E(i["name"])}</b> · {E(i["place"])} · {i["outlets"]} outlets</div>' for i in l[:4]) or '<div>none</div>', 400)
    + cell('Military aircraft', f'<div style="{SG}; font-weight: 600; font-size: 22px">{len(m)} in view</div><div style="font-size: 12px; color: {MUT}">of 120 airborne · adsb.fi · 12 s</div>', 240)
    + cell('Not verified', f'<div style="font-size: 12px; color: {MUT}; line-height: 1.4">Clashes are GDELT\'s machine coding of news reports. A leader\'s place is where the news put them.</div>', 300) + '</div>', "In this view", pad=16)
body = markers('low', hide) + topbar('Low orbit: the Levant') + lt + picker('low', 187, 138, full=True) + groundpill(24, 84, 'photo')
page('EyeLow.dc.html', 'Eye, low orbit', 'low', body, 'The eastern Mediterranean from 420 km up, looking east over Cyprus to the Levant, the horizon near the top')

# ===== 14 Chase =====
cam = V['chase']['cams'][0][0]
ax, ay, _ = cam.proj(AC['lon'], AC['lat'], AC['alt_km']/6371); gx, gy, _ = cam.proj(AC['lon'], AC['lat'])
hx, hy, _ = cam.proj(*__import__('views').dest(AC['lon'], AC['lat'], AC['hdg'], 30), AC['alt_km']/6371)
ang = math.degrees(math.atan2(hx - ax, -(hy - ay)))
hide = [(1404, 84, 492, 846), (187, 950, 1546, 130), (ax - 14, ay - 14, 28, 28), (gx - 12, gy - 12, 24, 24)]
plane = (f'<svg width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true" style="position: absolute; left: 0; top: 0"><line x1="{ax:.1f}" y1="{ay:.1f}" x2="{gx:.1f}" y2="{gy:.1f}" stroke="#ffffff" stroke-opacity="0.7" stroke-dasharray="3 4"></line><circle cx="{gx:.1f}" cy="{gy:.1f}" r="3" fill="#ffffff"></circle>'
         f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="26" fill="none" stroke="#8fdcff" stroke-width="1.6"></circle><path d="M0 -6 L4 5 L0 2.6 L-4 5 Z" fill="#ffffff" transform="translate({ax:.1f} {ay:.1f}) rotate({ang:.0f}) scale(2.4)"></path>'
         f'<text x="{ax+34:.0f}" y="{ay+5:.0f}" fill="#ffffff" font-family="Space Grotesk, sans-serif" font-size="16" font-weight="600" stroke="#000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">GAF633</text></svg>')
sheet = panel(1404, 84, 492, 846,
    f'<div style="font-size: 12px; color: #8fdcff; font-weight: 500">Military aircraft · following</div><div style="{SG}; font-weight: 700; font-size: 40px; line-height: 1.05; letter-spacing: -0.01em">GAF633</div><div style="color: {MUT}">Type code GL5T · registration 14+04 · Germany, from its address block · 3F7B3C</div>'
    + '<div style="display: flex; gap: 8px">' + big("Altitude", "41,025 ft", "12.5 km") + big("Ground speed", "513 kt", "950 km/h") + big("Heading", "110°", "east-south-east") + '</div>'
    + '<div style="display: flex; gap: 8px">' + big("Last report", "12 s", "before the capture") + big("Position", "39.30° N 35.54° E", "central Turkey") + '</div>'
    + '<div style="display: flex; gap: 8px">' + act("Stop following") + act("From above") + act("Details") + '</div>'
    + rule() + hd("Camera", "") + '<div>' + ''.join(row([(a, M), (b, B + "; " + R)], [130, None], False, 27) for a, b in [("Behind it", "520 km"), ("Height", "260 km"), ("Turn", "follows its heading"), ("Drag", "orbits around it")]) + '</div>'
    + rule() + note('adsb.fi military feed. No published route: military aircraft do not file public ones. Drawn 40 s behind real time, between real reports.')
    + f'<div style="margin-top: auto; font-size: 12px; color: {MUT}">The dashed line drops to the point on the ground beneath it. Ground here is about 500 m per pixel; the sharp photo layer would replace it.</div>', "Aircraft being followed", gap=10, pad=18)
bar = f'<div aria-label="Follow controls" style="position: absolute; left: 24px; top: 84px; height: 48px; box-sizing: border-box; padding: 0 8px; border-radius: 999px; {G}; display: flex; align-items: center; gap: 4px; {SG}; font-weight: 500; font-size: 14px">' + ''.join(f'<span style="padding: 9px 13px; border-radius: 999px; {"background: #f2f4f6; color: #0a0e12" if n == "Behind it" else ""}">{n}</span>' for n in ['↺', '↻', 'N', 'Behind it', 'Stop']) + '</div>'
body = markers('chase', hide, kinds=('mil', 'unrest', 'leaders', 'outages')) + plane + topbar('Chase: GAF633') + sheet + bar + picker('chase', 187, 950, full=True)
page('EyeChase.dc.html', 'Eye, chase', 'chase', body, 'Central Turkey seen from behind and above a followed aircraft, the horizon near the top')

# ===== 15 Flat map =====
hide = []
cols = ''
for n, (t, sub, rws) in enumerate(REG):
    cols += panel(24 + n*471, 818, 459, 188, hd(t, sub) + '<div>' + ''.join(row([(a, B), (b, "color: #e6eaed"), (c, R + "; font-size: 12px; " + ("color: #ffe066" if 'late' in c else M))], [84, None, 74], False, 26) for a, b, c in rws) + '</div>', t, pad=12, gap=3)
body = markers('flat', hide) + topbar('Flat map · mono') + cols + legend(28, 1022, ['mil', 'clash', 'protest', 'ship', 'quake', 'launch', 'outage', 'name'], 1100) + groundpill(1420, 1014, 'mono')
page('EyeFlat.dc.html', 'Eye, flat map', 'flat', body, 'The whole world unrolled as a flat map without colour')
