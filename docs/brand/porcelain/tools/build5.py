"""World Watch Porcelain: the design-language page. Builds out/porcelain.html (published as an artifact)."""
import base64, html, math, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.append(str(HERE.parent / "logo" / "tools"))
import typo, porcelain as P, mock, reports, geo, gmarks as G, glyph as GL
from geo import MUC
esc = lambda s: html.escape(str(s), quote=True)
OUT = HERE / "out"


def b64(p, mime="image/webp"):
    return f"data:{mime};base64," + base64.b64encode((OUT / p).read_bytes()).decode()


IMG = {f"{t}-{s}": b64(f"i-{t}-{s}.webp") for t in ["light", "dark", "dark-planet"] for s in (640, 128)}


def wm(key="monasans-w118-640", size=100, track=-0.005, text="World Watch"):
    d, w, cap = typo.text_path(key, text, size, track)
    b = typo.ink_bounds(key, text, size, track)
    vb = f"{b[0] - .5:.1f} {b[1] - .5:.1f} {b[2] - b[0] + 1:.1f} {b[3] - b[1] + 1:.1f}"
    return d, vb, b[2] - b[0] + 1, b[3] - b[1] + 1


WM22 = wm(size=16 / 0.72)
mock.WMVB, mock.WMH = WM22[1], WM22[3]
WMBIG = wm(size=100)


def wmsvg(w, cls="wm", fill="currentColor", label="World Watch", src=None):
    d, vb, ww, hh = src or WMBIG
    return f'<svg class="{cls}" viewBox="{vb}" width="{w}" height="{w * hh / ww:.1f}" role="img" aria-label="{label}"><path d="{d}" fill="{fill}"/></svg>'


def flat(theme, px, uid):
    return P.flat_svg(theme, uid).replace("<svg ", f'<svg width="{px}" height="{px}" role="img" aria-label="World Watch icon" ', 1)


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + .05) / (lb + .05)


# ---------- construction drawing of the mark
def construction():
    r, C = 120, 150
    o = [f'<svg viewBox="0 0 300 300" class="cons" role="img" aria-label="How the mark is built: a globe seen from 20 degrees north 10 degrees west, the Sentinel-2 horizon around Munich, Munich as the pupil">']
    o.append(f'<circle cx="{C}" cy="{C}" r="{r}" class="c-globe"/>')
    for lon in range(-180, 180, 30):
        pts = [(lat, lon) for lat in range(-90, 91, 3)]
        o.append(f'<path d="{geo.project_path(pts, G.FP_CAM, C, C, r)}" class="c-grat"/>')
    for lat in range(-60, 90, 30):
        pts = [(lat, lon) for lon in range(-180, 181, 3)]
        o.append(f'<path d="{geo.project_path(pts, G.FP_CAM, C, C, r)}" class="c-grat"/>')
    rho = geo.horizon_angle(G.S2_ALT)
    o.append(f'<path d="{G.onlimb(geo.small_circle(MUC[0], MUC[1], rho, 720), G.FP_CAM, r, C, C)}" class="c-cap"/>')
    mx, my, _ = geo.project_pts([MUC], G.FP_CAM, C, C, r)[0]
    o.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{3.6 / 26.5 * r:.1f}" class="c-pupil"/>')
    o.append(f'<circle cx="{C}" cy="{C}" r="2.5" class="c-dot"/>')
    o.append("</svg>")
    return "".join(o), rho


CONS, RHO = construction()
WIDTH_KM = 2 * RHO * 111.195


# ---------- swatches
def sw(hexv, name, src, role, on=None):
    on = on or ("#010101" if lum(hexv) > .4 else "#ffffff")
    return (f'<div class="swatch"><div class="chip" style="background:{hexv};color:{on}"><span class="mono">{hexv.upper()}</span></div>'
            f'<b>{esc(name)}</b><span>{esc(role)}</span><span class="src">{esc(src)}</span></div>')


def pair(label, light, dark, kind="ink", src=""):
    lb, db = ("#ffffff", "#18181b") if kind != "map" else ("#ffffff", "#18181b")
    return (f'<tr><th>{esc(label)}</th><td><span class="pp" style="background:{light}"></span><span class="mono">{light.upper()}</span></td>'
            f'<td><span class="pp" style="background:{dark}"></span><span class="mono">{dark.upper()}</span></td><td class="src">{esc(src)}</td></tr>')


def ratio(a, b):
    return f"{cr(a, b):.1f}:1"


# ---------- components (scoped UI, both themes)
def components(t):
    g = lambda k, c, s=18: mock.ico(k, c, s)
    return f'''<div class="ui {t} comp">
<div class="crow"><span class="btn ink">Country dossier</span><span class="btn">Spy passes</span><span class="btn quiet">Show on map</span></div>
<div class="crow"><nav class="tabs"><span class="tab on">Map</span><span class="tab">Connections</span><span class="tab">Investigate</span><span class="tab">Sources</span></nav></div>
<div class="crow"><span class="search"><i class="lens"></i>Find a place, person or company</span></div>
<div class="crow pills"><span class="feeds"><i class="dot live"></i>live</span><span class="feeds"><i class="dot late"></i>late · USNI 40 days</span><span class="feeds"><i class="dot fail"></i>failing</span><span class="feeds"><i class="dot"></i>not set up</span></div>
<div class="crow"><span class="switch on"><i></i></span><span class="lbl">Protests and clashes</span><span class="switch"><i></i></span><span class="lbl">Unrest, one outlet</span></div>
<ul class="clist">
  <li><i class="g">{g("aerial", "var(--u-conf)")}</i><span class="t">Kharkiv<small>aerial weapons (air strike, drone)</small></span><b class="num">95</b></li>
  <li class="sel"><i class="g">{g("strategic", "var(--u-mil)")}</i><span class="t">RCH4934<small>C-17 · FL310</small></span><b class="num">03:08</b></li>
  <li><i class="g">{g("launch", "var(--u-sat)")}</i><span class="t">USSF-380<small>Falcon 9 Block 5 · Go for Launch</small></span><b class="num">29 Nov 04:39</b></li>
</ul>
<div class="crow tilesrow"><div class="tile"><i class="g">{g("cargo", "var(--u-ship)", 16)}</i><b class="num">663</b><span class="n">Ships</span><span class="s"><i class="dot live"></i>Digitraffic · 03:08</span></div>
<div class="tile"><i class="g">{g("occupied", "var(--u-conf)", 16)}</i><b class="num">116,931</b><span class="n">km² occupied</span><span class="s"><i class="dot live"></i>DeepState · 28 Nov</span></div></div>
</div>'''


def splash(t):
    icon = IMG["light-640"] if t == "l" else IMG["dark-640"]
    return f'''<div class="ui {t} splash"><img src="{icon}" width="112" height="112" alt="World Watch icon">
{wmsvg(190, "wm", "currentColor", src=WMBIG)}<div class="bar"><i></i></div><span class="num">Connecting to 45 feeds</span></div>'''


def strips():
    rows = [("#202020", "Dark taskbar", "#d4d4d8"), ("#f3f3f3", "Light taskbar", "#3f3f46"), ("linear-gradient(#e8e8ee,#cfd2da)", "Dock", "#3f3f46")]
    sets = [("light", "Light"), ("dark", "Dark twin"), ("dark-planet", "Planet")]
    o = ['<div class="strips">']
    for bg, name, fg in rows:
        o.append(f'<div class="srow" style="background:{bg};color:{fg}"><span class="sn">{name}</span>')
        for k, lab in sets:
            o.append('<span class="sset">')
            for px in (16, 24, 32):
                o.append(flat(k, px, f"{k[:2]}{px}{name[:2]}"))
            for px in (48, 64):
                o.append(f'<img src="{IMG[k + "-128"]}" width="{px}" height="{px}" alt="">')
            o.append("</span>")
        o.append("</div>")
    o.append('<div class="srow legend"><span class="sn"></span>' + "".join(f'<span class="sset slab">{lab}<small>16 · 24 · 32 flat, 48 · 64 rendered</small></span>' for _, lab in sets) + "</div></div>")
    return "".join(o)


def zoom16():
    o = []
    for k in ["light", "dark", "dark-planet"]:
        src = "data:image/svg+xml;base64," + base64.b64encode(P.flat_svg(k, "z" + k[:2]).encode()).decode()
        o.append(f'<div class="z"><canvas class="px16" width="16" height="16" data-src="{src}" aria-label="{k} icon at 16 pixels"></canvas><span>{k.replace("-", " ").replace("dark planet", "planet").replace("dark", "dark twin")} at 16 px, each pixel 6×</span></div>')
    return "".join(o)


# ---------- glyph legend for the light map
def legend_row(key, col, label, t):
    return f'<li><i class="g">{mock.ico(key, col, 20)}</i>{esc(label)}</li>'



def face(spec_html, name, role, story, lic, href):
    return (f'<div class="face"><span class="role">{role}</span><div class="spec">{spec_html}</div><b style="font-family:var(--f-head);font-weight:640;font-stretch:112%;font-size:17px">{name}</b>'
            f'<p>{story}</p><span class="lic">{lic} · <a href="{href}">source</a></span></div>')


def ring_demo():
    o = ['<svg viewBox="0 0 260 150" role="img" aria-label="A selected item: one thin ring with a white halo">']
    o.append('<rect width="260" height="150" fill="#f0f9ff"/><path d="M0 92 C60 70 110 104 170 86 S240 60 260 70 V150 H0Z" fill="#ffffff" stroke="#d4d4d8" stroke-width=".8"/>')
    o.append(GL.svg("aerial", 130, 75, 24, "#e11d48", "#ffffff", edge_w=7))
    o.append(GL.svg("clash", 62, 112, 16, "#e11d48", "#ffffff", edge_w=7))
    o.append(GL.svg("strategic", 212, 40, 22, "#4338ca", "#ffffff", rot=63, edge_w=6))
    o.append('<circle cx="130" cy="75" r="21" fill="none" stroke="#ffffff" stroke-width="4" stroke-opacity=".9"/><circle cx="130" cy="75" r="21" fill="none" stroke="#010101" stroke-width="1.4"/>')
    o.append("</svg>")
    return "".join(o)


def page():
    D = mock.data()
    occ = D["front"]["occupied_km2"]
    alt1 = wm("ddincond-700", 60, 0.0); alt2 = wm("cooperhewitt-600", 60, 0.0)
    T = []
    T.append(f'''<title>World Watch Porcelain</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=B612:ital,wght@0,400;0,700&family=B612+Mono:wght@400;700&family=Mona+Sans:wdth,wght@75..125,200..900&family=Redaction:ital,wght@0,400;0,700;1,400&family=Redaction+50:wght@700&display=swap">
<style>{(HERE / "page5.css").read_text()}{(HERE / "ui.css").read_text()}</style>''')
    # ---------------- hero
    T.append(f'''<div class="hero"><div class="wrap">
<div><span class="lab">World Watch · design language · 28 Nov 2026</span><h1>Porcelain</h1>
<p class="lede">Black ink on white porcelain, with a whisper of lavender and blue. The icon is the Earth seen from 20° N 10° W. The white patch is everything Sentinel-2 can see from 786 km above Munich, and the black dot is Munich.</p>
<dl><dt>Horizon</dt><dd>{RHO:.1f}° of arc · {WIDTH_KM:,.0f} km across</dd><dt>Satellite</dt><dd>Sentinel-2 · 786 km</dd><dt>Camera</dt><dd>20.0° N 10.0° W</dd><dt>Pupil</dt><dd>Munich · 48.14° N 11.58° E</dd></dl></div>
<div class="art"><img src="{IMG["light-640"]}" width="300" height="300" alt="World Watch icon: a black globe with a white footprint and a black pupil on an almost white tile">
<img class="twin" src="{IMG["dark-640"]}" width="132" height="132" alt="Dark twin of the icon: a white globe on a near-black tile"></div>
</div></div>''')
    # ---------------- icon
    T.append(f'''<section class="s" id="icon"><div class="wrap"><header><span class="lab">1 · The icon</span><div><h2>Lighter tile, rounder Earth</h2></div>
<p>The tile is now almost white, the globe is lit like a ball, and there is a dark twin for dark mode.</p></header>
<div class="grid g3">
<div class="fig"><div class="plate white"><img src="{IMG["light-640"]}" width="320" height="320" alt="Light icon"></div><b>Light</b>
<p>White porcelain. Tailwind's violet-100 glows in from the top left and sky-100 from the bottom right, and both fade to white before the middle. The last tile used those two colours edge to edge.</p></div>
<div class="fig"><div class="plate night"><img src="{IMG["dark-640"]}" width="320" height="320" alt="Dark twin"></div><b>Dark twin <span class="tag">your pick</span></b>
<p>Zinc-950 tile with violet-950 and sky-950 whispers, a white globe, and the footprint as its negative. A white ball with a dark disc reads more like an eye than the light icon does. It stays clear at 16 px on a dark taskbar.</p></div>
<div class="fig"><div class="plate night"><img src="{IMG["dark-planet-640"]}" width="320" height="320" alt="Planet alternative"></div><b>Planet <span class="tag" style="background:var(--ink3)">alternative</span></b>
<p>The same black Earth as the light icon, outlined by its own atmosphere on a dark tile. It is the better picture at Dock size, but at 16 px on a dark taskbar the globe disappears into the tile.</p></div>
</div>
<div class="notes"><div><b>More 3D</b><p>The globe is shaded as a matte sphere lit from the top left. A thin atmosphere glows along the sunlit edge, and the white footprint darkens towards the limb with it.</p></div>
<div><b>Sitting on the tile</b><p>The globe casts a soft shadow, tinted indigo-950, straight down onto the tile. The tile's rounded edge catches light along the top and turns faintly lavender along the bottom.</p></div>
<div><b>Same geometry</b><p>Nothing moved: the camera, the 786 km horizon and the pupil are computed exactly as in the mark you approved. From 32 px down a flat version takes over, with a bigger footprint and pupil.</p></div></div>
<div class="consrow">{CONS}<dl><dt>Camera</dt><dd>Orthographic view from 20.0° N 10.0° W, so Munich sits up and to the right of the centre</dd>
<dt>Footprint</dt><dd>Sentinel-2's horizon at 786 km: arccos(R / (R + h)) = {RHO:.1f}°, a cap {WIDTH_KM:,.0f} km across</dd>
<dt>Pupil</dt><dd>Munich at 48.137° N 11.575° E, radius 3.6 on the 64 grid (5.2 in the small version)</dd>
<dt>Tile</dt><dd>64 grid, corner radius 14. The globe has radius 26.5 (29 in the small version)</dd>
<dt>Rendered</dt><dd>Each pixel is ray-cast through the sphere in numpy and shaded in linear light. No 3D software is involved, so the shape stays exact</dd></dl></div>
</div></section>''')
    # ---------------- sizes
    T.append(f'''<section class="s" id="sizes"><div class="wrap"><header><span class="lab">2 · At real size</span><div><h2>16 to 64 pixels</h2></div>
<p>Shown at 1x, the way a Windows taskbar and the Dock show them. Up to 32 px the flat version is used, and from 48 px the rendered one.</p></header>
<div class="scroll">{strips()}</div><div class="zooms">{zoom16()}</div></div></section>''')
    # ---------------- name
    T.append(f'''<section class="s" id="name"><div class="wrap"><header><span class="lab">3 · Name and lockups</span><div><h2>World Watch, set wide</h2></div>
<p>Set in Mona Sans at 118 % width and weight 640, then turned into outlines so it never falls back to another font.</p></header>
<div class="bigwm">{wmsvg(900)}</div>
<div class="grid g3">
<div class="lock paper">{flat("light", 44, "lk1")}{wmsvg(190, "wm", "#010101")}</div>
<div class="lock night"><img src="{IMG["dark-128"]}" width="44" height="44" alt="">{wmsvg(190, "wm", "#fafafa")}</div>
<div class="lock paper stack"><img src="{IMG["light-128"]}" width="64" height="64" alt="">{wmsvg(150, "wm", "#010101")}</div>
</div>
<div class="rules"><div><b>Space around it</b>Keep a quarter of the icon's height clear on every side of a lockup.</div>
<div><b>Smallest</b>Icon 16 px. The wordmark is 16 px tall in the app's top bar and never smaller than 12 px.</div>
<div><b>Never</b>Tint the globe, put the icon on a photo without its tile, or set the name in another face.</div></div>
</div></section>''')
    # ---------------- colour
    brand = "".join([sw("#010101", "Ink", "Anduril website black", "Globe, text, buttons"),
                     sw("#ffffff", "Porcelain", "White", "Tile, paper, panels"),
                     sw("#ede9fe", "Lavender whisper", "Tailwind violet-100", "Top-left glow"),
                     sw("#e0f2fe", "Sky whisper", "Tailwind sky-100", "Bottom-right glow"),
                     sw("#09090b", "Night", "Tailwind zinc-950", "Dark tile, dark app"),
                     sw("#f4f4f5", "Moon", "Tailwind zinc-100", "Dark twin's globe")])
    ui_rows = [("Background", "#ffffff", "#09090b", "white / zinc-950"), ("Panel", "#ffffff", "#18181b", "white / zinc-900"),
               ("Raised tile", "#fafafa", "#27272a", "zinc-50 / zinc-800"), ("Field, chip", "#f4f4f5", "#27272a", "zinc-100 / zinc-800"),
               ("Hairline", "#e4e4e7", "#3f3f46", "zinc-200 / zinc-700"), ("Text", "#010101", "#fafafa", f"ink / zinc-50 · {ratio('#010101', '#ffffff')} · {ratio('#fafafa', '#18181b')}"),
               ("Second text", "#3f3f46", "#d4d4d8", f"zinc-700 / zinc-300 · {ratio('#3f3f46', '#ffffff')} · {ratio('#d4d4d8', '#18181b')}"),
               ("Quiet text", "#71717a", "#a1a1aa", f"zinc-500 / zinc-400 · {ratio('#71717a', '#ffffff')} · {ratio('#a1a1aa', '#18181b')}"),
               ("Live", "#16a34a", "#4ade80", "green-600 / green-400"), ("Late", "#eab308", "#facc15", "yellow-500 / yellow-400"),
               ("Failing", "#dc2626", "#f87171", "red-600 / red-400"), ("Not set up", "#a1a1aa", "#71717a", "zinc-400 / zinc-500")]
    map_rows = [("Sea", "#f0f9ff", "#09090b", "sky-50 / zinc-950"), ("Land", "#ffffff", "#18181b", "white / zinc-900"),
                ("Borders", "#d4d4d8", "#3f3f46", "zinc-300 / zinc-700"),
                ("Conflict, front line", "#e11d48", "#fb7185", f"rose-600 / rose-400 · {ratio('#e11d48', '#ffffff')} · {ratio('#fb7185', '#18181b')}"),
                ("Military aircraft", "#4338ca", "#a5b4fc", f"indigo-700 / indigo-300 · {ratio('#4338ca', '#ffffff')} · {ratio('#a5b4fc', '#18181b')}"),
                ("Ships", "#0369a1", "#7dd3fc", f"sky-700 / sky-300 · {ratio('#0369a1', '#ffffff')} · {ratio('#7dd3fc', '#18181b')}"),
                ("Space, launches", "#7c3aed", "#c4b5fd", f"violet-600 / violet-300 · {ratio('#7c3aed', '#ffffff')} · {ratio('#c4b5fd', '#18181b')}"),
                ("News places", "#18181b", "#e4e4e7", "zinc-900 / zinc-200, at 16-38 % opacity"),
                ("Document stamp", "#be123c", "#be123c", "rose-700, on paper only")]
    tr = lambda rows: "".join(pair(*r[:3], src=r[3]) for r in rows)
    T.append(f'''<section class="s" id="colour"><div class="wrap"><header><span class="lab">4 · Colour</span><div><h2>Ink, porcelain, two whispers</h2></div>
<p>Every value is a step of the Tailwind CSS palette (v3.4.17) or Anduril's black, as you asked: real colours, none mixed by me. Colour marks a layer or a state and is never decoration. There is no orange anywhere.</p></header>
<div class="swatches">{brand}</div>
<div class="tokgrid"><div><h3>App</h3><table class="tok"><thead><tr><th>Role</th><th>Light</th><th>Dark</th><th>Tailwind · contrast</th></tr></thead><tbody>{tr(ui_rows)}</tbody></table></div>
<div><h3>Map and layers</h3><table class="tok"><thead><tr><th>Role</th><th>Light</th><th>Dark</th><th>Tailwind · contrast on land</th></tr></thead><tbody>{tr(map_rows)}</tbody></table>
<p class="small" style="margin-top:12px">Buttons that act are ink: black on light, white on dark. The selected item gets one ring in ink, never a colour. Contrast is WCAG 2 against the panel (text) or the land (layers).</p></div></div>
</div></section>''')
    # ---------------- type
    T.append(f'''<section class="s" id="type"><div class="wrap"><header><span class="lab">5 · Type</span><div><h2>A cockpit face and a court face</h2></div>
<p>I picked four free faces, each made for a real job. A research pass checked 17 families: who drew each one, what it was made for, and its licence file. All four are SIL Open Font License 1.1 and on Google Fonts.</p></header>
<div class="faces">
{face('<span style="font-family:var(--f-head);font-weight:640;font-stretch:118%">Kharkiv · Now</span>', "Mona Sans", "Headings, the name", "GitHub's typeface, drawn with Degarism and inspired by industrial-era grotesques. It has a width axis from 75 to 125 %. Headings use 112–118 %, so they sit wide like a map.", "OFL 1.1 · Google Fonts", "https://fonts.google.com/specimen/Mona+Sans")}
{face('<span style="font-family:var(--f-text)">RCH4934 over Kyiv</span>', "B612", "Everything you read in the app", "Commissioned by Airbus with ENAC and the Université de Toulouse III, and drawn by Intactile DESIGN for cockpit screens. It was tested for map labels, waypoint lists and capitals mixed with digits, which is this app's job.", "OFL 1.1 · Google Fonts", "https://github.com/polarsys/b612")}
{face('<span style="font-family:var(--f-mono);font-size:30px">253400JT3MQWNDKMJE44</span>', "B612 Mono", "Codes and IDs", "The same cockpit family with every character the same width, used for LEIs, register numbers, transponder addresses and email addresses. Numbers do not need it: B612's own digits all share one width, so counts, times and coordinates line up in plain B612 and keep a narrow point and comma.", "OFL 1.1 · Google Fonts", "https://fonts.google.com/specimen/B612+Mono")}
{face('<span style="font-family:var(--f-doc);font-weight:700">Rosneft Deutschland</span> <span class="stamp" style="font-size:15px;vertical-align:8px">Specimen</span>', "Redaction", "Printed reports and case files", "Jeremy Mickel drew it for Titus Kaphar and Reginald Dwayne Betts' <i>The Redaction</i> (MoMA PS1, 2019), from Times and Century Schoolbook, the faces of US legal documents. Its numbered cuts are degraded like photocopied filings, and Redaction 50 Bold is our stamp.", "OFL 1.1 · Google Fonts since Oct 2026", "https://github.com/jeremymickel/Redaction")}
</div>
<div class="scale">
<div class="row"><span class="k">Display</span><span style="font:640 48px/1 var(--f-head);font-stretch:118%">Porcelain</span><span class="m">Mona Sans 640 · 118 % · 48–96</span></div>
<div class="row"><span class="k">Title</span><span style="font:640 26px/1.1 var(--f-head);font-stretch:112%">Kharkiv</span><span class="m">Mona Sans 640 · 112 % · 26</span></div>
<div class="row"><span class="k">Heading</span><span style="font:640 17px var(--f-head);font-stretch:112%">Now in this view</span><span class="m">Mona Sans 640 · 112 % · 17</span></div>
<div class="row"><span class="k">Text</span><span style="font:13.5px/1.45 var(--f-text)">Machine-coded by GDELT from 95 outlets; not verified.</span><span class="m">B612 400 · 13–15</span></div>
<div class="row"><span class="k">Label</span><span style="font:11px var(--f-text);letter-spacing:.08em;text-transform:uppercase">Signals · outlets, 24 h</span><span class="m">B612 caps · +8 % · 10.5–11</span></div>
<div class="row"><span class="k">Number</span><span style="font:15px var(--f-text);font-variant-numeric:tabular-nums">116,931 km² · FL310 · 49.98 N · 03:08 UTC</span><span class="m">B612 400 · equal-width digits · 11–19</span></div>
<div class="row"><span class="k">Code</span><span style="font:14px var(--f-mono)">LEI 391200PKEUF3Y2NUMW25 · hex 4B820A</span><span class="m">B612 Mono 400 · 11–14</span></div>
<div class="row"><span class="k">Document</span><span style="font:12.5px/1.45 var(--f-doc)">Rosneft declares that no known person or company controls it.</span><span class="m">Redaction 400 / 700 · 12.5 / 34</span></div>
<div class="row"><span class="k">Stamp</span><span><span class="stamp" style="font-size:13px">Consent on file</span></span><span class="m">Redaction 50 Bold caps · documents only</span></div>
</div>
<div class="alts"><div><span class="lab">Considered: public signage</span>{wmsvg(240, "wm", "currentColor", src=alt1)}<span>D-DIN Condensed (German road signs, DIN 1451), Overpass (US highway signs), STIX Two Text and the Big Shoulders Stencil cut (City of Chicago). It has a strong voice, but the text face is plainer.</span></div>
<div><span class="lab">Considered: museum and low vision</span>{wmsvg(240, "wm", "currentColor", src=alt2)}<span>Cooper Hewitt (Smithsonian Design Museum), Atkinson Hyperlegible Next (Braille Institute) and Intel One Mono. It is the most legible set, but the least particular.</span></div></div>
</div></section>''')
    # ---------------- devices
    T.append(f'''<section class="s" id="devices"><div class="wrap"><header><span class="lab">6 · Devices</span><div><h2>Four things that repeat</h2></div>
<p>They come from the icon and from the subject: a footprint, a camera position, porcelain, and the stamp on a filing.</p></header>
<div class="grid g4">
<div class="dev"><div class="demo ringdemo">{ring_demo()}</div><b style="font-family:var(--f-head);font-weight:640;font-stretch:112%">Horizon ring</b><p>The selected thing gets one thin ring, the way the footprint rings Munich. It is ink on light and white on dark, with a halo so it reads on any ground. Never a crosshair.</p></div>
<div class="dev"><div class="demo" style="background:var(--ground)"><div class="seenline"><span>Seen from</span><br>44.2° N 36.0° E · zoom 3.2<br>28 Nov 2026 03:08 UTC</div></div><b style="font-family:var(--f-head);font-weight:640;font-stretch:112%">Seen-from line</b><p>Every map view and every report says where it was seen from and when. The icon says the same thing about itself.</p></div>
<div class="dev"><div class="demo porcel"><div class="levels"><i></i><i></i><i></i></div></div><b style="font-family:var(--f-head);font-weight:640;font-stretch:112%">Porcelain surface</b><p>Panels are white with 18 px corners, a hairline, a light top edge and a soft indigo-tinted shadow. No blur and no glass, which is cheaper for Safari over a moving map.</p></div>
<div class="dev"><div class="demo stamps"><span class="stamp">Specimen</span><span class="stamp">Consent on file</span><span class="stamp">Sanctioned by LEI</span><span class="stamp">Not verified</span></div><b style="font-family:var(--f-head);font-weight:640;font-stretch:112%">Stamps</b><p>Only in printed documents: Redaction 50 Bold in rose-700, slightly crooked, saying a fact about the file. Never on screen and never on the map.</p></div>
</div></div></section>''')
    # ---------------- components
    T.append(f'''<section class="s" id="components"><div class="wrap"><header><span class="lab">7 · Components</span><div><h2>Controls, light and dark</h2></div>
<p>The same parts in both themes: buttons, the page switcher, search, feed states, switches, list rows and layer tiles.</p></header>
<div class="grid g2">{components("l")}{components("d")}</div></div></section>''')
    # ---------------- app
    legend = "".join([legend_row("aerial", "#e11d48", "Air strike, drone", "l"), legend_row("clash", "#e11d48", "Armed clash", "l"),
                      legend_row("attack", "#e11d48", "Attack", "l"), legend_row("protest", "#e11d48", "Protest", "l"),
                      legend_row("strategic", "#4338ca", "Military aircraft by type", "l"), legend_row("news", "#18181b", "News place (dot on the map)", "l")])
    T.append(f'''<section class="s" id="app"><div class="wrap"><header><span class="lab">8 · The app</span><div><h2>The map in Porcelain</h2></div>
<p>Your Dense layout, with the map on the left and the column on the right, redrawn in this look. Everything on it is real: the feeds as the server last stored them, newest at 28 Nov 2026 03:08 UTC.</p></header>
<div class="boards">{mock.board("l", (WM22[0], WM22[2]))}{mock.board("d", (WM22[0], WM22[2]))}</div>
<ul class="legend">{legend}<li><span class="pp" style="background:#e11d48;opacity:.35"></span>Occupied, DeepState ({occ:,} km²)</li><li><span class="pp" style="background:#0369a1"></span>Ships, Finland's open AIS</li></ul>
<div class="notes"><div><b>White land, pale sea</b><p>The land is white and the sea is sky-50, so the porcelain panels float over the map the way the icon's Earth sits on its tile. In dark mode the land is zinc-900 on a zinc-950 sea.</p></div>
<div><b>Your symbols, solid</b><p>These are the 147 approved symbols, drawn solid with a white edge. They are smaller and calmer than in God's eye. News is ink dots sized by outlets, like newsprint.</p></div>
<div><b>What is thin</b><p>World aircraft are left out because the stored snapshot is 9 days old. No earthquakes fell inside this view in USGS's last day, and the USNI carriers are outside it.</p></div></div>
</div></section>''')
    # ---------------- documents
    T.append(f'''<section class="s" id="documents"><div class="wrap"><header><span class="lab">9 · Documents</span><div><h2>Connections report and case file</h2></div>
<p>A4, printed from the app. Both pages hold real answers fetched today. The case file uses the reserved test address, so it names no one.</p></header>
<div class="docs"><div><div class="fit" data-w="794" data-h="1123">{reports.connections(WM22)}</div><p class="cap">GLEIF, Wikidata and OpenSanctions through our Connections code, 28 Nov 12:36 UTC.</p></div>
<div><div class="fit" data-w="794" data-h="1123">{reports.casefile(WM22)}</div><p class="cap">XposedOrNot, Hudson Rock Cavalier, Gravatar, RDAP and crt.sh for test@example.com and example.com, 28 Nov 12:38 UTC.</p></div></div>
</div></section>''')
    # ---------------- splash
    T.append(f'''<section class="s" id="splash"><div class="wrap"><header><span class="lab">10 · Opening</span><div><h2>Splash</h2></div>
<p>Shown while the page connects to the server, on the same porcelain ground as the icon.</p></header>
<div class="splashes">{splash("l")}{splash("d")}</div></div></section>''')
    # ---------------- sources
    T.append(f'''<section class="s" id="sources"><div class="wrap"><header><span class="lab">11 · Sources</span><div><h2>Where everything comes from</h2></div>
<p>So the system can be checked, rebuilt and changed.</p></header>
<div class="srcs">
<h3>Colour and icon</h3>
<p>Tailwind CSS v3.4.17 palette (<span class="mono">src/public/colors.js</span>, MIT). Anduril black <span class="mono">#010101</span> from anduril.com's stylesheet, read in the earlier colour round.</p>
<p>The icon is rendered by our own numpy ray caster from the mark's exact geometry. The sources are in <span class="mono">docs/brand/porcelain/</span>.</p>
<h3>Type</h3>
<p>Mona Sans: GitHub and Degarism. B612 and B612 Mono: Airbus, ENAC, Université de Toulouse III and Intactile DESIGN. Redaction: Jeremy Mickel (MCKL).</p>
<p>All four are under the SIL Open Font License 1.1, which was read in each project's OFL.txt. They load from Google Fonts here. The wordmark is outlined from Mona Sans at 118 % width and weight 640.</p>
<h3>Data on the boards</h3>
<p>App: GDELT Events and GKG, adsb.fi, Fintraffic Digitraffic (CC BY 4.0), DeepState, Launch Library 2 and Natural Earth outlines. All of it is the latest copy in the server's store, newest 28 Nov 2026 03:08 UTC.</p>
<p>Documents: GLEIF (CC0), Wikidata (CC0), OpenSanctions (CC BY-NC 4.0), XposedOrNot, Hudson Rock Cavalier, Gravatar, rdap.org and crt.sh. These were fetched 28 Nov 2026 12:36–12:38 UTC.</p>
<h3>Not tested</h3>
<p>Safari and real screens: everything was checked in headless Chromium only. The icon was not seen on a real Windows taskbar or Dock. There are no .ico or Icon Composer files yet.</p>
<p>B612 for long text is untried in the real app. The Redaction cuts are static fonts, and printing from the browser is untried.</p>
</div></div></section>
<footer class="end"><div class="wrap">World Watch · Porcelain · built 28 Nov 2026 · a proposal: nothing in the app has changed.</div></footer>''')
    T.append('''<script>
(function(){
  function fit(){document.querySelectorAll('.fit').forEach(function(f){var w=+f.dataset.w,h=+f.dataset.h,b=f.firstElementChild;var s=f.clientWidth/w;b.style.transform='scale('+s+')';f.style.height=(h*s)+'px';});}
  document.querySelectorAll('canvas.px16').forEach(function(c){var im=new Image();im.onload=function(){var x=c.getContext('2d');x.fillStyle='#202020';x.fillRect(0,0,16,16);x.drawImage(im,0,0,16,16);};im.src=c.dataset.src;});
  fit();window.addEventListener('resize',fit);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);
})();
</script>''')
    return "\n".join(T)


if __name__ == "__main__":
    (OUT / "porcelain.html").write_text(page())
    print("written", round((OUT / "porcelain.html").stat().st_size / 1024), "KB")
