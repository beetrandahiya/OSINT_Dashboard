# Audit: space (satellites, launches, sky rasters, imaged, GPS, quakes)

Scripts and screenshots: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/space/

### Photo / Sharp photo / Live photo hide Night, Aurora, Rain, Lightning and both GPS layers   [severity: high]  [confirmed by running]
Repro: order.js, order2.js. Night + Rain + GPS on, then Sharp photo on (screenshots order-sharp-night.png vs order-night-only.png).
Seen: with Sharp on, the night shading, the rain radar and the GPS hexagons disappear completely. Style order measured:
36 ww-night, 37 ww-aurora, 38 ww-lightning, (rain goes in just before aurora), 41 ww-gps, 43-45 ww-gpsl-*, then 46 ww-photo, 47 ww-sharp, 48-51 ww-live-*, 52 first base label.
3D mode switches Sharp photo on by itself (main.js `three()`), so the owner (Globe + 3D) never sees rain, lightning, night, aurora or GPS interference.
Expected: the opaque base pictures sit at the bottom; the overlays on top of them, under the labels.
Cause: photo/sharp/live are inserted "before the first symbol layer" (sky.js:146, :201, :235), i.e. at the top of the base map, while
night (sky.js:75), aurora (:111), rain (:19), lightning (:173), gps (gps.js:10, :50) are inserted "before the first ww- layer", which is ww-photo / ww-sharp
whenever those exist. Lightning's exclusion list even names ww-photo/ww-sharp, so it lands under them; live photo is re-added every 2 min, also under the labels and above everything else.
Fix: one helper in map.js, e.g. `beforeOverlay()` = id of a fixed invisible anchor layer added right after the base map's last non-symbol layer, and
`beforeLabels()` = first base symbol layer. Insert photo/sharp/live before the anchor (bottom), and night/aurora/rain/lightning/gps before `beforeLabels()`
in a fixed order (or add empty placeholder layers 'ww-z-photo', 'ww-z-overlay' at style load and always insert before those). Re-adds (rain, lightning, live) must use the same anchors.
Risk: low; only layer order changes. Check that the 3D hillshade (`ww-relief`, inserted before first ww-) still sits under the photo.

### Satellites drawn through the Earth / wrongly hidden whenever the map is tilted (globe)   [severity: high]  [confirmed by running]
Repro: occl.js. Globe, satellites on, compare space.js's occlusion test with the true camera position (null space of the main matrix) on a grid of 2,448 points at 0.5, 500, 20,000 and 35,786 km.
Seen: pitch 0 (any bearing): 0 errors. Pitch 50 zoom 1: 248 points drawn that are behind the Earth, 218 hidden that are in view. Pitch 60 zoom 3: 650 wrongly drawn, 178 wrongly hidden. Estimated camera distance 10.9 Earth radii vs true 7.06 (pitch 50), 4.19 vs 2.27 (pitch 60). Screenshot g-z3-p60.png: satellites, the orbit ring and spotlight beam painted over the globe face where they should be behind the limb. Rotation is now enabled everywhere, so this hits every tilted globe view.
Cause: space.js:89-104. `camera()` assumes the camera sits straight above the map centre and derives its distance from depth along that axis; `place()` does the ray/sphere test in a frame centred on the map centre. Both are only true at pitch 0.
Fix: take the camera position from the matrix the engine hands over, as the test did: solve rows 0,1,3 of M·[X,Y,Z,1]=0 (Cramer, once per frame), get the Earth centre/radius in the same world frame from `getMatrixForModel` of two antipodal ground points (also once per frame), and per point use the world position `T[12..14]/T[15]` that `clip()` already computes for the ray/sphere test. Same cost, exact at any pitch/bearing. `sitAt()` must then use |camera - centre| for `have`.
Risk: medium (the drawing core); verify with occl.js (all zero) at pitch 0/40/60 and zoom -2..5.

### "Look down from it" ignores tilt and turn, and a drag while riding flies you back and closes the card   [severity: medium]  [confirmed by running]
Repro: look.js, look3.js. Globe, tilt 35 / bearing 20, select ISS, "Look down from it".
Seen: riding view keeps pitch 35 and bearing 20 (not "facing straight down", the card claims it is), and the zoom is solved from the pitch-broken camera distance. Dragging while riding: zoom jumped 8.91 -> 7.69 during the drag, on release the card closed and the camera eased back to the pre-ride view (0,0 z2), discarding the drag.
Cause: `act('follow')`/`sitAt()` (space.js:208-212, 270-277) never set pitch/bearing; `map.on('dragstart', stopFollowing)` (space.js:242) starts `easeTo(restore)` in the middle of the user's pan, which stops the pan handler; the release then counts as a click on empty map -> pick(null).
Fix: in act('follow') save {center, zoom, pitch, bearing} and ease to pitch 0 in sitAt (`{..., pitch: 0}`); on dragstart only set `following = false; restore = null; refresh()` (no easeTo: the user is taking the camera), keep the card. Optionally keep pitch/bearing locked by disabling dragRotate while riding.
Risk: low.

### "Look down from it" from the flat map switches to the globe for good   [severity: medium]  [confirmed by running]
Repro: look2.js. Flat map, select ISS, Look down, Leave.
Seen: after Leave the map stays on the globe and localStorage 'ww-globe' = '1' (survives reload).
Cause: space.js:274 `document.getElementById('globe')?.click()` goes through main.js `shape(true)` with save=true; stopFollowing never goes back.
Fix: remember `wasFlat = !isGlobe()` in act('follow'); call the projection switch without saving (expose `shape(true, false)` via an event like 'ww-shape'), and on stopFollowing switch back to flat if wasFlat.
Risk: low.

### Spy-pass button freezes the page ~1 s   [severity: medium]  [confirmed by running]
Repro: spy.js (news card, Kwajalein). Long task of 1,156 ms after the click (software CPU here; expect ~0.2-0.4 s on the M-series Mac, still a visible hitch with the map animating).
Cause: `passes()` space.js:466-481: ~130 low-orbit spy satellites x 1,440 SGP4 propagations + look angles, synchronously on the main thread.
Fix: coarse-to-fine: step 5 min, refine with 30 s steps only around samples above ~15 deg (6x fewer propagations), and/or run it in chunks with `await new Promise(requestAnimationFrame)` per 20 satellites, or a module Worker importing the vendored satellite.js.
Risk: low; a pass shorter than 5 min above 30 deg is impossible for LEO at the coarse threshold of 15 deg.

### Aurora picture rebuilt every 5 minutes even when off and unchanged (0.7 s long task)   [severity: medium]  [confirmed by running]
Repro: costs.js: `aurora.render(map)` took 738 ms here.
Cause: main.js `load()` calls `layer.render()` after every fetch (space_weather every 300 s); sky.js:92-116 smooths 65k cells twice and paints a 768x768 picture + `toDataURL` each time, whether the Aurora chip is on or the NOAA observation time changed. `paint()` (dark-mode switch) does it again.
Fix: in render, return early unless `sw.aurora_observed !== lastBuilt` or the colour changed; skip building while `auroraOn` is false and build on `visible(true)`. Same idea for night (sky.js:76, builds a 384x384 PNG every minute even when off).
Risk: low.

### Imaged outlines stay on the map after the card is closed   [severity: medium]  [confirmed by running]
Repro: spy.js: "Which satellites actually photographed it", then close the card: outlines still there (18 source features 2.5 s after close).
Cause: imaged.js:168-171 watches `#imaged.dataset.done`; main.js renderDetail on pick(null) only sets `#detail.hidden`, the old HTML (with #imaged done=1) stays in the DOM. They only go when another card is opened.
Fix: in keepWatching also clear when `document.getElementById('detail').hidden` or `!box.isConnected`: `if (!b || !b.dataset.done || b.closest('[hidden]')) ...`. Better: main.js clears `#detail` innerHTML when nothing is picked.
Risk: none.

### Imaged answer lost when the card redraws during the request   [severity: medium]  [confirmed by running (forced redraw)]
Repro: spy.js: click the imaged button, move the mouse off the card, a redraw happens (any feed load calls refreshPick -> renderDetail; I fired 'ww-detail'): the box reverts to the plain button and the result never appears.
Cause: imaged.js:188 `if (!document.body.contains(box)) return;` drops the answer because renderDetail replaced the element; main.js keeps #imaged only when `dataset.done`. Requests take 1.5-30 s, feeds refresh every 10-30 s, and the hover guard only holds while the pointer is on the card.
Fix: after the await, re-find the box: `const box2 = document.getElementById('imaged'); if (!box2 || box2.dataset.lat != lat || box2.dataset.lon != lon) return;` and write into box2; mark `box.dataset.done='wait'` before the fetch so the keep-list preserves the "Asking…" state.
Risk: low.

### Military-satellite "manoeuvres" that are natural drift ("changed its orbital plane")   [severity: medium]  [confirmed from live data + reading]
Seen: list rows "USA 325 raised its orbit and changed its orbital plane": inclination 1.42 -> 1.4844 deg between two element sets 24.6 days apart (USA 324: 1.1209 -> 1.1837 in 24.1 d). A geostationary satellite's inclination drifts by itself by up to ~0.85 deg/year (~0.055 deg in 24 days); USA 325's "raise" is perigee -1.1 / apogee +4.9 km (semi-major axis +1.9 km), within element-set noise for GEO.
Cause: satinfo.py:214-222: fixed thresholds (0.03 deg, 0.8 km) regardless of the time between the two element sets and of the orbit class. Card text says history kept 1.2 days while the compared epochs are 24 days apart.
Fix: allow natural change per day: plane change only when |di| > 0.03 + 0.0025*days for GEO/period > 600 min (lunisolar), "raised" for GEO only above ~3 km; or compare only element sets < 3 days apart. Mention the span ("between X and Y, 24 days apart") in the row.
Risk: low; fewer false rows.

### Satellite card throws when the main satellite feed has not loaded   [severity: medium]  [by reading only]
Cause: space.js:347 `satInfo.fetched` — satInfo is set only by the 'satellites' feed. If CelesTrak's feed is still waiting/failing (it often is, see the log) but 'recon_sats' has data (it has a McCants fallback), sats = recon list only and opening any satellite (including the manoeuvre rows) throws in renderDetail, leaving a broken card.
Fix: `${satInfo ? 'fetched ' + ago(satInfo.fetched) : 'not loaded yet'}` and use `reconInfo.fetched` for recon satellites.
Risk: none.

### Raster layers flash empty on every update (rain ~10 min, lightning 5 min, live photo 10-15 min)   [severity: low]  [by reading only]
Cause: sky.js:15-20, 168-174, 203-207 remove the layer and source and add new ones: the area is blank until the new tiles arrive (slow through Safari / EUMETSAT WMS). Live photo removes 4 sources at once.
Fix: add the new source/layer under a new id at opacity 0, on `map.once('idle')` (or `sourcedata` with `isSourceLoaded`) set it visible and remove the old one.
Risk: low.

### Labels turn dark over the photo when a second photo layer is switched off / at load   [severity: low]  [confirmed by running]
Repro: photohook.js. Load with Photo on: label colour #4f83b8 (normal map colours, not white). Photo + Sharp then Photo off: labels go dark while Sharp still shows (photohook-sharp-dark-labels.png).
Cause: photo, livephoto and sharp each call the shared `photoHook(on)` (sky.js:150, 215, 240) with their own state; at load main.js `show()` runs photo -> livephoto(false) -> sharp(false), so the last one wins.
Fix: `photoHook(photoOnState || liveOn || sharpOn)` from each visible(), keeping a flag per layer.
Risk: none.

### Canvas legend and per-satellite matchMedia in the per-frame draw   [severity: low]  [confirmed by running (profile)]
Repro: prof.js satellites globe sat:25544: drawHeights 10 ms/frame here; 1.7 ms of it is `isDark()` -> `matchMedia()` called per satellite via `tint()` (space.js:76-77, 178), plus `sats.find(ISS)` and `new Set(sats.map(...))` every frame (170, 201). Also `getMatrixForModel` allocates a matrix per satellite per frame (clip()).
Fix: compute `dark` once per frame and pass the colour table; cache ISS and the used-classes list in annotate(); compute the model translation directly (MapLibre's globe getMatrixForModel is translate(ecef)*scale; or call it once and reuse a scratch array if the API allows).
Risk: low.

### Satellites tick keeps running and repainting with the layer off   [severity: low]  [confirmed by running]
Repro: costs.js with Satellites off: `setData` on ww-sats every 2 s (empty collection) and a `triggerRepaint` every 2 s.
Cause: space.js:214-226/243: the 2 s interval propagates all ~1,050 satellites and repaints regardless of `shown`; on the globe it also sends an empty collection every 2 s.
Fix: `if (!shown) return;` at the top of tick (visible(true) already calls tick); send setData only when switching flat/globe or when shown on the flat map.
Risk: none.

### A click almost anywhere on the globe selects a satellite   [severity: low]  [confirmed by running]
Repro: hit.js: with Satellites on, 16-19 % of all viewport points (much more over the globe face) select a satellite on click; a click on "empty" globe to close a card opens a random satellite instead.
Cause: space.js:265-269 hit radius 12 px around every one of ~1,050 drawn points, consulted for any click that hits no map feature.
Fix: radius 6 px for small dots (12 for ISS/selected), and do not take hits for plain dots when more than ~300 are drawn (keep spy diamonds and ISS).
Risk: low.

### Picking a satellite from the list on the globe does not fly to it   [severity: low]  [by reading only]
Cause: `locate()` returns null on the globe (space.js:311), so main.js pick(..., fly=true) has no point to ease to; a manoeuvre row for a satellite on the far side opens a card with nothing visible.
Fix: add `locate3d`-like `flyTo(id)` or let main.js use a layer's optional `where(id)` for flying while `locate()` stays null for the ring.
Risk: low.

### Smaller issues   [severity: low]
- Canvas legend centred with hard-coded 420/340 px (space.js:201): runs under the open card (look-1-riding.png, "Geost…" cut) and is off-centre with the sidebar minimised. [confirmed]
- Lightning: if /api/eumetsat/time fails at start the layer is never added and nothing says so (sky.js:166); a dead feed is not shown as dead (hard rule). Live photo then silently loads untimed tiles. [reading]
- Legend for Sharp photo says the date "is shown in the corner"; it is in the chip. [confirmed]
- Amateur names arrive truncated ("USA 425 StarSh") from classfd.tle and are shown as is in cards and spy-pass lists. [confirmed]
- corridor(): a SPACE TFR with empty `polys` gives ringMid NaN, and `NaN > 150` is false, so it is not filtered and a NaN line coordinate is sent to MapLibre (space.js:377-378). [reading]
- GPS hexagons are not split at the antimeridian (feeds.py:648, 1156); none crossed today, would smear across the map when one does. [reading]
- Dead code: track(), footprint(), mul() in space.js; `best` unused in passes().
- quakes rows: meta is esc()'d in quakes.js:118 and again by main.js (double escaping if a type ever contains & or <).

Checked and fine:
- Satellite canvas at pitch 0 with any bearing on the globe: occlusion exact (0 of 2,448), positions match the engine; minZoom -2 on globe, 0.3 flat; ring/spotlight drawn; card with picture (ISS, Wikimedia), flags, owner, orbit text; purpose letters threshold; satellite chip off while selected closes the card, while riding restores the view; Leave restores centre/zoom.
- Spy-pass result list and source text; imaged results (9 captures Kwajalein, outlines drawn, hover rows map to outlines; failed previews removed via onerror, 502s from the sandbox only).
- Night and aurora pictures align on the globe and tilted flat/globe views (MapLibre image sources); dark mode colours.
- Quakes layer flat/globe, card, list; nearTestSite works (Punggye-ri 1 km, Lop Nur/Malan 6 km).
- No console errors from these layers in any run (only GL driver warnings and sandbox 502s).

Could not test here:
- Frame cost on the owner's GPU / Safari (software GL here: drawHeights ~10 ms/frame of CPU with ~1,050 satellites and spotlight).
- 3D terrain with satellites (headless times out); the layer-order bug was confirmed without terrain but 3D turns Sharp on, so it applies.
- Corridors: no launch in the next 4 days matched a TFR/navy warning during testing (NGA 503 here).
- Lightning / live photo tile failures from EUMETSAT, GIBS tiles (sandbox tunnel); Esri tiles did load.
