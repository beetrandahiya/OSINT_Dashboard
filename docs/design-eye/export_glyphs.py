"""Writes server/worldwatch/static/js/glyphs.js from icons2.py (the God's eye icon set). Run from this folder."""
import json, re, icons2 as J, icons as I
def rnd(d): return re.sub(r'(\d+\.\d{2})\d+', r'\1', d)
lib = {}
for i, s in J.LIB.items():
    lib[i] = dict(n=s['name'], k=s['colkey'], grp=s['group'], r=1 if s['rot'] else 0, g=[[rnd(d), m] for d, m in s['g']])
    if s['codes']: lib[i]['c'] = s['codes']
    if s['small']: lib[i]['sm'] = J.SMALLMAP[s['small']]
small = {k: [[rnd(d), m] for d, m in I.S[k]['g']] for k in set(J.SMALLMAP.values())}
acc = {'sanctioned': 'clash', 'breaking': 'clash', 'quake_test': 'nuke', 'head': 'vip', 'camlive': 'ok'}
out = {'lib': lib, 'small': small, 'acc': acc, 'pal': {p: {m: J.PAL[p][m] for m in ('dark', 'light')} for p in 'AC'}, 'ink': {'dark': I.INK, 'light': '#ffffff'}}
js = ("// Generated from docs/design-eye/icons2.py (the God's eye icon set the owner approved, 2026-11-17): 147 symbols drawn on a\n"
      "// 64-unit grid, each piece [path, mode]: f fill, k ink cut-out, s stroke, d dashed stroke, a translucent area, x accent fill.\n"
      "// Palettes A and C, dark and light. Do not edit by hand; regenerate with docs/design-eye/export_glyphs.py.\n"
      'export default ' + json.dumps(out, separators=(',', ':')) + ';\n')
open('../../server/worldwatch/static/js/glyphs.js', 'w').write(js)
