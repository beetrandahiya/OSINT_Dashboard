# World Watch Porcelain: design language proposal (28 Nov 2026)

Owner's ask: the Footprint icon on "the palest" soft tile, but lighter ("almost white") and more 3D, then "a full
design language and everything, like the reports". His answers: show a brand **and** app look (he decides later
whether it goes in), find "NON AI SLOP" fonts online, reports = Investigate case file + Connections report, dark
icon = dark twin.

Published page: https://claude.ai/artifact/M9YPGR3DxF5shLZo6i1cAg (copy: `porcelain.html`).

## Icon
- `tools/porcelain.py`: numpy ray caster of the exact Footprint geometry (64 grid, globe r 26.5, camera 20 N 10 W,
  786 km horizon cap 27.1 deg around Munich, pupil r 3.6). Matte globe lit from the top left, thin atmosphere on the
  sunlit limb, Lambert-shaded white footprint, analytic soft contact shadow (indigo-950), bevelled tile edge.
  Themes: `light` (white tile, violet-100 / sky-100 whispers fading to white), `dark` (the dark twin he picked:
  zinc-950 tile, zinc-100 globe, footprint as its negative), `dark-planet` (alternative: black globe with its
  atmosphere on a dark tile; fades at 16 px on a dark taskbar). `flat_svg()` is the 16-32 px version (r 29, pupil 5.2).
- First renders used a glossy clear-coat: it read as a pool 8-ball. The matte sphere plus atmosphere reads as a planet.
- `icons/`: 1024 px PNG renders, 640/128 px WebP, flat SVGs. No .ico / Icon Composer files yet.

## Type (research agent, licences read from each OFL.txt; all on Google Fonts)
- Mona Sans (GitHub + Degarism) for headings and the wordmark (outlined at wdth 118, wght 640).
- B612 (Airbus, ENAC, Université de Toulouse III, Intactile DESIGN; cockpit map labels) for all text **and numbers**:
  its digits are all one width (1300/2000 units) with narrow point and comma.
- B612 Mono only for codes and IDs. In B612 Mono a point or comma takes a full cell, so "790,803,860" read like three
  numbers: found in the first build, numbers moved to B612.
- Redaction (Jeremy Mickel for Titus Kaphar and Reginald Dwayne Betts' *The Redaction*, from Times and Century
  Schoolbook) for printed reports; Redaction 50 Bold for stamps (documents only).
- Considered: D-DIN Condensed + Overpass + STIX Two + Big Shoulders Stencil; Cooper Hewitt + Atkinson Hyperlegible
  Next + Intel One Mono. 17 families checked in all; files were downloaded to the session scratchpad only.

## Colour
Tailwind CSS v3.4.17 steps plus Anduril black #010101; no orange. Light map: white land, sky-50 sea, zinc-300 borders;
layers rose-600 (conflict), indigo-700 (military), sky-700 (ships), violet-600 (space), zinc-900 dots (news).
Dark: zinc-900 land on zinc-950, the -300/-400 steps. Full tables with WCAG ratios are on the page.

## Data on the page (all real)
- App boards: latest payloads in `data/worldwatch.db`, newest 28 Nov 2026 03:08 UTC (GDELT unrest/news, adsb.fi
  military, Digitraffic ships, DeepState front, Launch Library 2). World aircraft left out (stored snapshot 9 days old).
- Connections report: `data/rosneft.json`, built with `worldwatch.connections.node.build` 12:36 UTC (GLEIF,
  Wikidata (429 for PJSC Rosneft), OpenSanctions by LEI).
- Case file: reserved test identifiers only (test@example.com, example.com; RFC 2606). `data/case-summary.json`
  (XposedOrNot breach names/years/records/data types, Hudson Rock count and dates without logins), `data/rdap.json`,
  `data/xon.json`. crt.sh failed; Gravatar 404.

## Rebuilding
Tools expect the session scratchpad layout (`../globe` for geo/gmarks, `../logo/tools/typo.py`, fonts in
`../logo/fonts`, Mona Sans static instances made with fontTools instancer). Run
`uv run --no-project --with numpy --with shapely --with uharfbuzz --with fonttools python build5.py`.
Checked in headless Chromium at 1440 light/dark and 400 px: no overflow, no errors, all five faces loaded.
Not checked in Safari, on a real taskbar or Dock, or printed.
