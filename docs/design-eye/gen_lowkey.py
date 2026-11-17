import math, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from gen_icons import *
import icons_lk as L
FONTS = '&family=IBM+Plex+Mono:wght@400;500;600'
def page3(name, ttl, body, img=None, alt=''):
    page2(name, ttl, body, img, alt)
    s = open(OUT + name).read().replace('&display=swap', FONTS + '&display=swap', 1); open(OUT + name, 'w').write(s)
GR3 = [(0, 'land'), (2, 'mono'), (3, 'dark')]
def lsheet(name, groups, ttl):
    ids = [k for k, v in I.S.items() if v['group'] in groups]
    n = len(ids); rh = min(52, (960 - 40)//n); px = rh - 10
    x0, y0 = 24, 124; cw = [3*(rh+2) + 26, 3*(rh+2) + 26, 3*(rh*2+2) + 26]
    head = f'<div style="position: absolute; left: {x0}px; top: {y0-44}px; font-size: 12px; color: {MUT}">Symbol · code</div>'
    fx = x0 + 300
    for f, fam in enumerate(L.LKF):
        w = rh*2 if fam == 'scope' else rh
        head += (f'<div style="position: absolute; left: {fx}px; top: {y0-50}px"><div style="{SG}; font-weight: 600; font-size: 15px">{L.LKN[fam]}</div>'
                 f'<div style="display: flex; gap: 2px; font-size: 10px; color: {MUT}">' + ''.join(f'<span style="width: {w}px">{g}</span>' for _, g in GR3) + '</div></div>')
        fx += cw[f]
    rows = ''
    for r, k in enumerate(ids):
        s = I.S[k]; y = y0 + r*rh
        rows += (f'<div style="position: absolute; left: {x0}px; top: {y}px; width: 290px; height: {rh-2}px; display: flex; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.07)">'
                 f'<span style="width: 34px; flex: none; font-family: {L.MONO}; font-size: 11px; color: {L.colour(k)}">{L.CODE[k]}</span><span style="font-size: {13 if rh > 44 else 12}px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(s["name"])}</span></div>')
        fx = x0 + 300
        for f, fam in enumerate(L.LKF):
            w = rh*2 if fam == 'scope' else rh
            for j, (g, _) in enumerate(GR3):
                sv = f'<svg width="{w}" height="{rh-2}" viewBox="0 0 {w} {rh-2}" aria-hidden="true" style="display: block">{L.lk(k, fam, (rh-2)/2 + 2, (rh-2)/2, px, 35)}</svg>'
                rows += f'<div style="position: absolute; left: {fx + j*(w+2)}px; top: {y}px; width: {w}px; height: {rh-2}px; border-radius: 6px; overflow: hidden; background: url(/_blob/{SW}) {-g*w}px 0 / {4*w}px {rh-2}px">{sv}</div>'
            fx += cw[f]
    sx = fx + 10
    side = panel(sx, 76, 1896 - sx, 980, hd("Low key", "three quiet families", 17)
        + note('Thin lines, small marks, no fills. Colour only where it carries a warning: <b style="color: #ff6b81">rose</b> conflict and danger, <b style="color: #ffe066">yellow</b> a notice in force, everything else one neutral grey-white. Ice blue is kept for the selection.')
        + rule() + hd("Where the idea comes from", "")
        + note('Military map symbols (NATO APP-6, US MIL-STD-2525) tell the domain by the frame: an arch for air, a bowl for the sea surface, a rectangle on land. We borrow that: <b style="color: #f2f4f6">the frame says where it is</b>, a three-letter code says what it is.')
        + note('We do <b style="color: #f2f4f6">not</b> borrow their friend / hostile colours and shapes (blue rectangle, red diamond): the app does not judge sides, and a red diamond would read as "enemy" to anyone who knows the standard.')
        + rule() + hd("The three families", "")
        + note('<b style="color: #f2f4f6">Frame and code</b>: domain frame with the code inside. Readable when zoomed in.')
        + note('<b style="color: #f2f4f6">Reticle</b>: brackets around a dot, code under it; aircraft and ships get a heading tick. Very light.')
        + note('<b style="color: #f2f4f6">Scope and data block</b>: as on an air-traffic scope: a small target and a leader line to a block of real data (callsign, height, speed). The block can show on hover only.')
        + rule() + '<div style="display: flex; gap: 14px; align-items: center">' + ''.join(f'<div style="display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 11px; color: {MUT}"><svg width="56" height="56" viewBox="0 0 64 64" aria-hidden="true"><path d="{L.FR[d]}" fill="none" stroke="{L.NEU}" stroke-width="2.4"{" stroke-dasharray=\"5 4\"" if d == "warn" else ""}></path></svg>{t}</div>' for d, t in [('air', 'air'), ('sea', 'sea'), ('space', 'space'), ('land', 'land, sites'), ('event', 'event'), ('net', 'network'), ('warn', 'notice')]) + '</div>'
        + f'<div style="margin-top: auto">{note("Sources: Wikipedia, NATO Joint Military Symbology (APP-6); milsymbol, an MIT-licensed JavaScript library that draws real APP-6 / 2525 symbols, if we ever want the standard itself.")}</div>', "Low-key families", gap=9, pad=18)
    page3(name, ttl, title(ttl, f'{n} symbols · three low-key families · photo, mono and dark grounds') + head + rows + side)
lsheet('LowAirSea.dc.html', [I.A, I.SE], 'Low key: air, sea and space')
lsheet('LowConflict.dc.html', [I.C, I.EA], 'Low key: conflict, news and Earth')
lsheet('LowNet.dc.html', [I.NW], 'Low key: networks, warnings and sites')

# ===== on the map =====
def lk_items(view, fam, clip, dx, dy, data=False, sc=1.0):
    out = []
    def ok(x, y): return inr(x, y, clip)
    for i, x, y, cam in seen(view, 'mil', [(dx, dy, 600, 70)]):
        if not ok(x, y): continue
        t = (i['track'] or 0)*r; x2, y2, _ = cam.proj(i['lon'] + 0.2*math.sin(t)/max(0.2, math.cos(i['lat']*r)), i['lat'] + 0.2*math.cos(t))
        ang = math.degrees(math.atan2(x2 - x, -(y2 - y)))
        dat = [i['flight'], f"{'FL%03d' % round(i['alt']/100) if isinstance(i['alt'], (int, float)) else ''} {round(i['gs'] or 0)}kt"] if data else ([] if fam == 'scope' else None)
        out.append(L.lk(milsym(i), fam, x-dx, y-dy, 26*sc, ang, data=dat))
    for c in FR['changes'][-8:]:
        cam = V[view]['cams'][0][0]; x, y, vis = cam.proj(c['lon'], c['lat'])
        if vis and ok(x, y): out.append(L.lk('frontchange', fam, x-dx, y-dy, 18*sc, data=[] if fam == 'scope' else None))
    for kind, f in [('unrest', lambda i: (unsym(i), 26, [i['place'], f"{i['outlets']} out"])), ('outages', lambda i: ('outage', 26, [i['code'], 'IODA'])), ('leaders', lambda i: ('leader', 22, [i['name'].split()[-1].upper()]))]:
        for i, x, y, cam in seen(view, kind, [(dx, dy, 600, 70)]):
            if not ok(x, y): continue
            k, px, dd = f(i); out.append(L.lk(k, fam, x-dx, y-dy, px*sc, data=(dd if (data or kind != 'mil') else []) if fam == 'scope' else None))
    return ''.join(out)
q = ''
VARS = [('frame', False, 'Frame and code'), ('reticle', False, 'Reticle'), ('scope', False, 'Scope, blocks for events, aircraft quiet'), ('scope', True, 'Scope, every data block on (dense)')]
for n, (fam, dat, lab) in enumerate(VARS):
    qx, qy = QX[n % 2], QY[n//2]
    items = lk_items('theatre', fam, (ORG[0], ORG[1], QW, QH), ORG[0], ORG[1], dat, 1.15)
    q += (f'<div style="position: absolute; left: {qx}px; top: {qy}px; width: {QW}px; height: {QH}px; overflow: hidden; border-radius: 18px; border: 1px solid rgba(255,255,255,0.16)">'
          f'<img src="/_blob/{IMG["theatre_outline"] if n % 2 else IMG["theatre"]}" alt="" style="position: absolute; left: {-ORG[0]}px; top: {-ORG[1]}px; width: 1920px; height: 1080px">'
          f'<svg width="{QW}" height="{QH}" viewBox="0 0 {QW} {QH}" role="img" aria-label="Real items drawn as {lab}" style="position: absolute; left: 0; top: 0">{items}</svg>'
          f'<div style="position: absolute; left: 14px; top: 12px; padding: 7px 14px; border-radius: 999px; {G}"><span style="{SG}; font-weight: 600; font-size: 15px">{lab}</span><span style="font-size: 12px; color: {MUT}"> · {"photo" if n % 2 == 0 else "outline"} ground</span></div></div>')
page3('LowOnMap.dc.html', 'Low key on the map', title('Low key on the map', 'the same real items, three quiet families; the right column on the outline ground') + q
      + f'<div style="position: absolute; left: 24px; top: 1050px; font-size: 12px; color: {MUT}">Data blocks carry only reported values: callsign, flight level from the reported height, ground speed; for clashes the place and the number of outlets.</div>')
print('ok')
