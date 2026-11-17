import math, html, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from gen_eye import *          # helpers, cameras, items (regenerates the eye boards quietly)
import icons as I
SW = '904da8a744526ca0047cf6e50306e932'
GR = ['Photo, land', 'Photo, desert', 'Mono', 'Dark']
def page2(name, title, body, img=None, alt=''):
    pic = f'<img src="/_blob/{IMG[img]}" alt="{alt}" style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px">' if img else ''
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap">
<style>
body{{margin:0}}
a{{color:#ffffff}}a:hover{{color:#8fdcff}}
</style>
</helmet>
<div style="position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #05080c; color: #f2f4f6; font-family: Inter, system-ui, sans-serif; font-size: 13px; line-height: 1.4">
{I.DEFS}{pic}
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
    open(OUT + name, 'w').write(doc); print(name, len(doc))
def title(t, sub):
    return (f'<div style="position: absolute; left: 28px; top: 14px"><div style="display: flex; align-items: baseline; gap: 12px"><span style="{SG}; font-weight: 700; font-size: 22px">World Watch</span>'
            f'<span style="{SG}; font-weight: 500; font-size: 15px; color: #8fdcff">{t}</span></div><div style="color: {MUT}; font-size: 12px">{sub}</div></div>')
FAMTXT = dict(solid='Filled silhouettes with a dark edge. Closest to today\'s icons; reads at a glance, heaviest on a busy map.',
              line='Thin outlines with a soft glow. The projected-display feel of look 6; lightest, but weaker on bright desert.',
              badge='The symbol knocked out of a coloured disc. Most legible on any ground; takes the most room, so it suits sparse layers.',
              point='A plain shape plus one or two letters. Densest and fastest to draw; for thousands of items or a zoomed-out view.')
def sheet(name, group, ttl):
    ids = [k for k, v in I.S.items() if v['group'] in group]
    n = len(ids); rh = min(58, (960 - 40)//n); px = rh - 16
    x0, y0 = 24, 124
    fw = 4*(rh + 2) + 26
    head = f'<div style="position: absolute; left: {x0}px; top: {y0-44}px; width: 300px; font-size: 12px; color: {MUT}">Symbol · colour</div>'
    for f, fam in enumerate(I.FAM):
        fx = x0 + 300 + f*fw
        head += (f'<div style="position: absolute; left: {fx}px; top: {y0-50}px; width: {fw-26}px"><div style="{SG}; font-weight: 600; font-size: 15px">{I.FAMN[fam]}</div>'
                 f'<div style="display: flex; gap: 2px; font-size: 10px; color: {MUT}">' + ''.join(f'<span style="width: {rh}px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis">{g.split(",")[-1].strip()}</span>' for g in GR) + '</div></div>')
    rows = ''
    for r, i in enumerate(ids):
        s = I.S[i]; y = y0 + r*rh
        rows += (f'<div style="position: absolute; left: {x0}px; top: {y}px; width: 290px; height: {rh-2}px; display: flex; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.07)">'
                 f'<span style="width: 12px; height: 12px; border-radius: 3px; flex: none; background: {s["col"]}"></span><span style="font-size: {13 if rh > 44 else 12}px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(s["name"])}</span></div>')
        for f, fam in enumerate(I.FAM):
            fx = x0 + 300 + f*fw
            for g in range(4):
                rows += (f'<div style="position: absolute; left: {fx + g*(rh+2)}px; top: {y}px; width: {rh}px; height: {rh-2}px; border-radius: 6px; background: url(/_blob/{SW}) {-g*rh}px 0 / {4*rh}px {rh-2}px; display: grid; place-items: center">'
                         f'{I.cell(i, fam, px, rot=0)}</div>')
    pal = {}
    for i in ids: pal.setdefault(I.S[i]['col'], []).append(I.S[i]['name'])
    sx = x0 + 300 + 4*fw + 20
    side = panel(sx, 76, 1896 - sx, 980, hd("The four families", "every symbol drawn four ways", 17)
        + ''.join(f'<div style="display: flex; gap: 12px; align-items: flex-start"><div style="display: flex; gap: 4px; flex: none">{I.cell(ids[0], fam, 30)}{I.cell(ids[min(3, n-1)], fam, 30)}</div><div><div style="{SG}; font-weight: 600; font-size: 14px">{I.FAMN[fam]}</div>{note(FAMTXT[fam])}</div></div>' for fam in I.FAM)
        + rule() + hd("Colours on this sheet", "")
        + '<div>' + ''.join(row([(f'<span style="display: inline-block; width: 26px; height: 14px; border-radius: 4px; background: {c}; vertical-align: middle"></span>', ""), (c, M + "; font-size: 12px"), (E(", ".join(v)), "")], [30, 66, None], False, 26) for c, v in pal.items()) + '</div>'
        + note('No orange or amber. Rose red means conflict and danger, yellow means a warning notice, aqua is the sea, ice blue marks the selection and system notes. Shape carries the meaning too, so nothing depends on colour alone.')
        + f'<div style="margin-top: auto">{note("Each symbol is shown on four grounds: the photo over land and over desert, the mono ground, and plain dark. Pick a family per layer if one does not suit all.")}</div>', "Families and colours", gap=10, pad=18)
    page2(name, ttl, title(ttl, f'{n} symbols · four families · four grounds') + head + rows + side)
sheet('IconsAir.dc.html', [I.A], 'Icons: air')
sheet('IconsSea.dc.html', [I.SE], 'Icons: sea and space')
sheet('IconsConflict.dc.html', [I.C, I.EA], 'Icons: conflict, news and Earth')
sheet('IconsNet.dc.html', [I.NW], 'Icons: networks, warnings and sites')

# ===== states =====
ST = [('airliner', 'DLH585', 28, 'outlets'), ('military', 'GAF633', 28, ''), ('carrier', 'Roosevelt', 28, ''), ('clash', 'Kyiv', 28, ''), ('protest', 'Manila', 28, ''),
      ('sat_leo', 'ISS (ZARYA)', 26, ''), ('quake', 'M6.6 Tual', 28, ''), ('outage', 'Serbia', 28, ''), ('leader', 'Narendra Modi', 26, '')]
COLS = [('Normal', ''), ('Hover', 'thin white ring'), ('Selected', 'ice ring and ticks'), ('Low confidence', 'one outlet, half strength'), ('Last known', 'feed stale: grey, dashed'),
        ('Grouped', 'count of a cluster'), ('With label', 'name beside it'), ('Sizes', 'scale by outlets or magnitude')]
def statecell(i, fam, ci, lab, px):
    s = I.S[i]; W_, H_ = 96, 74; cx, cy = W_/2, H_/2
    if ci == 0: g = I.sym(i, fam, cx, cy, px, 35)
    elif ci == 1: g = I.sym(i, fam, cx, cy, px, 35, 'hover')
    elif ci == 2: g = I.sym(i, fam, cx, cy, px, 35, 'sel')
    elif ci == 3: g = I.sym(i, fam, cx, cy, px, 35, 'faint')
    elif ci == 4: g = I.sym(i, fam, cx, cy, px, 35, 'stale') + f'<text x="{cx}" y="{H_-4}" text-anchor="middle" font-family="Inter" font-size="10" fill="#c9d1d6">last known</text>'
    elif ci == 5: g = (I.sym(i, fam, cx-12, cy+6, px*0.8, 35, 'faint') + I.sym(i, fam, cx-4, cy, px*0.8, 35, 'faint') +
                       f'<circle cx="{cx+10}" cy="{cy-6}" r="15" fill="{I.INK}" fill-opacity="0.75" stroke="{s["col"]}" stroke-width="2"></circle><text x="{cx+10}" y="{cy-1.5}" text-anchor="middle" font-family="Space Grotesk" font-weight="700" font-size="13" fill="#ffffff">12</text>')
    elif ci == 6: g = I.sym(i, fam, 20, cy, px*0.85, 35) + f'<text x="36" y="{cy+4}" font-family="Inter" font-weight="600" font-size="11" fill="#ffffff" stroke="#000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">{E(lab)}</text>'
    else: g = I.sym(i, fam, 16, cy, px*0.55, 35) + I.sym(i, fam, 40, cy, px*0.8, 35) + I.sym(i, fam, 72, cy, px*1.15, 35)
    return f'<svg width="{W_}" height="{H_}" viewBox="0 0 {W_} {H_}" aria-hidden="true" style="display: block">{g}</svg>'
blocks = ''
for b, fam in enumerate(['solid', 'badge']):
    bx = 24 + b*948
    blocks += f'<div style="position: absolute; left: {bx}px; top: 84px; {SG}; font-weight: 600; font-size: 16px">{I.FAMN[fam]}</div>'
    for c, (cn, cd) in enumerate(COLS):
        blocks += f'<div style="position: absolute; left: {bx + 120 + c*102}px; top: 112px; width: 98px"><div style="font-size: 12px; font-weight: 600">{cn}</div><div style="font-size: 10px; color: {MUT}; line-height: 1.25">{cd}</div></div>'
    for r, (i, lab, px, _) in enumerate(ST):
        y = 156 + r*96
        blocks += f'<div style="position: absolute; left: {bx}px; top: {y}px; width: 112px; height: 78px; display: flex; align-items: center; font-size: 12px; color: #e6eaed">{E(I.S[i]["name"])}</div>'
        for c in range(len(COLS)):
            blocks += (f'<div style="position: absolute; left: {bx + 120 + c*102}px; top: {y}px; width: 96px; height: 78px; border-radius: 10px; overflow: hidden; background: url(/_blob/{SW}) {-(c % 3)*96}px 0 / 384px 78px; display: grid; place-items: center">'
                       f'{statecell(i, fam, c, lab, px)}</div>')
foot = f'<div style="position: absolute; left: 24px; top: 1040px; width: 1870px; font-size: 12px; color: {MUT}">States are the same for every family: hover gets a thin white ring, the selection an ice ring with ticks (the old amber is gone), low confidence is drawn at half strength, a stale feed turns grey with a dashed ring and the words "last known". Markers never animate.</div>'
page2('IconStates.dc.html', 'Icon states', title('Icon states', 'normal, hover, selected, low confidence, last known, grouped, labelled, sized') + blocks + foot)

# ===== families on the map =====
TYPEMAP = {}
for t in 'H60 EC45 A119 UH1 H47 NH90 AS32 EC35 EC30 H64 EC55 AS65 LYNX S70 H160 EC75 A139 B412 MI8 MI17'.split(): TYPEMAP[t] = 'milheli'
for t in 'F16 F15 F18 F35 EUFI TOR GRIF RFAL M2K HAWK F22 MF17 SU27 SU30 MG29 T38 L39 M346'.split(): TYPEMAP[t] = 'fighter'
for t in 'K35R KC46 A332 B762 KC10 MRTT A310 IL78'.split(): TYPEMAP[t] = 'tanker'
def milsym(a): return TYPEMAP.get((a.get('type') or '').upper(), 'military')
def unsym(u): return {'protest': 'protest', 'attack': 'attack', 'riot': 'riot', 'mass': 'mass'}.get(u['cat'], 'clash')
def shipsym(s): return 'carrier' if s['hull'].startswith('CVN') else 'amphib'
def draw_items(view, fam, hide=(), dx=0, dy=0, sc=1.0, clip=None, names=True, scale=1.0):
    out = []; lab = []
    def ok(x, y): return clip is None or inr(x, y, clip)
    for i, x, y, cam in seen(view, 'mil', hide):
        if not ok(x, y): continue
        t = (i['track'] or 0)*r; x2, y2, _ = cam.proj(i['lon'] + 0.2*math.sin(t)/max(0.2, math.cos(i['lat']*r)), i['lat'] + 0.2*math.cos(t))
        out.append(I.sym(milsym(i), fam, (x-dx)*sc, (y-dy)*sc, 20*scale, math.degrees(math.atan2(x2 - x, -(y2 - y)))))
    for c in FR['changes'][-8:]:
        for cam, x0, y0, w, h in V[view]['cams']:
            x, y, vis = cam.proj(c['lon'], c['lat'])
            if vis and ok(x, y) and not any(inr(x, y, hr, -2) for hr in hide): out.append(I.sym('frontchange', fam, (x-dx)*sc, (y-dy)*sc, 14*scale))
    for kind, f in [('quakes', lambda i: ('quake', 18 + (i['mag'] - 4.5)*8)), ('launches', lambda i: ('launch', 22)), ('ships', lambda i: (shipsym(i), 24)), ('outages', lambda i: ('outage', 22)),
                    ('unrest', lambda i: (unsym(i), 16 + math.sqrt(i['outlets'])*5))]:
        for i, x, y, cam in seen(view, kind, hide):
            if not ok(x, y): continue
            s_, px = f(i); out.append(I.sym(s_, fam, (x-dx)*sc, (y-dy)*sc, px*scale))
    if names:
        for i, x, y, cam in seen(view, 'leaders', hide):
            if not ok(x, y): continue
            X, Y = (x-dx)*sc, (y-dy)*sc
            out.append(I.sym('leader', fam, X, Y, 16*scale))
            lab.append(f'<text x="{X+12:.1f}" y="{Y+4:.1f}" fill="#ffffff" font-family="Inter, sans-serif" font-size="12" font-weight="500" stroke="#000" stroke-opacity="0.6" stroke-width="3" paint-order="stroke">{E(i["name"])}</text>')
    return ''.join(out) + ''.join(lab)
QW, QH = 936, 476; QX = [24, 960]; QY = [80, 568]
ORG = (140, 190)
q = ''
for n, fam in enumerate(I.FAM):
    qx, qy = QX[n % 2], QY[n//2]
    items = draw_items('theatre', fam, clip=(ORG[0], ORG[1], QW, QH), dx=ORG[0], dy=ORG[1], scale=1.3, hide=[(ORG[0], ORG[1], 560, 70)])
    q += (f'<div style="position: absolute; left: {qx}px; top: {qy}px; width: {QW}px; height: {QH}px; overflow: hidden; border-radius: 18px; border: 1px solid rgba(255,255,255,0.16)">'
          f'<img src="/_blob/{IMG["theatre"]}" alt="" style="position: absolute; left: {-ORG[0]}px; top: {-ORG[1]}px; width: 1920px; height: 1080px">'
          f'<svg width="{QW}" height="{QH}" viewBox="0 0 {QW} {QH}" role="img" aria-label="Real items in this crop drawn as {I.FAMN[fam]} symbols" style="position: absolute; left: 0; top: 0">{items}</svg>'
          f'<div style="position: absolute; left: 14px; top: 12px; padding: 7px 14px; border-radius: 999px; {G}"><span style="{SG}; font-weight: 600; font-size: 15px">{I.FAMN[fam]}</span><span style="font-size: 12px; color: {MUT}"> · {FAMTXT[fam].split(";")[0].split(".")[0]}</span></div></div>')
page2('IconsOnMap.dc.html', 'Icons on the map', title('The four families on the map', 'the same crop of the theatre view, the same real items, drawn four ways') + q
      + f'<div style="position: absolute; left: 24px; top: 1050px; font-size: 12px; color: {MUT}">Military aircraft by broadcast type code (helicopters, fighters and tankers get their own shape), clashes and protests by GDELT kind, sized by outlets; front-line changes as squares; leaders where the news placed them.</div>')

# ===== legends A: whole Earth, solid =====
hideA = [(1452, 84, 444, 650), (24, 964, 1872, 92), (90, 150, 340, 250)]
mk = draw_items('whole', 'solid', hideA)
def cnt(view, kind, hide, pred=lambda i: True): return sum(1 for i, *_ in seen(view, kind, hide) if pred(i))
KEY = [('Air', [('military', 'Military aircraft', cnt('whole', 'mil', []), 'adsb.fi · 12 s'), ('milheli', 'Military helicopter', sum(1 for i, *_ in seen('whole', 'mil', []) if milsym(i) == 'milheli'), 'by type code'), ('tanker', 'Tanker', sum(1 for i, *_ in seen('whole', 'mil', []) if milsym(i) == 'tanker'), 'by type code')]),
       ('Conflict', [('clash', 'Armed clash', cnt('whole', 'unrest', [], lambda i: i['cat'] == 'clash'), 'GDELT · 1 min'), ('attack', 'Attack', cnt('whole', 'unrest', [], lambda i: i['cat'] == 'attack'), 'GDELT · 16 min'),
                     ('protest', 'Protest', cnt('whole', 'unrest', [], lambda i: i['cat'] == 'protest'), 'GDELT · 1 min'), ('frontchange', 'Front-line change', 8, 'DeepState · 1 d 14 h')]),
       ('News', [('leader', 'Leader placed by the news', cnt('whole', 'leaders', []), 'GDELT · 57 min')]),
       ('Sea', [('carrier', 'US carrier', cnt('whole', 'ships', [], lambda i: i['hull'].startswith('CVN')), 'USNI · 22 d, late'), ('amphib', 'US amphibious ship', cnt('whole', 'ships', [], lambda i: not i['hull'].startswith('CVN')), 'USNI · 22 d, late')]),
       ('Earth and space', [('quake', 'Earthquake M4.5+', cnt('whole', 'quakes', []), 'USGS · 1 min'), ('launch', 'Launch pad, next 4 days', cnt('whole', 'launches', []), 'LL2 · 43 s')]),
       ('Networks', [('outage', 'Internet outage', cnt('whole', 'outages', []), 'IODA · 22 s')])]
tagc = lambda t, x, y: f'<div style="position: absolute; left: {x}px; top: {y}px; padding: 4px 10px; border-radius: 999px; background: #8fdcff; color: #04202a; font: 700 12px Space Grotesk, sans-serif">{t}</div>'
keyA = ''
for gname, its in KEY:
    keyA += f'<div style="font-size: 11px; color: {MUT}; margin-top: 4px">{gname}</div>'
    for i, nm, c, src in its:
        keyA += row([(I.cell(i, 'solid', 22), "display: flex"), (nm, ""), (str(c), B + "; " + R), (src, M + "; font-size: 11px; " + R + ("; color: #ffe066" if "late" in src else ""))], [36, None, 30, 110], False, 34)
pA = panel(1452, 84, 444, 650, hd("Key", "what is drawn · how many in view · source", 16) + '<div>' + keyA + '</div>' + note('Counts are what falls on the visible side of the globe in this view.'), "Grouped key", gap=4)
strip = '<div style="display: flex; flex-wrap: wrap; gap: 4px 22px; align-items: center; align-content: center; height: 100%; padding: 0 18px">' + ''.join(f'<span style="display: flex; align-items: center; gap: 8px; white-space: nowrap">{I.cell(i, "solid", 22)}<span style="font-size: 13px">{nm.split(",")[0]}</span><b style="{SG}">{c}</b></span>' for _, its in KEY for i, nm, c, src in its if c) + '</div>'
pB = f'<section aria-label="Key strip" style="position: absolute; left: 24px; top: 964px; width: 1872px; height: 92px; box-sizing: border-box; border-radius: 22px; {G}; overflow: hidden">{strip}</section>'
kv = [ (x, y) for i, x, y, c in seen('whole', 'unrest', hideA) if i['place'] == 'Kyiv'][0]
kyiv = [i for i in IT['unrest'] if i['place'] == 'Kyiv'][0]
cardC = panel(90, 150, 340, 250, f'<div style="display: flex; gap: 12px; align-items: center">{I.cell("clash", "solid", 40)}<div><div style="{SG}; font-weight: 700; font-size: 18px">Armed clash · Kyiv</div><div style="font-size: 12px; color: {MUT}">what this mark says</div></div></div>'
    + '<div>' + ''.join(row([(a, M), (b, "color: #e6eaed")], [62, None], False, 26) for a, b in [("Shape", "burst = armed clash (GDELT 190)"), ("Size", f"{kyiv['outlets']} outlets reported it"), ("Colour", "rose = conflict, not verified"), ("Age", f"newest report {age(kyiv['last'])} ago")]) + '</div>'
    + note('Appears when the pointer rests on a mark for half a second.'), "Explain on hover", gap=6)
lineC = f'<svg width="1920" height="1080" viewBox="0 0 1920 1080" aria-hidden="true" style="position: absolute; left: 0; top: 0"><path d="M{kv[0]:.0f} {kv[1]:.0f} L430 270" stroke="#8fdcff" stroke-width="1.2"></path><circle cx="{kv[0]:.0f}" cy="{kv[1]:.0f}" r="16" fill="none" stroke="#ffffff" stroke-width="1.5"></circle></svg>'
page2('LegendsA.dc.html', 'Legends A', f'<svg width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-label="Real items on the whole Earth in solid symbols" style="position: absolute; left: 0; top: 0">{mk}</svg>' + lineC
      + title('Legend variants A, B, C', 'solid symbols on the whole-Earth view') + pA + pB + cardC + tagc('A  Grouped key', 1460, 60) + tagc('B  Key strip', 32, 940) + tagc('C  Explain on hover', 98, 126), 'whole', 'The whole Earth disc from geostationary distance')

# ===== legends B: theatre outline, line family =====
hideB = [(24, 84, 400, 972), (1600, 860, 296, 196)]
cam = V['theatre_outline']['cams'][0][0]
mkB = draw_items('theatre_outline', 'line', hideB)
LAY = [('Air', [('military', 'Military aircraft', True, cnt('theatre', 'mil', []), 'adsb.fi · 12 s'), ('airliner', 'All aircraft', False, None, 'off'), ('vip', 'VIP jets', False, None, 'off')]),
       ('Conflict', [('clash', 'Protests and clashes', True, cnt('theatre', 'unrest', []), 'GDELT · 1 min'), ('occupied', 'Front line, Ukraine', True, None, 'DeepState · 1 d 14 h'), ('navwarn', 'Navy warnings', False, None, 'off'), ('airspace', 'Airspace warnings', False, None, 'off')]),
       ('News', [('leader', 'Leaders today', True, cnt('theatre', 'leaders', []), 'GDELT · 57 min'), ('news', 'News places', False, None, 'off')]),
       ('Networks', [('outage', 'Internet outages', True, cnt('theatre', 'outages', []), 'IODA · 22 s'), ('hijack', 'Internet hijacks', False, None, 'no key')]),
       ('Sites', [('base', 'Military bases', False, None, 'off'), ('nuke', 'Nuclear sites', False, None, 'off')])]
def tog(on): return f'<span style="width: 34px; height: 20px; border-radius: 999px; flex: none; position: relative; background: {"#8fdcff" if on else "rgba(255,255,255,0.18)"}"><span style="position: absolute; top: 2px; left: {16 if on else 2}px; width: 16px; height: 16px; border-radius: 999px; background: #ffffff"></span></span>'
lay = ''
for gname, its in LAY:
    lay += f'<div style="font-size: 11px; color: {MUT}; margin-top: 6px">{gname}</div>'
    for i, nm, on, c, src in its:
        lay += (f'<div style="display: flex; align-items: center; gap: 10px; height: 36px; border-top: 1px solid rgba(255,255,255,0.08); {"" if on else "opacity: 0.6"}">{I.cell(i, "line", 22)}<span style="flex: 1; font-size: 13px">{nm}</span>'
                f'<span style="font-size: 11px; color: {"#ffe066" if "key" in src else MUT}">{src}</span><b style="{SG}; width: 28px; text-align: right">{"" if c is None else c}</b>{tog(on)}</div>')
        if i == 'clash':
            lay += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px 10px; padding: 4px 0 6px 32px">' + ''.join(f'<span style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #e6eaed">{I.cell(k, "line", 16)}{t}</span>' for k, t in [('clash', 'Armed clash'), ('attack', 'Attack'), ('riot', 'Riot'), ('protest', 'Protest'), ('mass', 'Mass violence'), ('frontchange', 'Front change')]) + '</div>' + note('Size = number of outlets. Machine-coded from news, not verified.')
pD = panel(24, 84, 400, 972, hd("Layers", "the key lives inside each layer", 16) + '<div>' + lay + '</div>', "Layers with their key", gap=4)
# E: counters of items beyond the screen edges, by direction
edge = {'top': {}, 'bottom': {}, 'left': {}, 'right': {}}; far = 0
for kind, sk in [('mil', 'military'), ('unrest', 'clash'), ('leaders', 'leader'), ('ships', 'carrier'), ('quakes', 'quake'), ('outages', 'outage'), ('launches', 'launch')]:
    for i in IT[kind]:
        x, y, vis = cam.proj(i['lon'], i['lat'])
        if not vis: far += 1; continue
        if 0 <= x <= 1920 and 0 <= y <= 1080: continue
        dx_, dy_ = x - 960, y - 540
        e = ('right' if dx_ > 0 else 'left') if abs(dx_)/960 > abs(dy_)/540 else ('bottom' if dy_ > 0 else 'top')
        edge[e][sk] = edge[e].get(sk, 0) + 1
def chips(d, vertical=False):
    return ''.join(f'<span style="display: flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; {G}; white-space: nowrap">{I.cell(k, "line", 16)}<b style="{SG}">{v}</b></span>' for k, v in sorted(d.items(), key=lambda kv: -kv[1]))
pE = (f'<div aria-label="Beyond the top edge" style="position: absolute; left: 1240px; top: 64px; display: flex; gap: 6px; align-items: center"><span style="font-size: 12px; color: {MUT}">▲ beyond this edge</span>{chips(edge["top"])}</div>'
      f'<div aria-label="Beyond the right edge" style="position: absolute; right: 24px; top: 380px; display: flex; flex-direction: column; gap: 6px; align-items: flex-end"><span style="font-size: 12px; color: {MUT}">beyond this edge ▶</span>{chips(edge["right"])}</div>'
      f'<div aria-label="Beyond the bottom edge" style="position: absolute; left: 700px; bottom: 20px; display: flex; gap: 6px; align-items: center"><span style="font-size: 12px; color: {MUT}">▼ beyond this edge</span>{chips(edge["bottom"])}</div>'
      + (f'<div aria-label="Beyond the left edge" style="position: absolute; left: 440px; top: 380px; display: flex; flex-direction: column; gap: 6px"><span style="font-size: 12px; color: {MUT}">◀ beyond this edge</span>{chips(edge["left"])}</div>' if edge['left'] else ''))
pF = panel(1600, 860, 296, 196, hd("Ambient key", "icons only") + '<div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px">' + ''.join(I.cell(k, 'line', 22) for k in ['military', 'milheli', 'tanker', 'clash', 'attack', 'protest', 'frontchange', 'occupied', 'leader', 'outage', 'carrier', 'quake']) + '</div>' + note('Words appear on hover; for a screen left running.'), "Ambient key", gap=6)
page2('LegendsB.dc.html', 'Legends B', f'<svg width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-label="Real items on the theatre view in line symbols" style="position: absolute; left: 0; top: 0">{mkB}</svg>'
      + title('Legend variants D, E, F', 'line symbols on the theatre view, outline ground').replace('left: 28px; top: 14px', 'left: 440px; top: 14px') + pD + pE + pF
      + tagc('D  Key inside the layers panel', 32, 60) + tagc('E  Counters beyond each edge', 1240, 20) + tagc('F  Ambient key', 1608, 836)
      + f'<div style="position: absolute; left: 440px; top: 100px; width: 760px; font-size: 12px; color: {MUT}">E counts items on the visible side of the globe that fall outside the screen, by the edge they lie beyond; {far} more are on the far side of the Earth.</div>', 'theatre_outline', 'Europe and the Black Sea at an angle, drawn as country outlines')
print('edges', {k: sum(v.values()) for k, v in edge.items()}, 'far', far)
