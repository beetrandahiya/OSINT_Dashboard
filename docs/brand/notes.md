# World Watch identity: research notes and decisions (28 Nov 2026)

Files (all in this folder):
- `sheet.html`: the brand book (self-contained: inline SVG, renders embedded as PNG data, fonts embedded as WOFF2 subsets; no external JS, no network). Light and dark follow the system; `data-theme="light|dark"` on `<html>` forces one.
- `marks/NN-name.svg` (64 grid; the same SVG is the 1024 master) and `marks/NN-name-small.svg` (16/24 px variant).
- `lockups/NN-name.svg` (dark text, for light backgrounds) and `lockups/NN-name-dark.svg` (white text). Wordmarks are outlined paths (HarfBuzz shaping, so kerning is applied); no font needed.
- `renders/NN-name-{16,24,32,48,256}-{dark,light,dock}.png`: 1x device pixels, Chromium. 16 and 24 use the small variant.
- `tools/`: generator (`marks.py`, `directions.py`, `build.py`, `typo.py`), render scripts (`render.js`, `shot.js`, `secshots.js`).
- `review/`: my check screenshots (sheet at 1920x1080 light and 1440x900 dark, 4x pixel zooms).

## 1. App icon practice (sources read)

- Microsoft, "Construct your Windows app's icon": https://learn.microsoft.com/windows/apps/design/style/iconography/app-icon-construction
  Minimum set 16, 24, 32, 48, 256 px. At 100 % scale the taskbar draws 24 px; title bar, tray and context menus 16 px;
  at 200 % the taskbar draws 48 px. So 16-24 px is the size that matters on his PC.
- Microsoft Fluent 2 iconography: https://fluent2.microsoft.design/iconography and
  https://learn.microsoft.com/windows/apps/design/iconography/app-icon-design : base grid 48x48; below 48 px
  icons simplify detail for readability; draw specific sizes rather than scaling one. Hence one "small" variant per mark.
- Apple HIG, App icons: https://developer.apple.com/design/human-interface-guidelines/app-icons
  "Embrace simplicity ... express it in a simple, unique way with a minimal number of shapes"; avoid extremely thin
  lines and sharp corners at small sizes; include text only when essential; let the system add glows/highlights
  (no custom glows); provide unmasked square layers, the system rounds the corners (macOS 26 Liquid Glass, Icon Composer).
- Derived rules used here: one idea per mark, two or three shapes, strokes no thinner than 1 px at 24 px
  (about 2.7 units on the 64 grid; small variants use 6-11 units), solid plate for contrast on both dark and light
  taskbars, no text except the Footnote monogram, no gradients, no glows.

## 2. What makes the defence / intelligence identities work

- Palantir: the name is Tolkien's far-seeing stone (palan "far", tir "watch over"); the mark (orb on a stand) has stayed
  essentially unchanged since 2003; its strength is one literal idea, drawn once, never chased by trends.
  Sources (secondary, mixed quality): https://logos-world.net/palantir-logo/ , https://www.designrush.com/best-designs/logo/palantir
- Helsing (identity by Spin, London): the 'H' read as protection, off-black and off-white core with spot colours used
  sparingly, deliberately avoiding deep-tech clichés. https://spin.co.uk/work/helsing (read through a search excerpt).
- Anduril: built by an in-house team led by Jen Bucci (https://www.fastcompany.com/91527326/anduril-redesigning-future-of-warfare);
  its site uses black, mid grey, an olive green and a lime loading bar (read from anduril.com's own data).
- A critic calls the shared look of these companies "Defence Dun" (sameness of dark colours and typography):
  https://summaryjudgement.substack.com/p/anduril-vs-helsing-marketing-head-to-head . Lesson taken: restraint alone is
  generic; each direction here needs an idea that belongs to World Watch.
- Shield AI was not researched (time); nothing in the sheet depends on it.

## 3. Palettes (every hex in the sheet comes from one of these)

| Direction | Source | Values used | How verified |
|---|---|---|---|
| 01 Cocked Hat | Palantir Blueprint, https://github.com/palantir/blueprint/blob/develop/packages/colors/src/colors.ts | #111418 #1C2127 #F6F7F9 #5F6B7C #4C90F0 #2D72D2 (+#2F343C #ABB3BF #D3D8DE in UI) | file read directly |
| 02 Terminator | ESA: Deep Space #003247 (brand.esa.int, https://brand.esa.int/) and https://www.esa.int/assets/css/styles.css | #00121A #003247 #009BDB #E8E8E4 #9FB0BB #335E6F | stylesheet read directly; brand.esa.int refused this sandbox, Deep Space value from a search excerpt of it |
| 03 Quadkey | Bundesregierung styleguide, https://styleguide.bundesregierung.gov.de/sg-de/basiselemente/farben/petrol-2051434 | Petrol #007194 (Pantone 315), tints #338DA9 #66AABF #99C6D4 #CCE3EA, black | page read directly |
| 04 Great Circle | UN brand identity quick guide 2020, https://www.un.org/styleguide/pdf/UN_brand_identity_quick_guide_2020.pdf | UN Blue #009EDB (Pantone 2925), white, black | PDF refused this sandbox (403); value from a search quote of the PDF, matching brandcolorcode.com which cites it |
| 05 Plot | NGA website stylesheet, https://www.nga.mil/assets/css/main.css | #0D2F4B #1B1B1B #F0F0F0 #2FA3AA #154E7D #DFE1E2 | read directly; a website, not a brand guide |
| 06 W Trace | Anduril website data, https://www.anduril.com/ | Black #010101, Mid Gray #8E9291, Green #505544, lime #DFF140 (loading bar) | read directly; a website, not a brand guide |
| 07 GMT Bezel | NASA brand guidelines, https://www.nasa.gov/nasa-brand-center/brand-guidelines/ | NASA Blue #0032A0 (PMS 286), NASA Red #E4002B (PMS 185) | read from NASA's colour chart image on that page |
| 08 Contact | NATO Visual Identity Guidelines 2016, https://www.act.nato.int/wp-content/uploads/2023/06/NATO-VIGs-2016-en.pdf | #004990 (PMS 280), #118ACB (PMS 2718), black | PDF read directly (colour table) |
| 09 Shells | GOV.UK Design System, https://design-system.service.gov.uk/styles/colour/ | #1D70B8 #0B0C0C #0F385C #CA3535 #FFFFFF | page read directly |
| 10 Footnote | Canada.ca design system, https://design.canada.ca/styles/colours.html | #26374A #284162 #333333 #D3080C #FFFFFF | page read directly |

Also verified but not used: EU emblem Reflex Blue #003399 and Yellow #FFCC00 (Regulation 821/2014 Annex II,
https://www.legislation.gov.uk/eur/2014/821/annex/II).
Not found as published values: NRO, NGA's brand guide, US Space Force (AFI 84-105 "USSF Colors" refused this sandbox),
Bundeswehr, BND. No orange anywhere; Blueprint's and EU's warm colours were left out.
Each section of the sheet lists the UI mixes it uses in mock-ups (e.g. #00303F) and says they are mixes, not published colours.

## 4. Real values used in devices

- Munich, 28 Nov 2026 (NOAA solar equations: declination -21.3°, equation of time about +12 min, refraction -0.833°):
  solar noon 11:02 UTC, sunrise 06:39 UTC (07:39 CET), sunset 15:25 UTC (16:25 CET). Used by the GMT bezel.
- Subsolar point at 12:00 UTC: 21.3 S, about 3 W. The Terminator mark is the day/night line for 28 Nov 2026 at
  08:56 UTC (subsolar longitude 43 E), twilight to -12° (the app's own fade), -18° in the small variant.
- Munich quadkey (Web Mercator, 48.137 N 11.575 E): 1-2-0-2-3-0. The mark shows five levels, the small variant three.
- RCH4992 (C-17, FL306, 535 kt, 063°) is from the project's real capture of 17 Nov 2026 (CLAUDE.md).
- GLEIF facts in the Footnote device (Rosneft Deutschland's direct parent PJSC Rosneft; Rosneft's own parent a
  reporting exception) are from the project's GLEIF probe of 28 Nov 2026 (CLAUDE.md), not re-checked here.
- Everything else in device mock-ups (feed counts, ownership chain names, '12 connections', 'Contacts 214') is marked
  as an example in the sheet; the activity trace shape is labelled illustrative.

## 5. The ten directions

| # | Name | One sentence | Palette | Wordmark |
|---|---|---|---|---|
| 01 | Cocked Hat | Three bearings never meet in one point; the small triangle between them is where the truth lies, and its size says how sure you can be. | Palantir Blueprint | Archivo Expanded 600 caps |
| 02 | Terminator | The shape night makes on the flat map, computed for one real moment; the brand's main line is a fact. | ESA | Space Grotesk 600 |
| 03 | Quadkey 1-2-0-2-3 | Munich's tile address: split the world in four, take one, repeat. | Bundesregierung | Barlow Semi Condensed 600 caps |
| 04 | Great Circle | The straight line on the flat map is not the shortest way; the curve is. | UN | Sora 600 |
| 05 | Plot | Radar history dots: only positions someone actually reported, the newest one leading. | NGA | Public Sans 700 caps |
| 06 | W Trace | The initial drawn as a signal burst on a quiet baseline. | Anduril | IBM Plex Mono 600 caps |
| 07 | GMT Bezel | A GMT watch tells the time in two places at once; World Watch tells you what happens everywhere at once. | NASA | Michroma caps |
| 08 | Contact | Hull down: the mast is the first sign of a ship beyond the curve of the Earth. | NATO | Big Shoulders Display 800 caps |
| 09 | Shells | Open each shell until you reach the solid one: the person who really owns it. | GOV.UK | Libre Franklin 700 |
| 10 | Footnote | W with its reference mark: nothing appears without a source. | Canada.ca | Fraunces 600 |

Each has: mark + small variant, lockup, taskbar/Dock renders, colour system with shares, type, two graphic devices
(dark and light), top bar dark and light, A4 case-file cover, splash. Honest weaknesses per direction are in the sheet.

Small-size test results (from the 4x pixel zooms): readable at 16 px: 01, 04, 06, 09 (best: 06 and 09); readable but
quiet: 02, 03, 05, 10; weakest: 07 (reads as a ring with a red dot, gauge-like) and 08 (a thin tick on a blue tile).
Nothing turned to mush, but 07 and 08 rely on the story.

Dropped after the test: Racetrack (paperclip / link icon), Two hemispheres (cartoon eyes), Date line (random-looking),
Morse WW (bulleted-list icon), Null Island (crosshair; the owner rejected crosshairs before). Redrawn: Great Circle
(first version read as a handbag), Plot (paintbrush), GMT (speedometer), Cocked Hat (App Store 'A', fixed by a 25° turn),
Contact (white sea vanished on the light taskbar).

## 6. Recommendation (top 3)

1. **Cocked Hat** (Palantir Blueprint). The best idea: it puts the project's hard rule (sources, honesty about how sure
   we are) into geometry, it has a story worth telling once, and it is stark monochrome plus one accent. Its devices
   (fix badge: 1 / 2 / 3 sources) are useful UI, not decoration. Weakness: an asterisk-with-a-dot at 16 px.
2. **W Trace** (Anduril). The most legible at 16 px and the most 'defence tech'; doubles as a monogram; its device can be
   real data (counts per 15 minutes). Weakness: sits in the waveform/heartbeat icon family.
3. **Terminator** (ESA). The calmest and most 'world'; the only one whose line is a computed fact every time it is drawn,
   and Space Grotesk already matches the app. Weakness: a light hump at 16 px, can read as a bell curve.
Runners-up: Shells (best for the Connections page, very clear) and Quadkey (most personal).

## 7. Not verified / limits

- UN Blue and ESA Deep Space were confirmed only through search excerpts of the official pages (both refused direct
  download from this sandbox). NGA and Anduril values are from their websites' code, not brand guides.
- Renders are Chromium at 1x. Windows downscales ICO/PNG assets with its own filter, and macOS applies its own mask and
  Liquid Glass effects; final icons should be exported per size (16/24/32/48/256 PNG in an .ico, and an Icon Composer
  file for macOS) and checked on the real taskbar and Dock.
- Microsoft Word's icon is a white W on blue: the Footnote mark sits close to it on a Windows taskbar.
- Michroma (GMT) has a single weight; Big Shoulders and Fraunces are display faces chosen for character, not for being
  any agency's typeface.
- I did not open the sheet in Safari; it was checked in headless Chromium at 1920x1080 and 1440x900, light and dark,
  with no horizontal overflow and no console errors.
