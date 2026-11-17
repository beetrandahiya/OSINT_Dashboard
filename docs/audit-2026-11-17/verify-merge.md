# Verify merge: integ (fix/shell + intel + lookup + space + moving on af6c04f)

Worktree /home/user/wt-merge, branch integ. Front end tested through scratchpad/verify/proxy.py on :8730 (merged static
files AND the merged index/feeds/lookup HTML, everything else forwarded to the old server on :8710) and :8731 (same, plus
emulated `{unchanged:true}` answers). Comparison proxies: :8732 = wt-space, :8733 = wt-moving. Python tested by direct
calls and a lifespan-less TestClient (no collector started, WW_DATA = scratch copy). Scripts: scratchpad/verify/.

## Commits made on integ
- 9be5ba6  lookup/store.py:64 `_forget_names` deleted `wdent:<qid>`, but fix/intel renamed that cache key to `wdent2:`
  (dossier.py:540/556). "Delete everything" / removing a name left the Wikidata entity rows behind. Now
  `key GLOB 'profile*:'||qid OR key GLOB 'wdent*:'||qid`. store_test.py (extended with wdent2:/profile4: rows): 0 failures.
- d38715b  main.js:362-380, 470. fix/space's `ww-shape` listener called `shape(globe, false)`, which with fix/moving's
  model overwrote `userGlobe` (the user's choice). Seen: flat map -> Look down -> press Globe (saved '1') -> Leave ->
  map drawn FLAT, Globe button off, localStorage still '1' (reload would show the globe). Fix: a separate `lent` flag
  (the satellite borrows the globe only when the user's choice is flat; handing back clears it); buttons always show the
  user's choice; chaseStart clears `lent`. Re-run (t3b.js, flat and globe start): every state consistent, saved value
  untouched by rides.

## Per check
1. PASS. All 37 modules import (dynamic import of each in the page); static import/export cross-check: no missing
   names (one false positive: `export const unrest = ..., unrestSingle = ...`); `node --check` on all modules; fresh load
   0 page errors, default layers as before (fresh.png). One stray 404 on one load, not reproducible (external image).
2. PASS. 40-chip sweep (verify/sweep/t2.out, 1280x800): every chip counts, draws, opens a card where it has items, no
   undefined/NaN, closes cleanly, nothing left drawn after off, legend section gone. Only warnings: leaders/people
   `array<number,2>` (known, intel) and willReadFrequently from the test itself.
3. PASS after d38715b. Flat<->Globe buttons save 'ww-globe' correctly; Look down enter/leave from flat (globe borrowed,
   back to flat, saved '' untouched) and from globe; ride then pick+follow an aircraft then Stop (projection returns to
   the choice); follow then pick ISS then Look down then Leave; Munich during a follow (chase stops, flies to 11.57/48.14,
   globe returns when chosen); Globe/Map pressed during a ride. space lookfix.js: ride at 437 km, leave restores
   35°/20°, drag takes the camera over (one flaky run where the drag did not register; 3 later runs and the space
   worktree fine, events confirmed with drag.js).
4. PASS. moving t7b.js (all sequences: projection + button right every time), clock.js twice: 0 backward steps, 0
   jumps > 1.5x, worst 1.14x (one aircraft held 45 % in one run: it stopped reporting; 7/8 at 0 %). t5b at globe
   1100x700 and flat 1512x982: plane outside legend/markets/card, wheel over it zooms 10.5 -> 13.7 / 13.3. Models
   stats: items = models, one sel ring position, trail/route drawn.
5. PASS (verify/moving/card.js). Live aircraft card: altitude/speed/report age update every 3 s, also with the mouse over
   the card; photo <img> kept (same node through 27 s), #actype/#route never fall back to "Looking it up", no duplicate
   ids. ISS card: #satwho/#satabout filled and kept after ww-detail + 22 s, one #satwho. News card: spy-pass and
   imaged results kept after a forced renderDetail(true) + 25 s, no duplicate sections.
6. PASS (t6.js, /api/hotspots injected because the live list is empty): 0 pulse markers while off (also after a reload
   while off), one per hotspot when on; ids: fallback `hot:<i>` with the old answer, server `id` when present; card
   stays open after a 5-minute reload with the list reversed; a signal link works; off removes markers.
7. PASS for the merge (space ordertest.js): photo < sharp < live < night < aurora < rain < lightning < gps < cables/fires,
   all under the labels, in 3 start states, after toggling, and with 3D on (relief under the photo; three() turns Sharp
   on and the legend/chip follow; off again restores). Labels white with Photo+Sharp.
   NOT a merge regression (same on wt-space :8732): labels stay dark when the page LOADS with Photo on, and when 3D turns
   Sharp on - main.js:110 `onPhoto(v => { setPhoto(v); if (map.isStyleLoaded()) paintBase(...) })`: during load / while
   terrain tiles load isStyleLoaded() is false, so the colour switch is skipped. Fix: drop the isStyleLoaded gate (or
   paintBase on next 'idle'). Left for the space owner.
8. PASS. Old server: pages send ?since= (277 of 1708 data requests), server ignores it, data flows. :8731 emulated
   unchanged answers (news, quakes): list 1312 rows and chip counts intact, counts still moving, open quake card kept.
   TestClient on merged web.data: same since -> {unchanged:true} without payload, other since -> payload.
9. PASS. /lookup light+dark and /feeds render through the proxy, no errors, no NaN/undefined/null; lookup page asks only
   GET /api/lookup/state when idle; feeds shows "3 not set up (optional key)".
10. PASS. compileall clean; all 37 Python modules import. Live/real data: news.person_mentions (offsets stripped, V1 rows);
   unrest._t epoch + clamp, unrest payload times sane; courts: data/icc-situations.json 19 pages, 17 shield copies, load
   keeps 2, icc_matches reports missing 17 (Duterte case found); satinfo.limits GEO 3 km / LEO 0.8 km, manoeuvres on the
   real history 1 (as the space fixer reported); _ais_speed and ais.Stream 102.3 -> None, heading 0 kept; collector
   trails: 300 area aircraft x 800 answers -> max 134 points each (cap 120 + 50 step), military trail 2745 (cap 2700+50);
   picture proxy _public_url and lookup enrich.check_url refuse loopback/RFC1918/169.254/CGNAT/::1/file/ftp, allow
   example.com; /api/news/image unlisted local -> 404; guard_test.py 20/20. No duplicate function/class definitions or
   duplicate dict keys in any module; cache keys consistent (profile4:, wdent2: everywhere after 9be5ba6; ukcase2:).

## Other observations (not merge regressions, for the owners)
- "Expected value to be of type number, but found null" MapLibre warnings (6-10 per run) with aircraft+military+quakes+
  news on and a followed aircraft: same count on wt-moving alone. Source layer not pinned down.
- Munich pressed while following, then World: the saved world view is the chase view (pitch 60, zoom 10.5) because
  place() saves it after chaseStop(false). By fix/lookup's design; arguably World should return to the pre-chase view.
- Once, an aircraft picked right after leaving a satellite ride showed "No longer in the feed" (the live area had moved
  with the ride); not reproduced in 2 later runs.
- hotspots.js: render() calls pulse(), which removes and recreates every marker on each render (animation restarts on
  the 5-minute reload). Cosmetic.
- After switching Military or Cables off, ~11 renders in 3 s still happen (shell's own sweep showed 6-7); not checked
  further.

## Not tested here
3D terrain with models (headless times out), real GPU/Safari frame rates, server-side changes running live (8710 is the
old code until restarted).
