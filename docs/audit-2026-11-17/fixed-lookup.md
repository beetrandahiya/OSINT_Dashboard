# Fixes: lookup (branch fix/lookup, worktree /home/user/wt-lookup)

Commits (on af6c04f): ed980d2 guard, 381e48c store, 9bbe091 SSRF, 092973a lookup page, 86f7336 feeds/Munich/MVG, 471be45 README.
Test scripts: scratchpad/fix-lookup/ (guard_test.py, store_test.py, page_test.js, scan_test.js, m4.js, mu.js, fd.js, g.js, testapp.py).
Testing: a small test app (testapp.py, :8722) served the worktree's lookup API on a scratch database plus the worktree's
static files, everything else proxied to :8710. No second worldwatch serve. The running :8710 server still has the old code:
**restart needed** for the server-side fixes (1, 3, 4, 5, 7, 9, 11-13, 16).

| # | Finding | Status | Verified |
|---|---|---|---|
| 1 | CSRF / DNS rebinding on lookup API | fixed: `refuse()`/`guarded` in lookup/api.py on every /api/lookup route: Host must be loopback (or WW_HOST / WW_ALLOWED_HOSTS; with WW_LOOKUP_REMOTE=1 also IP literals, one-word names, *.ts.net), Origin (else Referer) absent or same host, "null" refused; POST/DELETE need X-WW: 1, POST needs application/json. X-Forwarded-For never read (request.client as uvicorn sets it). Page's `call()` sends both. | guard_test.py: 21 cases (cross-site text/plain, cross-site JSON+header, Origin null, cross-site Referer, form post, missing header, DELETE without header, wrong Host x2, remote-mode allow/deny) all as expected; page adds/removes/scans/wipes through the guard (page_test.js, scan_test.js) |
| 2 | Legend off screen / not hidden | fixed: lookup legend renamed `.lk-legend` (app.css untouched), swallowed statement on its own line, `[hidden]` rule | legend at x 1080-1420 in graph tab, display none in dossier tab, light+dark screenshots |
| 3 | New finding inherits old page read | fixed: save_findings deletes the vanished findings' `pages` rows first | store_test.py (B gets id 1, no page, due for reading) |
| 4 | Delete everything keeps typed names | fixed: wipe() and remove_identifier() drop `search:<name>` and, for each Wikidata hit of that search, `profile*:<qid>`, `wdent:<qid>`, `ukcase2:<name>`. Decision: those public-figure records exist only because of the typed name, so they go too; other cache rows (leaders, os-datasets, profiles opened from the map) stay. | store_test.py; scan_test: scratch db empty incl. cache after wipe |
| 5 | SSRF in page reader | fixed: enrich.check_url (http/https only, resolve, refuse non-global and multicast: loopback, RFC1918, link-local, ULA, CGNAT/Tailscale, 0.0.0.0, mapped v6), redirects followed by hand (max 5) with every hop checked, and the connected peer address checked before the body is read (closes the DNS-rebinding window for direct connections). Through a configured HTTP proxy the peer is the proxy, so only the resolve check applies (small window remains, stated in code). Refused pages show "not opened: ..." as unchecked. emails.py/tools.py fetch fixed service hosts only; usernames.py uses the WMN dataset's URL patterns (not scraped content): left as is. | 127.0.0.1, localhost, [::1], 10/8, 100.64/10, file:, ftp: refused; example.com read; local 302 chain to 127.0.0.1:8710 refused at the third hop; peer check caught a direct 127.0.0.1 connection |
| 6 | Detail card rebuilt every 2 s | fixed: state polled every 2 s only while a job runs; otherwise on load, after actions, on focus/visibility; identical answer -> no render; detail, SVG, legend, id list only rewritten when their HTML changes; age texts refreshed by a 30 s `times()` | 0 state requests in 6 s idle; selection kept across a reload; 0 requests after a scan ended |
| 7 | /feeds NaN / null / crash | fixed: Windy pseudo-feed gets total_bytes/ok/fail/tried; feeds.html guards total_bytes, interval ("on demand"), ok/fail, tried | fd.js with a forced Windy failure: no NaN/undefined/null, no error |
| 8 | Munich twice loses world view | fixed (main.js): no-op when already there; saves bearing+pitch; a running chase is stopped and the flight starts once it has landed (`chaseStop(level, after)`) | m4.js: world view (incl. bearing 30 / pitch 40) restored after Munich twice, quick toggle, and World pressed while chasing |
| 9 | MVG "machine-translated" while German | fixed: feeds.py keeps the failure count (payload `translated`/`untranslated`, note says "N headlines left in German (translation paused/failed)"); munich.js claims translation only when an original exists and says when headlines stay German | mvg() run once: note "30 headlines left in German (translation paused: Google is limiting requests)"; panel text checked |
| 10 | README keys/feeds out of date | fixed: all 6 key/contact files with env var, where to register, what they unlock; 44 feeds from FEEDS; "Find a person or country"; package count dropped; lookup access rule incl. WW_ALLOWED_HOSTS | fresh clone: `uv run python -c "import worldwatch.web"` ok, 44 feeds |
| 11 | Not me lost when another tool finds the page | fixed: a new account row whose normalised URL (same rule as lookup.js norm) matches a not_me row of the same identifier starts marked | store_test.py |
| 12 | Remove during scan -> orphans | fixed: DELETE answers 409 while running, ✕ disabled, and step() skips identifiers that no longer exist | TestClient 409; buttons disabled during scan_test |
| 13 | Read the pages with nothing due | fixed: no scan row; answer note shown under the buttons | scan_test: note shown, last scan line unchanged |
| 14 | Figure card never retried | fixed: error shown in the dossier ("... Asking again in a minute"), retried after 60 s; figures of removed names dropped | by reading + page loads without errors (no forced 429 test) |
| 15 | javascript:/data: hrefs | fixed: `safeUrl`/`ext()` in dossier.js (exported, used by lookup.js): only http(s) become links, else text | page_test with hostile URLs: 0 non-web hrefs in dossier, detail and timeline |
| 16 | small: malware "none found", count, github "-", dup, labels, Gravatar, blog | fixed: Breaches/Malware tiles say "not checked"/"failed"/"no email address" unless the services check ran after the address was added (`checks_run` in state); findings counted as stored; GitHub regex without leading/trailing/double hyphen; duplicate add says "already in the list" (409); tabs get a frosted backing; Gravatar stored as `image` (old `photo` rows also read); bare-domain websites get https:// | browser + TestClient. Label density in big graphs remains (known weakness; a list view is the real fix, owner to decide) |
| 17 | Munich small | fixed: wind null/calm handled; ended MVG messages dropped client-side; "N more incidents and M more planned changes"; hover no longer freezes the panel longer than a minute | mu.js |
| 18 | "N starting" forever | fixed (main.js + feeds.html): "not set up" feeds counted separately, dot not grey for them alone | by run (feeds.html summary shows "2 not set up (optional key)") |

Shared-file edits:
- web.py: Windy entry in `status()` gains total_bytes/last_bytes/last_ms/ok_count/fail_count/tried/next_at (one dict, 2 lines).
- feeds.py: `mvg()` keeps the translation failure count, adds `translated`/`untranslated` to the payload and a clause to the note.
- main.js: `chaseStop(level, after)` takes an optional callback (passed through groundAgain's `then`); `place()` rewritten (where guard, bearing/pitch, chase stop); feeds card counts "not set up" separately.
- app.css: not touched. util.js: not touched (esc still does not escape `'`; no single-quoted data attribute exists).

Left for the owner / others:
- WW_LOOKUP_REMOTE=1 now also needs the request's Host to be an IP, a one-word machine name, *.ts.net or listed in WW_ALLOWED_HOSTS (a custom DNS name for the Mac must be added there).
- profile.js (person dossier) builds hrefs from Wikidata/ICC/news data without a scheme check (Wikidata URL values are validated upstream; not in my file list).
- Map image proxies and sdr.js/news links: not in my area (other fixer).
- Peak memory 587 MB in /api/status today (CLAUDE.md says ~205): outside this area.

Lessons for CLAUDE.md:
- Lookup API rule: Host loopback/allowed, Origin same-origin, writes need JSON + X-WW header; the page's `call()` sends them. Any new lookup route must go through `guarded`.
- The page reader never follows redirects itself (httpx follow_redirects=False); each hop goes through check_url and the peer check.
- `findings.id` rowids are reused by SQLite: anything keyed by finding id must be deleted with the finding.
- A page whose class name matches a map panel's (`.legend`) picks up app.css's absolute positioning: lookup page classes are `lk-` prefixed.
- Removed the audit's three leftover cache rows from the real data/lookup.db (search:linus torvalds, search:<b>xss</b> test, profile3:Q34253).
