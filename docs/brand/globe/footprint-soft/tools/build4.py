"""Footprint: Anduril's black and white on a soft lavender-to-blue 3D tile (Tailwind CSS v3.4.17 palette)."""
import base64, html, json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "logo" / "tools"))
sys.path.append(str(HERE.parent / "vivid"))
import typo  # noqa: E402
from soft import footprint, VARIANTS, TW  # noqa: E402

OUT = HERE / "out"; (OUT / "png").mkdir(parents=True, exist_ok=True); (OUT / "marks").mkdir(exist_ok=True)
esc = lambda s: html.escape(s, quote=True)
F = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
OPTS = [
    ("mesh", "Two soft pools", 1, "Lavender (violet-300) glowing from the top left and light blue (sky-200) from the bottom right, over a pale "
     "indigo-100 base, with light from above and a little shade at the bottom. The most 3D of the four.", ["violet-300", "indigo-100", "sky-200", "indigo-300"]),
    ("lavender-blue", "Lavender to blue, diagonal", 2, "One clean diagonal from violet-200 to sky-200, the same light and shade on top.",
     ["violet-200", "sky-200", "indigo-300"]),
    ("vertical", "Lavender to blue, top to bottom", 3, "violet-200 at the top fading to blue-100 at the bottom: calmer, like a sky.",
     ["violet-200", "blue-100", "indigo-200"]),
    ("soft", "Palest", 0, "The lightest steps of the scale, violet-100 to sky-100: almost white, the colour only shows at large sizes.",
     ["violet-100", "sky-100", "indigo-200"]),
    ("lavender-blue-flat", "Same tile, flat globe", 0, "The diagonal tile with a plain black globe and no shadow, to compare the 3D globe against.",
     ["violet-200", "sky-200"]),
]
WM = typo.text_path("geist-600", "World Watch", 100, -0.012)


def wordmark(fill, x, base, cap):
    d, w, capu = WM; s = cap / capu
    return f'<path transform="translate({F(x)} {F(base)}) scale({F(s)})" d="{d}" fill="{fill}"/>', w * s


def T(x, y, s, size, fill, weight=400):
    return f'<text x="{F(x)}" y="{F(y)}" font-family="Inter, system-ui, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(s)}</text>'


def inner(svg):
    return svg[svg.index(">") + 1: svg.rindex("</svg>")]


def icon_at(k, v, x, y, size, uid):
    return f'<svg x="{F(x)}" y="{F(y)}" width="{F(size)}" height="{F(size)}" viewBox="0 0 64 64">{inner(footprint(k, v, uid))}</svg>'


APP = dict(dark=dict(bg="#0B0D10", panel="#1A1E24", line="#2A3038", ink="#F2F4F6", sub="#9AA3AD"),
           light=dict(bg="#F5F6F8", panel="#FFFFFF", line="#DCE0E5", ink="#0B0D10", sub="#5A6470"))


def topbar(k, tone, uid):
    t = APP[tone]; w, h = 960, 60
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/><line x1="0" y1="{h - .5}" x2="{w}" y2="{h - .5}" stroke="{t["line"]}"/>'
    b += icon_at(k, "small", 18, 15, 30, uid)
    p, ww = wordmark(t["ink"], 60, 37, 13); b += p
    x = 60 + ww + 34
    for i, n in enumerate(["Map", "Connections", "Investigate", "Sources"]):
        wd = 9 + len(n) * 7.3
        if i == 0:
            b += f'<rect x="{F(x - 10)}" y="16" width="{F(wd + 8)}" height="28" rx="8" fill="{t["panel"]}"/>'
        b += T(x, 35, n, 13.5, t["ink"] if i == 0 else t["sub"], 600 if i == 0 else 500); x += wd + 18
    b += f'<rect x="{w - 330}" y="15" width="200" height="30" rx="15" fill="{t["panel"]}" stroke="{t["line"]}"/>' + T(w - 314, 35, "Find a person or country", 12.5, t["sub"])
    b += f'<rect x="{w - 116}" y="15" width="98" height="30" rx="15" fill="none" stroke="{t["line"]}"/><circle cx="{w - 98}" cy="30" r="4" fill="{TW["violet-300"]}"/>' + T(w - 88, 35, "Feeds", 12.5, t["ink"], 500)
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Top bar, {tone}">{b}</svg>'


def splash(k, tone, uid):
    t = APP[tone]; w, h = 960, 340
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>' + icon_at(k, "full", 80, 80, 180, uid)
    p, _ = wordmark(t["ink"], 310, 170, 44)
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Splash, {tone}">{b}{p}{T(312, 214, "Real data only. Every layer shows its source.", 22, t["sub"])}</svg>'


def png(k, bg):
    return "data:image/png;base64," + base64.b64encode((OUT / "png" / f"{k}-{bg}.png").read_bytes()).decode()


def big(k, size, uid):
    return footprint(k, "full", uid).replace("<svg ", f'<svg width="{size}" height="{size}" class="big" aria-hidden="true" ', 1)


def main():
    marks = {k: {"full": footprint(k, "full", "s" + k[:3]), "small": footprint(k, "small", "t" + k[:3])} for k, *_ in OPTS}
    (OUT / "marks.json").write_text(json.dumps(marks))
    subprocess.run(["node", str(HERE.parent / "globe" / "strips.js"), str(OUT / "marks.json"), str(OUT / "png")], check=True)
    for k, m in marks.items():
        (OUT / "marks" / f"footprint-{k}.svg").write_text(m["full"]); (OUT / "marks" / f"footprint-{k}-small.svg").write_text(m["small"])
    body = ('<title>Footprint soft tile</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Space+Grotesk:wght@500;600&display=swap">'
            f'<style>{(HERE / "page4.css").read_text()}</style><main class="wrap">')
    body += ('<header class="intro"><p class="eyebrow">World Watch · Footprint · soft tile</p><h1>Footprint on a soft lavender and blue tile</h1>'
             '<p class="lede">The Anduril version you liked, black Earth (#010101), white footprint and black point on Munich, with the lime '
             'swapped for a very light lavender-to-blue gradient. The tile colours are steps of the Tailwind CSS colour scale, one of the most '
             'used published design palettes (<a href="https://github.com/tailwindlabs/tailwindcss/blob/v3.4.17/src/public/colors.js">colors.js, v3.4.17</a>). '
             'The 3D comes from soft light from above, a little shade along the bottom, a thin light rim, and a sheen and contact shadow on '
             'the globe so it sits on the tile like a ball.</p></header>')
    body += '<div class="ov">' + "".join(f'<a class="ovc" href="#{k}">{big(k, 110, "o" + k[:4])}<b>{esc(n)}</b></a>' for k, n, *_ in OPTS[:4]) + "</div>"
    for k, n, rank, why, cols in OPTS:
        tag = {1: "My pick", 2: "Second", 3: "Third"}.get(rank, "")
        s = f'<section class="opt{" top" if rank == 1 else ""}" id="{k}"><div class="head">{big(k, 160 if rank else 120, "h" + k[:4])}<div class="txt">'
        s += f'<p class="eyebrow">{tag}</p><h2>{esc(n)}</h2><p>{esc(why)}</p></div></div>'
        s += '<ul class="sw">' + "".join(f'<li><span class="chip" style="background:{TW[c]}"></span><b>{c}</b> <code>{TW[c]}</code></li>' for c in cols)
        s += f'<li><span class="chip" style="background:#010101"></span><b>Anduril black</b> <code>#010101</code></li><li><span class="chip" style="background:#FFFFFF"></span><b>White</b> <code>#FFFFFF</code></li></ul>'
        s += '<div class="sizes">' + "".join(f'<figure><img class="px" src="{png(k, bg)}" alt=""><figcaption>{lab}</figcaption></figure>'
                                            for bg, lab in (("dark", "Windows, dark"), ("light", "Windows, light"), ("dock", "macOS Dock"))) + "</div>"
        if rank:
            s += f'<div class="zoom"><img class="z3" src="{png(k, "dark")}" alt=""><img class="z3" src="{png(k, "light")}" alt=""></div>'
            s += topbar(k, "dark", "d" + k[:4]) + topbar(k, "light", "l" + k[:4]) + '<div class="pair">' + splash(k, "dark", "e" + k[:4]) + splash(k, "light", "f" + k[:4]) + "</div>"
        body += s + "</section>"
    body += ('<section class="outro"><p class="eyebrow">Recommendation</p><h2>Two soft pools</h2>'
             '<p>Both colours show and the tile has real depth without getting loud. The black Earth stays the strongest thing at every size, '
             'which is what makes it work on any taskbar. At 16 and 24 px the tile reads as near white with a hint of colour: the small sizes '
             'keep the tile simple on purpose.</p><h3>Questions for you</h3><ol><li>Which tile? I can also make it a touch stronger or softer.</li>'
             '<li>Once you pick: shall I make the real icon files (Windows .ico, macOS icon) and put the icon and these colours into the app\'s top bar?</li></ol>'
             '<p class="small">Checked in Chromium at one device pixel per pixel, light and dark; not in Safari, not on your real taskbar or Dock. '
             'Wordmark: Geist SemiBold, outlined.</p></section></main>'
             "<script>document.querySelectorAll('img.z3').forEach(i=>{const s=()=>{i.style.width=i.naturalWidth*3+'px'};i.complete?s():i.addEventListener('load',s)})</script>")
    (OUT / "page.html").write_text(body); print(round(len(body) / 1024), "KB")


main()
