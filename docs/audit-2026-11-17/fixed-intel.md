# Fixes: intel (branch fix/intel, worktree /home/user/wt-intel)

Testing: Python changes were tested by calling the functions directly on real data (the GDELT cache files, the live
server's /api/data payloads, a handful of Wikidata calls cached in scratch). Front-end changes were tested through a
proxy on port 8724 (scratchpad/intelfix/proxy.py: my static files, live API). The running server on 8710 still runs
the OLD Python, so server-side fixes do not show in the page until the server restarts on the merged code.

## Per finding

1. Person dossier "In the news" 0 (high): FIXED. New `news.person_mentions()` is the single reader of the person
   field (strips ",offset", copes with old V1 rows); used by dossier.person, news.leaders_today and the WATCH filter in
   news.parse. On the real 6 h cache: Trump 624 outlets (239 naming him in a headline; Leaders today 253 at Washington),
   Modi 26, Netanyahu 54. New `tracked` flag: for someone not on the leaders list the tile says "names in articles are
   kept only for heads of state and government" instead of 0.
2. ICC "not named" from bot-shield copies (high): FIXED. `courts.good_copy()` (is_challenge + title "Gcore") applied on
   load, on save, on each fresh page and in icc_matches. Payload carries `missing` (pages refused with no good copy);
   old payloads without it are counted on the fly. Feed note starts "the court's site refused n of 19 situation pages
   ... warrants named there may be missing". Dossier: "not named in its case list. Its situation pages ... could be
   read only in part: 17 of 19 were refused ..., so a warrant cannot be ruled out" (case list wording kept separate).
   The fake Safari User-Agent was removed (default project UA). The real data/icc-situations.json was not edited: the
   loader drops its 17 shield pages on the next run and the next save writes only good ones. Feed state stays "ok"
   (the case list did read); not made late: no honest data_time exists for refused pages. Shield not touched.
3. Hotspot pulse: shell's (not touched; my hotspots.js edits are below line 20, outside the pulse block).
4. Card redraws: shell's.
5. Maxar "Open the pictures" crash: FIXED in dossier_country.js: the button is gone (layer removed by the owner), the
   events stay listed with a line saying the layer is off. Guard in main.js pick() still recommended (patch below).
6. Hotspot links: FIXED. `owns()` on unrest (both chips via mine()), airspace (FIR/TFR), navwarn, hazards. Verified:
   TFR and unrest links now open their cards from the hotspot card. quakes.js is space's: patch below.
7. Former heads of government as current: FIXED. SPARQL `?st a wikibase:BestRank` in dossier._facts and in
   people.leaders(); `_best_rank()` in the EntityData fallback. Cache key country-facts2:. Verified live: Taiwan
   Lai Ching-te / Cho Jung-tai, Nauru David Adeang only.
8. "mul" labels: FIXED. `geo.wd_label()` (en -> mul -> Latin-script languages) and LABEL_LANGS_API / _SPARQL used in
   people._basics, _label_map (API + SPARQL), leaders(), dossier._facts (label service), _facts_entity, _wd_entity.
   Keys bumped: profile4: (dossier.py + lookup/api.py), wdent2:. sites.py names already used en/mul; left.
   Q42 live check not done (Wikidata 429 at that moment); wd_label unit-tested on Q42's shape.
9. Unrest "in 234482885 d": FIXED server-side (articles' time through `_t`, epoch, clamped). Verified on cached
   events/mentions. All other ago()/local() callers in my modules checked: epoch everywhere.
10. Protest pictures 404: shell's (web.py allowlist).
11. Military-area card switching: FIXED. ids `marea:<osm id>`, areas remembered across pans (cap 20,000). Also stable
    ids for hotspots (server: oldest counted signal), spikes (server: series + place), fires (lon,lat,time), front
    points/changes/areas (from the item; hotspot signals use the same change id). Verified: pan keeps the card,
    "No longer in the feed" for a vanished front item.
12. Dead hijacks feed: FIXED. netwatch drops events older than 24 h by our own clock (the layer is "last 24 hours");
    while the feed is failing/waiting or unread for 30 min, no "still announced"/"still going", a warning line on the
    card, and the chip title says "Cloudflare Radar feed stopped: last read 30 h ago (not set up: ...)". Outages:
    Cloudflare notes without an end from a stopped feed read "no end noted when last read 30 h ago (feed stopped)",
    are faded and not counted. Verified via proxy: hijacks 0, chip text as above, note meta as above.
13. Palestine: FIXED. geo.QID_FIX PS -> Q219060 applied on load (old table gets it; old QID still maps to PS).
    Empty facts are not cached; leaders-list fallback used when facts have no heads (server and dossier_country.js).
    Verified live: Abbas / Mohammad Mustafa, Ramallah + East Jerusalem, population 5.2 M. Taiwan, Kosovo, Somaliland
    items are the polities; Western Sahara (Q6250) and Northern Cyprus left as they are (noted in code).
14. Off layers downloading: per-feed polling is shell's. Mine: web.py /api/data takes `?since=<fetched>` and answers
    `{...state, unchanged: true}` without payload (tiny, backwards compatible). News map payload: 3 articles per
    place instead of 8 (-20 %; the card fetches the rest). Page side is shell's: patch below.
15. Retry chains: shell's.
16. Escape closes two things: shell's (left alone).
17. Show on map on off layers: FIXED in profile.js (clicks the layer's chip on first). Note: if shell stops off layers
    from loading, the pick needs the layer's data to arrive first.
18. Airspace line-width warning: FIXED.
19. Front-line: FIXED (centroid ring, guarded lookups, no double escape; also cables.js meta).
20. Small: navwarn rows sort by parsed issue time (`issued_t`); GDACS empty country names dropped; TfL "\/" unescaped;
    country dossier says adsb.fi; news hero = first story's picture (none if that story has none) and follows the full
    list; hazard dates carry the year (hazards.js; util.local patch below); non-person / unknown QID -> 404 with
    "X is not a person on Wikidata..." / "No such Wikidata item" (people._basics, lookup/api.py). Find-box re-render:
    main.js, patch below.

## Shared-file edits (check at merge)
- web.py `data()`: the `?since=` block (9 lines).
- lookup/api.py: cache key profile3: -> profile4:; `except _people.ProfileError` -> 404 with the message.
- feeds.py: courts_icc rewritten (my feed), gdacs countries cleanup.
- hotspots.js: only render/rows/locate/detail and a helper above `const hotspots`; pulse block untouched.

## Patches for the lead (main.js / util.js / quakes.js)
- main.js pick(): `if (p && !byId[p.layer]) return;` at the top (dead layer ids such as maxar).
- quakes.js (space): `owns: id => quakes.some(q => q.id === id),` (use the module's quake array name).
- util.js local(): `d.toLocaleDateString('en-GB', {day: 'numeric', month: 'short', ...(d.getFullYear() !== today.getFullYear() ? {year: 'numeric'} : {})})`; then hazards.js `at()` can go.
- main.js load(feed): remember `lastFetched[feed] = d.fetched` and ask `/api/data/${feed}?since=${lastFetched[feed]}`;
  when `d.unchanged`, skip onData/render (still update feed age from the state fields).
- main.js find box: build the country rows once (`list.innerHTML = lands() + '<li class="empty" id="find-people">Searching people…</li>'`),
  and when people arrive replace only that placeholder: `const ph = $('#find-people'); if (ph) ph.outerHTML = people || '<li class="empty">No person found.</li>';`
  so a click on a country row at that moment does not hit a detached node.

## For the owner
- ICC: with an honest User-Agent the shield may refuse as before or more; the dossier now says so plainly.
- Wikidata 429 from the sandbox limited live checks (Q42 entity path).

## Lessons for CLAUDE.md
- GDELT V2EnhancedPersons entries are "name,offset": always read them through news.person_mentions().
- Wikidata: read labels via geo.wd_label (en -> mul -> Latin); current office = best rank (`a wikibase:BestRank`),
  not "no end date". Natural Earth points PS at the region item; QID_FIX corrects it.
- Never keep a "last good copy" without validating it again on load (ICC shield pages were kept for days).
- Ids of map items must come from the item, never a list index of data that is reloaded or viewport-dependent.
