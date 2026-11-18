"""Every screen of the Dense layout in the God's eye glass look (owner's picks, 2026-11-18):
glass panels from the first God's eye boards (rounded, frosted), Space Grotesk headings and numbers, Inter text,
sentence case; solid 147-symbol set in palette C with an ice tint for military aircraft; one hairline selection ring.
Capture boards use the frozen capture (17 Nov 2026 10:01 UTC); the two dossier boards use live server data (18 Nov)."""
import sys, io, contextlib, json, math, html, datetime as dt
sys.argv = ['x', 'c1b03a33e5c17fad9269b2ef0f3a7f96']
with contextlib.redirect_stdout(io.StringIO()):
    from gen_icons2 import *
    from gen_scifi import NF, IMGS
import icons2 as J, scifi as S
E = html.escape
# military aircraft get their own pale ice tint (owner, 2026-11-18)
J.PAL['C']['dark']['mil'] = '#a9d8f2'; J.PAL['A']['dark']['mil'] = '#bfe6fb'
J.PAL['C']['light']['mil'] = '#2a6f9a'; J.PAL['A']['light']['mil'] = '#1f6a99'
PAL = 'C'
IMGX = dict(IMG); IMGX.update(NEW); IMGX.update(nearfull=IMGS['nearfull'], whole_grade=IMGS['whole'], theatre_grade=IMGS['theatre'])
SG = "font-family: 'Space Grotesk', sans-serif"
ROSE, ICE, YEL, RED, GRN = '#ff3b5c', '#8fdcff', '#ffe066', '#ff6b6b', '#7be0a0'
T = {'dark': dict(bg='rgba(10,14,18,0.66)', bd='rgba(255,255,255,0.14)', tx='#f2f4f6', mu='#c9d1d6', faint='rgba(255,255,255,0.08)', tile='rgba(255,255,255,0.06)',
                  acc=ICE, on='#f2f4f6', onx='#0a0e12', halo='#000000', page='#030303'),
     'light': dict(bg='rgba(250,252,253,0.78)', bd='rgba(10,30,50,0.12)', tx='#0b141b', mu='#4c5c68', faint='rgba(10,30,50,0.08)', tile='rgba(10,30,50,0.05)',
                   acc='#0a6d99', on='#0b141b', onx='#ffffff', halo='#ffffff', page='#e8edf1')}
th = T['dark']
def glass(): return f"background: {th['bg']}; border: 1px solid {th['bd']}; -webkit-backdrop-filter: blur(18px) saturate(140%); backdrop-filter: blur(18px) saturate(140%)"
def ago(t, now):
    s = now - t
    if s < 90: return f"{max(1, round(s))} s"
    if s < 5400: return f"{max(1, round(s/60))} min"
    if s < 172800: return f"{s/3600:.0f} h" if s >= 36000 else f"{s/3600:.1f} h"
    return f"{s/86400:.0f} d"
cap_age = lambda t: ago(t, CAP)

# ---------------- building blocks ----------------
def panel(x, y, w, h, inner, label, pad=16, gap=10, r=22, extra=''):
    return f'<section aria-label="{E(label)}" style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; box-sizing: border-box; padding: {pad}px; border-radius: {r}px; {glass()}; display: flex; flex-direction: column; gap: {gap}px; overflow: hidden; {extra}">{inner}</section>'
def hd(t, sub='', size=16, close=False):
    x = f'<span aria-hidden="true" style="width: 26px; height: 26px; flex: none; border-radius: 999px; background: {th["tile"]}; display: grid; place-items: center; color: {th["mu"]}; font-size: 15px">×</span>' if close else ''
    return f'<div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; min-height: 24px; flex: none"><span style="{SG}; font-weight: 600; font-size: {size}px; white-space: nowrap">{t}</span><span style="display: flex; gap: 10px; align-items: center; min-width: 0"><span style="font-size: 12px; color: {th["mu"]}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{sub}</span>{x}</span></div>'
def note(t, size=12): return f'<div style="font-size: {size}px; color: {th["mu"]}; line-height: 1.45; flex: none">{t}</div>'
def rule(): return f'<div style="height: 1px; flex: none; background: {th["faint"]}"></div>'
def num(v, size=22, col=None): return f'<span style="{SG}; font-weight: 600; font-size: {size}px; font-variant-numeric: tabular-nums; {"color: " + col if col else ""}">{v}</span>'
def chip(t, on=False, col=None):
    st = f"background: {th['on']}; color: {th['onx']}" if on else f"background: {th['tile']}; border: 1px solid {th['bd']}"
    return f'<span style="display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 12px; border-radius: 999px; {st}; {SG}; font-weight: 500; font-size: 13px; white-space: nowrap">{(f"<span style=width:8px;height:8px;border-radius:999px;background:{col}></span>" if col else "")}{t}</span>'
def btn(t, primary=False): return chip(t, primary)
def kv(k, v, w=None): return f'<div style="display: flex; flex-direction: column; gap: 2px; min-width: 0; {"width: " + str(w) + "px" if w else "flex: 1"}"><span style="font-size: 12px; color: {th["mu"]}">{k}</span>{num(v, 19) if not isinstance(v, tuple) else v[0]}</div>'
def icon(i, px=22, rot=0, ck=None, mode=None):
    md = mode or ('light' if th is T['light'] else 'dark')
    return f'<svg width="{px}" height="{px}" viewBox="0 0 {px} {px}" aria-hidden="true" style="flex: none">{J.draw(i, "solid", px/2, px/2, px*0.92, rot, PAL, md, colkey=ck)}</svg>'
STATE = {'ok': GRN, 'late': YEL, 'fail': RED, 'off': '#9aa3a9', 'wait': '#9aa3a9'}
def dot(state): return f'<span style="width: 8px; height: 8px; border-radius: 999px; flex: none; box-sizing: border-box; {"background: " + STATE[state] if state not in ("off", "wait") else "border: 1.5px dashed " + STATE[state]}"></span>'

# ---------------- map marks ----------------
def heading(proj, a):
    x, y, _ = proj(a['lon'], a['lat']); t = (a['track'] or 0)*math.pi/180
    x2, y2, _ = proj(a['lon'] + 0.2*math.sin(t)/max(0.2, math.cos(a['lat']*math.pi/180)), a['lat'] + 0.2*math.cos(t))
    return math.degrees(math.atan2(x2 - x, -(y2 - y)))
def lbl(x, y, t, anchor='start', size=12, wt=500, col=None):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{col or th["tx"]}" font-family="Inter, sans-serif" font-size="{size}" font-weight="{wt}" stroke="{th["halo"]}" stroke-opacity="0.65" stroke-width="3" paint-order="stroke">{E(t)}</text>'
def marks(proj, hide=(), sel=None, labels=True, kinds=('mil', 'unrest', 'front', 'leaders', 'quakes', 'launches', 'ships', 'outages'), mil_px=20, region=(0, 0, 1920, 1080)):
    """real items of the capture at their position in this camera; items under a panel are left out. Returns svg, positions"""
    out, pos = [], {}
    md = 'light' if th is T['light'] else 'dark'
    def ok(x, y): return region[0] < x < region[0] + region[2] and region[1] < y < region[1] + region[3] and not any(inr(x, y, h, -6) for h in hide)
    if 'mil' in kinds:
        for a in IT['mil']:
            x, y, v = proj(a['lon'], a['lat'])
            if not (v and ok(x, y)): continue
            c = acls(a)
            out.append(J.draw(c, 'solid', x, y, mil_px, heading(proj, a), PAL, md, colkey='mil'))
            pos[a['flight']] = (x, y, a, c)
            if labels and mil_px >= 24: out.append(lbl(x + mil_px*0.7, y + 4, a['flight'], size=12, wt=600))
    if 'front' in kinds:
        for c in FR['changes'][-8:]:
            x, y, v = proj(c['lon'], c['lat'])
            if v and ok(x, y): out.append(J.draw('frontchange', 'solid', x, y, 14, 0, PAL, md)); pos.setdefault('front', []).append((x, y, c))
    if 'unrest' in kinds:
        for u in IT['unrest']:
            x, y, v = proj(u['lon'], u['lat'])
            if not (v and ok(x, y)): continue
            px = 18 + min(u['outlets'], 12)*1.3
            out.append(J.draw(uncls(u), 'solid', x, y, px, 0, PAL, md))
            pos['u:' + u['place']] = (x, y, u)
            if labels: out.append(lbl(x - px*0.6, y - px*0.55, f"{u['place']} · {u['outlets']}", 'end', 12, 600))
    if 'leaders' in kinds:
        for l in IT['leaders']:
            x, y, v = proj(l['lon'], l['lat'])
            if v and ok(x, y):
                out.append(J.draw('leader', 'solid', x, y, 16, 0, PAL, md))
                if labels: out.append(lbl(x + 11, y + 4, l['name'], size=12))
    if 'quakes' in kinds:
        for q in IT['quakes']:
            x, y, v = proj(q['lon'], q['lat'])
            if v and ok(x, y): out.append(J.draw('quake_l' if q['mag'] >= 6 else 'quake_m', 'solid', x, y, 14 + (q['mag'] - 4.5)*6, 0, PAL, md))
    if 'launches' in kinds:
        for l in IT['launches']:
            x, y, v = proj(l['lon'], l['lat'])
            if v and ok(x, y): out.append(J.draw('launch', 'solid', x, y, 20, 0, PAL, md))
    if 'ships' in kinds:
        seen = {}
        for s in IT['ships']:
            x, y, v = proj(s['lon'], s['lat'])
            if not (v and ok(x, y)): continue
            k = (round(x), round(y)); n = seen[k] = seen.get(k, 0) + 1
            y += (n - 1)*30
            out.append(J.draw('carrier' if s['hull'].startswith('CVN') else 'amphib', 'solid', x, y, 24, 0, PAL, md))
            pos['s:' + s['name']] = (x, y, s)
            if labels: out.append(lbl(x + 16, y + 4, s['name'].replace('USS ', '') + f" ({s['hull']})", 'start', 11, 500))
    if 'outages' in kinds:
        for o in IT['outages']:
            x, y, v = proj(o['lon'], o['lat'])
            if v and ok(x, y): out.append(J.draw('outage', 'solid', x, y, 20, 0, PAL, md)) or None; pos['o:' + o['code']] = (x, y, o)
    return ''.join(out), pos
def occupied(proj, step=24):
    s = []
    for a in FR['areas']:
        for ring in a['rings']:
            pts = [proj(lo, la) for lo, la in ring[::max(1, len(ring)//step)]]
            if len(pts) > 2 and all(p[2] for p in pts):
                d = 'M' + ' L'.join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts) + ' Z'
                s.append(f'<path d="{d}" fill="{ROSE}" fill-opacity="{0.24 if a.get("kind") == "occupied" else 0.12}" stroke="{ROSE}" stroke-opacity="0.8" stroke-width="1"></path>')
    return ''.join(s)
def svg(inner, label): return f'<svg width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-label="{E(label)}" style="position: absolute; left: 0; top: 0">{inner}</svg>'

# ---------------- the Dense frame ----------------
COL = (1400, 76, 504, 988)        # the column
STRIP = (16, 948, 1368, 116)      # view pictures
VIEWS = [('whole', 'Whole Earth'), ('theatre', 'Theatre'), ('dusk', 'Day and night'), ('sides', 'Two sides'), ('wall', 'Wall of four'), ('front', 'Look down'), ('polar', 'Over the pole'), ('low', 'Low orbit'), ('chase', 'Chase')]
def top(view, stamp='Frozen capture 17 Nov 2026, 10:01 UTC', feeds='40 of 45 feeds current · 1 late · 1 failing · 3 not set up', q=''):
    srch = (f'<div style="position: absolute; left: 520px; top: 14px; width: 560px; height: 48px; box-sizing: border-box; border-radius: 999px; {glass()}; display: flex; align-items: center; gap: 10px; padding: 0 18px; color: {th["mu"]}; font-size: 14px">'
            f'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-4-4"></path></svg>'
            f'{E(q) if q else "Find a place, a person, or anything on the map"}<span style="margin-left: auto; font-size: 12px; border: 1px solid {th["bd"]}; border-radius: 6px; padding: 1px 6px">/</span></div>')
    gear = f'<span aria-label="Settings" style="width: 48px; height: 48px; border-radius: 999px; {glass()}; display: grid; place-items: center; color: {th["tx"]}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="3.2"></circle><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"></path></svg></span>'
    fd = f'<span style="height: 48px; display: flex; align-items: center; gap: 8px; padding: 0 16px; border-radius: 999px; {glass()}; font-size: 13px">{dot("late") if "late" in feeds else dot("ok")}{E(feeds)}</span>' if feeds else ''
    return (f'<div style="position: absolute; left: 24px; top: 12px"><div style="display: flex; align-items: baseline; gap: 12px"><span style="{SG}; font-weight: 700; font-size: 22px; letter-spacing: -0.01em">World Watch</span><span style="{SG}; font-weight: 500; font-size: 15px; color: {th["acc"]}">{E(view)}</span></div><div style="color: {th["mu"]}; font-size: 12px">{E(stamp)}</div></div>'
            + srch + f'<div style="position: absolute; right: 16px; top: 14px; display: flex; gap: 8px">{fd}{gear}</div>')
def strip(cur, note_=''):
    its = ''
    for k, n in VIEWS:
        on = k == cur
        its += (f'<a href="#{k}" aria-current="{"true" if on else "false"}" style="display: flex; flex-direction: column; gap: 4px; text-decoration: none; color: {th["tx"] if on else th["mu"]}; font-size: 12px; font-weight: {600 if on else 400}">'
                f'<img src="/_blob/{IMGX[k]}" alt="" style="width: 132px; height: 70px; object-fit: cover; border-radius: 12px; border: {"2px solid " + th["acc"] if on else "1px solid " + th["bd"]}; box-sizing: border-box; display: block">{n}</a>')
    return f'<nav aria-label="Views of the globe" style="position: absolute; left: {STRIP[0]}px; top: {STRIP[1]}px; width: {STRIP[2]}px; height: {STRIP[3]}px; box-sizing: border-box; padding: 12px 14px; border-radius: 22px; {glass()}; display: flex; gap: 12px; overflow: hidden">{its}</nav>'
def zoom(x=1334, y=760):
    b = lambda t: f'<span style="width: 44px; height: 44px; display: grid; place-items: center; font-size: 20px">{t}</span>'
    return f'<div aria-label="Zoom and compass" style="position: absolute; left: {x}px; top: {y}px; width: 46px; border-radius: 16px; {glass()}; display: flex; flex-direction: column; align-items: center">{b("+")}{b("−")}{b("<svg width=14 height=18 viewBox=\'0 0 14 18\' aria-hidden=true><path d=\'M7 0 L13 18 L7 13 L1 18 Z\' fill=\'#ff6b6b\'></path></svg>")}</div>'
def keyrow(items, x=24, y=900):
    return (f'<div aria-label="What the symbols in view mean" style="position: absolute; left: {x}px; top: {y}px; height: 36px; box-sizing: border-box; padding: 0 14px; border-radius: 999px; {glass()}; display: flex; align-items: center; gap: 16px; font-size: 12px; color: {th["mu"]}">'
            + ''.join(f'<span style="display: flex; gap: 6px; align-items: center; white-space: nowrap">{icon(i, 18, ck=ck)}{E(t)}</span>' for i, t, ck in items) + '<span>· tap a symbol for its source and age</span></div>')

# ---------------- column contents ----------------
TILES = [('mil_generic', 'Military aircraft', '120', 'adsb.fi', '12 s', 'ok', 'mil'), ('clash', 'Protests and clashes', '14', 'GDELT', '1 min', 'ok', None),
         ('leader', 'Leaders in the news', '17', 'GDELT', '57 min', 'ok', None), ('frontchange', 'Front changes, 7 d', '8', 'DeepState', '1 d', 'ok', None),
         ('quake_m', 'Earthquakes, 24 h', '168', 'USGS', '1 min', 'ok', None), ('outage', 'Internet outages', '5', 'IODA', '22 s', 'ok', None),
         ('carrier', 'US carriers, amphibs', '8', 'USNI', '22 d late', 'late', None), ('launch', 'Launches listed', '20', 'LL2', '43 s', 'ok', None),
         ('nw_weapons', 'Navy warnings', '1', 'UKHO', '40 s', 'ok', None), ('hotspot', 'Hotspots', '0', 'our rule', 'none now', 'ok', None)]
def tile(i, label, cnt, src, age_, state, ck, h=64):
    return (f'<div style="height: {h}px; box-sizing: border-box; padding: 8px 10px; border-radius: 14px; background: {th["tile"]}; border: 1px {"solid" if state in ("ok",) else "solid"} {th["bd"] if state == "ok" else STATE[state] + "99"}; display: flex; gap: 10px; align-items: center">'
            f'{icon(i, 26, ck=ck)}<div style="flex: 1; min-width: 0"><div style="font-size: 12px; color: {th["mu"]}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(label)}</div>{num(cnt, 20)}</div>'
            f'<div style="display: flex; flex-direction: column; align-items: flex-end; gap: 3px; font-size: 11px; color: {th["mu"] if state == "ok" else STATE[state]}; white-space: nowrap">{dot(state)}<span>{E(src)}</span><span>{E(age_)}</span></div></div>')
def tiles(n=10, cols=2):
    return f'<div style="display: grid; grid-template-columns: repeat({cols}, minmax(0, 1fr)); gap: 8px">' + ''.join(tile(*t) for t in TILES[:n]) + '</div>'
UN = sorted(IT['unrest'], key=lambda u: -u['outlets'])
def segs(n, total=12, col=ROSE): return '<span style="display: inline-flex; gap: 2px">' + ''.join(f'<span style="width: 7px; height: 7px; border-radius: 2px; background: {col if k < n else "transparent"}; border: 1px solid {col}; opacity: {1 if k < n else 0.45}"></span>' for k in range(total)) + '</span>'
def signal_rows(n=7, sel=None):
    o = ''
    for u in UN[:n]:
        on = sel and u['place'] == sel
        o += (f'<div style="display: flex; gap: 10px; align-items: flex-start; padding: 8px 8px; border-radius: 12px; {"background: " + th["tile"] + "; box-shadow: inset 0 0 0 1px " + ROSE if on else ""}">{icon(uncls(u), 24)}'
              f'<div style="flex: 1; min-width: 0"><div style="display: flex; justify-content: space-between; gap: 8px"><span style="{SG}; font-weight: 600; font-size: 15px">{E(u["place"])}</span><span style="font-size: 12px; color: {th["mu"]}; white-space: nowrap">{cap_age(u["last"])}</span></div>'
              f'<div style="font-size: 12px; color: {th["mu"]}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(u["cat"].capitalize())} · {E(u["action"])}</div>'
              f'<div style="display: flex; gap: 8px; align-items: center; margin-top: 4px">{segs(min(u["outlets"], 12))}<span style="font-size: 11px; color: {th["mu"]}">{u["outlets"]} outlets</span></div></div></div>')
    return o
def signals_panel(x, y, w, h, n=7, sel=None):
    return panel(x, y, w, h, hd('Signals', 'protests and clashes, 2+ outlets') + note('GDELT, machine-coded from news, not verified. Newest report first within the strongest.') + f'<div style="display: flex; flex-direction: column; gap: 2px; overflow: hidden">{signal_rows(n, sel)}</div>', 'Signals')
def layers_panel(x, y, w, h, n=10):
    return panel(x, y, w, h, hd('Layers', '14 of 40 on · all layers →') + tiles(n) + note('Dot: green current, yellow late, red failing, dashed needs a key. Each tile switches its layer; the arrow opens every layer with its key.'), 'Layers')

# ---------------- page ----------------
OUT_B = []
def page(name, title, img, body, alt, desc):
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{E(title)}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap">
<style>
body{{margin:0}}
a{{color:{th["tx"]}}}a:hover{{color:{th["acc"]}}}
</style>
</helmet>
<div style="position: relative; width: 1920px; height: 1080px; overflow: hidden; background: {th["page"]}; color: {th["tx"]}; font-family: Inter, system-ui, sans-serif; font-size: 13px; line-height: 1.4">
{f'<img src="/_blob/{IMGX[img]}" alt="{E(alt)}" style="position: absolute; left: 0; top: 0; width: 1920px; height: 1080px">' if img else ''}
<svg width="0" height="0" style="position: absolute">{J.DEFS2}</svg>
{body}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1920,"height":1080}}}}'>
class Component extends DCLogic {{
renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>'''
    open(OUT + name, 'w').write(doc); OUT_B.append((name, desc)); print(name, len(doc))

cth = V['theatre']['cams'][0][0]
HIDE = [(COL[0], COL[1], COL[2], COL[3]), STRIP, (0, 0, 1920, 70), (16, 890, 1100, 50), (1330, 750, 60, 160)]
KEY = [('clash', 'Clash', None), ('protest', 'Protest', None), ('mil_generic', 'Military aircraft', 'mil'), ('frontchange', 'Front change', None), ('leader', 'Leader', None), ('outage', 'Outage', None)]

# 1 overview
m, P = marks(cth.proj, HIDE)
body = svg(m, 'Real items of the capture in the theatre view') + top('Theatre') + signals_panel(1400, 76, 504, 520, 5) + layers_panel(1400, 608, 504, 456, 8) + strip('theatre') + zoom() + keyrow(KEY)
page('D01Overview.dc.html', 'Dense: overview', 'theatre', body, 'Europe and the Black Sea from 2,100 km, NASA Blue Marble', '1 Overview: signals and layer tiles in the column, view pictures below')

# 2 clash selected (Kyiv)
ku = [u for u in IT['unrest'] if u['place'] == 'Kyiv'][0]
x, y, _ = cth.proj(ku['lon'], ku['lat'])
card = (hd('Armed clash, Kyiv', 'selected', 18, True) + note('GDELT coded news reports as "use of conventional military force". Machine-coded, not verified.')
        + f'<div style="display: flex; gap: 12px">{kv("Outlets", str(ku["outlets"]))}{kv("Last report", cap_age(ku["last"]))}{kv("Country", "Ukraine")}</div>'
        + f'<div style="display: flex; gap: 8px; align-items: center">{segs(min(ku["outlets"], 12))}<span style="font-size: 12px; color: {th["mu"]}">{ku["outlets"]} different outlets wrote about it today</span></div>'
        + f'<div style="display: flex; gap: 8px; flex-wrap: wrap">{btn("Spy passes")}{btn("Imaged from orbit")}{btn("Country dossier")}{btn("Satellite picture")}</div>' + rule()
        + hd('Reports', 'headline per outlet', 14) + note('Each outlet\'s own headline and picture appear here, newest first, with "machine-translated" under any translated one. The capture kept counts only, so this board shows no headlines.')
        + rule() + note('Source: GDELT 2.0 events, 15-minute files, last 24 h · this group: place + kind + UTC day'))
body = svg(m + S.lock(x, y, 26), 'Theatre view, Kyiv selected') + top('Theatre') + panel(1400, 76, 504, 470, card, 'Selected') + signals_panel(1400, 558, 504, 506, 5, 'Kyiv') + strip('theatre') + zoom() + keyrow(KEY)
page('D02Clash.dc.html', 'Dense: event selected', 'theatre', body, 'Europe and the Black Sea, Kyiv selected', '2 An event selected: its card takes the top of the column, signals move below')

# 3 aircraft selected (near view)
HIDE3 = [(COL[0], COL[1], COL[2], COL[3]), STRIP, (0, 0, 1920, 70), (1330, 750, 60, 160)]
m3, P3 = marks(NF.proj, HIDE3, kinds=('mil',), mil_px=30)
fx, fy, a, cls = P3['RCH4992']
fl = lambda a: ('FL%03d' % round(a['alt']/100)) if isinstance(a['alt'], (int, float)) else 'on the ground'
card = (hd('RCH4992', 'military · selected', 22, True) + note(f'{J.LIB[cls]["name"]} · type code {a.get("type")} · registration {a.get("reg")} · {a["hex"].upper()}')
        + f'<div style="height: 180px; flex: none; border-radius: 14px; border: 1px dashed {th["bd"]}; display: grid; place-items: center; color: {th["mu"]}; font-size: 12px; text-align: center">Photo from planespotters.net loads here,<br>with the photographer\'s name and a link</div>'
        + f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px">{kv("Altitude", fl(a))}{kv("Ground speed", str(round(a["gs"])) + " kt")}{kv("Track", "%03d°" % round(a["track"]))}{kv("Last report", str(round(a.get("seen") or 0)) + " s ago")}{kv("Position", ("<span style=\"font-size: 15px; font-weight: 600\">%.2f N %.2f E</span>" % (a["lat"], a["lon"]),))}{kv("Registered in", "United States")}</div>'
        + f'<div style="display: flex; gap: 8px; flex-wrap: wrap">{btn("Follow", True)}{btn("Path flown")}{btn("Look from above")}</div>' + rule()
        + note('No published route: military aircraft file none. The path drawn is the one the feeds reported. Drawn 40 s behind real time between real reports.')
        + note('Sources: adsb.fi military feed (30 s), aircraft register via adsbdb / hexdb.io'))
inv = sorted([v for k, v in P3.items()], key=lambda t: t[2]['flight'])
lst = ''.join(f'<div style="display: flex; gap: 10px; align-items: center; height: 30px; border-top: 1px solid {th["faint"]}; {"color: " + ROSE if t[2]["flight"] == "RCH4992" else ""}">{icon(t[3], 20, ck="mil")}<span style="{SG}; font-weight: 600; width: 84px">{E(t[2]["flight"])}</span><span style="flex: 1; color: {th["mu"]}; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(J.LIB[t[3]]["name"].split("(")[0].split(",")[0])}</span><span style="{SG}; font-variant-numeric: tabular-nums">{fl(t[2])}</span></div>' for t in inv)
body = (svg(m3 + S.lock(fx, fy, 30), 'Military aircraft over northern Germany') + top('Close: northern Germany') + panel(1400, 76, 504, 640, card, 'Selected aircraft')
        + panel(1400, 728, 504, 336, hd('In view', f'{len(inv)} military aircraft') + f'<div style="overflow: hidden">{lst}</div>', 'In view') + strip('', ) + zoom())
page('D03Aircraft.dc.html', 'Dense: aircraft selected', 'nearfull', body, 'Northern Germany from 640 km, graded', '3 An aircraft selected (close view): card with photo, numbers and Follow; "in view" list below')

# 4 carriers (whole Earth)
cw = V['whole']['cams'][0][0]
HIDE4 = [(COL[0], COL[1], COL[2], COL[3]), STRIP, (0, 0, 1920, 70)]
m4, P4 = marks(cw.proj, HIDE4, kinds=('ships', 'unrest', 'outages', 'launches'), labels=True)
fleet = json.load(open('../dd/usni_fleet.json'))['payload']
gw = [s for s in fleet['ships'] if s['hull'] == 'CVN-73'][0]
gx, gy, _ = P4['s:USS George Washington']
pub = dt.datetime.fromtimestamp(fleet['published'], dt.timezone.utc) if isinstance(fleet['published'], (int, float)) else None
card = (hd('USS George Washington', 'US carrier · selected', 20, True) + note(f'{E(gw["hull"])} · {E(gw["kind"])} · placed by region: {E(gw["region"])} (approximate; the ring is 400 km)')
        + f'<div style="padding: 10px 12px; border-radius: 14px; background: {th["tile"]}; font-size: 14px; line-height: 1.5">' + ''.join(f'"{E(t)}"<br>' for t in gw['said']) + f'<span style="font-size: 12px; color: {th["mu"]}">USNI News Fleet and Marine Tracker</span></div>'
        + f'<div style="display: flex; gap: 12px">{kv("Tracker edition", "19 Oct")}{kv("Age", "29 d")}{kv("Placed", "region")}</div>'
        + f'<div style="display: flex; gap: 8px; align-items: center; padding: 8px 12px; border-radius: 12px; border: 1px solid {YEL}99; color: {YEL}; font-size: 13px">{dot("late")}USNI has not published since 19 Oct. This position is that old.</div>'
        + f'<div style="display: flex; gap: 8px; flex-wrap: wrap">{btn("Ship photo")}{btn("USNI map graphic")}{btn("Spy passes")}</div>'
        + note('Carriers do not broadcast AIS. No free current picture of a warship exists.'))
lst = ''.join(f'<div style="display: flex; gap: 10px; align-items: center; height: 34px; border-top: 1px solid {th["faint"]}">{icon("carrier" if s["hull"].startswith("CVN") else "amphib", 22)}<span style="{SG}; font-weight: 600; flex: 1">{E(s["name"].replace("USS ", ""))} <span style="color: {th["mu"]}; font-weight: 400">{E(s["hull"])}</span></span><span style="font-size: 12px; color: {th["mu"]}">{E(s["port"] or s["region"])}</span></div>' for s in fleet['ships'])
body = (svg(m4 + S.lock(gx, gy, 22), 'Whole Earth with US carriers and amphibs') + top('Whole Earth') + panel(1400, 76, 504, 500, card, 'Selected ship')
        + panel(1400, 588, 504, 476, hd('US carriers and amphibs', '8 · USNI, 19 Oct') + f'<div style="overflow: hidden">{lst}</div>', 'Fleet list') + strip('whole') + zoom())
page('D04Carrier.dc.html', 'Dense: ship selected', 'whole_grade', body, 'Whole Earth from 35,786 km, graded', '4 A carrier selected (whole Earth): the quoted USNI sentence, the late-feed warning, the fleet list')

# 5 layers with key
GROUPS = [('Conflict', [('clash', 'Protests and clashes', '14', 'ok', 'GDELT · 1 min', True), ('frontchange', 'Front line, Ukraine', '8', 'ok', 'DeepState · 1 d', True), ('hotspot', 'Hotspots', '0', 'ok', 'our rule · none now', True), ('breaking', 'Breaking news', '', 'ok', 'GDELT', False)]),
          ('Air', [('mil_generic', 'Military aircraft', '120', 'ok', 'adsb.fi · 12 s', True), ('narrow', 'All aircraft', '', 'ok', 'adsb.fi, OpenSky', False), ('vip', 'Government and VIP jets', '', 'ok', 'plane-alert-db', False), ('doomsday', 'Doomsday planes', '', 'ok', 'plane-alert-db', False), ('tanker', 'Tankers and orbits', '', 'ok', 'own trails', False), ('as_avoid', 'Airspace warnings', '', 'wait', 'EASA, FAA', False)]),
          ('Sea', [('carrier', 'US carriers, amphibs', '8', 'late', 'USNI · 22 d late', True), ('cargo', 'Ships', '', 'off', 'needs aisstream key', False), ('nw_weapons', 'Navy warnings', '1', 'ok', 'UKHO · 40 s', True), ('sanctioned', 'Sanctioned ships, aircraft', '', 'ok', 'OpenSanctions', False)]),
          ('Space', [('sat_spy', 'Satellites', '', 'ok', 'CelesTrak', False), ('launch', 'Launches', '20', 'ok', 'Launch Library 2 · 43 s', True)]),
          ('Networks', [('outage', 'Internet outages', '5', 'ok', 'IODA · 22 s', True), ('hijack', 'Internet hijacks', '', 'off', 'needs Cloudflare token', False), ('cable_fault', 'Undersea cables', '', 'ok', 'TeleGeography', False), ('gps', 'GPS interference', '', 'ok', 'GPSJAM', False)]),
          ('Earth', [('quake_m', 'Earthquakes', '168', 'ok', 'USGS · 1 min', True), ('cyclone', 'Disasters', '', 'ok', 'GDACS, EONET', False), ('fire', 'Fires', '', 'ok', 'NASA FIRMS', False)]),
          ('Sites', [('airbase', 'Military bases', '', 'ok', 'Wikidata, OSM, DoD', False), ('nuke', 'Nuclear sites', '', 'ok', 'GEM, Wikidata', False), ('camera', 'Public cameras', '', 'ok', 'TfL, NYC, Caltrans ...', False), ('sdr', 'Listening stations', '', 'ok', 'KiwiSDR', False)]),
          ('People', [('leader', 'Leaders in the news', '17', 'ok', 'GDELT · 57 min', True), ('head', 'Heads of state', '', 'ok', 'Wikidata', False)])]
def lrow(i, t, cnt, st, src, on):
    sw = f'<span style="width: 34px; height: 20px; flex: none; border-radius: 999px; background: {GRN if on else th["tile"]}; border: 1px solid {th["bd"]}; position: relative"><span style="position: absolute; top: 2px; {"right" if on else "left"}: 2px; width: 14px; height: 14px; border-radius: 999px; background: #ffffff"></span></span>'
    return (f'<div style="display: flex; gap: 10px; align-items: center; height: 36px; border-top: 1px solid {th["faint"]}; {"" if on else "opacity: 0.78"}">{icon(i, 22, ck="mil" if i == "mil_generic" else None)}'
            f'<span style="flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(t)}</span>{num(cnt, 14) if on else ""}'
            f'<span style="width: 150px; display: flex; gap: 6px; align-items: center; justify-content: flex-end; font-size: 11px; color: {th["mu"] if st == "ok" else STATE[st]}; white-space: nowrap">{dot(st)}{E(src)}</span>{sw}</div>')
colA = ''.join(f'<div style="{SG}; font-weight: 600; font-size: 13px; color: {th["acc"]}; margin-top: 6px">{g}</div>' + ''.join(lrow(*r) for r in rows) for g, rows in GROUPS[:4])
colB = ''.join(f'<div style="{SG}; font-weight: 600; font-size: 13px; color: {th["acc"]}; margin-top: 6px">{g}</div>' + ''.join(lrow(*r) for r in rows) for g, rows in GROUPS[4:])
keyb = (hd('Key for what is on', 'same symbols as the map', 14) + '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; font-size: 12px">'
        + ''.join(f'<span style="display: flex; gap: 8px; align-items: center">{icon(i, 20, ck=ck)}{E(t)}</span>' for i, t, ck in [('clash', 'Armed clash', None), ('smallarms', 'Small arms', None), ('artillery', 'Artillery', None), ('aerial', 'Air strike, drone', None), ('attack', 'Attack', None), ('protest', 'Protest', None), ('frontchange', 'Front change', None), ('mil_generic', 'Military, other type', 'mil'), ('fighter', 'Fighter', 'mil'), ('tanker', 'Tanker', 'mil'), ('strategic', 'Strategic airlifter', 'mil'), ('carrier', 'Carrier', None), ('amphib', 'Amphib', None), ('nw_weapons', 'Weapons firing', None), ('launch', 'Launch pad', None), ('outage', 'Outage', None), ('quake_m', 'Quake M4.5+', None), ('leader', 'Leader, placed by news', None)])
        + '</div>' + note('Size of an event symbol = number of different outlets. Faded = only one outlet. Grey dashed = last known position of a feed that stopped.'))
body = (svg(marks(cth.proj, [(560, 76, 1360, 1004), (0, 0, 1920, 70)])[0], 'Theatre view behind the layers panel') + top('Theatre')
        + panel(560, 76, 1344, 760, hd('All layers', '14 of 40 on · counts only for layers that are on', 18, True) + f'<div style="display: flex; gap: 22px; min-height: 0"><div style="flex: 1; min-width: 0">{colA}</div><div style="flex: 1; min-width: 0">{colB}</div><div style="width: 360px; flex: none; display: flex; flex-direction: column; gap: 10px">{keyb}</div></div>', 'All layers'))
page('D05Layers.dc.html', 'Dense: all layers and key', 'theatre', body, 'Theatre view behind the panel', '5 All layers: grouped, switch per layer, source and feed state per row, the key beside')

# 6 search
SR = [('Countries', [(None, 'Ukraine', 'Country dossier · travel advice level 4 (US) · 3 protests and clashes now', True)]),
      ('On the map now', [('clash', 'Kyiv: armed clash', f'7 outlets · {cap_age(ku["last"])} · GDELT'), ('leader', 'Volodymyr Zelenskyy, reported in Kyiv', 'leaders in the news · GDELT'), ('as_avoid', 'Airspace of Ukraine: avoid', 'EASA CZIB-2022-01R14 · FIR Kyiv and five more')]),
      ('People', [('head', 'Volodymyr Zelenskyy', 'Head of state of Ukraine since 20 May 2019 · Wikidata')])]
res = ''
for g, rows in SR:
    res += f'<div style="font-size: 12px; color: {th["mu"]}; margin: 8px 4px 2px">{g}</div>'
    for r in rows:
        i, t, s = r[:3]; on = len(r) > 3
        res += (f'<div style="display: flex; gap: 12px; align-items: center; padding: 10px 12px; border-radius: 14px; {"background: " + th["tile"] + "; box-shadow: inset 0 0 0 1px " + th["acc"] if on else ""}">'
                + (icon(i, 24) if i else f'<span style="width: 24px; height: 17px; flex: none; border-radius: 3px; background: linear-gradient({ICE} 50%, {YEL} 50%)"></span>')
                + f'<div style="flex: 1; min-width: 0"><div style="{SG}; font-weight: 600; font-size: 15px">{E(t)}</div><div style="font-size: 12px; color: {th["mu"]}">{E(s)}</div></div>{"<span style=font-size:12px;color:" + th["mu"] + ">return ↵</span>" if on else ""}</div>')
body = (svg(m, 'Theatre view') + f'<div style="position: absolute; inset: 0; background: rgba(0,0,0,0.35)"></div>' + top('Theatre', q='kyiv')
        + panel(520, 70, 560, 600, res + note('Countries answer at once (local list). Items on the map search every layer that is on. People come from Wikidata and arrive a moment later.'), 'Search results', pad=12, gap=4))
page('D06Search.dc.html', 'Dense: search', 'theatre', body, 'Theatre view dimmed behind search', '6 Search: countries, items on the map now, people from Wikidata')

# 7 settings
gtile = lambda k, t, s, on=False: (f'<div style="display: flex; flex-direction: column; gap: 6px; padding: 8px; border-radius: 16px; {"box-shadow: inset 0 0 0 2px " + th["acc"] if on else "border: 1px solid " + th["bd"]}">'
                                    + (f'<img src="/_blob/{IMGX[k]}" alt="" style="width: 100%; height: 92px; object-fit: cover; border-radius: 10px">' if k else f'<div style="height: 92px; border-radius: 10px; background: {s}"></div>')
                                    + f'<span style="{SG}; font-weight: 600; font-size: 14px">{t}</span></div>')
setb = (hd('Settings', '', 20, True)
        + f'<div style="{SG}; font-weight: 600">Theme</div><div style="display: flex; gap: 8px">{chip("God\'s eye", True)}{chip("Apple Maps")}</div>' + note('Light and dark follow your Mac in both themes.') + rule()
        + f'<div style="{SG}; font-weight: 600">Ground</div><div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px">'
        + gtile('theatre_grade', 'Photo, graded', '', True) + gtile('horizon_mono', 'Mono', '') + gtile('whole_lights', 'Night lights', '') + gtile('theatre_outline', 'Outline', '') + gtile(None, 'Map', 'linear-gradient(135deg, #1b2630, #121a21)') + gtile(None, 'Relief', 'linear-gradient(135deg, #3a4a58, #0d151c)') + '</div>'
        + note('Photo: NASA Blue Marble zoomed out, Esri World Imagery closer in (each area from its own date). Night lights: NASA Black Marble 2016, not tonight.') + rule()
        + f'<div style="display: flex; gap: 28px"><div style="flex: 1"><div style="{SG}; font-weight: 600; margin-bottom: 8px">Symbol colours</div><div style="display: flex; gap: 8px">{chip("C, muted", True)}{chip("A, per domain")}</div></div>'
        + f'<div style="flex: 1"><div style="{SG}; font-weight: 600; margin-bottom: 8px">Panel motion</div><div style="display: flex; gap: 8px">{chip("Off")}{chip("Subtle", True)}{chip("Full")}</div></div></div>'
        + note('Only panel text may move. Map symbols and their labels never move. Off when macOS Reduce Motion is on.') + rule()
        + f'<div style="{SG}; font-weight: 600">Keys</div>' + ''.join(f'<div style="display: flex; gap: 10px; align-items: center; font-size: 13px">{dot(s)}<span style="flex: 1">{E(n)}</span><span style="color: {th["mu"]}; font-size: 12px">{E(v)}</span></div>' for n, s, v in [('aisstream.io (ships worldwide)', 'off', 'not set up: data/aisstream-key.txt'), ('Cloudflare Radar (hijacks, outage notes)', 'off', 'not set up: data/cloudflare-token.txt'), ('Windy (webcams)', 'off', 'not set up: data/windy-key.txt'), ('OpenSanctions (sanctions lists)', 'off', 'not set up: data/opensanctions-key.txt')])
        + note('This board shows the sandbox, which has no keys; on your Mac the rows you set up are green.'))
body = svg(m, 'Theatre view') + f'<div style="position: absolute; inset: 0; background: rgba(0,0,0,0.4)"></div>' + top('Theatre') + panel(560, 90, 800, 900, setb, 'Settings', pad=24, gap=12)
page('D07Settings.dc.html', 'Dense: settings', 'theatre', body, 'Theatre view dimmed behind settings', '7 Settings: theme, ground with pictures, symbol colours, panel motion, keys')

# ---- live dossiers ----
ua = json.load(open('../dos/ua.json')); zel = json.load(open('../dos/zel.json')); zp = json.load(open('../dos/zelp.json'))
NOW = ua['now']; stamp_live = 'Live server data, ' + dt.datetime.fromtimestamp(NOW, dt.timezone.utc).strftime('%d %b %Y, %H:%M UTC')
def sect(t, inner, sub=''): return f'<div style="display: flex; flex-direction: column; gap: 8px; padding: 14px; border-radius: 18px; background: {th["tile"]}; border: 1px solid {th["bd"]}; min-width: 0">{hd(t, sub, 15)}{inner}</div>'
def big(label, v, sub, state='ok'):
    return f'<div style="padding: 10px 12px; border-radius: 14px; border: 1px solid {th["bd"] if state == "ok" else STATE[state] + "99"}; min-width: 0"><div style="font-size: 12px; color: {th["mu"]}">{E(label)}</div>{num(v, 24)}<div style="font-size: 11px; color: {th["mu"] if state == "ok" else STATE[state]}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">{E(sub)}</div></div>'
f = ua['facts']; fd = ua['feeds']
def fage(k):
    x = fd.get(k) or {}; t = x.get('data_time') or x.get('fetched')
    return (ago(t, NOW) if t else '?'), {'ok': 'ok', 'late': 'late', 'failing': 'fail', 'waiting': 'wait'}.get(x.get('state'), 'ok')
na, ns = fage('news'); ua_, us_ = fage('unrest'); aa, as_ = fage('airspace')
right_now = ('<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px">'
             + big('Protests and clashes, 24 h', str(ua['unrest']['total']), f"{ua['unrest']['two_plus']} with 2+ outlets · GDELT · {ua_}", us_)
             + big('Airspace warnings', str(len(ua['airspace'])), f"EASA, FAA · {'waiting' if as_ == 'wait' else aa}", as_)
             + big('News places, 6 h', str(ua['news']['places']), f"{ua['news']['outlets']} outlets · GDELT · {na}", ns)
             + big('Military aircraft inside', str(ua['aircraft']['military']), 'adsb.fi · airborne now')
             + big('Navy warnings near the coast', str(len(ua['navwarn']['items'])), 'UKHO only: NGA answered 503', 'late')
             + big('Internet outages', str(len(ua['outages']) if isinstance(ua['outages'], list) else ua['outages']), 'IODA')
             + big('Quakes in or near', str(ua['quakes']['total']), 'USGS, 100 km')
             + big('Warships within 200 km', '–', 'world AIS not set up', 'off') + '</div>')
travel = ''.join(f'<div style="display: flex; gap: 10px; align-items: baseline; padding: 6px 0; border-top: 1px solid {th["faint"]}"><span style="{SG}; font-weight: 600; width: 120px">{src}</span><span style="flex: 1">{E(t)}</span><span style="font-size: 12px; color: {th["mu"]}">{E(d)}</span></div>'
                 for src, t, d in [('US State Dept.', ua['travel']['us'][0]['title'], 'issued ' + dt.datetime.fromtimestamp(ua['travel']['us'][0]['issued'], dt.timezone.utc).strftime('%d %b %Y')),
                                   ('German Foreign Office', ua['travel']['de'][0]['kinds'][0], 'changed ' + dt.datetime.fromtimestamp(ua['travel']['de'][0]['changed'], dt.timezone.utc).strftime('%d %b %Y'))])
air = ''.join(f'<div style="display: flex; gap: 10px; align-items: center; padding: 6px 0; border-top: 1px solid {th["faint"]}">{icon("as_avoid" if a_["level"] in ("avoid", "prohibited") else "as_notice", 22)}<span style="{SG}; font-weight: 600; width: 80px">{E(a_["source"])}</span><span style="flex: 1">{E(a_["title"])}: <b>{E(a_["level"])}</b></span><span style="font-size: 12px; color: {th["mu"]}">{E(a_.get("number") or "")}</span></div>' for a_ in ua['airspace'])
newsr = ''.join(f'<div style="display: flex; gap: 10px; align-items: center; padding: 6px 0; border-top: 1px solid {th["faint"]}"><span style="{SG}; font-weight: 600; width: 30px; text-align: right">{n["outlets"]}</span><span style="flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><b>{E(n["place"].split(",")[0])}</b> · {E(n["articles"][0]["title"])}</span></div>' for n in ua['news']['top'][:6])
rec = lambda k, v: f'<div style="display: flex; gap: 10px; padding: 5px 0; border-top: 1px solid {th["faint"]}"><span style="width: 150px; color: {th["mu"]}">{k}</span><span style="flex: 1">{v}</span></div>'
record = (rec('Capital', 'Kyiv') + rec('Population', f"{int(f['population']['value']):,} ({f['population']['date'][:4]})") + rec('Government', E(f['government'][0]['label']))
          + rec('Head of state', f"{E(f['head_of_state'][0]['label'])}, since {f['head_of_state'][0]['since']}") + rec('Head of government', f"{E(f['head_of_government'][0]['label'])}, since {f['head_of_government'][0]['since']}")
          + rec('Area', f"{int(f['area']['value']):,} km²") + rec('GDP', f"US$ {int(f['gdp']['value'])/1e9:,.0f} bn ({f['gdp']['date'][:4]})") + rec('Currency', E(f['currency'][0]['label'])) + rec('Language', E(f['languages'][0]['label'])))
head = (f'<div style="display: flex; gap: 18px; align-items: center"><span style="width: 72px; height: 48px; border-radius: 8px; background: linear-gradient(#0057b7 50%, #ffd700 50%)"></span>'
        f'<div style="flex: 1"><div style="{SG}; font-weight: 700; font-size: 34px; line-height: 1.1">Ukraine</div><div style="color: {th["mu"]}">Country dossier · Wikidata, our feeds and two travel advisories · every figure with its source and age</div></div>'
        f'<div style="display: flex; gap: 8px">{btn("Show on map")}{btn("Spy passes over Kyiv")}{btn("Imaged from orbit")}</div><span style="width: 34px; height: 34px; border-radius: 999px; background: {th["tile"]}; display: grid; place-items: center; font-size: 18px">×</span></div>')
dos = (head + sect('Right now', right_now, 'from our feeds')
       + f'<div style="display: grid; grid-template-columns: 1.15fr 1fr; gap: 12px; min-height: 0">'
       + f'<div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">{sect("Travel advice", travel)}{sect("Airspace", air, "EASA conflict-zone bulletin, FAA")}{sect("Where the news is", newsr, "places, outlets in 6 h · GDELT · headline of the biggest outlet")}</div>'
       + f'<div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">{sect("Record", record, "Wikidata")}{sect("Not known here", note("What changed since yesterday: needs a history store we do not have yet. Court records: ICC pages refused by its bot shield from this server (17 of 19 missing)."))}</div></div>')
body = svg(m, 'Theatre view') + f'<div style="position: absolute; inset: 0; background: rgba(0,0,0,0.45)"></div>' + top('Theatre', stamp_live, '') + panel(120, 76, 1680, 988, dos, 'Country dossier: Ukraine', pad=24, gap=14)
page('D08Country.dc.html', 'Dense: country dossier', 'theatre', body, 'Theatre view dimmed behind the country dossier', '8 Country dossier (live data from the server, 18 Nov): right now, travel advice, airspace, news places, record')

# 9 person dossier
ra = zel['reported_at']
sig = ('<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px">'
       + big('Outlets naming him, 6 h', str(zel['news']['outlets']), 'GDELT persons')
       + big('Reported at', ra['place'].split(',')[0], f"{ra['outlets']} outlets, {ra['headlines']} headlines · not abroad")
       + big('Aircraft listed with him', str(len(zel['aircraft'])), f"{zel['aircraft'][0]['type']} {zel['aircraft'][0]['reg']} · not airborne now")
       + big('Sanctions lists', 'not checked', 'no OpenSanctions key here', 'off') + '</div>')
places = ''.join(f'<div style="display: flex; gap: 10px; padding: 6px 0; border-top: 1px solid {th["faint"]}"><span style="{SG}; font-weight: 600; width: 26px; text-align: right">{p_["outlets"]}</span><span>{E(p_["place"])}</span></div>' for p_ in zel['news']['places'])
offices = (rec('Head of state of Ukraine', 'since 2019-05-20 (Wikidata, via the country record)') + rec('Two current offices', 'held since 2019-05-20; their names did not load: Wikidata refused label requests (429) from this server'))
recp = (rec('Born', '25 Jan 1978 (age 48)') + rec('Citizenship', 'Ukraine, and one more entry whose label did not load') + rec('Languages', '4 listed; labels did not load')
        + rec('Family', 'spouse, 2 children, mother, father listed; names did not load') + rec('Official accounts', ' · '.join(E(k.rstrip('/@').split('.')[0]) for k in zp['socials'])))
intro = zp['intro'].split('. ')[:2]
headp = (f'<div style="display: flex; gap: 18px; align-items: center"><div style="width: 96px; height: 96px; border-radius: 18px; border: 1px dashed {th["bd"]}; display: grid; place-items: center; color: {th["mu"]}; font-size: 11px; text-align: center">photo<br>Wikimedia</div>'
         f'<div style="flex: 1"><div style="{SG}; font-weight: 700; font-size: 34px; line-height: 1.1">Volodymyr Zelenskyy</div><div style="display: flex; gap: 8px; align-items: center; color: {th["mu"]}"><span style="width: 24px; height: 16px; border-radius: 3px; background: linear-gradient(#0057b7 50%, #ffd700 50%)"></span>Head of state of Ukraine since 20 May 2019 · Wikidata Q3874799</div></div>'
         f'<div style="display: flex; gap: 8px">{btn("Ukraine dossier")}{btn("Show his aircraft")}{btn("Wikipedia")}</div><span style="width: 34px; height: 34px; border-radius: 999px; background: {th["tile"]}; display: grid; place-items: center; font-size: 18px">×</span></div>')
dosp = (headp + sect('Signals', sig, 'from our feeds, now')
        + f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; min-height: 0">'
        + f'<div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">{sect("Where the news places him", places, "outlets per place, 6 h · GDELT")}{sect("In short", note(E(". ".join(intro)) + ".", 14), "Wikipedia, first two sentences")}</div>'
        + f'<div style="display: flex; flex-direction: column; gap: 12px; min-width: 0">{sect("Offices", offices, "Wikidata")}{sect("Record", recp, "Wikidata")}{sect("Court records", note("None found on the ICC case list. 17 of 19 ICC situation pages were refused by the court\'s bot shield from this server, so they were not read. England and Wales: not asked (no UK link)."), "ICC, National Archives")}</div></div>')
body = svg(m, 'Theatre view') + f'<div style="position: absolute; inset: 0; background: rgba(0,0,0,0.45)"></div>' + top('Theatre', stamp_live, '') + panel(120, 76, 1680, 988, dosp, 'Person dossier: Volodymyr Zelenskyy', pad=24, gap=14)
page('D09Person.dc.html', 'Dense: person dossier', 'theatre', body, 'Theatre view dimmed behind the person dossier', '9 Person dossier (live data, 18 Nov), with what failed to load said where it failed')

# 10 follow (chase)
cc = V['chase']['cams'][0][0]
acx, acy, _ = cc.proj(AC['lon'], AC['lat'], AC['alt_km']/6371)
gx0, gy0, _ = cc.proj(AC['lon'], AC['lat'])
gaf = [m_ for m_ in IT['mil'] if m_['flight'] == 'GAF633'][0]
plane = J.draw(acls(gaf), 'solid', acx, acy, 46, 0, PAL, 'dark', colkey='mil') + f'<path d="M{acx:.1f} {acy + 20:.1f} L{gx0:.1f} {gy0:.1f}" stroke="{th["tx"]}" stroke-opacity="0.5" stroke-dasharray="3 4"></path>' + S.lock(acx, acy, 36) + lbl(acx + 34, acy - 26, 'GAF633', size=14, wt=600)
ctl = f'<div style="position: absolute; left: 420px; top: 870px; height: 56px; box-sizing: border-box; padding: 0 10px; border-radius: 999px; {glass()}; display: flex; align-items: center; gap: 8px">{chip("Following GAF633", True)}{chip("↺ 45°")}{chip("↻ 45°")}{chip("North up")}{chip("Behind it")}{chip("Stop")}<span style="font-size: 12px; color: {th["mu"]}; padding: 0 8px">drag to look around it</span></div>'
card = (hd('GAF633', 'military · following', 22, True) + note(f'{J.LIB[acls(gaf)]["name"]} · type {gaf["type"]} · {gaf["reg"]} · {gaf["hex"].upper()} · transponder address in the German block')
        + f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px">{kv("Altitude", fl(gaf))}{kv("Ground speed", str(round(gaf["gs"])) + " kt")}{kv("Track", "%03d°" % round(gaf["track"]))}{kv("Last report", str(round(gaf["seen"])) + " s ago")}{kv("Over", "Türkiye")}{kv("Camera", "behind, 62°")}</div>'
        + rule() + note('Numbers update with every report. The aircraft is drawn 40 s behind real time and moves between real reports only. The dashed line drops to the point on the ground below it.'))
body = svg(plane, 'GAF633 seen from behind at its altitude') + top('Chase') + panel(1400, 76, 504, 420, card, 'Followed aircraft') + ctl + strip('chase') + zoom()
page('D10Follow.dc.html', 'Dense: follow', 'chase', body, 'Behind GAF633 over Türkiye', '10 Following an aircraft: the card stays live, the follow controls float above the view pictures')

# 11 front line close
cf = V['front']['cams'][0][0]
mf, PF = marks(cf.proj, HIDE, kinds=('front', 'unrest'))
ch = FR['changes'][-8]
hx, hy, _ = cf.proj(ch['lon'], ch['lat'])
lst = ''.join(f'<div style="display: flex; gap: 10px; align-items: flex-start; padding: 7px 0; border-top: 1px solid {th["faint"]}">{icon("frontchange", 18)}<span style="flex: 1">{E(c["text"])}</span><span style="font-size: 12px; color: {th["mu"]}; white-space: nowrap">{cap_age(c["time"])}</span></div>' for c in FR['changes'][-8:][::-1])
card = (hd('Front line, Ukraine', 'DeepState', 18, True) + f'<div style="display: flex; gap: 12px">{kv("Occupied", "116,892 km²")}{kv("Change, 7 d", "+27 km²")}{kv("Update", "1 d 14 h")}</div>'
        + note("Ukrainian OSINT team's assessment, hours to a day behind events. Areas drawn exactly as they publish them; their political polygons are left out.")
        + hd('Changes they logged', 'newest first', 14) + f'<div style="overflow: hidden">{lst}</div>')
body = svg(occupied(cf.proj, 160) + mf + S.lock(hx, hy, 16), 'Eastern Ukraine with the occupied area') + top('Look down: eastern Ukraine') + panel(1400, 76, 504, 988, card, 'Front line') + strip('front') + zoom() + keyrow([('frontchange', 'Change logged', None), ('clash', 'Clash', None)], y=900)
page('D11Front.dc.html', 'Dense: front line', 'front', body, 'Eastern Ukraine from 1,019 km with the occupied area', '11 Look down over the front: the occupied area, logged changes, the change list in the column')

# 12 feeds and states
FEEDS = [('Military aircraft', 'adsb.fi', 'ok', '12 s'), ('Protests and clashes', 'GDELT', 'ok', '1 min'), ('Leaders in the news', 'GDELT', 'ok', '57 min'),
         ('Earthquakes', 'USGS', 'ok', '1 min'), ('Front line', 'DeepState', 'ok', '1 d 14 h'), ('Navy warnings', 'UKHO; NGA 503', 'late', 'NGA failing'),
         ('US carriers', 'USNI News', 'late', '22 d'), ('Court records', 'ICC', 'fail', 'bot shield'), ('Ships worldwide', 'aisstream.io', 'off', 'no key'), ('Internet hijacks', 'Cloudflare Radar', 'off', 'no key'),
         ('Windy cameras', 'Windy', 'off', 'no key'), ('Launches', 'Launch Library 2', 'ok', '43 s'), ('Internet outages', 'IODA', 'ok', '22 s')]
fl_ = ''.join(f'<div style="display: flex; gap: 10px; align-items: center; height: 36px; border-top: 1px solid {th["faint"]}">{dot(s)}<span style="flex: 1">{E(n)}</span><span style="font-size: 12px; color: {th["mu"]}; width: 130px">{E(src)}</span><span style="font-size: 12px; width: 90px; text-align: right; color: {th["mu"] if s == "ok" else STATE[s]}">{E(a_)}</span></div>' for n, src, s, a_ in FEEDS)
feedsp = hd('Feeds', '40 of 45 current · 1 late · 1 failing · 3 not set up', 16, True) + note('A feed that stops is never hidden: its layer turns grey and says since when. Ages are the data\'s own time where the source gives one. This board lists the feeds whose age the capture kept; the app lists all 45.') + f'<div style="overflow: hidden">{fl_}</div>'
dead = panel(480, 300, 420, 230, hd('USS Boxer', 'US amphib', 16) + f'<div style="display: flex; gap: 8px; align-items: center; padding: 8px 12px; border-radius: 12px; border: 1px solid {YEL}99; color: {YEL}">{dot("late")}Last known: USNI tracker of 19 Oct, 29 days old</div>' + note('The symbol is grey and dashed on the map while its feed is late. Aircraft from a stopped live feed do the same after 30 s and disappear after 2 minutes.'), 'Late feed card')
empty = panel(480, 560, 420, 170, hd('Hotspots', 'none now', 16) + note('No place has 3 or more different kinds of signal within 250 km in 24 hours. Most hours show none; that is the rule working, not a fault.'), 'Empty layer')
nokey = panel(480, 760, 420, 150, hd('Ships worldwide', 'not set up', 16) + note('Needs a free aisstream.io key in data/aisstream-key.txt. Until then only Finland\'s open feed (northern Baltic) is drawn.'), 'Layer without key')
body = svg(m, 'Theatre view') + top('Theatre') + dead + empty + nokey + panel(1400, 76, 504, 988, feedsp, 'Feeds') + strip('theatre') + zoom()
page('D12Feeds.dc.html', 'Dense: feeds and states', 'theatre', body, 'Theatre view with state examples', '12 Feeds and states: the feed list in the column, a late feed, an empty layer, a layer without its key')

# 13 light
th = T['light']
ml, _ = marks(cth.proj, HIDE)
ku_l = cth.proj(ku['lon'], ku['lat'])
body = svg(ml, 'Theatre view, light') + top('Theatre') + signals_panel(1400, 76, 504, 520, 5) + layers_panel(1400, 608, 504, 456, 8) + strip('theatre') + zoom() + keyrow(KEY)
page('D13Light.dc.html', 'Dense: light', 'theatre_light', body, 'Europe and the Black Sea, light ground', '13 Light mode (follows the Mac): the same overview on the light ground')
th = T['dark']

# 14 column folded
mz, _ = marks(cth.proj, [(1820, 76, 84, 988), (0, 0, 1920, 70), (1330, 750, 60, 160), (16, 890, 1100, 50)])
rail = ''.join(f'<div style="display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 0">{icon(i, 26, ck=ck)}{num(c, 13)}</div>' for i, _, c, _, _, _, ck in TILES[:8])
body = svg(mz, 'Theatre view, wide') + top('Theatre') + panel(1832, 76, 72, 988, rail + note('›', 16), 'Folded column', pad=8, gap=4, r=20) + zoom(1770, 760) + keyrow(KEY)
page('D14Folded.dc.html', 'Dense: column folded', 'theatre', body, 'Theatre view with the column folded', '14 Column folded and pictures hidden: a rail of counts, the map uses the screen')
json.dump(OUT_B, open('denseboards.json', 'w')); print(len(OUT_B))
