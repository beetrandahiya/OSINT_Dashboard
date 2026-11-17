# Fixes: perf (branch fix/perf, worktree /home/user/wt-perf, made from integ 9be5ba6)

Commits (oldest first): d4c7f5e server, 32ebf30 front end, 17ae64c lazy gzip + save intervals, 7b20849 areas/low power/
hidden timers, b1d70eb latest_seen, 3cc10c2 sanctioned key, 5453b5a models retry.
Scripts and results: scratchpad/fix-perf/ (proxy.py on :8726 serves wt-perf static and maps /api/data/sites_nuclear to
sites for the old server; harness.js = the auditor's with BASE and FAKE_CF; before/ = integ static via a temporary
proxy, after/ = this branch; t_data.py, t_hot.py, t_memo.py, t_mem.py, t_db.py, t_coll.py = direct Python tests with
real payloads saved from 8710 in payloads/ and a copy of data/gdelt in tmpdata/; changes.py = 15 min record of which
feed payloads really change; smoke.js, t_low.js, t_ver.js = browser checks).
The server on 8710 still runs OLD code: server numbers are from direct function timing on a quiet machine (load ~2);
browser runs through the proxy talk to the old server, so they show the client side only (no versions, no gzip: the
proxy strips gzip, so kB below are uncompressed).

## Re-measure on integ (what was already fixed)
1 hotspot pulse: fixed on integ (shell: CSS markers). Not re-measured by frame; code read.
2 models3d repaint when idle / per-frame allocations: fixed on integ (moving; its perf.js numbers).
3 hidden layers' timers: VIP/doomsday, satellite tick while off, night/aurora while off fixed on integ. Remaining and
  fixed here: satellite tick and other timers in hidden tabs; off layers still downloaded+rendered every poll (see D).
4 glide setData on hidden sources: fixed on integ (moving).
7 satellites matchMedia etc.: fixed on integ (space).
12 hidden tabs: main.js feed polls fixed on integ (shell); the other timers fixed here (see D).
H inLive before inView: fixed on integ (moving: on-screen test first; only on-screen world aircraft get the haversine).
Card patching, `?since=`/unchanged, one timer per feed: on integ (shell/intel), kept.

## A. Server response cost (finding 5, server half): FIXED
wire.py (new): a feed payload is serialised once per version in a thread; gzip (level 6) is built the first time someone
asks; per request only `{state, now}` is appended by continuing a copy of the kept compressor (one valid gzip stream).
Version = blake2b of the payload bytes (same data refetched keeps it), in /api/status and every data answer. ETag =
version+fetched, If-None-Match -> 304 (the page does not use it: a cached body would feed its clock an old `now`).
`?since=` unchanged answer kept. Ships merge cached 10 s (stream read in the loop, merged in a thread). GZipMiddleware
level 6 for everything else. Plain bytes dropped once gzipped (rebuilt for the rare non-gzip client).
Measured (news 2.45 MB): before per request dumps 19 ms in the event loop + gzip9 90 ms (thread); after 0.25 ms per
request, one 100 ms build per version in a thread. sites 17+135 ms -> 0.28 ms; aircraft_world 14+100 -> 0.20 ms;
cameras 14+71 -> 0.19 ms. Payloads identical to JSONResponse's (t_data.py), 304, identity and since paths checked.
Not done: /api/news/place and /api/sites/areas are per-request by nature (small answers); areas_in ~15 ms in a thread.

## B. Recomputed answers (finding 9): FIXED
news.spikes (default thresholds) and news.leaders_today memoised on the windows' slot keys (+ leaders list, WATCH);
web.py Memo for /api/news/spikes, /api/hotspots (inputs' fetch times + windows + patterns key, max 5 min),
/api/aircraft/patterns (military/near/vip fetch times, max 60 s), /api/sanctioned/live (feed fetch times + AIS stream in
30 s steps, max 30 s). One computation at a time in a thread; `now` added fresh. Dossiers also use the memoised
leaders_today. Before (quiet machine, real 6 h windows, 29,458 articles): spikes 316 ms, leaders_today 80-113 ms,
hotspots 380-404 ms per request; after: 0 ms in Python, ~2-3 ms per request through TestClient.

## C. SQLite writes (finding 10): FIXED
`latest` gets a `version` column (ALTER TABLE on old databases, checked on a copy of the owner-style db: 4 ms) and a
small `latest_seen` row: an identical payload only moves latest_seen (load_latest uses its newer fetched when versions
match, so restart ages stay true). news/news_translated/unrest saved at most every 15 min, ships/aircraft_military/
aircraft_near every 10 min, quakes 5 min (a restored payload keeps its own fetch time: older, never fresher).
Index fetches_started (DELETE now uses it: query plan checked), clean-up every 10 min, synchronous=NORMAL with WAL.
Measured: save of an identical 2.5 MB news payload 2.50 MB -> 0.01 MB written. From a 15-min record of real changes
(changes.json): payload bytes written 36.3 MB/15 min before -> ~9.4 MB/15 min estimated with skip + intervals
(~2.4 -> ~0.6 MB/min of payload, before WAL checkpoint copies). Not run against the live server.

## D. Client polling (finding 5 client half, 3, 12): FIXED
main.js schedule() runs on every /api/status answer: a feed is downloaded only when its version moved (old server
without versions: when fetched moved), never faster than its layer's interval x prefs rate, only if a layer using it is
on; off layers refresh at most every 15 min (chip counts); layers off by default (cameras, bases, sdr) are not
downloaded until switched on. Same version + new fetch: the state fields are copied into the answer the layers hold
(t_ver.js: card age moved 40 -> 21 min ago with 0 downloads; 1 download once the version changed). Ships (live merge)
stays on a timer. First downloads right after map load; status loop 5 s (30 s low power), none while hidden.
Small polls (hotspots, patterns, sanctioned, spikes, leaders, markets, munich, lightning, live photo, night) on
prefs.every(): one 1 s clock, nothing while hidden, due jobs run on return. Satellite tick skips hidden tabs.
nuclear layer now reads `sites_nuclear` (web.py VIEWS: sites without the 12,049 military rows, ~0.4 of 1.6 MB).
Measured via proxy against the OLD server (so only the client effect): all layers off, 60 s: 23 -> 17 req/min,
3,050 -> 343 kB/min (321 of it is /api/status), data requests 7 -> 0, setData 6 sources -> 1. Default layers, 90 s:
data requests news 2->1, news_translated 1->0, aircraft_world 1->0, quakes 3->2, ships 2->1. Startup: 219 -> 183
requests, 20.2 -> 15.2 MB uncompressed (cameras, full sites, three.js, models gone).
Not done: /api/status is still ~25 kB raw every 5 s per tab (static fields could be split off); markets.js polls its
three small feeds every 60 s itself.

## E. Hijack streaks (finding 6): FIXED
netwatch.js animate: frame cap prefs.fps (30), vertices projected lazily once per view, tail pieces batched per colour
and fade step (<= 132 strokes), colour strings per theme, glow-head sprites, loop stops when off / Reduce Motion /
animations off / low power (restarted on 'ww-motion'). With a fresh fake cf_radar payload (no token here):
script 194 -> 28 ms per second; animate self time 8.9 % -> 0.4 %; rgba 2.0 % -> gone. Screenshots before/after
look the same (flat light, globe dark, map moving during the test).

## F. List (finding 8): FIXED
150 rows + "Show all n" (prefs listRows, 100 in low power); local() with two formatters made once and a per-minute
memo. Default layers: live DOM 8,647 -> 1,525 nodes, list 1,357 -> 153 rows; renderList (0.5 %) and local (0.3 %)
no longer in the profile's top 12. 100k local() calls 87 ms.

## G. three.js at startup (finding 11): FIXED
models3d.js: three.js, GLTFLoader, meshopt and the models load on the first zoom to >= 6 (dynamic import); renderer made
inside the custom layer's render; retry on a later zoom if loading fails. Icons stay until onReady (aircraft.js
unchanged). Startup: 6 three files (2.26 MB raw) + 26 model requests -> 0; smoke.js: zoom 8.5 near Munich -> 55
requests, isOn true, icon maxzoom 7, models drawn.

## I. Server memory (finding 13): PARTLY
t_mem.py (tracemalloc, real payloads, no server): news windows 27.6 MB, held payloads of all feeds 57 MB (Python
objects), military areas 22.5 MB -> 8.8 MB (columns, same answers checked), kept gzip answers for 32 page feeds +10.8 MB.
70 big answers the old way (JSONResponse + gzip9, 4 threads): RSS +21..+49 MB (allocator growth, not freed);
the new way: +0..+2 MB. That supports the auditor's guess that per-request re-serialising drove much of the growth.
Bounded already (read): trails (moving's caps), unrest heads (30 h), image/imaged/track/camera caches (size caps),
news/unrest windows (by slot). Could not determine: growth over hours on the real server (cannot restart 8710 or attach
a profiler to it); whether the AIS world stream grows (no key here).

## Not fixed
- 14: models3d setRibbon reallocation (minor, not touched); status payload size.
- lowPower does not stop aircraft playback (moving's code); it only steps the flat icons at 1 Hz.

## Shared-file edits
web.py (data route, VIEWS, ships merge, memo routes, gzip level), collector.py, db.py, news.py (memo wrappers),
sites.py (areas_in), main.js (scheduler, list cap, status loop, banner threshold), util.js (local only), app.css (3
lines), aircraft.js (glide line + import), space.js (one line), sky.js (3 timers), hotspots/patterns/sanctioned/spikes/
people/markets/munich (one timer line each), sites.js (nuclear feed + merge), models3d.js, netwatch.js, new prefs.js, wire.py.

## For the owner / lead
- Restart the server after merging (all server parts). First start: one-off ALTER TABLE + CREATE INDEX (milliseconds).
- Military bases chip shows no count until switched on (its 1.6 MB is no longer downloaded at start).
- prefs.js `ww-prefs` keys: lowPower, animations, fps, maxModels, listRows, rate; setPrefs() + 'ww-prefs' event for the
  settings sheet.

## Lessons for CLAUDE.md
- Never build a JSON answer of a multi-MB payload per request: encode once per version (wire.py) and append per-request
  fields; the page's clock needs a fresh `now` in every answer, so never serve a cached body with an old `now` (no 304s
  for the page).
- The page downloads a feed only when /api/status shows a new payload version; a refetch with the same bytes only moves
  ages. New layers declare their feeds as usual; a layer that needs part of another feed gets a VIEW (web.py).
- Background polls go through prefs.every() (stops in hidden tabs); continuous animations check prefs.moving().
