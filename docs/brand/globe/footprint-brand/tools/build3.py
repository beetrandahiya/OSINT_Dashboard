"""Footprint in real brand colours: every hex from an official brand file, guideline or the brand's own code."""
import base64, html, json, pathlib, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "logo" / "tools"))
import typo  # noqa: E402
from fp import footprint  # noqa: E402
from opts import cr  # noqa: E402

OUT = HERE / "out"
(OUT / "png").mkdir(parents=True, exist_ok=True)
esc = lambda s: html.escape(s, quote=True)
F = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")

SRC = {
    "nasa": ("NASA brand guidelines: insignia colours", "https://www.nasa.gov/nasa-brand-center/brand-guidelines/",
             "NASA Blue PMS 286 #0032A0, NASA Red PMS 185 #E4002B, read from NASA's colour chart (round one)."),
    "apple": ("Apple Human Interface Guidelines: Color, system colours", "https://developer.apple.com/design/human-interface-guidelines/color",
              "Values from the HIG's colour table (updated 9 June 2025): Indigo 97/85/245 = #6155F5, Blue 0/136/255 = #0088FF, Cyan 0/192/232 = #00C0E8 (light appearance)."),
    "telegram": ("Telegram logo file", "https://telegram.org/img/t_logo.svg",
                 "The logo's own gradient stops, #2AABEE to #229ED9, and white."),
    "nato": ("NATO Visual Identity Guidelines 2016", "https://www.act.nato.int/wp-content/uploads/2023/06/NATO-VIGs-2016-en.pdf",
             "Dark blue PMS 280 #004990, light blue PMS 2718 #118ACB (round one)."),
    "anduril": ("Anduril website colours", "https://www.anduril.com/",
                "Black #010101 and the lime of its loading bar #DFF140, from the site's code (round one). Not a published guide."),
    "signal": ("Signal Desktop source code", "https://github.com/signalapp/Signal-Desktop/blob/main/stylesheets/_variables.scss",
               "$color-ultramarine-logo #3B45FD, $color-ultramarine #2C6BED."),
}

OPTS = [
    dict(key="nasa", name="NASA, insignia order", rank=1, src="nasa",
         mark=dict(plate="#FFFFFF", globe="#0032A0", fp="#FFFFFF", pupil="#E4002B"),
         sw=[("#0032A0", "NASA Blue", "globe"), ("#E4002B", "NASA Red", "pupil: Munich"), ("#FFFFFF", "White", "tile and footprint")],
         why="The colours in the order NASA's insignia uses them: a blue disc, white drawn on it, one red accent. The footprint "
             "becomes a white patch of light on a blue Earth, and the red point is Munich. Strongest contrast of the set at every size.",
         weak="On a light taskbar the white tile blends in (the blue globe still stands out, as with any white-tile app icon). "
              "It borrows NASA's look; for a private tool that is homage, not a problem."),
    dict(key="apple", name="Apple Indigo and Blue", rank=2, src="apple",
         mark=dict(plate="#6155F5", globe="#0088FF", fp="#FFFFFF", pupil="#6155F5"),
         sw=[("#6155F5", "Indigo", "tile, pupil"), ("#0088FF", "Blue", "globe"), ("#FFFFFF", "White", "footprint")],
         why="Apple's own system colours, as Apple's icons use them: a saturated colour background and white for the subject. "
             "Looks at home in the macOS Dock beside Apple's apps.",
         weak="Indigo tile and blue globe are close in brightness, so at 16 px the globe edge is soft (the white footprint still reads)."),
    dict(key="telegram", name="Telegram sky blue", rank=3, src="telegram",
         mark=dict(plate="#FFFFFF", globe="#2AABEE", fp="#FFFFFF", pupil="#229ED9"),
         sw=[("#2AABEE", "Light blue", "globe"), ("#229ED9", "Blue", "pupil"), ("#FFFFFF", "White", "tile, footprint")],
         why="The brightest and friendliest: Telegram's sky blue as the Earth, white light on it.",
         weak="Lowest contrast inside the mark (2.6 to 3.0): fine at 32 px and up, soft at 16 px. Reads more 'messaging app' than 'intelligence'."),
    dict(key="nato", name="NATO blues", rank=0, src="nato",
         mark=dict(plate="#118ACB", globe="#004990", fp="#FFFFFF", pupil="#118ACB"),
         sw=[("#004990", "Dark blue PMS 280", "globe"), ("#118ACB", "Light blue PMS 2718", "tile, pupil"), ("#FFFFFF", "White", "footprint")],
         why="The alliance's two blues: serious, official, and the white footprint glows on the dark globe.", weak="Only blues; less memorable than NASA."),
    dict(key="anduril", name="Anduril lime", rank=0, src="anduril",
         mark=dict(plate="#DFF140", globe="#010101", fp="#FFFFFF", pupil="#010101"),
         sw=[("#DFF140", "Lime", "tile"), ("#010101", "Black", "globe, pupil"), ("#FFFFFF", "White", "footprint")],
         why="The loudest: defence-tech lime with a black Earth. Impossible to miss on a taskbar.",
         weak="A black ball with a white spot can read as an 8-ball; the lime vanishes on a light taskbar."),
    dict(key="apple-white", name="Apple Blue and Cyan, white globe", rank=0, src="apple",
         mark=dict(plate="#0088FF", plate2="#00C0E8", globe="#FFFFFF", fp="#6155F5", pupil="#000000"),
         sw=[("#0088FF", "Blue", "tile, top"), ("#00C0E8", "Cyan", "tile, bottom"), ("#6155F5", "Indigo", "footprint"), ("#FFFFFF", "White", "globe")],
         why="Apple's gradient-tile style with the original white globe.", weak="White globe with a coloured iris is the cartoon-eye look you called AI."),
    dict(key="nasa-classic", name="NASA, blue tile", rank=0, src="nasa",
         mark=dict(plate="#0032A0", globe="#FFFFFF", fp="#E4002B", pupil="#FFFFFF"),
         sw=[("#0032A0", "NASA Blue", "tile"), ("#E4002B", "NASA Red", "footprint"), ("#FFFFFF", "White", "globe, pupil")],
         why="NASA's colours with a white globe and a red footprint.", weak="A red iris on a white ball reads as an angry eye."),
    dict(key="signal", name="Signal ultramarine", rank=0, src="signal",
         mark=dict(plate="#3B45FD", globe="#FFFFFF", fp="#2C6BED", pupil="#000000"),
         sw=[("#3B45FD", "Ultramarine (logo)", "tile"), ("#2C6BED", "Ultramarine", "footprint"), ("#FFFFFF", "White", "globe")],
         why="Signal's electric blue tile.", weak="White globe with a blue iris again: closest to the version you rejected."),
]

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
    return f'<svg x="{F(x)}" y="{F(y)}" width="{F(size)}" height="{F(size)}" viewBox="0 0 64 64">{svg[svg.index(">") + 1: svg.rindex("</svg>")]}</svg>'


APP = dict(dark=dict(bg="#0B0D10", panel="#1A1E24", line="#2A3038", ink="#F2F4F6", sub="#9AA3AD"),
           light=dict(bg="#F5F6F8", panel="#FFFFFF", line="#DCE0E5", ink="#0B0D10", sub="#5A6470"))


def topbar(o, tone):
    t = APP[tone]
    acc = o["sw"][0][0] if o["sw"][0][0] != "#FFFFFF" else o["sw"][1][0]
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
    b += f'<circle cx="{w - 98}" cy="30" r="4" fill="{acc}"/>' + T(w - 88, 35, "Feeds", 12.5, t["ink"], 500)
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Top bar, {tone}">{b}</svg>'


def splash(o, tone):
    t = APP[tone]
    w, h = 960, 340
    b = f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>' + icon_at(o, "full", 80, 80, 180)
    p, _ = wordmark(t["ink"], 310, 170, 44)
    b += p + T(312, 214, "Real data only. Every layer shows its source.", 22, t["sub"])
    return f'<svg class="spec" viewBox="0 0 {w} {h}" role="img" aria-label="Splash, {tone}">{b}</svg>'


def render():
    marks = {o["key"]: {"full": footprint("full", o["mark"]), "small": footprint("small", o["mark"])} for o in OPTS}
    (OUT / "marks.json").write_text(json.dumps(marks))
    subprocess.run(["node", str(HERE.parent / "globe" / "strips.js"), str(OUT / "marks.json"), str(OUT / "png")], check=True)
    (OUT / "marks").mkdir(exist_ok=True)
    for k, m in marks.items():
        (OUT / "marks" / f"footprint-{k}.svg").write_text(m["full"])
        (OUT / "marks" / f"footprint-{k}-small.svg").write_text(m["small"])


def png(k, bg):
    return "data:image/png;base64," + base64.b64encode((OUT / "png" / f"{k}-{bg}.png").read_bytes()).decode()


def big(o, size):
    return footprint("full", o["mark"]).replace("<svg ", f'<svg width="{size}" height="{size}" class="big" aria-hidden="true" ', 1)


def contrast(o):
    m = o["mark"]
    pairs = [("tile / globe", m["plate"], m["globe"]), ("globe / footprint", m["globe"], m["fp"]), ("footprint / pupil", m["fp"], m["pupil"])]
    return "".join(f'<span class="cr{" low" if cr(a, b) < 3 else ""}">{n} <b>{cr(a, b):.1f}</b></span>' for n, a, b in pairs)


def card(o, detail):
    src = SRC[o["src"]]
    tag = {1: "My pick", 2: "Second", 3: "Third"}.get(o["rank"], "")
    s = f'<section class="opt{" top" if detail else ""}" id="{o["key"]}">'
    s += f'<div class="head">{big(o, 150 if detail else 110)}<div class="txt"><p class="eyebrow">{tag}</p><h2>{esc(o["name"])}</h2>'
    s += f'<p>{esc(o["why"])}</p><p class="weak">{esc(o["weak"])}</p></div></div>'
    s += '<ul class="sw">' + "".join(f'<li><span class="chip" style="background:{h}"></span><b>{esc(n)}</b> <code>{h}</code> <span>{esc(r)}</span></li>' for h, n, r in o["sw"]) + "</ul>"
    s += f'<p class="note">Source: <a href="{src[1]}">{esc(src[0])}</a>. {esc(src[2])}</p>'
    s += f'<p class="crs">Contrast {contrast(o)}</p>'
    s += '<div class="sizes">' + "".join(f'<figure><img class="px" src="{png(o["key"], bg)}" alt=""><figcaption>{lab}</figcaption></figure>'
                                        for bg, lab in (("dark", "Windows, dark"), ("light", "Windows, light"), ("dock", "macOS Dock"))) + "</div>"
    if detail:
        s += f'<div class="zoom"><img class="z3" src="{png(o["key"], "dark")}" alt=""><img class="z3" src="{png(o["key"], "light")}" alt=""></div>'
        s += topbar(o, "dark") + topbar(o, "light") + '<div class="pair">' + splash(o, "dark") + splash(o, "light") + "</div>"
    return s + "</section>"


def main():
    render()
    css = (HERE / "page3.css").read_text()
    body = ('<title>Footprint brand colours</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Space+Grotesk:wght@500;600&display=swap">'
            f'<style>{css}</style><main class="wrap">' + (HERE / "intro3.html").read_text())
    body += '<div class="ov">' + "".join(f'<a class="ovc" href="#{o["key"]}">{big(o, 96)}<b>{esc(o["name"])}</b></a>' for o in OPTS) + "</div>"
    body += "".join(card(o, o["rank"] in (1, 2, 3)) for o in OPTS)
    body += (HERE / "outro3.html").read_text() + "</main>"
    body += ("<script>document.querySelectorAll('img.z3').forEach(i=>{const s=()=>{i.style.width=i.naturalWidth*3+'px'};"
             "i.complete?s():i.addEventListener('load',s)})</script>")
    (OUT / "page.html").write_text(body)
    print(round(len(body) / 1024), "KB")


if __name__ == "__main__":
    main()
