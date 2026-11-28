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
