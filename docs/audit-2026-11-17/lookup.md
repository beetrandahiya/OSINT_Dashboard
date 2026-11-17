# Audit: lookup (Munich view, /lookup, /feeds + /api/status, README)

Scripts and screenshots: /tmp/claude-0/-home-user/bbcfb72d-ba4d-521d-8ffc-417ae38a2ca2/scratchpad/audit/lookup/
Test identifiers used: test@example.com, example.com, GitHub/username "torvalds", name "Linus Torvalds", +49 89 1234567 (offline only).
Checks run: services (email), records (domain), github, phone, name, read_pages. No WMN sweep, no Maigret/Sherlock/Holehe/theHarvester, no self-test.
All test findings deleted with the page's "Delete everything" (identifiers/findings/scans/pages = 0), but see finding 4.

### 1. Lookup API takes cross-site POSTs (CSRF) and any Host header (DNS rebinding)   [severity: high]  [confirmed by running]
Repro: `curl -X POST localhost:8710/api/lookup/identifiers -H 'Origin: https://evil.example' -H 'Content-Type: text/plain' --data '{"kind":"domain","value":"example.com"}'` -> 200 {"ok":true}, identifier stored. `curl -H 'Host: attacker.example' localhost:8710/api/lookup/state` -> full findings.
Seen: any web page open in the owner's browser can, with a no-preflight `fetch(..., {mode:'no-cors', body: text/plain})`, add identifiers, start a scan (including `holehe` + `holehe_reset`, which sends password-reset mails to his inbox, or `maigret_deep`), or call `/api/lookup/wipe`. A DNS-rebinding page can also READ every finding (Host is never checked; the client address is 127.0.0.1).
Expected: "only answers on the computer it runs on" should also mean "only to this app's own pages".
Cause: lookup/api.py:16-17 `_local()` checks only `request.client.host`; `await request.json()` parses any content type; no Origin/Host check anywhere (web.py has no TrustedHostMiddleware).
Fix: in `guarded()`: refuse unless `request.headers.get("host","").split(":")[0] in {"127.0.0.1","localhost","[::1]"}` (plus the Tailscale name when WW_LOOKUP_REMOTE=1), and for non-GET require `Origin` absent or equal to the page's own origin, and `Content-Type: application/json` (forces a CORS preflight that the server never answers). Same Host check is worth adding app-wide via `TrustedHostMiddleware(allowed_hosts=[...])`.
Risk of the fix: low; when opened over Tailscale with WW_LOOKUP_REMOTE=1 the allowed host list must include that name.

### 2. Graph legend (and the only "Show N marked not me" button) is off screen   [severity: medium]  [confirmed by running]
Repro: l6.js. Open /lookup, Graph tab. Legend box is at x=1500 in a 1440 px window (getBoundingClientRect left 1500).
Seen: no colour key in the graph, and once something is marked "Not me" there is no way to show it again / undo it (the toggle lives only in that legend).
Cause: app.css:375 (the map's new legend panel, 2026-11-16) styles every `.legend` with `left: calc(var(--side-w) + gap*2); width: 290px`. On /lookup `#legend` is `position: relative` inside `.right`, so `left` pushes it ~420 px right, out of the window. Second bug on the same line: lookup.js:64 the statement `$('#legend').style.display = tab === 'graph' ? '' : 'none';` was swallowed into the end-of-line comment, so the legend is never hidden in the Dossier tab either (it is just off screen).
Fix: scope the map rule (`#legend.legend` or `body:not(.lookup) .legend`), or rename the lookup one `.lk-legend`; move the commented statement onto its own line.
Risk: none.

### 3. A new finding can inherit another finding's page read (alive, title, picture)   [severity: medium]  [confirmed by running against a scratch db]
Repro: WW_DATA=<scratch> python: save finding A, save its page, rescan without A (row deleted), save finding B -> B gets id 1 and shows `{'alive': True, 'title': 'PAGE OF SITE A'}`.
Cause: lookup/store.py:60-64 deletes vanished findings but not their `pages` row; `findings.id` is a plain INTEGER PRIMARY KEY, so SQLite reuses the highest freed rowid. `pages_to_read()` then also skips B for a week because a fresh-looking read exists.
Fix: in `save_findings`, `DELETE FROM pages WHERE finding IN (SELECT id FROM findings WHERE identifier=? AND tool=? AND last_seen<? AND not_me=0)` before the findings delete; and/or `id INTEGER PRIMARY KEY AUTOINCREMENT` (needs a table rebuild) or store the URL in `pages` and check it matches.
Risk: low.

### 4. "Delete everything" leaves the names you typed in lookup.db   [severity: medium]  [confirmed by running]
Repro: add Full name "Linus Torvalds", wait for the Public figure card, Delete everything. `SELECT key FROM cache` still has `search:linus torvalds` (and the profile3:Q34253 body). Left from this audit (not removed, audit is read-only): rows `search:linus torvalds`, `search:<b>xss</b> test`, `profile3:Q34253` in data/lookup.db `cache`.
Seen: for the owner this keeps his own full name (and any name he types) after he deleted "everything"; store.py's own docstring says deleting the subject deletes everything about it. Removing a single name identifier also leaves it.
Cause: lookup.js:72-79 `findFigures()` calls `/api/people/search`, which caches under `"search:" + q.lower()` (api.py people_search) in the same db; `store.wipe()` (store.py:121) clears only pages/findings/identifiers/scans.
Fix: have `wipe()` and `remove_identifier()` delete `cache` rows `search:<value>` for name identifiers (or don't cache searches made from the lookup page: pass `?nocache=1`).
Risk: none. Cleanup for this audit's rows: `DELETE FROM cache WHERE key IN ('search:linus torvalds','search:<b>xss</b> test','profile3:Q34253')`.

### 5. Page reader fetches any address, including this server and the LAN (SSRF)   [severity: medium]  [confirmed by running enrich.read_page in a separate process]
Repro: `enrich.read_page(client, 'http://127.0.0.1:8710/lookup')` -> status 200, title "World Watch Lookup", alive True. `file:` is refused by httpx (UnsupportedProtocol).
Seen: every found URL (DuckDuckGo results for a name, Gravatar-linked account URLs, Maigret/Sherlock URLs, theHarvester URLs) is fetched with `follow_redirects=True` and no address check, so a page that merely ranks for the owner's name can 302 the reader to 127.0.0.1:8710/8700, the router, or other LAN hosts; the title/description of the answer is stored and shown.
Cause: lookup/enrich.py:65.
Fix: resolve the host before each request and after each redirect (event hook on `request`), refuse loopback/private/link-local/ULA/CGNAT 100.64/10 (Tailscale) addresses and non-http(s) schemes; follow redirects manually (max 5) applying the same check.
Risk: low; a few legit sites on odd ports still work.

### 6. Detail card is rebuilt every 2 s: text selection lost, and the whole state reloaded while idle   [severity: medium]  [confirmed by running]
Repro: l4.js. Open a card, select its title, wait 4.5 s -> selection "" . In the Graph tab the SVG (237 nodes) is rewritten every 2 s while nothing changes (3 rewrites in 6 s idle).
Cause: lookup.js:202 polls `/api/lookup/state` (all findings with page bodies; hundreds of KB with real scans) every 2 s whenever the tab is visible, and `render()` always calls `renderDetail()` (innerHTML rebuilt, lookup.js:143-156) and `draw()`. The CSS allows selecting text in `.detail` (lookup.css:55), so copying a URL or bio is nearly impossible.
Fix: poll every 2 s only while `S.job.running`, otherwise every 30 s or on focus; in `render()` skip `renderDetail()`/`draw()` when the response is unchanged (compare a hash or `findings.length + last_scan.finished + job`), like the dossier already does with `dataset.html`.
Risk: low.

### 7. /feeds report: "NaN MB" downloaded, "null s" / "undefined / undefined" row, and a crash path   [severity: medium]  [confirmed by running; crash by reading]
Repro: f1.js. Summary tile reads "NaN MB downloaded this run"; the "Public webcams worldwide" row shows "null s" and "undefined / undefined".
Cause: web.py:57 appends a pseudo-feed `windy` without `total_bytes`, `interval`, `ok_count`, `fail_count`, `tried`; feeds.html:78 sums `x.total_bytes` (NaN), :94 `every(null)`, `${x.ok_count} / ${x.fail_count}`. When a Windy key exists and the last call failed, feeds.html:91 calls `clock(x.tried)` -> `new Date(NaN).toISOString()` throws RangeError and the whole table stops updating.
Fix: give the pseudo-feed `total_bytes: 0, interval: None, ok_count/fail_count: 0/0, tried: _WINDY_LAST["time"]`, and in feeds.html use `(x.total_bytes||0)`, `x.interval ? every(x.interval) : 'on demand'`, guard `x.tried &&`.
Risk: none.

### 8. Munich: pressing Munich twice loses the world view   [severity: medium]  [confirmed by running]
Repro: m4.js. World at (-40,20) z2.2 -> Munich -> Munich again -> World: camera stays at Munich (11.6,48.1 z8.3).
Cause: main.js:435 saves `worldView` on every Munich press, even when already in Munich. Also only centre/zoom are saved, so bearing/pitch/globe tilt from the world view are not restored, and `place()` does not stop a running chase camera (its per-frame jumpTo overrides the easeTo, while the sidebar switches).
Fix: `let where = 'world'`; in `place()` return early if `where === to`; save `{center, zoom, bearing, pitch}`; call `chaseStop()` first if a chase is active.
Risk: none.

### 9. Munich transport panel says "English headlines are machine-translated" while every headline is German   [severity: medium]  [confirmed by running]
Repro: /api/data/mvg now: 208 messages, none with `title_original`; the panel footer still claims machine translation; feed note says nothing.
Cause: feeds.py:1208 `english, _ = await translate.to_english(...)` throws away the failure count (Google blocks this sandbox; pause logic in translate.py), so neither the feed note nor the panel can say translation failed. munich.js footer text is static.
Fix: `english, failed = ...`; add `failed` to the payload and the note ("headlines left in German: translation paused/failed for N"); munich.js prints "machine-translated" only when some `title_original` exists, else "Headlines in German (translation unavailable right now)".
Risk: none.

### 10. README does not list every key, and its feed/size facts are out of date   [severity: medium]  [by reading]
Seen: key table lists only aisstream and OpenSanctions; config.py also reads `data/windy-key.txt` (webcams), `data/brave-key.txt` (ship photos, paid card needed), `data/cloudflare-token.txt` (hijacks/leaks/outage notes) - hard rule "list every key". "Python packages (three small ones)": a clean clone installs 13 (uv picked CPython 3.14.6; import of worldwatch.web works). Feed table lists 24 feeds; the server has ~45 (status page) and says "Military aircraft adsb.lol 5 min" (now adsb.fi every 30 s). "Find a person" is now "Find a person or country". The "answers only on this computer" promise is weakened by finding 1.
What is right: `data/` at the repo root matches config.py (`parents[2]/data`); `uv lock --check` clean; .gitignore covers data/; one command from `server/` works on a fresh clone (import tested; server not started, one was already running).
Fix: add the three keys with where to register and what they switch on; regenerate the feed table from `FEEDS`; drop the package count.

### 11. "Not me" does not survive a different tool finding the same page   [severity: low]  [by reading]
Cause: lookup.js:26 a joined dot is hidden only if `every` row is marked; marks are stored per row (store.mark). When a later scan (e.g. Maigret after the built-in checker) adds a new row for the same URL, it arrives with not_me=0 and the whole dot comes back. Rescans by the same tool keep the mark (confirmed: services-only rescan kept not_me=1).
Fix: when saving a finding whose normalised URL already has a not_me row for the same identifier, insert it with not_me=1 (or store "not me" by identifier+normalised URL).

### 12. Removing an identifier during a scan leaves orphan findings   [severity: low]  [by reading]
Cause: api.py:79 `remove` is not blocked while `job["running"]` (wipe is); `_scan` captured `ids` at start and keeps calling `save_findings(ident["id"], ...)`, inserting rows for a deleted identifier (no foreign key). They count in "Stored", the dossier and breaches, but have no node in the graph and no remove button; only "Delete everything" clears them.
Fix: return 409 from `remove` while a scan runs (and disable the ✕ buttons), or check the identifier still exists in `step()`.

### 13. "Read the pages" with nothing to read overwrites the last scan summary with "0 findings from 0 checks"   [severity: low]  [confirmed by running]
Repro: after a scan, press Read the pages when every page was read in the last 7 days -> last_scan.summary = {findings: 0, checks: []}; sidebar: "Last scan just now: 0 findings from 0 checks." No feedback that nothing was due.
Cause: api.py start("read") always creates a scans row; summary has no `pages_read` when `pages_to_read()` is empty (7-day window, store.py:84), and lookup.js:52 falls to the generic text.
Fix: if nothing is due, return {"ok": true, "note": "All pages were read in the last 7 days"} without creating a scan; or add a "re-read all" path with max_age=0.

### 14. Public figure card silently never appears after one Wikidata refusal   [severity: low]  [by reading; 429 seen live]
Cause: lookup.js:76 marks the name `asked` before the fetch; a 502 (Wikidata 429, seen during this audit) yields `figures[name] = []` and it is never asked again until reload, with no message.
Fix: on error delete from `asked` and retry after 60 s; show "Wikidata busy, will retry" in the dossier.

### 15. Hostile URLs (javascript:/data:) reach href attributes unfiltered   [severity: low]  [confirmed by running with mocked findings]
Repro: l7.js injects findings with `url: 'javascript:...'`, `data:text/html,...`, archive snapshot `javascript:`: 21 such hrefs end up in the dossier, detail card and timeline. All text (titles, bios, names, site names, problems, Wikidata names in the figure card) WAS escaped: no injected attribute or script ran. Clicking one in Chromium opened about:blank (noopener) without running it; Safari not tested.
Cause: lookup.js:154, dossier.js:63/98/99/seenOn/timeline use `esc(f.url)` with no scheme check; the same pattern exists in the map cards (sdr.js receiver URLs from the public KiwiSDR list, news/unrest/cables links). Also `esc()` (util.js:32) does not escape `'`; no single-quoted attribute with data was found, so currently safe.
Fix: `const safeUrl = u => /^https?:\/\//i.test(u || '') ? u : null;` and use it for every href/src built from data; add `'` -> `&#39;` to esc.
Risk: none.

### 16. Small lookup honesty/UI defects   [severity: low]  [confirmed by running]
- Dossier shows "Malware exposure: none found" before any scan or with no email identifier (dossier.js:80). Should be "not checked".
- Scan line counts 231 findings, store has 230 (duplicates in one tool's answer counted, api.py summary uses len(found)).
- GitHub account "-" accepted (api.py CHECK github regex allows a lone/leading hyphen); duplicate email in other case is ignored silently (no "already added").
- Graph: 215 breach labels in one sector run under the sidebar and over the Dossier/Graph tab buttons (graph.png); known label weakness, but the tabs become hard to read.
- Gravatar picture is stored as `photo`, which the dossier never reads (it reads `image`), so it never appears under "Pictures shown"; GitHub `blog` without scheme is dropped from "Links".

### 17. Munich panel small defects   [severity: low]  [by reading]
- munich.js:27 wind direction null (calm) -> "from the undefined"; `Math.round(null)` -> "0 km/h" when wind is unknown.
- MVG messages are filtered for "in force" only at fetch time (every 5 min); a message whose `to` passed is still shown until the next fetch (e.g. "Reparatur an einem Signal beendet" with to = now).
- "N more planned changes in force" counts incidents too when there are more than 8.
- Panel is never updated while the mouse is over it (by design), so a pointer resting on it freezes ages and data indefinitely.

### 18. Main feeds card says "N starting" forever for feeds that need a key   [severity: low]  [confirmed by running]
Seen: "40 of 45 feeds in, 4 starting" with 4 keyless optional feeds that will never start. main.js:410 counts every `waiting` as starting. Fix: treat `note` beginning "not set up" separately ("4 not set up").

### Other observations (outside this area, for whoever owns them)
- /api/status reports peak memory 461 MB (CLAUDE.md says ~205 MB).
- With ALL layers switched off the map page still had 3.8-6.2 s of long tasks per 10 s at world view and ~9.8 s at Munich zoom (machine shared with other auditors' browsers, so only indicative); 2-3 map renders per second with nothing on (m3.js). Playwright evaluate calls at Munich zoom sometimes waited minutes.
- cables.js:34 meta calls `esc()` on a string renderList escapes again (double escaping: `&` would show as `&amp;`).

Checked and fine:
- /lookup loads with no console errors in light and dark; identifiers add/remove for each kind; validation messages for bad email/domain/phone/username/name; "<img ...>" rejected as username, accepted as name but rendered as text.
- Pre-scan sheet lists each check with who receives what; checkbox choices persist across the 2 s poll and in localStorage; Maigret-all-sites and Holehe-reset are off by default; WMN is disabled when the checker is untested.
- A small scan ran with progress (n of 5, then page reading) and listed failures honestly (GitHub hourly limit, DuckDuckGo block); 403 page counted as "unchecked", not dead.
- Dossier/Graph tab switching, pan by drag (no text selection while dragging), wheel zoom, node click opens the detail; "Not me" hides the item and survives a rescan by the same tool.
- Public figure card appears for "Linus Torvalds" and opens the profile overlay; Esc closes it without leaving an invisible layer.
- Delete everything (two clicks) empties identifiers, findings, scans and pages; VACUUM runs.
- Lookup API and X-Forwarded-For: uvicorn trusts XFF only from 127.0.0.1; a 127.0.0.1 request with XFF 8.8.8.8 is refused, so a local reverse proxy that sets XFF is handled correctly; a remote client cannot spoof it. A local proxy that does NOT set XFF would make every remote caller look local.
- Munich: weather (temperature, wind, station, observed time and age), DWD warning with onset/expiry, 8 nearest airborne aircraft with distance/direction/altitude and data age, MVG incidents first; clicking an overhead aircraft opens its card even with the Aircraft chip off; World/Munich quick toggle mid-flight restores the world view.
- README: data folder path matches config.py; lock file in sync; fresh clone imports on Python 3.14 with `uv run`.

Could not test here:
- Maigret, Sherlock, Holehe, theHarvester, the WMN sweep and "Test the checker" (forbidden by the brief).
- GitHub account check (shared address over its hourly limit), DuckDuckGo name search (blocked), Internet Archive dates.
- Safari behaviour of javascript: hrefs with target=_blank.
- Windy error path on /feeds (no key), MVG translation success path (Google blocks this sandbox).
- Starting the server from the fresh clone (a shared server was already running).
- Munich screenshots (screenshots at Munich zoom timed out waiting for fonts on the loaded machine).
