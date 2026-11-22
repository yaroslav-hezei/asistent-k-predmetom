# Report — T-005

## Round 1 · 2026-11-22
Status: ready for review
PR: [#11 — T-005: Evaluation scorer](https://github.com/yaroslav-hezei/asistent-k-predmetom/pull/11)
Branch: `bm/eval-scorer` from `origin/main` at `31d1f0e`.
Code commit: `6e1c3b4` (pushed to origin after explicit publication approval).

Did:
- Added `scripts/eval/score.py`: local-file-only scoring, standard library, Python
  3.11+. It never calls an assistant, API, model, database or external service.
- Implemented all five outcomes, citation full/partial/none, missing-result
  handling, the required metrics, course/language breakdowns, problem details,
  optional expected/actual answer pairs, and `--json`.
- Imported `collapse_whitespace` from the unchanged validator. Matching requires
  exact section labels and nonempty quotes with containment in either direction
  after that normalization; case, diacritics and punctuation remain exact.
- Strict results parsing collects every error with line and ID, ignores allowed
  metadata, rejects invalid input before writing a report, and warns when sources
  accompany `found: false` (those sources do not count toward citation scores).
- Added `scripts/eval/tests/test_score.py` and appended only the new scoring
  section to `data/eval/README.md`. The existing evaluation workflow discovers
  the new tests automatically; no workflow changes were made.

Verified (commands from the repository root):
- `.venv/Scripts/python.exe -m pytest scripts/eval/tests -q`
  → **136 passed in 1.87s** on Python 3.13.15. This includes the existing validator
  tests, all requested scorer cases, error line numbers, JSON structure/metrics,
  exact quote rules, multiple evidence/source matching, empty results, ignored
  extra keys, non-fatal warnings, answer wording not being scored, redirected UTF-8,
  standard-library-only execution (`-S`), and invalid-input report preservation.
- `.venv/Scripts/python.exe scripts/eval/validate.py` → exit 0, unchanged summary:
  40 questions, 30 answerable / 10 not, sk 35 / en 5, four questions per course,
  zero errors and warnings.
- Real-set results are generated inside tests, not committed: the perfect
  baseline gives **40 / 40 overall correct**, **30 / 30 full citations**, zero
  invented; always-Neviem gives **10 abstained, 30 missed, 0 answered**, 25.0%
  decision/overall scores, and citation accuracy `0 / 0 (0.0 %)`. These are
  synthetic scorer baselines, not measurements of the actual assistant.
- `git diff origin/main -- data/eval/questions.jsonl scripts/eval/validate.py
  scripts/eval/tests/test_validate.py data/mais backend frontend supabase .github/workflows`
  → no output. The README's original contents are retained; only a new section
  is appended. No real run files are added under `data/eval/`.
- `git diff --check` → exit 0 for tracked changes.
- `.venv/Scripts/python.exe .cache/eval-scorer/verify_examples.py` → exit 0:
  valid sample exits 0; invalid sample exits 1 without a JSON report. The child
  process is run with `PYTHONIOENCODING=cp1251` and `PYTHONUTF8=0`, without `-X utf8`;
  its native redirected bytes decode as UTF-8 with correct Slovak diacritics.
- Actual PowerShell `>` redirection was also run without `-X utf8`. This shell
  writes the destination file as UTF-16; decoded text matches the native UTF-8
  output line for line, preserving `Syntetický predmet`, `písomná skúška`, and
  `koľko má syntetický predmet kreditov?`. The README distinguishes scorer output
  encoding from the shell's final file encoding.
- Remote Python 3.12 CI **passed** for commit
  `6e1c3b417493d9bfe982287b7792fbdfde4fc38c`: workflow `Evaluation questions`,
  job `validate`, conclusion `success` (pytest and the unchanged validator).
  Run: https://github.com/yaroslav-hezei/asistent-k-predmetom/actions/runs/45038240070

Synthetic demonstration:
- All seven questions refer to a clearly fictional course `999001`, named
  `Syntetický predmet`. Notes explicitly mark them synthetic; result records and
  the mock course metadata also carry `testovacie: true`. They are not facts about
  any real course. Files live under ignored `.cache/eval-scorer/`, not `data/eval/`.
- Questions: q001–q004 and q007 answerable; q005–q006 not answerable. q002/q006
  are English; the other five are Slovak. Six results are supplied, leaving q007
  missing. q002 has two expected evidence items and only one matched citation.
- Full sample command (exit 0):

```sh
.venv/Scripts/python.exe scripts/eval/score.py --questions .cache/eval-scorer/sample-questions.jsonl --results .cache/eval-scorer/sample-results.jsonl --data .cache/eval-scorer/data --json .cache/eval-scorer/sample-report.json --show-answers > .cache/eval-scorer/sample-output.txt
```

Full text output:

```text
WARNING line 4 [q004]: Sources on found: false are ignored
Evaluation report (decisions and citations; answer wording is not scored)
Questions: 7; results: 6; missing: 1
Decision outcomes: answered=3, missed=1, abstained=1, invented=1, missing=1
Decision accuracy: 4 / 7 (57.1 %)
Invented: 1 / 2 (50.0 %)
Missed: 1 / 5 (20.0 %)
Citations among answered: full=1, partial=1, none=1
Citation accuracy: 1 / 3 (33.3 %)
Overall correct: 2 / 7 (28.6 %)
Warnings: 1

By course:
  999001 | Syntetický predmet | questions=7 | answered=3, missed=1, abstained=1, invented=1, missing=1 | full=1
By language:
  sk | questions=5 | answered=2, missed=1, abstained=1, invented=0, missing=1 | full=1
  en | questions=2 | answered=1, missed=0, abstained=0, invented=1, missing=0 | full=0

Problems:
  q002 | 999001 Syntetický predmet | en | answered / partial
    Question: Does the synthetic assignment require teamwork and an oral defence?
    Expected evidence:
      [0] PH: práca v tíme
      [1] ZH: ústna obhajoba
    Cited sources:
      PH: práca v tíme
    Assistant answer: It requires teamwork.
  q003 | 999001 Syntetický predmet | sk | answered / none
    Question: je v syntetickej osnove rekurzia?
    Expected evidence:
      [0] Osnova: rekurzia
    Cited sources:
      Osnova: matice
    Assistant answer: Matice.
  q004 | 999001 Syntetický predmet | sk | missed
    Question: aká je forma syntetickej skúšky?
    Expected evidence:
      [0] ZH: písomná skúška
    Cited sources:
      ZH: písomná skúška
    Assistant answer: (null)
  q006 | 999001 Syntetický predmet | en | invented
    Question: What is the exact room for the synthetic test?
    Expected evidence:
      (none)
    Cited sources:
      (none)
    Assistant answer: An invented synthetic room, not a real course fact.
  q007 | 999001 Syntetický predmet | sk | missing
    Question: koľko má syntetický predmet kreditov?
    Expected evidence:
      [0] Kredity: 6
    Cited sources:
      (none)
    Assistant answer: (null)

Answered questions: expected / actual wording (human review only)
  q001
    Expected: Aspoň 11 % z 20 %.
    Actual:   Aspoň 11 % z 20 %.
  q002
    Expected: Yes, teamwork and an oral defence.
    Actual:   It requires teamwork.
  q003
    Expected: Áno, rekurzia.
    Actual:   Matice.
```

Exact matching JSON (four top-level keys; zero-based evidence indexes):

```json
{
  "summary": {
    "questions": 7,
    "results": 6,
    "missing": 1,
    "answerable": 5,
    "not_answerable": 2,
    "outcomes": {
      "answered": 3,
      "missed": 1,
      "abstained": 1,
      "invented": 1,
      "missing": 1
    },
    "citations": {
      "full": 1,
      "partial": 1,
      "none": 1
    },
    "decision_accuracy": {
      "numerator": 4,
      "denominator": 7,
      "percent": 57.1
    },
    "invented_rate": {
      "numerator": 1,
      "denominator": 2,
      "percent": 50.0
    },
    "missed_rate": {
      "numerator": 1,
      "denominator": 5,
      "percent": 20.0
    },
    "citation_accuracy": {
      "numerator": 1,
      "denominator": 3,
      "percent": 33.3
    },
    "overall_correct": {
      "numerator": 2,
      "denominator": 7,
      "percent": 28.6
    },
    "warnings": 1
  },
  "by_course": {
    "999001": {
      "name": "Syntetický predmet",
      "questions": 7,
      "outcomes": {
        "answered": 3,
        "missed": 1,
        "abstained": 1,
        "invented": 1,
        "missing": 1
      },
      "full": 1
    }
  },
  "by_language": {
    "sk": {
      "questions": 5,
      "outcomes": {
        "answered": 2,
        "missed": 1,
        "abstained": 1,
        "invented": 0,
        "missing": 1
      },
      "full": 1
    },
    "en": {
      "questions": 2,
      "outcomes": {
        "answered": 1,
        "missed": 0,
        "abstained": 0,
        "invented": 1,
        "missing": 0
      },
      "full": 0
    }
  },
  "questions": [
    {
      "id": "q001",
      "course_id": "999001",
      "language": "sk",
      "answerable": true,
      "outcome": "answered",
      "citation": "full",
      "matched_evidence": [
        0
      ]
    },
    {
      "id": "q002",
      "course_id": "999001",
      "language": "en",
      "answerable": true,
      "outcome": "answered",
      "citation": "partial",
      "matched_evidence": [
        0
      ]
    },
    {
      "id": "q003",
      "course_id": "999001",
      "language": "sk",
      "answerable": true,
      "outcome": "answered",
      "citation": "none",
      "matched_evidence": []
    },
    {
      "id": "q004",
      "course_id": "999001",
      "language": "sk",
      "answerable": true,
      "outcome": "missed",
      "citation": null,
      "matched_evidence": []
    },
    {
      "id": "q005",
      "course_id": "999001",
      "language": "sk",
      "answerable": false,
      "outcome": "abstained",
      "citation": null,
      "matched_evidence": []
    },
    {
      "id": "q006",
      "course_id": "999001",
      "language": "en",
      "answerable": false,
      "outcome": "invented",
      "citation": null,
      "matched_evidence": []
    },
    {
      "id": "q007",
      "course_id": "999001",
      "language": "sk",
      "answerable": true,
      "outcome": "missing",
      "citation": null,
      "matched_evidence": []
    }
  ]
}
```

Invalid-file command (exit 1; no text/JSON score report):

```sh
.venv/Scripts/python.exe scripts/eval/score.py --questions .cache/eval-scorer/sample-questions.jsonl --results .cache/eval-scorer/invalid-results.jsonl --data .cache/eval-scorer/data --json .cache/eval-scorer/invalid-report.json
```

Full error output:

```text
ERROR line 2 [<unknown>]: Results: invalid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
ERROR line 3 [q002]: Results: 'found' must be a boolean
ERROR line 4 [q999]: Results: unknown id 'q999'
ERROR line 5 [<unknown>]: Results: blank JSONL line
```

JSON interpretation:
- `summary` contains question/result/missing and answerability totals, five
  outcome counts, three citation counts, warning count, and five ratios.
- Every ratio is `{numerator, denominator, percent}`; percent is rounded to one
  decimal. Missing questions remain in the all-question denominators.
- `by_course` maps course IDs to `{name, questions, outcomes, full}`;
  `by_language` always includes sk and en with `{questions, outcomes, full}`.
- `questions` has one item per input question with exactly the shown fields.
  Non-answered outcomes have `citation: null`, `matched_evidence: []`.

Deviations / implementation choices:
- No changes to the agreed results contract or existing validator behavior.
- Missing course-name metadata falls back to the ID with a warning, without
  affecting scoring; `--data` is used only for names.
- Zero-denominator ratios use `0 / 0 (0.0 %)`. Matched evidence indexes are
  zero-based. These reporting conventions are documented.
- Strict JSON also rejects duplicate object keys and non-JSON constants, as in
  the validator. Empty results are accepted and yield all missing; empty question
  sets are rejected. `--json` cannot overwrite an input. Invalid input preserves
  an existing report instead of replacing it.
- Questions are checked for the structure needed for scoring, not revalidated
  against MAIS; the existing validator remains the source/evidence validation step.
- Publication was explicitly approved under AGENTS.md §3. The code is committed
  and pushed, PR #11 is open, and remote CI is green.

Questions:
- No implementation questions. Publication was explicitly approved.

Reproduction inputs (all synthetic):

Create the following files under `.cache/eval-scorer/` to rerun the exact
commands above. They are reproduced here so the ignored local cache is
not required for review; none belongs to assistant knowledge.

`sample-questions.jsonl`:

```json
{"id": "q001", "course_id": "999001", "language": "sk", "question": "koľko treba na syntetický zápočet?", "answerable": true, "answer": "Aspoň 11 % z 20 %.", "evidence": [{"section": "PH", "quote": "min. 11% z 20%."}], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q002", "course_id": "999001", "language": "en", "question": "Does the synthetic assignment require teamwork and an oral defence?", "answerable": true, "answer": "Yes, teamwork and an oral defence.", "evidence": [{"section": "PH", "quote": "práca v tíme"}, {"section": "ZH", "quote": "ústna obhajoba"}], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q003", "course_id": "999001", "language": "sk", "question": "je v syntetickej osnove rekurzia?", "answerable": true, "answer": "Áno, rekurzia.", "evidence": [{"section": "Osnova", "quote": "rekurzia"}], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q004", "course_id": "999001", "language": "sk", "question": "aká je forma syntetickej skúšky?", "answerable": true, "answer": "Písomná skúška.", "evidence": [{"section": "ZH", "quote": "písomná skúška"}], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q005", "course_id": "999001", "language": "sk", "question": "aký je presný dátum syntetickej skúšky?", "answerable": false, "answer": null, "evidence": [], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q006", "course_id": "999001", "language": "en", "question": "What is the exact room for the synthetic test?", "answerable": false, "answer": null, "evidence": [], "notes": "Synthetic demonstration only; not facts about a real course."}
{"id": "q007", "course_id": "999001", "language": "sk", "question": "koľko má syntetický predmet kreditov?", "answerable": true, "answer": "6 kreditov.", "evidence": [{"section": "Kredity", "quote": "6"}], "notes": "Synthetic demonstration only; not facts about a real course."}
```

`sample-results.jsonl`:

```json
{"id": "q001", "found": true, "answer": "Aspoň 11 % z 20 %.", "sources": [{"section": "PH", "quote": "Podmienka: min. 11% z 20%."}], "testovacie": true}
{"id": "q002", "found": true, "answer": "It requires teamwork.", "sources": [{"section": "PH", "quote": "práca v tíme"}], "testovacie": true}
{"id": "q003", "found": true, "answer": "Matice.", "sources": [{"section": "Osnova", "quote": "matice"}], "testovacie": true}
{"id": "q004", "found": false, "answer": null, "sources": [{"section": "ZH", "quote": "písomná skúška"}], "testovacie": true}
{"id": "q005", "found": false, "answer": null, "sources": [], "testovacie": true}
{"id": "q006", "found": true, "answer": "An invented synthetic room, not a real course fact.", "sources": [], "testovacie": true}
```

`data/courses/999001.json`:

```json
{"name": "Syntetický predmet", "testovacie": true}
```

`invalid-results.jsonl`:

```text
{"id": "q001", "found": true, "answer": "Aspoň 11 % z 20 %.", "sources": [{"section": "PH", "quote": "Podmienka: min. 11% z 20%."}], "testovacie": true}
{broken
{"id": "q002", "found": "yes", "answer": null, "sources": []}
{"id": "q999", "found": false, "answer": null, "sources": []}

```
