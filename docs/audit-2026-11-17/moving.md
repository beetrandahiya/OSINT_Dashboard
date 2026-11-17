# Audit: moving (aircraft, models3d, chase camera, ships, orbits/tankers, sanctioned)

Scripts and screenshots: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/moving/ (h.js harness, t1-t12).
Test area: New York (busy at 01:00 UTC; Frankfurt was empty at night), Finland for ships.

### Playback clock jumps back and forth by up to ~2 s: the main source of jerky / backward-stepping aircraft   [severity: high]  [confirmed by running]
Repro: t3.js (samples aircraft.js `display()` every frame for 8 live planes, 30 s), t12.js (samples `now() - Date.now()/1000`).
Seen: the playback time `d.t` of every plane steps BACKWARDS at the same frames (e.g. 1188.3 -> 1186.8, 1206.3 -> 1206.1) and jumps forward elsewhere (2.2 s of playback in 0.47 s, 4x the normal speed). All 8 planes showed 3 backward steps and a 3-4x speed spike in 30 s, at the same instants. The skew estimate itself, with server and browser on the same machine (true skew 0), wanders between -0.82 and +0.24 s from one second to the next; after a slow /api/aircraft/area answer (1.2-6.8 s round trip, it waits for the shared adsb.fi gate) it is off by seconds.
Expected: a monotonic clock; aircraft never step back.
Cause: static/js/util.js:10 `skew = d.now - (t0 + Date.now()) / 2000` is recomputed from EVERY api() answer, assuming the server stamped `now` at the midpoint of the round trip. The area route stamps it at the end of a multi-second wait, so the estimate jumps by half the latency. aircraft.js:74 `frameNow = now() - performance.now()/1000 + frameT()` feeds that straight into playback, so every new answer shifts every live aircraft by (skew jump x speed): 100-500 m, eased over 0.3 s = a visible lurch, sometimes backwards. The same wobble moves every "n s ago" in the app.
Fix: update skew only from fast answers and keep the best one, e.g. `const rtt = Date.now()-t0; if (rtt < 300 && (rtt < bestRtt || Date.now()-bestAt > 600000)) { skew = ...; bestRtt = rtt; bestAt = Date.now(); }`. In aircraft.js give playback its own monotonic clock: `base = now() - performance.now()/1000` captured once, re-based only by slewing (at most 50 ms per second) when `now()` drifts.
Risk of the fix: low; ages elsewhere become steadier. Skew still converges, just from good samples.

### Following from the globe, then following another aircraft soon after: the globe is lost   [severity: medium]  [confirmed by running]
Repro: t7.js part (a). Globe on, follow A, click aircraft B (follow stops), press "Follow it" on B within ~0.7 s, then Stop.
Seen: after Stop the map stays flat (projection mercator, Globe button not pressed) while localStorage still says globe.
Expected: back to the globe.
Cause: main.js:320 chaseStop passes `wasGlobe ? () => shape(true,false)` as the `then` of groundAgain, which runs only on the next moveend and only `if (!chase)` (main.js:309). The new chaseStart sets `chase` before that moveend, so the callback is dropped, and chaseStart:329 reads `globeOn()` from the Globe button, which says false because the first follow switched to flat with save=false.
Fix: keep the user's projection in one variable (`userGlobe`, set by shape(..., save=true) and by the buttons) and use that in chaseStart instead of reading aria-pressed; or in chaseStart inherit `wasGlobe` from the follow being replaced: `const wasGlobe = chase?.wasGlobe ?? pendingGlobe ?? globeOn()` with pendingGlobe set by chaseStop until its groundAgain completes.
Risk of the fix: low.

### The legend panel sits over the middle of the map and covers the followed aircraft at 1100x700   [severity: medium]  [confirmed by running]
Repro: t5.js globe 1100 700 (screenshot t5_globe_1100_below7.png); also t4_f_z68.png.
Seen: the legend (x 420-710, y 330-580) covers the free-area centre where the chase camera holds the plane (570,350): the ring is half under the legend, the model hidden; mouse wheel over the plane scrolls the legend instead of zooming (zoom stayed 9.48 through all wheel steps); a drag there selects the legend and card text.
Expected: the followed aircraft visible and reachable.
Cause: freeArea() (main.js:296) only subtracts the sidebar and the card; the legend (and markets strip, NavigationControl) are ignored. The legend's placement "beside the sidebar, above the markets strip" puts it mid-map on short windows.
Fix: include `#legend` (when not minimised) as a bottom inset in freeArea (pad.bottom = cv.bottom - legend.top when it overlaps the horizontal middle), same for `#marketsbar`; or auto-minimise the legend while following.
Risk of the fix: low; the plane is held a bit higher on screen.

### When the live area feed fails, every aircraft freezes in the air with no sign on the map, and the card's delay text becomes nonsense   [severity: medium]  [confirmed by running]
Repro: t8.js (route /api/aircraft/area to 502 for 60 s).
Seen: all 80 models stay where they are (held) indefinitely; delay creeps 15 -> 34 s; the card keeps saying "Drawn 15 seconds behind real time ... moving between its real reports" or "Drawn 23 seconds behind" (text from the last redraw), "Position reported (61 s ago)". Nothing on the map shows the positions are stale.
Expected: a dead feed shown as dead (hard rule): fade or grey the live aircraft once their newest report is older than ~30 s, and say so on the card; or fall back to world/military positions.
Cause: aircraft.js:244 swallows the error and keeps `view` forever; playback holds at the last report (aircraft.js:48); delayOf (39) switches to DELAY_SLOW after 20 s, which only changes the text.
Fix: in loadView's catch, if `now() - viewInfo.data_time > 30` mark `viewInfo.stale = true`; in the model provider give stale aircraft the world tint and label "no update since hh:mm"; liveCard writes "No new position for n s (adsb.fi not answering)". Clear `view` after ~2 min so world positions take over.
Risk of the fix: low.

### Continuous repaint and setData every 200 ms while nothing changes   [severity: medium]  [confirmed by running]
Repro: t2.js. Zoom 9 (a) with Aircraft and Military chips OFF, (b) mid-Atlantic with no aircraft, (c) zoomed in with icons hidden.
Seen: (a) models3d renders every frame forever (frame counter 54 in 13 s idle) with 0 items, because render() always ends with `map.triggerRepaint()` once zoom >= 7; ww-air-vip / ww-air-doom get setData every 2 s with their chips off. (b)/(c) ww-air-live, ww-air-mil, ww-air-extra get setData at every glide tick (10 per 5 s here, 25 per 5 s on a fast machine) although at zoom >= 7 those layers are hidden by their zoom range; main.js:149 resets the ww-pick source every 200 ms too. On the owner's Mac this keeps the GPU at 60 fps permanently whenever zoom >= 7, and the map's workers re-tile three GeoJSON sources 5x a second.
Expected: no repaint when no model is drawn; no setData for hidden layers.
Cause: models3d.js:243 unconditional triggerRepaint; aircraft.js:418 glide interval only checks chip state, not zoom; aircraft.js:483/522 vip/doomsday intervals ignore visibility.
Fix: models3d: `if (items.length) map.triggerRepaint();` (and trigger once from providers when data arrives). aircraft.js glide: `if (isOn()) { drawExtras only when sel changes; return; }` (models read display() themselves). vip/doom intervals: check a `shown` flag set in `visible(on)`. ring interval: skip when `l.ring()` returns 0.
Risk of the fix: low; make sure a frame is requested when an area answer arrives (glide(true) can call map.triggerRepaint()).

### VIP and doomsday aircraft disappear from zoom 7 when the Aircraft / Military chips are off   [severity: medium]  [by reading only]
Repro: chips: VIP jets on, Aircraft off; zoom to an airborne VIP jet past 7.
Seen (from code): aircraft.js:417 limits ww-vip-halo/label and ww-doom-halo/label to zoom < 7, expecting the model to take over, but the model provider skips any aircraft whose civil/military chip is off (aircraft.js:555). Result: nothing drawn, while the VIP list row and card still exist.
Expected: VIP/doomsday aircraft shown whenever their chip is on.
Fix: in the provider, `const forced = v && (v.category === 'Doomsday' ? on.doomsday : on.vip)`; skip only if `!forced && chip off` (pass the VIP/doomsday visible state into aircraft.js via their `visible()` hooks).
Risk of the fix: low.

### Live-area positions fill the server's trail store without bound for 3 hours (server memory)   [severity: medium]  [by reading; RSS growth observed but not attributed]
Repro: keep a page zoomed in on a busy area. web.py:787 calls `collector._remember(ac, ...)` for every /api/aircraft/area answer.
Seen: server RSS 279 MB -> 563 MB -> 604 MB over the first hour of this audit session (several auditors' pages polling areas). collector.py:134 appends a point per aircraft per answer (every ~5-8 s, condition t > last + 4) and keeps 3 h, no cap: ~300 aircraft x 1,800 points = ~540k Python lists (~100 MB) per watched region; the prune loop also walks every trail on each call on the event loop. CLAUDE.md said trails were for near + military aircraft.
Expected: trails for military/near aircraft and the selected one; bounded memory (the M1 target).
Fix: in `area()` remember only `military` flagged aircraft (or none: /api/track uses OpenSky first); and/or thin to one point per 30 s and cap 360 points per hex. Run the 3 h prune once a minute, not per call.
Risk of the fix: the fallback path for civil aircraft when OpenSky fails gets shorter or disappears (it is the rare fallback).

### Aircraft models, ring, label and flown path vanish across the antimeridian   [severity: medium]  [confirmed by running (matrix), not by sight]
Repro: t6.js end: centre [179.95, 52], `transform.getMatrixForModel([-179.95,52])` gives world x 0.0001 while the centre is at 0.9999.
Seen: a model 7 km away on the other side of the date line is placed one world-width away (renderWorldCopies does not apply to the custom layer), so it is not drawn; the item still counts in stats/inView. Flat icons below zoom 7 are fine. Affects the Bering Sea, Aleutians, Fiji, Kamchatka, trans-Pacific tracks.
Expected: drawn like any other.
Cause: models3d.js:176 and rel() (139) pass the raw longitude.
Fix: `const lonNear = l => l + 360 * Math.round((ctr.lng - l) / 360);` and use it in both getMatrixForModel calls and in the screen-position test.
Risk of the fix: very low.

### Ships report 102.3 kn ("speed not available") as a speed   [severity: medium]  [confirmed by running]
Repro: /api/data/ships (6 ships at 102.3 kn now); /api/sanctioned/live: SAGA "speed_kn": 102.3 shows "Tanker · 102.3 kn" in its card.
Expected: "not reported". AIS SOG 102.3 means not available (as heading 511 and COG 360, which are handled).
Cause: feeds.py:1263 copies `sog` unfiltered; ais.py same for the world stream.
Fix: `"speed_kn": p.get("sog") if (p.get("sog") is not None and p["sog"] < 102.2) else None` in both parsers.
Risk of the fix: none.

### Zooming in on a selected cruising aircraft: past zoom ~12 the model and its ring vanish   [severity: low]  [confirmed by running]
Repro: t6.js, globe, pitch 0, centre on a plane at 6,096 m: zoom 11 model on its ground point; 12.5 model 67 px off; 14 `stats.sel` null (not drawn, no ring) while the card stays open.
Cause: physics: the camera at zoom 13-14 is lower than the aircraft, so it is behind the eye (v4.w <= 0 skips the ring too).
Fix: when the selected aircraft is above the camera, draw the ring at its ground point with a note "above the camera", or cap zoom at the selected aircraft's altitude, or suggest Follow.
Risk: low.

### Chase intro can stop short of the target zoom / pitch   [severity: low]  [confirmed by running]
Seen: target zoom 10.5 / 12, ended at 9.84, 9.48, 11.9 (t5a, t5b, t9): after the 1.6 s intro, zoom is never set again, so on a frame drop the last intro frame (u < 1) stays.
Cause: main.js:360-366, the post-intro jumpTo omits zoom.
Fix: on the first frame with u >= 1, include `zoom: chase.zoom` once (`if (!chase.landed) { opts.zoom = chase.zoom; chase.landed = true; }`).
Risk: none.

### A pick flies the item to the middle of the area left of the sidebar, under the card on narrower windows   [severity: low]  [confirmed by running]
Seen: t4_f_z68.png at 1100 wide: the selected aircraft sits under the detail card (card left edge 740, map centre with sidebar padding ~750).
Cause: main.js:203 easeTo uses the map padding (sidebar only).
Fix: pass `padding: freeArea()` to that easeTo.

### Tanker and sanctioned-aircraft markers lag behind the moving aircraft   [severity: low]  [by reading only]
patterns.js loads /api/aircraft/patterns every 120 s and sanctioned.js every 60 s; their circles sit at those snapshot positions on the ground while the live/military model (40 s playback) moves on: up to ~30 km apart at 450 kt, and at zoom >= 7 the circle is on the ground under an empty sky. Fix: draw these markers at `AC.civil.locate(hex)` when the aircraft feed has the hex (export a lookup), else at the snapshot.

### Aircraft new to the view stand still ~15 s and the card says "no newer report yet"   [severity: low]  [by reading only]
aircraft.js:46: before its first report's time, playback returns the first report with held: true. A plane entering the area (or every plane after panning) sits still for DELAY seconds, and the card text claims it is waiting for a newer report. Fix: separate `waiting` (before first report) from `held` (after last), and word the card accordingly.

### Route check is done once when the card opens   [severity: low]  [confirmed by running]
BAW116 near JFK: "Route unknown ... heading away from that destination" (departure turn). fillRoute sets data-done and never re-checks, so the route stays rejected for the rest of the flight while the card is open. Fix: re-ask /api/route (cached server-side) every few minutes while selected, or skip the heading test within ~150 km of the origin.

### Photo failures and "photos off" are shown as "No photo of this aircraft on planespotters.net"   [severity: low]  [by reading only]
web.py:256 returns `{photo: None, off: true}` without a contact address and `{photo: None, error}` on 4xx/5xx; aircraft.js:397 stores null and prints the "no photo" claim (cached for the page's life). On a network error fillPhoto returns leaving the box empty with done=1. Fix: show `error` / "photos not set up (data/contact.txt)" and do not cache errors.

### Smaller ones
- Ship heading 0 (north) dropped: feeds.py:1264 `(p.get("heading") or 511) < 360` turns 0 into 511. Use `p.get("heading") is not None and p["heading"] < 360`. [low, reading]
- Pressing Globe while following gives no feedback (button stays unpressed; it only sets `chase.wasGlobe`). [low, confirmed t7]
- Card numbers (altitude, speed, heading, "Position reported") are the newest report while the drawn aircraft is 15-40 s behind; "Drawn N seconds behind" is the value at the last redraw, not live. [low, confirmed t8]
- models3d render allocates a Matrix4 per aircraft per frame (models3d.js:182) plus `Rel.clone()`, and the provider runs a haversine for all ~7,000 world aircraft per frame (aircraft.js:566 inLive before inView): measured 6.8 ms JS median per frame for 359 models in the sandbox. Test inView first, reuse a pool of matrices. [low, measured]
- Dropped line goes to sea level, and baro altitude can put landing aircraft under 3D terrain at high airports (hidden by depth). [low, reading]

Checked and fine:
- Icons below 7, models from 7; crossing 7.2 <-> 6.8 four times: exactly one trail and one route each time (3D ribbons above 7, ground lines below), overlay canvas cleared below 7, no doubled labels, no flicker frames caught.
- Model count = items on screen (stats: 359/359, 67, 80); world aircraft not drawn inside the live circle; world-feed aircraft outside it drawn grey.
- Click hit-testing on models: flat pitch 0 and 60, globe pitch 60 all selected the right aircraft.
- Models on the globe match the ground point at pitch 0 up to zoom 11 (0-2 px).
- Follow on flat 1440x900, globe 1100x700, globe 1728x1000 with sidebar minimised: plane held within 0-2 px of the free-area centre (dy -5..1), card minimise re-centres, ↺ ↻ N "Behind it" and drag-orbit work; wheel zoom to 14 and down to 5.6 keeps following (icons below 7, ring stays); Stop restores pitch 0, bearing 0, padding, centerClampedToGround true, scrollZoom (around-center off) and dragPan, globe projection when it started on the globe; Escape and closing the card stop it cleanly; Map pressed while following saves flat.
- World-feed aircraft: drawn at the newer OpenSky path point with the note; path joins it; zooming in hands it to the live feed.
- Ships (Finland): 421 icons, card, Wikimedia picture state, follow; sanctioned ship card; tanker card with photo. No console errors from this area in any run.

Could not test here:
- Frame rate / smoothness on a real GPU (1-4 fps software GL); 3D terrain with models (times out headless); Safari.
- A live VIP or doomsday aircraft (none airborne in view); world AIS ships and warships (no key); a selected aircraft leaving the feed (code shows "No longer in the feed", chase stops).
- Page hidden then visible (by reading: display() snaps after 3 s and planes hold until the next area answer, <= 5 s).
- Theme switch at runtime with models drawn (code recomputes tints per frame and icons on change).
