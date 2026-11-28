import base64, pathlib, sys
d = pathlib.Path(sys.argv[1])
keys = sorted(p.stem for p in (d / "marks").glob("*.svg") if not p.stem.endswith("-small"))
h = ['<html><body style="margin:6px;background:#777;font:12px sans-serif;color:#fff">']
for k in keys:
    h.append(f'<div style="display:flex;align-items:center;gap:4px;margin:3px 0"><div style="width:100px">{k}</div>')
    for bg in ("dark", "light", "dock"):
        for s in (16, 24, 32, 48):
            b = base64.b64encode((d / "renders" / f"{k}-{s}-{bg}.png").read_bytes()).decode()
            h.append(f'<img src="data:image/png;base64,{b}" style="width:{(s+40)*2}px;height:{(s+24)*2}px;image-rendering:pixelated">')
    h.append("</div>")
(d / "review" / "all.html").write_text("".join(h) + "</body></html>")
