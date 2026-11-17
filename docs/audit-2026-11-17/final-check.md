# Final acceptance check (live server on merged code, HEAD 7854bfd + 7 fix commits)

Scripts and outputs: scratchpad/final/ (st.py status table, data.py data-route check, f1/f2 page load and polling,
sweep/t2.out 40-chip sweep, fx.js C1/C2/C4, lazy.js / lazy2.js lazy three.js, moving/ (t7b, clock, card, warn), v/t3b.js
flat/globe/Look down, lp.js hijacks idle + low power, sizes.js, hot.js, more.js, lk.js lookup + /feeds, lead2.js, lt.js).
Server restarted once by me (04:34, for the dossier fix).

## A. Live server: PASS (with notes)
1. Log: no traceback in either run. /api/status 45 feeds: 41 ok, usni_fleet late (real: USNI stopped publishing),
   cf_radar / ships_world / windy "waiting, not set up" (no keys). courts_icc "waiting" for ~35 min after a start (first
   fetch reads 19 situation pages 20 s apart + 90 s retry per refused page), then ok with note "the court's site refused 17
   of 19 situation pages and no earlier copy is held". Satellites (CelesTrak) and fires answered this time. DB migration ran:
   `latest.version` column, `latest_seen` table, `fetches_started` index present; second start restored payloads with
   versions. Disk writes 0.7 MB per 90 s steady (was ~8 MB/min).
   RSS/CPU, run 1 (03:43 start): 320 MB at 2 min, 365 at 10, 377 at 18, 389 at 34, 404 at 42, 408 at 50 min; CPU 81 s in
   50 min (~2.7 % of one core, incl. my browser tests' area queries). Old code (perf audit): 424 / 477 / 566 (35 min) /
   609 (88 min). Run 2 (04:34): 373 MB at 8 min, CPU 16 s. Growth slows but is not flat; still ~2x the old 205 MB
   figure. Not isolated further (no profiler on the live process).
2. /api/data for all 44 feeds + sites_nuclear: 200, gzip for everything above the small-payload threshold, ETag, version in
   ETag = /api/status version (sites_nuclear carries the sites version in its state; its ETag is the view's own hash, the
   page uses the state field, fine), `?since=<fetched>` -> `{unchanged:true}`, If-None-Match -> 304, `now` in every answer.
   Ships: no ETag/since by design. Payload keys match what the layers read (all layers drew in the sweep). First-request
   times include the one-off gzip build (news 79 ms, translated 93 ms); repeats ~1-2 ms.
3. Page vs live server (f1, f2): first downloads at t=2 s for on layers only; over 6 min news reloaded once (version
   moved), military 12x (30 s, version moves), quakes 3, unrest 3; off-by-default layers (cameras, bases, sdr) never
   downloaded; chip counts for every other off layer present at t=15 s. Quake card ages = status (fetched 16-18 s, USGS
   generation time). Hidden tab: 0 requests in 60 s; on return status + due jobs + changed feeds at once.
4. Server-side fixes live:
   - Person dossier counts (with ?name= as the page sends): Trump 592 outlets / 252 in headline (Leaders today:
     Washington 225), Modi 23/4, Netanyahu 48/4 (Leaders today: Gaza 13). Without ?name and no cached profile the counts
     were 0 and name "" -> FIXED (6dcdf18): name from the leaders list; after restart Trump 567/236, Modi 22/5, Netanyahu 38/3.
   - ICC: Duterte case "In ICC custody"; Putin/Netanyahu/Modi: no match, `missing` lists the 17 refused pages, pages 19.
   - Country dossiers: with Wikidata 429 the honest line "Wikidata could not be asked (the query service answered 429...)"
     and the leaders-list fallback. That fallback showed FORMER heads (Taiwan: Wu Den-yih, Frank Hsieh, Lien Chan...;
     Palestine: Shtayyeh) because the cached `leaders` list (lookup.db, 10 h old) was built by the old query without
     BestRank; it refreshes after 12 h. When Wikidata answered (later): Taiwan Cho Jung-tai, Palestine Mohammad Mustafa,
     Nauru David Adeang. Not a code bug; see open problems.
   - Unrest article ages 0.02-23.6 h, none in the future. Protest pictures via /api/news/image: 200 image/jpeg.
   - Stable ids: military areas `marea:node/...` from OSM ids; hotspots none live (tested with injected data, C3).
   - Hijacks chip: "Cloudflare Radar feed stopped: last read 31 h ago (not set up...). Only events of the last 24 hours are
     drawn." Count 0. Outages: no Cloudflare notes drawn (none within the 7-day rule); IODA rows say Ongoing/Ended.
   - Ships speed: 3 ships with null speed -> card "not reported" (read); Digitraffic max 102.2 shown as reported.
   - /feeds: 41 of 45 ok, 1 late, 3 not set up; no undefined/NaN/null; no console errors.
   - MVG: note "2 headlines left in German (translation paused: Google is limiting requests)"; card text exists.
   - Lookup guard: cross-site POST 403, text/plain POST 403, foreign Host 403; /lookup page (light+dark) added and
     removed test@example.com through the UI, 0 identifiers left, no console errors.
   - SSRF: /api/news/image with 127.0.0.1 and 169.254.169.254 -> 404; cam/maxar 400; imaged/pic 404.
   - /api/track altitude: OpenSky path points carry metres as 4th value; /api/trail too.
   - Trails cap: military trails 3-82 points, area aircraft (after ~40 min of area queries) max 93.
   - Memo answers: hotspots 53 ms first / 0.8 ms repeat; spikes 1 ms; patterns 0.7 ms; sanctioned 12 ms / 1.1 ms.
   - Manoeuvres: 1 (USA 324 raised, GEO limits 3 km), history 1.3 days.

## B. Whole-app regression on the live server: PASS
- Fresh load: 0 page errors; console only 502s from /api/news/image (upstream images refused) and GPU-stall notices.
- 40-chip sweep (sweep/t2.out): every chip counts, draws, opens its card where it has items; nothing left visible or stray
  after off; legend sections go. Warnings: leaders `array<number,2>` (fixed after, see C4); livephoto GIBS GOES-West 500s
  (upstream).
- t7b (all follow/flat/globe sequences): projection, button and saved value right every time. t3b (Look down from flat and
  globe, ride + aircraft + follow, Munich during follow): consistent; Munich->World now returns to zoom 8 pitch 0 (was the
  chase view).
- clock.js: 4,568 frames, 0 backward steps, 0 jumps > 1.5x, worst 1.08. card.js: live numbers patch every few seconds incl.
  with the mouse over the card; ISS and news card sections kept after forced redraws; no duplicate ids.
- Lazy three.js: 0 three/model requests before zoom-in; zoom 2.5 -> 9 over Frankfurt: icons at 72-113 ms, models at
  1.0-1.5 s, no frame without either (flat); globe: one ~200 ms sample during the follow glide with nothing listed; pick +
  follow right after the zoom-in works on flat and globe (plane in the ring at the free-area centre).
- List: 150 rows + "Show all 1,152"; after it 1,152 rows, kept over a reload cycle; row 400 opens its card.
- 1100x700 light, 1512x982 dark, 1728x1000 light, globe, ISS card: no horizontal scroll; orbit-class key sits between
  sidebar and card (wraps to 3 rows at 1100, one row at 1512).
- Hijacks layer on with the dead feed: 0 animation frames requested in 20 s.
- lowPower {"lowPower":true}: list 100 rows, status every 30 s, `ww-still` set, models drawn at zoom 9, no errors.

## C. Leftovers
1. Labels over a photo: FIXED 0203efe (main.js onPhoto: paint as soon as the style exists, again on the next idle). Load with
   Photo on: label colour #ffffff right after load; 3D button: before #4a4a4f, after #ffffff with Sharp on.
2. Munich then World after a follow: FIXED 0203efe (saved world view = chase.from). Before follow -73.9/40.7 z8 p0; World
   -> -75.0/39.85 z8 p0 b0 (the centre is where the map stood when Follow was pressed, after the pick's pan).
3. Hotspot pulses: FIXED 3b97d34 (rebuilt only when the sorted set of positions changes). hot.js with an injected answer
   reversed on reload (prefs rate 0.25 -> reload at 75 s): same marker elements kept, off -> 0, on -> 2.
4. Style warnings: FIXED 4f7c97e. people.js offsets were array properties, which come back as JSON strings in MapLibre's
   hit tests ("array<number,2>, found string"): now numbers turned into [x, y] with an interpolate over literal arrays
   (offsets checked: three leaders at one city stand at -24/0/+24 px, a click at +24 opens the third). All
   `['case', ['get', X], ...]` (29, in 10 files) now `['==', ['get', X], true]` (all are booleans; a missing property no
   longer warns). "Expected number, found null": 0 in three runs afterwards (default layers + follow at NYC; and
   aircraft/military/quakes/news/leaders/airspace + follow + clicks), so the source is not pinned down; it was 6-10 per run
   before.
5. Orbit-class key vs card: confirmed fine at 1100x700 and 1512x982 (screenshots size_1100_light.png, size_1512_dark.png).
6. Low power: FIXED d2dc78c: moving models ask for a frame every 250 ms instead of every frame (zoom 9: 28 map frames
   in 5 s in low power).

## D. Other findings
- FIXED 6dcdf18: person dossier without ?name (see A4).
- FIXED 237649a: lightning asked /api/eumetsat/time every minute while off; now every 15 min while off, at once when
  switched on (lt.js: 0 requests in 130 s off; one on switching on, chip time updated).
- Open: country-dossier fallback shows former heads while lookup.db's `leaders` list predates the BestRank fix (heals within
  12 h when Wikidata answers; on the owner's Mac the first start on this code may show former heads in a 429 moment).
  Proposed: bump the cache key to `leaders2` with the fallback reading `leaders2` then `leaders` (all callers use
  store.cache_get("leaders", ...): people.py, dossier.py, web.py).
- Open: courts_icc stays "waiting" ~35 min after a start while it reads refused pages (shows the disk copy meanwhile).
  Restored payloads have no feed note until the next fetch (note not saved in `latest`), so after a restart the ICC
  "refused n of 19" note is missing for up to a day; the dossier still computes `missing` from the payload. Proposed:
  save `note` with the payload.
- Open (seen once, not reproduced): picking a world-feed aircraft right after zooming in and following it can follow an
  aircraft the world snapshot says is on the ground: it is drawn neither as model nor icon (models3d skips world
  on_ground), so the camera follows an invisible point (lazy.js flat run 1: sel null throughout). Proposed: draw the
  selected aircraft even when on_ground, or disable Follow for an on-ground world position.
- Open: server RSS ~375-410 MB within the first hour (A1); trend slower than before but rising.
- Noise: /api/news/image answers 502 for upstream images that fail; the page logs them as console errors (4-8 per load).

## Commits (branch claude/blissful-brown-m2ryy5, not pushed)
0203efe labels over photo while loading; World after Munich during follow
3b97d34 hotspot pulses only rebuilt when positions change
4f7c97e style warnings (leader offsets, boolean case tests)
d2dc78c low power: models at 4 Hz
6dcdf18 person dossier: leader name fallback (server)
237649a lightning time poll only while on

## Facts worth recording in the project log
- Merged code tested live 2026-11-17: all feeds ok except known (USNI late, three keys missing); data route gzip/ETag/
  since/304 verified per feed; page downloads only on version change; hidden tab sends nothing.
- Server RSS on the merged code: ~320 MB at 2 min, ~405 MB at 50 min (old code 424 / 609 MB at 2 / 88 min); CPU ~2-3 %
  of a core; SQLite writes ~0.5 MB/min (was ~8).
- MapLibre: feature properties that are arrays or objects come back as JSON strings in hit tests and placement; pass numbers
  and build arrays in the expression (interpolate over literal arrays). Boolean tests: `['==', ['get', x], true]`.
- isStyleLoaded() is false while any tiles load; setPaintProperty needs only the style: do not gate paint changes on it.
- The ICC first fetch after a start takes ~35 min when the shield refuses pages (20 s spacing + one 90 s retry each).
