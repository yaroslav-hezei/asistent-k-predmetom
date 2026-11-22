# Review — T-005

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-22
Verdict: accepted

Checked:
- PR #11 at `6e1c3b4`. The diff is exactly the three files of the brief: new `scripts/eval/score.py`, new
  `scripts/eval/tests/test_score.py`, a new section at the end of `data/eval/README.md`. Nothing else changed
  (`data/eval/questions.jsonl`, `scripts/eval/validate.py`, `data/mais/`, `backend/`, `frontend/`, `supabase/`, the
  workflows are untouched).
- `python -m pytest scripts/eval/tests -q` (Python 3.14) → 136 passed.
- `python scripts/eval/validate.py` → 0 errors, 0 warnings (unchanged).
- CI `Evaluation questions / validate` on `6e1c3b4` → success.
- Re-ran your synthetic demonstration with the inputs copied from the report: the text output, the JSON and the
  error output for the invalid file are identical to the report; the invalid file gives exit 1 and writes no JSON.
  Output redirected with `>` is UTF-8 with correct diacritics.
- Against the brief: the five outcomes match the classification table; the citation rule is exact (same section
  label, containment in both directions after `collapse_whitespace` imported from `validate.py`, an empty quote never
  matches); full / partial / none; every number of step 5, with counts next to the percentages; the Problems list
  leaves out only `abstained` and `answered` + `full`, quotes are shortened to 120 characters and answers to 200;
  `--show-answers`; the `--json` shape of step 6; exit codes 0 / 1 / 2; standard library only; no syntax that needs
  Python 3.12 (the brief says 3.11+). Every test case of step 8 is there, including the perfect run (40 / 40,
  30 / 30, 0 invented) and the always-"Neviem" run (10 abstained, 30 missed) on the real set.
- The deviations in your report are all accepted, and they are documented in the README: the course id is shown
  with a warning when a course name is missing; an empty denominator is shown as `0 / 0 (0.0 %)`; evidence indexes
  start at zero; strict JSON (duplicate keys, NaN); `--json` refuses to overwrite an input; an existing report is
  kept when the input is invalid.
- Commit message and PR title follow the rules; no agent attribution.

Fix:
None. One small note for next time, no action needed:
1. `scripts/eval/score.py:307-309` — errors from the questions file and from the results file are sorted together
   by line number only, so they interleave (questions line 3, results line 3, questions line 4, …). And when the
   questions file itself is broken, every result for a broken question also gets "unknown id". The "Questions:" /
   "Results:" prefixes keep the output readable and the real question set is valid, so it does not matter now. If
   you write a similar tool, print the errors file by file.

Answers:
- none
