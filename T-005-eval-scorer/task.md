---
id: T-005
title: Evaluation scorer for the assistant's answers
assignee: BM
status: done          # open → changes → done | dropped
created: 2026-11-21
due: 2026-11-26
---

# T-005 — Evaluation scorer for the assistant's answers

## Goal
Write the script that **measures how well the assistant answers**: it takes the assistant's answers to the 40
evaluation questions you prepared in T-003 and reports, with numbers, (1) whether the assistant said "Neviem" exactly
when the course sheet has no answer, and (2) whether, when it answered, it quoted the right part of the sheet.

Why it matters: the assistant (being built now by Yaroslav) has a setting we cannot guess — how sure it must be
before it answers instead of saying "Neviem". Too strict and it says "Neviem" to questions the sheet answers; too
loose and it **invents** answers — the worst error, because a student trusts a confident answer with a source. The
only honest way to set it is to run the 40 questions, score the answers and compare the numbers. The same numbers
are the measurable result of the MVP for the final presentation ("on 40 test questions the assistant answered X of 30
correctly with the right quote and invented an answer in Y of 10 cases"). Your question set is half of this; the
scorer is the other half.

What you should be able to explain about your part: the scorer checks only things that can be checked
**mechanically and fairly** — the "answer / Neviem" decision and the quoted source — and it treats a wrong answer
to an unanswerable question ("invented") as a separate, worst category. It does **not** judge whether the wording of
an answer is correct: that would need another AI model as a judge, which costs money and can itself be wrong, so
the report shows expected and actual answers side by side for a person to check. The scorer never sends the
questions anywhere and never puts them into the knowledge base; it only reads files.

## Context
- **Your T-003 set** — `data/eval/questions.jsonl` (40 questions: 10 HI Bc. courses × 3 answerable + 1 not
  answerable; 35 Slovak, 5 English) and its README `data/eval/README.md`. Each answerable question has `evidence`:
  a list of `{section, quote}` — the exact section label of the MAIS sheet and the shortest sufficient quote.
  Not answerable → `evidence: []`, `answer: null`. The validator `scripts/eval/validate.py` and its tests exist; CI
  (`.github/workflows/eval.yml`) runs `pytest scripts/eval/tests` and the validator on every PR that touches
  `scripts/eval/**` or `data/eval/**`, so your new tests run in CI automatically.
- **How the assistant will answer** (being built; this is what is decided, not code yet): it answers only from the
  sources of the chosen course; under every answer it shows its sources, and for a sheet source the **section** and
  the **exact quote** are filled in by code from the sheet, not written by the model — so a cited quote is real text
  of the sheet, usually a longer passage that contains the expected evidence. If it finds nothing good enough it
  says "Neviem" (`found = false`) and shows no answer. Sources can also be answers of students or teachers; for this
  scorer only the section + quote pairs matter.
- **Decided for this task:**
  1. **The scorer reads a results file** (format in Contract) — it does not call the assistant. The assistant's API
     does not exist yet; when it does, a small runner will ask the 40 questions and write this file (a later task).
     So you can build and test everything now, with synthetic results.
  2. **A quote counts as matched** when the cited source has **exactly the same section label** as the expected
     evidence and, after whitespace normalization, **one of the two quotes contains the other** (the cited passage
     contains the expected quote, or the expected quote contains the cited passage). An empty cited quote never
     matches. Whitespace normalization is the one from `validate.py` (`collapse_whitespace`: every run of whitespace,
     including line breaks and non-breaking spaces, becomes one space; everything else — case, diacritics,
     punctuation — must match exactly). Reuse that function; do not write a second one.
  3. **The wording of answers is not scored automatically** (see Goal); the report can print expected vs actual
     answers for a person to read.
  4. **Standard library only** for the script (like `validate.py`), Python 3.11+; pytest only for tests.

## What to do
1. **`scripts/eval/score.py`** with a command line:
   ```
   python scripts/eval/score.py --results <results.jsonl>
          [--questions data/eval/questions.jsonl] [--data data/mais/2026-27]
          [--json <report.json>] [--show-answers]
   ```
   `--data` is only used to print course names (from `courses/<course_id>.json` → `name`).
2. **Read and check the results file** strictly, in the style of `validate.py` (line numbers in every error,
   `<unknown>` when a broken line has no `id`): valid JSON object per line, no blank lines, required keys with the
   right types (Contract), `id` must exist in the questions file, each `id` at most once. Extra keys are allowed and
   ignored (the real runner will add more, e.g. the model name or the source type). Any error → print all errors,
   exit code 1, no report. Questions with no result line are **not** an error: they are scored as `missing`.
3. **Classify every question** into exactly one outcome:

   | Outcome | Question | Result | Meaning |
   |---|---|---|---|
   | `answered` | answerable | `found: true` | answered — its citation is scored (step 4) |
   | `missed` | answerable | `found: false` | said "Neviem" although the sheet answers |
   | `abstained` | not answerable | `found: false` | correctly said "Neviem" |
   | `invented` | not answerable | `found: true` | answered although the sheet has no answer — **worst error** |
   | `missing` | any | no result line | the run did not produce an answer |

4. **Score the citation** of every `answered` question: each expected evidence item is matched or not (rule in
   Context 2) against any of the cited sources; the question is `full` (all items matched), `partial` (some) or
   `none`. Sources of a `found: false` result are ignored; if there are any, count it as a warning.
5. **Report** (stdout, readable, English):
   - Totals: number of questions, results, missing.
   - **Decision**: the counts of the five outcomes; `decision accuracy = (answered + abstained) / all questions`;
     separately `invented: X of <number of not-answerable questions>` and `missed: Y of <number of answerable>`.
   - **Citation**: of the `answered` questions — `full` / `partial` / `none`; `citation accuracy = full / answered`.
   - **Overall correct** = `abstained` + `answered` with `full` citation, out of all questions — the one headline number.
   - Breakdown **per course** (course id + name) and **per language** (sk / en): the outcome counts and `full`.
   - **Problems**: every question that is not `abstained` and not `answered`+`full`, with: id, course name, language,
     the question, the outcome, the expected evidence (section + quote), the cited sources (section + the quote
     shortened to ~120 characters), and the assistant's answer shortened to ~200 characters.
   - `--show-answers`: additionally, for every `answered` question, the expected answer and the assistant's answer
     next to each other (for a person to judge the wording).
   - Percentages with one decimal and always next to the counts (`27 / 30 (90.0 %)`).
6. **`--json <path>`**: the same results as JSON for comparing runs: `summary` (all numbers from step 5),
   `by_course`, `by_language`, and `questions` — one item per question: `id`, `course_id`, `language`, `answerable`,
   `outcome`, `citation` (`full | partial | none | null`), `matched_evidence` (indexes of matched evidence items).
   Show its exact shape in the report.
7. **Exit codes**: 0 when the inputs are valid (whatever the score), 1 for invalid input, 2 for wrong command-line
   arguments (argparse default).
8. **Tests** `scripts/eval/tests/test_score.py` (load `score.py` the way `test_validate.py` loads `validate.py`;
   build small input files in `tmp_path`), at least:
   - each outcome: `answered`, `missed`, `abstained`, `invented`, `missing`;
   - citation: cited passage longer than the expected quote → match; cited passage shorter and inside the expected
     quote → match; same text but a different section label → no match; empty cited quote → no match; a quote that
     differs only in line breaks / non-breaking spaces → match; one character different (e.g. diacritics) → no match;
   - a question with two evidence items, one matched → `partial`;
   - input errors with the right line number: broken JSON, missing key, wrong type, unknown `id`, duplicate `id`,
     blank line → exit 1;
   - extra keys in a result and in a source are ignored;
   - **on the real set**: a "perfect" results file built inside the test from `questions.jsonl` itself (`found` =
     `answerable`, sources = the evidence, answer = the expected answer) → 40 / 40 overall correct, 30 / 30 full
     citations, 0 invented; and an "always Neviem" file → 10 abstained, 30 missed, 0 answered;
   - `--json` output has the documented keys and numbers.
9. **Docs**: a new section "Score the assistant's answers" in `data/eval/README.md`: the results-file format (copy
   the Contract), the outcomes table, the citation rule, the commands, how to read the report, and that results files
   of real runs are not committed into `data/eval/` (they will have their own place, decided later).

## Out of scope
- Calling the assistant, the API or any AI model; an "LLM judge" for answer wording.
- Changing `data/eval/questions.jsonl` or what `validate.py` accepts (importing its functions is fine). If you find a
  problem in the question set, report it — do not fix it here.
- Committing results of real runs (none exist yet). The only results files in the repo are test inputs built by the
  tests or small fixtures under `scripts/eval/tests/` that are clearly synthetic.
- Anything in `backend/`, `frontend/`, `supabase/`, `data/mais/`, `docs/`, the CI workflows.

## Files and folders
- New: `scripts/eval/score.py`, `scripts/eval/tests/test_score.py` (fixtures, if any, in `scripts/eval/tests/`).
- Change: `data/eval/README.md` (new section only).
- Do not touch: `data/eval/questions.jsonl`, `scripts/eval/validate.py` (behaviour), everything listed in Out of scope.

## Contract
- **Questions file** — exactly as in `data/eval/README.md` (T-003): `id`, `course_id`, `language`, `question`,
  `answerable`, `evidence` [`{section, quote}`], `answer`, `notes`.
- **Results file (new, defined here)** — UTF-8 JSONL, one object per line (illustrative values: the first cited
  quote is longer than q001's evidence `min. 11% z 20%.` and contains it, so it matches):
  ```json
  {"id": "q001", "found": true, "answer": "Na zápočet treba aspoň 11 % z 20 %.",
   "sources": [{"section": "Priebežné hodnotenie (PH)", "quote": "Podmienky: min. 11% z 20%."}]}
  {"id": "q004", "found": false, "answer": null, "sources": []}
  ```
  | Key | Type | Rule |
  |---|---|---|
  | `id` | string | an `id` from the questions file; at most once per file |
  | `found` | boolean | `false` = the assistant said "Neviem" |
  | `answer` | string or null | non-empty string when `found` is true; may be null when `found` is false |
  | `sources` | list | objects with `section` (string or null — a non-sheet source may have none) and `quote` (string); other keys allowed and ignored |

  Any other top-level key is allowed and ignored. This is the format the future runner will write; if you think a
  field is missing or wrong, say so in the report instead of changing it.
- **The report JSON (`--json`)** — you define the exact shape within step 6 and show it in the report.

## Done when
- [ ] `python scripts/eval/score.py --results <file>` prints the report described in step 5; `--json` writes the
      JSON of step 6; `--show-answers` adds the answer pairs.
- [ ] The outcome rules and the citation rule are exactly as in this brief (classification table, Context 2).
- [ ] Invalid results files are rejected with every error and its line number, exit code 1.
- [ ] `pytest scripts/eval/tests` passes with all the cases of step 8, including the "perfect" (40 / 40, 30 / 30) and
      "always Neviem" (10 abstained, 30 missed) runs on the real question set.
- [ ] `python scripts/eval/validate.py` still reports 0 errors / 0 warnings on the set (unchanged).
- [ ] `data/eval/README.md` has the new section; nothing else in `data/eval/` changed.
- [ ] Standard library only in `score.py`; Python 3.11+; CI on the PR is green.

## How to verify
```
python -m pip install -r scripts/eval/requirements.txt
pytest scripts/eval/tests
python scripts/eval/validate.py
# a small synthetic run you write by hand for the report (do not commit it into data/eval/):
python scripts/eval/score.py --results <your-sample.jsonl> --json <your-report.json> --show-answers
```
In the report paste: the pytest summary line; the full text output of one synthetic run that contains every outcome
(`answered` full / partial / none, `missed`, `abstained`, `invented`, `missing`) and the matching JSON; the output for
one invalid file (with line numbers); and every deviation from this brief with the reason.

## Notes
- Windows: earlier the validator crashed with `UnicodeEncodeError` when its output was redirected to a file
  (fixed in PR #5: `validate.py` switches its output to UTF-8 with `sys.stdout.reconfigure`). Make sure the scorer prints Slovak text correctly when redirected
  (`python scripts/eval/score.py ... > out.txt`) — check it and mention it in the report.
- The set must stay out of the assistant's knowledge and prompts — the scorer only reads it, as the README says.
- If something in this brief contradicts the code or the question set, do not guess: add a report round with
  `Status: blocked` and your questions.
- Branch `bm/eval-scorer`; commit messages like `eval: citation matching (T-005)`; PR title
  `T-005: Evaluation scorer`. Open the PR yourself.
