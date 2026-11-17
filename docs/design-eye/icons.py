"""Symbol library for the God's eye look: every map symbol in four families (solid, line, badge, point).
Glyphs live on a 64 x 64 grid. Element modes: f fill, k knockout (drawn in the dark ink), s stroke, d dashed stroke,
a area (soft fill + edge), x accent badge (uses the symbol's accent colour)."""
import math
INK = '#05080c'
P = dict(civil='#d7dde2', mil='#ffffff', vip='#f5d76e', doom='#ff3b5c', tanker='#7ee0b5', isr='#ff8fa3',
         ship='#5fe3ff', leo='#7ee0b5', meo='#ffe066', geo='#8fdcff', heo='#ffa3d9', spy='#ff3b5c', launch='#b9a2ff',
         clash='#ff3b5c', protest='#ffc2cd', front='#ffffff', warn='#ffe066', quake='#ffffff', disaster='#f2a6ff',
         fire='#fff0a0', bolt='#ffffff', net='#c9d1d6', hijack='#ff3b5c', leak='#8fdcff', cable='#9aa7b2', ok='#7ee0b5',
         site='#c9d1d6', nuke='#d8f36a', cam='#8fdcff', sdr='#c8c0e8', leader='#ffffff', news='#e6eaed', hot='#ff3b5c', ice='#8fdcff')
def circ(cx, cy, r): return f'M{cx-r} {cy}a{r} {r} 0 1 0 {2*r} 0a{r} {r} 0 1 0 {-2*r} 0Z'
def star(n, r1, r2, cx=32, cy=32, rot=-90):
    pts = []
    for i in range(2*n):
        a = math.radians(rot + i*180/n); r_ = r1 if i % 2 == 0 else r2
        pts.append(f'{cx + r_*math.cos(a):.1f} {cy + r_*math.sin(a):.1f}')
    return 'M' + ' L'.join(pts) + 'Z'
def trefoil(cx=32, cy=32, r1=7, r2=26):
    d = ''
    for k in range(3):
        a0 = math.radians(-90 + k*120 - 30); a1 = math.radians(-90 + k*120 + 30)
        p = lambda r_, a: f'{cx + r_*math.cos(a):.1f} {cy + r_*math.sin(a):.1f}'
        d += f'M{p(r1, a0)} L{p(r2, a0)} A{r2} {r2} 0 0 1 {p(r2, a1)} L{p(r1, a1)} A{r1} {r1} 0 0 0 {p(r1, a0)}Z'
    return d + circ(cx, cy, 4)
SH = {
  'jet': 'M32 3c2.6 0 3.8 5 3.8 10.5V25l22.7 14.2v5.3L35.8 37.6v14.2l6.7 5.4v4L32 58.2 21.5 61.2v-4l6.7-5.4V37.6L5.5 44.5v-5.3L28.2 25V13.5C28.2 8 29.4 3 32 3z',
  'heavy': 'M32 2c3.2 0 4.6 5 4.6 11v9.5L62 42v6l-25.4-8V51l8.4 6.2v4.3L32 58 19 61.5v-4.3l8.4-6.2V40L2 48v-6l25.4-19.5V13c0-6 1.4-11 4.6-11z',
  'eng': 'M44 24.5h4v8h-4zM52 30.5h4v8h-4zM16 24.5h4v8h-4zM8 30.5h4v8h-4z',
  'prop': 'M32 7c1.9 0 2.9 3 2.9 7v6.5h22.6v7l-22.6 3v14.5l7.5 3.5v4L32 51l-10.4 1.5v-4l7.5-3.5V30.5l-22.6-3v-7h22.6V14c0-4 1-7 2.9-7zM27 4.5h10v2.5H27z',
  'fighter': 'M32 3c1.6 0 2.6 4.5 3.2 10l1.3 12L55 46.5v5l-17-3.5.4 6.5 6.1 4v3.5L32 58.5 19.5 62v-3.5l6.1-4 .4-6.5-17 3.5v-5L27.5 25l1.3-12C29.4 7.5 30.4 3 32 3z',
  'heli': 'M32 12c5 0 8 5 8 11 0 6-3 10-5.5 12L33.5 54h-3L29.5 35C27 33 24 29 24 23c0-6 3-11 8-11zM25 50h14v3.5H25z',
  'rotor': 'M11.9 5.1L14.1 2.9 52.1 40.9 49.9 43.1zM49.9 2.9L52.1 5.1 14.1 43.1 11.9 40.9z',
  'glider': 'M32 9c1.3 0 2 3 2 6v8.5h28v4.2l-28 2.3v17l6.5 2.5v3.2L32 51l-8.5 1.7v-3.2L30 47V30L2 27.7v-4.2h28V15c0-3 .7-6 2-6z',
  'balloon': 'M32 5a20 20 0 0 1 20 20c0 9.5-7.5 15.5-12.5 21h-15C19.5 40.5 12 34.5 12 25A20 20 0 0 1 32 5zM27 49h10v9H27z',
  'drone': 'M32 4c3.6 0 5.2 3.2 5.2 7 0 3.2-1.4 5.6-3 7.2L33.8 54h-3.6L29.8 18.2c-1.6-1.6-3-4-3-7.2 0-3.8 1.6-7 5.2-7zM3 28h58v3.6L34 34.5h-4L3 31.6zM32 46l10 8v3.4L32 53l-10 4.4V54z',
}
SHIP = 'M32 4L44 22V58H20V22Z'
# id: (name, colour, glyph elements, point spec (shape, code), rotates with heading, accent colour)
S = {}
def add(i, name, col, g, pt, rot=False, acc=None, group=''): S[i] = dict(name=name, col=P[col], g=g, pt=pt, rot=rot, acc=P[acc] if acc else None, group=group)
A = 'Air'
add('airliner', 'Airliner', 'civil', [(SH['jet'], 'f')], ('chev', ''), True, group=A)
add('heavy', 'Heavy jet', 'civil', [(SH['heavy'], 'f'), (SH['eng'], 'f')], ('chev', ''), True, group=A)
add('prop', 'Propeller, light aircraft', 'civil', [(SH['prop'], 'f')], ('chev', ''), True, group=A)
add('heli', 'Helicopter', 'civil', [(SH['heli'], 'f'), (SH['rotor'], 'f')], ('dot', 'H'), True, group=A)
add('glider', 'Glider', 'civil', [(SH['glider'], 'f')], ('chev', ''), True, group=A)
add('balloon', 'Balloon, airship', 'civil', [(SH['balloon'], 'f')], ('dot', 'B'), group=A)
add('drone', 'Drone', 'civil', [(SH['drone'], 'f')], ('dia', 'D'), True, group=A)
add('military', 'Military jet', 'mil', [(SH['jet'], 'f'), ('M30 40h4v12h-4Z', 'k')], ('chev', ''), True, group=A)
add('fighter', 'Fighter', 'mil', [(SH['fighter'], 'f')], ('chev', ''), True, group=A)
add('milheli', 'Military helicopter', 'mil', [(SH['heli'], 'f'), (SH['rotor'], 'f')], ('dot', 'H'), True, group=A)
add('tanker', 'Tanker', 'tanker', [(SH['heavy'], 'f'), ('M31 58h2v6h-2Z', 'f'), (circ(32, 63, 3), 'f')], ('chev', 'T'), True, group=A)
add('isr', 'Surveillance aircraft in an orbit', 'isr', [('M8 32a24 14 0 1 0 48 0a24 14 0 1 0-48 0Z', 'd'), (circ(32, 32, 7), 'f')], ('ring', 'O'), group=A)
add('vip', 'Government / VIP jet', 'vip', [(SH['jet'], 'f'), (star(5, 9, 4, 32, 30), 'k')], ('dia', 'V'), True, group=A)
add('doomsday', 'Airborne command post', 'doom', [(SH['heavy'], 'f'), (SH['eng'], 'f'), (circ(32, 30, 7), 'k')], ('dia', '!'), True, group=A)
add('ground', 'Aircraft on the ground', 'civil', [('M22 20h20a3 3 0 0 1 3 3v18a3 3 0 0 1-3 3H22a3 3 0 0 1-3-3V23a3 3 0 0 1 3-3z', 'f')], ('sq', ''), group=A)
SE = 'Sea and space'
add('ship', 'Ship', 'ship', [(SHIP, 'f')], ('tri', ''), True, group=SE)
add('warship', 'Warship', 'ship', [('M32 2L41 18V60H23V18Z', 'f'), ('M28 26h8v14h-8Z', 'k')], ('tri', 'W'), True, group=SE)
add('carrier', 'Aircraft carrier', 'ship', [('M22 3H42V61H22Z', 'f'), ('M42 22h6v12h-6Z', 'f'), ('M27 10h3v42h-3Z', 'k')], ('sq', 'CV'), True, group=SE)
add('amphib', 'Amphibious assault ship', 'ship', [('M24 4H40V60H24Z', 'f'), ('M40 26h5v10h-5Z', 'f'), ('M24 50h16v4H24Z', 'k')], ('sq', 'LH'), True, group=SE)
add('sanctioned', 'Sanctioned or shadow-fleet ship', 'ship', [(SHIP, 'f'), (circ(48, 14, 11), 'x')], ('tri', 'S'), True, acc='clash', group=SE)
add('sat_leo', 'Satellite, low orbit', 'leo', [('M26 26h12v12H26Z', 'f'), ('M4 28h18v8H4Z', 'f'), ('M42 28h18v8H42Z', 'f')], ('dot', ''), group=SE)
add('sat_meo', 'Satellite, medium orbit (navigation)', 'meo', [('M26 26h12v12H26Z', 'f'), ('M4 28h18v8H4Z', 'f'), ('M42 28h18v8H42Z', 'f')], ('dot', 'N'), group=SE)
add('sat_geo', 'Satellite, geostationary', 'geo', [('M26 26h12v12H26Z', 'f'), ('M4 28h18v8H4Z', 'f'), ('M42 28h18v8H42Z', 'f')], ('dot', 'G'), group=SE)
add('sat_heo', 'Satellite, highly elliptical', 'heo', [('M26 26h12v12H26Z', 'f'), ('M4 28h18v8H4Z', 'f'), ('M42 28h18v8H42Z', 'f')], ('dot', 'E'), group=SE)
add('sat_spy', 'Military imaging / signals satellite', 'spy', [('M32 6L54 32 32 58 10 32Z', 'f'), (circ(32, 32, 7), 'k')], ('dia', ''), group=SE)
add('iss', 'Space station', 'leo', [('M28 22h8v20h-8Z', 'f'), ('M2 14h20v10H2Z', 'f'), ('M42 14h20v10H42Z', 'f'), ('M2 40h20v10H2Z', 'f'), ('M42 40h20v10H42Z', 'f'), ('M22 30h20v4H22Z', 'f')], ('dot', 'ISS'), group=SE)
add('launch', 'Launch pad, launch coming up', 'launch', [('M32 3c6 8 9 18 9 30v12H23V33c0-12 3-22 9-30Z', 'f'), ('M23 38l-8 10v8l8-4Z', 'f'), ('M41 38l8 10v8l-8-4Z', 'f'), ('M27 48h10l-2 10h-6Z', 'f')], ('tri', 'L'), group=SE)
C = 'Conflict and news'
add('clash', 'Armed clash', 'clash', [(star(8, 29, 14), 'f')], ('dot', 'C'), group=C)
add('attack', 'Attack', 'clash', [('M32 6L59 55H5Z', 'f'), ('M29.5 22h5v18h-5ZM29.5 44h5v5h-5Z', 'k')], ('dot', 'A'), group=C)
add('riot', 'Riot', 'clash', [(star(12, 29, 21), 'f'), (circ(32, 32, 11), 'k')], ('dot', 'R'), group=C)
add('mass', 'Mass violence', 'clash', [(star(10, 30, 16), 'f'), (star(10, 14, 7), 'k')], ('dot', 'M'), group=C)
add('protest', 'Protest', 'protest', [(circ(32, 32, 24), 's')], ('ring', 'P'), group=C)
add('occupied', 'Occupied area (DeepState)', 'clash', [('M6 10H58V54H6Z', 'a'), ('M6 30L26 10M6 50L46 10M22 54L58 18M42 54L58 38', 's')], ('area', ''), group=C)
add('frontchange', 'Front-line change', 'front', [('M12 12H52V52H12Z', 's')], ('sq', ''), group=C)
add('unit', 'Unit position', 'clash', [('M8 16H56V48H8Z', 's'), ('M8 16L56 48M56 16L8 48', 's')], ('sq', 'U'), group=C)
add('direction', 'Direction of attack', 'clash', [('M6 25H36V12L60 32 36 52V39H6Z', 'f')], ('tri', ''), group=C)
add('hotspot', 'Hotspot (3+ kinds of signal)', 'hot', [(circ(32, 32, 27), 's'), (circ(32, 32, 15), 's'), (circ(32, 32, 5), 'f')], ('ring', '3'), group=C)
add('news', 'Place in the news', 'news', [('M8 10H56V44H30L18 56V44H8Z', 'f'), ('M16 20h32v4H16ZM16 30h22v4H16Z', 'k')], ('dot', '12'), group=C)
add('breaking', 'Breaking: sudden jump in reports', 'news', [('M8 10H56V44H30L18 56V44H8Z', 'f'), ('M16 20h32v4H16ZM16 30h22v4H16Z', 'k'), (circ(50, 12, 11), 'x')], ('ring', '!'), acc='clash', group=C)
add('leader', 'Leader placed by the news', 'leader', [(circ(32, 20, 12), 'f'), ('M10 60c0-16 10-24 22-24s22 8 22 24Z', 'f')], ('dia', ''), group=C)
add('head', 'Head of state, at the country', 'leader', [(circ(32, 22, 11), 'f'), ('M12 60c0-15 9-22 20-22s20 7 20 22Z', 'f'), (star(5, 9, 4, 52, 12), 'x')], ('dia', 'HS'), acc='vip', group=C)
EA = 'Earth'
add('quake', 'Earthquake (size = magnitude)', 'quake', [(circ(32, 32, 7), 'f'), (circ(32, 32, 17), 's'), (circ(32, 32, 27), 'd')], ('ring', '5.4'), group=EA)
add('quake_test', 'Quake near a nuclear test site', 'quake', [(circ(32, 32, 7), 'f'), (circ(32, 32, 17), 's'), (circ(32, 32, 27), 'd'), (circ(52, 12, 10), 'x')], ('ring', '☢'), acc='nuke', group=EA)
add('cyclone', 'Tropical cyclone', 'disaster', [(circ(32, 32, 10), 'f'), ('M32 20c12-14 30-4 26 9', 's'), ('M32 44c-12 14-30 4-26-9', 's')], ('dot', 'Cy'), group=EA)
add('flood', 'Flood', 'disaster', [('M4 24c7-8 14 8 21 0s14 8 21 0 14 8 14 0', 's'), ('M4 40c7-8 14 8 21 0s14 8 21 0 14 8 14 0', 's')], ('dot', 'F'), group=EA)
add('volcano', 'Volcano', 'disaster', [('M4 58L24 24h16l20 34Z', 'f'), ('M28 18l-6-12M36 18l6-12M32 16V2', 's')], ('tri', 'V'), group=EA)
add('wildfire', 'Wildfire alert', 'disaster', [('M32 4c4 12 18 18 18 34a18 18 0 0 1-36 0c0-10 6-14 8-22 4 6 4 10 8 12 0-10 0-16 2-24Z', 'f')], ('dot', 'W'), group=EA)
add('fire', 'Hot spot (NASA MODIS)', 'fire', [(circ(32, 32, 12), 'f')], ('dot', ''), group=EA)
add('lightning', 'Lightning', 'bolt', [('M36 2L12 36h16L22 62 52 24H34Z', 'f')], ('tri', ''), group=EA)
NW = 'Networks, warnings, sites'
add('outage', 'Internet outage (IODA)', 'net', [('M8 44h8v12H8Z', 'f'), ('M22 34h8v22h-8Z', 'f'), ('M36 24h8v32h-8Z', 'a'), ('M50 14h8v42h-8Z', 'a'), ('M6 6L58 58', 's')], ('sq', 'IR'), group=NW)
add('cfnote', 'Cloudflare outage note', 'ice', [('M14 6H42L52 16V58H14Z', 'f'), ('M20 24h26v4H20ZM20 34h26v4H20ZM20 44h16v4H20Z', 'k')], ('sq', 'C'), group=NW)
add('hijack', 'Possible route hijack', 'hijack', [('M6 52C14 18 40 10 54 18', 's'), ('M46 8L61 18 45 27Z', 'f')], ('bar', ''), group=NW)
add('leak', 'Route leak', 'leak', [('M6 52C14 18 40 10 54 18', 'd'), ('M46 8L61 18 45 27Z', 'f')], ('bar', ''), group=NW)
add('cable', 'Undersea cable', 'cable', [('M4 40C20 20 44 52 60 28', 's')], ('bar', ''), group=NW)
add('cable_fault', 'Cable named in fault news', 'clash', [('M4 40C20 20 44 52 60 28', 's'), ('M22 22L42 42M42 22L22 42', 's')], ('bar', '×'), group=NW)
add('cable_fixed', 'Cable reported repaired', 'ok', [('M4 40C20 20 44 52 60 28', 'd'), ('M20 30l8 8 16-16', 's')], ('bar', '✓'), group=NW)
add('navwarn', 'Navy warning area', 'warn', [('M32 4L60 54H4Z', 's'), ('M14 46c6-5 12 5 18 0s12 5 18 0', 's')], ('tri', 'N'), group=NW)
add('airspace', 'Airspace warning (conflict zone)', 'warn', [('M18 6H46L60 32 46 58H18L4 32Z', 'd'), (SH['jet'].replace('M32 3', 'M32 3'), 'f')], ('area', ''), group=NW)
add('tfr', 'Temporary flight restriction', 'warn', [(circ(32, 32, 26), 'd'), ('M20 20h24v6H35v20h-6V26H20Z', 'f')], ('ring', 'T'), group=NW)
add('base', 'Military base', 'site', [('M8 8H56V56H8Z', 'f'), (star(5, 17, 7), 'k')], ('sq', ''), group=NW)
add('sigint', 'Missile or signals site', 'clash', [('M8 8H56V56H8Z', 'f'), ('M30 22h4v26h-4Z', 'k'), (circ(32, 20, 6), 'k')], ('sq', 'S'), group=NW)
add('radar', 'Military radar', 'ice', [('M10 46A26 26 0 0 1 46 10L10 46Z', 'f'), ('M28 28L50 50', 's'), (circ(52, 52, 6), 'f')], ('sq', 'R'), group=NW)
add('milarea', 'Military area (OSM)', 'site', [('M6 10H58V54H6Z', 'a'), ('M6 30L26 10M6 50L46 10M22 54L58 18M42 54L58 38', 's')], ('area', ''), group=NW)
add('nuke', 'Nuclear power plant', 'nuke', [('M18 58c4-12 4-30 0-46h28c-4 16-4 34 0 46Z', 'f'), ('M24 8c2-4 6-4 8 0M34 6c2-4 6-4 8 0', 's')], ('dot', 'NP'), group=NW)
add('nukesite', 'Research / fuel-cycle / waste site', 'nuke', [(trefoil(), 'f')], ('dot', '☢'), group=NW)
add('testsite', 'Nuclear test site', 'clash', [(circ(32, 32, 28), 's'), (trefoil(32, 32, 6, 21), 'f')], ('ring', '☢'), group=NW)
add('camera', 'Public camera', 'cam', [('M6 20h40v26H6Z', 'f'), ('M46 26l12-6v26l-12-6Z', 'f'), (circ(26, 33, 7), 'k')], ('dot', ''), group=NW)
add('camlive', 'Webcam with a live stream', 'cam', [('M6 20h40v26H6Z', 'f'), ('M46 26l12-6v26l-12-6Z', 'f'), (circ(26, 33, 7), 'k'), (circ(52, 12, 9), 'x')], ('dot', '●'), acc='ok', group=NW)
add('sdr', 'Shortwave receiver', 'sdr', [('M30 26h4v32h-4Z', 'f'), ('M20 16a16 16 0 0 1 24 0', 's'), ('M12 8a26 26 0 0 1 40 0', 's'), (circ(32, 26, 5), 'f')], ('dot', 'SW'), group=NW)
FAM = ['solid', 'line', 'badge', 'point']
FAMN = dict(solid='Solid', line='Line with glow', badge='Badge', point='Point and code')
DEFS = ('<svg width="0" height="0" style="position: absolute" aria-hidden="true"><defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="2.2" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter></defs></svg>')
def els(sym, fam, col, ink=INK):
    o = []; g = sym['g']; acc = sym['acc'] or col
    if fam == 'solid':
        for d, m in g:
            if m in ('f', 'x'): o.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="6" stroke-linejoin="round"></path>')
            if m in ('s', 'd'): o.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"></path>')
        for d, m in g:
            if m == 'f': o.append(f'<path d="{d}" fill="{col}"></path>')
            elif m == 'k': o.append(f'<path d="{d}" fill="{ink}"></path>')
            elif m == 's': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"></path>')
            elif m == 'd': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="5" stroke-dasharray="7 6"></path>')
            elif m == 'a': o.append(f'<path d="{d}" fill="{col}" fill-opacity="0.35" stroke="{col}" stroke-width="3"></path>')
            elif m == 'x': o.append(f'<path d="{d}" fill="{acc}"></path>')
    elif fam == 'line':
        inner = []
        for d, m in g:
            if m == 'f': inner.append(f'<path d="{d}" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-width="3.2" stroke-linejoin="round"></path>')
            elif m == 'k': inner.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.4"></path>')
            elif m == 's': inner.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"></path>')
            elif m == 'd': inner.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="3.2" stroke-dasharray="6 5"></path>')
            elif m == 'a': inner.append(f'<path d="{d}" fill="{col}" fill-opacity="0.18" stroke="{col}" stroke-width="2.6"></path>')
            elif m == 'x': inner.append(f'<path d="{d}" fill="{acc}"></path>')
        o.append('<g filter="url(#glow)">' + ''.join(inner) + '</g>')
    elif fam == 'badge':
        o.append(f'<circle cx="32" cy="32" r="30" fill="{col}" stroke="{ink}" stroke-width="3"></circle><g transform="translate(32 32) scale(0.58) translate(-32 -32)">')
        for d, m in g:
            if m == 'f': o.append(f'<path d="{d}" fill="{ink}"></path>')
            elif m == 'k': o.append(f'<path d="{d}" fill="{col}"></path>')
            elif m == 's': o.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"></path>')
            elif m == 'd': o.append(f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="6" stroke-dasharray="7 6"></path>')
            elif m == 'a': o.append(f'<path d="{d}" fill="{ink}" fill-opacity="0.45" stroke="{ink}" stroke-width="4"></path>')
            elif m == 'x': o.append(f'<path d="{d}" fill="{acc}" stroke="{ink}" stroke-width="4"></path>')
        o.append('</g>')
    else:
        sh, code = sym['pt']; t = ''
        if code:
            fs = 30 if len(code) == 1 else (24 if len(code) == 2 else 19)
            tc = col if sh in ('ring',) else ink
            t = f'<text x="32" y="{32 + fs*0.36:.1f}" text-anchor="middle" font-family="Inter, sans-serif" font-weight="700" font-size="{fs}" fill="{tc}">{code}</text>'
        if sh == 'chev': o.append(f'<path d="M32 8L50 54 32 44 14 54Z" fill="{col}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"></path>' + (f'<text x="32" y="40" text-anchor="middle" font-family="Inter" font-weight="700" font-size="16" fill="{ink}">{code}</text>' if code else ''))
        elif sh == 'dot': o.append(f'<circle cx="32" cy="32" r="{24 if code else 14}" fill="{col}" stroke="{ink}" stroke-width="4"></circle>{t}')
        elif sh == 'ring': o.append(f'<circle cx="32" cy="32" r="24" fill="{ink}" fill-opacity="0.55" stroke="{col}" stroke-width="6"></circle>{t}')
        elif sh == 'sq': o.append(f'<rect x="{10 if code else 18}" y="{10 if code else 18}" width="{44 if code else 28}" height="{44 if code else 28}" rx="6" fill="{col}" stroke="{ink}" stroke-width="4"></rect>{t}')
        elif sh == 'dia': o.append(f'<path d="M32 {4 if code else 12}L{60 if code else 52} 32 32 {60 if code else 52} {4 if code else 12} 32Z" fill="{col}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"></path>{t}')
        elif sh == 'tri': o.append(f'<path d="M32 6L60 56H4Z" fill="{col}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"></path>' + (t.replace(f'y="{32 + (30 if len(code) == 1 else 24)*0.36:.1f}"', 'y="50"') if code else ''))
        elif sh == 'bar': o.append(f'<path d="M6 44C22 20 42 48 58 24" fill="none" stroke="{ink}" stroke-width="12" stroke-linecap="round"></path><path d="M6 44C22 20 42 48 58 24" fill="none" stroke="{col}" stroke-width="6" stroke-linecap="round"></path>' + (f'<circle cx="32" cy="34" r="13" fill="{col}" stroke="{ink}" stroke-width="3"></circle><text x="32" y="41" text-anchor="middle" font-family="Inter" font-weight="700" font-size="20" fill="{ink}">{code}</text>' if code else ''))
        elif sh == 'area': o.append(f'<rect x="8" y="12" width="48" height="40" rx="6" fill="{col}" fill-opacity="0.35" stroke="{col}" stroke-width="4"></rect>')
    return ''.join(o)
def sym(i, fam, x, y, px, rot=0, state=None, col=None):
    """svg group of symbol i at (x, y), px wide. state: None, hover, sel, faint, stale"""
    s = S[i]; c = col or s['col']; op = ''
    if state == 'stale': c = '#8a949c'
    if state == 'faint': op = ' opacity="0.5"'
    body = els(s, fam, c)
    r = rot if (s['rot'] and fam != 'point') or (fam == 'point' and s['pt'][0] in ('chev', 'tri') and s['rot']) else 0
    if fam == 'badge' and r: body = body.replace('<g transform="translate(32 32) scale(0.58) translate(-32 -32)">', f'<g transform="translate(32 32) rotate({r:.0f}) scale(0.58) translate(-32 -32)">'); r = 0
    k = px/64
    g = f'<g transform="translate({x - px/2:.1f} {y - px/2:.1f}) scale({k:.4f})"{op}>' + (f'<g transform="rotate({r:.0f} 32 32)">' + body + '</g>' if r else body) + '</g>'
    ring = ''
    if state == 'hover': ring = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{px*0.62:.1f}" fill="none" stroke="#ffffff" stroke-opacity="0.75" stroke-width="1.5"></circle>'
    if state == 'sel':
        R = px*0.72
        ring = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="none" stroke="{P["ice"]}" stroke-width="2"></circle>'
                f'<path d="M{x-R-7:.1f} {y:.1f}h6M{x+R+1:.1f} {y:.1f}h6M{x:.1f} {y-R-7:.1f}v6M{x:.1f} {y+R+1:.1f}v6" stroke="{P["ice"]}" stroke-width="2"></path>')
    if state == 'stale': ring = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{px*0.66:.1f}" fill="none" stroke="#8a949c" stroke-width="1.4" stroke-dasharray="3 3"></circle>'
    return g + ring
def cell(i, fam, px=28, bg=None, rot=0, state=None):
    return f'<svg width="{px+12}" height="{px+12}" viewBox="0 0 {px+12} {px+12}" aria-hidden="true" style="display: block">{sym(i, fam, (px+12)/2, (px+12)/2, px, rot, state)}</svg>'
