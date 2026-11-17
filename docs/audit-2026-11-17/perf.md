# perf audit: what makes World Watch heavy (measured 2026-11-17)

Scripts, raw results and CPU profiles: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/perf/
(harness.js = scenario runner with CDP metrics + rAF/setInterval/setData/triggerRepaint attribution; exp.js = idle-repaint
experiment that removes one cause per phase; startup.js; stall.py / probe.py = server event-loop probes; top.js = self time
from a .cpuprofile; res-*.json / log-*.txt = results; prof-*.cpuprofile).

How to read the numbers: headless Chromium here has software GL and the 4-core machine ran at load 7-29 from other
auditors, so absolute ms are inflated and "frames/s" is capped by GL speed (1-8 fps). The reliable signals are COUNTS:
repaint requests/s, setData calls/s and their sizes, rAF loops/s, requests and bytes/min, DOM nodes, and the relative
self-time ranking inside CPU profiles. On the owner's Mac each forced frame is cheap but there are 60-120 of them a
second (ProMotion), with globe + terrain + buildings + thousands of icons in each: anything that keeps the map
repainting while nothing changes is the main cost there.

## Ranked findings

### 1. Hotspot pulse repaints the whole map every animation frame, forever   [severity: high]  [confirmed by running]
Repro: exp.js / `FAKE_HOT=1 node harness.js hot '["hotspots"]' 0 '{"center":[114,22],"zoom":4}' 30 1` (one hotspot injected
via page.route; the owner had one live, Shenzhen, and the all-on run here got one from the server).
Seen: `hotspots.js:18` rAF at the full frame rate; `setPaintProperty` x2 per frame (hotspots.js:16-17) = map repaint every
frame; with one hotspot the map never goes idle (frames/s = GL maximum in every phase of exp.js until the pulse stopped:
4.2-7.6 fps -> 1.8 fps with reduced motion). Chip is on by default.
Cause: hotspots.js:12-19 `pulse()` animates a paint property; every paint-property change re-renders every layer, terrain,
globe, 3D buildings and all custom layers (models3d, satellites canvas).
Fix: draw the pulse outside the WebGL map: one `maplibregl.Marker` per hotspot with a CSS `@keyframes` ring (compositor-only,
costs ~nothing, honours `prefers-reduced-motion` in CSS), or draw it on an existing overlay canvas. If it must stay in the map:
step it at ~8 Hz instead of every frame. Expected gain: idle map frames from 60-120/s to ~0 when only hotspots are on.
Risk: low (look changes slightly; markers must be removed/added on data change).

### 2. models3d asks for a repaint every frame at zoom >= 7, even with zero aircraft or aircraft chips off   [high]  [confirmed by running]
Repro: `node harness.js none-z9 '[]' 0 '{"center":[11.6,48.3],"zoom":9}' 30` (all layers off), and exp.js phase A (aircraft off).
Seen: trig `models3d.js:243` = 3.5/s and 4.2/s = one per rendered frame, `stats.items: 0`. The map renders continuously at
zoom >= 7 regardless of layers. With aircraft on it is continuous by design (playback), and per frame it also: loops every
world aircraft through `inLive()` haversine before the cheap `inView` test (aircraft.js:566; `inLive` is the top JS
function in the zoom-9 profile, 1.1 % of all samples, above any MapLibre function), allocates a `new THREE.Matrix4()` per
aircraft and a `Float64Array` per `getMatrixForModel` call (models3d.js:163-185), rebuilds `drawn`/`items`/`groups`, and
re-projects the selected aircraft's whole trail with `getMatrixForModel` per point (models3d.js:212).
Cause: models3d.js:243 unconditional `map.triggerRepaint()`.
Fix: `if (items.length && anyMoving) map.triggerRepaint();` where anyMoving = some drawn aircraft has `held === false` or its
smoothed position moved > 0.3 px since the last frame; optionally cap to 30 fps (`if (t - lastT < 33) requestAnimationFrame
(() => map.triggerRepaint())`). In the provider test `inView(a.lon, a.lat)` before `inLive(a)`, and cache the inLive result
per world snapshot / viewInfo change (it only changes when either changes). Reuse a pool of Matrix4s instead of
`new THREE.Matrix4()` per item. Expected gain: idle at zoom >= 7 from continuous to 0 frames; with aircraft on, ~7,000
haversines/frame removed (~0.3-0.5 ms/frame on a Mac, i.e. 20-60 ms/s at 60-120 Hz).
Risk: low; check that the playback still advances while held aircraft wait (they need no repaint).

### 3. Hidden layers keep working and keep the map repainting: timers that never check "is my layer on / did anything change"   [high]  [confirmed by running]
Repro: `node harness.js none-flat '[]' 0 '{}' 60` (every chip off).
Seen with all layers off: map still rendered 1.6 fps (= continuous bursts here), repaint requests 4.3/s; setData calls on
hidden sources: `ww-air-vip` 0.5/s and `ww-air-doom` 0.5/s (aircraft.js:483, 522, every 2 s whether on or not, whether or
not anything changed), `ww-sats` 0.5/s plus `triggerRepaint` (space.js:243 `tick()` every 2 s: SGP4 for all ~1,050
satellites, then setData of an EMPTY collection and a repaint, even with Satellites off), `ww-news` 5,538-6,230 features,
`ww-air` 7,273 features, `ww-ships` 640, quakes 194 re-sent on every poll although hidden. Each setData sends the whole
collection to a worker, re-indexes it and starts a symbol-fade period (~300 ms of continuous frames).
exp.js phase B (drop setData whose data is identical to the last one): unchanged-data setData calls fell from ~2.2/s to
~0.7/s; phase D (pulse/animations off as well): repaint requests 4.7/s and 1.8 fps, the rest is the satellite tick.
Also: sky.js:76 recomputes the 384x384 night picture (147k pixels of trig + PNG encode + texture upload) every minute even
when Night is off.
Cause: main.js:117-121 `load()` always calls `layer.render(map)`; VIP/doomsday/satellite intervals ignore `on`.
Fix: (a) in main.js `load()`, skip `onData/render` when `d.fetched` equals the last one seen for that feed (see 6), and skip
`render` while the layer is off, rendering on `visible(true)` instead; (b) vip/doomsday: render only from `onData` and from
the aircraft feeds' updates, and only when on; (c) space.js `tick()`: return early when `!shown` (no propagation, no
setData, no repaint); on the globe, skip the setData entirely (it is always empty there); (d) night: skip when off.
Expected gain: idle with everything off from a repaint burst every ~0.7 s to none; ~1,050 SGP4 runs every 2 s removed.
Risk: low; layers must render once when switched on (call `render` in `show()`).

### 4. Aircraft glide sends three GeoJSON sources to the workers 5 times a second, including when the icons are hidden   [high]  [confirmed by running]
Repro: `node harness.js air-z9 '["aircraft","military"]' 0 '{"center":[11.6,48.3],"zoom":9}' 45 1`, and air-z6.
Seen: `ww-air-live`, `ww-air-mil` (~145 features), `ww-air-extra` each 3.4 setData/s (5/s intended, throttled here) =
~10-15 setData/s; MapLibre-internal repaint requests 48/s (z9) and 71/s (z6). At zoom >= 7 all three icon layers have
maxzoom 7 (invisible) so all of it is waste; at world view (< 5.2) only military-feed aircraft move, by sub-pixel amounts
(40 s playback delay, positions every 30 s). `main.js:149` also `setData`s `ww-pick` every 200 ms while a moving item is
selected, even when `ring()` returns 0 (models draw their own ring).
Cause: aircraft.js:418 interval, glide() at aircraft.js:198-212; main.js:149 + ring() main.js:192-197.
Fix: in the interval, `if (isOn()) return;` (models draw them; icons hidden) except the selected aircraft's flat extras;
below `VIEW_MIN_ZOOM` glide at 1 Hz (or only on new military data); at 5.2-7 keep 5 Hz but only for `ww-air-live`, and send
`ww-air-mil` only when a military aircraft moved > 1 px. In ring(): remember the last value and skip setData when it is the
same empty collection. Expected gain: at zoom >= 7, ~15 worker round-trips + placement passes/s -> 0; at world view 15/s -> ~2/s.
Risk: low-medium: check the selected aircraft's ring/route on the flat map between zoom 5.2 and 7.

### 5. Server sends every feed's full payload on every poll, re-serialised and gzipped at level 9 each time; clients poll faster than the data changes and fetch feeds for layers that are off, some twice   [high]  [confirmed by running]
Seen (browser, CDP Network): default layers 2.4 MB/min (40 req/min) per tab = ~145 MB/hour; all layers 2.5 MB/min; all layers
OFF still 1.0 MB/min (news alone 764-804 KB/min). Payloads (raw / gzip): news 2.8 MB / 0.8 MB, news_translated 3.2 MB /
1.0 MB, cameras 1.9 / 0.29, sites 1.6 / 0.44, aircraft_world 1.3 / 0.27, fires 0.71 / 0.18, cables 0.68 / 0.23, gps 0.60 /
0.13, sanctioned 0.58 / 0.07, unrest 0.45-0.6 / 0.13. Client intervals vs server intervals: news 60 s vs 120 s, news_translated
120 vs 300, aircraft_world 120 vs 1,200 (10x), quakes 30 vs 60, outages 120 vs 300. No ETag / If-None-Match, so an unchanged
2.8 MB news payload is downloaded, JSON-parsed (~21 ms in V8 here) and fully re-rendered every minute.
Duplicate polls: `ships` (ships + warships: 2 per minute measured), `unrest` (unrest + unrestSingle: 2 per 2 min, 132 KB gz each),
`cf_radar` (hijacks + outages), `airspace` and `navwarn` (their layer + launches), `vip_aircraft` (vip + doomsday).
Startup: 52 /api/data requests, 4.9 MB gzipped, before the map is usable, including cameras (286 KB) and sites (431 KB),
whose chips are off by default.
Server cost per poll: news 140-165 ms of server time per request; Python: json.dumps in the event loop news 58 ms, sites 78 ms;
gzip level 9 news 542 ms, sites 543 ms, fires 264 ms, aircraft_world 202 ms vs level 6: 140 / 48 / 47 / 47 ms for 1-2 % larger
output (measured on the saved payloads; machine under load). Starlette 1.7 puts gzip of > 128 KB in a worker thread, so
it costs CPU rather than event-loop time; json.dumps still blocks the loop.
Cause: web.py:72-85 `data()` builds a JSONResponse per request; web.py:1025 `GZipMiddleware(minimum_size=2000)` (default
compresslevel 9); main.js:135 polls every feed of every layer at the layer's own `feeds` interval, on or off, per layer.
Fix (server): keep per feed a cached `(version, body_bytes, gzip_bytes, etag)` built once when a fetch stores a new payload
(in a thread); `data()` returns the cached bytes with `ETag` and answers `304` to a matching `If-None-Match`; set
`GZipMiddleware(compresslevel=6)` for everything else. (Ships merges the live AIS stream per request: cache it for 10 s.)
Fix (client): poll a feed only while some layer using it is on (fetch once on switch-on); one timer per feed, not per layer
(dedupe the `[feed]` set across LAYERS, fan the data out to every layer that uses it); poll at max(layer interval, server
`interval` from /api/status); send `If-None-Match` (the browser does it automatically when the response has an ETag and
`cache: 'no-cache'` is used instead of `no-store`). Expected gain: per tab from ~2.4 MB/min to a few KB/min when idle
(news changes every 2-5 min: ~0.4 MB/min worst case); server CPU per poll from ~0.15-0.6 s to ~0; browser JSON.parse +
full re-render of unchanged data disappears; startup ~0.7 MB smaller.
Risk: medium (touches every layer's data path; "x min ago" texts must keep updating from the status poll, not from refetches).

### 6. Hijack streaks: a full-screen 2D canvas redrawn at display rate with ~5,000 strokes per frame   [medium]  [confirmed by running]
Repro: `node harness.js hijacks '["hijacks"]' 0 '{}' 30 1`.
Seen: `netwatch.js:84` rAF 52/s; script 205 ms per second of main thread (20 %) with nothing else on; profile self time:
`animate` 9.6 %, `rgba` (string formatting of a colour per segment) 2.4 %, `stroke` 1.5 %, `project` 1.1 %, `addColorStop`.
Chip is on by default. Per frame: per flow (up to 120) 22 tail steps x (map.project + 2 x beginPath/stroke with a fresh
`rgba(...)` string) + a radial gradient per head; `lighter` compositing in dark mode over a devicePixelRatio-2 canvas on
the Mac. Runs whether or not anything is visible on screen.
Cause: netwatch.js:39-85.
Fix: cap to 30 fps (skip frames by timestamp); precompute a 16-step alpha table of style strings once per theme; batch all
segments of the same alpha bucket into one path and stroke once per bucket (2 x 16 strokes per frame instead of ~5,000);
cache each flow's projected points until the map moves (`map.on('move')` sets a dirty flag); skip flows whose bbox is off
screen; stop the loop while the tab is hidden (rAF does) and while the map is moving fast (optional). Expected gain:
~5-10x less canvas work per frame; at 30 fps half again. Risk: low (look nearly identical).

### 7. Satellites on the globe: matchMedia() called once per satellite per frame, plus per-satellite matrix allocation and two canvas calls per dot   [medium]  [confirmed by running]
Repro: `W=640 H=400 node harness.js sats-globe '["satellites"]' 1 '{}' 30 1`.
Seen: top JS self time on the globe is `matchMedia` (123 ms of 31 s, above `drawHeights` 52 ms and `sgp4` 48 ms), via
`tint(s)` -> `isDark()` (space.js:76-77) for each of ~1,050 satellites every frame; `place()` -> `clip()` ->
`transform.getMatrixForModel` allocates a Float64Array(16) and does a 4x4 product per satellite per frame (space.js:84-86);
each dot is its own beginPath/arc/fill/stroke (space.js:181-184). The canvas is also cleared every map frame when
Satellites is off (space.js:161-167, `drawHeights` runs from an always-present custom layer).
Fix: read dark once per frame (`const dk = isDark()` at the top of drawHeights, pass it in); compute `getMatrixForModel`'s
origin column analytically (Earth-centred position x the map's matrix; the code already derives the camera) or call it once
per satellite only when the 2 s tick moves them, caching screen-independent world positions; batch dots by colour into one
path each (4 classes + spy); in drawHeights return before `clearRect` when nothing was drawn last frame and `!shown`.
Expected gain: ~1,000 matchMedia + ~1,000 allocations per frame removed; canvas calls from ~4,000 to ~10 per frame.
Risk: low.

### 8. The list: ~1,400 rows (~9,000 DOM nodes) rebuilt from scratch on every feed update, with a slow date formatter per row   [medium]  [confirmed by running]
Seen: all layers: 1,402 list rows, 8,973 live DOM nodes; CDP node count swings 17k-147k over 6 min (detached garbage from
each rebuild); news alone: 1,174 rows. `local()` (util.js:25-29, `toLocaleDateString('en-GB', {...})` creates an Intl formatter
per call) is the top JS function in the default-layers profile (2.1 % of all samples, ~1.5 s per 70 s), `renderList` 0.8 %.
renderList runs after every one of ~40 feed loads and every 20 s (main.js:121, 445); renderChips rebuilds all 40 chips
each time too.
Fix: `const DF = new Intl.DateTimeFormat('en-GB', {day: 'numeric', month: 'short'})` once, and memoise `local(t)` per minute;
coalesce renderList/renderChips to at most one per animation frame or per second (`queueMicrotask`/rAF flag); render only
the first ~150 rows and append more on scroll (the list is newest-first, nobody reads row 1,400); compare row data, not a
1 MB HTML string. Expected gain: list work per update ~10x smaller, far fewer GC pauses. Risk: low.

### 9. Server recomputes hotspots and news spikes on every request   [medium]  [confirmed by running]
Seen: `/api/hotspots` 0.53-0.60 s per request on a quiet machine (2.3-8.5 s under load), `/api/news/spikes` 0.5-0.7 s (and
2.0 s under load), `/api/people/today` 0.38-0.8 s; during a spikes request a cheap route waited up to 168 ms (GIL
contention from the thread). Each tab asks hotspots every 5 min, spikes every 2 min; hotspots internally recomputes
spikes and patterns again. Results only change when the news window / unrest / military feeds change.
Cause: web.py:972-984 hotspot_list and news spikes route compute per call (news.py:410-450 walks every article of both
windows with a regex, urlparse and `_headline()` each).
Fix: compute spikes once per news/news_translated fetch (in the feed function, in a thread) and keep the result; compute
hotspots once per fetch of any input feed (or at most once a minute) and serve the cached JSON bytes. Expected gain:
~1 s CPU per tab every 2-5 min -> ~0; no loop jitter. Risk: low.

### 10. Server writes ~8 MB/min to SQLite, mostly re-saving unchanged multi-MB payloads   [medium]  [confirmed by running]
Seen: /proc/<pid>/io write_bytes +41.8 MB in 303 s (8.3 MB/min, ~12 GB/day); `latest` rows: news_translated 3.2 MB (every
300 s), news 2.6 MB (every 120 s), cameras 1.9, sites 1.7, aircraft_world 1.2, unrest 0.6 MB (every 120 s); WAL then
checkpoints copy them again. `log_fetch` also runs `DELETE FROM fetches WHERE started < ?` on every fetch with no index on
`started` (9,373 rows now; ~150k after 7 days -> full scan every second or so).
Cause: collector.py:126 `db.save_latest` after every successful fetch; db.py:50-56.
Fix: save `latest` only when the payload changed (compare a hash of the serialized bytes you now build anyway for 5) and, for
news / news_translated / unrest (rebuilt from data/gdelt on start), at most every 15 min; add `CREATE INDEX fetches_started
ON fetches(started)` or prune once an hour. Expected gain: ~10x fewer bytes written. Risk: low (after a crash the
restored news is up to 15 min old; it refills on the first fetch anyway).

### 11. three.js and all 47 aircraft/helicopter models load at startup, before the map is usable   [medium]  [confirmed by running]
Seen (startup.js, fresh profile): 6 three.js files 455 KB gz (three.core.js is 1.46 MB of JS to parse/compile) + 49 model
requests 538 KB, all finished before the map's style was loaded, competing with 24 base-map tiles and 52 data requests.
They are only needed at zoom >= 7 with Aircraft/Military on.
Cause: models3d.js:12-14 static imports and the eager loader at models3d.js:63-68; main.js imports models3d eagerly.
Fix: `attachModels` loads `three` with dynamic `import()` the first time zoom >= 6.5 with an aircraft chip on; fetch the generic
model first and others on demand by type (types.json already maps type -> file). Expected gain: ~1 MB and 55 requests
less at startup, ~1.5 MB less JS parsed for users who stay zoomed out. Risk: low-medium (first zoom-in shows icons for a
moment longer).

### 12. Every /api/data poll continues in hidden tabs; most intervals have no `document.hidden` check   [low]  [by reading only]
main.js:135 feed intervals, main.js:444 status every 5 s, munich.js:65, markets.js:27, patterns.js:19, sanctioned.js:24,
spikes.js:21, hotspots.js:38, people.js:85, sky.js:76/177/213, space.js:243 (the SGP4 tick) run regardless; only
aircraft.js:418/483/522 and main.js:149 check `document.hidden`. Safari throttles background timers but does not stop
them, so a forgotten tab keeps pulling ~1-2.4 MB/min. Fix: one `visibilitychange` handler that pauses the feed scheduler
and resumes with an immediate refresh. Risk: low.

### 13. Server RSS keeps growing: 424 MB at 2 min, 477 MB at 8 min, 566 MB at 35 min, 609 MB at 88 min   [medium]  [confirmed by running, cause not isolated]
Server CPU averaged 15-20 % of a core over 88 min (with ~6 auditors' browsers polling it). CLAUDE.md's last figure was
~205 MB steady. Part is expected (the 6 h news and 24 h unrest windows were still filling after the restart: news payload grew
1.5 -> 2.8 MB), part is likely allocator growth from re-serialising multi-MB JSON per request (finding 5) and the 96k
military areas held as Python objects. Could not attach a profiler here. Fix: after 5 and 10, measure on the Mac with
`tracemalloc` snapshots 1 h apart; keep big static tables (military areas) as compact arrays or in SQLite. Risk: none.

### 14. Smaller items   [low]
- sky.js:76 night picture rebuilt every minute when Night is off (by reading; see 3).
- models3d trail: `setRibbon` reallocates all six attributes and the index whenever the trail length changes (every new
  track point while selected) (models3d.js:108-115; by reading). Allocate to a capacity and use `setDrawRange`.
- Loading bar `place()` calls `getBoundingClientRect` (forced layout) on every map `idle` and request start (main.js:50-57, 74);
  cheap, but `idle` fires after every burst. Only place it when the bar becomes visible.
- Chase camera: `map.jumpTo` each frame fires `moveend` each frame; all `moveend` handlers are debounced, so it is fine,
  but aircraft area polling then relies only on the 5 s interval (by reading).
- `/api/status` every 5 s is 25 KB raw / ~8 KB gz (91 KB/min); fine, could drop to 15 s when the Feeds panel is closed.

## Inventory: timers, loops and per-frame work (measured rates from res-*.json, file:line)

| Where | What | Rate | Stops when layer off? | Stops when tab hidden? | Stops when nothing changed? |
|---|---|---|---|---|---|
| hotspots.js:12-19 pulse | 2 setPaintProperty -> full map repaint | every frame while >= 1 hotspot | yes | rAF yes | NO (runs forever) |
| models3d.js:243 render | triggerRepaint, provider loop over all aircraft, three.js render, overlay canvas | every frame at zoom >= 7 | NO | rAF yes | NO |
| netwatch.js:39-85 animate | full-screen 2D canvas, ~5k strokes | every frame (52/s here) | yes | rAF yes | no (animation) |
| space.js custom layer -> drawHeights | clear + redraw satellite canvas | every map frame | partly (still clears) | n/a | no |
| space.js:243 tick | SGP4 for ~1,050 sats, setData, triggerRepaint | 2 s | NO | NO | NO |
| aircraft.js:418 glide | setData live / mil / extras | 200 ms | if both aircraft chips off | yes | NO; also at zoom >= 7 where icons are hidden |
| main.js:149 ring | setData ww-pick | 200 ms while a moving item is picked | n/a | yes | NO |
| aircraft.js:483 / 522 vip, doomsday render | vipNow() over all aircraft + setData | 2 s each | NO | yes | NO |
| aircraft.js:230 liveCard | update card numbers | 1 s | returns early without card | NO | cheap |
| aircraft.js:419 loadView | /api/aircraft/area (zoom >= 5.2) | 5 s | ? (only when aircraft view applies) | NO | n/a |
| aircraft.js:254 loadTrack | /api/track for selected | 45 s | n/a | NO | n/a |
| main.js:135 feed polls | /api/data/<feed> per layer per feed, then onData+render+renderChips+renderList+refreshPick | 30 s - 6 h per feed | NO (polled and rendered while off) | NO | NO (full re-render of unchanged data) |
| main.js:444 loadStatus | /api/status | 5 s | n/a | NO | n/a |
| main.js:445 | renderFeeds + renderList | 20 s | n/a | NO | compares HTML string after building it |
| munich.js:65 | 3 feeds + render | 20 s | only while Munich view active | NO | yes (html compare) |
| markets.js:27 | 3 feeds 60 s, render 20 s | | n/a | NO | |
| sky.js:76 night | 384x384 picture + PNG + upload | 60 s | NO | NO | NO |
| sky.js:177 lightning / sky.js:213 live photo | tile time refresh | 60 s / 120 s | lightning ? / live photo yes | NO | |
| patterns.js:19 | /api/aircraft/patterns | 120 s | NO | NO | |
| sanctioned.js:24 | /api/sanctioned/live | 60 s | NO | NO | |
| spikes.js:21 | /api/news/spikes (0.5-2 s server CPU) | 120 s | NO | NO | |
| hotspots.js:38 | /api/hotspots (0.5-8 s server CPU) | 300 s | NO | NO | |
| people.js:85 | leaders today | 600 s | NO | NO | |
| ships.js:34 | ship trail | 60 s while a ship is picked | n/a | NO | |
| cameras.js:118/123 | camera picture refresh | 3-60 s while a camera card is open | cleared when card closes (by reading) | NO | |
| main.js:355-369 chase | jumpTo every frame | while following | n/a | rAF yes | by design |

## Settings worth exposing (a "Performance" section) and defaults
- Motion: Full / Reduced / Off (default Full; "Off" = no hotspot pulse, no hijack streaks, no aircraft playback between reports,
  aircraft redrawn only on new reports). Today only the OS Reduce Motion switch does part of this.
- Frame cap for animations (30 / 60 / display) - default 30 for netwatch streaks and the hotspot pulse.
- 3D aircraft models: On / Off, start zoom (default 7), max models (default 300, nearest the centre first), labels on models on/off.
- Satellite letters and orbit rings on the globe: on/off (default on below 160 in view as now).
- Update rates: "Live" (as now, but never faster than the server), "Normal" (x2 slower, default), "Saver" (x4 slower; aircraft
  area 15 s, military 60 s).
- List length (default 150 rows) and thumbnails in the list on/off.
- Pause updates when the tab is hidden (default on).
- Picture layers resolution (live photo / lightning / rain at half resolution) - optional.

## Proposed "Low power" mode
One switch (and automatic when the Mac reports battery saver? Safari exposes no Low Power API, so manual):
- No continuous animation: hotspot pulse static ring, hijack streaks off (lines stay), no satellite letters, no orbit rings
  except the selected one.
- Map repaints only on user interaction and on new data; aircraft are drawn at their last report (no playback, no 200 ms
  glide); models off below zoom 9 and capped at 100.
- Polling: every feed at 2x its server interval, only for layers that are on; aircraft area 15 s; status 30 s; nothing while
  hidden.
- 3D terrain and building extrusions off (globe allowed); devicePixelRatio of overlay canvases capped at 1.
- List capped at 100 rows; no thumbnails.

## Checked and fine
- Static files: served at /s/<start>/... with `Cache-Control: public, max-age=31536000, immutable` and gzip (three.module.js
  663 KB -> 131 KB); page `no-store`. Good.
- JS heap: all layers on for 6 min (flat): 75 -> 70 MB, oscillating 70-145 MB with GC; no JS heap leak found. Live DOM stays
  ~9k nodes (garbage is collected).
- Event loop of the server on a quiet machine: cheap route p50 1 ms; a single big /api/data or hotspots request adds 24-168 ms
  of waiting to concurrent requests (not seconds). The 1-2.7 s stalls seen earlier came with the machine at load 25-30 and
  ~6 browsers polling.
- No console errors from the app itself in any run (only upstream 500/502 tiles from GIBS / EUMETSAT, which are sandbox/upstream).
- `glide()` no longer re-sends the ~7,000 world aircraft every 200 ms (only on new world data: ww-air ~0.04/s with ~7,000
  features), as CLAUDE.md says.
- MapLibre worker count set to 2-4 (map.js), debounced moveend handlers in cameras/sites/sky/maxar/aircraft.

## Could not test here
- Real frame times, GPU load and Safari specifics on the owner's Mac (software GL here; the machine ran at load 7-29 from
  other auditors, so wall-clock numbers are inflated). Counts above are machine-independent.
- 3D terrain (the "3D" button) with models: headless times out; terrain cost reviewed by reading only.
- Globe runs with many layers: the default-layers globe run did not finish in 19 min here (software GL), so globe numbers are
  from Satellites alone at 640x400.
- Server memory attribution (no tracemalloc/py-spy on the running process; not allowed to restart it).
- ProMotion 120 Hz effect (doubles every per-frame cost listed above).
