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
import suite_assets as SA


class CamView:
    def inside(self, lon, lat, pad=0): return S.inview(lon, lat)


mock.V = CamView()
OUT = HERE / "out"
S.IMG = {n: B.b64(str(OUT / f"{n}.webp")) for n in ["s-map", "s-map-full", "s-conn", "s-air", "s-sea"] + [f"t-A-{i}" for i in range(6)]}
PAGES = [("map", "Map", S.map_board, "Both side panels open; the views now sit behind one button (bottom left). Left: world signals, standing situations and markets. Right: the selected item, what is in view, and twelve layer tiles with each feed's state. On the map: GPS interference, airspace warnings, cables, the front line, protests, news, military aircraft and ships."),
         ("map-folded", "Map, panels put away", lambda t: S.map_board(t, folded=True), "Both side panels fully retracted with the buttons in the top bar (beside the logo and beside Settings), leaving small tabs at the screen edges to bring them back. The Views button is open here, showing the six views."),
         ("connections", "Connections, graph", S.conn_board, "No globe behind it now. A live search for Rosneft in GLEIF, Wikidata, the Offshore Leaks and the sanctions lists; PJSC Rosneft selected, with where its chain stops, its matches in other registers, and its holdings with their sources."),
         ("connections-map", "Connections, on the map", S.conn_map_board, "The same company on the globe, because the registers say where: 22 of the 25 companies in this chain have a headquarters or registered address in Wikidata or GLEIF, or are a site with its own coordinates. Lines run from Rosneft to each holding; the chain continues from Rosneft Deutschland in Berlin to its Austrian holding. Three have no location in either register and are listed, not guessed."),
         ("connections-air", "Their aircraft now: Lufthansa", lambda t: SA.air_board(S, t), "A worked example on live data from 15:22 UTC today. Deutsche Lufthansa AG's chain comes from GLEIF and Wikidata as before; each aircraft near Munich is linked by its register entry (solid) or only by its flight number (dashed). SWR868L is selected: a Swiss flight flown by an aircraft registered to airBaltic, which is outside the group."),
         ("connections-sea", "Their ships now: Finnlines", lambda t: SA.sea_board(S, t), "The same for ships, on Finland's open AIS feed at 15:27 UTC. A ship is linked when its IMO number leads to a Wikidata ship item that names an owner or operator; the company is then followed up its own chain. Finnlines is selected: eight ships, owned in turn by Grimaldi Group in Palermo, where GLEIF's chain stops."),
         ("investigate", "Investigate", S.inv_board, "No globe: nothing here belongs on a map, and placing a person is something the tool never does. The specimen case on the reserved test addresses: cases and identifiers on the left, the dossier in the middle, the dated timeline on the right."),
         ("sources", "Sources", S.src_board, "No globe. All 45 feeds as the cloud test server logged them at 03:08 UTC, with the failing OpenSky feed selected. Your M1 shows different states.")]
HOW = """<section class="pg how" id="how"><div class="wrap"><h2>How a company's aircraft and ships get onto the map</h2>
<p class="lede">Connections already builds a company's chain. Linking its assets is a join on identifiers that the registers and the live feeds both carry. Nothing is matched on a look-alike name, the paint, a route or an airport.</p>
<ol class="flow">
<li><span class="lab">1 · The chain</span><b>Companies above and below the subject</b><p>GLEIF parents and children by LEI; Wikidata parent organisation, owners and subsidiaries. Joined where both carry the same LEI.</p></li>
<li><span class="lab">2 · Their identifiers</span><b>What each company is known by</b><p>Airline code (ICAO, Wikidata P230, e.g. SWR) and exact names. For ships: the ships Wikidata says it owns (P127) or operates (P137), with their IMO numbers (P458).</p></li>
<li><span class="lab">3 · The live feeds</span><b>What each aircraft or ship carries</b><p>Aircraft: the callsign it broadcasts, and its registered owner from the free registers (adsbdb, else hexdb.io) by transponder address. Ships: the IMO number in its AIS message.</p></li>
<li><span class="lab">4 · The link</span><b>Drawn with its source and its words</b><p>Registered owner: solid. Flight number only: dashed. Owner outside the chain or unknown: said on the card, not drawn as ownership.</p></li></ol>
<div class="notes"><div><b>Cost</b><p>Callsigns match instantly. Register lookups go one a second and are kept 14 days; the app already makes them for aircraft cards. Wikidata answers 300 IMO numbers per query, refreshed daily. No keys, nothing to install.</p></div>
<div><b>Limits</b><p>A register can name a leasing company or a sister airline; none of the 80 owners found below was a lessor. Owners of ordinary cargo ships are not in any free source. Sanctioned ships and aircraft keep their own match, by IMO and registration, as now.</p></div></div></div></section>"""
figs = []
for key, name, fn, cap in PAGES:
    if key == "connections-air": figs.append(HOW)
    figs.append(f'''<section class="pg" id="{key}"><div class="wrap"><header><h2>{name}</h2><div class="tog" role="group" aria-label="Theme of this board">
<button type="button" class="on" data-t="d" aria-pressed="true">Dark</button><button type="button" data-t="l" aria-pressed="false">Light</button></div></header>
<p class="lede">{cap}</p><figure>{fn("d")}</figure></div></section>''')
page = f'''<title>Real Earth Suite</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=B612:ital,wght@0,400;0,700&family=B612+Mono:wght@400;700&family=Mona+Sans:wdth,wght@75..125,200..900&display=swap">
<style>{(HERE / "page.css").read_text()}{(LANG / "ui.css").read_text()}{(HERE / "boards.css").read_text()}{(HERE / "suite.css").read_text()}{(HERE / "assets.css").read_text()}
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
section.how .flow{{list-style:none;margin:20px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
section.how .flow li{{background:var(--raise);border-radius:14px;padding:14px 16px;box-shadow:inset 0 0 0 .5px var(--line)}}
section.how .flow b{{display:block;font:640 16px var(--f-head);font-stretch:110%;margin:6px 0 4px}}
section.how .flow p,section.how .notes p{{margin:0;font-size:14px;color:var(--ink2);line-height:1.5}}
section.how .notes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-top:12px}}
section.how .notes>div{{padding:12px 16px;border-radius:14px;border:0!important;box-shadow:inset 0 0 0 .5px var(--line)}}
section.how .notes b{{font-size:13px}}
nav.jump a{{font-size:13px;padding:7px 12px;border-radius:9px;background:var(--raise);box-shadow:inset 0 0 0 .5px var(--line);text-decoration:none}}
</style>
<header class="top"><div class="wrap"><span class="lab">World Watch · direction A, denser · 28 Nov 2026</span><h1>Real Earth Suite</h1>
<p>Direction A on all four pages, third round. The small edge tabs stay. New: how a company's aircraft and ships would get onto the map, shown with two worked examples on live data from this afternoon (Lufthansa's aircraft, Finnlines' ships). Every number comes from real data. The map uses the server's stored feeds, newest 28 Nov 2026 03:08 UTC. Connections is a live answer from today, and Investigate uses the reserved test addresses only. Each board starts dark; switch it to light above it.</p>
<nav class="jump"><a href="#map">Map</a><a href="#map-folded">Panels put away</a><a href="#connections">Connections</a><a href="#connections-map">On the map</a><a href="#how">How assets are linked</a><a href="#connections-air">Aircraft</a><a href="#connections-sea">Ships</a><a href="#investigate">Investigate</a><a href="#sources">Sources</a></nav></div></header>
{"".join(figs)}
<section class="next"><div class="wrap"><span class="lab">Next</span><h2 style="margin-top:8px">What I would like to know</h2>
<ol><li>Is this the kind of link you meant? Solid for a register entry, dashed for a flight number only, and the mismatches spelled out (a Swiss flight on an airBaltic aircraft).</li>
<li>The other way round too: on the Map page, an aircraft or ship card would name its registered owner (aircraft cards already do), with "Open in Connections" to see the whole chain.</li>
<li>Should "Their aircraft and ships now" be a switch in Connections (as drawn), or always on?</li>
<li>Then I draw the remaining screens in this look (each card kind, layers sheet, search, Settings, dossiers, follow mode) before building.</li></ol></div></section>
<footer class="end"><div class="wrap">Real Earth Suite · globes ray-cast from NASA Blue Marble Next Generation with the camera of the God's eye boards. Data: GDELT, adsb.fi, Digitraffic, DeepState, GPSJAM, EASA, FAA, TeleGeography, USNI, USGS, Yahoo, ECB, CoinGecko (store, 03:08 UTC); GLEIF, Wikidata, ICIJ Offshore Leaks, OpenSanctions (live 14:49 UTC); adsb.fi, adsbdb, hexdb.io, Digitraffic, GLEIF, Wikidata for the two examples (15:22-15:31 UTC); XposedOrNot, Hudson Rock, Gravatar, RDAP, crt.sh (12:38 UTC); the collector's fetch log. Checked in headless Chromium only. A proposal: nothing in the app has changed.</div></footer>
<script>(function(){{
function fit(){{document.querySelectorAll('.fit').forEach(function(f){{var w=+f.dataset.w,h=+f.dataset.h,b=f.firstElementChild,s=f.clientWidth/w;b.style.transform='scale('+s+')';f.style.height=(h*s)+'px';}});}}
document.querySelectorAll('section.pg').forEach(function(sec){{var b=sec.querySelector('.board');sec.querySelectorAll('.tog button').forEach(function(btn){{btn.addEventListener('click',function(){{
b.classList.remove('d','l');b.classList.add(btn.dataset.t);sec.querySelectorAll('.tog button').forEach(function(x){{var on=x===btn;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on?'true':'false');}});}});}});}});
fit();addEventListener('resize',fit);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fit);}})();</script>'''
(OUT / "suite.html").write_text(page)
print(round(len(page) / 1024), "KB")
