# Investigate (the /lookup page turned into a case tool), 2026-11-28

Built in its own worktree. Files: `server/worldwatch/lookup/` (store, api, pivot, patterns, sources, images, export; changed:
enrich, tools, emails), `server/worldwatch/config.py` (one helper: `github_token()`), `static/lookup.html`, `lookup.css`,
`js/lookup.js`, `js/dossier.js`, new `js/investigate-views.js`, `js/investigate-hash.js`. `web.py`, `main.js`, `app.css` were
not touched: the routes are still registered through `lookup.api.routes`.

## Hard boundaries (in pivot.py's header, images.py, sources.py, lookup.js and one line on the page)

No face recognition and no face-search engines; pictures are compared only as files (difference hash). Nothing that infers
where a person lives, is or goes: GPS metadata in a picture is detected (EXIF GPS directory / XMP GPS fields) and reported as
"carries location metadata", the coordinates are never decoded, stored or shown. No breach contents or passwords. No logged-in
scraping, nothing past a login, captcha or bot shield (DBLP and PyPI user pages were dropped for that reason). Holehe's
password-reset probing stays off by default. No scan without a consent record. No "search any person" outside a case.

## What was built

1. **Cases with consent.** Table `subjects` (label, created, is_self, consent_by, consent_at, consent_how, consent_scope, note).
   `identifiers`, `findings`, `pages`, `scans` carry `subject`; new tables `leads`, `fingerprints`; findings get `confirmed`.
   Migration: an old-schema `lookup.db` becomes case 1 "Me (self-test)" (is_self, consent "self"); the identifiers table is rebuilt
   with `UNIQUE (subject, kind, value)`, other tables get columns added. A case can only be created with a complete consent
   record (written/verbal, who, a date not in the future, scope) or as the one self-test case. `start()` refuses any scan or page
   reading for a case whose record is incomplete (403). Deleting a case removes its identifiers, findings, page reads, leads,
   fingerprints, uploaded picture files (when no other case uses the same file), the name-search cache entries, then VACUUM;
   the connection runs with `secure_delete`. "Delete all cases" replaces the old wipe.
2. **Seeds**: username, email, full name, phone, domain, GitHub account, and a **picture file** (JSON upload with base64, 5 MB,
   type from the file's first bytes: JPEG/PNG/GIF/WebP only, stored as `data/lookup-images/<sha256>.<ext>`; served back only to
   its own case, `no-store`).
3. **Pivot engine** (`pivot.py`). Anchors = findings the owner confirmed, or "bound" findings that are the identifier itself
   (GitHub profile of the GitHub account entered, Gravatar of an address entered, a Keybase account that signed a proof for a
   GitHub account or domain in the case, a Bluesky account whose handle is a domain in the case). Leads come only from anchors and
   explicit searches, never from unconfirmed pages. Usernames are recognised in any address with the WhatsMyName URL patterns plus
   a few big platforms (`patterns.py`). The page reader now also keeps (server-side only) a page's rel="me" links, links to known
   profile pages and mailto addresses. An anchor's outgoing link to an unread page becomes a "Links between pages" finding so the
   page reader opens it and the next pass can see whether it links back.
   - Strong (followed during a scan, at most 2 steps, 8 per round): links both ways / rel="me" both ways with an anchor; a
     platform-verified profile email (GitHub, GitLab); emails in public commits of an anchored GitHub account; the account GitHub
     attributes an entered address's commits to; Keybase proofs of a Keybase account tied to the case; other addresses on the same
     PGP key (parsed from the key's user-ID packets); an identical picture fingerprint (distance 0) to an anchor's or seed picture.
   - Weak (queue): display names, one-way links, usernames found by web search. Name sources (ORCID, OpenAlex, DuckDuckGo, Brave)
     never give strong leads. Rejected leads stay rejected for good; removing an identifier that came from a lead rejects that lead.
4. **Evidence chips** per account, no number anywhere: confirmed/tied, links both ways, rel="me" both ways, linked from / links to
   a confirmed account, Keybase proof, shows an address of the case, same display name, same website, same picture (with the
   Hamming distance, <= 6 of 64 bits), its picture is the Gravatar of an address in the case, found by several tools. The owner
   marks Confirmed or Not me (marks carry over to the same page found later by another tool or identifier).
   **Picture fingerprints**: 64-bit dHash computed in the browser (canvas, 9x8 grey blocks), from found avatars fetched through a new
   guarded proxy `/api/lookup/img` (only addresses the case's own findings name, SSRF checks on every hop, real image bytes only, no
   SVG, `X-Location-Meta` header) and from uploaded seed pictures; posted to `/api/lookup/fingerprints`. Default avatars
   (placeholder/default paths) and flat pictures are not compared.
5. **New sources** (`sources.py`): Bluesky (getProfile + searchActors for own-domain handles), Keybase (by username; by GitHub
   account and by domain as the "Keybase proofs" check), GitLab, Codeberg, npm (maintainer search), Docker Hub, ORCID, OpenAlex,
   Brave web search for quoted usernames, addresses and names (needs `data/brave-key.txt`; the check shows "needs a key" otherwise),
   Internet Archive history of confirmed accounts (oldest and newest copy from the availability API, the bio of the oldest copy when
   web.archive.org answers), GitHub token support (`data/github-token.txt` or `WW_GITHUB_TOKEN`) in the GitHub account check and the
   commit search. `enrich.first_archived` now falls back to the availability API when the CDX server does not answer.
6. **Views**: Accounts (primary; grouped "Confirmed", "Tied by a stated reason", "Some evidence", "No evidence yet", "Not me";
   filter All/Confirmed/Unconfirmed/Not me; Confirm / Not me on each row; other findings folded by kind), Leads (strong waiting,
   weak waiting, decided, with Approve/Add now/Reject/Undo), Timeline (dated facts only, built on the server, "confirmed accounts
   only" switch), Dossier (wording "them/their" for anyone but the owner), Graph (labels only for identifiers, confirmed accounts,
   the selected dot, and the dot under the pointer via CSS). Export: JSON download and a printable HTML case file (consent first,
   CSP without scripts, avatars through the proxy). The page imports `look.js`, so it follows the map's theme (God's eye by
   default, Apple Maps when chosen) in light and dark. No polling while idle (state is asked every 2 s only while a scan runs).

## Sources probed from the sandbox (2026-11-28, public test identifiers)

| Source | Result |
|---|---|
| Bluesky public AppView getProfile / searchActors | 200, works (also own-domain handles) |
| Keybase lookup.json by usernames / github / domain | 200, works; proofs with `state: 1` |
| GitLab `api/v4/users?username=` | 200, works (public_email when set) |
| Codeberg `api/v1/users/{u}` | 200 / 404, works |
| npm registry search `maintainer:` | 200, works (maintainer emails in the answer) |
| Docker Hub `v2/users/{u}` | 200 / 404, works |
| ORCID expanded-search | 200, works (family names of several words needed a second query form) |
| OpenAlex authors | 200, works |
| archive.org/wayback/available | 200, works |
| keys.openpgp.org by fingerprint | 200; user-ID parser tested on a public project key |
| **DBLP author search** | **202 bot check ("Making sure you're not a bot!"): dropped** |
| **PyPI user page** | **"Client Challenge" bot check: dropped** |
| web.archive.org (CDX and id_ snapshots) | connection reset from the sandbox (as noted before in CLAUDE.md); code written, untested here |
| api.github.com | 403 from the sandbox proxy ("sessions are bound to their configured repositories"); untested here |
| Brave Search API | reachable (422 "token required" without a key); untested with a key |

## Tested (scratch data folder, test app mounting only the lookup routes; no second World Watch server)

- Migration of a copy of the sandbox's old-schema `lookup.db` with injected old-style rows: case 1 created, rows moved, columns added.
- Engine on synthetic data: strong leads (rel=me both ways, GitHub-verified email, commit email), weak leads (one-way links,
  display name), link findings created, same-picture chip with distance 1, same-name chip, a rejected lead stays rejected,
  confirming makes an anchor, deleting a case leaves no rows in any table.
- API: guard (no X-WW, foreign Origin, foreign Host: 403), case without consent refused (400), future consent date refused,
  second self case refused, scan and page reading of a case without a consent record refused (403), picture with GPS EXIF
  detected / without not, SVG and > 5 MB refused, stored detail has no coordinates, picture served only to its own case,
  picture proxy refuses addresses not in the case, fingerprints accepted only for the case's own pictures.
- Real scans on a test case (username "gvanrossum", test@example.com, name "Guido van Rossum"): developer and social sites,
  breach/profile services, research records, WhatsMyName sweep, page reading, archive history. Following: confirming GitLab
  turned its GitLab-verified public email into a strong lead, a scan with only the developer-site check followed it into an
  identifier (source pivot, step 1, not marked scanned because no email check was chosen; no breach service was asked about a real
  address), removing it marked the lead rejected. Keybase: the proof-tied account of Keybase's co-founder (via its GitHub proof)
  gave strong leads for its proved Twitter account and domain.
- Browser (Playwright, Chromium, 1440x900 and 1280x800): God's eye light and dark, Apple Maps light; case list, list view with
  30 accounts and 218 other findings, avatars fingerprinted in the browser (the Gravatar copy of the GitLab picture matched with
  distance 0 and shows as "Tied by a stated reason"), confirm, leads queue, reject, detail panel, timeline, dossier, graph,
  consent gate (scan button disabled with the message), new-case sheet refusing missing consent, creating and deleting a case,
  picture upload through the page and its fingerprint, Escape order, JSON export and case file. No page errors.
- `py_compile` on every changed Python file; `import worldwatch.web` lists the 15 lookup routes, all behind `guarded`.
- State endpoint with ~250 findings: about 30 ms, 250 KB (215 of them are test@example.com's breaches).

## Untested / known limits

- Maigret, Sherlock, Holehe and theHarvester in the new flow (not run: large downloads; their code paths are unchanged).
- GitHub account check and commit search with or without a token (API blocked from the sandbox), so GitHub-based strong leads
  were tested only on synthetic data. Brave search (no key). web.archive.org: archive "bio back then" and the CDX path.
- Safari: dHash uses `createImageBitmap` and canvas `getImageData`, both in Safari; not run there. Fingerprints computed in
  different browsers may differ by a bit or two (resampling), which the distance threshold of 6 absorbs.
- The picture proxy's answers are cached a day by the browser (avatars); after a case is deleted they can stay in the browser
  cache for that long. Uploaded seed pictures are `no-store`.
- Leads from unconfirmed pages are deliberately not made (namesakes). With only a username seed and nothing confirmed, a scan
  therefore gives evidence chips but few leads until the owner confirms an account or adds an email/GitHub/domain seed.
- A strong username lead (e.g. a Mastodon account that links back) is followed with the same checks as the scan that found it,
  which can include Maigret/Sherlock: up to 8 identifiers per round, 2 rounds.
- README (not in this worktree's file list) should mention `data/github-token.txt` (WW_GITHUB_TOKEN) and the Investigate page.
- CLAUDE.md (not in the file list) needs a log entry for this work.

## Open questions for the owner

1. Should strong leads really be followed automatically by default (option "Follow strong leads automatically", on)? It is
   capped (8 per round, 2 steps), but a followed username runs every username check chosen for that scan.
2. Keybase accounts tied by a proof: should their own Keybase username also become a lead (it is often generic, like "chris")?
   Not done now.
3. GitLab's and GitHub's public profile emails count as platform-verified (both platforms only allow a verified address there).
   Is that the right call for a strong lead?
4. A free GitHub token in `data/github-token.txt` would make the GitHub checks reliable (60 requests an hour without one).
