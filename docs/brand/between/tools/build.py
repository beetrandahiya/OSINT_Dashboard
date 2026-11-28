import sys, base64, pathlib
HERE = pathlib.Path("/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between")
LANG = pathlib.Path("/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/lang")
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(LANG)); sys.path.append(str(LANG.parent / "logo" / "tools"))
import typo
import boards as B, mock
OUT = HERE / "out"
d, w, cap = typo.text_path("monasans-w118-640", "World Watch", 16 / 0.72, -0.005)
bb = typo.ink_bounds("monasans-w118-640", "World Watch", 16 / 0.72, -0.005)
mock.WMVB = f"{bb[0]-.5:.1f} {bb[1]-.5:.1f} {bb[2]-bb[0]+1:.1f} {bb[3]-bb[1]+1:.1f}"; mock.WMH = bb[3] - bb[1] + 1
mock.WMVB_PATH, mock.WMW = d, bb[2] - bb[0] + 1
img = lambda n: B.b64(str(OUT / n))
th = lambda k: [img(f"t-{k}-{i}.webp") for i in range(6)]
G = {k: img(f"g-{k}.webp") for k in ["A", "B-l", "B-d", "C-l", "C-d"]}
T = {k: th(k) for k in ["A", "B-l", "B-d", "C-l", "C-d"]}
D = mock.data()


def pair(k_l, k_d, pal_l, pal_d, mat_l, mat_d, cap_l, cap_d):
    return (f'<div class="pair"><figure>{B.board("x", "light", G[k_l], T[k_l], pal_l, mat_l)}<figcaption>Light. {cap_l}</figcaption></figure>'
            f'<figure>{B.board("x", "dark", G[k_d], T[k_d], pal_d, mat_d)}<figcaption>Dark. {cap_d}</figcaption></figure></div>')


page = f'''<title>Three Earths</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=B612:ital,wght@0,400;0,700&family=B612+Mono:wght@400;700&family=Mona+Sans:wdth,wght@75..125,200..900&display=swap">
<style>{(HERE / "page.css").read_text()}{(LANG / "ui.css").read_text()}{(HERE / "boards.css").read_text()}</style>
<header class="top"><div class="wrap"><span class="lab">World Watch · between Porcelain and God's eye · 28 Nov 2026</span><h1>Three Earths</h1>
<p>The panels are Porcelain on every board: its fonts, colours, buttons, list and tiles, in your Dense layout. What changes is the Earth under them and the space around it, which is where God's eye lives. Same theatre view, same data on all six: the server's stored feeds, newest 28 Nov 2026 03:08 UTC.</p>
<div class="axes">
<div><b>A · Real Earth, smoked panels</b>Closest to God's eye.<div class="k"><span>Earth</span><span>NASA photo</span><span>Space</span><span>black, blue rim</span><span>Panels</span><span>see-through porcelain</span></div></div>
<div><b>B · Ink Earth</b>The icon at full size. My pick.<div class="k"><span>Earth</span><span>black seas, charcoal land</span><span>Space</span><span>porcelain white / night</span><span>Panels</span><span>solid porcelain</span></div></div>
<div><b>C · Silver Earth</b>Closest to Porcelain.<div class="k"><span>Earth</span><span>the photo without colour</span><span>Space</span><span>porcelain white / night</span><span>Panels</span><span>solid porcelain</span></div></div>
</div></div></header>

<section class="dir" id="a"><div class="wrap"><header><span class="lab">A</span><h2>Real Earth, smoked panels</h2></header>
<p class="lede">God's eye's NASA photo and black space, with Porcelain's parts made slightly see-through so the Earth shows under them. There is no blur, which was what made Safari slow before.</p>
{pair("A", "A", "dark", "dark", "smoke", "smoke", "White panels at 90 % over the photo.", "Near-black panels at 78 %.")}
<div class="notes"><div><b>What it keeps</b>The real colours of the land: deserts, forests, snow. It is the most "God's eye" of the three.</div>
<div><b>What it costs</b>Colour markers compete with the photo's browns and greens, which is why orange had to go. Picture tiles are also the heaviest ground to draw.</div>
<div><b>In the app</b>The Photo ground already exists. Only the panels change.</div></div></div></section>

<section class="dir" id="b"><div class="wrap"><header><span class="lab">B</span><h2>Ink Earth</h2><span class="pick">My pick</span></header>
<p class="lede">The icon at full size: black seas, charcoal land with hairline borders and a little relief, and a pale atmosphere along the sunlit edge. In light mode the globe hangs in white porcelain space; in dark mode it sits in night.</p>
{pair("B-l", "B-d", "dark", "dark", "porcelain-bg", "porcelain-bg", "White porcelain panels and white space around a black Earth, like the icon's tile.", "The same black Earth on zinc-950 night with the faint lavender and blue of the dark icon.")}
<div class="notes"><div><b>Why I pick it</b>It is the brand and the map in one picture. Every colour marker reads on black, and nothing in the ground pretends to know more than a border.</div>
<div><b>What it costs</b>Nothing extra: it is a vector style with no picture tiles, so it is lighter to draw than the photo. The photo stays one click away under Settings › Ground.</div>
<div><b>To check in the app</b>Whether MapLibre's globe leaves the space around it transparent, so the white or night page shows through. I have not tried that yet.</div></div></div></section>

<section class="dir" id="c"><div class="wrap"><header><span class="lab">C</span><h2>Silver Earth</h2></header>
<p class="lede">NASA's photo with the colour taken out: real mountains, rivers and coasts in greys. In light mode it is a pale porcelain Earth on white; in dark mode a dim silver one on night.</p>
{pair("C-l", "C-d", "light", "dark", "porcelain-bg", "porcelain-bg", "A light Earth needs the dark marker colours of the light theme.", "Real terrain without colour; markers keep the dark theme's colours.")}
<div class="notes"><div><b>What it keeps</b>The terrain detail of the photo, without its colours fighting the markers.</div>
<div><b>What it costs</b>The light version is soft: land and sea are both pale, so at a glance it reads less clearly than A or B. It still loads picture tiles, like the photo.</div>
<div><b>In the app</b>It is the Mono ground recoloured: warm grey on white instead of cold blue on black.</div></div></div></section>

<section class="next"><div class="wrap"><span class="lab">Next</span><h2 style="margin-top:8px">Once you pick</h2>
<ol><li>Which Earth is the default: A, B or C. The other grounds stay in Settings either way.</li>
<li>Panels solid (B, C) or see-through (A), whichever Earth you pick.</li>
<li>Then I draw every panel and screen in it before building anything: each kind of card (event, aircraft, ship, satellite, base, outage), the layers sheet and key, search, Settings, feeds, person and country dossiers, follow mode, look down, Connections and Investigate pages, empty and dead-feed states.</li></ol>
</div></section>
<footer class="end"><div class="wrap">World Watch · Three Earths · globes ray-cast from NASA Blue Marble Next Generation and Natural Earth outlines with the camera of the God's eye boards (35.0° N 19.0° E, 2,676 km up). Markers: GDELT, adsb.fi, Digitraffic and DeepState as stored at 03:08 UTC. Checked in headless Chromium only. A proposal: nothing in the app has changed.</div></footer>
<script>(function(){{function fit(){{document.querySelectorAll('.fit').forEach(function(f){{var w=+f.dataset.w,h=+f.dataset.h,b=f.firstElementChild,s=f.clientWidth/w;b.style.transform='scale('+s+')';f.style.height=(h*s)+'px';}});}}
fit();addEventListener('resize',fit);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);}})();</script>'''
(OUT / "three-earths.html").write_text(page)
print(round(len(page) / 1024), "KB")
