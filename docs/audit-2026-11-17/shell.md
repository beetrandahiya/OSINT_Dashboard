# Audit: shell (index.html, app.css, main.js, map.js, legend.js, util.js)
Scripts and screenshots: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/shell/

### Protest/unrest thumbnails are refused by our own image proxy (404)   [severity: high]  [confirmed by running]
Repro: t5_misc.js (news + unrest on). Network shows dozens of `404 /api/news/image?u=...` for list-row and card pictures.
Seen: 488 of the 622 picture addresses in the `unrest` payload are not in the news window; `/api/news/image` answers 404 for
them, `onerror` removes the thumbnail, so protest rows and cards lose their pictures. This defeats the 2026-11-16 fix
("protest cards lost their picture after 6 hours": `Unrest.heads_seen` keeps pictures 30 h).
Cause: web.py:746 allows only `news_window.images()` (+ USNI graphic); unrest borrows from `heads_seen`.
Fix: allow `url in news_window.images() or url in unrest.heads_images()` (a set built from `heads_seen` values when it is saved).
Risk: low; still not an open proxy.

### Open card is rebuilt on every feed answer of any layer, resetting what the user did in it   [severity: medium]  [confirmed by running]
Repro: t5_misc.js: open a news card, click "Today" on the satellite picture, move the mouse off the card, wait 65 s.
Seen: 7 full rebuilds of #detail in 65 s with only 4 layers on; the "Today" choice is back to "Yesterday" (and the image
reloads). Same for any card state not in the keep-list (expanded "Read more", focus, a playing GIF, half-read text
selection). Playwright also hit "element detached" twice while clicking card buttons.
Cause: main.js:121 `load()` calls `refreshPick()` after every feed of every layer (quakes and military every 30 s, news 60 s,
aircraft/unrest/outages 120 s ...), and `renderDetail` (main.js:208) rewrites `innerHTML` whenever the mouse is not over it.
Fix: refresh only when the answered layer is the picked one (`if (picked?.layer === layer.id) refreshPick()`), and inside
`renderDetail` skip the DOM write when the new HTML equals the last one (`if (key === detailKey && html === lastHtml) return`).
Risk: cards that show ages ("3 min ago") update less often; a 20 s timer can refresh them.

### Narrow window (1100x700): the event list is gone and the legend covers the zoom/compass control   [severity: medium]  [confirmed by running]
Repro: `node t3_shape.js 1100 700`; screenshot s_1100x700_feedsopen.png.
Seen: #list is 22 px high (one clipped row); the 40 chips fill the sidebar. Legend box [420,258,710,580] overlaps the
navigation control [674,490,710,598] by 36x90 px: the right-drag in the test landed on the legend and nothing rotated;
compass and zoom buttons are half hidden. At 1280x800 the list shows only 2 rows; at 1440x900 about 2-3 (fresh_10.png).
Cause: app.css:107 chips have no height limit; app.css:375 legend 290 px wide at side+gap; app.css:407 control placed
`right: 340px + 2 gaps` without regard to the legend; the free map area at 1100 px is only ~320 px.
Fix: give `.chips` `max-height: 40%; overflow-y: auto` (or collapse into a "Layers" disclosure), give `.list` a
`min-height: 180px`; move the navigation control into the right column above the feeds card, or set
`.legend { max-width: calc(100vw - var(--side-w) - 340px - 4*var(--gap) - 52px) }`.
Risk: layout only.

### "Munich" pressed twice loses the way back to the world view   [severity: low]  [confirmed by running]
Repro: t9_scroll.js: World view -> Munich -> Munich -> World. Map stays on Munich (centre 48.137 N).
Cause: main.js:435 saves `worldView` on every Munich press, overwriting it with the Munich view.
Fix: `if (m && $('#home').getAttribute('aria-pressed') === 'true') return;` at the top of `place()`.

### Escape does not close the search list   [severity: low]  [confirmed by running]
Repro: type "germ" in Find, press Escape: input blurs, the result list stays open over the chips.
Cause: main.js:258 handler only blurs and `pick(null)`.  Fix: also `$('#find-list').hidden = true` (and if the profile overlay
is open, close only that, not the card underneath: today one Escape closes both).

### Satellite orbit-class legend on the globe is cut off under the card   [severity: low]  [confirmed by running]
Repro: satellites on, Globe, open any card (s_1440x900_rotated.png). The row "Military imaging · Low Earth · Medium ·
Geostationary · ●" runs under the detail card; HEO entry hidden. It is also duplicated by the Legend panel now.
Fix: drop the on-map legend (the Legend panel already has these entries) or place it inside the free area (use freeArea()).

### Layers that are off still do their periodic work   [severity: medium]  [confirmed by running]
Seen with all chips off (t2 baseline, t5): `ww-sats` setData 6x/10 s (space.js:243 `tick` computes SGP4 for all 1,046
satellites every 2 s and calls triggerRepaint even when the layer is off), `ww-air-vip`/`ww-air-doom` setData every 2 s
(aircraft.js:483, :522), and every layer's feeds are still fetched, parsed, `render`ed and the list/card rebuilt.
With default layers on, hotspots' pulse (hotspots.js:16-17 setPaintProperty every frame) and glide (200 ms) keep MapLibre
rendering continuously; at zoom >= 7 models3d.js:243 calls `map.triggerRepaint()` every frame unconditionally, even when no
aircraft layer is on. On the owner's Mac that is 60 full map frames a second forever (battery, fan, jank in other panels).
Fix: guard the timers with the layer's on state (`if (!shown) return` before computing; `visible(v)` hooks exist); in
models3d only re-trigger when something was drawn (`if (drawn.length || sel) map.triggerRepaint()`); hotspots: pulse at a
low rate (e.g. a 50 ms setInterval / CSS-free step) or only while the hotspot is in view.
Risk: low; check counts still refresh for off chips (they come from onData, not render).

### Shared feeds fetched twice per interval   [severity: low]  [confirmed by running]
`ships` (ships + warships), `vip_aircraft` (vip + doomsday), `airspace`/`navwarn` (also launches), `cf_radar` (hijacks +
outages): each module gets its own `load()` + `setInterval` (main.js:135), so the same payload is downloaded and parsed twice
and the list/card rebuilt twice. Seen: `data/ships` 2x per minute.  Fix: one timer per feed name, fan out
`onData` to every layer that lists it, then one renderChips/renderList.

### Retry chains pile up for a feed that never gets a payload   [severity: low]  [by reading only]
main.js:117: a load with no payload schedules a 5 s retry; the feed's own setInterval keeps calling load() too, and each of
those starts another 5 s chain. A feed with no saved payload that keeps failing (e.g. fires or CelesTrak timing out on a
fresh install, `sites` while its first build runs for minutes) gains one more permanent 5 s poller every interval.
Fix: keep one pending retry per feed (`if (retry[feed]) return; retry[feed] = setTimeout(...)`).

### Map padding and the bottom row ignore a minimised sidebar   [severity: low]  [confirmed by running]
With the sidebar minimised (s_1440x900_allmin.png) the map keeps `padding.left = 420`, so "fly to" from list/search/
hotspot links centres items at x~930 instead of the middle, and legend/markets/attribution stay offset by the sidebar width
leaving an empty band. Fix: in `minimiser` for the sidebar call `map.easeTo({padding: {left: v ? 0 : SIDEBAR_SPACE}})`.

### Aircraft/ship/sanctioned cards: the "No photo"/"Looking for a photo" strip runs under the close and minimise buttons   [severity: low]  [confirmed by running]
layer_aircraft.png: the text "No photo of this aircraft on planespotters.net." sits at the top edge behind the ^ and x buttons
(the minimise button is barely visible). Fix: `padding-right: 84px` on the photo placeholder, or put the buttons on a
backed pill.

### MapLibre expression warnings in the console   [severity: low]  [confirmed by running]
"Expected value to be of type boolean, but found null" from airspace.js:28-29 (`['case', ['get','strong'|'tfr'] ...]` on FIR
features without `tfr`; the line-width case is also a no-op, both branches 1.2). Use `['==', ['get','tfr'], true]`.
"Expected array<number,2>, found string" when Leaders today is on (people.js:79-83); spreading still works (checked at Kyiv).

### Loading bar is positioned only when it appears   [severity: low]  [by reading only]
main.js:58 `place()` runs on show; if the card opens or closes (or a dossier opens) while a request is in flight, the bar
stays on the old panel's edge. Fix: call `place()` from pick()/renderDetail and the profile open/close, or on a rAF while visible.

Checked and fine:
- Fresh load (localStorage cleared): no JS errors, no failed module imports; style loaded at 3.7 s, all chip counts and 610
  list rows by 10 s; feed card honest ("1 of 45 feeds late": USNI).
- Every one of the 40 chips switched on alone: count appears (or the layer's note), legend section appears, items drawn,
  a card opens without undefined/NaN/[object]/Invalid Date for every layer that has clickable items (hotspots, spikes,
  orbits, doomsday had 0 items; people opens a profile via `pick`; gpslive cells clicked only by map, not tested);
  switching off: all map layers `visibility:none`, no stray rendered features, overlay canvases empty, legend section gone.
  Table: t2.out (count / rows / drawn / card / after-off state per id).
- Selecting an item then switching its chip off closes the card and clears the ring.
- Flat <-> Globe with a card open: card and ring stay, ring at the same coordinates; right-drag rotate+tilt then compass
  resets bearing and pitch on both projections; wide 1728x1000 and 1440x900: no panel overlaps (feeds, markets, legend,
  nav control, attribution, card).
- Minimise sidebar/card/legend/markets and reload: globe, minimised panels and layer choices persist; reduced motion makes
  list fly instant; dark mode colours of chips, legend, panels, card fine (d_card.png).
- Search: country matches at once ("usa" -> United States of America), nonsense -> "No person or country found.", <2 chars
  hides; Wikidata 429 shown honestly ("Wikidata is limiting requests ..."); country dossier opens and Escape closes it.
- mousemove hit-testing 0.9 ms per event; renderList ~78 ms per 10 s with 1,500 rows; status poll excluded from loadbar.

Could not test here:
- 3D terrain button (headless times out); chase camera across globe switch beyond reading.
- Real frame rate: in software GL the main thread is saturated by GPU emulation ("(program)" 12.6 s of 10 s profile with
  default layers), so click latency there says nothing about the Mac; continuous-render findings are by call counts.
- Safari-specific behaviour (no ctx.filter / lookbehind found in the shell files).
