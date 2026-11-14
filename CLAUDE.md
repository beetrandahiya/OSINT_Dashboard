# World Watch: project log

Personal live OSINT dashboard: a map of what is happening in the world and around Munich,
later a lookup tool for people and organisations from public sources. This file is the
single source of truth for any future session. Read it fully before doing anything.

## Status

- **2026-11-14: slice 0 (feed proof) done.** Collector, SQLite log, live feed report at `/feeds`.
- **2026-11-14: slice 1 done and approved** ("app feel in general is good"). The owner runs it on
  his Mac from the branch (`git pull`, restart); all 11 feeds were green from his network,
  CelesTrak included. The cloud session's port preview does not show up for him.
- **2026-11-14: slices 2-5 built in one go, waiting for review:** aircraft (near / military /
  world), news places, satellites with ISS track, launches, country-level outages, markets
  strip, layer chips with counts, one mixed list ("Coming up" then "Latest").
- **Building and testing happen in the cloud session; the owner pulls and tries each slice on
  his Mac; the M1 install comes at the very end** (owner's decision 2026-11-14).
- Not built yet: aircraft photos, type-specific aircraft icons beyond plane / helicopter, SF
  Symbols, 48 h history, around-me Munich view, search, conflicts layer, the lookup tool.

## Hard rules (from the owner, not negotiable)

- Real data only. Never simulate, guess, interpolate into fiction, or decorate.
- Every layer shows its source and when it last updated. A dead feed is shown as dead.
- No made-up analysis. Any summary must be traceable to source data. No invented scores.
- Free only. Free API keys are fine; list every key the owner must register for.
- It must set up and run first try from the README. One command, no Docker.
- Be honest: say when something is bad, broken, untested or slow.

## How we work

1. Interview in rounds before building anything new (options plus a recommendation).
2. Research, show a plan, wait for go.
3. Prove the riskiest part first.
4. Build in slices the owner tests by hand. After each: what changed, what to check,
   what opinion is wanted.
5. Keep this log current: decisions with dates, cancellations with reasons, lessons.

## Decisions (2026-11-14, from the interview)

| Topic | Decision |
|---|---|
| Main purpose of v1 | "What's happening now"; the other purposes build on it |
| Screen | Laptop/desktop browser. Phone is not a target |
| Sessions | Mostly quick checks, sometimes long exploring |
| Alerts | None in v1 |
| Map | Flat 2D map with a globe toggle |
| Opening view | Map plus a feed column of newest items across layers |
| News volume | Cluster by place, marker sized by number of distinct outlets |
| History | Keep the last 24-48 hours |
| Lookup tool | After the map works. Not in v1 |
| Private-person lookup | Record who consented and when, then search; deletable per person |
| Self footprint check | Usernames/emails, breaches, web mentions, domains/code, plus the wider Kali-style toolkits |
| Lookup storage | Local database, delete button per subject |
| Aircraft | World at a glance, full detail nearby, toggles for military/government/"interesting" |
| Own ADS-B receiver | No hardware, ever |
| Markets | A small strip of key numbers, delay labelled |
| Later layers wanted | Quakes/fires/storms, ships (AIS), Munich local, webcams and imagery |
| AI summaries | None in v1 |
| Languages | English UI; news in English, German, Hindi (see open issues on translation) |
| Access | Tailscale while testing; eventually probably one machine |
| Setup | One command, no Docker |
| Look | Follow system light/dark; calm by default, dense on demand; polish means typography, spacing, feel and speed |

### Decisions (2026-11-14, after the plan)

- **Look: Apple Maps.** Build it from Apple's real Human Interface Guidelines and from
  measuring Apple's own web apps, not from memory. Read the HIG before slice 1.
- **Icons:** Apple's SF Symbols where they fit, the same way the music app does it
  (`music/android/scripts/sf-symbols`: extracted on the owner's Mac from the installed SF
  fonts; the fonts never go in the repo). Aircraft get type-specific icons (airliner,
  helicopter, military and so on); the exact set is chosen later with the owner.
  SF Symbols' licence covers apps for Apple platforms; this is a private personal tool,
  the owner knows, his call.
- **Runs on the M1.** The owner accepts about 200 MB of RAM there.
- **Stack follows the music app** (repo `beetrandahiya/music`, read 2026-11-14): Python 3.13,
  Starlette + uvicorn, stdlib sqlite3, managed with `uv`; front end is vanilla HTML/CSS/JS
  with no build step; runs as a launchd LaunchAgent on the M1; deployed with an rsync
  `push.sh`; private via Tailscale, no login. This replaces the Node proposal.
  Reuse from it: the frosted-glass CSS recipe and theme-token structure in
  `server/music/pwa/app.css`, the font stack, `deploy/install-m1.sh` as the template.
- Music app constraints that also apply here: no Docker, no React, dependency-light,
  the owner tests by hand, keep automated checks minimal.

Not yet decided: explicit go on the plan with the Python stack.

### Decisions (2026-11-14, after trying slices 1-5 on his Mac)

- The app feel, the mixed list, the chips and the default of all layers on are approved.
- **Gliding allowed, as the one stated exception to "never guess":** nearby aircraft (10 s feed)
  are drawn moving on along their last reported heading and speed between reports, at most
  30 s ahead (`GLIDE_MAX` in `aircraft.js`). The card says it is an estimate. Do not extend
  this to other layers or to the 15-minute world aircraft without asking.
- **Route on the map:** a dashed great-circle line between the usual route's two airports
  (labelled "not its actual path") plus a solid trail of the positions we ourselves received
  since the page opened.
- **German and Hindi news added** as a second GDELT feed (`news_translated`). Headlines stay
  in their own language. GDELT lists these files about an hour before they can be downloaded,
  so the feed walks back to the newest one that exists. Cost: about 8 MB every 15 minutes
  (roughly 0.8 GB a day).

### Decisions (2026-11-14, second round of additions)

Owner's picks from researched options:
- **World layers (built):** disaster alerts (GDACS + NASA EONET), rain radar (RainViewer tiles),
  night shading (computed), aurora zone and Kp (NOAA SWPC), undersea cables (TeleGeography).
- **Aircraft extras (to build):** photos in the card (planespotters.net; needs a contact email or
  URL of the owner's in our User-Agent, not yet given), icons by aircraft type, GPS interference
  view (derived from ADS-B accuracy fields, must be labelled as derived). He did NOT pick
  emergency-squawk alerts.
- **Munich view (to build):** "overhead now" panel (nearest aircraft, current weather, DWD
  warnings via Bright Sky) and MVG / S-Bahn disruptions (unofficial MVG feed). Not picked:
  satellite passes, air quality.
- **Order:** new layers first, then aircraft extras and Munich; search and 48 h history later.
- GDACS detail: orange/red alerts kept a week past their end date, green cyclone/flood/volcano
  three days, green wildfires dropped (about 100 at any time), earthquakes dropped (USGS has them).
  I first told the owner there were "82 orange and red alerts right now"; that count included
  ended alerts. The real number of current ones was about a dozen. Corrected to him.

### Decisions (2026-11-14, feedback on the second round)

- **Headlines are machine-translated to English** (owner: "they need to be translated").
  `translate.py` uses the free, unofficial endpoint behind Google Translate's web page, per
  language, in batches, cached 90 days in `lookups`. The card shows the original beneath and
  says "machine-translated". If Google blocks it, headlines stay in their language and the
  feed note counts the failures. Only headline text is sent.
- **Night and aurora are soft pictures, not shapes:** both are drawn into a canvas in Web
  Mercator and laid over the map as an image source (`picture()` / `overlay()` in `sky.js`).
  Night fades from sun altitude 0 to -12 degrees (standard twilight definitions).
  No `ctx.filter` anywhere: Safari, the owner's browser, does not support it.
- **Military aircraft have no published routes** and the public trackers' flight-history
  files are not an API (403 / "blocked for scraping" when tried): do not scrape them. Instead
  the server keeps the positions it received for every near and military aircraft for 3 hours
  (`Collector.trails`, `/api/trail/{hex}`), and the selected aircraft shows that as its trail.
- Bug fixed: a layer whose feed the server had not fetched yet was asked again only after its
  normal interval (an hour for cables). `main.js` now retries after 5 s.

### Decisions (2026-11-14, third round: aircraft)

- **"All planes are planes"** (owner): no special look for aircraft around Munich. One colour and
  size for every civil aircraft. Live 10-second positions now follow the map: when zoomed in
  (zoom >= 5.2) the page asks `/api/aircraft/area` for the circle on screen (adsb.fi, up to 250 NM,
  reused 8 s, all adsb.fi calls spaced 1.2 s by `adsbfi_area`). Zoomed out, positions come from
  the 20-minute OpenSky snapshot. The fixed Munich feed stays in the collector (20 s) for the
  coming "overhead now" panel but the map no longer treats it specially.
- **Route lines must be right or absent** (owner: "it should be correct"). Three changes:
  1. The solid line is the path really flown, from OpenSky's `/api/tracks/all` via our
     `/api/track/{hex}` (cached 60 s; falls back to the positions this server received).
     Works for military aircraft too.
  2. adsbdb's crowd-sourced route is tested against the aircraft (`route_fits` in `web.py`:
     detour via the aircraft <= 1.25 x direct + 150 km, and heading within 100 degrees of the
     bearing to the destination). If it fails, the card says the listed route does not match
     and nothing is drawn. Example that prompted it: a flight over Turkey listed as Los
     Angeles to Shanghai.
  3. When it fits, the dashed line runs from the aircraft to the destination only, labelled
     "straight to the destination, not the planned path". No free source of filed flight
     plans exists; airways are not drawn.
- OpenSky's anonymous allowance (400 credits a day) is shared between world snapshots (4 each)
  and path lookups, so the snapshot moved from 15 to 20 minutes. A free OpenSky account gives
  ten times more; suggest it if the owner hits the limit.
- **Photos on:** planespotters.net, contact address in `data/contact.txt` (git-ignored) or
  `WW_CONTACT`; the owner supplied an alias address for this, which must stay out of the repo.
  Cached 24 h, photographer credited, image links back, per their terms.
- Route / trail / airport layers are not tied to the Aircraft chip any more (they were hidden
  when only Military was on, which is why military routes never drew).
- Owner tested this round: paths, gliding, photos and the route check work ("go on").

### Built 2026-11-14, fourth round (waiting for review)

- **Aircraft icons by category** (`SHAPES` / `KINDS` in `aircraft.js`): jet, heavy jet, propeller,
  fighter, helicopter, glider, balloon, drone, ground vehicle, drawn as paths in code, sized by
  class. The category is what the aircraft broadcasts (adsb.fi / adsb.lol). OpenSky's
  `extended=1` category came back 0 for every aircraft, so world-feed aircraft stay generic.
  The card also shows the position accuracy the aircraft reports (NACp, in metres).
- **GPS interference layer** (`gps.js`, feed `gps`): GPSJAM's daily file
  (`gpsjam.org/data/<day>-h3_4.csv`, newest day from `manifest.csv`), hexagons turned into
  polygons with the `h3` Python package (new dependency). GPSJAM's own bands: red > 10 % of
  aircraft with poor accuracy, yellow 2-10 %; hexagons under 5 aircraft dropped. It is their
  analysis of a past day, labelled as such. GPSJAM states no licence; private use with credit.
- **Munich view** (`munich.js`, World / Munich switch in the sidebar): weather now and DWD
  warnings (Bright Sky, feed `munich_weather`), the 8 nearest airborne aircraft (feed
  `aircraft_near`), MVG messages in force (feed `mvg`, unofficial; incidents first, then rail,
  first 30 headlines machine-translated). Switching flies to Munich and back.
- Peak memory in the sandbox is now about 180 MB (was 82 MB with 11 feeds); the owner's limit
  for the M1 is about 200 MB. Watch this; the GPS file and the 8 MB translated news file are
  the big moments.
- Not built: search, 48 h history, SF Symbols, conflicts layer, the lookup tool, M1 install.

### 2026-11-14, after the fourth round

- Owner: icons by type, GPS layer and the Munich view all work.
- **No move to the M1 yet** (owner: "there's still lots to do"). Do not raise the move again
  until he does.
- **Design sheet** for judging icons and tokens: https://claude.ai/artifact/5wHPZPnid3bhtgTiKiq9iG
  Source template in `docs/design-sheet.tpl.html` (the `__DATA__` placeholder takes the
  `SHAPES` and `KINDS` from `aircraft.js`). Republish it when icons, colours or components
  change, so he always judges the current state. Waiting for his notes on it.

### 2026-11-14, fifth round

- Owner approved the redrawn helicopter, drone and heavy-jet icons. Multi-part icon paths are
  drawn piece by piece (no even-odd fill), or overlapping parts cut holes.
- Asked what next, he picked: **ships, fires and imagery, and starting the lookup tool**; no
  preference among the refinements (search, "new since last visit", declutter, chip tidy), so
  those follow in my recommended order: search, then new-since-last-visit. SF Symbols: later.
- **Fires (built):** NASA FIRMS MODIS 24-hour CSV, which needs no key
  (`firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv`,
  ~0.9 MB, ~11,000 detections). Dots only, not in the list; the card says a detection is a
  hot pixel, not necessarily a wildfire. The larger VIIRS files timed out from the sandbox.
- **Photo (built):** NASA GIBS tiles, layer `VIIRS_NOAA20_CorrectedReflectance_TrueColor`,
  yesterday's date, inserted under the base map's place names; names switch to white while
  it is on (`setPhoto` in `map.js`). Off by default (`defaultOff` on a layer module).
  The VIIRS SNPP and NOAA-21 layers stop at 2026-11-02; NOAA-20 is current.
- **Ships (built, partly):** only Finland's open Digitraffic AIS (northern Baltic, ~600 ships,
  no key, CC BY 4.0). World coverage needs an aisstream.io key the owner must register for;
  its websocket client is NOT written yet because it cannot be tested without a key. Write it
  with him once he has one (key in `data/`, never in git, never pasted in chat).
- FIRMS and CelesTrak both time out intermittently from the cloud sandbox (10 s tunnel limit);
  that is the sandbox, not the feeds. Do not "fix" it by shortening retries.
- 23 feeds; peak memory in the sandbox about 175 MB.

## Boundaries on the lookup tool

Public sources only. Never build features aimed at tracking a private person's location,
home address or routine. Private-person lookups require a recorded consent entry.

## Research findings (2026-11-14)

### Prior art: verdict is build our own, borrow parts

- **God's Eye View** (bilawalsidhu/gods-eye-view, MIT code, ~65k stars, active). Vue 3 +
  CesiumJS, ~800k lines, Cesium-only (no flat map), no markets or outage layer. Traffic is
  simulated and launch ascent paths are synthesised, both admitted in its README. Does
  per-layer feed health well (`src/data/feedState.js`). Borrowable MIT pieces:
  `src/data/satellitePass.js` (pass prediction, depends only on satellite.js), the
  CelesTrak fetch/cache, the OpenSky credit governor, the source/policy/rendering split.
- **ShadowBroker** (BigBodyCobain/Shadowbroker, AGPL-3.0, ~11.6k stars, active). Python
  FastAPI + Next.js + MapLibre, ~350k lines, Docker, 4 GB backend default. The HN
  criticisms were true at launch (random "escalation" percentages, simulated UAVs) and
  were removed within a week. Upstream services have complained about its scraping load.
  Ideas only (AGPL): tiered fetch scheduling, multi-source ADS-B fallback, backend-held keys.
- **worldmonitor** (koala73, AGPL-3.0, ~90k stars). Closest to our layer list, MapLibre +
  deck.gl with a globe toggle, but 10k files and tied to Vercel/Redis/Clerk. Read, don't copy.
- Smaller MIT references: kevtoe/worldview, katipally/argus.
- Lessons to keep: per-source "last updated", keys never in the browser or in git, cache
  CelesTrak, identify ourselves with a User-Agent, be a polite client.

### Feeds, measured from a cloud sandbox on 2026-11-14 ~09:47 UTC

| Layer | Source | Key | Measured | Limit / gotcha |
|---|---|---|---|---|
| Aircraft nearby | adsb.fi `/v3/lat/lon/dist` | none | 105 KB (17 KB gzip), 0.3 s, 185 aircraft in 100 NM of Munich | 1 req/s, personal use, must credit |
| Aircraft mil/LADD/PIA | adsb.lol `/v2/mil` etc. | none | 34 KB, 88 aircraft, 0.5-1.5 s | 500 req/day keyless |
| Aircraft world | OpenSky `/states/all` | none | 790 KB (239 KB gzip), 6,102 aircraft, 0.9 s | anonymous 400 credits/day = ~100 world calls, so one per ~15 min |
| Aircraft | airplanes.live | - | 403 "contact us" from datacenter IP | untested from a home IP |
| Routes / photos | adsbdb.com, planespotters.net | none | work | photos need a User-Agent with contact, link back and credit |
| Satellites | CelesTrak GP JSON | none | stations 7.6 KB, visual 65 KB | **failed 3 of 5 attempts here**; fetch at most every 2 h or get blocked |
| Launches | Launch Library 2 | none | 11 KB, 0.2 s | 15 req/hour |
| News | GDELT GKG 15-min file | none | 2.2 MB zip, 6.7 MB raw, 528 articles, 158 city-level places | location is machine-extracted |
| News | GDELT DOC API | none | 18 s response, 429s | too flaky to depend on |
| News | GDELT GEO API | - | **404, treat as dead** | |
| News | GDELT translation files | none | listed in lastupdate but **404 for the newest ~3 slots**; 06:00 slot worked | titles stay in original language; 113 German, 0 Hindi in one batch |
| Quakes | USGS all_day.geojson | none | 166 KB, 233 quakes | updates every minute |
| Hazards | GDACS, NASA EONET | none | work | |
| Outages | IODA v2 | none | 7-12 KB, 1-10 s | undocumented limits |
| Outages | Cloudflare Radar | free token | needs token | optional later |
| Markets | Yahoo chart endpoint | none | works, 1.7 KB per symbol | unofficial, can break any day; label "delayed, unofficial" |
| Markets | CoinGecko, Frankfurter (ECB) | none | work | ECB rate is daily, not live |
| Markets | Stooq | - | **dead for keyless use** | |
| Conflicts | ACLED | - | **no free event-level access** | excluded |
| Conflicts | UCDP | token by email | monthly candidate data, weeks old | optional later |
| Basemap | OpenFreeMap | none | style loads | no SLA |

None of adsb.fi, adsb.lol, OpenSky or Yahoo allow browser calls (no CORS), and history
needs storage, so a static site is ruled out: a small local server is required.

Keys needed for v1: **none**. Optional later: Cloudflare Radar token, NASA FIRMS key,
aisstream.io key, adsb.lol key, UCDP token.

### Lookup tools (for the later milestone)

Maintained and usable without paid keys: Maigret (MIT, JSON, library; best pick),
Sherlock (MIT), WhatsMyName dataset, theHarvester (GPL-2), Amass, PhoneInfoga.
Stale or dead: Holehe (2024), SpiderFoot (2023), h8mail (2022). Free breach checks to
verify: XposedOrNot, HIBP breach catalogue, Hudson Rock Cavalier. HIBP per-email is paid.

## Plan (proposed 2026-11-14, awaiting go)

- **Approach:** build our own; borrow MIT pieces from God's Eye View; ideas only from AGPL projects.
- **Stack:** one Python process (collector + local API + SQLite), Starlette + uvicorn via
  `uv`, matching the music app. Browser front end in vanilla JS with MapLibre GL JS v5
  (flat map and globe from one engine), satellite.js for orbits, OpenFreeMap basemap.
  No framework, no Docker, no build step.
- **Where:** collector on the always-on M1 (needed for 24-48 h history); view from any browser.
  Weight: parsing one full round of the three biggest feeds (GDELT file, world aircraft,
  nearby aircraft) took 0.09 s and 32 MB peak in Python on a cloud Xeon (measured
  2026-11-14). Everything else about weight on the M1 is an estimate until the proof
  measures it there.
- **Order:** 0 feed proof (24 h run, honest timestamps, status page) -> 1 map shell, quakes,
  feed-status panel -> 2 aircraft -> 3 news clusters and feed column -> 4 satellites, ISS,
  launches -> 5 markets strip, outages -> 6 48 h history -> 7 around-me Munich -> lookup milestone.

## Risks and open issues

- Conflict data is the weakest layer: no free curated source. v1 can only show GDELT
  media-derived events, clearly labelled unverified, plus hazards.
- Hindi/German: no free feed gives translated titles. Options: show originals, or a local
  translation model later (needs the Windows PC, not the 8 GB M1).
- World aircraft view refreshes about every 15 minutes on free anonymous OpenSky; only the
  area being looked at can be near-real-time.
- CelesTrak reliability from the owner's network is unverified; cache on disk, keep last good.
- Yahoo Finance is unofficial and may break; markets strip must degrade visibly.
- All measurements were taken from a datacenter IP once. The proof must repeat them from
  the owner's machine over 24 h.

## Mockups

Five looks (Apple Maps, Flightradar24, Ops room, Financial Times, Linear) drawn with a
frozen real capture: https://claude.ai/artifact/LDCXQkPUjfRagb61zxtQxL
Owner chose Apple Maps (2026-11-14).

## How to run

`cd server && uv run python -m worldwatch serve`, then open http://127.0.0.1:8710/ .
Needs only `uv`. No keys. Data in `data/` (git-ignored). Settings via `WW_*` environment
variables, see `server/worldwatch/config.py`.

## Code map

- `server/worldwatch/feeds.py`: one function per feed plus the `FEEDS` table (interval, limits).
- `collector.py`: timers, back-off, the four states (waiting / ok / late / failing), clock check.
- `db.py`: `fetches` log (7 days) and `latest` good payload per feed.
- `web.py`: `/api/status`, `/api/data/{feed}`, the page in `static/index.html`.

## Design rules (Apple Maps look, sources read 2026-11-14)

All numbers are in the comment at the top of `server/worldwatch/static/app.css`. In short:
- From maps.apple.com's stylesheets: panels are blur(50px) over #fff9 (light) / #0009 (dark),
  solid #f2f2f2 / #2b2b2b without transparency; card radius 16px, control radius 12px; controls
  36x36; shadow `0 -2px 20px #0000001a, 0 0 12px #0000001a`; transitions .25s ease-in-out;
  focus ring 2px #007cff; label / separator / fill colours as tokens.
- From Apple's HIG: type sizes 22 / 17 / 15 / 13 / 11 (never under 10); text contrast 4.5:1;
  a selected map item gets an outline as well as a colour change; markers may carry a 2-3
  character label; cluster overlapping points; no colour-only meaning; with Reduce Motion, no
  flying and no blur animation; no in-app dark-mode switch (follow the system).
- Apple's licence forbids embedding the SF font, so the CSS names the system font only.
- SF Symbols can only be produced on the owner's Mac (see the music repo's script). Until
  then the UI uses CSS-drawn shapes, no icon font.
- Our choices that are not Apple's: left panel 380px (Apple's card is 420px) to leave more map.
- Layer colours (Apple system colours): news red, quakes orange, disasters pink, aircraft indigo,
  military purple, satellites green, launches teal, outages and cables grey, rain blue, aurora mint. One shared black/white ring marks
  the selected item on any layer.
- Every layer is one module in `static/js/` with the same shape: `id, title, color, feeds
  {name: seconds}, layers [map layer ids], addTo, paint, onData, render, count, rows, locate,
  ring, detail` (optional `owns`, `moving`, `visible`). `main.js` knows nothing layer-specific.
- Aircraft are drawn where they last reported; never moved forward between reports. The 15-min
  world view is drawn smaller and grey, and is hidden wherever a fresher feed has the aircraft.
- Routes come from adsbdb via our `/api/route/{callsign}`, looked up only when a card opens,
  cached a day in the `lookups` table, labelled crowd-sourced.
- Satellites: positions computed in the browser with satellite.js (vendored, MIT) from
  CelesTrak OMM data; the card states the age of the orbit data. ISS track is +-45 min.
- Outages: IODA country-level events only (`entityType=country`); marker at the country's
  centre from `countries.json` (generated from the `world-countries` npm package, ODbL).
- Front end files: `static/index.html`, `app.css`, `js/main.js` (wiring), `js/map.js` (base map,
  recoloured OpenFreeMap "positron" style for both themes, globe), `js/quakes.js` (one module
  per layer: addTo, paint, setData, rows, detail), `js/util.js`. MapLibre 5.24.1 is vendored.

## Lessons

- **GDELT file names are not times** (2026-11-14). The file "20261114101500" was published at
  10:04:42 UTC, eleven minutes before its own name. We use the listing's Last-Modified header
  as the data time. Never derive a time from a file name.
- OpenSky does not compress its answer: 0.8 MB per world snapshot, about 77 MB a day at 15 min.
- The collector compares its clock with the feeds' HTTP Date headers and shows the difference,
  because every "x seconds ago" depends on the local clock being right.
- Measured in the sandbox (Linux, cloud Xeon), first minute: 82 MB peak memory, about 1 % of
  one core. Not measured on the M1 yet.
- This cloud sandbox cannot reach the owner's machines (no Tailscale, no Remote Control; his
  Claude runs only in the browser). He runs things on the Macs himself.

- **GDELT lists files before they exist** (2026-11-14). Both series do it: the English file can
  be listed 15-30 minutes before it downloads, the translated one about an hour. `_gdelt_newest`
  walks back slot by slot to the newest file that answers 200 and uses that file's own
  Last-Modified as the data time. A 404 on the listed file is normal, not a failure.

## Cancelled / ruled out

- Forking God's Eye View, ShadowBroker or worldmonitor (size, licence, wrong map engine). 2026-11-14.
- Static-site hosting (CORS and history). 2026-11-14.
- ACLED, Stooq, GDELT GEO API, own ADS-B hardware. 2026-11-14.
