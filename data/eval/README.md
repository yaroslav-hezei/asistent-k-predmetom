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

On this Windows workstation, use `.venv/Scripts/python.exe -X utf8` in place of
`python`, and `.venv/Scripts/python.exe -m pytest scripts/eval/tests` for pytest.

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
   course's topic mix. Keep the language and answer consistent.
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

This set was prepared with agent assistance, with complete-sheet reading and
literal evidence checks. The human author confirmed that he checked the questions
and authorized publication on 2026-11-19. Human sign-off is separate from automatic
validation; it must not be inferred from a green validator or from these tests.
