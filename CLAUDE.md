# World Watch: project log

Personal live OSINT dashboard: a map of what is happening in the world and around Munich,
later a lookup tool for people and organisations from public sources. This file is the
single source of truth for any future session. Read it fully before doing anything.

## Status

**2026-11-14: interview and research done, plan proposed, waiting for the owner's go.
No application code exists yet.** Next step after the go: the feed proof (see Plan).

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

Nothing to run yet.

## Cancelled / ruled out

- Forking God's Eye View, ShadowBroker or worldmonitor (size, licence, wrong map engine). 2026-11-14.
- Static-site hosting (CORS and history). 2026-11-14.
- ACLED, Stooq, GDELT GEO API, own ADS-B hardware. 2026-11-14.
