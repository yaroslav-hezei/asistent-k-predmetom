# HI Bc. evaluation questions (T-003)

This is a test set for measuring whether the assistant answers from the selected
course's sources, cites the right passage, and abstains when those sources do not
answer the question. It is not training data or pre-written assistant knowledge.

**Never load this set into the knowledge database, a retrieval index, an assistant
prompt, or training data.** Only evaluation scripts read it. In a later evaluation,
send the question as the test input; keep its expected answer, evidence and notes
outside the assistant's input. Database knowledge comes from official MAIS sheets
and contributions from people, independently of this file.

The set has 40 questions: 10 courses × (3 answerable + 1 not answerable), with
35 Slovak and exactly 5 English questions. Questions are deliberately short,
informal and often lack diacritics. This avoids making retrieval artificially easy
by copying headings or formal wording from the information sheets.
The English question IDs are `q002`, `q006`, `q014`, `q022` and `q040`.

## Source snapshot and course selection

Evidence comes only from `sections` in `data/mais/2026-27/courses/<course_id>.json`.
Course eligibility comes from P / PV / V rows of HI Bc. program `65669424` in
`data/mais/2026-27/programs.json`, including its state-exam block. Prerequisite and
alternative rows do not make a course eligible. No source files are modified.

All ten choices are mandatory (P) courses, spanning the three years. Periods below
are selection context from the plan; they are not used as answer evidence.

| Course ID | Course | HI Bc. period | Why selected |
|---|---|---|---|
| `65954478` | Základy algoritmizácie a programovania | Year 1, winter | Required by the brief; clear pass threshold and explicit distance-lecture note. |
| `65953562` | Programovanie | Year 1, summer | Programming progression, recommended books and a nontrivial historical grade distribution. |
| `65516728` | Matematika I-HI | Year 1, winter | Adds a mathematics course with a final threshold, named teachers and concrete syllabus topics. PH is empty, so no question invents PH conditions. |
| `65666722` | Jazyk Python | Year 1, summer | Filled PH/ZH, familiar data libraries and literature suitable for a foreign-student question. |
| `65666620` | Aplikácie webových technologií | Year 2, winter | Filled assessment sections plus teacher and quantified project-workload evidence. |
| `65666517` | Analýza a návrh informačných systémov 1 | Year 2, winter | Filled PH/ZH, explicit team-assignment evidence and process-modeling content. |
| `65666873` | Manažment projektov | Year 2, winter | Describes the written exam, planning methods and project-management literature. |
| `65666930` | Znalostné systémy | Year 3, winter | Distinguishes a Moodle test's point value from its unstated question count; also has teachers and books. |
| `65667030` | Riadenie IT prostredia | Year 3, summer | Covers ITIL/COBIT, semester obligations and study workload, while leaving the tool version unspecified. |
| `69574272` | Hospodárska informatika v praxi | Final state-exam block | Required by the brief; covers state-exam completion, business-model content and product-design literature. |

Topics include grading/thresholds, assessment format, course content, teachers,
literature, distance lectures, grade distribution and workload. No course has more
than two questions about a single topic, even if assessment format and grading are
grouped together. Grade percentages describe the captured historical distribution;
they do not predict an individual student's result.

## JSONL format

`questions.jsonl` is UTF-8, one object per line, no blank lines, sorted by `id`.
The contract is fixed; do not add fields without agreement.

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Unique ASCII ID from `q001` through `q999`. |
| `course_id` | string | MAIS `predmet_id` of an eligible HI Bc. course, not its course code. |
| `language` | `"sk"` or `"en"` | Language of the question and expected answer. |
| `question` | non-empty string | A realistic chat question. |
| `answerable` | boolean | Whether the source sheet answers this specific question. |
| `evidence` | list of `{section, quote}` | Exact section label and shortest sufficient source passage, at most 300 characters each. |
| `answer` | string or null | Answerable: a short supported answer. Not answerable: null. |
| `notes` | string or null, optional | Reviewer context, especially why no answer is present. |

For an answerable question, use at least one evidence item and a non-empty answer
in the question's language. Use multiple short evidence items if several facts are
needed. For a not-answerable question, `evidence` must be `[]` and `answer` must be
`null`; in a later evaluation the assistant is expected to abstain (for example,
"Neviem"), rather than produce an invented answer.

Evidence matching collapses each whitespace run (including line breaks and
nonbreaking spaces) to one space on both sides. Everything else is exact: case,
diacritics and punctuation. The 300-character limit counts the original quote,
before normalization. A section label must match exactly. An empty heading such
as `Podmienky na absolvovanie predmetu` cannot support an answer; use PH or ZH
when that is where the information actually appears.

Threshold answers retain the sheet's notation (for example, "21 % zo 40 %"); they
do not reinterpret it as a new calculated percentage. The grade-distribution
excerpt keeps the column labels and values together so the FX percentage can be
identified without guessing. Workload answers describe the sheet's allocation of
hours, rather than promising the same actual effort for every student.

## Run and interpret validation

The validator uses only the standard library and requires Python 3.11+.
Only the tests need pytest:

```sh
python -m pip install -r scripts/eval/requirements.txt
python scripts/eval/validate.py
pytest scripts/eval/tests
```

To validate a different question file or MAIS snapshot:

```sh
python scripts/eval/validate.py --questions data/eval/questions.jsonl --data data/mais/2026-27
```

Errors include the line number and question ID (`<unknown>` when a broken record
cannot provide one). Exit status is 1 on errors and 0 otherwise. File/source errors
use line 0 and `<dataset>` where no particular question can be identified. Unknown
fields, duplicate JSON keys, non-JSON constants, blank/empty files and unsorted IDs
are also rejected, in addition to the required type, course and evidence checks.

Warnings do not change exit status:

- At least five consecutive words shared by the question and sheet. This check
  case-folds and tokenizes Unicode words, ignoring punctuation but retaining
  diacritics. It warns about possible copied wording; it is not a similarity score.
- A represented course with a question count other than four.

The final summary reports question totals, answerability, language counts and
questions per course. The validator also supports small drafts; the dataset test
enforces this release's complete 40-question / 10-course / 30+10 / 35+5 profile,
four questions and three answerable questions per course, and mandatory ZAP/HIP.

CI uses Python 3.12 on PRs and pushes to `main` affecting the evaluation data,
evaluation scripts, MAIS snapshot, or the workflow itself. It runs the tests and
then the validator.

## Add or revise a question

1. Choose an eligible course and read its **whole** information sheet, not just
   search results or a matching section. Never use the plan as answer evidence.
2. Write a natural student question. Pick a topic that does not overfill that
   course's topic mix. Keep the language and answer consistent. Do not put words
   into the question that a student could know only from the sheet, such as a
   book title or an author who does not teach the course; they make retrieval
   trivially easy. A teacher of the course may be named.
3. If answerable, write the shortest supported answer and copy the shortest
   sufficient literal evidence from its actual section. Do not infer a policy
   from a missing or ambiguous statement.
4. If not answerable, check all sections for a direct, indirect or partial answer.
   Record what related information exists and what is missing in English `notes`.
   A date of last change is not an exam date; a point count is not a question count;
   hours of project work are not a submission deadline.
5. Assign a unique ID, keep JSONL sorted, run validation and tests, and inspect
   any warnings. Maintain the 40-question profile when replacing an item.
6. Have the human author check every quote, answer and abstention against the
   full sheet before signing off. Automatic validation cannot prove answer
   correctness, the absence of an answer, language quality or topic balance.

## Score the assistant's answers

`scripts/eval/score.py` measures answer/abstention decisions and citation matches
from local files, using only the standard library (Python 3.11+). It never calls
the assistant, an API or a model, and never writes evaluation data to the knowledge
database or a prompt. Answer wording is **not** scored: use `--show-answers` for
expected/actual pairs that a person can judge.

### Results-file contract

The future runner will write UTF-8 JSONL, one object per line, with no blank lines.
The following values illustrate the format, not a measured assistant run:

```json
{"id": "q001", "found": true, "answer": "Na zápočet treba aspoň 11 % z 20 %.", "sources": [{"section": "Priebežné hodnotenie (PH)", "quote": "Podmienky: min. 11% z 20%."}]}
{"id": "q004", "found": false, "answer": null, "sources": []}
```

| Key | Type | Rule |
|---|---|---|
| `id` | string | An ID from the questions file; at most once per results file. |
| `found` | boolean | `false` means the assistant said "Neviem". Integers are not booleans. |
| `answer` | string or null | A non-empty string when `found` is true; may be null when false. |
| `sources` | list | Objects with required `section` (string or null) and `quote` (string). A non-sheet source may have no section, represented as null. An empty quote is valid input but cannot match evidence. |

Other top-level and source keys are allowed and ignored, so a runner can include
metadata such as model name or source type. JSON must remain strict: duplicate
keys and non-JSON constants such as NaN are rejected. Results need not be sorted.
An empty results file is valid: every question is then `missing`.

All input errors are printed with line numbers and question IDs (`<unknown>` when
a broken record cannot provide an ID; line 0 for file-level failures). Invalid
input gives exit 1 and produces no text/JSON report. An existing JSON output file
is left untouched on input errors. Valid inputs give exit 0 even for a poor score;
wrong command-line arguments give exit 2. `--json` cannot overwrite either input.

The scorer checks the necessary question structure but does not revalidate its
evidence against MAIS or its course eligibility; run `validate.py` on the set
separately. `--data` is used **only** for course display names. If a name is missing,
the ID is displayed with a warning; scores do not change.

### Decisions and citations

Every question receives exactly one outcome:

| Outcome | Question | Result |
|---|---|---|
| `answered` | Answerable | `found: true`; citation is scored. |
| `missed` | Answerable | `found: false`; unnecessary abstention. |
| `abstained` | Not answerable | `found: false`; correct abstention. |
| `invented` | Not answerable | `found: true`; the separate, worst category. |
| `missing` | Either | No results record for the question. |

For each expected evidence item of an `answered` question, at least one cited
source must have the **exact same section label** and overlapping quote text:
after applying `collapse_whitespace` imported from `validate.py`, one quote must
contain the other. A longer cited passage or a shorter excerpt inside the expected
quote counts. Empty/whitespace-only cited quotes do not count. Case, diacritics
and punctuation remain exact. Section labels are not normalized.

All evidence matched gives `full`, some gives `partial`, and none gives `none`.
One source may match several expected evidence items, and different sources may
match different items. Other outcomes have citation null and no matched indexes.
Sources on `found: false` results are ignored for scoring and produce one warning
per result, even if the result contains several sources. They must still have
the required input types. A null source section cannot match a sheet label.

This implements the agreed containment rule; it does not verify the authenticity
of a cited passage or judge the answer's meaning. The future backend supplies
source passages from metadata; the scorer does not use an LLM judge.

### Run and read the report

```sh
python scripts/eval/validate.py
pytest scripts/eval/tests
python scripts/eval/score.py --results path/to/results.jsonl
python scripts/eval/score.py --results path/to/results.jsonl --json path/to/report.json --show-answers
python scripts/eval/score.py --results path/to/results.jsonl --questions data/eval/questions.jsonl --data data/mais/2026-27
python scripts/eval/score.py --results path/to/results.jsonl --show-answers > path/to/out.txt
```

The scorer emits UTF-8 stdout and JSON, including when stdout is redirected on
Windows; no `-X utf8` flag is needed. A shell may re-encode the final redirected
file (for example, Windows PowerShell 5 writes UTF-16); Slovak characters remain
intact. Real run results/reports **must not be committed into `data/eval/`**.
Their permanent location will be decided later. Synthetic test inputs are built
in temporary directories by `scripts/eval/tests/test_score.py`.

The English text report shows totals, decision counts, citation counts, course
and language breakdowns, problems and optional answer pairs. In particular:

- **Decision accuracy:** `(answered + abstained) / all questions`.
- **Invented:** `invented / not-answerable questions`; **missed:**
  `missed / answerable questions`.
- **Citation accuracy:** `full / answered`.
- **Overall correct:** `(abstained + answered with full citation) / all questions`.
  This is the headline mechanical score, not a claim that answer wording is right.

Percentages have one decimal and always appear next to numerator/denominator
counts. Missing results remain in the all-question denominators. A zero denominator
is represented as `0 / 0 (0.0 %)`, not NaN or infinity. Both language groups are
reported, even when one is empty. Missing results are not input errors.

The Problems list includes every question except correct abstentions and fully
cited answers. It shows question ID, course/name, language, question, outcome,
all expected evidence, source quotes shortened to 120 characters, and the actual
answer shortened to 200 characters. `--show-answers` separately shows unshortened
expected/actual answers for every `answered` question.

### JSON report shape

The report has exactly four top-level keys:

| Key | Shape |
|---|---|
| `summary` | `questions`, `results`, `missing`, `answerable`, `not_answerable`, `outcomes`, `citations`, five ratio objects below, and `warnings` (count). |
| `by_course` | Map from course ID to `{name, questions, outcomes, full}`. |
| `by_language` | Map with `sk` and `en`, each `{questions, outcomes, full}`. |
| `questions` | Input-order list of `{id, course_id, language, answerable, outcome, citation, matched_evidence}`. |

`outcomes` always has integer counts for `answered`, `missed`, `abstained`,
`invented`, `missing`; `citations` always has `full`, `partial`, `none` counts.
The five summary ratios are `decision_accuracy`, `invented_rate`, `missed_rate`,
`citation_accuracy`, `overall_correct`, each `{numerator, denominator, percent}`.
`percent` is a number from 0 to 100 rounded to one decimal. `matched_evidence`
contains **zero-based** indexes into that question's evidence array. It is empty
when none match or the outcome is not `answered`. Numeric scoring is the same
in stdout and JSON; the original inputs retain answers and source text for review.
