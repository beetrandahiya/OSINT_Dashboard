"""Footprint colour options page: every colour sampled from a real picture or a real paint standard."""
import base64, html, json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "logo" / "tools"))
import typo  # noqa: E402
from fp import footprint  # noqa: E402

OUT = HERE / "out"
esc = lambda s: html.escape(s, quote=True)
F = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")
b64 = lambda p: base64.b64encode(pathlib.Path(p).read_bytes()).decode()

SRC = {
    "epic": dict(img="out/epic_small.jpg", title="NASA DSCOVR EPIC, natural colour, 25 Nov 2026 11:01 UTC",
                 url="https://epic.gsfc.nasa.gov/", note="The whole sunlit Earth from 1.5 million km, centred 19° S 3° E. NASA, public domain."),
    "s2": dict(img="out/s2_small.jpg", title="Copernicus Sentinel-2A, Munich (tile 32UPU), 26 Sep 2026, 0 % cloud",
               url="https://browser.dataspace.copernicus.eu/?zoom=9&lat=48.1&lng=11.5",
               note="The satellite in the mark, over home: Ammersee and Starnberger See bottom centre. Contains modified Copernicus Sentinel data 2026."),
    "corona": dict(img="out/corona_small.jpg", title="CORONA KH-4B frame DS1107-2298DA015, Baikonur, 11 Aug 1969",
                   url="https://commons.wikimedia.org/wiki/File:Baikonur_Cosmodrome_imaged_by_KH-4B_on_1969-08-11_-_DS1107-2298DA015.jpg",
                   note="America's first photo-reconnaissance satellite, declassified in 1995. Public domain (USGS)."),
    "fs": dict(img=None, title="U.S. Federal Standard 595C paint chips",
               url="https://people.csail.mit.edu/jaffer/Color/FED-STD-595C.txt",
               note="Measured chip values (CIE XYZ, illuminant C) from Aubrey Jaffer's table of the GSA data, converted to sRGB with a Bradford adaptation to D65. 36320 and 36375 are the 'Compass Ghost' greys of the F-15; 36118 is Gunship Gray."),
}


def C(hexv, name, what, src, derived=False):
    return dict(hex=hexv, name=name, what=what, src=src, derived=derived)


OPTS = [
    dict(key="two", name="Two satellites", rank=1,
         idea="The globe in the colour of the ocean as NASA's deep-space camera saw it; the footprint in the colour of the fields "
              "Sentinel-2 photographed around Munich; the pupil in Munich's forest.",
         mark=dict(plate="#000000", globe="#2F3C4D", fp="#837F5E", pupil="#101A06"),
         swatches=[C("#000000", "Space", "EPIC's own background around the disc", "epic"),
                   C("#2F3C4D", "Ocean", "darkest of 7 colour groups on the disc, 13 % of it: open ocean", "epic"),
                   C("#837F5E", "Fields", "lightest of 7 groups in the Munich scene, 6 %: harvested fields", "s2"),
                   C("#101A06", "Forest", "darkest group in the Munich scene, 13 %: forest in shadow", "s2"),
                   C("#B9BCBB", "Cloud", "lightest group on the EPIC disc, 10 %: cloud tops", "epic"),
                   C("#7C7E81", "Haze", "EPIC group, 17 %: thin cloud over sea", "epic")],
         srcs=["epic", "s2"],
         dark=dict(bg="#000000", panel="#11161C", line="#2F3C4D", ink="#B9BCBB", sub="#7C7E81", acc="#837F5E"),
         light=dict(bg="#ECEDEC", panel="#FFFFFF", line="#B9BCBB", ink="#101A06", sub="#484F57", acc="#2F3C4D"),
         derived="#11161C and #ECEDEC are steps between sampled colours for panels and the light background; #484F57 is an EPIC group.",
         good="The richest and the most World Watch: two real satellites in one mark, far and near, and home in the middle. Muted, "
              "physical colours that no UI kit ships with. The olive footprint keeps the eye from looking like a cartoon.",
         weak="Dark: on a dark taskbar the blue globe sits close to the black plate at 16 px (still visible, less punchy). "
              "The olive can read as khaki or military."),
    dict(key="epic", name="Whole Earth", rank=2,
         idea="All from one picture of the whole Earth: black space, ocean, and cloud white for the lit footprint.",
         mark=dict(plate="#000000", globe="#2F3C4D", fp="#B9BCBB", pupil="#000000"),
         swatches=[C("#000000", "Space", "EPIC's background", "epic"), C("#2F3C4D", "Ocean", "darkest group, 13 %", "epic"),
                   C("#B9BCBB", "Cloud", "lightest group, 10 %", "epic"), C("#7C7E81", "Haze", "17 %", "epic"),
                   C("#7B6A5B", "Desert", "Sahara and Namib, 10 %", "epic"), C("#484F57", "Sea under haze", "18 %", "epic")],
         srcs=["epic"],
         dark=dict(bg="#000000", panel="#11161C", line="#2F3C4D", ink="#B9BCBB", sub="#7C7E81", acc="#B9BCBB"),
         light=dict(bg="#ECEDEC", panel="#FFFFFF", line="#B9BCBB", ink="#11161C", sub="#484F57", acc="#2F3C4D"),
         derived="#11161C and #ECEDEC are steps between sampled colours.",
         good="Calm and clear: the lit footprint is the brightest thing, as it should be. One source, one story.",
         weak="A pale iris with a black pupil can look like a blind or ghostly eye. Less colour than Two satellites."),
    dict(key="ghost", name="Compass Ghost", rank=3,
         idea="The paint of air-superiority fighters: the two-tone ghost greys of the F-15, Gunship Gray and Navy black.",
         mark=dict(plate="#595F66", globe="#C5CACA", fp="#69737D", pupil="#333333"),
         swatches=[C("#595F66", "36118 Gunship Gray", "plate", "fs"), C("#C5CACA", "36495 Light Gray", "globe", "fs"),
                   C("#69737D", "36176 Ocean Gray", "footprint", "fs"), C("#333333", "37038 Black", "pupil", "fs"),
                   C("#8B969F", "36320 Dark Ghost Gray", "lines", "fs"), C("#9BA3AA", "36375 Light Ghost Gray", "secondary text", "fs")],
         srcs=["fs"],
         dark=dict(bg="#333333", panel="#4C5050", line="#595F66", ink="#C5CACA", sub="#9BA3AA", acc="#8B969F"),
         light=dict(bg="#C5CACA", panel="#FFFFFF", line="#9BA3AA", ink="#333333", sub="#595F66", acc="#69737D"),
         derived="#4C5050 is chip 36081 (F-4 Deep Gray); white panels are not a chip.",
         good="The most 'defence': colours that really are painted on surveillance and fighter aircraft. Quiet, cold, expensive-looking.",
         weak="No colour at all: on a grey Windows taskbar it can disappear, and it says 'military' more than 'world'."),
    dict(key="s2", name="Munich from orbit", rank=0,
         idea="Only the Munich scene: a dark forest globe on an olive plate, with the footprint in field colour.",
         mark=dict(plate="#4E5033", globe="#101A06", fp="#837F5E", pupil="#101A06"),
         swatches=[C("#101A06", "Forest", "13 %", "s2"), C("#1E2A11", "Woodland", "17 %", "s2"), C("#2E3E20", "Meadow", "13 %", "s2"),
                   C("#4E5033", "Farmland", "22 %", "s2"), C("#837F5E", "Fields", "6 %", "s2"), C("#0B2B1C", "Lakes", "Ammersee and Starnberger See", "s2")],
         srcs=["s2"],
         dark=dict(bg="#101A06", panel="#1E2A11", line="#3A3D22", ink="#837F5E", sub="#656445", acc="#837F5E"),
         light=dict(bg="#E9E8DF", panel="#FFFFFF", line="#837F5E", ink="#101A06", sub="#4E5033", acc="#2E3E20"),
         derived="#E9E8DF is a light step of the field colour for the light background.",
         good="Entirely home: every colour is a piece of land around Munich, the lakes included.",
         weak="Reads as camouflage: olive and khaki say 'army surplus' before they say 'satellite'. Low contrast on a dark taskbar."),
    dict(key="corona", name="CORONA film", rank=0,
         idea="The greys of the first spy-satellite photographs.",
         mark=dict(plate="#4B4B4B", globe="#C5C5C5", fp="#7B7B7B", pupil="#4B4B4B"),
         swatches=[C("#4B4B4B", "Shadow", "15 %", "corona"), C("#606060", "Steppe", "31 %", "corona"), C("#7B7B7B", "Ground", "24 %", "corona"),
                   C("#9E9E9E", "Salt pan", "19 %", "corona"), C("#C5C5C5", "Highlights", "11 %", "corona")],
         srcs=["corona"],
         dark=dict(bg="#4B4B4B", panel="#606060", line="#7B7B7B", ink="#C5C5C5", sub="#9E9E9E", acc="#C5C5C5"),
         light=dict(bg="#C5C5C5", panel="#E2E2E2", line="#9E9E9E", ink="#4B4B4B", sub="#606060", acc="#4B4B4B"),
         derived="#E2E2E2 is a light step for panels.",
         good="The best story for a spy-feel tool, and timeless: film greys never look like a template.",
         weak="Neutral grey only, no depth; at 16 px the pupil barely separates from the footprint."),
    dict(key="current", name="Round two (for comparison)", rank=-1,
         idea="What you saw: Palantir Blueprint's interface colours.",
         mark=dict(plate="#111418", globe="#F6F7F9", fp="#2D72D2", pupil="#111418"),
         swatches=[], srcs=[], dark={}, light={}, derived="",
         good="", weak="Interface blue on white is what makes it look generated: the same blue as every web app, on a cartoon-white eyeball."),
]

# ------------------------------------------------------------------ wordmark (Geist SemiBold, outlined)
WM = typo.text_path("geist-600", "World Watch", 100, -0.012)


def wordmark(fill, x, base, cap):
    d, w, capu = WM
    s = cap / capu
    return f'<path transform="translate({F(x)} {F(base)}) scale({F(s)})" d="{d}" fill="{fill}"/>', w * s


def T(x, y, s, size, fill, weight=400, fam="Inter", anchor="start"):
    return (f'<text x="{F(x)}" y="{F(y)}" font-family="{fam}, system-ui, sans-serif" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def icon_at(o, v, x, y, size):
    svg = footprint(v, o["mark"])
    inner = svg[svg.index(">") + 1: svg.rindex("</svg>")]
    return f'<svg x="{F(x)}" y="{F(y)}" width="{F(size)}" height="{F(size)}" viewBox="0 0 64 64">{inner}</svg>'


def topbar(o, tone):
    t = o[tone]
    w, h = 960, 60
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/><line x1="0" y1="{h - .5}" x2="{w}" y2="{h - .5}" stroke="{t["line"]}"/>'
    b += icon_at(o, "small", 18, 15, 30)
    p, ww = wordmark(t["ink"], 60, 37, 13)
    b += p
    x = 60 + ww + 34
    for i, n in enumerate(["Map", "Connections", "Investigate", "Sources"]):
        wd = 9 + len(n) * 7.3
        if i == 0:
            b += f'<rect x="{F(x - 10)}" y="16" width="{F(wd + 8)}" height="28" rx="8" fill="{t["panel"]}"/>'
        b += T(x, 35, n, 13.5, t["ink"] if i == 0 else t["sub"], 600 if i == 0 else 500)
        x += wd + 18
    b += f'<rect x="{w - 330}" y="15" width="200" height="30" rx="15" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    b += T(w - 314, 35, "Find a person or country", 12.5, t["sub"])
    b += f'<rect x="{w - 116}" y="15" width="98" height="30" rx="15" fill="none" stroke="{t["line"]}"/>'
    b += f'<circle cx="{w - 98}" cy="30" r="4" fill="{t["acc"]}"/>' + T(w - 88, 35, "Feeds", 12.5, t["ink"], 500)
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Top bar, {tone}">{b}</svg>'


def splash(o, tone):
    t = o[tone]
    w, h = 960, 360
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>' + icon_at(o, "full", 80, 90, 180)
    p, _ = wordmark(t["ink"], 310, 180, 44)
    b += p + T(312, 226, "Real data only. Every layer shows its source.", 22, t["sub"])
    b += T(312, 280, "Sentinel-2 at 786 km sees 27.1° around Munich", 20, t["acc"], 500, "IBM Plex Mono")
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Splash, {tone}">{b}</svg>'


def render_strips():
    marks = {o["key"]: {"full": footprint("full", o["mark"]), "small": footprint("small", o["mark"])} for o in OPTS}
    (OUT / "marks.json").write_text(json.dumps(marks))
    subprocess.run(["node", str(HERE.parent / "globe" / "strips.js"), str(OUT / "marks.json"), str(OUT / "png")], check=True)
    (OUT / "marks").mkdir(exist_ok=True)
    for k, m in marks.items():
        (OUT / "marks" / f"footprint-{k}.svg").write_text(m["full"])
        (OUT / "marks" / f"footprint-{k}-small.svg").write_text(m["small"])


def png(k, bg):
    return "data:image/png;base64," + b64(OUT / "png" / f"{k}-{bg}.png")


def big(o, size=220):
    svg = footprint("full", o["mark"])
    return svg.replace("<svg ", f'<svg width="{size}" height="{size}" class="big" aria-hidden="true" ', 1)


def section(o):
    if o["key"] == "current":
        return ""
    k = o["key"]
    rank = {1: "My pick", 2: "Second", 3: "Third"}.get(o["rank"], "Also sampled")
    s = f'<section class="opt" id="{k}"><p class="eyebrow">{rank}</p><h2>{esc(o["name"])}</h2><p class="idea">{esc(o["idea"])}</p>'
    s += f'<div class="hero">{big(o)}<div class="srcs">'
    for sk in o["srcs"]:
        src = SRC[sk]
        img = f'<img src="data:image/jpeg;base64,{b64(HERE / src["img"])}" alt="" class="srcimg">' if src["img"] else ""
        s += f'<figure class="src">{img}<figcaption><a href="{src["url"]}">{esc(src["title"])}</a><br>{esc(src["note"])}</figcaption></figure>'
    s += "</div></div>"
    s += '<ul class="sw">' + "".join(
        f'<li><span class="chip" style="background:{c["hex"]}"></span><b>{esc(c["name"])}</b><code>{c["hex"]}</code><span>{esc(c["what"])}</span></li>'
        for c in o["swatches"]) + "</ul>"
    if o["derived"]:
        s += f'<p class="note">{esc(o["derived"])}</p>'
    s += '<h3>At real size</h3><div class="sizes">' + "".join(
        f'<figure><img class="px" src="{png(k, bg)}" alt=""><figcaption>{lab}</figcaption></figure>'
        for bg, lab in (("dark", "Windows, dark"), ("light", "Windows, light"), ("dock", "macOS Dock"))) + "</div>"
    s += f'<div class="zoom"><img class="z3" src="{png(k, "dark")}" alt=""><img class="z3" src="{png(k, "light")}" alt=""></div>'
    s += "<h3>In use</h3>" + topbar(o, "dark") + topbar(o, "light")
    s += '<div class="pair">' + splash(o, "dark") + splash(o, "light") + "</div>"
    s += f'<div class="verdict"><div><h4>What works</h4><p>{esc(o["good"])}</p></div><div><h4>What does not</h4><p>{esc(o["weak"])}</p></div></div>'
    return s + "</section>"


def small(o, size):
    svg = footprint("small" if size <= 24 else "full", o["mark"])
    return svg.replace("<svg ", f'<svg width="{size}" height="{size}" aria-hidden="true" ', 1)


def overview():
    s = '<div class="ov">'
    for o in OPTS:
        s += (f'<a href="#{o["key"]}" class="ovc{" dim" if o["key"] == "current" else ""}">{big(o, 120)}'
              f'<span class="ovs">{small(o, 32)}{small(o, 24)}{small(o, 16)}</span>'
              f'<b>{esc(o["name"])}</b></a>')
    return s + "</div>"


def main():
    render_strips()
    css = (HERE / "page2.css").read_text()
    body = ('<title>Footprint colours</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Space+Grotesk:wght@500;600&display=swap">'
            f"<style>{css}</style><main class=\"wrap\">")
    body += (HERE / "intro2.html").read_text() + overview()
    body += "".join(section(o) for o in OPTS)
    body += (HERE / "outro2.html").read_text()
    body += ("</main><script>document.querySelectorAll('img.z3').forEach(i=>{const s=()=>{i.style.width=i.naturalWidth*3+'px'};"
             "i.complete?s():i.addEventListener('load',s)})</script>")
    (OUT / "page.html").write_text(body)
    print(round(len(body) / 1024), "KB")


if __name__ == "__main__":
    main()
