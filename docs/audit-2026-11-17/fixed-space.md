# Fixes: space  (branch fix/space, worktree /home/user/wt-space)
Commits: 6a7f6bc (layer slots, sky), f16e1fc (satellites, passes, manoeuvres, smaller), 8f68071 (legend wrap, quakes owns).
Test scripts: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/fix-space/ (proxy.py on :8721).

## Findings
1. Photos hide night/aurora/rain/lightning/GPS — FIXED. `slot(map, name)` in map.js adds invisible anchor layers once,
   just under the base map's first label layer, bottom first: photo, sharp, live, night, aurora, rain, lightning, gps,
   area. Every overlay inserts before its own anchor (re-adds too), cables and fires before 'area'. Live photo is kept
   above sharp (so a live photo switched on is not hidden by the sharp photo 3D turns on). Verified (ordertest.js): order
   correct and all under labels from three different start states, after toggling 9 chips in mixed order, and after 3D on
   (ww-relief stays under ww-photo). Screenshot: rain + GPS visible over the sharp photo with white labels.
2. Satellites wrong when tilted — FIXED. camera() solves rows 0,1,3 of mainMatrix (Cramer) for the camera position in the
   globe frame (unit sphere at origin, which MapLibre's globe getMatrixForModel uses); place() computes the world point
   directly (no getMatrixForModel per satellite) and does the ray/sphere test from the true camera. Verified (occl2.js) at
   zoom -1.5/0.5/1/2/3/5, pitch 0/30/40/60/70, bearings 0/10/30/47/75/-120/-160: camera vs engine's
   transform.cameraPosition within 2e-6 radii; screen position vs map.project 0 px; 0 of 1,836 height points wrong vs an
   independent truth (engine camera, sphere, in front of camera); ground visibility agrees with isLocationOccluded except
   2-3 points exactly on the limb. Returns null when the globe is rendered flat (high zoom).
3. Look down ignores tilt, drag flies back — FIXED. Rides at pitch 0, bearing 0 (north up: chosen, the card says so).
   Zoom solved from |camera - centre point| with the cos(latitude) globe scale: camera ends at 417 km for ISS at 417 km.
   Saves {center, zoom, pitch, bearing}; Leave restores exactly (verified 35°/20° back). A drag/rotate/pitch by hand
   (events with originalEvent; the engine fires rotatestart for our own easeTo) just ends the ride: no fly back, card kept.
4. Look down from flat switches to globe for good — FIXED. Switches via new `ww-shape` event (main.js shape(.., false), not
   saved), Leave goes back to flat; ww-globe stays ''. Verified. After a drag-takeover the globe stays (unsaved).
5. Spy-pass freeze — FIXED. Coarse 150 s at >= 5°, refine at 30 s (a pass peaking >= 30° stays above 5° >= 260 s even at
   180 km), yields every 12 satellites; button keeps 'wait' state through redraws and writes into the current box.
   Same passes as the old 60 s method at 6 places (one boundary case at exactly 30.0°), longest task during the run
   118 ms here vs idle render frames of 350 ms. Work 163k vs 351k propagations.
6. Aurora rebuilt while off/unchanged — FIXED (only when on and observation/theme changed; Kp strip still updated).
   Night: built only while on, every minute; blank picture until then. costs.js: aurora render 0 ms while off.
7. Imaged outlines stay after close — FIXED (hidden box counts as gone; also checks lat/lon). Verified 30 -> 0.
8. Imaged answer lost on redraw — FIXED ('wait' marker, re-finds the box by lat/lon after the fetch). Verified with a
   forced redraw mid-request.
9. Manoeuvre false alarms — FIXED in satinfo.limits(): high orbits (period > 225 min) rise/drop 3 km, plane 0.03° +
   0.0025°/day; LEO plane 0.03 + 0.0005°/day; amateur unchanged plus the high-orbit plane allowance. Rows and cards give the
   gap ("orbits 24 days apart"); card wording no longer claims "kept 1.2 days". On the real history (270 sats, 488 pairs):
   2 -> 1 manoeuvre left: USA 324 raised (apogee 35,738 -> 35,831 km, 24 days apart), plausibly real (inspector sats
   manoeuvre). USA 325 and both "plane changes" gone. Takes effect after a server restart.
10. Card throws without the satellites feed — FIXED (source line uses the right feed's fetched time or "unknown").
11. Rasters flash on update — FIXED: `tiles()` keeps the source and calls setTiles, old tiles stay until new arrive.
    Not visually verified (EUMETSAT/RainViewer tiles through the sandbox); logic from MapLibre's reload path.
12. Labels dark with a second photo — FIXED (names follow photo || live || sharp).
13. matchMedia per satellite, per-frame finds — FIXED (dark once per frame, ISS/classes/spy cached in annotate, no
    matrix allocation per satellite, canvas not cleared every frame while off, off-screen satellites skipped).
14. Satellite tick while off — FIXED (returns early; globe empties the source once). costs.js: 0 setData in 10 s.
15. Click anywhere selects a satellite — FIXED: 6 px (12 for ISS/selected), only ISS and spy diamonds when > 300 on
    screen. Globe hit fraction 16-19 % -> 1.1 %.
16. List pick on the globe doesn't fly — FIXED inside space.js: select() eases to the satellite when it is not on screen.

Smaller: canvas legend centred between sidebar and card, wraps to rows (fixed, screenshot); lightning chip says
"no answer" and the about text explains when EUMETSAT gives no time (fixed); sharp-photo legend text (fixed, legend.js);
amateur "StarSh" expanded to StarShield in satinfo.parse_mccants (the list abbreviates it to fit its name field; server
restart needed); corridor NaN (ringMid null -> skipped); GPS hexagons unwrapped at the date line in gps.js (front end,
not feeds.py); dead code track/footprint/lines/mul/best removed; quakes meta double escape removed.
Coordinator addition: quakes `owns(id)`; verified quake picks from list, map click and ww-try-pick.

## Shared-file edits
- map.js: new exported `slot(map, name)` + SLOTS (16 lines, after setPhoto).
- main.js: one line, `document.addEventListener('ww-shape', e => shape(!!e.detail?.globe, false))`.
- cables.js, fires.js: import slot; insertion point `slot(map, 'area')` (one line each).
- legend.js: sharp-photo note text.
- space.js exports `satDebug` (debug only).

## Not verified here / for the owner
- Frame time on his GPU; 3D terrain with satellites (headless times out).
- Raster swap without flash: not seen live (tiles fail through the sandbox).
- Order choice within the sky band: night < aurora < rain < lightning; photos daily < sharp < live. Owner may prefer otherwise.

## Lessons for CLAUDE.md
- MapLibre globe frame: Earth = unit sphere at origin, point = (1+h/R)(cos lat sin lon, sin lat, cos lat cos lon);
  camera = solve mainMatrix rows 0,1,3 = 0. Never assume the camera sits above the map centre.
- Insert our overlays only through map.js slot(); never "before the first ww- layer".
- easeTo fires rotatestart/pitchstart too: test e.originalEvent to detect the user.
- Yielding with setTimeout in headless software GL looks slow (each yield waits for a render frame); measure long tasks.
