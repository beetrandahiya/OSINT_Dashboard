import sys, pathlib
HERE = pathlib.Path("/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/between")
LANG = HERE.parent / "lang"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(LANG)); sys.path.append(str(LANG.parent / "logo" / "tools"))
import typo, mock, boards as B
d, w, cap = typo.text_path("monasans-w118-640", "World Watch", 16 / 0.72, -0.005)
bb = typo.ink_bounds("monasans-w118-640", "World Watch", 16 / 0.72, -0.005)
mock.WMVB = f"{bb[0]-.5:.1f} {bb[1]-.5:.1f} {bb[2]-bb[0]+1:.1f} {bb[3]-bb[1]+1:.1f}"; mock.WMH = bb[3] - bb[1] + 1
mock.WMVB_PATH, mock.WMW = d, bb[2] - bb[0] + 1
import suite as S


class CamView:
    def inside(self, lon, lat, pad=0): return S.inview(lon, lat)


mock.V = CamView()
OUT = HERE / "out"
S.IMG = {n: B.b64(str(OUT / f"{n}.webp")) for n in ["s-map", "s-suite"] + [f"t-A-{i}" for i in range(6)]}
PAGES = [("map", "Map", S.map_board, "Your Dense layout with a column on each side. Left: world signals, standing situations and markets. Right: the selected item, what is in view, and twelve layer tiles with each feed's state. On the map: GPS interference, airspace warnings, cables and the front line as well as the usual layers."),
         ("connections", "Connections", S.conn_board, "A live search for Rosneft in GLEIF, Wikidata, the Offshore Leaks and the sanctions lists. PJSC Rosneft is selected; the graph shows where its chain stops, the matches in other registers, and its holdings with their sources."),
         ("investigate", "Investigate", S.inv_board, "The specimen case on the reserved test addresses (they belong to no one): cases and identifiers on the left, the dossier in the middle, and the dated timeline on the right."),
         ("sources", "Sources", S.src_board, "All 45 feeds as the cloud test server logged them at 03:08 UTC: state, ages, size, interval and the last 24 hours of tries. The failing OpenSky feed is selected with its last tries. Your M1 shows different states.")]
figs = []
for key, name, fn, cap in PAGES:
    figs.append(f'''<section class="pg" id="{key}"><div class="wrap"><header><h2>{name}</h2><div class="tog" role="group" aria-label="Theme of this board">
<button type="button" class="on" data-t="d" aria-pressed="true">Dark</button><button type="button" data-t="l" aria-pressed="false">Light</button></div></header>
<p class="lede">{cap}</p><figure>{fn("d")}</figure></div></section>''')
page = f'''<title>Real Earth Suite</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=B612:ital,wght@0,400;0,700&family=B612+Mono:wght@400;700&family=Mona+Sans:wdth,wght@75..125,200..900&display=swap">
<style>{(HERE / "page.css").read_text()}{(LANG / "ui.css").read_text()}{(HERE / "boards.css").read_text()}{(HERE / "suite.css").read_text()}
section.pg{{padding-block:40px;border-bottom:.5px solid var(--line)}}
section.pg header{{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:6px}}
section.pg h2{{font-size:clamp(24px,3vw,36px)}}
section.pg .lede{{color:var(--ink2);margin-bottom:18px}}
section.pg figure{{margin:0}}
section.pg .fit{{box-shadow:0 0 0 .5px var(--line),0 24px 60px -30px rgb(30 27 75 / .45)}}
.tog{{display:flex;gap:2px;padding:3px;border-radius:10px;background:var(--raise);box-shadow:inset 0 0 0 .5px var(--line)}}
.tog button{{font:13px var(--f-text);border:0;background:none;color:var(--ink3);padding:6px 12px;border-radius:8px;cursor:pointer}}
.tog button.on{{background:var(--ink);color:var(--paper)}}
.tog button:focus-visible{{outline:2px solid var(--ink);outline-offset:2px}}
nav.jump{{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}}
nav.jump a{{font-size:13px;padding:7px 12px;border-radius:9px;background:var(--raise);box-shadow:inset 0 0 0 .5px var(--line);text-decoration:none}}
</style>
<header class="top"><div class="wrap"><span class="lab">World Watch · direction A, denser · 28 Nov 2026</span><h1>Real Earth Suite</h1>
<p>Direction A, the NASA photo with see-through Porcelain panels, carried across all four pages and packed with more information. Every number comes from real data. The map uses the server's stored feeds, newest 28 Nov 2026 03:08 UTC. Connections is a live answer from today, and Investigate uses the reserved test addresses only. Each board starts dark; switch it to light above it.</p>
<nav class="jump"><a href="#map">Map</a><a href="#connections">Connections</a><a href="#investigate">Investigate</a><a href="#sources">Sources</a></nav></div></header>
{"".join(figs)}
<section class="next"><div class="wrap"><span class="lab">Next</span><h2 style="margin-top:8px">What I would like to know</h2>
<ol><li>Is this the density you meant, or should a page carry even more, for example a 24-hour timeline under the map?</li>
<li>Do the side columns stay as they are, or should either one fold away to give the map more room?</li>
<li>Once it is right, I draw the remaining screens in this look (each card kind, layers sheet, search, Settings, dossiers, follow mode) before building.</li></ol></div></section>
<footer class="end"><div class="wrap">Real Earth Suite · globes ray-cast from NASA Blue Marble Next Generation with the camera of the God's eye boards. Data: GDELT, adsb.fi, Digitraffic, DeepState, GPSJAM, EASA, FAA, TeleGeography, USNI, USGS, Yahoo, ECB, CoinGecko (store, 03:08 UTC); GLEIF, Wikidata, ICIJ Offshore Leaks, OpenSanctions (live 14:49 UTC); XposedOrNot, Hudson Rock, Gravatar, RDAP, crt.sh (12:38 UTC); the collector's fetch log. Checked in headless Chromium only. A proposal: nothing in the app has changed.</div></footer>
<script>(function(){{
function fit(){{document.querySelectorAll('.fit').forEach(function(f){{var w=+f.dataset.w,h=+f.dataset.h,b=f.firstElementChild,s=f.clientWidth/w;b.style.transform='scale('+s+')';f.style.height=(h*s)+'px';}});}}
document.querySelectorAll('section.pg').forEach(function(sec){{var b=sec.querySelector('.board');sec.querySelectorAll('.tog button').forEach(function(btn){{btn.addEventListener('click',function(){{
b.classList.remove('d','l');b.classList.add(btn.dataset.t);sec.querySelectorAll('.tog button').forEach(function(x){{var on=x===btn;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on?'true':'false');}});}});}});}});
fit();addEventListener('resize',fit);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);}})();</script>'''
(OUT / "suite.html").write_text(page)
print(round(len(page) / 1024), "KB")
