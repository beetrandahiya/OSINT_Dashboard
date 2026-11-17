import sys, io, contextlib, json, math, html
sys.argv = ['x', 'c1b03a33e5c17fad9269b2ef0f3a7f96']
with contextlib.redirect_stdout(io.StringIO()):
    from gen_icons2 import *        # page2, title, J, IT, FR, V, NEAR, acls, uncls, age, E, MUT, SG
import scifi as S
from cam import Cam
IMGS = dict(theatre='40a16fae57632686edefd4f7dbe2a139', near='d6a5f287a535b4a9bd26f59853ccd099', whole='a648821de07caec2fc85cb87737d37d8', nearfull='e21da2bc43f671b83667e82f41973a21')
FONTS = '&family=Barlow+Condensed:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500'
def pg(name, ttl, body, img=None, alt=''):
    pic = f'<img src="/_blob/{IMGS[img]}" alt="{alt}" style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px">' if img else ''
    page2(name, ttl, pic + body)
    s = open(OUT + name).read().replace('&display=swap', FONTS + '&display=swap', 1).replace(I.DEFS, J.DEFS2 + S.DEFS, 1)
    open(OUT + name, 'w').write(s); print(name, len(s))
SVG = lambda inner, w=1920, h=1080, x=0, y=0, label='': f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}" style="position: absolute; left: {x}px; top: {y}px">{inner}</svg>'
HEAD = lambda t, sub: (S.txt(28, 40, 'WORLD WATCH', 22, '#ffffff', wt=700, ls='0.18em') + S.txt(232, 40, t.upper(), 16, S.ICE, wt=600, ls='0.14em')
                       + S.txt(28, 60, sub, 13, '#9fb3bf', wt=500, ls='0.05em'))
B = []
# ===== 1 research notes =====
obs = [
 ('Cold, graded picture', 'The camera picture is pushed to steel blue-grey, darker and low in colour, so the overlay reads on top.', 'grade'),
 ('Layered glass panels', 'Thin rectangles, partly see-through, stacked over each other; bright corner brackets mark the frame.', 'frame'),
 ('Small geometric markers', 'Points on the city map are tiny: plus signs, dots in rings, small triangles and pictograms, each with a caps label.', 'markers'),
 ('Red lock on the target', 'The tracked target gets a thin red mark; everything else stays cool.', 'lock'),
 ('Condensed caps and micro text', 'Labels are condensed capitals with wide spacing; behind them, columns of tiny text add density.', 'type'),
 ('Segmented bars', 'Progress is a row of small blocks, not a smooth bar.', 'segments'),
 ('Leader lines', 'Thin lines run from a point on the picture to a label block off to the side.', 'callout'),
 ('Glitch only in transitions', 'Pixel blocks and colour fringing appear when something changes, not while it rests.', 'glitch'),
]
def diag(kind, x, y):
    if kind == 'grade': return f'<rect x="{x}" y="{y}" width="120" height="70" fill="#5a6b52"></rect><rect x="{x+130}" y="{y}" width="120" height="70" fill="#27343b"></rect>' + S.txt(x+125, y+42, '→', 18, S.ICE, anchor='middle')
    if kind == 'frame': return S.frame(x, y, 150, 70) + S.frame(x+60, y+20, 150, 60).replace('fill-opacity="0.72"', 'fill-opacity="0.4"')
    if kind == 'markers': return ''.join([f'<path d="M{x+20} {y+35}h14M{x+27} {y+28}v14" stroke="{S.ICE}" stroke-width="1.2"></path>', f'<circle cx="{x+70}" cy="{y+35}" r="7" fill="none" stroke="{S.ROSE}" stroke-width="1.2"></circle><circle cx="{x+70}" cy="{y+35}" r="2" fill="{S.ROSE}"></circle>',
                                         f'<path d="M{x+110} {y+29}l6 11h-12Z" fill="{S.ICE}"></path>', S.txt(x+20, y+62, 'SECURITY CAM', 10, '#9fb3bf', ls='0.1em')])
    if kind == 'lock': return S.lock(x+60, y+38, 22)
    if kind == 'type': return S.txt(x, y+24, 'PRIMARY SIGNAL', 20, '#ffffff', wt=600, ls='0.12em') + ''.join(S.txt(x, y+40+k*9, '0x3F7B3C 41025 513 110 39.30 35.54 adsb.fi', 8, '#6f8794', font=S.MONO) for k in range(4))
    if kind == 'segments': return S.segments(x, y+20, 7, 12, S.ROSE) + S.txt(x, y+56, '7 OUTLETS', 12, S.ROSE, wt=600, ls='0.12em')
    if kind == 'callout': return S.callout(x+20, y+60, [('RCH4992', 15, '#ffffff', 600), ('C-17 · FL306', 11, '#9fb3bf', 500)], dx=50, dy=-30)
    if kind == 'glitch': return ''.join(f'<rect x="{x + (k*13) % 150}" y="{y + (k*7) % 60}" width="{10 + k % 3*6}" height="6" fill="{["#ff3b5c", "#8fdcff", "#ffffff"][k % 3]}" fill-opacity="0.5"></rect>' for k in range(14))
    return ''
cards = ''
for n, (t, d, kind) in enumerate(obs):
    x = 28 + (n % 4)*470; y = 150 + (n//4)*300
    cards += S.frame(x, y, 450, 280, f'{n+1:02d}  {t}') + diag(kind, x + 24, y + 50)
    words = d.split(); lines = []; cur = ''
    for w in words:
        if len(cur) + len(w) > 58: lines.append(cur); cur = w
        else: cur = (cur + ' ' + w).strip()
    lines.append(cur)
    cards += ''.join(S.txt(x + 24, y + 170 + k*20, l, 15, '#c9d6de', wt=400, ls='0.02em') for k, l in enumerate(lines))
quotes = (S.frame(28, 760, 930, 290, 'What the designers said', 'Cantina Creative, 2015')
  + ''.join(S.txt(52, 820 + k*34, q, 17, '#e6eef2', wt=400, ls='0.02em') for k, q in enumerate([
    '"organised but not neat": processing shown as rapid and messy, not pretty',
    '"it\'s all about the layering of transparencies"',
    '"beautifully dense by nature to help visually exaggerate the story"',
    '"most of the time that means pushing back on all the beautiful complexity"',
    'Studio: Cantina Creative, with director James Wan (graphics supervisor Alan Torres).']))
  + S.txt(52, 1000, 'Read from cantinacreative.com, hudsandguis.com and pushing-pixels.org; stills studied, not reproduced here.', 13, '#9fb3bf', wt=400))
take = (S.frame(990, 760, 902, 290, 'What we take, what we leave')
  + ''.join(S.txt(1014, 820 + k*30, s, 16, c, wt=500) for k, (s, c) in enumerate([
    ('TAKE: graded cold ground, glass panels, hairlines, corner brackets', S.ICE), ('TAKE: small precise markers, a red lock only on the selection', S.ICE),
    ('TAKE: condensed caps labels, leader lines, segmented counts of real numbers', S.ICE),
    ('LEAVE: orange labels (you ruled orange out)', '#ff8fa3'), ('LEAVE: invented percentages, fake IDs and code columns: every number must be real', '#ff8fa3'),
    ('LEAVE: face recognition and person tracking: not something this tool does', '#ff8fa3'), ('LEAVE: glitch on markers (markers never move)', '#ff8fa3')])))
pg('SciResearch.dc.html', 'God\'s Eye research', SVG(HEAD('What the film\'s God\'s Eye screens do', 'notes from the designers\' own pages and stills of Furious 7, 2015') + cards + quotes + take, label='Research notes'))
B.append(('SciResearch.dc.html', 'Research: what the film\'s screens do, what we take and leave'))

# ===== 2 why cartoony, four treatments =====
SY = ['narrow', 'wide', 'heli_med', 'fighter', 'tanker', 'awacs', 'hale', 'container', 'carrier', 'sat_img', 'sat_spy', 'clash', 'aerial', 'protest', 'quake_m', 'airbase', 'nuke', 'out_power']
ct = HEAD('Less cartoon, more instrument', 'the same silhouettes in four treatments, palettes A and C, on the graded ground')
for b_, pal in enumerate('AC'):
    bx = 28 + b_*946
    ct += S.txt(bx, 104, f'PALETTE {pal}', 15, S.ICE, wt=600, ls='0.16em')
    for c, st in enumerate(S.STYLES):
        cx = bx + 150 + c*196
        ct += S.txt(cx + 90, 104, ['TODAY', 'HOLOGRAM', 'ETCHED', 'HAIRLINE'][c], 13, '#ffffff', wt=600, ls='0.14em', anchor='middle')
    for r_, i in enumerate(SY):
        y = 120 + r_*50
        ct += S.txt(bx, y + 30, J.LIB[i]['name'].split('(')[0].split(',')[0][:22], 13, '#c9d6de', wt=500)
        for c, st in enumerate(S.STYLES):
            cx = bx + 150 + c*196
            ct += f'<rect x="{cx}" y="{y+2}" width="180" height="46" fill="#000" fill-opacity="0.25" stroke="#8fdcff" stroke-opacity="0.08"></rect>'
            ct += S.draw(i, st, cx + 40, y + 25, 22, 0, pal) + S.draw(i, st, cx + 118, y + 25, 38, 0, pal)
why = (S.txt(28, 1050, 'Why today\'s set reads as cartoon: a thick dark outline, flat saturated fills and rounded joins, the language of game icons. The film\'s marks are thin, see-through and lit from the edge.', 14, '#9fb3bf', wt=400))
pg('SciTreat.dc.html', 'Four treatments', SVG(ct + why, label='Four icon treatments') , 'theatre', 'Graded Europe')
B.append(('SciTreat.dc.html', 'Less cartoon: four treatments of the same silhouettes, A and C'))

# ===== 3 components =====
cp = HEAD('Building blocks', 'selection lock, callouts, segmented counts, panels, ground and type')
cp += S.frame(28, 90, 600, 470, 'Selection', 'one hairline ring: rose when selected')
cp += S.draw('strategic', 'holo', 180, 260, 44, 35, 'A', colkey='mil') + S.lock(180, 260, 34)
cp += S.draw('clash', 'holo', 440, 260, 34, 0, 'A') + S.lock(440, 260, 30)
cp += S.draw('carrier', 'holo', 180, 450, 36, 20, 'A') + S.lock(180, 450, 30, S.ICE)
cp += S.txt(110, 330, 'AIRCRAFT, SELECTED', 12, '#9fb3bf', ls='0.12em') + S.txt(380, 330, 'EVENT, SELECTED', 12, '#9fb3bf', ls='0.12em') + S.txt(110, 515, 'HOVER: SAME RING IN ICE BLUE', 12, '#9fb3bf', ls='0.12em')
cp += S.frame(660, 90, 600, 470, 'Callouts', 'real values only')
cp += S.draw('strategic', 'holo', 720, 280, 30, 50, 'A', colkey='mil') + S.callout(720, 280, [('RCH4992', 20, '#ffffff', 600), ('C-17 · STRATEGIC AIRLIFTER', 13, '#9fb3bf', 500), ('FL306 · 535 KT · 063°', 13, S.ICE, 500)], dx=70, dy=-60)
cp += S.draw('clash', 'holo', 740, 470, 26, 0, 'A') + S.callout(740, 470, [('KYIV · ARMED CLASH', 18, '#ffffff', 600), ('GDELT · NOT VERIFIED · 1 MIN', 12, '#9fb3bf', 500)], dx=70, dy=-40, col=S.ROSE) + S.segments(816, 448, 7, 12, S.ROSE)
cp += S.frame(1292, 90, 600, 470, 'Counts', 'blocks = real numbers')
for k, (lab, n, tot, col) in enumerate([('OUTLETS REPORTING KYIV', 7, 12, S.ROSE), ('FEEDS CURRENT', 40, 45, S.ICE), ('MILITARY AIRCRAFT IN THE NEAR VIEW', 10, 12, '#ffffff'), ('US CARRIERS (USNI, 22 D OLD)', 8, 12, '#ffe066')]):
    y = 150 + k*96
    cp += S.txt(1316, y, lab, 13, '#9fb3bf', ls='0.12em')
    cp += S.segments(1316, y + 12, n if tot <= 12 else round(n/45*24), 12 if tot <= 12 else 24, col, w=14 if tot <= 12 else 7, h=14)
    cp += S.txt(1868, y + 25, f'{n}' + (f' / {tot}' if tot > 12 else ''), 18, '#ffffff', anchor='end', font=S.MONO)
cp += S.frame(28, 590, 900, 460, 'Ground', 'raw photo, graded, graded with dot grid and scan lines')
for k, (lab, img, extra) in enumerate([('RAW', 'theatre_raw', ''), ('GRADED', 'theatre', ''), ('+ GRID, SCAN', 'theatre', 'grid')]):
    x = 52 + k*292
    cp += f'<image href="/_blob/{IMG["theatre"] if img == "theatre_raw" else IMGS["theatre"]}" x="{x - 400}" y="{640 - 380}" width="1920" height="1080" clip-path="url(#c{k})"></image>'
    cp += f'<clipPath id="c{k}"><rect x="{x}" y="640" width="276" height="370"></rect></clipPath>'
    if extra: cp += f'<rect x="{x}" y="640" width="276" height="370" fill="url(#dots)"></rect><rect x="{x}" y="640" width="276" height="370" fill="url(#scan)"></rect>'
    cp += S.txt(x + 10, 1030, lab, 13, '#ffffff', ls='0.14em')
cp += S.frame(960, 590, 932, 460, 'Type', 'Barlow Condensed and IBM Plex Mono, both free')
cp += S.txt(984, 680, 'SECONDARY SIGNAL · KYIV', 40, '#ffffff', wt=600, ls='0.1em') + S.txt(984, 720, 'Labels: condensed capitals, wide spacing, two weights', 18, '#c9d6de', wt=400)
cp += S.txt(984, 780, '50.43 N  30.52 E   FL410   513 KT   12 S', 26, S.ICE, font=S.MONO) + S.txt(984, 812, 'Numbers: monospaced, so columns line up and digits do not jump', 18, '#c9d6de', wt=400)
cp += S.txt(984, 880, 'Body text stays in a normal sans (Inter) for anything longer than a line.', 18, '#c9d6de', wt=400, font="Inter, sans-serif", ls='0')
pg('SciParts.dc.html', 'Building blocks', SVG(cp, label='Selection, callouts, counts, ground, type'))
B.append(('SciParts.dc.html', 'Building blocks: lock, callouts, segmented counts, ground, type'))

# ===== 4 near, full screen =====
NF = Cam(NEAR.C.tolist() and json.load(open('near_centre.json'))[0], json.load(open('near_centre.json'))[1], 0.1, *json.load(open('near_centre.json')), 1300, 960, 540)
def heading(proj, a):
    x, y, _ = proj(a['lon'], a['lat']); x2, y2, _ = proj(a['lon'] + 0.2*math.sin((a['track'] or 0)*r)/max(0.2, math.cos(a['lat']*r)), a['lat'] + 0.2*math.cos((a['track'] or 0)*r))
    return math.degrees(math.atan2(x2 - x, -(y2 - y)))
def fl(a): return ('FL%03d' % round(a['alt']/100)) if isinstance(a['alt'], (int, float)) else 'GROUND'
def scene(proj, pal, style, sel_flight=None, rect=(0, 0, 1920, 1080), hide=(), labels=True, events=True):
    out = []; x0, y0, w, h = rect; sel = None
    def ok(x, y): return 0 <= x - x0 <= w and 0 <= y - y0 <= h and not any(inr(x, y, hr, -2) for hr in hide)
    mil = []
    for a in IT['mil']:
        x, y, vis = proj(a['lon'], a['lat'])
        if vis and ok(x, y): mil.append((a, x - x0, y - y0))
    for a, x, y in mil:
        cls = acls(a); ck = 'mil' if J.LIB[cls]['colkey'] == 'civil' else None
        out.append(S.draw(cls, style, x, y, 30 if labels else 18, heading(proj, a), pal, colkey=ck))
        if a['flight'] == sel_flight: sel = (a, x, y, cls)
        elif labels: out.append(S.txt(x + 18, y + 4, a['flight'], 12, '#d7e6ee', wt=600, ls='0.08em', op=0.85))
    if events:
        for u in IT['unrest']:
            x, y, vis = proj(u['lon'], u['lat'])
            if vis and ok(x, y):
                X, Y = x - x0, y - y0
                out.append(S.draw(uncls(u), style, X, Y, 26, 0, pal))
                out.append(S.txt(X - 16, Y - 16, f"{u['place'].upper()}", 13, '#ffffff', wt=600, ls='0.1em', anchor='end') + S.segments(X - 16 - min(u['outlets'], 12)*7, Y - 10, min(u['outlets'], 12), None, S.ROSE, 5, 7, 2))
        for c in FR['changes'][-8:]:
            x, y, vis = proj(c['lon'], c['lat'])
            if vis and ok(x, y): out.append(S.draw('frontchange', style, x - x0, y - y0, 14, 0, pal))
        for l in IT['leaders']:
            x, y, vis = proj(l['lon'], l['lat'])
            if vis and ok(x, y): out.append(S.draw('leader', style, x - x0, y - y0, 18, 0, pal) + S.txt(x - x0 + 14, y - y0 + 22, l['name'].upper(), 12, '#d7e6ee', wt=500, ls='0.08em'))
    return ''.join(out), sel, len(mil)
items, sel, nmil = scene(NF.proj, 'A', 'holo', 'RCH4992', hide=[(1460, 90, 432, 960), (28, 90, 400, 620)])
a, sx, sy, cls = sel
items += S.lock(sx, sy, 34) + S.callout(sx, sy, [(a['flight'], 22, '#ffffff', 600), (J.LIB[cls]['name'].upper(), 13, '#9fb3bf', 500), (f"{fl(a)} · {round(a['gs'] or 0)} KT · {round(a['track'] or 0):03d}°", 14, S.ICE, 500)], dx=90, dy=-80)
inview = [(b, acls(b)) for b in IT['mil'] if (lambda p: p[2] and 0 < p[0] < 1920 and 0 < p[1] < 1080)(NF.proj(b['lon'], b['lat']))]
side = S.frame(1460, 90, 432, 960, 'Selected', 'adsb.fi · military feed')
side += S.txt(1484, 170, a['flight'], 48, '#ffffff', wt=700, ls='0.06em') + S.txt(1484, 198, J.LIB[cls]['name'].upper(), 15, '#9fb3bf', ls='0.12em')
side += S.txt(1484, 222, f"TYPE {a.get('type') or '?'} · REG {a.get('reg') or '?'} · {a['hex'].upper()}", 14, S.ICE, font=S.MONO)
for k, (lab, val) in enumerate([('ALTITUDE', fl(a)), ('GROUND SPEED', f"{round(a['gs'] or 0)} KT"), ('TRACK', f"{round(a['track'] or 0):03d}°"), ('POSITION', f"{a['lat']:.2f} N {a['lon']:.2f} E"), ('LAST REPORT', f"{round(a.get('seen') or 0)} S")]):
    y = 270 + k*70
    side += S.txt(1484, y, lab, 12, '#9fb3bf', ls='0.14em') + S.txt(1484, y + 30, val, 26, '#ffffff', font=S.MONO) + f'<path d="M1484 {y+44}H1868" stroke="#8fdcff" stroke-opacity="0.15"></path>'
side += S.txt(1484, 660, 'NO PUBLISHED ROUTE (MILITARY)', 13, '#9fb3bf', ls='0.12em') + S.txt(1484, 684, 'DRAWN 40 S BEHIND REAL TIME', 13, '#9fb3bf', ls='0.12em')
for k, t in enumerate(['FOLLOW', 'FROM ABOVE', 'DETAILS']):
    side += f'<rect x="{1484 + k*130}" y="720" width="120" height="40" fill="none" stroke="#8fdcff" stroke-opacity="0.6"></rect>' + S.txt(1544 + k*130, 745, t, 14, S.ICE, wt=600, ls='0.14em', anchor='middle')
left = S.frame(28, 90, 400, 620, 'In view', f'{len(inview)} military aircraft')
for k, (b, c) in enumerate(sorted(inview, key=lambda t: t[0]['flight'])[:16]):
    y = 150 + k*34
    left += S.draw(c, 'holo', 52, y - 4, 18, 0, 'A', colkey='mil' if J.LIB[c]['colkey'] == 'civil' else None) + S.txt(72, y, b['flight'], 14, '#ffffff' if b['flight'] != 'RCH4992' else S.ROSE, wt=600, ls='0.06em') + S.txt(170, y, J.LIB[c]['name'].split(',')[0].split('(')[0].upper()[:20], 12, '#9fb3bf', ls='0.06em') + S.txt(404, y, fl(b), 13, S.ICE, font=S.MONO, anchor='end')
over = '<rect width="1920" height="1080" fill="url(#dots)"></rect><rect width="1920" height="1080" fill="url(#scan)"></rect>'
hdr = HEAD('Near: northern Germany', 'hologram treatment · palette A · real military aircraft from the capture')
pg('SciNear.dc.html', 'Near, hologram', SVG(over + items + side + left + hdr, label='Military aircraft over northern Germany, hologram treatment'), 'nearfull', 'Northern Germany from 640 km, graded')
B.append(('SciNear.dc.html', 'Near view, hologram, palette A, one aircraft locked'))

# ===== 5/6 theatre =====
cth = V['theatre']['cams'][0][0]
for pal in 'AC':
    hide = [(1460, 90, 432, 960), (28, 820, 1400, 230)]
    it, _, n = scene(cth.proj, pal, 'holo', None, hide=hide, labels=False)
    u = [x for x in IT['unrest'] if (lambda p: p[2] and 0 < p[0] < 1460 and 90 < p[1] < 820)(cth.proj(x['lon'], x['lat']))]
    sig = S.frame(1460, 90, 432, 960, 'Signals in view', 'GDELT · machine-coded, not verified')
    for k, x in enumerate(sorted(u, key=lambda x: -x['outlets'])[:10]):
        y = 150 + k*62
        sig += S.draw(uncls(x), 'holo', 1494, y + 4, 24, 0, pal) + S.txt(1520, y, x['place'].upper(), 17, '#ffffff', wt=600, ls='0.08em') + S.txt(1868, y, age(x['last']).upper(), 13, '#9fb3bf', font=S.MONO, anchor='end')
        sig += S.txt(1520, y + 20, (x['action'] or '').upper()[:34], 12, '#9fb3bf', ls='0.06em') + S.segments(1520, y + 28, min(x['outlets'], 12), 12, S.ROSE if pal == 'A' else '#f06a7e', 9, 8, 2)
    sig += S.txt(1484, 790, 'FRONT LINE, UKRAINE', 13, '#9fb3bf', ls='0.14em') + S.txt(1484, 826, '116,892 KM²', 32, '#ffffff', font=S.MONO) + S.txt(1484, 852, '+27 KM² SINCE 8 NOV · DEEPSTATE · 1 D 14 H', 12, S.ICE, ls='0.08em')
    bot = S.frame(28, 820, 1400, 230, 'Layers', '40 of 45 feeds current · 1 late · 1 failing · 3 not set up')
    for k, (i, lab, cnt, src) in enumerate([('mil_generic', 'MILITARY AIRCRAFT', '120', 'ADSB.FI · 12 S'), ('clash', 'CLASHES, PROTESTS', '14', 'GDELT · 1 MIN'), ('leader', 'LEADERS', '17', 'GDELT · 57 MIN'), ('frontchange', 'FRONT CHANGES', '8', 'DEEPSTATE'), ('carrier', 'US CARRIERS', '8', 'USNI · 22 D LATE'), ('quake_m', 'QUAKES 24 H', '168', 'USGS · 1 MIN'), ('out_power', 'OUTAGES', '5', 'IODA · 22 S')]):
        x = 52 + k*196
        bot += S.draw(i, 'holo', x + 16, 892, 30, 0, pal, colkey='mil' if i == 'mil_generic' else None) + S.txt(x + 40, 884, lab, 12, '#9fb3bf', ls='0.1em') + S.txt(x + 40, 912, cnt, 26, '#ffffff', font=S.MONO) + S.txt(x, 960, src, 11, '#ffe066' if 'LATE' in src else S.ICE, ls='0.08em')
    hdr = HEAD('Theatre: Europe and the Black Sea', f'hologram treatment · palette {pal} · real items from the capture')
    nm = f'SciTheatre{pal}.dc.html'
    pg(nm, f'Theatre {pal}', SVG(over + it + sig + bot + hdr, label=f'Theatre view, palette {pal}'), 'theatre', 'Europe and the Black Sea, graded')
    B.append((nm, f'Theatre, hologram, palette {pal}'))
# ===== 7/8 all symbols =====
ids = list(J.LIB)
for pal in 'AC':
    g = HEAD(f'All {len(ids)} symbols, hologram', f'palette {pal} · 34 px · on the graded dark ground')
    cols = 14
    for n, i in enumerate(ids):
        x = 60 + (n % cols)*132; y = 112 + (n//cols)*86
        g += S.draw(i, 'holo', x + 30, y + 24, 34, 0, pal) + S.txt(x + 30, y + 64, J.LIB[i]['name'].split('(')[0].split(',')[0][:18].upper(), 9, '#9fb3bf', ls='0.06em', anchor='middle')
    nm = f'SciAll{pal}.dc.html'
    pg(nm, f'All symbols {pal}', SVG('<rect width="1920" height="1080" fill="#05090d"></rect><rect width="1920" height="1080" fill="url(#dots)"></rect>' + g, label=f'All symbols, palette {pal}'))
    B.append((nm, f'All {len(ids)} symbols in hologram, palette {pal}'))
json.dump(B, open('sciboards.json', 'w')); print(len(B))
