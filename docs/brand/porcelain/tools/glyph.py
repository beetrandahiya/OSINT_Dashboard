"""The approved 147-symbol set (server/worldwatch/static/js/glyphs.js), drawn solid: every edge first, then the fills."""
import json, html
SRC = "/home/user/OSINT_Dashboard/server/worldwatch/static/js/glyphs.js"
_t = open(SRC).read(); LIB = json.loads(_t[_t.index("{"):_t.rindex("}") + 1])["lib"]
CODES = {}
for k, v in LIB.items():
    for c in (v.get("c") or "").split():
        CODES.setdefault(c, k)


def for_type(t, military=True):
    return CODES.get(t or "", "mil_generic" if military else "narrow")


def svg(key, x, y, size, fill, edge, rot=0, edge_w=6.0, title=None):
    g = LIB[key]["g"]; s = size / 64
    out = [f'<g transform="translate({x - size / 2:.1f} {y - size / 2:.1f}) scale({s:.4f}) rotate({rot:.0f} 32 32)">']
    if title: out.append(f"<title>{html.escape(title)}</title>")
    for d, m in g:   # edges
        if m in ("f", "k", "x", "a"):
            out.append(f'<path d="{d}" fill="{edge}" stroke="{edge}" stroke-width="{edge_w}" stroke-linejoin="round"/>')
        elif m in ("s", "d"):
            out.append(f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="{edge_w + 3}" stroke-linecap="round" stroke-linejoin="round"/>')
    for d, m in g:   # fills
        if m == "f": out.append(f'<path d="{d}" fill="{fill}"/>')
        elif m == "k": out.append(f'<path d="{d}" fill="{edge}"/>')
        elif m == "x": out.append(f'<path d="{d}" fill="{edge}"/>')
        elif m == "a": out.append(f'<path d="{d}" fill="{fill}" fill-opacity=".28"/>')
        elif m == "s": out.append(f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>')
        elif m == "d": out.append(f'<path d="{d}" fill="none" stroke="{fill}" stroke-width="3.2" stroke-dasharray="5 4"/>')
    out.append("</g>")
    return "".join(out)
