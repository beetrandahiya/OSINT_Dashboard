# World Watch identity, round two: globe marks (28 Nov 2026)

Owner's ask: "make it something with a globe maybe, but make sure to keep it special and non generic".
Published page: https://claude.ai/artifact/3KY5CpxFbBEFaB8pr3iCNS (copy: `globe-marks.html`).
Round one (ten directions, no globe): https://claude.ai/artifact/7vz14iNt1ma3EUEC31zM3v (`../brand-book.html`).

## The six directions (ranked)

| Rank | Name | The fact behind it | Palette |
|---|---|---|---|
| 1 | Oko | Molniya orbit at true scale (600 x 39,700 km, e 0.737, 11.94 h) with the Earth at its focus; flown by the Soviet early-warning satellites Oko ("eye"), Kosmos 520 (1972) to Kosmos 2469 (2010) | NATO |
| 2 | Unrolled | West of Greenwich an orthographic globe, east of it Web Mercator zoom-2 tiles; Munich's tile (2/2/1) lit | NGA website |
| 3 | Footprint | Sentinel-2 (786 km) horizon circle around Munich, 27.1 deg, 6,030 km across, seen from 20 N 10 W: the globe as an eye | Palantir Blueprint |
| - | Above home | Munich-centred hemisphere: 45.5 % land, 79.1 % of all land; best possible 46.7 % (western France) | Bundesregierung |
| - | Octant | Pole, 0/0, 0/90E: three right angles, 1/8 of the Earth, Munich inside | EUMETSAT website |
| - | Lune | UTC+1 nominal slice 7.5-22.5 E, a two-sided figure, Munich inside | DLR website |

Dropped after the 16 px test: graticule globe with Munich's cell lit (generic), day/night globes (moon, dark-mode
icon), polar clock and polar hour hand (gauge), Munich's meridian + parallel (trident), Goode's interrupted
homolosine (its southern edge is VVVV but reads as teeth), true-scale ISS ring (invisible), spotlight cone (map pin).

## Numbers and how they were made

- Horizon angle acos(R / (R + h)); shares (1 - cos a) / 2; ground width 2 a x 111.195 km.
- Molniya: typical perigee 600 km, apogee 39,700 km; period from Kepler's third law (mu 398,600.4418);
  far-half time share 0.5 + e / pi = 73.5 %; time dots from Kepler's equation.
- Land shares: `tools/landhemi.py`, 400,000 Fibonacci-sphere points against the app's Natural Earth admin-0
  outlines (`data/countries-geo.json`); whole Earth 28.7 % in this data.
- Tiles: standard slippy-map formula for 48.137 N 11.575 E (z2 2/1, z6 34/22, z10 544/355, z14 8718/5685).
- Oko facts: Wikipedia (Kosmos 520, Oko) and RussianSpaceWeb, via a web search on 28 Nov 2026.
- EUMETSAT colours: named CSS variables on eumetsat.int (--eumetsat-blue #00205B, --primary #0079C0,
  --secondary #A8CF45, #6D96B2, #1E3650). DLR: most-used colours in dlr.de's stylesheet. Both websites, not brand guides.

## Rebuilding

`tools/build.py` expects round one's `typo.py` and fonts beside it (they were in the session scratchpad:
`logo/tools/typo.py`, `logo/fonts/*.ttf`; fonts are OFL, from Google Fonts: Chakra Petch 600, Public Sans 700,
Geist 600, Manrope 700, Red Hat Display 600, IBM Plex Sans Condensed 600). Run with
`uv run --with uharfbuzz --with fonttools --with brotli --with numpy --with shapely python build.py`.
Checked in headless Chromium only (1440 light/dark, 400 dark: no overflow, no errors); not in Safari, not on the
real taskbar or Dock.
