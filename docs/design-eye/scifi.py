"""Sci-fi treatments of the icons2 silhouettes. Lines are hairlines at any size (non-scaling strokes)."""
import math, html
import icons2 as J
NS = ' vector-effect="non-scaling-stroke"'
DEFS = ('<svg width="0" height="0" style="position: absolute" aria-hidden="true"><defs>'
        '<filter id="holo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.6" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter>'
        '<pattern id="dots" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#8fdcff" fill-opacity="0.22"></circle></pattern>'
        '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity="0.18"></rect></pattern>'
        '</defs></svg>')
STYLES = ['solid', 'holo', 'etched', 'hair']
STYN = dict(solid='Today (solid, dark edge)', holo='Hologram: glass fill, bright hairline edge, glow', etched='Etched: solid, slim light edge, no dark outline', hair='Hairline: edge only, with corner ticks')
def body(i, style, col, acc, px):
    g = J.glyph(i, px); o = []
    if style == 'holo':
        for d, m in g:
            if m == 'f': o.append(f'<path d="{d}" fill="{col}" fill-opacity="0.26" stroke="{col}" stroke-width="1.1" stroke-linejoin="round"{NS}></path>')
            elif m == 'k': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-opacity="0.9" stroke-width="0.8"{NS}></path>')
            elif m == 's': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.3" stroke-linecap="round"{NS}></path>')
            elif m == 'd': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.1" stroke-dasharray="3 3"{NS}></path>')
            elif m == 'a': o.append(f'<path d="{d}" fill="{col}" fill-opacity="0.14" stroke="{col}" stroke-width="1"{NS}></path>')
            elif m == 'x': o.append(f'<path d="{d}" fill="{acc}"></path>')
        return '<g filter="url(#holo)">' + ''.join(o) + '</g>'
    if style == 'etched':
        for d, m in g:
            if m == 'f': o.append(f'<path d="{d}" fill="{col}" fill-opacity="0.82" stroke="#ffffff" stroke-opacity="0.75" stroke-width="0.7"{NS}></path>')
            elif m == 'k': o.append(f'<path d="{d}" fill="#0a1218" fill-opacity="0.85"></path>')
            elif m == 's': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" stroke-linecap="round"{NS}></path>')
            elif m == 'd': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.3" stroke-dasharray="3 3"{NS}></path>')
            elif m == 'a': o.append(f'<path d="{d}" fill="{col}" fill-opacity="0.3" stroke="{col}" stroke-width="0.8"{NS}></path>')
            elif m == 'x': o.append(f'<path d="{d}" fill="{acc}"></path>')
        return ''.join(o)
    if style == 'hair':
        for d, m in g:
            if m in ('f', 'a'): o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1" stroke-linejoin="round"{NS}></path>')
            elif m in ('k',): o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-opacity="0.6" stroke-width="0.7"{NS}></path>')
            elif m in ('s',): o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1"{NS}></path>')
            elif m == 'd': o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1" stroke-dasharray="3 3"{NS}></path>')
            elif m == 'x': o.append(f'<path d="{d}" fill="{acc}"></path>')
        t = 'M2 10V2H10M54 2H62V10M62 54V62H54M10 62H2V54'
        o.append(f'<path d="{t}" fill="none" stroke="{col}" stroke-opacity="0.55" stroke-width="0.8"{NS}></path>')
        return ''.join(o)
    return None
def draw(i, style, x, y, px, rot=0, pal='A', colkey=None):
    if style == 'solid': return J.draw(i, 'solid', x, y, px, rot, pal, 'dark', colkey=colkey)
    s = J.LIB[i]; col = J.PAL[pal]['dark'][colkey] if colkey else J.colour(i, pal)
    acc = {'sanctioned': 'clash', 'breaking': 'clash', 'quake_test': 'nuke', 'head': 'vip', 'camlive': 'ok'}.get(i)
    acc = J.PAL[pal]['dark'][acc] if acc else J.PAL[pal]['dark']['warn']
    b = body(i, style, col, acc, px); k = px/64; r = rot if s['rot'] else 0
    return f'<g transform="translate({x - px/2:.1f} {y - px/2:.1f}) scale({k:.4f})">' + (f'<g transform="rotate({r:.0f} 32 32)">{b}</g>' if r else b) + '</g>'
# ---------- components ----------
ROSE = '#ff3b5c'; ICE = '#8fdcff'
COND = "'Barlow Condensed', 'Arial Narrow', sans-serif"; MONO = "'IBM Plex Mono', ui-monospace, monospace"
def lock(x, y, r=26, col=ROSE):
    """selection: one thin hairline circle around the item (owner 2026-11-17: no arcs, ticks or brackets). Static."""
    return f'<circle cx="{x}" cy="{y}" r="{r*0.8:.1f}" fill="none" stroke="{col}" stroke-opacity="0.95" stroke-width="1.2"></circle>'
def callout(x, y, lines, dx=60, dy=-46, col=ICE, w=None):
    """leader line from the item to a caps label block; lines = [(text, size, colour, weight)]"""
    ex, ey = x + dx, y + dy; w = w or max(len(t) for t, *_ in lines)*7.4 + 20
    o = [f'<path d="M{x:.1f} {y:.1f}L{ex:.1f} {ey:.1f}H{ex + (w if dx > 0 else -w):.1f}" fill="none" stroke="{col}" stroke-opacity="0.8" stroke-width="0.9"></path>',
         f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{col}"></circle>']
    tx = ex + (6 if dx > 0 else -w + 6); ty = ey - 6
    for n, (t, sz, c, wt) in enumerate(lines):
        if n == 0: ty = ey - 5
        else: ty += sz + 4
        o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-family="{COND}" font-size="{sz}" font-weight="{wt}" letter-spacing="0.06em" fill="{c}">{html.escape(t)}</text>')
    return ''.join(o)
def segments(x, y, n, total=None, col=ROSE, w=7, h=9, gap=2):
    total = total or n
    return ''.join(f'<rect x="{x + k*(w + gap)}" y="{y}" width="{w}" height="{h}" fill="{col if k < n else "none"}" fill-opacity="{0.85 if k < n else 0}" stroke="{col}" stroke-opacity="0.6" stroke-width="0.8"></rect>' for k in range(total))
def frame(x, y, w, h, title='', meta='', col=ICE):
    """panel: thin border, bright corner brackets, caps header with a hairline under it"""
    q = 12
    br = f'M{x} {y+q}V{y}H{x+q}M{x+w-q} {y}H{x+w}V{y+q}M{x+w} {y+h-q}V{y+h}H{x+w-q}M{x+q} {y+h}H{x}V{y+h-q}'
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#04090e" fill-opacity="0.72" stroke="{col}" stroke-opacity="0.25" stroke-width="1"></rect>'
         f'<path d="{br}" fill="none" stroke="{col}" stroke-width="1.6"></path>')
    if title:
        s += (f'<text x="{x+14}" y="{y+22}" font-family="{COND}" font-size="14" font-weight="600" letter-spacing="0.14em" fill="{col}">{html.escape(title.upper())}</text>'
              f'<text x="{x+w-14}" y="{y+22}" text-anchor="end" font-family="{MONO}" font-size="10" fill="#9fb3bf">{html.escape(meta)}</text>'
              f'<path d="M{x+14} {y+31}H{x+w-14}" stroke="{col}" stroke-opacity="0.3" stroke-width="1"></path>')
    return s
def txt(x, y, s, size=12, col='#d7e6ee', font=None, wt=500, anchor='start', ls='0.04em', op=1):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{font or COND}" font-size="{size}" font-weight="{wt}" letter-spacing="{ls}" fill="{col}" fill-opacity="{op}">{html.escape(str(s))}</text>'
