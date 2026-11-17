"""Low-key families: frame (domain frame + code, after the idea of APP-6 / MIL-STD-2525 frames, domain only, no affiliation),
reticle (corner brackets + centre dot), scope (ATC-style small target + data block). Three colours only."""
import math, html
import icons as I
NEU, ROSE, WARN, ICE, INK = '#d7dde2', '#ff6b81', '#ffe066', '#8fdcff', '#05080c'
DOM = {}
CODE = dict(airliner='CIV', heavy='HVY', prop='PRP', heli='HEL', glider='GLD', balloon='BLN', drone='UAV', military='MIL', fighter='FTR', milheli='HEL', tanker='TKR', isr='ISR',
            vip='VIP', doomsday='C2', ground='GND', ship='SHP', warship='WAR', carrier='CVN', amphib='LHD', sanctioned='SAN', sat_leo='LEO', sat_meo='MEO', sat_geo='GEO',
            sat_heo='HEO', sat_spy='SPY', iss='ISS', launch='LCH', clash='CLH', attack='ATK', riot='RIO', mass='MAS', protest='PRT', occupied='', frontchange='Δ', unit='UNT',
            direction='', hotspot='HOT', news='NWS', breaking='BRK', leader='LDR', head='HOS', quake='5.4', quake_test='5.4', cyclone='CYC', flood='FLD', volcano='VOL',
            wildfire='WLD', fire='', lightning='', outage='IR', cfnote='CF', hijack='', leak='', cable='', cable_fault='', cable_fixed='', navwarn='NAV', airspace='ASP',
            tfr='TFR', base='BSE', sigint='SIG', radar='RDR', milarea='', nuke='NPP', nukesite='NUC', testsite='TST', camera='CAM', camlive='CAM', sdr='SW')
for k in I.S:
    g = I.S[k]['group']
    d = {'Air': 'air', 'Sea and space': 'sea'}.get(g, 'event')
    if k.startswith('sat') or k == 'iss': d = 'space'
    if k in ('ground', 'launch', 'frontchange', 'unit', 'base', 'sigint', 'radar', 'nuke', 'nukesite', 'camera', 'camlive', 'sdr'): d = 'land'
    if k in ('occupied', 'milarea'): d = 'area'
    if k in ('hijack', 'leak', 'cable', 'cable_fault', 'cable_fixed'): d = 'line'
    if k in ('outage', 'cfnote'): d = 'net'
    if k in ('navwarn', 'airspace', 'tfr'): d = 'warn'
    if k in ('fire', 'lightning'): d = 'point'
    if k == 'direction': d = 'arrow'
    if k in ('isr',): d = 'air'
    if k in ('testsite',): d = 'land'
    DOM[k] = d
ROSEK = {'clash', 'attack', 'riot', 'mass', 'occupied', 'unit', 'direction', 'hotspot', 'breaking', 'doomsday', 'sanctioned', 'sat_spy', 'hijack', 'cable_fault', 'sigint', 'testsite', 'quake_test'}
WARNK = {'navwarn', 'airspace', 'tfr'}
def colour(k): return ROSE if k in ROSEK else (WARN if k in WARNK else NEU)
FR = dict(air='M12 52V30A20 20 0 0 1 52 30V52', sea='M12 12V32A20 20 0 0 0 52 32V12', space='M12 52V32A20 20 0 0 1 52 32V52M20 6H44',
          land='M12 14H52V50H12Z', event=I.circ(32, 32, 21), net='M32 10L51 21V43L32 54 13 43V21Z', warn='M12 14H52V50H12Z')
MONO = "'IBM Plex Mono', ui-monospace, monospace"
def txt(x, y, s, size, col, anchor='middle', op=1):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO}" font-weight="500" font-size="{size}" fill="{col}" fill-opacity="{op}">{html.escape(s)}</text>'
def frame(k, col, sw=2.4):
    d = DOM[k]; c = CODE[k]; o = []
    if d in FR:
        dash = ' stroke-dasharray="5 4"' if d == 'warn' or k == 'protest' else ''
        o.append(f'<path d="{FR[d]}" fill="{INK}" fill-opacity="0.35" stroke="{col}" stroke-width="{sw}"{dash}></path>')
        if c: o.append(txt(32, 38, c, 15 if len(c) <= 2 else 13, col))
    elif d == 'area': o.append(f'<path d="M10 14H54V50H10Z" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-width="{sw*0.8}"></path><path d="M10 30L26 14M10 46L42 14M22 50L54 18M38 50L54 34" stroke="{col}" stroke-opacity="0.6" stroke-width="1.4"></path>')
    elif d == 'line':
        dash = ' stroke-dasharray="5 4"' if k in ('leak', 'cable_fixed') else ''
        o.append(f'<path d="M6 42C22 22 42 50 58 26" fill="none" stroke="{col}" stroke-width="{sw}"{dash}></path>')
        if k == 'cable_fault': o.append(f'<path d="M27 29l10 10M37 29l-10 10" stroke="{col}" stroke-width="{sw}"></path>')
        if k in ('hijack', 'leak'): o.append(f'<path d="M52 20l7 5-8 4" fill="none" stroke="{col}" stroke-width="{sw}"></path>')
    elif d == 'point': o.append(f'<circle cx="32" cy="32" r="5" fill="{col}"></circle>' if k == 'fire' else f'<path d="M34 18L26 33h7l-3 13 10-17h-7Z" fill="{col}"></path>')
    elif d == 'arrow': o.append(f'<path d="M10 32H50M40 22l11 10-11 10" fill="none" stroke="{col}" stroke-width="{sw}"></path>')
    return ''.join(o)
BR = dict(air='M14 24V14H24M40 14H50V24', sea='M14 40V50H24M40 50H50V40', space='M14 24V14H24M40 14H50V24M24 8H40',
          land='M14 24V14H24M40 14H50V24M14 40V50H24M40 50H50V40', warn='M14 24V14H24M40 14H50V24M14 40V50H24M40 50H50V40',
          event='M20 16A18 18 0 0 1 44 16M48 20A18 18 0 0 1 48 44M44 48A18 18 0 0 1 20 48M16 44A18 18 0 0 1 16 20',
          net='M32 12L48 21M48 43L32 52M16 43V21')
def reticle(k, col, rot=0, sw=2.4):
    d = DOM[k]; c = CODE[k]; o = []
    if d in BR:
        dash = ' stroke-dasharray="3 3"' if d == 'warn' else ''
        o.append(f'<path d="{BR[d]}" fill="none" stroke="{col}" stroke-width="{sw}"{dash}></path><circle cx="32" cy="32" r="3.2" fill="{col}"></circle>')
        if I.S[k]['rot']: o.append(f'<path d="M32 32V20" stroke="{col}" stroke-width="{sw}" transform="rotate({rot:.0f} 32 32)"></path>')
        if c: o.append(txt(32, 63, c, 12, col, op=0.85))
    else: o.append(frame(k, col, sw))
    return ''.join(o)
SC = dict(air='M27 27h10v10H27Z', sea='M32 26l6 10H26Z', space='M32 25v14M25 32h14', land='M28 28h8v8h-8Z', warn='M27 27h10v10H27Z', event=I.circ(32, 32, 5.5), net='M32 26l5 3v6l-5 3-5-3v-6Z')
def scope(k, col, rot=0, data=None, sw=2.2):
    d = DOM[k]; o = []
    if d in SC:
        fill = col if d in ('land',) else 'none'
        o.append(f'<path d="{SC[d]}" fill="{fill}" stroke="{col}" stroke-width="{sw}"></path>')
        if I.S[k]['rot']: o.append(f'<path d="M32 26V16" stroke="{col}" stroke-width="{sw}" transform="rotate({rot:.0f} 32 32)"></path>')
        lines = data if data is not None else [CODE[k] or I.S[k]['name'].split()[0].upper()]
        if lines:
            o.append(f'<path d="M37 27L48 16H54" fill="none" stroke="{col}" stroke-opacity="0.6" stroke-width="1.2"></path>')
            for n, s in enumerate(lines): o.append(txt(56, 18 + n*12, s, 11, col, 'start', 0.9 if n == 0 else 0.65))
    else: o.append(frame(k, col, sw))
    return ''.join(o)
LKF = ['frame', 'reticle', 'scope']
LKN = dict(frame='Frame and code', reticle='Reticle', scope='Scope and data block')
def lk(k, fam, x, y, px, rot=0, state=None, data=None):
    col = colour(k)
    if state == 'stale': col = '#7d868e'
    body = frame(k, col) if fam == 'frame' else (reticle(k, col, rot) if fam == 'reticle' else scope(k, col, rot, data))
    op = ' opacity="0.45"' if state == 'faint' else ''
    s = px/64
    g = f'<g transform="translate({x - px/2:.1f} {y - px/2:.1f}) scale({s:.4f})"{op}>{body}</g>'
    if state == 'sel':
        R = px*0.62
        g += f'<path d="M{x-R:.1f} {y-R+6:.1f}V{y-R:.1f}H{x-R+6:.1f}M{x+R-6:.1f} {y-R:.1f}H{x+R:.1f}V{y-R+6:.1f}M{x+R:.1f} {y+R-6:.1f}V{y+R:.1f}H{x+R-6:.1f}M{x-R+6:.1f} {y+R:.1f}H{x-R:.1f}V{y+R-6:.1f}" fill="none" stroke="{ICE}" stroke-width="1.6"></path>'
    if state == 'hover': g += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{px*0.58:.1f}" fill="none" stroke="#ffffff" stroke-opacity="0.5" stroke-width="1"></circle>'
    return g
