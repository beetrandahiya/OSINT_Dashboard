# World Watch: design review and redesign proposal (area: design)

Screenshots: `/tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/design/shots/` (written below as `shots/…`).
All at 1512x982, Chromium, captured 2026-11-17 against the shared server. Scripts: `design/cap1.js … cap6.js`, `design/lib.js`.
Limits: headless software GL, so no 3D terrain shots. The chase camera bar did not open in the script (the click missed), so the
follow controls are judged from the code (`main.js` 317-372). Dark mode was captured for the default globe only. Cards are light.

---

## Part 1. Why it feels like a mess (in plain words)

### 1. Forty switches in one heap, and most of them start on
The sidebar holds 40 layer buttons ("chips") in one wrapped block, in no order you can see. Nearly half the sidebar height
goes on them before you reach any news. 31 of the 40 start switched on, so a first look is everything at once: news circles,
fires, aircraft, satellites, cables, airspace, nuclear sites, leaders' names, all together.
Some buttons are really options of another one ("Unrest, one outlet" belongs to Protests; "GPS" and "GPS, last hour" are one
thing at two times; "Photo", "Live photo" and "Sharp photo" are three ground pictures that should not be on together).
The number beside each button means different things: a count ("News 2,413"), a date ("GPS 16.11."), a clock time
("Rain 00:50"), an index ("Aurora Kp 0.7"), or nothing ("Night"). Buttons with 0 stay on and take space ("Hotspots 0",
"Breaking 0", "Orbits 0", "Doomsday 0"); Hotspots, the most important one, is the first button and is usually empty.
Shots: `shots/04-sidebar-light.png`, `shots/01-default-light.png`.

### 2. Red means ten different things
News, Breaking, Front line, Airspace, Internet hijacks, Doomsday planes, Sanctioned, Cables, GPS last hour and Hotspots/Disasters
are all red or pink. On the map the airspace warning areas fill Russia, Ukraine, the Middle East and North Africa pink, the front
line's occupied area is red on top of that pink, cables are red lines, news is red circles. You cannot tell at a glance which red
is which, and the pink wash makes half the map look "alarming" all the time, which is decorative in effect even though the data is real.
Shots: `shots/20-card-front-light.png` (Russia pink from airspace, Ukraine red from the front, red cables, red news),
`shots/20-card-unrest-light.png`, `shots/20-card-warships-light.png`.

### 3. Panels everywhere, each with its own rules
On screen at once: the sidebar (left), the legend (floating in the middle of the map), a second satellite legend (a text row at
the top of the map on the globe), the markets strip (bottom middle), the feeds card (bottom right), the zoom/compass buttons
(floating mid-right, not attached to anything), the map credits (a pill above the markets strip), the detail card (top right),
the follow bar (when following), the loading bar. Four of them have their own minimise chevron. The open legend covers the
centre of the map where the globe is; the globe at its opening zoom is squeezed between the sidebar and the legend.
Shots: `shots/02-globe-default-light.png`, `shots/05-globe-default-dark.png`.

### 4. Every card is built differently
Cards are long (aircraft 1,100 px, satellite 1,370 px, leader 1,600 px, news place 5,570 px) inside a box about 580 px tall,
because the feeds card holds the bottom of the right column. The facts you came for come late: on an aircraft card the altitude and
speed sit under the photo, the title, a full-width "Follow it" button and a register block that explains where the register comes from.
Buttons and links are mixed with no order: "Country dossier" (grey button) next to "Open this country on IODA" (blue link
that wraps onto the next line); bases and nuclear sites have three stacked buttons of different widths whose labels are whole
questions ("Which spy satellites passed over in the last 24 hours?"). On ship and warship cards the "Search photos of it" links
and the "no picture" note sit above the title, under the close/minimise buttons, which overlap that text. The source line is
always at the bottom (good), but it is a paragraph of fine print, and on bases and nuclear cards it describes both layers.
Shots: `shots/20-card-vip-light-full.png`, `shots/20-card-military-light.png`, `shots/20-card-ships-light-full.png`,
`shots/20-card-warships-light.png`, `shots/20-card-bases-light-full.png`, `shots/20-card-outages-light-full.png`,
`shots/20-card-satellites-light-full.png`, `shots/20-card-airspace-light-full.png` (monospace block of advice text).

### 5. The list does not answer "what matters now"
"Latest" is sorted by time only. News places all share the same 15-minute slot, so the top of the list is whatever city has the most
outlets: "Powerful Storms To Slam Weather" (Washington), "United Airlines resolves tech…", "Fans cheer as popular online…". The
geopolitical items he cares about (front changes, navy warnings, carriers, VIP jets airborne) drown under them. When launches exist,
"Coming up" pushes everything below the fold. Shots: `shots/01-default-light.png`, `shots/10-combo-light.png`,
`shots/30-follow-light.png`.

### 6. The map labels compete with the place names
Leaders' names (Vladimir Putin, Benjamin Netanyahu, Narendra Modi, Paul Kagame…), test sites ("Totskoye range", "Kapustin Yar"),
carrier names and aircraft callsigns are drawn in the same weight as country and city names, so at world zoom the map reads like a
word cloud. 12,049 military-base dots and 15,911 fire dots, where switched on, turn whole continents brown or orange.
Shots: `shots/01-default-light.png`, `shots/10-combo-light.png`.

### 7. Health and sources are in the wrong place
"1 of 45 feeds late" is a big panel in the bottom right, but it does not say which layer you are looking at is affected; the open
list has truncated names, and shows a removed layer ("Disaster imagery (Maxar…) data 334 d ago") in green. Meanwhile layers on the
map have no age next to them (the chip shows a count instead). Shots: `shots/03-feeds-open-light.png`.

### 8. Actions are hard to discover
Follow, Dossier, Country dossier, Spy passes, "Which satellites photographed it", "Look at it in the sharp photo", "Look down from it"
exist, but each card shows a different subset in a different place and style. Tilting needs right-drag (only said in a tooltip).
The Munich switch, the Lookup link and the person/country search sit in the sidebar head with the map/globe switch, so the top of the
sidebar is four rows of controls before any content. In the Munich view the legend still explains the Ukraine front line and protests.
Shots: `shots/40-munich-light.png`, `shots/52-find-light.png`.

What already works and must stay: the globe's look in dark mode (`shots/05-globe-default-dark.png`), the panel material and type,
the person and country dossiers (`shots/50-dossier-person-light.png`, `shots/51-dossier-country-light-full.png`: the signal tiles
with source and age under each value are the best pattern in the app and should become the pattern for cards too), the honesty of
every card's source text.

---

## Part 2. Information architecture

### 2.1 Layer groups (40 chips become 9 groups, 30 switches)

| Group | Layers (switch: sub-options) | Colour family |
|---|---|---|
| **Now** | Hotspots · Breaking · Leaders today | system red (only group allowed pure red) |
| **Conflict** | Protests and clashes (sub: "include one-outlet reports") · Front line, Ukraine · Navy warnings · Airspace warnings · GPS interference (sub: Last hour / Yesterday) | brown / orange / amber; airspace as outline, not fill |
| **News** | News places | grey-blue circles (not red) |
| **Air** | Aircraft · Military (sub: orbits, tankers) · VIP and government jets · Doomsday planes | indigo / purple / gold |
| **Sea** | Ships · Warships and US carriers · Sanctioned ships and aircraft | brown / dark grey / magenta outline |
| **Space** | Satellites · Launches | green / teal |
| **Sites** | Military bases (with military areas) · Nuclear sites · Heads of state (the old "People") | earth tones, small |
| **Networks** | Internet outages · Internet hijacks · Undersea cables · Listening stations · Public cameras | grey / cyan |
| **Earth and sky** | Earthquakes · Disasters · Fires · Rain · Lightning · Aurora · Night | orange / pink / blue |
| **Ground picture** (choose one) | Map · Daily photo · Live photo · Sharp photo | radio buttons, not switches |

Rules: one colour family per group; red is kept for "Now" (and the selection of a warning level inside a card); airspace shows as
an outlined region with a light hatch only for "do not operate", so it stops washing half the map pink. The legend colours are
generated from the same table (today they are copied by hand, `legend.js` line 1-2 warns about it).

### 2.2 Views (presets)
A view is just a saved set of switches plus a camera; picking a view replaces the switches; changing any switch marks it "Custom".

| View | Switched on | Camera |
|---|---|---|
| **Overview** (opening view) | Hotspots, Breaking, Leaders today, Protests (2+ outlets), Front line, Navy warnings, Airspace warnings, Military, VIP jets, Doomsday, Warships, Earthquakes (M5+ only on the map), Outages, Night | globe, whole world |
| Conflict | Overview + GPS last hour, Military orbits/tankers, Bases, Nuclear, Sanctioned | globe, last conflict area viewed |
| Air | Aircraft, Military, VIP, Doomsday, GPS last hour, Airspace | flat, around the screen centre |
| Sea | Ships, Warships, Sanctioned, Navy warnings, Cables | flat |
| Space | Satellites, Launches, Night, Aurora | globe zoomed out |
| Internet | Outages, Hijacks, Cables | globe |
| Earth | Earthquakes, Disasters, Fires, Rain, Lightning | flat |
| Munich | Aircraft, Rain, Lightning + the Munich panel | flat, Munich |
| Custom | whatever he last set | last camera |

### 2.3 One search for everything
The search field at the top of the sidebar searches, as you type: countries (open dossier), people (dossier), places
(fly there), and items on the map now (callsign, registration, ship name/IMO, satellite name/NORAD number, cable name, base name),
plus layer names ("tankers" offers the switch). Results grouped by kind, at most 3 per kind, Enter opens the first.

### 2.4 The list becomes "Now"
Three sections, each capped and expandable: **Signals** (hotspots, breaking, front changes, new navy warnings, new airspace
warnings, airborne doomsday/VIP-government jets, satellite manoeuvres, M5+ quakes near test sites); **Coming up** (launches,
max 2 rows, "and N more"); **Latest** (everything else from switched-on layers, by time, news collapsed to the top 5 places with
"all news places" at the end). No scores: the order inside Signals is by time, the section is chosen by kind (a fixed, stated rule).

---

## Part 3. Layout

### 3.1 Main screen

```
+--------------------------------------------------------------------------------------------------+
| +--------------------------+                                              +---+  +-------------+ |
| | (search everything    )  |                                              |Lay|  |  CARD       | |
| | [Overview v]  2 late  ⚙  |                                              |ers|  |  (see 3.2)  | |
| |--------------------------|                                              |Glb|  |             | |
| | SIGNALS                3 |                                              |3D |  |             | |
| |  ● Front: change near …  |                MAP / GLOBE                   |Mun|  |             | |
| |  ● Navy warning NAV I …  |                                              +---+  |             | |
| |  ● VIP: SPAR18 airborne  |                                              |+ |   |             | |
| | COMING UP              2 |                                              |- |   |             | |
| |  ↑ Falcon 9 · in 2 d     |                                              |N |   |             | |
| | LATEST                   |                                              +--+   |             | |
| |  … rows …                |                                                     +-------------+ |
| |                          |   [Following ER44  ↺ ↻ N  Behind  Stop]  (only when following)     |
| | S&P −1.9% DAX −0.6% ...  |                                                     credits ⓘ        |
| +--------------------------+                                                                       |
+--------------------------------------------------------------------------------------------------+
```
- **Sidebar (left, 360 px):** search; a row with the View picker, the feed-health word ("All feeds OK" / "2 late", opens
  Settings › Data) and the Settings gear; then the Now list. Markets become one quiet line at the foot of the sidebar
  (or off, see Settings). Minimising leaves only the search field (Apple Maps style).
- **Map controls (right edge, one vertical glass stack, Apple Maps style):** Layers (opens the layer panel), Map/Globe toggle,
  3D, Munich (home), then zoom +/− and compass in a second stack below. This replaces the header segmented controls and the
  floating NavigationControl in the middle of the screen.
- **Card (right, under/left of the controls, 360 px, full height when needed):** the feeds card no longer shares the column.
- **Legend:** no permanent panel. Each layer row in the layer panel shows its symbols; plus a small "Key" button in the
  controls stack that opens a popover listing only the layers whose symbols are on screen now. The satellite orbit-class row at the
  top of the globe moves into that key.
- **Follow bar:** bottom centre, one glass capsule, same buttons as today; the card's Follow button turns into "Stop following".
- **Loading bar:** keep, on the sidebar's top edge only.
- **Lookup:** stays its own page, reached from Settings' header and from the search ("Look up a person…").

### 3.2 One card anatomy

```
+------------------------------------+
| [ photo / still / picture, 16:9 ]  |  optional; credit in a 11px line under it; "no picture" = one grey line, never a box
| EYEBROW · layer colour dot   ⌄  ✕  |  kind and layer
| Title                    [flag]    |  22 px
| one line: where / what it is       |
|------------------------------------|
| KEY FACTS: 2-4 tiles in a row      |  the live or headline numbers, each with its own small age
| [ 11,525 ft ] [ 285 kt ] [ 176° ]  |
|------------------------------------|
| ACTIONS: one row of pill buttons   |  same order everywhere; only the ones that apply
| (Follow) (Dossier) (Country) (From |
|  above ▾) (Sharp photo) (Open ↗)   |  "From above" = spy passes + who photographed it
|------------------------------------|
| DETAILS: grouped key-value lists   |  ≤ 6 rows open; "More" folds the rest
| LISTS: headlines, signals, units   |  ≤ 5 shown, "Show all N"
|------------------------------------|
| ● Source · age                     |  one line, dot = feed state (green/amber/red/grey)
| How this is worked out ▸           |  the long caveat text, folded
+------------------------------------+
```
Action order (fixed): Follow · Dossier · Country · From above · Sharp photo · Look down from it · external link(s) last.

**Worked examples**

Aircraft (military, live):
```
Military helicopter · Military        ⌄ ✕
C6518  [US]
Aérospatiale MH-65D Dolphin · US Coast Guard
[ on the ground ] [ 13 kt ] [ 18 s ago ]
(Follow) (From above ▾) (adsb.fi ↗)
Details: Registration 6518 · Transponder AE266C · Squawk 1200 · Accuracy 3 m
         Route: no published route (military)
● adsb.fi · 14 s ago · drawn 40 s behind real time
How this is worked out ▸ (register source, playback delay, path source)
```
Satellite:
```
Science satellite · Satellites        ⌄ ✕
HST  [US]
Low Earth orbit · 470 km · 28.5°
[ 470 km ] [ 27,478 km/h ] [ 94 min orbit ] [ orbit data 7 h old ]
(Look down from it) (From above ▾ = passes it made) (CelesTrak ↗) (watched.earth ↗)
Details: Over 8.3° S 124.3° W · Sees 4,800 km circle · Catalogue 20580 · Launched 1990
What it is (UCS, May 2023): Space science · Government · ESA/NASA
● CelesTrak · fetched 16 min ago   ● UCS database · May 2023
How this is worked out ▸
```
News place (today 5,570 px tall):
```
News place · News · last 6 h          ⌄ ✕
Jerusalem  [IL]
49 outlets · newest 10 min ago
[ 49 outlets ] [ 31 headlines ] [ 12 languages ]
(Country) (From above ▾)
Top stories (same story grouped, agency copies once): 5 rows, picture on the first
Show all 31 headlines ▸
● GDELT · fetched 12 min ago
How this is worked out ▸
```
The lead picture is the first story's own picture, not any picture in the window (today a brain diagram from a neuroscience
story leads the Jerusalem card: `shots/20-card-news-light.png`).

Base / nuclear site:
```
Military base · Sites                 ⌄ ✕
Marine Corps Base Hawaii  [US]
United States Marine Corps
(Sharp photo) (From above ▾) (Country) (Wikidata ↗)
Details: Where 21.44° N 157.75° W · Kind base · Also in OpenStreetMap: yes
● Wikidata · OSM (≈2 months behind) · read 18 min ago, weekly
How this is worked out ▸ (only the bases text, not the nuclear one)
```

### 3.3 Layer panel (opened from the Layers control; a popover/sheet, 420 px, over the map's right side)

```
+-----------------------------------------------+
| Layers                       View: Overview v |
| (filter layers…)                              |
|-----------------------------------------------|
| NOW                                           |
|  [x] Hotspots            0   · 4 min    (i)   |
|  [x] Breaking            0   · 12 min   (i)   |
|  [x] Leaders today      15   · 12 min   (i)   |
| CONFLICT                                      |
|  [x] Protests and clashes 152 · 2 min  (i)    |
|       [ ] include one-outlet reports (388)    |
|  [x] Front line, Ukraine  8 changes · 25 min  |
|  [x] Navy warnings        1  · late ⚠          |
|  [x] Airspace warnings   84  · 27 min         |
|  [ ] GPS interference  (Last hour | Yesterday)|
| AIR …   SEA …   SPACE …   SITES …             |
| NETWORKS …   EARTH AND SKY …                  |
| GROUND PICTURE  (o) Map ( ) Daily ( ) Live ( ) Sharp
+-----------------------------------------------+
```
Each row: switch, name, count (only a count; dates and times move to the age column), the feed age, a state mark when late or
failing, and (i) which unfolds that layer's legend symbols and its source line. A group header has its own switch (all on/off) and
a count of how many of its layers are on. Groups fold; the fold state is remembered.

### 3.4 Map label rules
- Country and city names win. Leader names only from zoom 4, carrier and test-site names from zoom 4, callsigns from zoom 7.
- Dense point layers (bases 12k, fires 16k, cameras 7k) are drawn as small faint dots below zoom 5 and are not in Overview.
- Airspace: outline plus small FIR code; fill only for "do not operate", at 10 %.
- News: neutral circles (grey-blue) so red keeps its meaning.

---

## Part 4. Settings sheet

Opened from the gear in the sidebar. An Apple-style sheet over the map, 640 px, sections on the left, controls on the right.

```
+-------------------------------------------------------------+
| Settings                                               Done |
|-------------+-----------------------------------------------|
| General     |  Opening view      [ Overview          v ]    |
| Map         |  Opening camera    (o) Same as the view       |
| Aircraft    |                    ( ) Where I left off       |
| Units & time|  Appearance        (o) Follow the system      |
| Motion      |                    ( ) Light  ( ) Dark        |
| Data & keys |  Markets line      [x] show at the foot       |
| Privacy     |  Home place        Munich (48.14, 11.58)  Edit|
+-------------+-----------------------------------------------+
```

| Section | Setting | Default | Need? |
|---|---|---|---|
| General | Opening view | Overview | **real** |
| | Opening camera: view's / where I left off | where I left off | real |
| | Appearance: system / light / dark | system (HIG; a forced mode only if he asks) | nice |
| | Markets line on/off | on | real (he asked for a small strip; lets him hide it) |
| | Home place (the "Munich" button and view) | Munich | nice |
| Map | Shape: Map / Globe | Globe | real (already remembered; here it is visible) |
| | 3D terrain and buildings | off (on is heavy) | real |
| | Terrain height ×1 | 1.0 (fixed: models fly at true height) | no, show as text only |
| | Place-name size: normal / larger | normal | nice |
| | Labels on the map: names of leaders, ships, callsigns | on | real (the clutter switch) |
| | Ground picture default | Map | real |
| Aircraft | 3D models: on / off | on | **real** (performance, taste) |
| | Models from zoom | 7 | nice |
| | Playback delay (live / military) | 15 s / 40 s, shown read-only with the reason | no (keep fixed; shown so he knows) |
| | Callsign labels: all / selected only / none | all from zoom 7 | real |
| | Show world snapshot aircraft (20 min old) | on | real |
| Units & time | Altitude ft / m | ft (aviation) | real |
| | Speed kt / km/h | kt with km/h beside it (today's behaviour) | real |
| | Distance km / NM | km | nice |
| | Time zone: local (Europe/Berlin) / UTC | local, with UTC on hover | **real** (OSINT sources are UTC) |
| | Date format | 17 Nov 2026 | no |
| Motion and performance | Low-power mode: no hijack streaks, no gliding playback (positions jump per report), no satellite canvas labels, layers refresh at half rate, 3D models off | off | **real** (M1 / battery / Safari) |
| | Animations (fly-to, streaks) | follow system Reduce Motion | real |
| | Satellite labels on the globe | on below 160 in view | nice |
| Data and keys | Feed health: the full feeds list (today's feeds card) grouped like the layers, with state, source, last fetch, next fetch, error | – | **real** |
| | Keys: aisstream (world ships), OpenSanctions, Cloudflare Radar, Windy, Brave, planespotters contact address: each shows *present / missing*, what it unlocks, where to get it, and the file it goes in (`data/aisstream-key.txt`, `data/opensanctions-key.txt`, `data/cloudflare-token.txt`, `data/windy-key.txt`, `data/brave-key.txt`, `data/contact.txt`, all in the repo-root `data/`). Never shows the key; never accepts a key typed in the page (files only, as now). | – | **real** |
| | Storage: size of `data/`, lookup db, "clear caches" | – | nice |
| Privacy | What leaves this machine, per service: headline text to Google Translate; the contact address in the User-Agent to planespotters and Wikimedia; identifiers to the lookup tools only when he presses Scan; all map data fetched by the server, his browser talks only to our server and the map/tile hosts (OpenFreeMap, NASA GIBS, Esri, EUMETSAT, RainViewer, Mapterhorn) | – | real (read-only page) |
| | Machine translation of headlines on/off | on | real |
| | Lookup page reachable from other machines | off (`WW_LOOKUP_REMOTE`), shown read-only | nice |

Storage of settings: per-browser conveniences (fold states, units) in localStorage as now; settings that change what the server
fetches (none proposed) would need a server endpoint, so none are proposed.

---

## Part 5. Three overall directions

**A. "Apple Maps, tidied" (recommended).** Keep today's layout family: sidebar left, card right, glass panels. Change: grouped layer
panel behind a Layers control, views, one search, Now list in three sections, one card anatomy, controls stack on the right, legend
inside the layer panel, feeds into Settings. Panels on screen by default: 2 (sidebar, controls) plus the card when something is
picked. Cost: moderate (`main.js` chips and list, `app.css`, a `card()` helper in `util.js` that every layer's `detail()` uses,
`legend.js` merged into the layer table). Risk: every layer's `detail()` must be rewritten to the helper; doable one layer per slice.

**B. "Situation room".** Fixed three columns: briefing on the left (Signals with more text), map in the middle, card always open
on the right with a pinned "watch list" of places/aircraft. Dense, god's-eye feel, good on the external display. Cost: higher;
the map gets narrower on the laptop (1512 px leaves ~800 px of map). He chose Apple Maps over the "Ops room" mock-up on 2026-11-14,
so this would go against an earlier choice; worth showing only as a mode for the big screen.

**C. "Map first".** Everything collapses into a floating search bar top-left (Apple Maps compact) and a bottom "Now" ticker; the list
opens as a sheet only when asked. Calmest and most cinematic on the globe. Loses the always-visible list he uses for quick checks,
and a ticker invites motion he did not ask for.

**Recommendation: A**, with C's minimised sidebar (search field only) as the "minimise" state, and B's watch list as a later idea.

### Build order (slices he can test)
1. Layer panel with groups, sub-options, ground-picture radio, counts vs ages; colour families; airspace outline. (Biggest calm-down.)
2. Views + opening view + Settings sheet (General, Map, Units, Data & keys incl. feed health). Remove the feeds card.
3. Card helper and the four worked examples (aircraft, satellite, news, base), then the rest layer by layer.
4. Now list sections; search across layers; key popover; controls stack; label zoom rules; low-power mode.

---

## Part 6. Screenshots per problem

| Problem | Screenshots |
|---|---|
| 1 Forty chips, most on, mixed numbers, empty ones first | `shots/04-sidebar-light.png`, `shots/01-default-light.png` |
| 2 Red everywhere, airspace pink wash | `shots/20-card-front-light.png`, `shots/20-card-unrest-light.png`, `shots/20-card-warships-light.png`, `shots/20-card-news-light.png` |
| 3 Panel sprawl, legend over the globe, second legend on top | `shots/02-globe-default-light.png`, `shots/05-globe-default-dark.png`, `shots/03-feeds-open-light.png` |
| 4 Card anatomy: length, order, overlapping buttons, mixed buttons/links | `shots/20-card-vip-light-full.png`, `shots/20-card-military-light.png`, `shots/20-card-ships-light-full.png`, `shots/20-card-warships-light.png`, `shots/20-card-bases-light-full.png`, `shots/20-card-nuclear-light-full.png`, `shots/20-card-outages-light-full.png`, `shots/20-card-satellites-light-full.png`, `shots/20-card-airspace-light-full.png`, `shots/20-card-leaders-light-full.png`, `shots/20-card-news-light-full.png` |
| 5 List led by unrelated news | `shots/10-combo-light.png`, `shots/30-follow-light.png` |
| 6 Labels and dense dots | `shots/01-default-light.png`, `shots/10-combo-light.png` |
| 7 Feed health detached, removed layer listed | `shots/03-feeds-open-light.png` |
| 8 Discoverability / Munich legend mismatch | `shots/40-munich-light.png`, `shots/52-find-light.png` |
| Good patterns to reuse | `shots/50-dossier-person-light.png`, `shots/51-dossier-country-light-full.png`, `shots/05-globe-default-dark.png`, `shots/20-card-cameras-light-full.png` |
| Lookup page (own look, fine; title tiles match the dossier pattern) | `shots/60-lookup-light.png` |

## Bugs tripped over (one line each)
- Unrest card article ages read "in 234482884 d": `a.time` is a GDELT slot string ("20261116100000") passed to `ago()` (`unrest.js:73`); also against the "file names are not times" lesson.
- Person dossier says "In the news, 6 h: 0 outlets" for Netanyahu while his Leaders-today card says "Articles naming them: 37 outlets" (`shots/50-dossier-person-light.png` vs `shots/20-card-leaders-light-full.png`).
- `ww-pick` is listened for on `window` (`main.js` 250); the brief's `document.dispatchEvent` does not reach it (events from document do not bubble to window unless `bubbles: true`).
- Close and minimise buttons overlap the "no photo / no picture" line on aircraft, ship and warship cards (`shots/20-card-military-light.png`, `shots/20-card-warships-light.png`).
- Ship cards put "Search photos of it / ShipSpotting photos" above the eyebrow and title (`shots/20-card-ships-light-full.png`).
- Follow (chase camera) is offered for a moored ship (0.0 kn) and a helicopter on the ground.
- Front-line area card: title "Status unknown (contested)" and subtitle "Unknown status" repeat each other (`shots/20-card-front-light.png`).
- Bases and nuclear cards share one source paragraph describing both layers (`shots/20-card-bases-light-full.png`).
- Feeds list shows the removed "Disaster imagery (Maxar)" feed as green with "data 334 d ago" (`shots/03-feeds-open-light.png`).
- Legend stays on the Ukraine front line and protests in the Munich view (`shots/40-munich-light.png`).
- Screenshots of the default view needed >30 s in headless (main thread busy with all 31 default layers); the perf auditor should confirm the cost of the default layer set.
