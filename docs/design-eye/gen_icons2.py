import math, json, io, contextlib, sys, os
with contextlib.redirect_stdout(io.StringIO()):
    from gen_icons import *            # page2, title, panel, hd, row, note, G, SG, MUT, E, age, IT, FR, V, seen, inr
import icons2 as J
from cam import Cam
SW2 = sys.argv[1] if len(sys.argv) > 1 else 'SW2'
NEW = json.load(open('newimg.json')) if os.path.exists('newimg.json') else {}
def page4(name, ttl, body, img=None, alt=''):
    page2(name, ttl, body.replace(I.DEFS, ''), img, alt)
    s = open(OUT + name).read().replace(I.DEFS, J.DEFS2, 1); open(OUT + name, 'w').write(s)
def bgimg(key, x, y, w, h, ox, oy, scale=1.0):
    return f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; overflow: hidden; border-radius: 16px; border: 1px solid rgba(255,255,255,0.16)"><img src="/_blob/{key}" alt="" style="position: absolute; left: {-ox*scale}px; top: {-oy*scale}px; width: {1920*scale}px; height: {1080*scale}px"></div>'
GR4 = ['land', 'mono', 'dark', 'light']
def cellsvg(i, fam, w, h, px, mode, rot=0):
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true" style="display: block">{J.draw(i, fam, w/2, h/2, px, rot, "A", mode)}</svg>'
import os
os.makedirs('pages', exist_ok=True)
def sheet(name, ttl, ids, sub):
    n = len(ids); rh = min(58, (950 - 30)//n); px = rh - 14
    x0, y0 = 24, 124; tw = rh
    fw = 4*(tw + 2) + 30
    head = f'<div style="position: absolute; left: {x0}px; top: {y0-44}px; width: 420px; font-size: 12px; color: {MUT}">Symbol · what it is drawn from</div>'
    for f, fam in enumerate(['solid', 'line']):
        fx = x0 + 440 + f*fw
        head += (f'<div style="position: absolute; left: {fx}px; top: {y0-50}px; width: {fw-30}px"><div style="{SG}; font-weight: 600; font-size: 15px">{"Solid" if fam == "solid" else "Line with glow"}</div>'
                 f'<div style="display: flex; gap: 2px; font-size: 10px; color: {MUT}">' + ''.join(f'<span style="width: {tw}px">{g}</span>' for g in GR4) + '</div></div>')
    rows = ''
    for r_, i in enumerate(ids):
        s = J.LIB[i]; y = y0 + r_*rh
        rows += (f'<div style="position: absolute; left: {x0}px; top: {y}px; width: 430px; height: {rh-2}px; display: flex; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.07)">'
                 f'<span style="width: 10px; height: 10px; border-radius: 3px; flex: none; background: {J.colour(i)}"></span>'
                 f'<span style="display: flex; flex-direction: column; min-width: 0"><span style="font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(s["name"])}</span>'
                 f'<span style="font-size: 11px; color: {MUT}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(s["codes"])}</span></span></div>')
        for f, fam in enumerate(['solid', 'line']):
            fx = x0 + 440 + f*fw
            for g in range(4):
                mode = 'light' if g == 3 else 'dark'
                rows += (f'<div style="position: absolute; left: {fx + g*(tw+2)}px; top: {y}px; width: {tw}px; height: {rh-2}px; border-radius: 6px; overflow: hidden; background: url(/_blob/{SW2}) {-g*tw}px 0 / {4*tw}px {rh-2}px">'
                         f'{cellsvg(i, fam, tw, rh-2, px, mode)}</div>')
    sx = x0 + 440 + 2*fw + 10
    big = ''.join(f'<div style="display: flex; flex-direction: column; align-items: center; gap: 4px; width: 104px"><div style="display: flex; gap: 4px"><div style="border-radius: 10px; background: #05080c">{cellsvg(i, "solid", 50, 50, 42, "dark")}</div><div style="border-radius: 10px; background: #eef0eb">{cellsvg(i, "solid", 50, 50, 42, "light")}</div></div><span style="font-size: 10px; color: {MUT}; text-align: center; line-height: 1.2">{E(J.LIB[i]["name"].split(",")[0].split("(")[0])}</span></div>' for i in ids[:12])
    side = panel(sx, 76, 1896 - sx, 980, hd(ttl.split(": ")[-1].capitalize(), sub, 17)
        + f'<div style="display: flex; flex-wrap: wrap; gap: 10px 6px">{big}</div>' + rule()
        + note('Each symbol is drawn from the data the feed really carries (second line of each row): the broadcast ICAO type code, the AIS ship-type number, the GDELT CAMEO event code, the UCS purpose, the GDACS or EONET category, the Cloudflare cause. Where a feed does not say, the general symbol is used, never a guess.')
        + note('Columns: photo over land, mono ground, plain dark, and the light theme (darker colours, white edge). Colours are palette A until you pick one.')
        + f'<div style="margin-top: auto">{note("Large previews above: dark and light at 42 px, the size of a selected symbol.")}</div>', "About this sheet", gap=10, pad=18)
    page4(name, ttl, title(ttl, f'{n} symbols · solid and line · dark grounds and light') + head + rows + side)
    return name
B = []
def split(ids, k):
    return [ids[i:i+k] for i in range(0, len(ids), k)]
groups = [('Aircraft', 'air', 'by the broadcast type code'), ('Ships', 'ships', 'by the AIS ship type'), ('Space', 'space', 'by UCS purpose and catalogue'),
          ('Conflict and news', 'conflict', 'by GDELT CAMEO code and source'), ('Earth', 'earth', 'by USGS, GDACS and EONET'), ('Networks and warnings', 'net', 'by cause and notice kind'), ('Sites', 'sites', 'by Wikidata, OSM and GEM class')]
for gname, slug, sub in groups:
    ids = [i for i, s in J.LIB.items() if s['group'] == gname]
    parts = split(ids, 16) if len(ids) > 16 else [ids]
    if len(parts) > 1 and len(parts[-1]) < 6: parts = split(ids, (len(ids) + 1)//2)
    for k, p in enumerate(parts):
        suffix = f' ({k+1} of {len(parts)})' if len(parts) > 1 else ''
        B.append((sheet(f'V2{slug.capitalize()}{k+1}.dc.html', f'Icons: {gname.lower()}{suffix}', p, sub), f'{gname}{suffix}: solid and line, dark and light'))

# ===== palettes =====
REP = ['narrow', 'mil_generic', 'heli_med', 'tanker', 'awacs', 'vip', 'doomsday', 'container', 'tanker_s', 'carrier', 'sanctioned', 'sat_img', 'sat_nav', 'sat_com', 'sat_spy', 'launch',
       'clash', 'aerial', 'protest', 'occupied', 'hotspot', 'news', 'quake_m', 'cyclone', 'wildfire', 'out_power', 'hijack', 'nw_missile', 'as_avoid', 'airbase', 'nuke', 'camera']
pb = ''
for c, pal in enumerate('ABC'):
    cx = 24 + c*632
    pb += f'<div style="position: absolute; left: {cx}px; top: 84px; width: 616px"><div style="{SG}; font-weight: 600; font-size: 17px">{J.PALN[pal]}</div></div>'
    for m, mode in enumerate(['dark', 'light']):
        y = 126 + m*468
        bg = '#05080c' if mode == 'dark' else '#eef0eb'
        cells = ''
        for n_, i in enumerate(REP):
            x = 40 + (n_ % 8)*72; yy = 50 + (n_//8)*100
            cells += J.draw(i, 'solid', x, yy, 36, 0, pal, mode) + f'<text x="{x}" y="{yy+34}" text-anchor="middle" font-family="Inter" font-size="9" fill="{"#c9d1d6" if mode == "dark" else "#5c6670"}">{E(J.LIB[i]["name"].split(",")[0].split("(")[0][:14])}</text>'
        pb += (f'<div style="position: absolute; left: {cx}px; top: {y}px; width: 616px; height: 452px; border-radius: 18px; overflow: hidden; background: url(/_blob/{SW2}) {-(0 if mode == "dark" else 3)*616}px 0 / {4*616}px 452px; border: 1px solid rgba(255,255,255,0.16)">'
               f'<div style="position: absolute; inset: 0; background: {bg}; opacity: {0.55 if mode == "dark" else 0.35}"></div>'
               f'<svg width="616" height="452" viewBox="0 0 616 452" aria-hidden="true" style="position: absolute; left: 0; top: 0">{cells}</svg>'
               f'<div style="position: absolute; right: 12px; bottom: 10px; font-size: 11px; color: {"#c9d1d6" if mode == "dark" else "#3a4652"}">{mode} theme</div></div>')
pb += f'<div style="position: absolute; left: 24px; top: 1052px; font-size: 12px; color: {MUT}">The same 32 symbols in each palette, on a dark and a light ground. A keeps a colour per domain, B keeps colour only for danger and notices, C keeps A\'s hues but softer, so the photo shows through more.</div>'
page4('V2Palettes.dc.html', 'Palettes', title('Three palettes', 'A colour per domain · B fewer colours · C muted; each with its light-theme twin') + pb)
B.insert(0, ('V2Palettes.dc.html', 'Three palettes, dark and light'))

# ===== sizes =====
SZ = ['narrow', 'wide', 'bizjet', 'heli_med', 'fighter', 'tanker', 'awacs', 'hale', 'container', 'tanker_s', 'carrier', 'sat_img', 'sat_spy', 'clash', 'aerial', 'protest', 'quake_m', 'out_power', 'nw_missile', 'airbase', 'nuke']
SIZES = [12, 16, 24, 32]
sb = f'<div style="position: absolute; left: 24px; top: 84px; width: 300px; font-size: 12px; color: {MUT}">Symbol</div>'
blocks = [('solid', 'dark'), ('line', 'dark'), ('solid', 'light'), ('line', 'light')]
bw = 380
for b_, (fam, mode) in enumerate(blocks):
    bx = 270 + b_*(bw + 12)
    sb += f'<div style="position: absolute; left: {bx}px; top: 78px"><div style="{SG}; font-weight: 600; font-size: 14px">{"Solid" if fam == "solid" else "Line"} · {mode}</div><div style="display: flex; gap: 0; font-size: 10px; color: {MUT}">' + ''.join(f'<span style="width: 95px">{s_} px</span>' for s_ in SIZES) + '</div></div>'
    bg = '#05080c' if mode == 'dark' else '#eef0eb'
    sb += f'<div style="position: absolute; left: {bx}px; top: 118px; width: {bw}px; height: {len(SZ)*44 + 8}px; border-radius: 14px; background: {bg}"></div>'
for r_, i in enumerate(SZ):
    y = 124 + r_*44
    sb += f'<div style="position: absolute; left: 24px; top: {y}px; width: 236px; height: 40px; display: flex; align-items: center; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.07)">{E(J.LIB[i]["name"].split("(")[0])}</div>'
    for b_, (fam, mode) in enumerate(blocks):
        bx = 270 + b_*(bw + 12)
        g = ''.join(J.draw(i, fam, 47 + k*95, 20, s_, 0, 'A', mode) for k, s_ in enumerate(SIZES))
        sb += f'<svg width="{bw}" height="40" viewBox="0 0 {bw} 40" aria-hidden="true" style="position: absolute; left: {bx}px; top: {y}px">{g}</svg>'
sb += f'<div style="position: absolute; left: 24px; top: 1066px; font-size: 12px; color: {MUT}">At 16 px and below an aircraft falls back to its simple class shape (airliner, heavy, propeller, helicopter, fighter, drone), because type details turn to mush at that size. Ships, events and sites keep their own shape at every size.</div>'.replace('top: 1066px', f'top: {124 + len(SZ)*44 + 14}px')
page4('V2Sizes.dc.html', 'Icon sizes', title('Sizes: 12, 16, 24 and 32 px', 'the same symbols at four sizes, solid and line, dark and light') + sb)
B.insert(1, ('V2Sizes.dc.html', 'Sizes 12 to 32 px, solid and line, dark and light'))

# ===== zoom steps =====
DIRECT = {'use of conventional military force': 'clash', 'fighting with artillery and tanks': 'artillery', 'aerial weapons (air strike, drone)': 'aerial', 'occupation of territory': 'occupy',
          'physical assault': 'attack', 'demonstration or rally': 'protest', 'protest': 'protest', 'fighting with small arms and light weapons': 'smallarms'}
def acls(a): return J.typecode_class(a.get('type')) or 'mil_generic'
def uncls(u): return DIRECT.get(u.get('action') or '', 'protest' if u['cat'] == 'protest' else ('attack' if u['cat'] == 'attack' else 'clash'))
def items_in(proj, rect, fam, size, mode, labels=False, simple=False, names=True):
    out = []; lab = []
    x0, y0, w, h = rect
    def ok(x, y): return 0 <= x - x0 <= w and 0 <= y - y0 <= h
    for a in IT['mil']:
        x, y, vis = proj(a['lon'], a['lat'])
        if not (vis and ok(x, y)): continue
        x2, y2, _ = proj(a['lon'] + 0.2*math.sin((a['track'] or 0)*r)/max(0.2, math.cos(a['lat']*r)), a['lat'] + 0.2*math.cos((a['track'] or 0)*r))
        ang = math.degrees(math.atan2(x2 - x, -(y2 - y)))
        cls = acls(a)
        out.append(J.draw(cls, fam, x - x0, y - y0, size, ang, 'A', mode, colkey='mil' if J.LIB[cls]['colkey'] == 'civil' else None))
        if labels: lab.append((x - x0 + size*0.6, y - y0 + 4, a['flight'], J.LIB[cls]['name'].split(',')[0].split('(')[0]))
    for u in IT['unrest']:
        x, y, vis = proj(u['lon'], u['lat'])
        if vis and ok(x, y): out.append(J.draw(uncls(u), fam, x - x0, y - y0, size*(0.9 + 0.12*math.sqrt(u['outlets'])), 0, 'A', mode))
    for c in FR['changes'][-8:]:
        x, y, vis = proj(c['lon'], c['lat'])
        if vis and ok(x, y): out.append(J.draw('frontchange', fam, x - x0, y - y0, size*0.6, 0, 'A', mode))
    for q in IT['quakes']:
        x, y, vis = proj(q['lon'], q['lat'])
        if vis and ok(x, y): out.append(J.draw('quake_s' if q['mag'] < 5.5 else ('quake_m' if q['mag'] < 6.5 else 'quake_l'), fam, x - x0, y - y0, size, 0, 'A', mode))
    if names:
        for l in IT['leaders']:
            x, y, vis = proj(l['lon'], l['lat'])
            if vis and ok(x, y):
                out.append(J.draw('leader', fam, x - x0, y - y0, size*0.7, 0, 'A', mode))
                lab.append((x - x0 + size*0.5, y - y0 + 4, l['name'], ''))
    tc = '#ffffff' if mode == 'dark' else '#1c2430'; sc = '#000000' if mode == 'dark' else '#ffffff'
    t = ''.join(f'<text x="{x:.0f}" y="{y:.0f}" font-family="Inter" font-size="12" font-weight="600" fill="{tc}" stroke="{sc}" stroke-opacity="0.65" stroke-width="3" paint-order="stroke">{E(a)}<tspan font-weight="400" fill-opacity="0.75"> {E(b)}</tspan></text>' for x, y, a, b in lab)
    return ''.join(out) + t
cn = json.load(open('near_centre.json'))
NEAR = Cam(cn[0], cn[1], 0.1, cn[0], cn[1], 654, 308, 235)
PW, PH = 616, 470
cwhole = V['whole']['cams'][0][0]; cth = V['theatre']['cams'][0][0]
FAR_O = (700, 250); MID_O = (100, 220)
STEPS = [('Far: whole Earth', 'whole', cwhole.proj, FAR_O, 10, False, 'icons small; aircraft drop to their simple shape'),
         ('Middle: theatre', 'theatre', cth.proj, MID_O, 18, False, 'symbols by type, no labels'),
         ('Near: 640 km across', 'near', NEAR.proj, (0, 0), 30, True, 'full type silhouettes, callsign and type beside')]
zb = ''
for rI, (fam, mode) in enumerate([('solid', 'dark'), ('line', 'dark')]):
    for cI, (lab, img, proj, org, size, labels, sub) in enumerate(STEPS):
        x = 24 + cI*(PW + 16); y = 84 + rI*(PH + 18)
        key = NEW.get('near') if img == 'near' else IMG[img]
        pic = (f'<img src="/_blob/{key}" alt="" style="position: absolute; left: 0; top: 0; width: {PW}px; height: {PH}px">' if img == 'near'
               else f'<img src="/_blob/{key}" alt="" style="position: absolute; left: {-org[0]}px; top: {-org[1]}px; width: 1920px; height: 1080px">')
        items = items_in(proj, (org[0], org[1], PW, PH), fam, size, mode, labels, names=cI > 0)
        zb += (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {PW}px; height: {PH}px; overflow: hidden; border-radius: 16px; border: 1px solid rgba(255,255,255,0.16)">{pic}'
               f'<svg width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}" role="img" aria-label="Real items at {lab}" style="position: absolute; left: 0; top: 0">{items}</svg>'
               f'<div style="position: absolute; left: 12px; top: 10px; padding: 6px 12px; border-radius: 999px; {G}"><span style="{SG}; font-weight: 600; font-size: 14px">{lab}</span><span style="font-size: 12px; color: {MUT}"> · {"Solid" if fam == "solid" else "Line"} · {size} px · {sub}</span></div></div>')
zb += f'<div style="position: absolute; left: 24px; top: 1052px; font-size: 12px; color: {MUT}">Real items from the capture, each view with its own camera. Military aircraft by broadcast type code; the ones whose code is not in the table use the general military shape. Clashes by GDELT\'s coded action.</div>'
page4('V2Zoom.dc.html', 'Zoom steps', title('Zoom steps', 'how the set changes from far to near, solid above and line below') + zb)
B.insert(2, ('V2Zoom.dc.html', 'Zoom steps: far, middle, near'))

# ===== light theme on the map =====
lb = ''
for cI, (fam, lab) in enumerate([('solid', 'Solid'), ('line', 'Line')]):
    x = 24 + cI*944
    items = items_in(cth.proj, (MID_O[0], MID_O[1], 928, 700), fam, 20, 'light', names=True)
    lb += (f'<div style="position: absolute; left: {x}px; top: 84px; width: 928px; height: 700px; overflow: hidden; border-radius: 16px; border: 1px solid rgba(0,0,0,0.12)">'
           f'<img src="/_blob/{NEW.get("theatre_light")}" alt="" style="position: absolute; left: {-MID_O[0]}px; top: {-MID_O[1]}px; width: 1920px; height: 1080px">'
           f'<svg width="928" height="700" viewBox="0 0 928 700" role="img" aria-label="Real items, light theme, {lab}" style="position: absolute; left: 0; top: 0">{items}</svg>'
           f'<div style="position: absolute; left: 12px; top: 10px; padding: 6px 12px; border-radius: 999px; background: rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.1); color: #1c2430"><span style="{SG}; font-weight: 600; font-size: 14px">{lab}, light theme</span></div></div>')
nearl = items_in(NEAR.proj, (0, 107, PW, 256), 'solid', 30, 'light', True, names=False)
lb += (f'<div style="position: absolute; left: 24px; top: 800px; width: {PW}px; height: 256px; overflow: hidden; border-radius: 16px; border: 1px solid rgba(0,0,0,0.12)">'
       f'<img src="/_blob/{NEW.get("near_light")}" alt="" style="position: absolute; left: 0; top: -107px; width: {PW}px; height: {PH}px">'
       f'<svg width="{PW}" height="256" viewBox="0 0 {PW} 256" role="img" aria-label="Near view, light theme, solid" style="position: absolute; left: 0; top: 0">{nearl}</svg>'
       f'<div style="position: absolute; left: 12px; top: 10px; padding: 6px 12px; border-radius: 999px; background: rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.1); color: #1c2430"><span style="{SG}; font-weight: 600; font-size: 14px">Near, light theme</span></div></div>')
lb += panel(656, 800, 1240, 256, hd("Light theme", "for the Apple Maps look") + note('Every colour has a darker twin with enough contrast on a pale ground (rose #d6203f, aqua #0089a8, violet #6a4bd6, aircraft slate #2a3440, notices #a37b00, selection #0071c2), and the edge turns white instead of black. The line family loses its glow in the light theme, because a glow on a pale ground looks like a smudge.') + note('The light ground here is the photo turned pale; in the app it would be the Apple-Maps-style street map.'), "Light theme notes", gap=8)
page4('V2Light.dc.html', 'Light theme', title('Light theme on the map', 'the same real items, solid and line, on a pale ground').replace('#8fdcff', '#8fdcff') + lb)
B.insert(3, ('V2Light.dc.html', 'Light theme on the map'))
json.dump(B, open('v2boards.json', 'w'))
print(len(B), 'boards')
