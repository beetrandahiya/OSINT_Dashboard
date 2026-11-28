# Real Earth Suite: direction A, denser, on all four pages (28 Nov 2026)

Owner: "can you show A but with more dense information, and all the 4 panels, map, connections, investigate, sources".
Published page: https://claude.ai/artifact/48Py7PMcZ4wqd848uB9S6d (copy: `real-earth-suite.html`). Each board starts dark with
a light switch above it; panels are see-through Porcelain (no blur) over the NASA photo Earth.

- **Map**: Dense layout with a column on each side. Left: World (top protests/clashes by outlets, 24 h), Watch (front line,
  IODA shown as a dead feed, USNI carriers marked late, airspace "do not fly", M5+ quakes), Markets (delayed, unofficial).
  Right: Kharkiv card, Now in this view, 12 layer tiles with each feed's state (failing ones outlined red with "from <date>").
  Map: GPSJAM hexes (27 Nov), EASA/FAA airspace outlines, TeleGeography cables, DeepState occupied area, news dots, unrest
  symbols, military aircraft with callsigns, Digitraffic ships. Camera as the God's eye theatre, principal point at x 920.
- **Connections**: live search "Rosneft" (28 results: GLEIF 6, Wikidata 10, Offshore Leaks 3, sanctions 9) and PJSC Rosneft
  built live at 14:49 UTC (GLEIF 2 + Wikidata 28 holdings, 24 loaded; a US patent Wikidata lists as owned by it left out),
  chain end (GLEIF NO_KNOWN_PERSON), OpenSanctions match by LEI (8 lists), ICIJ ROSNEFT INC. as "same name only".
- **Investigate**: specimen case on reserved test identifiers (test@example.com, example.com), dossier from the 12:38 UTC checks,
  username self-test of this server (397 of 690 trusted), dated timeline.
- **Sources**: all 45 feeds as the cloud test server logged them at 03:08 UTC (37 ok, 2 late, 3 failing, 2 not set up,
  1 on request; 495 MB and 852 requests in 24 h), OpenSky's failing feed selected with its last tries; keys table.

Tools need the session scratchpad (`gv/cam.py`, NASA textures, `lang/` mock and glyph modules). Checked in headless Chromium
(1440 light/dark, 400; boards at 1920 in dark and light): no overflow, no errors. Not checked in Safari.

## Round two (same day, same link)

Owner: World panel had no right padding; light theme must show the light logo (black globe, white footprint); Connections
needs no globe unless companies can be placed by headquarters; both side panels fully retractable; the bottom views strip
behind a button that expands.

- Padding: dense tables use fixed columns (`.dt.fx`), so the right padding holds.
- Logo: both flat icons in the top bar, CSS shows the one for the theme (`.ic-l` / `.ic-d`).
- Panels: a fold button for each side in the top bar (beside the logo and beside Settings); when folded, small tabs at the
  screen edges bring them back. Board "Map, panels put away" shows both folded with the full-width camera.
- Views: a "Views · Theatre" button bottom-left; the strip of six pictures opens above it (shown open on the folded board).
- Connections: graph view on a plain background; new "On the map" view (Graph | On the map switch): companies at their
  registered place. Wikidata P159 headquarters (coordinates of the HQ item), P131 location or the item's own P625 (sites such
  as refineries), GLEIF legal address city for LEI companies (city coordinates from Wikidata: Moscow Q649, Berlin Q64,
  Matrei in Osttirol Q261697). 22 of 25 placed; Petro Shorouk, Восточная нефтехимическая компания and Nakhodka tank farm have
  no location in either register and are listed as not placed. Arcs from Rosneft (Moscow) lifted slightly above the globe,
  the chain continuing Berlin -> Matrei. Labels placed greedily without overlaps inside the free area.
- Investigate and Sources: no globe either (nothing there belongs on a map; placing people is never done).

## Round 3 (28 Nov 2026 afternoon): the tabs stay; companies' aircraft and ships on the map

Owner: "small tabs are good, the panels put away screen looks nice"; asked how exactly the Connections map would light up
ships and aircraft owned by a company, with an example. Same page (version 3): a method section ("How a company's aircraft
and ships get onto the map") and two boards, `connections-air` and `connections-sea` (`tools/suite_assets.py`, `assets.css`).

Data, all fetched live 15:22-15:31 UTC (`inputs/assets/`; the big raw answers, adsb.fi 552 aircraft and Digitraffic 946
ships, are not kept, only what was derived from them in `air.json` / `sea.json`):
- Aircraft: adsb.fi `/v3/lat/48.35/lon/11.79/dist/250` (552). Group = Deutsche Lufthansa AG (GLEIF 529900PH63HYJ86ASW55,
  27 children) + Wikidata airlines found by ICAO code (P230) whose parent/owner leads to Lufthansa Group (Q62589018) or
  Lufthansa (Q9325, same LEI). Owner per transponder address from adsbdb (76), then hexdb.io (4). Link rules: owner's
  airline code in the register = a chain airline's ICAO code (72), else exact normalised name (1, Eurowings Europe Ltd
  (Malta)); otherwise callsign code + digits = flight number only (dashed). When two Wikidata items share a code (DLH:
  Lufthansa and the Lufthansa Regional brand), the one with an LEI wins.
- Result: 85 aircraft fly group codes (83 with a flight number, 2 bare "SWR"); 73 registered to a group company; 5 Swiss
  flights on aircraft registered to Helvetic Airways (3) or Air Baltic (2); 7 with no owner in either register; ITA Airways
  (2) not linked: neither GLEIF nor Wikidata names Lufthansa as owner, and EI-EID is still registered to Alitalia
  (dissolved 14 Oct 2021 per Wikidata). None of the 80 owners was a lessor.
- Ships: Digitraffic AIS, 659 with an IMO number, 532 found in Wikidata by P458, 84 name an owner (P127) or operator
  (P137), 48 companies. Finnlines (8 ships; Wikidata LEI = GLEIF Finnlines Oyj) -> GRIMALDI GROUP S.P.A. (GLEIF, Palermo
  address), which declares control by natural persons (chain stops). Three Finnlines ships last heard 9-23 h earlier.
- Found while doing it: Wikidata lacks LEIs for Swiss, Austrian, Air Dolomiti, CityLine and Lufthansa Cargo, which GLEIF
  has, so today's Connections would show each of them twice (merge is by identifier only). GLEIF misses Eurowings,
  Edelweiss and Brussels Airlines as group children (their reporting exceptions: NON_PUBLIC, NON_CONSOLIDATING,
  NATURAL_PERSONS); Wikidata fills those in.
Globes: `tools/assets/rend.py` (cameras Cam(11.2, 42.0, 0.20, 11.2, 48.5, 1450, 920, 600) and Cam(22.5, 54.8, 0.17,
22.5, 59.4, 1450, 920, 600)). Checked in headless Chromium (1440 dark/light, 400): no overflow, no errors.

### Correction (same evening, version 4 of the page)
The first aircraft board built Lufthansa's chain only from the airlines' own parent/owner statements. Under the method as
stated (the chain Connections builds, which also reads the parents' "subsidiary" statements), Wikidata's Lufthansa item
lists **ITA Airways** and **SunExpress** as current subsidiaries, so both belong in the chain. The board had said "neither
GLEIF nor Wikidata names Lufthansa as an owner" of ITA: wrong. Corrected numbers: 89 aircraft fly group codes (87 with a
flight number + 2 bare "SWR"); 81 of 89 owners found (adsbdb 77, hexdb.io 4); 75 registered to group companies; 14 dashed
(3 Helvetic, 2 Air Baltic, 1 Alitalia, 8 not listed). Wikidata contradicts itself on ITA (its own item names the
Government of Italy as parent; GLEIF reports no consolidating parent) and names Lufthansa and Turkish Airlines as owners
of SunExpress: both shown, flagged. Inputs: `wd-lh-subs.json` (current, not dissolved P355 of Q9325 / Q62589018),
`wd-airlines-extra.json`; `prep.py` uses them.
