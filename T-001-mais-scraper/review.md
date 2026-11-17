# Review — T-001

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-17
Verdict: accepted

The snapshot matches MAIS today, the parser is deterministic, and every "Done when" item holds. Good work.

Checked:
- `gh pr checkout 2` (`d9f9418`), fresh venv, `pip install -r scripts/scraper/requirements.txt`,
  `pytest scripts/scraper/tests -q` → 10 passed.
- Live re-crawl with your `scrape.py` into a separate cache and output: all 32 plans plus 15 sample sheets
  (controls `65954478`, `65953562`; historical `23692625`, `2683224`; current `65953235`; `69718558` with an empty
  change date; 9 random), about 100 requests, 106 s. `programs.json` is identical to the committed one; all 15 sheets
  are identical except `fetched_at`.
- `--parse-only` and `verify.py` cannot be re-run without your raw cache (not committed, as agreed). The live
  re-crawl above covers the same claim for the plans and the sample sheets, and both parse-only tests pass.
- All 665 committed sheets: `check_coverage` passes, `unknown_labels` is empty everywhere, no `Ã` / `Å` in
  `data/mais/`, 8,238,376 bytes.
- Control values: `65954478` → code `26000629`, credits 5, 12286 students, FX 28, `2026-09-01`;
  `65953562` → 16748 students, FX 38. Both match.
- Fixtures: `full_text` has the same words as BeautifulSoup's own `get_text()` of `table.Page_1` (title excluded)
  for both sheets; there is no text outside `table.Page_1`.
- Plans: 191 non-regular rows (113 `Zameniteľný`, 78 `Prerekvizita`); each one is preceded by a `P` / `PV` / `V`
  row in the same table. For all 32 programs the number of `rules` equals the number of "V období od" in
  `full_text`. No null `credits` or `short_name`.
- Scope: changes only in `.gitignore`, `data/mais/2026-27/` and `scripts/scraper/`; HTML only in `tests/fixtures/`;
  no secrets; the commit message and the PR carry no agent attribution.

Fix:
- none

Notes (not required — for defending the work; we will add the reading rules to the README ourselves):
- How to read the output: a `Prerekvizita` / `Zameniteľný` row belongs to the nearest preceding `P` / `PV` / `V`
  row of the same table, and its `period` is that table's period. The courses of the programs are the `P` / `PV` /
  `V` rows: 563 unique `predmet_id`s, `code` ↔ `predmet_id` 1:1. The other 102 sheets are linked only through
  `Prerekvizita` / `Zameniteľný` rows; 18 of them are older versions (2010–2025) of a course that also has a
  current sheet. 24 sheets ("Modul k DP a ZS …") have an empty change date → `last_changed` is `null`.
- Coverage check: `full_text` and `sections` come from the same traversal (`events` / `walk`), so the check proves
  the split into sections is lossless, not the rendering itself. If someone asks how you know nothing is lost,
  the stronger answer is a comparison with BeautifulSoup's own `get_text()` — it matches on both fixtures.

Answers:
- Count difference (your deviation 2): explained, no change needed. The reference numbers in the brief counted
  unique `predmet_id`s over rows of type `P` / `PV` / `V` in all tables, the state-exam tables included. Your
  `programs.json` gives exactly 282 / 39 / 270 and the union 563 this way; the state-exam `P` rows for PRVY are 12,
  as the brief said. The brief's wording "regular period tables" was wrong on our side. Your 282 / 38 / 309 are
  all rows of the period tables, `Prerekvizita` / `Zameniteľný` included, so your numbers are correct.
- Keeping the linked prerequisite / alternative sheets: keep them. They help answer "what do I need before X?".
