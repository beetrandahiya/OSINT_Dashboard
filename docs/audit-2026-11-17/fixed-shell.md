# Fixes: shell (branch fix/shell, worktree /home/user/wt-shell)

Commits: 90d5ebf (picture proxy), 19a222f (shell front end). Test proxy: scratchpad/fix-shell/proxy.py on :8723.
Scripts: scratchpad/fix-shell/ (smoke.js, tmin.js, t5_misc.js and t2_layers.js are the auditor's, pointed at :8723).

## Per finding
1. Protest thumbnails refused by /api/news/image (high) - FIXED (web.py). Allowlist = news window images OR every
   picture in the current `unrest` payload OR `Unrest.heads_seen` pictures (`_unrest_images()`, cached per payload)
   OR the USNI fleet graphic. Other img() users (spikes, people/leaders, profile, country dossier) take their pictures
   from the news window, already covered. New `_public_url()`: http/https only, host must resolve only to global
   addresses (rejects loopback, RFC1918, link-local/169.254, CGNAT 100.64/10, ::1); redirects are followed by hand,
   each hop checked (max 5). Verified in Python against the live payload: 622/622 unrest pictures allowed, 6 fetched
   200 image/jpeg; 127.0.0.1, localhost, 10.x, 169.254.169.254, 100.64.x, [::1], file:// refused; unlisted URL 404.
   NOT verifiable in the browser here: the shared server on 8710 runs the old web.py until restarted (my proxy forwards
   /api to it, so the t5/t2 runs still show those 404s).
2. Card rebuilt on every feed answer (medium) - FIXED (main.js). The card is redrawn from scratch only for a new item.
   The same item is compared as an HTML string with what was last drawn (equal: nothing touched) and otherwise patched:
   a three-way DOM patch (last-drawn template vs new template vs live DOM) touches only the nodes whose HTML the layer
   changed, so loaded pictures, lazily filled sections (anything inside an unchanged placeholder), the satellite-picture
   day buttons, focus, scroll and the element under the mouse stay. Fallback when children don't line up: full
   innerHTML plus the old keep-list restore, now only for placeholders the layer itself left unchanged. Refresh
   triggers: only when the picked layer's feed answered (batched per frame) + a 20 s timer (ages; cards that read
   other layers' data). The hover guard is gone (live values now update under the mouse); instead an update is held
   while a mouse button is down in the card and applied on release (no "element detached" mid-click).
   Events that used to clear detailKey (act, ww-detail, ww-flags, satellite change, chase start/stop) call
   renderDetail(true): patch, bypassing `still`, no scroll reset.
   Verified (t5): "Today" still pressed after 65 s, scrollTop 200 kept, 1 patch in 65 s (was 7 full rebuilds).
3. 1100x700: list gone, legend over zoom/compass (medium) - FIXED (app.css). .chips max-height 42% with own scroll,
   .list min-height 150px; legend width min(290px, room left of the nav control). Measured: 1100x700 list 237 px
   (was 22), legend right edge 654 < nav 674; 1512x982 legend 710 < nav 1086; 1728x1000 fine. Screenshots
   smoke_1100x700_light.png, min_*.png.
4. Munich pressed twice - NOT MINE (lookup fixer), untouched.
5. Escape does not close search list - FIXED. Escape: search list open -> close it only (stopImmediatePropagation so
   the dossier underneath stays); dossier open -> left to profile.js (closes only it); else blur + close card.
   Verified tmin: Esc1 closes list, card stays; Esc2 closes card; t5: dossier closes on Esc.
6. Orbit-class key under the card on the globe - NOT FIXED: drawn on space.js's canvas (space fixer's file). Note for
   `space`: drop it (the Legend panel has the same entries) or place it inside freeArea(). Still visible in
   min_1512x982_dark_globe_card.png.
7. Off layers doing periodic work (medium) - PARTLY. Mine: hotspot pulse no longer calls setPaintProperty every frame;
   it is one maplibregl.Marker per hotspot with a CSS transform/opacity animation (compositor only, no map repaint),
   opacityWhenCovered 0 on the globe, removed while the layer is off, hidden under Reduce Motion. VIP / doomsday 2 s
   timers return when their layer is hidden (aircraft.js, 2 one-line edits; main now calls layer.render on chip-on so
   halos appear at once). Main no longer fetches anything while the tab is hidden. Not mine: space.js tick (still 6
   setData/10 s with satellites off: `space`), models3d repaint per frame (`moving`). Off layers' feeds are still
   fetched and rendered (counts on chips need onData; render into hidden layers kept to avoid per-layer risk).
8. Shared feeds fetched twice - FIXED. One timer (shortest interval of its users) and one in-flight request per feed,
   onData/render fanned out to every layer that lists it, each in its own try/catch. t5: data/ships 1x per minute.
9. Retry pile-up - FIXED. One pending 5 s retry per feed (`retry[feed]`), in-flight guard per feed.
10. Padding ignores minimised sidebar - FIXED. minimiser callback eases padding.left to 0 / 420 (not during chase);
   initial padding from the stored state; CSS var --left (body:has(#sidebar.min)) moves legend, markets and
   attribution to the left edge. Verified tmin at 3 sizes: pad 420 -> 0 -> 420, legend/markets/attrib x 420 -> 20.
11. "No photo" strip under the card buttons - FIXED (app.css): `.photo .pic-wait` gets top corners and 96 px right
   padding. See layer_aircraft.png / layer_tankers.png from the sweep.
12. MapLibre expression warnings - NOT MINE (airspace.js, people.js: `intel`). Still present in the sweep.
13. Loading bar positioned only on show - FIXED: while visible it re-places itself every 200 ms (interval stops when
   hidden).
Also: renderChips writes the DOM only when its HTML changed; renderList compares with a JS variable; chips, list and
card are redrawn at most once per animation frame however many feeds answer; ww-chips from local layers batches too.

## Shared-file edits outside my list
- js/aircraft.js: the two VIP / doomsday `setInterval` lines only (visibility check). `moving` should keep them.
- js/hotspots.js (assigned exception): pulse rewritten as markers; layer `ww-hot-pulse` removed; paint sets `--hot`
  on the map container for the CSS ring colour.
- main.js: the chase block untouched except the two `detailKey = ''; renderDetail()` calls -> `renderDetail(true)`;
  the `#munich` place() block untouched. `three()` untouched.

## Verification matrix
1100x700 light flat, 1512x982 dark globe, 1728x1000 light globe (tmin.js: start, card, sidebar min/restore, Escape);
t5 (news+unrest+quakes+military, 1440x900); full 40-chip sweep t2 at 1280x800 (results below). Tilted views and 3D
terrain not re-tested (no change there; terrain times out headless).

## For the owner / lead
- The chip area now scrolls on every window size (about 12 rows visible at 1512x982) so the list always has room;
  a proper layer-panel redesign is being proposed separately.
- After merging, restart the server so the picture-proxy change takes effect.

## Lessons for CLAUDE.md
- Never set a MapLibre paint property every frame for an animation: it forces a full map repaint 60x/s forever. Use a
  DOM marker with a CSS animation (compositor only) or a canvas overlay redrawn only while something moves.
- Cards are patched, not rebuilt: a layer's detail() HTML should be deterministic for the same data (no random ids),
  and lazily filled sections should fill a placeholder element (with an id) rather than insert siblings, so the patch
  keeps them.
- Feeds are loaded once per feed name in main.js and handed to every layer listing it; a layer must not assume it
  is the only consumer of a payload object (do not mutate it destructively in onData).

## 40-chip sweep after the fixes (fix-shell/t2.out, 1280x800, via :8723)
All 40 chips: count appears, items drawn where the audit drew them, a card opens for every layer with clickable items
(now also hotspots, spikes and orbits, which had no data during the audit; doomsday/ships/people/picture layers have no
clickable card as before), no undefined/NaN in cards, no close failures, after switching off: no visible map layers,
no stray features, legend section gone, overlays empty. No page errors. Remaining console warnings: airspace.js
boolean/null and people.js array<number,2> (finding 12, intel), 404s from the not-yet-restarted picture proxy.

## Handed over by intel (commit after 19a222f), all four applied
1. pick(): `if (p && !byId[p.layer]) return;`.
2. util.js local(): year added when it is not the current year.
3. load(feed): sends `?since=<fetched of the last answer>`; `{unchanged: true}` is checked before the "no payload yet"
   retry and skips onData/render. Works with the old server (ignores since). Unchanged path tested by emulating
   fix/intel's data() answer in my proxy: quakes and aircraft_military answered unchanged, list (1442 rows) and counts
   intact afterwards. Ships never get unchanged (server excludes it).
4. Find box: the people placeholder `#find-people` is replaced alone; country rows stay the same nodes. Tested: rows
   while searching, people answer, nonsense -> "No person or country found.", click on a country row opens the dossier.
Not touched (lookup fixer's): chaseStop(level, after), Munich place(), feeds-card "not set up" count.
