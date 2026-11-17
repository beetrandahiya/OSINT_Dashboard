# Audit: intel (information layers and dossiers)

Scripts in /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/intel/ (layer.js = one layer alone + cards,
dbg.js = run code in page, dossier.js / nav.js = dossiers, sky.js, startup.js). Screenshots in intel/shots/.

### Person dossier "In the news" is always 0 (offsets never stripped)   [severity: high]  [confirmed by running]
Repro: open the dossier of Q22686 (Trump) or Q1058 (Modi) (`STEPS='qid:Q22686' node dossier.js`).
Seen: Signals tile "In the news, 6 h: 0 outlets, not named in any article we hold" next to "Reported at Washington, 141 headlines,
246 outlets" (shots/dos-qid_Q22686.png). The "headlines that name them" list is empty for everyone.
Expected: the outlet count and headlines from GKG persons.
Cause: dossier.py:451 `key not in {news_window._norm(p) for p in row[8].split(";")}`: row[8] is V2EnhancedPersons ("name,offset;..."),
so every normalised entry is "donald trump,1234" and never equals the key. news.leaders_today strips the offset with
`p.rpartition(",")` (news.py ~310), the dossier does not.
Fix: `{news_window._norm(p.rpartition(",")[0] or p) for p in row[8].split(";") if p}`. Also note: names are only kept for articles naming
a followed leader (news.WATCH), so non-leaders will still read 0; the tile should say "only tracked for heads of state/government" for them.
Risk: none.

### ICC check says "not named" for Putin/Netanyahu: the kept copies are the bot-shield page   [severity: high]  [confirmed by running]
Repro: `curl /api/dossier/courts/Q7747?name=Vladimir%20Putin` -> "icc":{"cases":[],"situations":[]}; dossier shows
"International Criminal Court: not named in its case list or situation pages."
Seen: data/icc-situations.json holds, for 17 of 19 situations (ukraine, palestine, ...), title "Gcore", text "Please enable cookies ...".
Feed courts_icc state "ok". Only afghanistan and kenya are real pages.
Cause: feeds.py:945-966 falls back to `kept.get(slug)` without checking it, and `save_situations` re-saves the kept copies; copies saved
before is_challenge existed (or by a version that missed it) live forever. courts.is_challenge(kept text) returns True, so the check
exists but is not applied to the fallback. profile.js:227 then states a negative.
Fix: in courts.load_situations (or at the fallback) drop entries where `is_challenge(s["text"])`; carry a `missing: [slugs]` list in the
payload; in court_records/profile.js say "ICC: N of 19 situation pages could not be read (bot protection); a match there cannot be ruled
out" instead of "not named"; mark the feed late/failing when most pages are refused. (Separately: the feed sends a fake Safari
User-Agent, which the project's own rule "identify ourselves" argues against.)
Risk: low.

### Hotspot pulse keeps the map from ever going idle: loading bar stuck on, full re-render every frame   [severity: high]  [confirmed by running]
Repro: default layers (Hotspots and Rain are both on by default), any hotspot present. dbg.js with {"hotspots":true,"rain":true}.
Seen: `#loadbar` never hides (5 samples over 10 s after 25 s, tiles all loaded); with Rain alone it hides. Map 'idle' fired 0 times in
6 s with hotspots on (3 times with it off); 6 setPaintProperty and ~17 triggerRepaint per second in software GL, i.e. one full map
repaint per animation frame on a real GPU (globe + 3D + models) for as long as a hotspot exists.
Cause: hotspots.js:12-19 `pulse()` calls `setPaintProperty('ww-hot-pulse', ...)` every rAF; main.js:69-76 clears the tile loading flag
only on 'idle', which never comes.
Fix: animate the pulse without touching the style: either a CSS-animated HTML marker per hotspot (maplibregl.Marker, a handful at most),
or a small canvas overlay like netwatch.js; at minimum throttle to ~10 Hz and stop when the tab is hidden. In main.js, also clear `tiles`
when `map.areTilesLoaded()` is true on 'sourcedata', not only on 'idle'.
Risk: low; the marker approach needs the click to still pick the hotspot (markers can dispatch ww-pick).

### Open cards are redrawn every few seconds by unrelated feeds (resets the satellite-picture day, can drop "photographed" results)   [severity: medium]  [confirmed by running]
Repro: sky.js: only News on, open a news card, press the "11-15" day button, move the mouse off the card, wait 65 s.
Seen: the card was rebuilt 8 times in 65 s and the picture/day went back to "Yesterday". The imaged.js result is thrown away when the
card is rebuilt while /api/imaged is in flight (`if (!document.body.contains(box)) return;`, imaged.js:49), leaving the button again.
Cause: main.js load() calls refreshPick() after every feed load of every layer, even layers that are off and unrelated to the open card;
renderDetail rebuilds innerHTML; '.sky' is not in the `keep` list (main.js:225) and an in-flight #imaged has no `done` yet.
Fix: only call refreshPick when `layer.id === picked?.layer` (or the layer's own feeds); add '.sky' state to `keep` (store the chosen day
on the figure's dataset and re-apply), and mark #imaged `data-done="pending"` while fetching and re-attach the result to the current
box by id instead of bailing.
Risk: low; layers whose card depends on another feed (warships uses ships + usni) need their feeds listed.

### "Open the pictures" (Maxar) in the country dossier crashes the page state   [severity: medium]  [confirmed by running]
Repro: openCountry({cc:'US'}), click "Open the pictures" under a Maxar event (e.g. "Texas Flooding July 2025").
Seen: overlay closes, nothing opens, "Cannot read properties of undefined (reading 'detail')" then "(reading 'moving')" 5 times a second
until something else is picked; every feed load also throws inside refreshPick.
Cause: dossier_country.js emits showOn('maxar', ...) but the maxar layer import is commented out in main.js:6, so byId.maxar is undefined;
pick() / ring interval (main.js:149) dereference it.
Fix: drop the maxar "Show on map" links (or the whole Maxar block) while the layer is off, and guard pick(): `if (p && !byId[p.layer]) return;`.
Risk: none.

### Hotspot signal links never select unrest, TFR, navy, quake or disaster items   [severity: medium]  [confirmed by running]
Repro: dbg.js with hotspots, unrest, airspace, ... on; open the hotspot card, click each signal link.
Seen: orbit link opens its card; airspace "TFR:6/7632" and unrest "285145|clash|20261116" only fly to zoom 7, the hotspot card stays.
Cause: main.js ww-try-pick requires `l.owns?.(id)`; unrest.js, airspace.js, navwarn.js, quakes.js, hazards.js define no `owns`.
Fix: add owns to those layers (`owns: id => groups.some(g => g.id === id)`, `id => /^(FIR|TFR):/.test(id)`, etc.) or in ww-try-pick
fall back to `l.locate(id)` being non-null. For unrest single-outlet groups, map to 'unrest1' when outlets < 2.
Risk: none.

### Taiwan, Nauru (and others): former heads of government listed as current   [severity: medium]  [confirmed by running]
Repro: STEPS="cc:Taiwan;cc:Nauru" node dossier.js
Seen: Taiwan: Head of government Wu Den-yih, Cho Jung-tai, Chang Chun-hsiung, Vincent Siew, Frank Hsieh, Lien Chan. Nauru: six heads of
government back to 2001.
Cause: dossier.py _facts keeps every non-deprecated statement without an end date (line ~85); Wikidata often has old P6/P35 statements
without P582 but marks the current one preferred. Same in _facts_entity.
Fix: per property, if any statement has rank preferred keep only preferred ones (use `wikibase:rank` in the SELECT, or query `wdt:` truthy
values); bump the cache key (country-facts2:) so the 30-day cached wrong lists go away.
Risk: low.

### Wikidata "mul" labels: names become Q-ids or silently vanish   [severity: medium]  [confirmed by running]
Repro: openProfile('Q42').
Seen: dossier title "Q42" (Douglas Adams); courts then say "a one-word name cannot be searched". Wikidata's EntityData for Q42 has no
"en" label, only "mul" ('Douglas Adams'); wbgetentities languages=en returns {} for it.
Cause: lookup/people.py:86 and :121-124, dossier.py:143-146, :527-536 read only labels.en; profile.js `named()` then drops any Q-id
entries (offices, parties, education) without saying so.
Fix: read `labels.en or labels.mul` and request `languages=en|mul` (or `languagefallback=1`); bump profile cache key.
Risk: none.

### Protest cards: every article reads "in 234482885 d"   [severity: medium]  [confirmed by running]
Repro: `node layer.js unrest 5` (WAIT=14000).
Seen: "rockymounttelegram.com · in 234482885 d" on every story line of every protests-and-clashes card.
Cause: unrest.py:244/250 keep article "time" as the GDELT stamp string ("20261116100000"); unrest.js passes it to ago().
Fix: in groups() output `{**a, "time": _t(a["time"])}` for each article (the sort before can stay on strings).
Risk: none.

### Protest pictures blocked by the image proxy (all 404)   [severity: medium]  [confirmed by running]
Seen: 15 of 15 unrest article images -> 404 from /api/news/image; list thumbnails and card heroes vanish (onerror removes them).
Cause: web.py news_image allows only `news_window.images()` (the current 6-hour window, and right after a restart only the few files
loaded), but unrest borrows pictures from `heads_seen` for 30 h. The documented fix "protest cards keep their picture after 6 h" cannot work.
Fix: allow `url in news_window.images() or url in {v[2] for v in unrest_window.heads_seen.values()}` (cache that set per update).
Risk: none (still a closed allowlist).

### Military-area cards switch to another area when the map moves   [severity: medium]  [confirmed by running]
Repro: dbg.js, Military bases on, zoom 8 near Hisar, pick 'marea:0' ("Suratgarh Airbase"), pan 250 px.
Seen: the same open card now shows "ishwar army training" and the ring jumps to it.
Cause: sites.js ids are `'marea:' + index` into `areas`, which is replaced on every moveend (pull()).
Same pattern, less often: hotspots.js 'hot:i' (reloaded every 5 min), spikes.js 'spike:i' (2 min), fires 'fire:i', front 'front:p/c i'.
Fix: use stable ids (OSM ref `a[3]` for areas; hotspot = rounded lat/lon + first signal id; spike = place name).
Risk: low.

### Dead feed shown as live: Internet hijacks from a 30-hour-old snapshot   [severity: medium]  [confirmed by running]
Seen: cf_radar is "not set up" (token revoked); the Internet hijacks chip still shows 21, list rows "29 h ago", cards "(still announced)",
"about: last 24 hours". Outage layer also draws Cloudflare notes from it. Only the card footer says "read 28 h ago".
Expected (hard rule): a dead feed is shown as dead.
Fix: in netwatch.js/outages.js, when `info.state !== 'ok'` or data older than 2 intervals, show the chip note "feed off" and drop
"still announced"/"ongoing" wording; or let the server stop serving payloads of feeds whose error says "not set up".
Risk: none.

### Palestine dossier has no leaders, capital or population   [severity: medium]  [confirmed by running]
Seen: Palestine (cc PS / fips GZ): no heads, Natural Earth 2019 population; "Wikidata, current statements only; fetched 3 min ago".
Cause: geo table maps PS to Q23792 (the geographic region) not Q219060 (State of Palestine); facts come back empty but non-null, so the
leaders-list fallback (dossier.py ~399, only when `not facts`) is skipped, and the empty result is cached 30 days.
Fix: QID overrides in geo (PS -> Q219060, check XK/TW/EH too); use the leaders fallback when head lists are empty; do not cache an empty
facts dict for 30 days.
Risk: low.

### Layers that are off still download and parse everything; news re-downloaded every minute   [severity: medium]  [confirmed by running]
Repro: startup.js with only Earthquakes on, 65 s.
Seen: 68 /api/data requests, 3.9 MB gzipped (~12 MB JSON parsed): news 823 KB, news_translated 540 KB, sites 441 KB, cameras 293 KB,
cables 234 KB, fires 177 KB ...; the same feed fetched once per layer that names it (unrest x2, airspace x3, ships x2, vip x2,
cf_radar x2). News is polled every 60 s although it changes every 15 min: ~0.8 MB/min while the News chip is off. Each response is
also re-serialised on the server's event loop (1.5-1.9 MB json.dumps per request).
Cause: main.js map 'load' loops `for (const l of LAYERS) ... load(l, feed); setInterval(...)` regardless of `on[l.id]`; no dedupe.
Fix: one poller per feed (fan out to every layer that wants it); poll only feeds of layers that are on (plus feeds dossiers need,
fetched on demand); send `?since=<data_time>` and answer 304/`{unchanged:true}` when the feed has not changed; cache the serialised
body per feed version on the server.
Risk: medium (dossiers and hotspots read other layers' state; they would need on-demand loads).

### Retry chains pile up for a feed that never has data   [severity: low]  [by reading only]
Cause: main.js load(): no payload -> `setTimeout(load, 5000)`, which reschedules itself forever, and every setInterval tick starts a
new chain. On a fresh install without a Cloudflare token (cf_radar never has a payload) hijacks + outages add a new 5-s chain every
10 min: ~12 chains after an hour, all hitting /api/data/cf_radar.
Fix: keep one pending retry per feed (`if (retrying[feed]) return;`) and stop retrying when the status says the feed is "waiting/not set up".
Risk: none.

### Escape in a dossier also closes the card underneath   [severity: low]  [confirmed by running]
Seen: open leader card -> "Dossier of India" -> Escape: overlay closes and the leader card is deselected too.
Cause: profile.js and main.js both handle keydown Escape.
Fix: in main.js skip when `!document.getElementById('profile')?.hidden`, or stopPropagation in the dossier handler (register it with capture).
Risk: none.

### "Show on map" from a dossier selects items on layers that are switched off   [severity: low]  [confirmed by running]
Seen: with chips off, Show on map for unrest/quakes/military/news/hazards opens the card and ring but the item's layer stays hidden.
Fix: in the ww-pick handler (or showOn), switch the layer's chip on first (same code as the chip click).

### Airspace line style warning on every load   [severity: low]  [confirmed by running]
Seen: "Expected value to be of type boolean, but found null instead."
Cause: airspace.js:29 `['case', ['get', 'tfr'], 1.2, 1.2]` on FIR features without `tfr`. Fix: `'line-width': 1.2` (both branches are equal).

### Front-line area ring drawn at the polygon's first vertex; stale indices can throw   [severity: low]  [by reading only]
Cause: frontline.js locate() returns `d.areas[n].rings[0][0]`; locate/detail for 'p'/'c' dereference `d.points[n]` without a check, so
after a refresh with fewer points renderDetail throws inside load() and the card goes stale. rows() meta uses esc() and renderList
escapes again (double-escaped "&amp;").
Fix: centroid for areas, `?.` guards, drop the esc() in meta.

### Smaller data/wording issues   [severity: low]  [confirmed by running]
- Hazard dates from other years print without the year ("Began 21 Sept, 00:00 (1518 d ago)"); util.local() omits the year. Add the year
  when it differs from this year.
- GDACS drought country lists contain empty entries ("Aruba, , Brazil").
- TfL camera "view" shows a raw escape: "facing Zoom-SOUTH A10 \/ Crown Road junction".
- Country dossier "Military aircraft over it" names "adsb.lol military list" though the feed is adsb.fi now.
- Navy-warning rows use the fetch time as their time, so they sort as "newest" on every fetch.
- News card hero image is the first article with a picture, often not the first story listed under it.
- Find box: the list is re-rendered when people results arrive (~0.3-6 s later), so a click on a country row at that moment hits a
  detached node (seen in tests). Keep the country rows and append people below instead of replacing innerHTML.
- Nonsense QID shows a raw httpx message ("HTTPStatusError: Client error '400 Bad Request' for url ...") instead of "No such Wikidata item".
- A non-person QID (Q64 Berlin) builds a "Person dossier"; profile() never checks P31 = human.

Checked and fine:
- News: clusters at zoom 3 (133 groups), cluster click zooms 3 -> 4.2, pointer cursor, single place opens card; /api/news/place answers
  in 0.2 s with all outlets; untranslated headlines counted and labelled; outlet totals vs distinct outlets differ by <= 2.
- News image proxy and camera image proxy allowlists hold (only listed addresses / six camera hosts); cable_about id regex.
- Cards without bad tokens (undefined/NaN/null) for news, unrest, hazards, navwarn, hijacks, cables, front, airspace, bases (incl. index
  out of range -> "No longer in the feed"), nuclear (plant, facility, test site, explosion point), cameras (all six sources incl. TfL clip,
  Caltrans HLS, Singapore via id), sdr data (no missing band/url).
- Country dossiers: Germany, Taiwan, Kosovo, USA ("usa" alias), Nauru, Antarctica, Western Sahara; sea point and unknown code give an honest
  "not in a country we know"; Wikidata 429 in people search shows "Wikidata is limiting requests ...".
- Navigation: leader card -> Open the dossier; person flag -> country; country head -> person; quick open person then country shows
  the country (token check works).
- Hijack streak canvas stays aligned on a tilted (50 deg), rotated (40 deg) globe; leaders' side-by-side dots keep screen offsets.
- Camera card refresh timers clear themselves when the card closes.

Could not test here:
- Translation (Google blocked the sandbox; paused) beyond the "could not be translated" path.
- OpenSanctions, Cloudflare Radar live, Windy (no keys); NGA navy warnings (503).
- Frame cost of the hijack canvas and hotspot pulse on a real GPU / Safari; 3D terrain.
- Breaking spikes (none in the current data) and their cards.
