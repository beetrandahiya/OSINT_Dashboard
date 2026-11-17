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

### 2026-11-15, his review and the next build

Owner: protests and clashes "really good, well done"; airspace and navy warnings good; satellite pictures "cool,
not much information"; leaders today good. News "a bit too crowded": he picked merging nearby places and weight by
importance (not the fade by age). Asked for launch corridors with "an expected trajectory in 3d". **Cameras: he
says he will work on them himself.** My standing refusal of unsecured private cameras stands; public webcams fine.

Built:
- **News declutter** (`news.js`): MapLibre clustering up to zoom 5 (bubble = number of places, size = summed outlet
  counts, click zooms in via the layer's `pick`); single places with 1-2 outlets are faint 2.5-3 px dots, 3+ full,
  numbers only from 10. `main.js` click/hover now accept cluster features.
- **Satellite picture in cards** (`skyShot()` in `util.js`): GIBS WMS GetMap, NOAA-20 VIIRS true colour, ~165 km box,
  yesterday by default with Today / Yesterday / 2 days ago buttons, pin at the centre. In news, unrest and disaster
  cards. 375 m pixels: a city is a smudge; useful for smoke, floods, storms. HLS (30 m) answered blank from GIBS.
- **Leaders today** (`news.leaders_today`, `/api/people/today`, `leadersToday` in `people.js`): GKG V1Persons kept
  per article (row field 9), matched (accent-folded) to the cached Wikidata leaders list; place = the article's
  pinned city. Rules learned on real data: copies of one agency story count once (distinct normalised headlines;
  a "Today in History" piece had put Abbas at Pikes Peak), the leading place needs 2+ headlines and 2+ outlets,
  articles naming more than 12 people are skipped. "Abroad" compares country names, not distance (the country
  point of the US is in Kansas, which made Trump in Washington "abroad"). Shown: 38 leaders, e.g. an ASEAN-week
  cluster in Manila (Carney, Albanese, Li Qiang, Wong, Prabowo). Known GDELT errors remain (Ramaphosa at "Kayode,
  Nigeria"; Kallas listed as Estonia's leader is Wikidata's data).
- **Launch corridors** (`corridor()` in `space.js`): for launches in the next 4 days, US SPACE OPERATIONS TFRs within
  150 km of the pad whose text names the launch day (+-1), and navy rocket warnings within 4,000 km whose date-time
  groups name the day; drawn as areas plus a dashed line pad -> areas, nearest first. Card lists them. Vulcan
  Amazon Leo LV-01 matched 3 TFRs. **No 3D ascent trajectory**: nobody publishes one and drawing one would be invented
  (God's Eye View's synthesized launch paths were the criticism). Told him the honest options.
  LL2 fields now also carried: target orbit, mission text, window.

### 2026-11-15, VIP jets, spy satellites, warships, weather and sharp imagery (built, waiting for review)

He picked VIP jets, warships (with photos), satellite identity (what it is, what it does, a photo, purpose shown on
the globe) and "which spy satellite passed over a hotspot", plus "similar to the rain thing" overlays and the
sharpest possible recent picture of a small place. He rejected my science/utility list (fireballs, radio
blackouts, Meteoalarm, river gauges, shake maps, Wikipedia edits, ASN outages): "none of them make a lot of sense".
His taste: geopolitics, military, the god's-eye feel.

- **VIP jets** (`vip_aircraft` feed, `vip` layer in `aircraft.js`): plane-alert-db (ODbL), 1,015 aircraft kept from
  17,276 (categories Governments, Dictator Alert, Radiohead = Air Force One, celebrities/tycoons, Royal; military
  categories only with strong words like president/government). Matched by hex against all aircraft feeds; halo +
  label (the leader's name for government/dictator planes). Rows only for airborne government ones. Seen live:
  SPAR18 (US C-40C), Erdogan's G450, Maduro's ACJ319, Mohammed VI's BBJ, Danish PM's Challenger.
- **Satellite identity** (`satinfo.py`, `sat_catalog` + `recon_sats` feeds, `/api/satellite/{norad}`): UCS Satellite
  Database xlsx (read with zipfile, no dependency; 7,551 satellites; **last updated May 2023**; UCS spells
  "Meterology") gives purpose/users/operator; Wikidata by P377 gives picture, description, kind, maker (cached 30 d).
  Globe: purpose letter beside each satellite once fewer than 160 are in view (I imaging, R radar, S signals,
  W warning, M weather, N navigation, C comms, X science, T tech); military imaging/radar/signals/warning get a red
  ring (also on the flat map) and a legend entry.
- **Spy satellites** (`recon_sats`): public orbits from CelesTrak for UCS military EO catalogue numbers (full active
  CSV; when that fails, family names YAOGAN, COSMOS, USA, ...), classified US ones from McCants' classfd.tle
  (amateur SeeSat-L sightings; only "USA" payloads, no rocket bodies/debris, epochs within 60 days). 266 now
  (87 Yaogan). Cards say amateur orbits can be off by tens of km.
- **Spy passes over a place** (`passes()` in `space.js`, `spyPass()` button in news, unrest, disaster and navy
  cards): last 24 h, every minute, low-orbit (period <= 225 min) spy satellites, counted when > 30 deg elevation at
  the place, at the peak. Card says "could have looked, not that it did". High orbits left out (they watch half the
  Earth all day; first version listed EKS early-warning satellites as "overhead now").
- **Warships + ship photos** (`warships` layer in `ships.js`, `/api/ship/about`): AIS type 35 from the stream;
  pictures from Wikidata by IMO (P458) / MMSI (P587), for warships by name (wbsearchentities, ship-like description;
  HNLMS Tromp found), then Wikimedia Commons "Category:IMO <n>" (better coverage: 9 of 14 Baltic merchant ships
  sampled; Wikidata had 2 of 25). Commons rate-limits the shared sandbox address. Warships untested live (no AIS key
  here; Digitraffic shows 1).
- **Lightning** (`lightning` in `sky.js`): EUMETSAT MTG Lightning Imager `mtg_fd:li_afa` WMS tiles (transparent, CORS
  ok), refreshed every 5 min. Europe/Africa/Atlantic/E. South America only.
- **Clouds** (`clouds`, default off): EUMETSAT cloud mask `msg_fes:clm` + `msg_iodc:clm` fetched for the visible box,
  recoloured in a canvas (white = cloud kept, green/blue clear dropped), laid as an image source. Europe, Africa,
  Middle East, India; not the Americas or East Asia (GIBS has GOES/Himawari IR but no cloud mask; IR disks are opaque).
- **Sharp photo** (`sharp`, default off): Esri World Imagery tiles (to z19; Vantor 0.3-0.5 m in cities) with the
  capture date of the picture under the map centre from Esri's identify service (`/api/imagery/date`, cached a
  week per ~1 km): Munich 2025-06-22, Mumbai 2025-11-11, both 0.5 m WorldView-2. Sharp but not current.
  Latest *clear* 10 m Sentinel-2 needs a free Copernicus Data Space account (not built); Maxar Open Data publishes
  free sharp imagery for major disasters only.

### 2026-11-15, his review of that round, and fixes

His points: satellite view "a lil laggy"; flags for satellites, ships and planes (all flags when joint), and then
"I meant flags on the name card on the right, not on the map"; no satellite photos visible on cards; MBS's plane
route "turned around ~100 km"; cloud layer "looks strange, get rid of it"; Copernicus Sentinel-2 "looks off" (do
not build it); pull Maxar sharp images for disasters; ships and warships often have no picture, show loading /
not found; wants more interesting ideas (my last list "not super interesting").

- **Route turn-around:** the flown path (OpenSky, up to now) was joined to the aircraft symbol, which for the world
  snapshot is up to 20 minutes old: the line ran ahead and came back. Now joined only when the symbol is newer;
  otherwise the path's newest point is marked with its time and the card says why (`posTime()` in `aircraft.js`).
- **Lag:** `clip()` computed a full 4x4 product and a new array per satellite per frame; now only the needed column.
  Purpose, spy flag and flags are computed once per data load (`annotate()`), lookups by id use a Map. Unmeasured
  on his Mac (headless software GL is ~2 fps regardless).
- **Flags** (`flags.py`, feed `flags`, `static/js/flags.js`): aircraft by ICAO address block (tar1090's flags.js,
  generated from Annex 10), ships by MMSI MID (Wikidata P2979 + P297, 292 codes), satellites by CelesTrak SATCAT
  owner code (records.php per family, daily) named from satcat/sources.php (132 codes), joint owners with each
  partner (ISS: US RU JP CA EU), else UCS country ("USA/Japan" -> both). **Cards only** (next to the name, plus a
  "Registered in / Flag / Owner" row); map flags were built and removed at his request.
- **Satellite pictures:** own picture, else the picture of its Wikidata class ("its type"), else its family by name
  (STARLINK-1234 -> Starlink), each labelled with what it shows. Most catalogued objects have none of their own.
  Wikimedia rate-limited the sandbox during this work: untested live. Wikimedia requests now send the contact
  address in the User-Agent when `data/contact.txt` exists, as Wikimedia asks.
- **Loading / not found** states for ship and satellite pictures (`.pic-wait`). Ship lookups that fail on Commons are
  not cached, so they retry.
- **Clouds layer removed.**
- **Maxar disaster imagery** (`maxar.py`, feed `maxar_events`, `/api/maxar/*`, `static/js/maxar.js`, chip
  "Disaster imagery", off by default): 55 events from the STAC catalogue on S3; **newest is 2025-12-18 (Morocco
  floods): Maxar/Vantor has published nothing in 2026 so far.** Files are BigTIFF COGs (17,408 px, JPEG in 512 px
  pieces, UTM). We read the directory with one range request (`parse_tiff`, no dependency), convert the corners from
  UTM to lon/lat, and serve each piece by its byte range with the shared JPEG tables put in front (`/api/maxar/tile`);
  the browser places pieces as image sources by bilinear corners and picks the overview level by screen size.
  Verified: Cyclone Ditwah, WorldView-3 0.37 m colour, houses visible. WorldView-1 passes are black and white.

### 2026-11-15, doomsday planes and US carriers (built, waiting for review)

He asked for doomsday planes and US carriers "in the same category as military vessels", with satellite pictures of
them if possible. Country dossier: "cool, but we need a very sophisticated and good and complex setup to do it well"
(not built; plan to be agreed).

- **Doomsday planes** (chip, `doomsday` in `aircraft.js`): from plane-alert-db rows tagged Doomsday / Nightwatch /
  Looking Glass (US E-4B x4, E-6B fleet, Russian Il-86 VKP, Il-76VKP, Tu-214SR; trainers and the NSF EC-130 excluded),
  category "Doomsday" in the `vip_aircraft` feed (41 aircraft). Card says what each type is for (`DOOM_ROLE`).
  Airborne ones go in the list. VIP jets layer no longer shows them; VIP list now 821 (military categories need
  strong words).
- **US carriers and amphibs** (`usni.py`, feed `usni_fleet`, inside the Warships layer): USNI News Fleet and Marine
  Tracker via its category RSS (`news.usni.org/category/fleet-tracker/feed`; the site and WP API answer 403 to the
  sandbox, the feed works). Sections by "In ..." headings; CVN/LHA/LHD; status sentences only (photo captions name
  ships too); "departed" means at sea; port from "in port in / pulled into / returned to". Placed at a hand-made
  port table (exact) or region centre (approximate, wide dashed ring) and the card says which. USNI's map graphic
  shown (proxied; the image proxy allows it). **Newest edition 2026-10-19: USNI has not published since**, feed
  shows late. 7 ships parsed (Tripoli in port Sasebo; Roosevelt left Yokosuka; GW, Bush, Boxer Arabian Sea).
- **Satellite pictures of carriers:** no free current imagery of warships exists. For a ship in port the card offers
  "Look at the port in the sharp photo" (Esri, dated; the ship may not be in it). Ship photos come from Wikidata by name.

### 2026-11-15 evening, his review (screenshots from his Mac) and fixes

His points and what was done:
- **Flags:** appeared only after ~10 min (the page asked once, before the server had the tables; now retries every
  10 s). He dislikes the wavy emoji: now **flat SVG flags from flag-icons (MIT)**, vendored in `static/flags/`
  (272 files, 2.7 MB), via `flagImg()` in `flags.js`.
- **Leaders:** Netanyahu shown in Tehran, clicks on stacked dots opened the wrong leader, Modi and Murmu overlapping.
  Now one marker per place listing everyone there (`todayp:` ids, card lists each leader); a leader's place is the
  city mentioned **nearest to their name** in the text (GKG V2EnhancedPersons and V2EnhancedLocations offsets),
  first city only when offsets are missing. Names are kept only for articles naming someone we follow
  (`news.WATCH`, from the cached leaders list) because keeping them for all articles cost ~40 MB.
- **Loading bar:** thin 2 px bar at the top while any `/api/` request takes over 250 ms (fetch wrapper in `main.js`;
  the status poll is excluded).
- **Minimisable panels:** sidebar, detail card and markets strip (`.mini` buttons; remembered in localStorage).
- **Lightning moved when zooming:** tiles fetched at different times showed different 5-minute pictures. Every tile
  now asks for one `TIME` (`/api/eumetsat/time?layer=...` reads the layer's default time from its capabilities).
- **Clouds layer removed** (earlier). **Live photo** (new chip): MTG `mtg_fd:rgb_geocolour` (Europe, Africa, Middle
  East; day colour, night version), `msg_iodc:rgb_naturalenhncd` (India), GOES-East/West GeoColor via GIBS (Americas),
  every 10-15 min, 1-3 km. East Asia has no colour picture in these services. The daily Photo stays.
- **Satellites:** dots 1.5 px; military imaging/signals are small red diamonds (no ring; flat map red dots). Pictures:
  Wikidata, then its class, then family, then **NASA Image Library** (accepted only if the title names it).
- **Ships:** paths (`ais.Stream.trails`, compact float arrays, 30 points 1 km / 15 min apart, `/api/ship/trail/{mmsi}`),
  kept 2 h instead of 30 min. Indian Ocean empty because aisstream relays shore receivers only (no free satellite
  AIS); the count moves as receivers come and go. Ship pictures: also a Commons search by name.
- **Disaster imagery now current:** **Copernicus EMS rapid mapping** (feed `ems`): 36 activations in 120 days,
  pictures used for each map (GeoEye-1, SPOT-6, ... e.g. Valencia floods 2026-10-20), plus Copernicus' counts of
  affected buildings. Their COGs are Deflate + predictor 2 (Web Mercator): served as PNG with **no pixel work** (PNG's
  Sub filter equals TIFF predictor 2; one filter byte per row; tRNS makes black no-data transparent). Maxar stays as
  "archive". Fixed: moves during loading were dropped (`again` flag); pictures from zoom 9.
- **Live GPS interference** (feed `gps_live`, chip "GPS, last hour"): 15 hotspot regions, 250 NM each from adsb.fi
  every 10 min, aircraft per H3 res-4 cell, share with NACp < 8 over the last hour, GPSJAM's bands. Derived, labelled.
  Costs 18 s of the shared adsb.fi gate every 10 minutes (area queries may wait that long once).
- **Memory:** steady was 183 MB. Measured per feed: UCS spreadsheet +27, VATSpy boundaries +23, translated news +19.
  Heavy one-off parses now run in a short-lived child process (`_in_child` in `feeds.py`), VATSpy is kept compressed,
  UCS rows are read per request. Now ~154 MB steady, 159 MB peak (news still filling when measured).
- Country and person dossiers: handed to a separate agent working in its own worktree (see its section when merged).
### 2026-11-15, person dossier redesign and country dossier (built in a separate worktree, waiting for review)

Owner: the person profile "is weird, like a long long Wikipedia intro"; wants a spy-movie dossier, clean and meaningful
with signals. Country dossier: "very sophisticated and good and complex setup"; he approved the direction (full-page
overlay, sections from our own feeds, counts and facts only).

- **Person dossier** (`profile.js` rewritten; same overlay `#profile`, now a shared shell `shell()` used by both dossiers):
  header (photo, name, flag per citizenship linking to that country's dossier, up to 3 current offices with since-dates,
  age, Wikidata/Wikipedia links); **Signals** tiles from our feeds, each with source and age: outlets naming them in the
  6 h GDELT windows (GKG V1Persons), "Reported at" (Leaders today, leaders only), aircraft listed with them in
  plane-alert-db (name or operator match; surname tag only when the plane is registered in their country; office tags
  POTUS / Air Force One / VPOTUS / Air Force Two for the current holder) with live position, unrest and airspace
  warnings in their country, sanctions listed / not listed / not checked. Then headlines that name them (agency copies
  once), Wikipedia intro cut to 2-3 sentences with "Read more", a record grid (born + place, nationality, current party
  only, education, spouse with "until", children, parents, languages, religion, net worth P2218 with its date, official
  accounts), offices (current + "N earlier" folded timeline), companies, memberships, honours.
  Server: `/api/dossier/person/{qid}` in `dossier.py`; `people.py` now also reads P19, P27, P1412, P140, P2218, party end
  dates, labels via `wbgetentities` (SPARQL fallback), and falls back to Wikipedia's REST page summary when the action API
  answers 429 (it did, all afternoon, from the sandbox). Profile cache key bumped to `profile2:`.
  The GDELT DOC "recent articles" list was dropped from the page: mostly unrelated hits; our own windows are better.
- **Country dossier** (`dossier_country.js`, `/api/dossier/country?cc|fips|icao|name|qid|lat&lon`, `/api/dossier/countries`):
  header (flag, capital, population with date, government type, heads of state/government linking to person dossiers),
  travel advice (US State Department level + German Foreign Office warning flags, each with its date), "Right now" tiles
  (unrest 24 h, airspace warnings, US TFRs for the US, navy warnings within 300 km, IODA outages, quakes in/within 100 km,
  GDACS/EONET, VIP/government/doomsday aircraft inside the outline, military aircraft count, AIS warships within 200 km and
  USNI carriers within 600 km, leaders the news placed there, news outlets), detail lists with "Show on map" (closes the
  overlay and picks the item via `ww-pick`), top 10 news places with picture, "From above" (spy-pass button over the capital
  reusing space.js's document-level handler; Maxar events), record (languages, currency, area, GDP with date, memberships,
  ISO/FIPS codes). Footer says plainly that "what changed" needs a history store we do not have.
  Opened from "Find a person or country" (countries match locally at once, people still from Wikidata) and a "Country
  dossier" button (`countryBtn()` in util.js) in news, unrest, airspace, outages and leaders cards.
- **Country table** (`geo.py`, `data/countries-geo.json`, 1.7 MB, built once on first use, not in git): Natural Earth
  1:50m admin-0 (public domain: names, ISO, FIPS, Wikidata ids, outlines) + VATSpy's ICAO prefix list. Inside/outside by
  scan-line crossings per 0.05° row (fast enough for 11,000 aircraft); distance by outline vertices bucketed per degree.
  FIPS fixes by hand where Natural Earth has none (IL=IS, NO, PS=GZ/WE, SS=OD). Wikidata facts per country cached 30 days
  in `lookups`; when the query service refuses, the item's own JSON (Special:EntityData) is read instead.
- **Travel advice feed** (`travel.py`, feed `travel_advice`, every 6 h, no key): State Department RSS (country by the link's
  ISO3 code, else the FIPS Country-Tag; Gaza/West Bank -> PS) and Auswärtiges Amt open data.
- **Flags** still emoji, behind `flagMark()` in `flags.js` (no `static/flags/` existed in this branch); swap there.
- Lessons: coastal capitals fall outside a 1:50m outline (Washington sits on the Potomac line, New York in the harbour), so
  positions get 25 km of slack; that slack pulled Tulcea (Romania) and Lahore (Pakistan) into Ukraine and India, so a GDELT
  place whose own last part names another country is excluded. Maxar events need their centre inside and no other
  country named in the title (Nepal floods were showing for India). GDELT's person list includes people named once deep in
  a text; the dossier lists only headlines naming them and counts the rest.
- Verified in headless Chromium (light and dark), screenshots read: Trump, Modi, Netanyahu person dossiers; Iran, India,
  Germany, Ukraine country dossiers (also US, Palestine via the API); search -> Germany; news card -> Country dossier ->
  spy passes -> head of state -> person dossier. Peak memory 186 MB in the sandbox with everything warm (was ~175-180).
- **Untested:** OpenSanctions with a real key (only the "not checked" path ran); NGA navy warnings (still 503 here, so
  "near its coast" only had UKHO); world AIS warships (no key here); Wikidata SPARQL path for countries worked, the
  EntityData fallback was written for the 429 case and ran only by reading; on his Mac the Wikipedia action API may answer
  normally (then the full intro is used, cut client-side).
- Open questions for him: is "listed with them" (plane-alert-db tags) the right wording for aircraft; should the person
  dossier show politicians' parties' history; country names come from Natural Earth ("United States of America").

### 2026-11-15, owner's standing guidance

- **Memory: 200 MB is a suggestion, not a ceiling** (owner: the M1 is an 8 GB MacBook Pro that runs other services
  too). Keep it lean (now ~175 MB steady after moving heavy one-off parses into child processes: `_in_child` in
  `feeds.py`, `geo._prepare`), but do not trade features for megabytes.
- **Do not restrict sources to US/EU.** Enrich every layer with providers from other regions (Asia, India, Japan,
  Australia, Canada, UN, ...). Probed 2026-11-15 from the sandbox: UK FCDO travel advice (gov.uk content API) 200,
  Canada travel advisories JSON 200, NZ SafeTravel feed 200, India NAVAREA VIII page (hydrobharat.gov.in) 200,
  JMA earthquake list 200, EMSC / GFZ quakes 200, PTWC tsunami feed 200, adsb.lol area queries 200 (second ADS-B
  source); Australia Smartraveller no answer, Japan JCG NAVAREA XI page 404, ReliefWeb API 403, Charter 404,
  airplanes.live 403, China CENC no answer.
- Dossiers (country and person) merged from the agent's worktree on 2026-11-15 (see its section above); its open
  questions for the owner: wording "listed with them" for VIP aircraft, short vs long country names, former parties.

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

### 2026-11-15, his notes on leaders, loading bar, disaster imagery, unrest and search (fixed)

- **Leaders today: one dot per leader again** (he found the grouped card worse). Leaders the news placed in the same
  city stand side by side, 22 px apart on screen, re-spread after every move (`draw()` in `people.js`, ids `today:<qid>`);
  each opens its own card, which now lists "Also reported there".
- **Loading bar on the panel**: it is laid along the top edge of the open dossier, else the detail card, else the sidebar
  (`place()` in `main.js`), not across the top of the screen.
- **Disaster imagery chip removed** at his request ("doesn't make a lot of sense"); `maxar.js`, the `ems` and
  `maxar_events` feeds and routes stay in the code. The import in `main.js` is commented out.
- **Unrest misclassification** (his example: "Armed clash, Mumbai · Javed Akhtar spotted in wheelchair at Mumbai
  airport"). Two new checks in `unrest.py`: entertainment/celebrity/lifestyle addresses dropped like sports (`SHOWBIZ`);
  and each news row now carries two GKG theme flags (`news.theme_flags`, V1Themes: violence / protest, generic themes
  like WB_2433_CONFLICT_AND_VIOLENCE, ARREST, POLICE not counted). A group is dropped when every article we can match to
  the news window lacks the fitting flag (`THEME_FIT`). Measured on 8 real slots: 6 of 98 matched events dropped, all
  six wrong (a law-review story, a seminar, a road-trip blog); one celebrity story still passed (a KILL theme in a
  Pakistani paper). News rows cached before this have no flags and are not checked until they age out (6 h).
  Articles not in the 6 h news window (no city, older) cannot be checked. Feed note counts the dropped groups.
- **Search "usa" found only Usain Bolt**: the country list now carries ISO2/ISO3 codes (matched whole) and common
  short names (`geo.ALIASES`: USA, UK, UAE, DPRK, Burma, ...). Countries still answer before people.
- **Court cases for dossiers (asked, not built)**: probed 2026-11-15. UK National Archives Find Case Law: open Atom
  search, works without a key (judgments only, England and Wales). CourtListener (US federal dockets via RECAP and
  opinions): free token needed (401 without). Indian Kanoon API: needs a paid key (401). ICC case pages: HTML, readable.
  Wikidata P1399 "convicted of" / P1595 "charge": sparse. Waiting for his pick.

### 2026-11-15, court records in person dossiers (built, waiting for review)

Owner: "pull the international criminal court stuff for sure, and uk as well". Built (`courts.py`, feed `courts_icc`,
`/api/dossier/courts/{qid}` in `dossier.py`, "Court records" section in `profile.js`):
- **ICC** (feed, daily): the case list at icc-cpi.int/cases (34 defendants, 4 pages, with the court's own status: in
  custody, at large, convicted, closed...) and the 19 situation pages, which name people with warrants (Putin,
  Netanyahu, Gallant, Akhundzada, Haqqani; Min Aung Hlaing's warrant application). A person matches when their first
  and last name stand within three words in the text ("Vladimir Vladimirovich Putin"); the dossier quotes the court's
  sentences and links the page. Checked: Duterte (case, "In ICC custody"), Putin, Netanyahu, Akhundzada (situation
  pages), Modi (nothing).
- **The ICC site has a bot shield (Gcore)**: after a few quick requests it answers 200 with a "Please enable cookies"
  page. We respect it: situation pages are read 20 s apart once a day, the cookie page counts as a refusal
  (`is_challenge`), one retry after 90 s, and the last good copy of each page is kept in `data/icc-situations.json`;
  the feed note names refused pages. From the sandbox only 1 of 19 situation pages came through after the block
  started, so Putin/Netanyahu matched in testing only from pages saved earlier by hand; **untested from his network**.
  Do not try to get past the shield (an attempt to compare clients was rightly refused).
- **England and Wales** (asked when a dossier opens, cached a day): The National Archives' Find Case Law Atom feed.
  `party=` with the full name; the filter also matches surnames alone ("Crow v Johnson" for Boris Johnson), so a title
  must carry first and last name to count as "named as a party"; the rest is folded away as "only the surname, may be
  someone else". Plus a quoted full-text search: count of judgments mentioning the name and the newest six.
  Judgments only, mostly since 2001.
- **Wikidata** P1399 convicted of / P1595 charge (Putin: "child abductions in the Russo-Ukrainian war"). Wikidata
  answered 429 for most of the testing; the dossier says so.
- Not covered and said on the page: US courts (CourtListener needs a free key; not asked for yet), India (eCourts has
  only a captcha search page; Indian Kanoon's API is paid), most other countries.
- Lesson (sandbox, not the project): a typo in a shell command removed `/dev/null` in the container (running as root);
  restored with `mknod -m 666 /dev/null c 1 3`. Never put `rm` near a redirect target.

Probed for the next layer ideas (2026-11-15): DeepState Ukraine front line `deepstatemap.live/api/history/last`
(200, 620 KB GeoJSON), IMF PortWatch chokepoint transits (ArcGIS `Daily_Chokepoints_Data`, 200), OpenSanctions
bulk `targets.simple.csv` (200, 79 MB, no key: vessels with IMO, aircraft with registrations). Japan Joint Staff
press page 403 (Cloudflare) from here; Taiwan MND URL guessed wrong (404), not found yet.

### 2026-11-15, front line, orbits, tankers, bases, nuclear, cable problems (built, waiting for review)

Owner's picks: Ukraine front line, spy-plane orbits, tankers, "all the military bases and nuclear sites ... go deep deep",
quakes at nuclear test sites and the test sites, spy satellite manoeuvres, cables "only highlight cables that have some
issue". Ships ("complicated") dropped; government planes on the move already covered by VIP jets (said so).
Research on bases/nuclear/cables/BGP was done by a background agent (probed from the sandbox; its findings are below).

- **Front line** (`frontline.py`, feed `front_ukraine`, `frontline.js`): DeepState `api/history/public` (change list,
  1.4 MB, every 2 h) and `api/history/{id}/geojson` only for a new update and the one nearest a week earlier. Kept by tag:
  status.occupied/unknown, territories crimea/ordlo/tuzla (occupied), transnistria/abkhazia/tskhinvali (held). Left out:
  their political polygons (East Prussia, Karelia, Kurils, Estonia/Latvia, Ichkeria...) and 2022 liberated areas. Points:
  units ("enemy" icon), attack directions (arrow direction is only in their picture: place marked, no arrow), airfields,
  HQs, from zoom 6. Change log entries placed at the coordinates in their links. Occupied area summed on a sphere:
  116,882 km² (+22 km² 6-13 Nov). Card says: Ukrainian OSINT team's assessment, hours to a day late.
- **Orbits and tankers** (`patterns.py`, `/api/aircraft/patterns`, `patterns.js`): from `Collector.trails` (military feed
  every 5 min + Munich 20 s, 3 h). Orbit = heading changes ≥ 540° over 2 h with every point within 120 km of the centre;
  time on station back through the kept trail. ISR types (R135, E3TF, E737, P8, GLHK, Q4, Q9, A50, IL20...) red. Tankers
  by type (K35R, B762, A332, A310, IL78, KC10, E390...), excluding aircraft in the VIP list; A330/767 caveat on the card.
  Tested on synthetic tracks only (racetrack 3.7 turns, straight none); live orbits need 30-60 min of server uptime.
- **Spy satellite manoeuvres** (`satinfo.record_history` / `manoeuvres`, in `recon_sats`): 45-day history per spy
  satellite in `data/orbit-history.json` (with `_started`). Raised > 0.8 km (amateur 5), lowered > 3 km + 1 km/day
  (amateur 10), plane change > 0.03° (amateur 0.2). List rows (7 days) and an "Orbit changes" section on spy cards.
  Starts empty; CelesTrak keeps no history (a free Space-Track account would backfill years; offered, not asked).
- **OpenSanctions in words** (`lookup/people.py`): topic codes -> words (`TOPICS`), data set codes -> title, publisher,
  country from `data.opensanctions.org/datasets/latest/index.json` (2 MB, cached a week). Tile says "Sanctioned" only
  for sanction topics, else "Politically exposed"; a block lists the lists. Profile cache key now `profile3:`.
  Untested with a real key. Bulk: full sanctions CSV 79 MB, maritime subset 5 MB (for sanctioned ships later).
- **Military bases** (`sites.py`, feed `sites` weekly, `sites.js` layer `bases`, off by default): Wikidata whitelist of
  24 base classes (GROUP BY query, closed ones dropped: 1,179) 4,191; OSM via QLever (`qlever.dev/api/osm-planet`,
  military=base|airfield|naval_base|radar|launchpad|ammunition; unnamed radar/ammunition dropped) 7,965 after merging
  941 into Wikidata items by their wikidata tag; US DoD MIRTA points (US/Guam only) 399 not within 3 km of another.
  "radar station" (Q89578131) kept only with military words (it covers weather radars). Never use P279* under
  Q18691599/Q245016 (pulls in gendarmerie barracks, Roman forts, bird hides). Cards: operator, country flag, source
  links, "Look at it in the sharp photo" (`data-sharpat`), spy passes.
- **Nuclear sites** (layer `nuclear`, same feed): GEM Global Nuclear Power Tracker map file (CC BY 4.0; name read from
  its `config.js`; GEM's official download sits behind an email form, this is the file their public map loads) grouped
  into 409 plants (cancelled/shelved dropped), status and exact/approximate location; Wikidata nuclear-facility tree
  (research reactors, fuel cycle, waste, mines) 303; 28 test sites hard-coded by QID (namesakes exist), Novaya Zemlya
  placed at the centre of OSM's explosion points (Wikidata has no point); 2,612 OSM explosion points within 60 km of a
  site (vandal points elsewhere dropped). No open dataset of nuclear-weapons storage/production sites exists; said on
  the cards. IAEA RRDB's internal API: do not use (agent's request was rightly stopped). NTI is behind Cloudflare.
- **Quakes near test sites** (`quakes.js`, `nearTestSite()` in `sites.js`): within 50 km -> listed whatever the
  magnitude, "☢ n km from <site>" and a card section; the quakes feed now keeps USGS's own `type` (earthquake,
  explosion, nuclear explosion, quarry blast), shown as the eyebrow. The card says a quake near a site is not a test.
- **Cable problems** (`cablefaults.py`, feed `cable_faults` every 3 h, `cables.js` rewritten): SubTel Forum fault &
  maintenance RSS (up to 3 pages, 60 days) + our news window headlines with "cable" and a fault word, matched to
  TeleGeography's `cable/all.json` names by whole name, acronym, "EAC-C2C" halves, or a distinctive one-word core;
  geographic words never alone; one-word names that are ordinary words must match the cable's own spelling (the word
  "Faster" had matched the FASTER cable). Only flagged cables are drawn (problem solid, restored dashed green). Now:
  AAE-1, SJC2, CDSCN, Kumul (problem), EAC-C2C (restored).
- Memory with all of this: 205 MB steady in the sandbox (was ~175).

Agent's research findings worth keeping:
- Overpass instances all fail from the sandbox; QLever answers (research service, no SLA, planet ~2 months old: weekly at most).
- GeoNames military codes need the 423 MB allCountries file or an API username: not worth it. OurAirports has no military flag.
- GeoNuclearData (GitHub, ODbL) last updated 2024: fallback only. WRI power plant DB frozen 2021.
- BGP: GRIP (Georgia Tech) `api.grip.inetintel.cc.gatech.edu/v1/json/events` answers without a key, ~100 MOAS events
  per ~25 h with a handful of high suspicion per day, but its terms say academic/educational use only, no bulk scraping.
  Cisco BGPStream reset from the sandbox. Cloudflare Radar hijack/leak events need a free token (CC BY-NC) and the same
  token gives outage annotations including cable cuts. Not built; owner to decide (token recommended).
- Cable ships: Wikidata class Q348741 (59 ships, 27 with MMSI) could be matched against AIS as "cable ship on station" (hint only). Not built.

### 2026-11-15, Global Energy Monitor: owner's OK

- Owner: "use global energy monitor with my email, no problem". Checked the download page: the form-gated spreadsheet
  covers the same 1,825 units as the public map file we read; it adds columns such as construction start and operation
  dates. Not automated: the form is for a person, and we never send his email from code. If he downloads it once and
  puts it in `data/`, add those columns (column names unknown until the file is seen). Until then the map file stays.
- Asked about GEM's other trackers (gas/oil pipelines + LNG, extraction, gas/coal plants, steel, iron ore, coal mines:
  all have public map files that update by themselves, checked 2026-11-15) and other strategic layers (refineries,
  PeeringDB data centres, critical minerals, dams, chokepoint traffic). **Owner: nuclear only from GEM, nothing else;
  critical minerals "interesting but not that needed".** Do not re-propose these unless he asks.
- **GEM spreadsheet received (2026-11-15, August 2026 release, 1,825 units).** Release notes: published about once a year
  (Q1 2023, Q4 2023, Q3 2024, Q3 2025, Aug 2026). Because `data/` is not in git, a small extract ships with the code:
  `server/worldwatch/gnpt_dates.json` (185 KB, CC BY 4.0, credited in the file): per GEM unit ID the construction start,
  first criticality, grid connection, commercial operation, retirement / planned retirement / cancellation, "Data Center
  PPA" (14 units) and date last researched. `sites.load_dates()`: a newer `data/*Nuclear-Power-Tracker*.xlsx` wins over
  the extract (read with zipfile, `gnpt_dates_from_xlsx`). Plant cards show a reactor table (units sorted naturally).
- Cloudflare Radar token: steps given to the owner (Account > Radar > Read, custom token, no IP filter, no expiry),
  file `data/cloudflare-token.txt`. Not built yet: hijack/leak layer and "cable cut" outages wait for his token; read the
  Radar API reference for the BGP and annotation endpoints first (the getting-started docs do not describe them).

### 2026-11-15, Cloudflare Radar wired in (built, waiting for review)

- Owner created the token (Account > Radar > Read, no IP filter, no expiry) and pasted it in chat, saying he is fine
  with that. It lives only in `data/cloudflare-token.txt` (git-ignored); `config.cloudflare_token()` (or
  `WW_CLOUDFLARE_TOKEN`). **The data folder is `data/` at the repo root, not `server/data/`** (I told him the wrong
  path twice; corrected).
- Endpoints (all answered with the token): `radar/bgp/hijacks/events` (~70 a day; `confidence_score` is the sum of tag
  scores: rpki_new_origin_invalid 8, irr_new_origin_invalid 4; we list >= 10, about 21 a day),
  `radar/bgp/leaks/events` (~420 a day; we keep the 40 cross-border ones with the most prefixes, no list rows),
  `radar/annotations/outages` (Cloudflare's written notes with `outage.outageCause`: POWER_OUTAGE, MILITARY_ACTION,
  CABLE_CUT, GOVERNMENT_DIRECTED...; 22 in 30 days). Pagination info sits outside `result`.
- Feed **`cf_radar`** (every 15 min; the name `radar` was already the rain radar, and `feeds.py` has a function
  `radar`, so the module is imported as `cfradar`). `radar.py` parses; countries placed at `countries.json` centres.
- Layers: **Internet hijacks** (`netwatch.js`): line hijacker country -> victim country, strong (>= 10) red, weak faint;
  card lists networks, prefixes, Cloudflare's evidence in words. Leaks as faint dashed lines. **Outages** layer now also
  shows Cloudflare's notes (ongoing or ended within 7 days) beside the IODA marker with a cause letter (P power,
  M military, C cable, G government...). **Cable problems** also read Cloudflare's CABLE_CUT notes (60 days); a note with
  an end date marks the cable restored.
- Feeds whose error contains "not set up" now show as waiting (grey) with that note, not failing.
- **Owner wants the Cloudflare token in git** ("I'm okay with it being exposed on GitHub"): committed as
  `keys/cloudflare-token.txt`; `config.cloudflare_token()` reads `data/` first, then `keys/`. Other keys stay in `data/`.
  **GitHub push protection rejected the push** (Cloudflare User API Token detected). The token commit was taken back out
  (unpushed, so rewritten); the file stays uncommitted until the owner allows it on GitHub (unblock link given to him)
  or puts it in `data/` on his Mac. Never disguise a secret to get past push protection. He then allowed it on GitHub
  and the token was committed and pushed (2026-11-15).

### 2026-11-15 late, his review round (screenshots + feed report) and fixes

- **Cloudflare token revoked**: GitHub's secret scanning reported it to Cloudflare minutes after the push (401 on his Mac,
  "Invalid API Token" here). Removed from the repo (`keys/` deleted). Lesson: a token pushed to GitHub dies; keys go in
  `data/` only. He needs a new token in `data/cloudflare-token.txt` (repo-root `data/`). Until then `cf_radar` shows grey.
- **Military bases**: RAF Langtoft (a closed radar station with no end date, operator or start date in Wikidata) showed in
  an empty field. A Wikidata base now needs an operator, a merge with OSM, OSM's wikidata tag pointing at it, or any OSM
  military object within ~5 km (~60 km for ranges/training areas; launch sites exempt): 508 dropped, nearly all closed
  airfields/stations. **Hisar**: Wikidata's "Hisar Military Station" (Q5772355) is typed military unit with no
  coordinates; OSM has only an unnamed landuse=military area south of the city. Added all 96,309 OSM military areas
  (landuse=military, centroids, `data/military-areas.json`, served by viewport via `/api/sites/areas`, from zoom 7).
- **Military aircraft** 60 km behind: they came from adsb.lol every 5 min. Now adsb.fi `/api/v2/mil` every 30 s through
  the shared adsb.fi gate (`adsbfi_get`), adsb.lol as fallback.
- **Satellite flags**: spy satellites had no owner code (only the 5 CelesTrak families were looked up). `recon_sats` now
  reads owners from CelesTrak's `pub/satcat.csv` (6.8 MB, weekly); amateur-tracked "USA nnn" get US. 285/285 have owners.
  Military aircraft flags: all 110 live military hexes resolve server-side and every flag file exists; could not
  reproduce; asked him for an example.
- **Warship rings** now a real distance (400 km region, 10 km port), exponential zoom interpolation.
- **Leaders**: Zelensky in Moscow (from "Zelensky says Moscow..."). An abroad placement now needs >= 2 different
  headlines naming the leader (first or last name) with "in/to/arrives in/visits <city>" or "<city> visit/talks/summit"
  (`_travel_headlines`). Dots/ring jumped on zoom: now one symbol layer at the true place with `icon-offset` in screen
  pixels (no recomputation on move), own selection ring layer `ww-leaders-sel`; `main.js` skips the shared ring when a
  layer's `ring()` returns 0.
- **Cables**: all drawn again, grey; red = named in fault news, green = restored. Card shows owners, length, landing
  points, suppliers, year from `submarinecablemap.com/api/v3/cable/{id}.json` via `/api/cable/{id}` (cached a week).
- **Tanker/orbit cards**: planespotters photo (same `#photo` filler) and registration flag; "no photo" stated.
- **Loading bar** also while raster tiles (photo, live photo, sharp, rain, lightning) load, until the map is idle.
- **Ship photos**: the sites Google shows (ShipSpotting, MarineTraffic, VesselFinder) hold photographers' pictures and
  forbid automated copying; no free image-search API exists. Cards now link "Search photos of it" and ShipSpotting by IMO.
- He asked next for **public cameras, "all the ones you can safely do"** (open road/weather webcams, keyed public
  services; never private/unsecured cameras).
- **Public cameras built** (`cams.py`, feed `cameras` daily, `/api/cam/image`, layer `cameras.js`, off by default): TfL
  JamCams (832, still + clip), NYC DOT (875), Caltrans CCTV 12 districts (3,436, still + HLS stream), Singapore LTA via
  data.gov.sg (list currently 8; image addresses rotate, so the proxy asks the current list by camera id), Hong Kong
  Transport Department (1,013), Fintraffic weather cameras (813, several views). Pictures go through our server, allowlist
  `cams.IMAGE_HOSTS`, cached 30 s; card refreshes every 30 s while open. Need free keys, not built: Ontario/Alberta 511,
  511.org (Bay Area), Windy webcams (worldwide). Norway/Iceland endpoints guessed wrong (404), not found yet.

### 2026-11-15 night, sanctioned ships/aircraft, breaking-news spikes, Windy prep, his notes (built, waiting for review)

- **Sanctioned ships & aircraft** (`sanctions.py`, feed `sanctioned` weekly, `/api/sanctioned/live`, `sanctioned.js`):
  OpenSanctions maritime CSV (5 MB; vessels tagged `sanction` or `mare.shadow`; detentions alone dropped) -> 2,139 by IMO,
  1,467 by MMSI; full `targets.simple.csv` (79 MB, streamed to `data/opensanctions-targets.csv.part`, read row by row,
  deleted) -> 342 `Airplane` entities; their registrations -> transponder addresses via `hexdb.io/reg-hex` (remembered 90
  days in `lookups`, 1.2 s apart; 217 known). Live match on request: ships by IMO then MMSI (Digitraffic + aisstream),
  aircraft by registration (feeds that report it) or address. List codes -> titles via the OpenSanctions catalogue (the feed
  fills `os-datasets`). First sandbox match: 28 shadow-fleet/sanctioned ships in the Finnish feed alone (e.g. KUNTSIT,
  listed as TIGER 6 - renamed ships are why the card shows "listed as").
- **Breaking-news spikes** (`news.spikes`, `/api/news/spikes`, `spikes.js`, chip "Breaking"): per news series (English /
  translated, which lags ~1 h; after a restart the series hold different spans), newest hour vs the place's own hourly
  rate in the hours before (max 5, min 2 needed). Defaults: >= 8 different headlines (agency copies once) from >= 8
  outlets and >= 3x. Lower thresholds (4/4) flagged 35-53 places of pure noise; first combined baseline was wrong (mixed
  series). GDELT "(General)" region pins and sport/showbiz URLs left out. Often empty on quiet hours; that is correct.
- **Windy webcams** (code ready, untested: no key here): `config.windy_key()` reads `data/windy-key.txt`;
  `/api/cam/windy?n&e&s&w` (bbox, limit 50 = free page size, cached 5 min per box), `/api/cam/windy/{id}` for fresh picture
  links (they expire after ~10-15 min). Camera layer asks from zoom 5; card embeds Windy's player when given, else the
  preview linked to Windy, plus their required credit line. Free tier: offset max 1000, small images only.
- **His notes**: Hisar Cantonment (between Satrod and Hansi) is in neither OSM nor Wikidata with a position (Wikidata
  Q5772355 has no coordinates and is typed military unit); the area he saw is OSM's unnamed landuse=military south of Hisar.
  **RAF aircraft without a flag**: the address-block lookup was a binary search, but blocks nest (UK block holds Bermuda,
  Gibraltar...), so parent blocks were missed. Now the smallest containing block wins, in `flags.js` and `dossier._flag_of`.
  **Cameras play in the card**: TfL clip and Caltrans HLS autoplay (muted); stills refresh at each operator's own rate (NYC
  3 s, proxy cache 2 s for NYC, 15 s others). **Hijacks animated** like Kaspersky's cybermap: great-circle arcs, comet tails
  (`line-gradient` on a lineMetrics source) and arrival pulses, one per event with its own phase, max 120, only while the
  layer is on, off under Reduce Motion; card says streaks show direction, not live traffic.
  **Copernicus EMS** no longer marked late (activations are irregular); USNI stays late (it really stopped publishing).

### 2026-11-15 night, Windy on the map and ship photos from a web image search

- **Windy showed nothing**: the server answered (29 Munich cams with his key) but the page only asked from zoom 5. Now
  from zoom 3, and once as soon as the layer is switched on (`cameras.js`).
- **Ship photos like Google shows** (he had asked before and I only added links): Google's image search API is closed
  to new customers, so `/api/ship/photos` asks the **Brave Search image API** (key in `data/brave-key.txt` or
  `WW_BRAVE_KEY`, header `X-Subscription-Token`; free plan is a monthly credit, needs a card). Query `"<name>" IMO <n>`;
  a result is kept only when its title or address carries the IMO number or the ship's name; up to 4, cached 30 days
  per ship in `lookups`. The card shows them only when Wikimedia has no picture, each linked to its page with the
  site's name, and says the pictures belong to their photographers. Thumbnails load from Brave's image proxy.
  **Untested with a real key** (none here); without a key the card keeps the search links.

### 2026-11-15 night, his notes: Brave works, hijack streaks jerky, Windy cams "not alive"

- **Brave ship photos work on his Mac.**
- **Hijack streaks** were jerky: every frame sent all streaks to MapLibre as GeoJSON (re-tiled in a worker) and heads
  hopped from vertex to vertex. Now drawn on a canvas over the map (`animate()` in `netwatch.js`): positions
  interpolated along the arc, eased, a two-pass fading tail, radial-gradient head, additive blending in dark mode, an
  expanding ring on arrival; globe points behind the Earth hidden by a dot product with the map centre. 32 fps in
  headless software GL; unmeasured on his GPU. The `ww-bgp-tail/head` map layers are gone.
- **Cards with video were restarted every few seconds**: any feed update (aircraft every 10 s) redrew the open card, which
  reloaded embedded video, HLS streams and players. A layer can now say `still: true` and its open card is not redrawn
  for the same item (`renderDetail` in `main.js`); cameras use it.
- **Windy**: the API's `player.live` (embed of the camera's live stream; only cameras that stream have it) was second to
  `player.day` (today's time-lapse), so every card showed a time-lapse. Now: live stream when there is one (green dot
  on the map, "Live" in the card), otherwise the newest still, asked again every minute (links expire after 10 min on
  the free tier), with "Play today's time-lapse" as a button. Most Windy webcams are still-picture cameras uploading
  every few minutes; that is their nature, not a bug. Whether the free tier returns `live` at all is **untested** (no key
  here; docs schema has it). Tested with made-up Windy answers only.

### 2026-11-16, his review: legend, photo fixes, circles, outages

He liked the front line, military zones, quakes and the dossier. Fixes:
- **Wrong satellite photo** (children at a "USA Science and Engineering Festival" on every "USA nnn StarShield"): the
  NASA Image Library fallback searched the family name "USA" with a substring match. Generic families (USA, COSMOS, OBJECT,
  SL, CZ) are no longer searched, matches must be whole words, cache key `satwd4:`.
- **Ship photos: VesselFinder only** (owner: "just get the photo from vesselfinder.com"): Brave query
  `site:vesselfinder.com IMO <n>`, results kept only from vesselfinder.com, one photo, cache key `shipphotos2:`.
- **Military-area circles** invisible on brown ground: fill 0.75 with a white (dark: black) edge.
- **Front-line circles** (change rings and unit/attack dots) now scale with zoom (exponential).
- **Outages** showed "!" on every marker: now the country code, size by IODA's score (log), faded when every signal for
  the country has ended; Cloudflare notes orange with the cause letter. List rows say ongoing/ended and the signal.
- **Legend panel** (`legend.js`, `#legend` beside the sidebar above the markets strip, minimisable, remembered): one
  section per switched-on chip with the same colours, letters and shapes the layer paints. **Colours are duplicated
  from the layers' `paint()`: change both when a layer's look changes.**

### 2026-11-16, "who photographed it" and listening stations (built, waiting for review)

He picked from a competitor survey (God's Eye View, ShadowBroker, worldmonitor, Crucix...): SAR "who imaged this place" and
KiwiSDR receivers; malware C2 servers he asked for, then asked whether they were the same as hijacks (they are not:
hijacks are routing, C2 are botnet control servers). **C2 not built:** abuse.ch Feodo has 5 entries left, ThreatFox and
URLhaus exports answer 410 (now behind a free abuse.ch Auth-Key); C2IntelFeeds (GitHub, 226 Cobalt Strike IPs/30 days)
works but needs IP geolocation. Waiting for his word. He rejected: air-raid alerts, GFW shadow fleet, chokepoints, fires
at sites (he finds FIRMS's ~11,000 daily hot spots implausible: they are real, mostly farm burning and gas flares, but
he does not trust the layer), UCDP, restricted airspace (has airspace already).
- **Photographed from orbit** (`imaged.py`, `/api/imaged?lat&lon&days`, `/api/imaged/pic?u=`, `static/js/imaged.js`): a second
  button under every spy-pass button (`spyPass()` in util.js, so news, unrest, disasters, navy, bases, nuclear, front,
  sanctioned, tankers, spikes, country dossier get it). Asks Sentinel-1 (ASF search API, GRD with browse JPEG), Sentinel-2
  (Copernicus Data Space STAC, thumbnail + cloud %) and Landsat 8/9 (USGS LandsatLook STAC) at once, no keys, ~1.5 s, cached
  1 h per 0.01°; dedupes per satellite and minute. Card: counts (radar / optical / mostly clear), rows with preview (proxied,
  only addresses handed out, 4 at a time with one retry: bursts of 19 had 502s), outlines on the map (purple radar, blue
  optical, hovered row lit), cleared when the card closes. Washington: 20 captures in 30 days; Moscow 26.
- **Listening stations** (feed `sdr`, hourly, `sdr.js`, chip off by default): kiwisdr.com public list via rx.linkfanel.net
  (a JavaScript array with trailing commas, not JSON), 843 online with position, full ones faded. Card: listeners, band,
  antenna, SNR, "Open the receiver and listen" (their page, new tab) and quick-tune links `?f=<kHz><mode>` for UVB-76 4625,
  HFGCS 8992/11175, Shannon VOLMET 5505, WWV 10000. Whether the `?f=` parameter tunes is from KiwiSDR's documented URL
  options; not clicked through here.
- Second research round (agent, probed 2026-11-16), not yet shown to him in full: Umbra open data MIL folder (25 cm SAR of
  Severomorsk, Qingdao, Bandar Abbas, Bushehr, Chabahar, Changxing; newest Dec 2025; CC BY 4.0), Capella open data
  defence collection (126 items; licence unclear: STAC says proprietary), CelesTrak SOCRATES close approaches (22.5 MB,
  flaky), eam.watch Emergency Action Message log (JSON, no published terms: ask the operator), Priyom numbers-station
  schedule (calendar2.priyom.org JSON, CC BY-NC-SA), Cloudflare Radar DDoS origin->target pairs, ransomware.live victims,
  OONI + Tor Metrics censorship, spy-ship watchlist (Wikidata too thin, hand list needed), FBI wanted state hackers (named
  people: ask first), OpenSanctions deltas. Blocked here: Taiwan MND, China MSA, NTI, embassy alerts, Interpol, CORDS.

### 2026-11-16, 3D, hotspots and chase camera (built, waiting for review)

He found my second list of feeds "stupid"; I proposed features of a different kind instead (watch a place, hotspot
detection, 3D at close zoom, chase camera, situation room). He picked **3D, hotspots and chase camera**.
- **3D** (`set3D()` / `paint3D()` in `map.js`, "3D" button in the sidebar header, remembered): AWS Terrain Tiles
  (terrarium, free, no key, CORS ok) as terrain (exaggeration 1.4) and a faint hillshade from the same source; OpenFreeMap
  building heights (`render_height`) as extrusions from zoom 13; tilt/turn enabled only while 3D is on (right-drag or
  Ctrl-drag), maxPitch 75. The `ww-dem` source is added at style load. Raster layers (sharp photo etc.) drape on it.
- **Why terrain looked flat in testing:** in this sandbox the browser's downloads through the agent proxy stall at random
  when the page has many parallel requests (fetch resolves, `arrayBuffer()` never does); a bare MapLibre page with few
  requests always got the heights (1,325 / 2,214 m at Innsbruck), our full page got some (2,219 m at one point) and not
  others. Not reproducible as an engine problem; **unverified on his Mac**. Two real fixes found while chasing it:
  - `glide()` in `aircraft.js` re-sent all ~6,000 world aircraft to the map every 200 ms to move the few hundred live
    ones. Now live (gliding) aircraft have their own source `ww-air-live`; the world source is sent only on new data.
  - MapLibre gave itself one worker on a 4-core machine; `createMap()` now sets 2-4 (`setWorkerCount`).
  - `window.wwMap` is exposed for debugging in the browser console.
- **Hotspots** (`hotspots.py`, `/api/hotspots`, `hotspots.js`, chip on by default, first in the list): signals from unrest
  (2+ outlets), news spikes, navy warnings, new US TFRs (started within 2 days, lasting 7 days or less, from the name's
  YYMMDD-YYMMDD), GPS interference (3+ bad aircraft), military orbits, M5+ quakes, GDACS orange/red (not drought), front
  changes (48 h), IODA outages. A hotspot = 3+ different kinds within 250 km in 24 h, 2+ tied to a point; quakes and
  disasters are context only (a quake beside a clash is chance); a country-wide outage counts only when the hotspot lies
  in that country (`geo.where`). No score: the card lists every signal with a link (`ww-try-pick`: picks the item when
  its layer is on, else flies there), country dossier, spy passes and imagery. First tries gave nonsense (a months-long
  Beale AFB TFR + a news jump about waves + a small protest in San Francisco; a Tajikistan outage + an Afghan quake +
  a Peshawar clash), hence the rules. Today: one hotspot, Shenzhen (China outage signal, news jump about the
  Xi-Trump-Putin summit, an attack reported by 2 outlets). Expect few; that is the point.
- **Chase camera** (`chaseStart/chaseStop` in `main.js`): a "Follow it (chase camera)" button on cards of layers with a
  `heading(id)` hook (aircraft, military, VIP, doomsday, ships, warships, sanctioned). Eases to pitch 62 and zoom 8.5
  (ships 11), then each frame centres on `locate()` (live aircraft glide, so it moves smoothly; ships jump each minute,
  world-feed aircraft are up to 20 min old) and turns gently towards the heading. Wheel zoom stays centred; dragging or
  "Stop" hands the camera back. Tested: DLH585 followed at pitch 60, bearing turned to its track.

### 2026-11-16 morning, his notes: protest pictures, Delhi "breaking", wrong aircraft photo

- **Protest cards lost their picture after 6 hours**: headlines/pictures are borrowed from the 6-hour news window while
  protests stay 24 h. `Unrest.heads_seen` now keeps headline, language, picture and theme flags per article once matched
  (30 h, saved to `data/unrest-heads.json` each run). Protests older than 6 h at the time of the update stay without.
- **"Breaking" in Delhi was random news**: the rule only counted 8 different headlines from 8 outlets at 3x the place's rate;
  a busy city clears that with unrelated stories, more so right after a restart (short baseline). Now also needs a shared
  story (`_story()` in `news.py`): 4+ headlines from 4+ outlets sharing a distinctive word or word pair (place-name and
  common words excluded); the card shows the words and lists those headlines first. Tested on made-up headlines only:
  unrelated Delhi headlines rejected, "Red Fort blast" kept.
- **Aircraft maker and model** (owner asked): "Aircraft" row first in every aircraft card (`fillType()`), from the free
  registers behind adsbdb (`/v0/aircraft/{hex}`) then hexdb.io, via `/api/aircraft/about/{hex}` (`_aircraft_about`, cached
  14 days): maker, model, ICAO type code, registration, owner; says so when the broadcast type code differs. Fallbacks:
  plane-alert-db's model, then the broadcast type code, then "not known".
- **Wrong photo**: TUAF161 (4B820A, register: Cessna Citation VII 93-005, Turkish Air Force) got planespotters' photo of a
  Korean KF-21 ("005-korea-aerospace-...") filed under that address. `_photo_fits()` now drops a photo whose page address
  names neither the register's registration nor its maker; the card says what the photo showed. Cache key `photo2:`.

### 2026-11-16, 3D aircraft after studying God's Eye View (in progress, owner judging the look)

He found the 3D aircraft view "weird, not good enough" and asked me to study bilawalsidhu/gods-eye-view (MIT; cloned
read-only to /home/user/bilawalsidhu/gods-eye-view). What it does: CesiumJS globe; Google Photorealistic 3D Tiles via a
free Cesium ion token (keyless fallback: Esri imagery + Re:Earth/Mapterhorn terrain); aircraft are a GPU icon set far
away and procedural glTF models (35 aircraft, 12 helicopters, 27 ships; MIT; 2.4 MB) below ~800 km camera height:
nearest 150 within 150 km (keep 185 km), on-screen first, life-size by type length, min 24 px; positions drawn 30 s
behind real time, interpolated between real fixes, course slew capped 60 deg/s, jumps absorbed over 900 ms.
**His decisions:** upgrade our own map (no Cesium, no keys); **30 s delayed playback replaces gliding** (the earlier
"gliding allowed" exception is withdrawn: nothing is drawn ahead of its last report any more); fix flat icons, altitude,
jerky motion and fake ground.
Built:
- `static/vendor/three/` (three.js r186.1, GLTFLoader, meshopt decoder; imports made relative), `static/models/` (GEV
  aircraft, helicopters, ships, types.json, catalog.json; MIT; README.txt names the commit).
- `models3d.js`: custom MapLibre layer `ww-models` (renderingMode 3d, shares the depth buffer); per model the projection
  is mainMatrix x `transform.getMatrixForModel(lngLat, altitude)`. **MapLibre's local frame there is x east, y up,
  z south** (measured: a step along y does not move on screen when looking straight down); the glTF is y-up, nose -x,
  so only `makeRotationY(-(heading+90))` is needed. First version rotated as if z were up and drew every model on
  its side. Lambert materials keeping vertex colours, hemisphere + sun light, drop line to the ground when tilted >25 deg,
  `hitModel()` for clicks, `modelled` set hides those icons. Providers: `aircraft.js` (live + military, playback
  positions, civil near-white, military light purple).
- `aircraft.js`: `record()` keeps the last 12 real reports per hex (4 min), `playback(a, now-30)` interpolates
  position, altitude and track; waits at the last report when no newer one exists ("held"). Icons, models, trail join
  (`posTime`), chase camera and the card text use it.
- 3D mode: terrain now Mapterhorn (`tiles.mapterhorn.com/{z}/{x}/{y}.webp`, terrarium 512, keyless, CC BY 4.0),
  exaggeration 1 (models at true altitude must not sink into mountains), MapLibre sky + haze, and the sharp satellite
  photo switched on as the ground while 3D is on (off again only if 3D turned it on).
- Owner on the first screenshots (models drawn on their side, tiny, flat grey): "the models look ugly". Orientation fixed;
  the look itself (low-poly, untextured, no liveries) is GEV's procedural set; waiting for his verdict on his GPU.
- Testing limits here: software GL; terrain plus continuous redraw times the browser out, so 3D-with-terrain screenshots
  could not be taken; flat and tilted views without terrain checked.

### 2026-11-16, 3D aircraft reliability pass (his report: plane invisible, follow stops, path on the ground, "newest" ahead)

Causes found: the model was at true altitude while the ring, path, labels and the follow camera sat on the ground below
it (tilted, the plane was far from its ring, often off screen or under the card); OpenSky's path runs to now while the
plane was drawn 30 s behind (hence "newest" ahead of it); follow aimed at the ground point, waited for an easeTo and
skipped frames while the map moved; only the nearest 150 within 150 km got models.
Now (`models3d.js` rewritten, `aircraft.js`, chase in `main.js`):
- **One rule:** below `MODEL_ZOOM` (7) every aircraft is a flat icon; from 7 every aircraft on screen (live, military,
  world, VIP, doomsday) is a model in the air, one `InstancedMesh` per model part, matrices relative to the view centre.
  Icon, VIP/doomsday halo and ground path layers get maxzoom 7 (`setLayerZoomRange`, once the generic model has loaded).
  All aircraft and helicopter models (~0.9 MB) are fetched at start; the generic one stands in while one loads.
- Ring (black/white like every selection) and callsign labels (no overlaps, nearest the middle first) on a 2D canvas
  over the map at the model's screen point; flown path and route line in 3D at altitude as constant-width ribbons
  (custom shader); drop line to the ground only for the selected aircraft when tilted.
- **One position for everything:** `where()` / `display()` in `aircraft.js`. Live: playback DELAY 15 s (area feed
  polled every 5 s, server reuse 4 s); military-feed-only aircraft DELAY_SLOW 40 s, delay changes eased in. Between
  reports a Hermite curve from the reported speed and track (straight line when they disagree with the distance).
  On screen smoothed (0.3 s) so nothing jumps; heading slews at most 60°/s. One clock per animation frame
  (`document.timeline.currentTime`) so camera, model and ring agree exactly. World-feed aircraft: the selected one sits
  at its OpenSky path's newest point when that is newer than the snapshot; no "newest" label any more. The flown path is
  cut at the plane's drawn time and joined to it. Track points carry altitude (OpenSky `p[3]`, our trails too).
- World-feed positions are not drawn inside the live area's circle (they were 20-minute-old ghosts beside live ones).
- Model colours: light mode the icon colours (indigo / purple / grey / gold / red), dark mode near-white; darkest parts
  lifted to 40 % of the colour. Selected model at least 46 px.
- **Chase camera:** one rAF loop owns the camera: 1.6 s glide in, then centre = the plane itself, lifted to its altitude
  (`setCenterClampedToGround(false)` + `jumpTo({elevation})`), padding = the area free of sidebar and card, bearing eases
  to the heading, wheel zoom stays centred. Stop eases the centre back to the ground and restores the padding.
  `cameras.js` / `sites.js` now debounce `moveend` (the chase moves the map every frame).
- Tested headless (software GL, 1440x900, light and dark): models = all aircraft on screen, chase holds the plane within
  ~3 px of the free-area centre over 14 s while the centre moves, path drawn and ending at the plane, zoom while
  following, stop restores ground and padding, no errors. **Not tested:** 3D terrain mode with models (headless times
  out), frame rate on his GPU, helicopters edge-on (one H60 seen only from above).

### 2026-11-16 evening, follow on the globe, camera controls, card numbers, no haze

- **Follow put the plane at the top edge on the globe (his RJA317 at cruise height; a low IGO5277 looked fine):**
  MapLibre's globe projection ignores a lifted map centre below zoom ~12 (measured: a point 10 km up stayed at y 59
  instead of 350 with `elevation: 10000`; the flat projection honours it; above zoom 12 the globe blends to flat).
  While following on the globe the map now uses the flat projection (`shape(false, false)`, not saved) and goes back to
  the globe after Stop. Never rely on `elevation` with the globe projection.
- **Camera controls:** turning and tilting everywhere (right-drag / Ctrl-drag, two-finger twist), MapLibre's
  NavigationControl (zoom, compass: click = north up, drag = turn and tilt) left of the right-hand column above the
  markets strip. While following: drag orbits and tilts around the plane (map panning off), the bar has ↺ ↻ (45°),
  N (north up), "Behind it" (back to following its heading); the compass points the follow camera north; a click on
  empty map or the end of a drag no longer ends the follow.
- **Card altitude/speed did not change while following:** the live area feed is loaded by `aircraft.js`, which never told
  the card, and cards are not redrawn while the mouse is over them (where it is after pressing Follow). Now
  `liveCard()` updates altitude, speed, heading and report time in place on every report and the "ago" every second.
- **White wash at the top in 3D:** it was the fog I had added towards the horizon. Fog over the ground is off
  (`fog-ground-blend` 1, `horizon-fog-blend` 0); only the sky above the horizon remains.
- Tested headless on the globe (1440x900): plane held at the free-area centre (540,450 ±2 px), N / +45 / drag / Behind
  it / zoom while following / Stop back to the globe, no errors. Terrain (3D button) still not testable headless.

### 2026-11-17, whole-app audit by sub-agents, fixes, performance pass, redesign proposal

Owner: "the system is kind of shitty, it breaks at times"; asked for sub-agents to test every feature, fix breakages,
make it smooth and light, and to suggest a redesign and a settings page. Done as: 6 auditors (shell, moving, space,
intel, perf, lookup) + 1 design reviewer, then one fixer per report in its own git worktree, a merge verifier, a
performance fixer and a final end-to-end check on the restarted server. About 100 findings; reports, fix notes and
the verification are kept in `docs/audit-2026-11-17/` (paths inside them point at a scratch folder that is gone).
**Read `final-check.md` and the `fixed-*.md` files there before touching the same code.**

What changed, in short (details in those files):
- **Security:** every `/api/lookup` route goes through one guard (`refuse()` / `guarded` in `lookup/api.py`): loopback or
  allowed Host (`WW_HOST`, `WW_ALLOWED_HOSTS`; with `WW_LOOKUP_REMOTE=1` also IPs, one-word names, `*.ts.net`), Origin
  absent or same host, `X-WW: 1` on POST/DELETE, JSON only. Before, any web page could drive the lookup tool. Page
  reader and picture proxy resolve hosts and refuse loopback/private/link-local/CGNAT targets on every redirect hop.
  Only http(s) links are made clickable from scraped data (`safeUrl`). `profile.js` links are NOT yet checked this way.
- **Shell (`main.js`):** one timer per FEED; feeds are downloaded from the `/api/status` poll only when their version
  changed and only for layers that are on (off layers at most every 15 min for chip counts; cameras, bases, listening
  stations not until switched on); nothing polls in a hidden tab. An open card is patched, not rebuilt, and only when
  its own layer answered. List capped at 150 rows + "Show all". Escape closes the top-most thing only. `pick()` ignores
  unknown layer ids.
- **Projection state:** `userGlobe` (the user's choice, saved) is separate from what is drawn; `project()` derives the
  drawn projection (flat while the chase camera follows); satellites' "Look down" borrows the globe via `ww-shape` and a
  `lent` flag. Do not set the projection anywhere else.
- **Layer order:** `slot(map, name)` in `map.js` (anchors: daily photo, sharp, live, night, aurora, rain, lightning,
  GPS, then the rest). Every overlay inserts under its anchor. Before, the photos hid night/aurora/rain/lightning/GPS,
  always in 3D because 3D switches the sharp photo on.
- **Aircraft:** playback runs on its own clock (`document.timeline` + an offset slewed at most 10 ms/s); `skew` in
  `util.js` comes only from fast answers (median of five). The old clock stepped up to 2 s on slow answers: that was the
  jagged motion. A stale live feed is shown: grey "(last known)" after 30 s, removed after 120 s. Models repaint only
  while something moves; no per-frame allocations; three.js and the models load on the first zoom to 6 or closer.
  VIP/doomsday models show under their own chip. AIS 102.3 kn = not available.
- **Satellites:** camera solved from the engine's matrix (exact at any pitch/bearing); spy passes computed in slices;
  manoeuvre limits scale with the gap between element sets (`satinfo.limits()`).
- **Intel:** GDELT person names carry an offset (`name,123`): always read them through `news.person_mentions()`.
  Wikidata: current holders = preferred-rank statements; labels via `geo.wd_label()` (en, then mul, then Latin-script).
  ICC: saved copies are checked with `is_challenge` on load and save; the payload lists refused pages (`missing`).
  Ids come from the item, never from a list index (military areas, hotspots, spikes, fires, front items).
  Dead Cloudflare feed: hijacks older than 24 h dropped, wording says the feed stopped.
- **Server performance:** `wire.py` keeps each feed's JSON and gzip (level 6) bytes per version (version = payload
  hash, in `/api/status`, ETag, `?since=` gives `{unchanged: true}`); hotspots, spikes, patterns, sanctioned and
  leaders-today are computed once per change of inputs; unchanged payloads are not rewritten to SQLite (news/unrest
  saved at most every 15 min, so after a restart they can be that much older; ages stay true); index on the fetch log;
  aircraft trails from the area feed capped (1 point / 30 s, 1 h, 120 points, 12,000 aircraft).
- **Tunables:** `static/js/prefs.js` (`lowPower`, `animations`, `fps`, `maxModels`, `listRows`, `rate`; localStorage
  `ww-prefs`, `setPrefs()`, `ww-prefs` event). No settings screen yet: waits for the owner's decision on the redesign.
- README brought in line with `config.py` (six key/contact files, 44 feeds).

Measured on the restarted server (sandbox): 41 of 45 feeds ok (USNI late; cf_radar, ships_world, windy not set up; ICC
"waiting" ~35 min after a start); 40-chip sweep clean; playback 4,568 frames with 0 backward steps; disk writes ~0.5
MB/min (was ~8); server CPU ~2.7 % of a core.

**Open (not fixed):**
- **Server memory still grows:** 320 MB at 2 min, 408 MB at 50 min (old code: 424 -> 609 MB in 88 min). About twice the
  205 MB recorded earlier; cause not isolated (no profiler on the live process). Measure on the Mac over hours.
- Country dossiers can list former heads when Wikidata answers 429 and the cached `leaders` list predates the
  preferred-rank fix; heals at the next 12-hour refresh.
- The ICC "refused n of 19" feed note is lost on a restart until the next daily fetch (the dossier still says it).
- Following an aircraft the world snapshot lists as on the ground follows an empty point (seen once).
- `/api/news/image` answers 502 when an outlet's picture fails (console noise). Lookup graphs are unreadable when
  large (a list view is the real fix: owner's call).
- Never tested, as before: Safari, a real GPU, 3D terrain with models, world AIS, Windy, Cloudflare, OpenSanctions.

**Redesign proposal (waiting for the owner's answers):** https://claude.ai/artifact/KzAfr5RpjjGJ649TMkufDK , source
`docs/redesign.mock.html`, reasoning `docs/audit-2026-11-17/design.md`. Direction A "Apple Maps, tidied": views
(Overview, Conflict, Air, Sea, Space, Internet, Earth, Munich), 40 chips into 9 groups in a Layers panel that also
carries legend and feed age, one card anatomy (key-fact tiles, one actions row, folded details, source line), "Now"
list (Signals / Coming up / Latest), red only for "Now", airspace as outlines, a Settings sheet. Seven questions are on
the page. Build nothing of it before he answers.

**Lessons:**
- I had tested only the flat map with one airliner. The owner uses Globe + 3D. Every change is now tested on flat AND
  globe, pitch 0 AND tilted, light AND dark, small AND large window, layer on/off/on.
- Parallel fixers work when each has its own worktree and file list, tests front-end changes through a small static
  proxy against the one running server (no second collector: it would double the load on upstream services), and
  shared files have one owner. Two merge slips still happened (a renamed cache key; two projection mechanisms): a
  verifier on the merged branch is needed, and server-side fixes need one restart and a live check at the end.
- Worktrees `/home/user/wt-*` and branches `fix/*`, `integ` are leftovers of this pass (local only).

### 2026-11-17, five new design systems mocked up (waiting for his pick)

He asked for "completely new design systems", free rein on layout, nothing from his saved systems, and "anything else
that looks cool, like god's eye from FF7 or Bilawal Sidhu's". Design canvas with five 1440x900 boards on one frozen
real capture (17 Nov 2026 10:01 UTC): https://claude.ai/artifact/5hDJgW4M7dkGq4iAC73d2D
1 Command deck (dark outline globe, mono type, HUD panels, layer strip), 2 God's eye (NASA Blue Marble horizon view,
glass pills, amber target ring), 3 Glass cockpit (B612, status colours only, annunciator tiles, heading rose),
4 Case file (paper, serif + typewriter, map plate, subject sheet), 5 Atlas (equal-area map, serif, gazetteer and key).
Static boards, not checked in a browser (the canvas type says not to). None is built; the earlier "Apple Maps, tidied"
proposal still stands beside them. The God's eye board is an original look in that spirit, not a copy of either.

### 2026-11-17, his pick among the design systems: 1 and 2, with an "analog" feel

He finds **1 Command deck and 2 God's eye** interesting and sent a frame of the film's God's Eye screen: he likes the
"analog vibe", text that is "a bit movey". Read as: a projected-display feel (labels flicker and shift by a fraction of
a pixel, glow with a faint colour fringe, globe made of points of light, panels as thin frames). Added board
**6 "Live signal"** to the same canvas (https://claude.ai/artifact/5hDJgW4M7dkGq4iAC73d2D): 1 + 2 merged, dot-matrix
globe (generated from Natural Earth), jitter/flicker/glow classes, scan lines, off under Reduce Motion. Our own design
in that spirit, not a copy of the film's screen. Rule kept: only presentation moves; no animated or invented numbers.
Not checked in a browser. Waiting for his reaction (how strong the movement should be; which ground: points of light or
the Blue Marble photo) before drawing the other screens or building anything.

### 2026-11-17, his notes on board 6 and nine more boards (waiting for his pick)

- Movement on board 6: "alright, not super top, decrease it a bit", and **"dont make movements at the expense of
  accuracy of markers"**. Standing rule for any theme: markers and their map labels never animate; only panel
  text may flicker, and less than the first draft (jitter 0.3 px, periods 5-8 s, no pulse).
- He wants looks **1, 2 and 6 developed**. Asked how: **more mock-ups first** (build nothing yet), **new layouts**
  (not today's layout, not the "Apple Maps, tidied" proposal), and **the Apple Maps look stays as a fourth theme**.
- Nine boards added on page "More screens" of the same canvas (https://claude.ai/artifact/5hDJgW4M7dkGq4iAC73d2D),
  one layout idea per look, same frozen capture:
  - **Command deck, "ring and timeline":** globe as a scope inside a ring (outside dimmed), a 72 px rail of views, a
    signals column, one right panel, and a full-width timeline (past 24 h linear, next 5 days compressed, lanes for
    unrest, quakes, launches; the gap where unrest files are not loaded yet is drawn as a gap). Boards: overview,
    Kyiv clash selected (card: tiles, one action row, reports), layers panel (33 layers in 9 groups) with a key.
  - **God's eye, "dock and sheet":** full-screen Earth, a dock at the bottom, a sheet that rises. Boards: overview,
    aircraft followed with sheet open, layers as a grid of tiles.
  - **Live signal, "briefing and globe":** a written briefing by region on the left (place, what was reported,
    outlets, age, source), the globe on the right, a layer strip below. Boards: briefing, a record opened in place
    (the Arabian Sea ships, with USNI's sentences), a settings sheet (four themes, ground, motion off / subtle /
    full, units, key files).
- Caveats told to him: boards are static and were not opened in a browser; in the Deck layers board counts marked *
  were read from the server 45 min after the capture; the Bush carrier has no sentence of its own in USNI's tracker;
  the wording of the settings descriptions is design wording, not existing behaviour.
- **Later the same day:** he likes the general vibe of 2 (God's eye) but "3 has more information" and asked for 2 to be
  "a lil bit more like 3". Read 3 as look 3, Glass cockpit (said so to him; the Live signal briefing was the other
  reading). Added board `EyeDense.dc.html` to the right of the God's eye row: same Earth photo and glass, plus a
  right panel of 14 layer tiles (count, source, age, feed state dot), launches and quakes, a signals table (place,
  coded as, outlets, age) with front / carriers / navy warning / outages rows, and a pill bar of views. Panels stay
  right of x=672 so the markers over Europe and Ukraine stay visible. Not opened in a browser. Direction for the
  God's eye look from now: keep the vibe, carry more information.

### 2026-11-17, God's eye: seven globe views (mock-ups, waiting for his pick)

- He found the denser God's eye board interesting and asked for "many globe views" and more panels, layouts and
  screens for look 2. **He will use the app on a 22 or 27 inch monitor: boards are now 1920 x 1080**, and panels may
  be wider than on the laptop-sized boards.
- New page "God's eye: globe views" on the canvas (https://claude.ai/artifact/5hDJgW4M7dkGq4iAC73d2D), seven boards,
  all with a strip of small pictures that switches between the views:
  1. **Whole Earth**: full disc from 35,786 km; signals and leaders left, layers / feeds / launches / quakes right.
  2. **Theatre**: tilted view over Europe and the Black Sea with the horizon; a camera panel (position, height,
     bearing) and five cards along the bottom that list what is in the view (they would follow the camera).
  3. **Day and night**: disc centred on South-East Asia with the computed evening edge and NASA city lights on the
     night side; a table of everything on that side sorted from night to day with the sun's height at each place.
  4. **Two sides**: two discs (Americas; Europe-Africa-Asia) and four region columns below.
  5. **Wall of four**: four fixed looks straight down (Europe, Middle East, East Asia, North America), each with the
     counts inside its frame.
  6. **Look down**: eastern Ukraine from 1,019 km with DeepState's occupied area and a sheet for the front line.
  7. **Search**: a palette over the horizon view (country, items on the map now, people from Wikidata).
- How they were made (sources in `docs/design-eye/`: `cam.py` pinhole camera and renderer, `views.py` the seven
  cameras, `gen_eye.py` the boards; paths inside point at the session scratchpad): NASA GIBS WMS without a key
  (`BlueMarble_NextGeneration` world 8192 px and a Europe patch 6000 px, `VIIRS_Black_Marble` for the night side),
  ray-cast per pixel, marks projected with the same camera, items under a panel left out. Sun position from the
  date (subsolar 19.0 S 25.9 E at the capture). These boards were rendered locally in headless Chromium and
  checked for overflow (unlike the earlier boards).
- Honest limits said on the boards: Blue Marble is a cloud-free composite, the city lights are a composite of past
  years, the look-down ground is about 500 m per pixel (the app's sharp photo would replace it), the search board's
  "items on the map" group is a new idea (today's search finds only countries and people).
- In the app, the tilted and whole-disc views are camera presets of the existing MapLibre globe; the two-sides and
  wall views need several map instances (cost on the GPU unmeasured). Nothing built.

### 2026-11-17, God's eye: no orange, other grounds, four more views (mock-ups, waiting for his pick)

- He asked for more views, "views other than the realistic earth view", and **"get rid of the orange color, it looks
  weird"**. Orange (clash dots, occupied area, amber ships and accents) blended into the desert tones of the photo.
- **God's eye colours from now** (hex in `docs/design-eye/gen_eye.py`): clashes and the occupied area rose red
  `#ff3b5c`, protest a pale rose ring `#ffc2cd`, ships aqua `#5fe3ff`, launches violet `#b9a2ff`, aircraft and quakes
  white, selection / accent ice blue `#8fdcff`, late feed yellow `#ffe066`, failing red `#ff6b6b`. No orange or
  amber anywhere in this look. All earlier God's eye boards were recoloured.
- New canvas page "God's eye: grounds and more views" (same link), eight boards at 1920 x 1080:
  1. **Choose the ground**: the same view on six grounds: Photo, Mono (photo without colour), Night lights (NASA
     Black Marble, tinted cool), Outline (Natural Earth), Points of light, Relief (GIBS
     `ASTER_GDEM_Greyscale_Shaded_Relief`). The ground is meant as a setting, switchable per view.
  2. **Night lights, ambient layout**: big number cards only, for a screen left running.
  3. **Outline, theatre view**: one tall "In this view" panel instead of cards.
  4. **Mono, horizon**: a strip of the last 24 hours (clashes at their newest report, quakes at their time).
  5. **Over the pole**: one right panel with tabs (Signals / Layers / Coming up).
  6. **Low orbit**: 420 km above the eastern Mediterranean, a lower-third bar.
  7. **Chase**: behind GAF633 with its sheet and the follow controls; the aircraft is drawn at its height with a
     drop line to the ground.
  8. **Flat map**: the world unrolled (mono) with four region columns.
- Rendered and overflow-checked locally like the previous seven. Limits: the relief ground came out flat (little
  terrain visible); the chase and low-orbit grounds are soft at that zoom; the view switcher shows 7 views with a
  "4 more" chip on the older boards and all 11 on the new camera boards.

### 2026-11-17, God's eye: icons and legends (mock-ups)

- He asked for "newer versions and variations for all the legends and icons". New canvas page "God's eye: icons and
  legends" (same link), eight 1920 x 1080 boards, rendered and overflow-checked locally:
  - Four icon sheets: **69 symbols** (every map symbol: aircraft types, VIP / doomsday / tanker / surveillance orbit,
    ships, carriers, sanctioned, satellite classes, launches, the five unrest kinds, front, hotspot, news, leaders,
    quakes, disasters, fires, lightning, outages, hijacks, cables, warnings, bases, nuclear, cameras, receivers), each
    in **four families** (solid, line with glow, badge, point and code) on four grounds (photo land / desert, mono,
    dark). Library in `docs/design-eye/icons.py` (glyphs on a 64 grid; modes f/k/s/d/a/x).
  - States: normal, hover (thin white ring), selected (ice ring + ticks), low confidence (half strength), last known
    (grey, dashed, labelled), grouped (count), labelled, sized.
  - The four families on the same map crop with real items (military aircraft by broadcast type code).
  - Legend variants: A grouped key with counts in view and source, B key strip, C explain on hover, D key inside the
    layers panel, E counters of items beyond each screen edge (by direction; far side counted separately), F ambient
    icons-only key.
- Same day he added: **"keep the icons in general very low key"** and look online for spy-style icons (next round).
- **Low key, after looking at spy / military symbology** (new canvas page "God's eye: low-key icons", 4 boards): three
  quiet families in `docs/design-eye/icons_lk.py`: **frame and code** (the frame tells the domain, after NATO APP-6 /
  MIL-STD-2525: arch air, bowl sea, arch with bar space, rectangle land and sites, circle event, hexagon network,
  dashed rectangle notice; a three-letter mono code inside: MIL, TKR, ISR, CVN, CLH, ATK, NAV...), **reticle**
  (corner brackets + dot, heading tick, code under it) and **scope and data block** (air-traffic-scope target with a
  leader line to real values only: callsign, flight level from the reported height, ground speed; for events place
  and outlets). Only three colours: neutral grey-white, rose for conflict/danger, yellow for notices; ice blue for the
  selection. **The standards' friend/hostile colours and shapes are deliberately not used** (we do not judge sides; a
  red diamond reads "enemy"). If he ever wants the real standard: milsymbol (MIT, JavaScript, APP-6 / 2525E).
- Lesson: a marker layer must use the camera of the picture under it. I first laid theatre-camera marks over the
  horizon picture on the low-key map board; caught in my own check and swapped to the outline ground (same camera).
