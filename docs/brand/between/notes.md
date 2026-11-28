# Three Earths: directions between Porcelain and God's eye (28 Nov 2026)

Owner, after the Porcelain page: "this design looks very good, now i think we can think about designing the panels and
layouts and everything in the app; we maybe need something between this and god's eye? for the actual app".

Published page: https://claude.ai/artifact/DZAbTkACsj1rDknuAyZAPq (copy: `three-earths.html`).

Six 1920 x 1080 boards, Dense layout, Porcelain parts (Mona Sans, B612, Tailwind colours, ink buttons, tiles), same
theatre camera as the God's eye boards (35.0 N 19.0 E, 2,676 km up, looking at 49.0 N 34.0 E; principal point moved left
so Ukraine sits beside the column), same data (server store, newest 28 Nov 2026 03:08 UTC).

- **A Real Earth, smoked panels**: NASA Blue Marble photo in black space (God's eye) with see-through porcelain panels
  (white 90 % / near-black 78 %, no blur).
- **B Ink Earth** (my pick): the icon at full size: black seas, charcoal land (zinc-ish #26262b) with hairline borders and a
  little ASTER relief, sky-100 atmosphere on the sunlit limb, in porcelain-white space (light) or zinc-950 night with
  violet/sky whispers (dark); solid porcelain panels.
- **C Silver Earth**: the photo without colour, pale on white (light) or dim silver on night (dark).

Tools: `tools/render.py` (uses the God's eye `gv/cam.py` pinhole camera and NASA textures from the session scratchpad),
`tools/thumbs.py` (view-strip thumbnails), `tools/boards.py` (markers projected with the same camera; reuses
`docs/brand/porcelain/tools/mock.py` for card, Now list, tiles, top bar), `tools/build.py`.
Checked in headless Chromium (1440 light/dark, 400): no overflow, no errors. Not checked: Safari; whether MapLibre's globe
leaves the space around it transparent so the page background shows (needed for B and C in the app).
