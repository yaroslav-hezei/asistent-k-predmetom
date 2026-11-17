# Report — T-001

## Round 1 · 2026-11-17
Status: ready for review
PR: [#2 — T-001: MAIS scraper](https://github.com/yaroslav-hezei/asistent-k-predmetom/pull/2)
Branch: `bm/mais-scraper`; code commit: `d9f9418` (pushed to origin).

Did:
- Built a standalone CLI with all requested options and default FEI / 2026/2027 /
  DENNA / PRVY + PRVY_PROFES_ORIENTOVANY + DRUHY scope.
- Implemented faculty/year lookup from the portal, program discovery, plan parsing,
  unique-sheet downloads, resumable HTML/timestamp caching and offline parsing.
- Used one session, sequential requests, at least 1.05 seconds between request starts
  including redirects, 60-second timeouts, and three retries with 2/4/8-second backoff.
- Preserved ordered sections and full text, parsed both sheet tables, and added word
  coverage checks. Unknown labels are retained; failed sheets are excluded and reported.
- Completed the full requested collection. No other faculties, years, forms or degrees
  were crawled. Historical prerequisite/alternative sheets linked by these plans were retained.
- Added parser and CLI regression tests, real public fixtures, installation/run instructions,
  and a standalone verifier that blocks network access during reconstruction.

Files:
- `.gitignore`: ignore `.cache/`.
- `scripts/scraper/scrape.py`, `requirements.txt`, `README.md`, `verify.py`.
- `scripts/scraper/tests/test_parser.py` and two real sheets plus one plan in `tests/fixtures/`.
- `data/mais/2026-27/manifest.json`, `programs.json`, and 665 `courses/<predmet_id>.json` files.
- This report. No task/review files, setup script, design docs or shared contracts were changed.

Verified (commands from the repository root):
- `.venv/Scripts/python.exe -X utf8 scripts/scraper/scrape.py`
  completed with exit 0 at 2026-11-17T15:20:19Z. Counts: 32 programs, 1540 plan rows,
  665 sheets, 646 unique course codes; `failures: []`.
- Collection time from final program-index write to completion: 1334.46 seconds
  (22 minutes 14 seconds). This resumed earlier development downloads: all plans and
  about 30 sheets were already cached. The README estimates 25–45 minutes for a cold run;
  actual time depends on MAIS. Development runs were interrupted and resumed to add
  support for merged prerequisite/alternative cells; completed downloads were reused.
- `.venv/Scripts/python.exe -X utf8 scripts/scraper/scrape.py --parse-only > .cache/mais/reparse.log`
  exited 0 after the final empty-table handling adjustment. It regenerated the delivered output.
- `.venv/Scripts/python.exe -X utf8 -m pytest scripts/scraper/tests -q`
  → **10 passed in 0.53s**. Tests cover control values, aligned multi-program rows,
  empty tables, historical sheets, unknown labels, bold values, coverage failures,
  prerequisite/state-exam rows, wrong-program responses, retry preservation of POST data,
  missing caches, and offline deterministic reconstruction.
- `.venv/Scripts/python.exe -X utf8 scripts/scraper/verify.py > .cache/mais/verification.log`
  → exit 0, 11.62 seconds. All 665 sheets pass coverage. Every plan reference resolves to
  a sheet with the same course code; manifest counts match the actual files/rows.
  All course JSON and `programs.json` SHA-256 digests match a fresh reconstruction in
  a temporary directory while `requests.Session.request` is patched to raise on any use.
  Manifest contents also match after excluding only `scraped_at`.
- Coverage compares `re.findall(r'\w+', text, flags=re.UNICODE)` tokens from ordered
  section labels + values against independently rendered sheet full text. The fixed
  sheet title is excluded. Tokens must match exactly in order and multiplicity.
  Stored text preserves punctuation; punctuation itself is not a word token.
- Mojibake scan of every delivered JSON file: no `Ã` or `Å`.
- Unknown labels: **none**. No null `programs`, `grades` or `teachers` convenience values.
  There are 83 genuinely empty recommended-program tables, represented as `[]`.
- Control `65954478`: code `26000629`, credits 5, total_students 12286, FX 28,
  last_changed `2026-09-01` — all match the brief.
- Control `65953562`: total_students 16748, FX 38 — both match the brief.
- JSON output size: **8,238,376 bytes** across 667 JSON files.
- `git diff --check` → exit 0 for tracked changes.
- `git check-ignore .cache/mais/2026-2027-FEI/index.json` → ignored.
  `git status --short` shows only `.gitignore`, `data/`, `scripts/scraper/` in the code
  worktree; no raw cache files. Only explicitly supplied test fixtures contain committed-intended HTML.

Deviations from the task:
- Live plans contain `Prerekvizita` and `Zameniteľný` rows, including seven-cell rows
  with the type spanning three columns. These are preserved in their source order and
  source type; unavailable profile/hours cells remain empty. State-exam period/hours
  remain null as required. No schema fields were added.
- Program counts match 15 + 1 + 16 = 32. Regular-table unique predmetIds are
  **282 / 38 / 309** for PRVY / PRVY_PROFES_ORIENTOVANY / DRUHY, versus the brief's
  282 / 39 / 270. Their union is **599**, versus the reference 563. The state-exam
  block contributes another 66 IDs, giving 665 overall. All linked IDs were collected;
  nothing was filtered to force the reference counts. Captured rows include 113
  `Zameniteľný` and 78 `Prerekvizita` occurrences across all blocks. The original
  2026-11-15 HTML baseline is unavailable, so an exact explanation for the remaining
  reference-count discrepancy cannot be established; it is not presented as proven
  evidence that MAIS changed.
- Publication was held until the requested explicit approval was received. The code
  and data are now committed and pushed, and PR #2 is open for review.

Questions:
- No implementation or contract questions.
