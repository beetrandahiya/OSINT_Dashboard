"""All layout candidates for the God's eye look, same capture, same view, solid icons, palette C, graded photo."""
import sys, io, contextlib, json, math, html
sys.argv = ['x', 'c1b03a33e5c17fad9269b2ef0f3a7f96']
with contextlib.redirect_stdout(io.StringIO()):
    from gen_icons2 import *
import scifi as S
from gen_scifi import pg, SVG, HEAD, scene, fl, IMGS
PAL = 'C'; ST = 'solid'
cth = V['theatre']['cams'][0][0]
ICE, ROSE, MUTE, WH, YEL = S.ICE, '#f06a7e', '#9fb3bf', '#ffffff', '#ffe066'
T = S.txt; F = S.frame
OVER = '<rect width="1920" height="1080" fill="url(#dots)"></rect><rect width="1920" height="1080" fill="url(#scan)"></rect>'
def P(lo, la): return cth.proj(lo, la)
def onmap(hide, labels=False): return scene(cth.proj, PAL, ST, None, hide=hide, labels=labels)[0]
def line(x1, y1, x2, op=0.15): return f'<path d="M{x1} {y1}H{x2}" stroke="{ICE}" stroke-opacity="{op}"></path>'
def box(x, y, w, h, op=0.6, col=ICE, fill='none'): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{col}" stroke-opacity="{op}"></rect>'
def btn(x, y, w, t, on=False): return box(x, y, w, 30, 0.9 if on else 0.35, ICE, '#8fdcff22' if on else 'none') + T(x + w/2, y + 20, t, 12, ICE if on else MUTE, wt=600, ls='0.14em', anchor='middle')
UN = sorted(IT['unrest'], key=lambda x: -x['outlets'])
LAYERS = [('mil_generic', 'MILITARY AIRCRAFT', '120', 'ADSB.FI', '12 S', 'mil'), ('clash', 'CLASHES, PROTESTS', '14', 'GDELT', '1 MIN', None),
          ('leader', 'LEADERS', '17', 'GDELT', '57 MIN', None), ('frontchange', 'FRONT CHANGES', '8', 'DEEPSTATE', '1 D', None),
          ('carrier', 'US CARRIERS', '8', 'USNI', '22 D LATE', None), ('quake_m', 'QUAKES 24 H', '168', 'USGS', '1 MIN', None),
          ('out_power', 'OUTAGES', '5', 'IODA', '22 S', None), ('launch', 'LAUNCHES 5 D', '4', 'LL2', '4 MIN', None)]
VIEWS = ['WHOLE EARTH', 'THEATRE', 'DAY / NIGHT', 'TWO SIDES', 'WALL OF FOUR', 'LOOK DOWN', 'OVER THE POLE', 'LOW ORBIT', 'CHASE', 'FLAT']
FEEDS = '40 OF 45 FEEDS CURRENT · 1 LATE · 1 FAILING · 3 NOT SET UP'
def ico(i, x, y, px=22, ck=None): return S.draw(i, ST, x, y, px, 0, PAL, colkey=ck)
def sig_rows(x, y, w, n=8, gap=58, big=True):
    s = ''
    for k, u in enumerate(UN[:n]):
        yy = y + k*gap
        s += ico(uncls(u), x + 12, yy - 5, 22) + T(x + 32, yy, u['place'].upper(), 16 if big else 14, WH, wt=600, ls='0.08em') + T(x + w, yy, age(u['last']).upper(), 12, MUTE, font=S.MONO, anchor='end')
        s += T(x + 32, yy + 18, (u['action'] or u['cat']).upper()[:40], 11, MUTE, ls='0.06em')
        if big: s += S.segments(x + 32, yy + 25, min(u['outlets'], 12), 12, ROSE, 8, 7, 2) + T(x + 32 + 12*10 + 6, yy + 32, f"{u['outlets']} OUTLETS", 10, MUTE, font=S.MONO)
    return s
def layer_tiles(x, y, cols, w=180, h=78, n=8):
    s = ''
    for k, (i, lab, cnt, src, ag, ck) in enumerate(LAYERS[:n]):
        X = x + (k % cols)*(w + 8); Y = y + (k//cols)*(h + 8)
        s += box(X, Y, w, h, 0.18, ICE, '#04090e99') + ico(i, X + 20, Y + 24, 24, ck) + T(X + 40, Y + 22, lab, 11, MUTE, ls='0.1em')
        s += T(X + 40, Y + 50, cnt, 24, WH, font=S.MONO) + T(X + 12, Y + 70, f'{src} · {ag}', 10, YEL if 'LATE' in ag else ICE, ls='0.08em')
    return s
def layer_rows(x, y, w, n=8, gap=34):
    s = ''
    for k, (i, lab, cnt, src, ag, ck) in enumerate(LAYERS[:n]):
        yy = y + k*gap
        s += f'<circle cx="{x+6}" cy="{yy-4}" r="3" fill="{YEL if "LATE" in ag else "#5fe39a"}"></circle>' + ico(i, x + 26, yy - 5, 18, ck) + T(x + 44, yy, lab, 13, WH, ls='0.08em') + T(x + w - 80, yy, cnt, 14, WH, font=S.MONO, anchor='end') + T(x + w, yy, ag, 11, YEL if 'LATE' in ag else MUTE, font=S.MONO, anchor='end')
    return s
def views_bar(x, y, active='THEATRE', w=None, n=10):
    s = ''; cx = x
    for v in VIEWS[:n]:
        ww = len(v)*8 + 26
        s += btn(cx, y, ww, v, v == active); cx += ww + 6
    return s
def thumbs(x, y, n=7, w=150, h=84):
    s = ''
    keys = ['whole', 'theatre', 'dusk', 'sides', 'wall', 'front', 'polar']
    for k in range(n):
        X = x + k*(w + 10)
        s += f'<clipPath id="th{k}{x}{y}"><rect x="{X}" y="{y}" width="{w}" height="{h}"></rect></clipPath><image href="/_blob/{IMG[keys[k]] if keys[k] in IMG else NEW.get(keys[k], "")}" x="{X}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#th{k}{x}{y})" opacity="0.8"></image>'
        s += box(X, y, w, h, 0.9 if keys[k] == 'theatre' else 0.25) + T(X + 8, y + h - 8, VIEWS[k], 10, WH, wt=600, ls='0.12em')
    return s
def top(title, sub, right=True):
    s = '<rect width="1920" height="64" fill="#02050a" fill-opacity="0.55"></rect>' + T(28, 40, 'WORLD WATCH', 22, WH, wt=700, ls='0.18em') + T(232, 40, title.upper(), 15, ICE, wt=600, ls='0.14em')
    s += T(232, 56, sub, 11, MUTE, ls='0.06em')
    if right: s += T(1892, 30, '17 NOV 2026 · 10:01 UTC', 14, WH, font=S.MONO, anchor='end') + T(1892, 50, FEEDS, 10, MUTE, ls='0.08em', anchor='end')
    return s
def card_clash(x, y, w, h):
    u = [v for v in IT['unrest'] if v['place'] == 'Kyiv'] or UN; u = u[0]
    s = F(x, y, w, h, 'Selected', 'GDELT · machine-coded, not verified')
    s += T(x + 24, y + 80, u['place'].upper(), 40, WH, wt=700, ls='0.06em') + T(x + 24, y + 104, (u['action'] or '').upper(), 13, MUTE, ls='0.1em')
    for k, (lab, val) in enumerate([('OUTLETS', str(u['outlets'])), ('LAST REPORT', age(u['last']).upper()), ('COUNTRY', u['country'])]):
        X = x + 24 + k*((w - 48)//3)
        s += T(X, y + 150, lab, 11, MUTE, ls='0.14em') + T(X, y + 178, val, 24, WH, font=S.MONO)
    s += S.segments(x + 24, y + 200, min(u['outlets'], 12), 12, ROSE, 12, 10, 3)
    bw = (w - 48 - 16)//3
    for k, t in enumerate(['SPY PASSES', 'IMAGED FROM ORBIT', 'COUNTRY DOSSIER']): s += btn(x + 24 + k*(bw + 8), y + 232, bw, t)
    s += T(x + 24, y + 296, 'REPORTS', 12, ICE, wt=600, ls='0.14em') + line(x + 24, y + 304, x + w - 24, 0.25)
    s += T(x + 24, y + 328, 'HEADLINES ARE SHOWN FOR EACH OUTLET THAT CODED THIS EVENT', 11, MUTE, ls='0.06em')
    return s, P(u['lon'], u['lat'])
def lockat(lo, la, r=22):
    x, y, v = P(lo, la); return S.lock(x, y, r) if v else ''
def kyiv(): u = [v for v in IT['unrest'] if v['place'] == 'Kyiv'][0]; return u['lon'], u['lat']
B = []
def board(nm, ttl, desc, body):
    pg(nm, ttl, SVG(OVER + body, label=ttl), 'theatre', 'Europe and the Black Sea, graded photo'); B.append((nm, desc))

# 1 Dense right column
hide = [(1400, 64, 520, 1016), (0, 960, 1400, 120)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 1 · Dense column', 'everything on the right, the map free on the left')
s += F(1416, 84, 488, 520, 'Signals in view', 'GDELT · not verified') + sig_rows(1432, 140, 456, 8)
s += F(1416, 620, 488, 440, 'Layers', '8 of 40 shown') + layer_tiles(1432, 660, 2, 232, 80, 8)
s += '<rect x="0" y="964" width="1400" height="116" fill="#02050a" fill-opacity="0.6"></rect>' + thumbs(20, 980, 7, 180, 84)
board('L1Dense.dc.html', 'Layout 1: Dense column', 'Dense column: signals and layer tiles on the right, view pictures below', s)

# 2 Dock and sheet
hide = [(0, 660, 1920, 420)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 2 · Dock and sheet', 'full-screen Earth; a sheet rises from the dock for the selected item')
cs, _ = card_clash(560, 660, 800, 340); s += cs
s += F(80, 1014, 1760, 54, '', '') + views_bar(100, 1026, 'THEATRE')
s += T(1820, 1046, 'LAYERS  ·  SEARCH  ·  SETTINGS', 12, ICE, wt=600, ls='0.14em', anchor='end')
board('L2Dock.dc.html', 'Layout 2: Dock and sheet', 'Dock and sheet: one bar at the bottom, a sheet rises for the selection', s)

# 3 Theatre with bottom cards
hide = [(0, 780, 1920, 300), (1500, 64, 420, 300)]
s = onmap(hide) + top('Layout 3 · Cards along the bottom', 'five cards list what is in the view and follow the camera')
cards = [('MILITARY AIRCRAFT', 'mil_generic', '51 IN VIEW', 'ADSB.FI · 12 S'), ('CLASHES, PROTESTS', 'clash', '6 IN VIEW', 'GDELT · 1 MIN'), ('LEADERS', 'leader', '5 IN VIEW', 'GDELT · 57 MIN'), ('FRONT, UKRAINE', 'frontchange', '116,892 KM²', 'DEEPSTATE · 1 D'), ('OUTAGES', 'out_power', '1 IN VIEW', 'IODA · 22 S')]
for k, (lab, i, big, src) in enumerate(cards):
    x = 28 + k*376
    s += F(x, 796, 360, 264, lab, src) + ico(i, x + 34, 860, 34, 'mil' if i == 'mil_generic' else None) + T(x + 66, 870, big, 26, WH, font=S.MONO)
    if i == 'clash': s += sig_rows(x + 16, 920, 328, 2, 56, False)
    elif i == 'mil_generic':
        for j, a in enumerate(sorted([m for m in IT['mil'] if (lambda p: p[2] and 0 < p[0] < 1500 and 64 < p[1] < 780)(P(m['lon'], m['lat']))], key=lambda m: -(m['alt'] if isinstance(m['alt'], (int, float)) else 0))[:4]):
            s += T(x + 16, 920 + j*30, a['flight'], 14, WH, wt=600, ls='0.06em') + T(x + 344, 920 + j*30, fl(a), 13, ICE, font=S.MONO, anchor='end')
    elif i == 'leader':
        for j, l in enumerate([l for l in IT['leaders'] if (lambda p: p[2] and 0 < p[0] < 1920 and 0 < p[1] < 780)(P(l['lon'], l['lat']))][:4]):
            s += T(x + 16, 920 + j*30, l['name'].upper(), 13, WH, ls='0.06em') + T(x + 344, 920 + j*30, l['place'].upper()[:14], 11, MUTE, anchor='end')
    elif i == 'frontchange':
        s += T(x + 16, 920, '+27 KM² SINCE 8 NOV', 14, ICE, ls='0.08em') + T(x + 16, 948, '8 CHANGES IN 7 DAYS', 13, MUTE, ls='0.08em')
    else:
        o = IT['outages'][0]; s += T(x + 16, 920, o['where'].upper(), 14, WH, ls='0.06em') + T(x + 16, 948, f"SIGNAL {o['signal'].upper()} · {age(o['start']).upper()}", 12, MUTE, ls='0.08em')
s += F(1516, 84, 376, 260, 'Camera', 'theatre') + ''.join(T(1540, 140 + k*44, a, 11, MUTE, ls='0.14em') + T(1868, 140 + k*44, b, 18, WH, font=S.MONO, anchor='end') for k, (a, b) in enumerate([('POSITION', '41.5 N 18.0 E'), ('HEIGHT', '2,100 KM'), ('LOOKING', 'NE · 034°'), ('TILT', '58°'), ('IN VIEW', '68 ITEMS')]))
board('L3Cards.dc.html', 'Layout 3: Cards along the bottom', 'Cards along the bottom: what is in the view, by layer, plus a camera panel', s)

# 4 One panel with tabs
hide = [(1480, 64, 440, 1016)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 4 · One panel, tabs', 'one right panel: Signals / Layers / Coming up / Selected')
s += F(1496, 84, 408, 976, '', '')
for k, t in enumerate(['SIGNALS', 'LAYERS', 'COMING UP', 'SELECTED']): s += btn(1512 + k*98, 100, 92, t, k == 0)
s += sig_rows(1516, 172, 368, 13, 64)
s += views_bar(28, 1030, 'THEATRE')
board('L4Tabs.dc.html', 'Layout 4: One panel, tabs', 'One panel with tabs on the right, views along the bottom', s)

# 5 Two sides (list left, card right)
hide = [(0, 64, 440, 1016), (1500, 64, 420, 1016)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 5 · List left, card right', 'like today: one list of everything on the left, the selected item on the right')
s += F(16, 84, 408, 980, 'Now', 'signals, coming up, latest')
for k, t in enumerate(['SIGNALS', 'COMING UP', 'LATEST']): s += btn(32 + k*128, 120, 120, t, k == 0)
s += sig_rows(36, 196, 368, 6, 62) + T(32, 590, 'COMING UP', 12, ICE, wt=600, ls='0.14em') + line(32, 598, 408, 0.25)
for k, l in enumerate(IT['launches'][:4]): s += ico('launch', 46, 624 + k*46, 20) + T(66, 628 + k*46, l['name'].split('|')[0].strip().upper(), 13, WH, ls='0.06em') + T(408, 628 + k*46, l['net'][5:16].replace('T', ' '), 11, MUTE, font=S.MONO, anchor='end') + T(66, 646 + k*46, l['site'].split(',')[0].upper()[:40], 10, MUTE, ls='0.06em')
s += T(32, 830, 'LAYERS', 12, ICE, wt=600, ls='0.14em') + line(32, 838, 408, 0.25) + layer_rows(36, 866, 368, 6, 32)
cs, _ = card_clash(1512, 84, 392, 380); s += cs
board('L5Sides.dc.html', 'Layout 5: List left, card right', 'List on the left, card on the right: today\'s layout in the new look', s)

# 6 Ring and timeline
s = ''
R = 470; cx, cy = 960, 470
mask = f'<mask id="ring"><rect width="1920" height="1080" fill="#fff"></rect><circle cx="{cx}" cy="{cy}" r="{R}" fill="#000"></circle></mask><rect width="1920" height="1080" fill="#02050a" fill-opacity="0.72" mask="url(#ring)"></rect>'
s += onmap([(0, 0, 1920, 1080)][:0]) if False else ''
def inring(x, y): return (x - cx)**2 + (y - cy)**2 < (R - 10)**2
hide = [(0, 64, 96, 1016), (0, 880, 1920, 200)]
items = onmap(hide)
s += items + mask + f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{ICE}" stroke-opacity="0.5"></circle>' + lockat(*kyiv())
for a in range(0, 360, 10):
    c, sn = math.cos(math.radians(a)), math.sin(math.radians(a)); l = 12 if a % 30 == 0 else 6
    s += f'<path d="M{cx + R*c:.1f} {cy + R*sn:.1f}L{cx + (R + l)*c:.1f} {cy + (R + l)*sn:.1f}" stroke="{ICE}" stroke-opacity="0.5"></path>'
s += top('Layout 6 · Scope and timeline', 'the view inside a ring, a rail of views, a timeline of the last 24 h and next 5 days')
s += '<rect x="0" y="64" width="96" height="816" fill="#02050a" fill-opacity="0.7"></rect>'
for k, v in enumerate(VIEWS[:9]): s += box(14, 84 + k*84, 68, 68, 0.9 if v == 'THEATRE' else 0.25) + T(48, 84 + k*84 + 62, v.split()[0][:7], 9, WH if v == 'THEATRE' else MUTE, ls='0.1em', anchor='middle')
s += F(1460, 84, 440, 780, 'Signals', 'GDELT · not verified') + sig_rows(1476, 140, 404, 11, 64)
s += F(16, 890, 1888, 176, 'Timeline', 'past 24 h · next 5 days compressed')
x0, x1, xn = 140, 1300, 1880
s += f'<path d="M{x1} 920V1050" stroke="{ICE}"></path>' + T(x1, 1062, 'NOW', 11, ICE, wt=600, anchor='middle', ls='0.14em')
for k, lab in enumerate(['UNREST', 'QUAKES', 'LAUNCHES']):
    y = 950 + k*34; s += T(32, y + 4, lab, 11, MUTE, ls='0.14em') + line(x0, y, xn, 0.12)
for u in IT['unrest']: t = (u['last'] - (CAP - 86400))/86400; s += ico(uncls(u), x0 + t*(x1 - x0), 950, 14) if 0 <= t <= 1 else ''
for q in IT['quakes']: t = (q['time'] - (CAP - 86400))/86400; s += f'<circle cx="{x0 + t*(x1 - x0):.0f}" cy="984" r="{q["mag"]*1.3:.1f}" fill="none" stroke="{WH}"></circle>' if 0 <= t <= 1 else ''
import datetime as dt
for l in IT['launches']:
    t = (dt.datetime.fromisoformat(l['net'].replace('Z', '+00:00')).timestamp() - CAP)/(5*86400)
    if 0 <= t <= 1: s += ico('launch', x1 + t*(xn - x1), 1018, 16)
board('L6Scope.dc.html', 'Layout 6: Scope and timeline', 'Scope and timeline: the view inside a ring, view rail on the left, timeline below', s)

# 7 Briefing and globe
hide = [(0, 64, 760, 1016)]
s = onmap(hide) + top('Layout 7 · Briefing and globe', 'a written briefing by region on the left, each line tied to its source')
s += '<rect x="0" y="64" width="760" height="1016" fill="#02050a" fill-opacity="0.82"></rect>'
y = 120
regions = {}
for u in UN: regions.setdefault(u['country'], []).append(u)
for c, us in list(regions.items())[:6]:
    s += T(40, y, c, 13, ICE, wt=600, ls='0.16em') + line(80, y - 4, 720, 0.2); y += 30
    for u in us[:3]:
        s += T(40, y, f"{u['place']}: {(u['action'] or u['cat'])}", 17, WH, font="Inter, sans-serif", wt=500, ls='0') + T(720, y, f"{u['outlets']} outlets · {age(u['last'])}", 12, MUTE, font=S.MONO, anchor='end'); y += 26
    y += 14
s += T(40, y + 10, 'FRONT, UKRAINE', 13, ICE, wt=600, ls='0.16em') + line(150, y + 6, 720, 0.2) + T(40, y + 40, 'DeepState: 116,892 km² held, +27 km² since 8 Nov; 8 changes in 7 days.', 17, WH, font="Inter, sans-serif", ls='0')
s += T(40, 1050, 'EVERY LINE IS A COUNT OR A CODED EVENT FROM A NAMED FEED; NOTHING IS SUMMARISED BY A MODEL', 11, MUTE, ls='0.08em')
s += F(780, 1000, 1120, 64, '', '') + views_bar(800, 1017, 'THEATRE', n=7)
board('L7Brief.dc.html', 'Layout 7: Briefing and globe', 'Briefing and globe: a written briefing on the left, the Earth on the right', s)

# 8 Corners HUD
hide = [(16, 80, 420, 330), (1484, 80, 420, 330), (16, 780, 520, 284), (1384, 780, 520, 284)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 8 · Four corners', 'four small panels in the corners, the middle of the screen stays free')
s += F(16, 84, 420, 326, 'Signals', 'top 4') + sig_rows(32, 140, 388, 4, 66)
s += F(1484, 84, 420, 326, 'Selected', 'Kyiv') + T(1508, 160, 'KYIV', 36, WH, wt=700, ls='0.06em') + T(1508, 186, 'USE OF CONVENTIONAL MILITARY FORCE', 12, MUTE, ls='0.1em') + S.segments(1508, 206, 8, 12, ROSE, 12, 10, 3) + btn(1508, 250, 180, 'OPEN CARD', True) + btn(1696, 250, 184, 'SPY PASSES')
s += F(16, 784, 520, 280, 'Layers', FEEDS[:22].lower()) + layer_rows(32, 830, 488, 7, 32)
s += F(1384, 784, 520, 280, 'Views', '') + ''.join(btn(1400 + (k % 3)*164, 830 + (k//3)*42, 156, v, v == 'THEATRE') for k, v in enumerate(VIEWS[:9]))
board('L8Corners.dc.html', 'Layout 8: Four corners', 'Four corners: small panels in each corner, the centre stays free', s)

# 9 Lower third
hide = [(0, 860, 1920, 220)]
s = onmap(hide) + lockat(*kyiv()) + top('Layout 9 · Lower third', 'one band across the bottom, like a news channel; nothing else on the map')
s += '<rect x="0" y="864" width="1920" height="216" fill="#02050a" fill-opacity="0.78"></rect>' + f'<path d="M0 864H1920" stroke="{ICE}" stroke-opacity="0.6"></path>'
s += T(28, 900, 'SIGNALS', 12, ICE, wt=600, ls='0.16em') + sig_rows(28, 930, 560, 3, 46, False)
s += f'<path d="M620 880V1064M1260 880V1064" stroke="{ICE}" stroke-opacity="0.2"></path>' + T(648, 900, 'LAYERS', 12, ICE, wt=600, ls='0.16em') + layer_tiles(648, 914, 3, 194, 70, 6)
s += T(1288, 900, 'SELECTED · KYIV', 12, ICE, wt=600, ls='0.16em') + T(1288, 950, 'KYIV', 38, WH, wt=700, ls='0.06em') + T(1288, 976, 'USE OF CONVENTIONAL MILITARY FORCE · 8 OUTLETS', 12, MUTE, ls='0.1em') + views_bar(1288, 1012, 'THEATRE', n=4)
board('L9Lower.dc.html', 'Layout 9: Lower third', 'Lower third: one band across the bottom', s)

# 10 Ambient
hide = [(0, 820, 1920, 260), (1500, 64, 420, 200)]
s = onmap(hide) + top('Layout 10 · Ambient', 'big numbers only, for a screen left running; click anything to open the full layout', right=False)
for k, (i, lab, cnt, src, ag, ck) in enumerate(LAYERS[:6]):
    x = 40 + k*310
    s += ico(i, x + 20, 870, 34, ck) + T(x + 50, 884, cnt, 56, WH, font=S.MONO, wt=400) + T(x, 930, lab, 13, MUTE, ls='0.14em') + T(x, 952, f'{src} · {ag}', 11, YEL if 'LATE' in ag else ICE, ls='0.08em')
s += T(1892, 120, '10:01', 64, WH, font=S.MONO, anchor='end', wt=400) + T(1892, 150, 'UTC · 17 NOV 2026', 13, MUTE, ls='0.14em', anchor='end') + T(1892, 180, FEEDS, 10, MUTE, ls='0.08em', anchor='end')
board('L10Ambient.dc.html', 'Layout 10: Ambient', 'Ambient: big numbers only, nothing to read closely', s)

# fonts
PAIRS = [("Barlow Condensed", "IBM Plex Mono"), ("Rajdhani", "Share Tech Mono"), ("Saira Semi Condensed", "JetBrains Mono"), ("Chakra Petch", "Space Mono")]
s = top('Fonts · four pairs', 'labels in the first font, numbers in the second; all free (Google Fonts, OFL)', right=False)
for k, (a, b) in enumerate(PAIRS):
    X = 28 + (k % 2)*946; Y = 90 + (k//2)*490
    f1 = f"'{a}', sans-serif"; f2 = f"'{b}', monospace"
    s += F(X, Y, 918, 470, f'{a} + {b}', 'option ' + 'ABCD'[k])
    s += T(X + 24, Y + 90, 'KYIV · ARMED CLASH', 44, WH, font=f1, wt=600, ls='0.08em') + T(X + 24, Y + 120, 'USE OF CONVENTIONAL MILITARY FORCE · GDELT · NOT VERIFIED', 15, MUTE, font=f1, ls='0.1em')
    s += T(X + 24, Y + 190, 'RCH4992   FL306   535 KT   063°', 34, ICE, font=f2) + T(X + 24, Y + 230, '50.43 N  30.52 E   116,892 KM²   12 S', 22, WH, font=f2)
    s += T(X + 24, Y + 290, 'SIGNALS IN VIEW', 14, ICE, font=f1, wt=600, ls='0.16em') + line(X + 24, Y + 298, X + 894, 0.25)
    for j, u in enumerate(UN[:3]): s += T(X + 24, Y + 330 + j*36, u['place'].upper(), 18, WH, font=f1, wt=600, ls='0.08em') + T(X + 260, Y + 330 + j*36, (u['action'] or '').upper()[:36], 13, MUTE, font=f1, ls='0.06em') + T(X + 894, Y + 330 + j*36, f"{u['outlets']:>2} · {age(u['last'])}", 15, ICE, font=f2, anchor='end')
    s += T(X + 24, Y + 450, 'Body text in Inter: a full sentence reads like this, for anything longer than a line.', 15, '#c9d6de', font="Inter, sans-serif", ls='0')
FX = '&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=Saira+Semi+Condensed:wght@500;600;700&family=JetBrains+Mono&family=Chakra+Petch:wght@500;600;700&family=Space+Mono'
pg('Fonts.dc.html', 'Fonts: four pairs', SVG('<rect width="1920" height="1080" fill="#05090d"></rect>' + OVER + s, label='Four font pairs'))
p = OUT + 'Fonts.dc.html'; t = open(p).read(); open(p, 'w').write(t.replace('&display=swap', FX + '&display=swap', 1))
B.append(('Fonts.dc.html', 'Fonts: four free pairs on the same real content'))
json.dump(B, open('layboards.json', 'w')); print(len(B))
