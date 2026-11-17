# Fixed: moving (branch fix/moving, worktree /home/user/wt-moving)
Commits: 2df01e8 (server), 24a1ae1 (front end), 04dedbd (follow-ups). Test scripts: scratchpad/fix-moving/ (proxy on 8725).

## Findings
1. Playback clock jumps (high): FIXED. util.js `api()` takes a clock sample only from quick answers (rtt <= best so far
   + 15 ms, the best ageing 1 ms/s, never > 1 s), uses the time the headers arrived, and the skew is the median of the last
   5 good samples. aircraft.js playback runs on its own clock: `frameNow()` = document.timeline time + an offset taken once
   from now(), afterwards slewed at most 10 ms/s (stepped only if > 30 s off). clock.js, 8 live aircraft, 60 s, every frame:
   before (8710) 67 backward steps, 63 per-frame jumps > 1.5x expected, worst 2.32x; after 0 backward, 0 jumps, worst 1.14x.
   Held statistics after: 0 % held for the 8 sampled (area answers 0.5-2.6 s); before, two planes held 41 s and 51 s.
2. Globe lost after follow/pick/follow (medium): FIXED. One state: `userGlobe` (Globe/Map buttons, saved) and `project()`
   draws `userGlobe && !chase`; chaseStart/Stop and the buttons call it; buttons always show the user's choice (with a
   tooltip "globe comes back when you stop following"). groundAgain now listens for moveend before easeTo (with Reduce
   Motion the instant move fired moveend inside easeTo and the globe was never restored). t7b.js: follow A / pick B /
   follow B / stop, Escape, Globe and Map pressed while following, double click, stop during the intro, card closed,
   item vanished (locate patched to null), rapid follow-pick-follow-pick-follow-stop: projection and button right every time.
3. Panels over the followed plane (medium): FIXED (my side). freeArea() also cuts out #legend, #marketsbar, #chasebar and
   the MapLibre control groups from whichever edge leaves most room. t5b.js globe 1100x700, legend open: plane held at
   (538,158), above the legend and below the follow bar; wheel over the plane zoomed 10.5 -> 13.2. The free band is small
   on such a window (~200 px); the legend's own placement is shell's.
4. Dead live feed (medium): FIXED. After 30 s without a new area report (checked every second, also when requests hang)
   live aircraft are grey (models) / 45 % opacity (icons), labelled "(last known)", stop at their last report, and the
   card says "No new position for n s: the live feed (adsb.fi) is not answering (answered 502)...". After 120 s they are
   removed and world/military positions take over; the card is redrawn when the selected aircraft changes feed. t8b.js.
5. Repaint/setData waste (medium): FIXED. models3d asks for the next frame only when an item moved > 0.05 px or turned,
   or the item set changed; an aircraft waiting at its first report gets one wake-up after 500 ms; aircraft.js calls
   triggerRepaint on new reports, chip and selection changes. Glide: nothing sent at zoom >= 7 (icon layers hidden), only
   changed sources sent below; world source re-sent only when snapshot / live circle / selection changed; extras by key.
   ring() in main.js sends ww-pick only when it moved. perf.js (10 s windows, sandbox software GL):
     B mid-Atlantic zoom 9: setData live/mil/extra 3.7/s each -> 0 (extra 0.2/s on area answers before the last fix)
     C New York 93 models: model-layer ms/frame median 3.3 -> 2.6 (incl. three.js submission), frames/s 2.9 -> 4.3
     A chips off: models3d no longer requests frames (the remaining 1-3 renders/s come from other layers: ww-sats setData
     0.5/s = space, VIP/doom 0.5/s = shell's change on fix/shell, not on this branch).
   Per-frame allocations removed: pooled provider items, pooled instance matrices per template, colour cache, label width
   cache, reused pick records; labels/ring redrawn only when something moved >= 1 px (overlays ~ frames while planes move
   at 4 fps in the sandbox; far fewer at 60 fps). getMatrixForModel kept per aircraft: in MapLibre 5 it depends only on
   lng/lat/alt and the projection (read in the vendored source), so it is exact; I did not replace it with local offsets.
6. VIP/doomsday invisible from zoom 7 with Aircraft/Military off (medium): FIXED. vip/doomsday `visible()` hooks set
   flags; the model provider draws them under their own chip; vip.hit / doomsday.hit answer clicks on their models.
   Not tested live (none airborne in view). shell already made the VIP/doom 2 s timers idle while hidden (fix/shell
   changes those two lines in aircraft.js; I left them untouched to avoid a conflict).
7. Server trail memory (medium): FIXED. collector._remember: military/Munich trails whole (4 s, 3 h, cap 2700 points);
   area-feed aircraft not seen in those feeds for 10 min: one point per 30 s, 1 h, cap 120; hard cap 12,000 aircraft
   (area-only and oldest first); points are tuples; prune once a minute. trailmem.py synthetic 3 h (300 area aircraft
   every 5 s with turnover + 120 orbiting military every 30 s): before 139.8 MB, 691k points, 8.4 s CPU; after 14.9 MB,
   75k points, 1.6 s CPU; patterns.analyse found 120/120 orbits in both.
8. Antimeridian (medium): FIXED (`near()` in models3d for model, ring, paths, sorting). Matrix check at centre 179.95:
   raw -179.95 is -0.9997 world away, shifted 0.00028 (correct ~7 km). Not seen with a live aircraft.
9. Ships 102.3 kn (medium): FIXED server (feeds.py `_ais_speed`, ais.py) and client guards (ships.js, sanctioned.js) for
   stored payloads; Digitraffic heading/course 0 kept (minor). Takes effect on the server after a restart.
10. Zoom > 12 loses the selected aircraft: FIXED by drawing a dashed ring at its ground point with "XYZ is above the
   camera, 7,238 m up: zoom out to see it" (t6b.js zoom 14: above=true). Chose this over capping zoom (the user may want
   to look at the ground). In follow mode it does not happen (the camera centre is lifted to the aircraft).
11. Chase intro short of zoom: FIXED (first frame after the intro sets the zoom once; t7b ends at 10.5 exactly).
12. Pick flies under the card: FIXED via `offset: freeOffset()` in pick()'s easeTo (padding left untouched).
13. Tanker / sanctioned markers lag: FIXED. aircraft.js `liveAt(hex)`; tanker and sanctioned-aircraft markers and
   locate use it, re-sent every 2 s only while their layer is visible; both layers `moving: true`.
14. New aircraft "no newer report": FIXED wording; playback marks `wait` (before first report) vs `held` (after last).
15. Route checked once: FIXED; a rejected route is asked again every 3 min while the card is open (server caches it).
16. Photo failures shown as "no photo": FIXED; "not set up (data/contact.txt)" and lookup errors are said and not cached.
Minor: heading 0 kept; Globe feedback while following (button state + tooltip); card "Drawn N s behind" is live
(#ac-fresh updated every second) and the report row is called "Latest report"; provider tests on-screen before the
world haversine; drop line goes to the terrain in 3D (queryTerrainElevation), not sea level. Also: no Follow button for
an aircraft on the ground or a ship moored / at anchor / aground / under 0.5 kn (heading() returns undefined).

## Shared-file edits (check at merge)
- util.js: `api()` / new `clockSample()` only (other callers of now() unchanged).
- main.js: `shape()` replaced by `userGlobe` + `project()`; #flat/#globe handlers; freeArea rewritten + `visibleEl`,
  `freeOffset()`; groundAgain listens before easeTo; chaseStop(level, after) - same signature as fix/lookup 86f7336,
  calls project() then after(); chaseStart (no wasGlobe, `landed`); pick(): `offset: freeOffset()`; ring(): send only on
  change (`ringKey`). fix/shell rewrote the `detailKey=''; renderDetail()` lines inside chaseStop/chaseStart to
  renderDetail(true): keep theirs, mine did not touch those lines.
- web.py: one argument (`area=True`) on `collector._remember` in the area route.

## Not done / for the owner
- Smoothness and repaint savings on a real GPU / Safari not measured; 3D terrain + models not testable headless.
- Live VIP/doomsday under their own chip, world AIS, a real aircraft across the date line: not seen live.

## Lessons for CLAUDE.md
- Never estimate server time from a slow answer: the round-trip midpoint is only right for quick ones. Animation must run
  on document.timeline with a slewed offset, never on now() directly.
- `map.once('moveend')` must be registered before easeTo: with duration 0 the event fires inside the call.
- The model layer requests frames only while something moves; anything that changes aircraft data must call
  map.triggerRepaint().
