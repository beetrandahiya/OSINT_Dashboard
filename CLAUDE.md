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

## Lookup tool (milestone 2): interview done 2026-11-14, plan proposed, awaiting go

Owner's answers:
- First thing that works: **his own footprint**.
- Depth: "everything like a true OSINT setup in Kali", with all identifier kinds: usernames,
  email addresses, full name and phone number, domains and code.
- Requests come **from his Mac, only when he presses the button**. No Tor.
- Lives on **its own page** in the same app and look.
- Results as a **graph view** (identifiers, accounts, sites linked), not a triage list.
- Runs only on demand. **Findings only**: no delete links, no erasure letters.

Limits I set and told him: no downloading of leaked password dumps (breach names and leaked
data types only); sign-up / password-reset probing can send reset emails to his own inbox.
While testing from the cloud, use only public test identifiers, never his.

Research (2026-11-14, probed from the sandbox with dummy identifiers):
- WhatsMyName dataset: 691 sites, CC BY-SA 4.0, one JSON file with a URL pattern, the
  expected "exists" / "missing" signals and known-good accounts per site. We can write our
  own checker on httpx (no new dependency) and self-test each site with its known account.
- Maigret 0.6.6 installs on Python 3.13 but pulls 141 packages, 190 MB. If used, run it on
  demand as a separate process (`uvx maigret`), never as a dependency of the server.
- No key needed and answering: XposedOrNot (breaches per email), HIBP `/breaches` (catalogue
  only), Hudson Rock Cavalier (infostealer exposure), Gravatar, keys.openpgp.org, GitHub
  commit search by author email, rdap.org. `phonenumbers` (offline) gives country and
  original carrier.
- Flaky from here: crt.sh (502), Wayback CDX (timeout). DuckDuckGo's HTML page answered but
  search scraping is unreliable everywhere.
- Holehe (sign-up probing) has had no release since 2024; expect many dead modules.

### Lookup, built 2026-11-14 after his "go on" (waiting for review)

- **Proof (step 1):** `lookup/usernames.py` self-test from the sandbox: 690 sites in the list,
  **404 trusted** (found the known account, did not find a made-up name), 0 false alarms,
  286 blind (122 of those answered 403 to a datacenter address). 48 s for 1,380 requests.
  The test must be run again on the owner's Mac (button "Test the checker"); results are per
  computer, kept in `data/whatsmyname-selftest.json`. Only trusted sites are asked in a scan.
- **Slice 2:** `/lookup` page (`static/lookup.html`, `lookup.css`, `js/lookup.js`), API in
  `lookup/api.py`, storage in `lookup/store.py` (`data/lookup.db`, separate from the map's db).
  One subject for now: the owner. Username sweep plus email checks (`lookup/emails.py`:
  XposedOrNot breaches, Hudson Rock, Gravatar by hash, keys.openpgp.org, GitHub commit search).
  Before a scan a sheet lists exactly what is sent to whom; scan runs as a background task with
  progress; failed services are listed, never skipped silently.
- **Graph:** a radial layout computed in `layout()` (you in the middle, identifiers around,
  findings fanned out behind their identifier in rings), plain SVG, pan and zoom, no library.
  "Not me" hides a finding and survives rescans (`findings.not_me`).
- The lookup API answers only to 127.0.0.1 unless `WW_LOOKUP_REMOTE=1`.
- Tested end to end with a public figure's username and `test@example.com` only: 92 profile
  pages and 218 email findings in 20 s. Test data wiped afterwards.
- Not built yet: full name, phone, domains and GitHub account (the page says "not checked yet"
  for those), sign-up probing, the optional Maigret run, other subjects with consent records.

### Satellites, round 2 (built 2026-11-14 at the owner's request, waiting for review)

He asked for: a trajectory for every satellite (not only the ISS), satellites "on scale
height", a way to see what a satellite looks at, a link to https://www.watched.earth, and
smaller dots. Built in `space.js`:
- Ground track for the selected satellite (half an orbit back, one ahead, capped at 3 h each
  way); the ISS track stays always on.
- **True height on the globe:** MapLibre draws only on the surface, so satellites are drawn on
  a canvas over the map. `camera()` works out the globe's camera distance and scale from two
  points `map.project` places (4 and 24 degrees east of centre), `place()` projects a point at a
  height and hides it when the Earth is in the way. Each satellite gets a thin line down to
  its ground point. Not possible on the flat map, where a dot marks the point beneath.
  A click on an elevated satellite is found through the layer's `hit(point)`.
- **What it can see:** the horizon circle (`acos(R / (R + h))`) of the selected satellite, its
  width and share of the Earth in the card, and "Look down from it", which centres the map
  beneath the satellite and follows it until the map is dragged. The card says this is
  geometry and the map, not a camera feed: nobody publishes where on-board cameras point.
- watched.earth linked from every satellite card (it shows which satellites passed over a
  place and their pictures; no deep link by satellite found).
- Dots: radius 2 px (ISS 5).
- New optional layer hooks used by `main.js`: `select(id)`, `hit(point)`, `act(name, map)`
  (for `data-act` buttons in a card), `shape(map)` (called after a flat/globe switch).

### 2026-11-14, after his first real lookup run

- **Blank map after a pull (his Safari):** the server sent script files with no cache rule, so
  Safari reused an old `space.js` beside a new `main.js` and the import failed. Not reproducible
  in Chromium; diagnosis by reasoning, fix by design: pages now point at `/s/<server start
  time>/...` (see `VERSION`, `Forever`, `page()` in `web.py`), pages are `no-store`, and module
  imports are relative. Never import with an absolute `/static/...` path again.
- **Owner on the lookup:** "looks alright, but can be done much deeper and better, and why aren't
  we using good Kali toolkits?" His first run (448 of 690 sites passed the checker test on his
  network) found 10 profiles for his username. He offered to build it himself; not needed.
- **Kali tools wired in** (`lookup/tools.py`): Maigret, Sherlock, Holehe and theHarvester run
  unchanged as separate programs via `uvx` (downloaded on first use into uv's tool cache; GPL
  tools are executed, never copied). Plus built-in checks: RDAP and crt.sh for domains,
  `phonenumbers` (new dependency, offline) for phones, GitHub's public API for an account
  (profile, emails in recent public commits), a DuckDuckGo search for a full name.
  theHarvester comes from its GitHub repo (`uvx --from git+https://github.com/laramies/theHarvester`):
  the PyPI package of that name has no program in it. Only key-less sources are passed with `-b`.
- The scan sheet now has a checkbox per check and two options: Maigret all 3,000 sites, and
  Holehe password-reset probing (off by default: can send reset emails).
- The graph joins findings of the same page from several tools into one dot (larger = found by
  more tools) and the card lists "Found by". Maigret's extracted profile details (name, picture,
  links, dates) show in the card; usernames it discovers and follows are marked as such.
- Tested from the sandbox with public test identifiers only: Maigret 106 profiles, Sherlock 84,
  built-in 93, crt.sh 77 hosts, RDAP, phone and name search worked. **Not verified here:**
  theHarvester results (all its sources fail without direct internet in the sandbox), Holehe in
  the full scan (116 of 117 sites rate-limited the sandbox on the second run; the first run
  found accounts), GitHub account (hourly limit of the shared address used up).
- Known weakness: with several hundred findings the graph labels are too small to read without
  zooming. A list beside the graph is the likely next step; ask him.
- Not built: GHunt (needs his Google session cookies), PhoneInfoga (a Go program, not on PyPI),
  SpiderFoot (dormant since 2023), Amass/subfinder (Go), other subjects with consent records.

### 2026-11-14, his review of satellites and lookup (decisions pending his answers)

His points:
- Satellites: at full zoom-out the height drawing collapsed into one clump (my camera estimate
  from two close points breaks when the globe is small; widened to 20 and 60 degrees as a
  stopgap). He wants real 3D positions, the orbit path through the satellite and not along
  the ground, "look down" from the satellite's actual point in space, orbit types (LEO, GEO,
  others) shown with visual cues on the map and not only as text, a glow on the area a
  satellite looks over, and generally "more stylized systems", it is "bland".
  Mock-ups of four styles (orrery, spotlight, look down, height ladder) on a real snapshot:
  https://claude.ai/artifact/2hMjiJ2kLYCYip8Xt8tX8x (source `docs/satellite-views.mock.html`).
  Orbit classes there: LEO green, MEO amber, GEO blue. Real 3D means a separate space view
  (three.js or own WebGL), because MapLibre only draws on the surface. Waiting for his pick.
- Lookup: dragging the graph selected text (fixed). His own results are "names and links, some
  of which do not open": wants enrichment and depth. He wants lookup as part of the map for
  public figures (heads of state: events, travel history, offices held, companies).
- He referred to the "God's Eye" of the film Furious 7. Told him plainly: that is live tracking
  of a person through cameras and phones; no public data does it and I will not build tracking
  of people's whereabouts. What is possible: deep profiles from public records.
- Asked how hard cameras on the globe are: moderate. Windy's webcam API (free key) and public
  traffic cameras are fine; unsecured private cameras (Insecam-style) are not.

### 2026-11-14, his decisions after the mock-ups, and what was built

His answers:
- Satellites: **spotlight and look-down**, built **into the existing globe**, keeping its look
  ("the globe right now is beautiful"; do not restyle it like the mock-ups). **Flat map: dots
  only.** Orbit types must be visible on the map, not only in the card.
- Public figures: **all three groups, deep and clear** (heads of state and government,
  politicians in office, business leaders) **plus anyone he searches for**, and the search
  must not lower the quality of the first three.
- His own footprint: verify and read every hit, a timeline, more tools, and "a full god's eye
  like FF7 profile, in the whole spy feel, not the design but the content": a dossier.

Built (satellites, `space.js`):
- **Exact 3D on the globe.** An invisible MapLibre custom layer (`ww-sat-3d`) hands us
  `args.defaultProjectionData.mainMatrix` every frame; `map.transform.getMatrixForModel(lngLat,
  metres)` places a point at a height. Checked against `map.project`: 0 px difference at zoom
  0.8, 1.9 and 4. Occlusion by the Earth is plain geometry, with the camera distance taken
  from the engine's depth value at the ground and one radius up (`camera()`). This replaced
  the two-point estimate that clumped when zoomed out. Do not go back to estimating.
- Orbit ring in space through the satellite (ISS always, plus the selected one), no ground
  tracks any more; spotlight = lit horizon patch plus a cone (cone only when seen from the
  side); colours by orbit class (LEO green, MEO amber, GEO blue, HEO pink) with a legend on
  the map; `orbit()` gives the standard names for the card.
- **Look down from it** puts the map camera at the satellite's point (zoom solved from the
  camera height), follows it, and restores the previous view on leaving. `minZoom` is 0.3
  normally and -2 while riding a satellite.
- Satellite families fetched: visual, stations, gps-ops, galileo, geo (802 in total), one
  CelesTrak request each, 2.5 s apart, every 2 h; a family that fails keeps its last data.

### Profiles and dossier: plan proposed 2026-11-14, awaiting his go

Research from the sandbox (2026-11-14):
- **Wikidata SPARQL** answers but slowly: all current heads of state and government of
  sovereign states in 29 s (362 people, 425 rows; one person can head several states), one
  person's offices, parties, memberships, education, family and awards in 14 s (offices come
  with start and end dates). Everything must be fetched in the background and cached.
- **LittleSis API** (`littlesis.org/api/entities/search`) answers without a key; CC BY-SA 4.0;
  relationships between people, companies and donors, strongest for the United States.
- **OpenSanctions** publishes a politically-exposed-persons data set for download
  (`data.opensanctions.org/datasets/latest/peps/`; the index redirected and was not read:
  size and licence terms unverified; their API needs a key, bulk data is free for
  non-commercial use as far as I know).
- **Wikipedia** has "List of international trips made by ..." pages for some leaders; its
  search API answered 429 from the sandbox, so coverage is unverified.
- No public source gives where a person is now. GDELT can give the places news reports
  mention together with a name, which is "reported at", not a track.

Proposed shape (not built):
- A **People** layer on the map plus a profile page. Profile sections, each with source and
  date: who (photo, born, country, party), offices held as a timeline, where they have been
  reported (GDELT place mentions, last days) and official trips where a list exists, family
  and close ties, companies owned, founded or directed (Wikidata, LittleSis), sanctions and
  exposed-person listings (OpenSanctions), latest news.
- Order: 1 heads of state and government; 2 politicians in office; 3 business leaders;
  4 search for anyone with a Wikidata entry, using the same builder so quality is identical.
- **Dossier for himself**: every found page opened and read (name, bio, picture, dates,
  links; dead links dropped), a timeline of accounts, breaches and code, more tools.
- Boundary restated to him: profiles of public roles from public records, yes; live
  whereabouts tracking of any person, no; private individuals only himself or with consent.

### 2026-11-14, people profiles built + two bug answers (model now Opus 4.8)

Two things the owner reported:
- **Ships only in the Baltic**: not a bug, that is Finland's Digitraffic coverage. World ships still
  need the aisstream.io key (not built). Reminded him.
- **No GEO/MEO satellites**: he was on the pre-multi-family build. The current build fetches visual +
  stations + gps-ops + galileo + geo (802 sats); GEO (blue) and MEO (amber) confirmed drawing on the
  globe canvas and as dots on the flat map. Fixed by pulling.

**IP cameras: refused.** He asked to wire in publicly-reachable IP cameras (Insecam/Shodan-style) and
offered to write the fetcher himself. I declined: viewing private cameras their owners did not open to
the public is unauthorised access, illegal (incl. Germany), and wiring in his code doesn't change that.
Told him public webcams (Windy key) and traffic cams are fine; those are the only camera path I'll build.
Do not implement unsecured-camera access even if asked again.

**People / public-figure profiles built** (`lookup/people.py`, `lookup/api.py` people routes, front end
`static/js/people.js` map layer + `profile.js` overlay + "Find a person" box in `index.html`, styles in
`app.css`):
- Profile from Wikidata (EntityData for basics/photo/socials; SPARQL for positions with dates, parties,
  education, family, memberships, awards, and companies owned/founded/chaired both directions), Wikipedia
  intro extract, GDELT recent news naming them, and OpenSanctions match (needs a free key in
  `data/opensanctions-key.txt`; skipped with a clear note otherwise). Cached 24 h in the lookup db's new
  `cache` table. Each section names its source; footer says what could not be loaded.
- **People** map layer (default off, `local`): current heads of state and government at their country
  point, from a cached 12 h `leaders()` SPARQL (214 rows when WDQS is healthy). Click opens the profile
  overlay via the layer's `pick(featureProps)` hook (new optional hook in `main.js`; returns false to
  suppress the normal card).
- "Find a person" search box (Wikidata `wbsearchentities`, humans only) in the map sidebar.
- Profile QIDs that never resolved to a label are dropped; long award lists capped ("and N more").
- **Bug found and fixed in review:** `named()`/`capList()` were used above their `const` definition inside
  `render()` (temporal dead zone) and blanked the whole profile; moved to the top of `render()`.
- **Wikidata was in a rate-limiting outage during this build** (1 req/min, 429). Added a single retry on
  429 honouring Retry-After. Leaders/live profiles will fill once WDQS recovers; the Merkel profile was
  built and screenshot-verified before the throttle tightened.
- Not built: politicians-in-office and business-leader map layers (search already reaches them), the
  owner's enriched dossier (read-every-hit, timeline, more tools), cameras.

### 2026-11-14, fixes from his review, ships worldwide, and the dossier (model now Opus 5.5)

His review: wire the ships; the side-on spotlight "cuts through the globe"; can't zoom out far enough in
3D; People chip empty; add the OpenSanctions key; build the enriched dossier ("a good base for the
politicians / business leaders map").

- **People chip empty:** the combined leaders query timed out on Wikidata. Now two small queries (heads of
  state P35, heads of government P6), each ~1-2 s, merged; 392 leaders. A failed refresh falls back to a
  cached list up to 30 days old and says so; the front end retries every 30 s while empty.
- **Spotlight:** the beam was one flat triangle on the canvas, so it painted over the Earth. Now the beam
  and the lit patch are meshes of small quads in 3D (`mesh()` in `space.js`), each drawn only where all its
  corners pass the same occlusion test as satellites, so the Earth hides what is behind it. Costs ~12 %
  frame time in software GL in the sandbox (149 -> 167 ms); unmeasured on his GPU.
- **Zoom:** `setGlobe()` sets `minZoom` -2 on the globe (the GEO ring fits), 0.3 on the flat map.
- **Ships worldwide** (`ais.py`): aisstream.io websocket, one world subscription, kept in memory only
  (lists not dicts, 30 min expiry, 60,000 cap), merged with Digitraffic at request time in `web.py`'s data
  route so it never hits the disk. Key in `data/aisstream-key.txt`. A wrong key is reported as such (the
  service accepts the connection then drops it silently; we treat a drop within 15 s with no messages as
  "key probably wrong"). Feeds card shows `ships_world`: grey "not set up" without a key. **Not tested with a
  real key** (none in the sandbox); parser tested on the documented message shapes. Memory with a full
  world stream is unmeasured; watch it on the M1.
- **OpenSanctions:** code reads `data/opensanctions-key.txt` (header `Authorization: ApiKey ...`); README
  lists where to register. Not tested with a real key.
- **Dossier** (`lookup/enrich.py`, `static/js/dossier.js`, Dossier / Graph tabs on `/lookup`):
  - Scan option "Open every page found" (on by default) and a "Read the pages" button. Each found page is
    fetched like a browser would (8 at a time, never two at once per site), and judged live / dead /
    unchecked with the reason (404/410, redirect to the front page, "not found" in the title, 403/429
    refusals and login walls count as unchecked, not dead). Title, description, profile picture and
    schema.org Person data are kept. Then a second pass asks the Internet Archive for the oldest copy of
    each live page (3 at a time; gives up after 6 failures in a row and says so). Stored in table `pages`.
  - The dossier shows: identifiers and counts; "As the internet shows you" (names, pictures, places, work,
    self-descriptions, links between profiles, each with the pages that show it); account cards; dead links
    left out with reasons; exposure (breaches table, malware, keys, address in code); domains; a timeline
    of dated facts only. Clicking a card opens the detail panel with "Not me".
  - Lessons: JSON-LD describing the WebSite/Organization was being read as the person's name; only
    `Person` / `ProfilePage` entities count now. A page's og:image is kept as the person's picture only
    when it looks like an avatar (path words or the username in it); otherwise it is the site's banner.
  - Sandbox test (public test identifiers only, wiped after): 196 pages read in 50 s, 138-140 live, 12-15
    unchecked, 2 dead dropped. Internet Archive never answered from the sandbox, so archive dates and that
    part of the timeline are **untested**. Soft-404 pages (200 with "not found" only in the body) can still
    pass as live.
- Not built yet: politician and business-leader map layers on top of this dossier design, GHunt /
  PhoneInfoga / Amass (need his Google cookies or separate installs).

### 2026-11-14, "Narendra Modi showed nothing" (fixed)

- People search hit Wikidata's 429 throttle: the human filter ran as a SPARQL query. Now it uses the
  `wbgetentities` API (lighter, separate limit), results are cached in the lookup db, and a 429 is shown as
  "Wikidata is limiting requests, try again in a minute" instead of an empty list.
- Lookup for a public figure's name: the username sweep only finds accounts, which is not what he wanted.
  The dossier now opens with a "Public figure record" card for any name identifier that matches a Wikidata
  person; clicking it opens the full profile. "Open every page found" is on by default in the scan sheet.
- Graph tab did not show (an SVG has no `.hidden` property; uses the attribute now). The profile overlay's
  `#profile` display rule beat `[hidden]` and left an invisible layer over the page after closing: fixed.
- Profile header shows the top two offices, highest first, plus "and N more"; the full list is in the timeline.

### 2026-11-15, next round chosen (owner's picks)

Owner put the aisstream.io and OpenSanctions keys in `data/` on his Mac (not tested here). He picked, in order:
**denser news with pictures**, **protests and clashes** ("super super good, just make sure it is well done"),
**navy warnings**, **airspace closures worldwide** ("not just US"), then **sanctioned ships and aircraft** and
**breaking-news spikes**. **Business leaders dropped** ("isn't that cool"); ministers not asked for either.
Not picked (keep as ideas): Wikipedia most-read places, radiation (BfS ODL, 1,672 stations, works), German
Foreign Office travel warnings (works), city lights (GIBS `VIIRS_NOAA20_DayNightBand_At_Sensor_Radiance` works),
circling aircraft, WHO outbreaks, tsunami/volcano, PeeringDB, RIPE BGP.

Research, measured from the sandbox 2026-11-15:
- **News sparse in India** because the map shows one 15-minute GKG file (~40 India articles per file; India is
  the 3rd most pinned country). Decision: **6-hour rolling window** (no extra downloads; every file is already
  fetched). 88 % of GKG rows carry the outlet's own share image (column 18, V2.1SHARINGIMAGE). Images go through
  our server so outlets don't see his browser. The translated series carries ~65 languages incl. Hindi, Gujarati,
  Telugu: take all, translate lazily when a card opens instead of everything up front.
- GKG files have holes: in one run 3 of 9 recent slots were 404 while older ones existed. Walk-back handles it.
- **Protests/clashes** from GDELT Events 2.0 export (~30-55 KB zip per 15 min). In 9 files: root codes 19 fight 343,
  18 assault 60, 14 protest 46, 20 mass violence 1; NumSources 1 for 444 of 450. Decision: IsRootEvent only,
  city-level ActionGeo (types 3/4) only, grouped by place + day + type, **single-outlet groups hidden behind a toggle**
  (owner's pick), sports URLs dropped, card says machine-coded and unverified.
- **Navy warnings:** NGA MSI (`msi.nga.mil/api/publications/broadcast-warn`) answered 503 "unavailable" from the
  sandbox, untested; UKHO NAVAREA I page (`msi.admiralty.co.uk/RadioNavigationalWarnings`) works (HTML). Draw areas
  only where coordinates parse exactly.
- **Airspace:** FAA NOTAM search 403 from here; ICAO/autorouter need accounts. Works: EASA conflict-zone bulletins
  (CZIB page, ~20 in force), FAA prohibitions page, FAA TFR list (56), VATSpy FIR boundaries (CC BY-SA 4.0,
  approximate, community-drawn: label so).

### Built 2026-11-15 (waiting for review)

- **News, 6 hours, all languages, pictures** (`news.py`, `static/js/news.js`): every GKG file of the last 6 hours is
  kept as compact rows (place, lat, lon, outlet, title, url, lang, image) and counted per place. Each slot's rows are
  written once to `data/gdelt/` so a restart does not refill. Map payload carries 8 articles per place; a card asks
  `/api/news/place?p=` for all of them, which also machine-translates their headlines then (cached 90 days). The
  translated feed translates only the leading headline of places with 3+ outlets up front. Pictures go through
  `/api/news/image?u=`, which fetches only addresses present in the current news data (not an open proxy).
  Measured: 6,657 English + 6,868 translated articles in the window, 3,277 places, 589 list rows; Mumbai 56 outlets.
  Peak memory 141 MB (GKG files are read line by line now; reading them whole had pushed the peak to 254 MB).
- **Google Translate blocked the sandbox** after the first burst (302 to its "unusual traffic" page). `translate.py`
  now pauses 30 minutes after a 302/429/503 and the feed note says so. On his Mac it worked before; untested at
  this volume there.
- **Protests and clashes** (`unrest.py`, `static/js/unrest.js`, chips "Protests and clashes" and "Unrest, one
  outlet" (off by default)): 24 h of Events + Mentions files, cached per slot like news. Filters: IsRootEvent, city
  level, roots 14/18/19/20, sports addresses, and `plausible()`: the vague codes (190, 191, 192, 180, 200) need an
  armed CAMEO actor type (MIL, REB, INS, UAF, SEP, SPY) or a known group, or two different countries (not for 192);
  assault/abduction also accept police/criminal actors. On a real 24 h this cut 1,628 events to 896 and removed the
  examples that prompted it (a port suing over a tanker coded as military force in Liberia; "opposition attacks
  cabinet" in Adelaide; a Savoy blue plaque coded as occupation in London). Groups = place + category + UTC day;
  outlets = distinct sources over the event's own article and all later mentions. Protests are rings, violent kinds
  filled, letter P/R/A/C/M. Headlines/pictures borrowed from the news window when the same address is there; else
  words from the address, labelled. GDELT slot times are clamped to now (they are labels, can be ahead).
- **Navy warnings** (`navwarn.py`, `static/js/navwarn.js`): NGA broadcast warnings + UKHO NAVAREA I. Only activity
  kinds (rocket, missile, weapons, exercise, security, GNSS) by keywords; buoys and lights dropped. Circles from
  "WITHIN n MILES OF", polygons from "BOUND BY", otherwise points. **NGA still 503 from the sandbox (whole site),
  so the NGA parser is written from the documented field names and untested**; UKHO gives 1 activity warning now.
- **Airspace** (`airspace.py`, `static/js/airspace.js`): 16 active EASA CZIBs (detail pages read once per revision
  number for FIR codes, affected airspace and recommendations; level "avoid" when the advice says not to operate),
  21 FAA country entries (SFAR = prohibited, else notice), 44 US TFRs with exact shapes from each NOTAM's XML (cached
  per NOTAM). FIRs drawn from VATSpy, one shape per FIR in its strongest level, card lists every warning. Unmapped
  codes are kept in the data (e.g. OLBA, UKBU).

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
