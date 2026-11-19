# Report — T-003

## Round 1 · 2026-11-19
Status: ready for review
PR: [#4 — T-003: Evaluation question set and validator](https://github.com/yaroslav-hezei/asistent-k-predmetom/pull/4)
Branch: `bm/eval-questions`, created from updated `origin/main`.
Code commit: `4a67baf` (pushed to origin).
The human author confirmed his review and authorized publication on 2026-11-19.

Did:
- Prepared 40 student-style questions about ten mandatory HI Bc. courses across
  all three years, including ZAP and HIP. Each course has three answerable questions
  and one not-answerable question. There are 35 Slovak and exactly five English
  questions (`q002`, `q006`, `q014`, `q022`, `q040`).
- Added 31 evidence items, each copied from its actual sheet section. The longest
  quote is 121 characters (limit 300). No answer uses a fact found only in the plan.
- Wrote a standard-library-only validator with typed-field, ID, course membership,
  source-sheet, evidence, answerability and quote checks; line/ID diagnostics;
  non-fatal copy/course-count warnings; and the requested summary.
- Added pytest tests and Python 3.12 CI for evaluation/MAIS changes. Documentation
  explains source selection, the format, authoring, validation and the rule that
  this set must never enter the knowledge database, retrieval index, assistant
  context or training data. Later evaluation sends only the question as test input.

Files:
- `data/eval/questions.jsonl`, `data/eval/README.md`.
- `scripts/eval/validate.py`, `requirements.txt`, `tests/test_validate.py`.
- `.github/workflows/eval.yml`.
- This report, in the separate `tasks` worktree.
- No changes to `data/mais/`, the backend, frontend, scraper, docs or AGENTS.md.

Course choices (all P rows of HI Bc. program `65669424`):

| ID | Course | Why selected |
|---|---|---|
| 65954478 | Základy algoritmizácie a programovania | Required; first-year thresholds, distance lectures and recursion. |
| 65953562 | Programovanie | First-year course with explicit Arduino content, literature and grade statistics. |
| 65516728 | Matematika I-HI | First-year mathematics diversity, final threshold and teachers; empty PH is not used as evidence. |
| 65666722 | Jazyk Python | First-year PH/ZH, data libraries and literature; a useful English content question. |
| 65666620 | Aplikácie webových technologií | Second-year assessment, teacher and project-workload evidence. |
| 65666517 | Analýza a návrh informačných systémov 1 | Second-year thresholds, explicit teamwork and BPMN content. |
| 65666873 | Manažment projektov | Second-year written exam, planning diagrams and project-management books. |
| 65666930 | Znalostné systémy | Third-year Moodle point-count evidence, named teachers and literature. |
| 65667030 | Riadenie IT prostredia | Third-year ITIL/COBIT, semester obligations and preparation workload. |
| 69574272 | Hospodárska informatika v praxi | Required; final state-exam block, business-model content and design literature. |

Verified (commands from the repository root):
- `.venv/Scripts/python.exe -X utf8 scripts/eval/validate.py` → exit 0:

```text
Questions: 40
Answerable: 30
Not answerable: 10
sk: 35
en: 5
Questions per course:
  65516728: 4
  65666517: 4
  65666620: 4
  65666722: 4
  65666873: 4
  65666930: 4
  65667030: 4
  65953562: 4
  65954478: 4
  69574272: 4
Errors: 0; warnings: 0
```

- `.venv/Scripts/python.exe -X utf8 -m pytest scripts/eval/tests -q`
  → **77 passed in 0.58s** on Python 3.13.15. Tests cover every required error,
  exact diagnostics, state-exam eligibility, rejection of prerequisite/alternative
  courses, whitespace normalization, case/diacritic sensitivity, the 300-character
  boundary, both warnings, CLI exit codes, and the full release profile.
- `.venv/Scripts/python.exe -I -S scripts/eval/validate.py` → exit 0 with the same
  summary. Isolated execution with site packages disabled confirms the validator
  has no third-party dependency.
- `git diff origin/main -- data/mais scripts/scraper` → no output: the source snapshot
  and scraper remain unchanged and match the fetched main snapshot.
- The question JSONL is 13,803 bytes, UTF-8, 40 nonblank records sorted by ID.
- Remote CI on Python 3.12 **passed** for the published commit
  `4a67bafd8b873edfe924170b1fc1a8f9f25f9575`: workflow `Evaluation questions`,
  job `validate`, conclusion `success`. It ran `pytest scripts/eval/tests` followed
  by `python scripts/eval/validate.py`.
  Run: https://github.com/yaroslav-hezei/asistent-k-predmetom/actions/runs/44612134645
- After switching to the task branch from updated main, the local tests were run
  again: **77 passed in 0.53s**; validation again reported zero errors/warnings.

How the questions were written and checked:
- Drafted with agent assistance after reading the complete `full_text` of each of
  the ten committed information sheets. Questions use student wording and several
  omit diacritics; answers are short and in the question's language.
- Selected facts and actual section labels were checked against `sections`, then
  literal passages were extracted and verified. PH/ZH evidence never cites the
  empty generic conditions heading. Numeric thresholds preserve the source's
  notation instead of inventing a calculated interpretation.
- Statistics evidence retains the complete A–FX header/value run so the association
  of FX with 38% is proved; the answer explicitly describes the recorded statistics.
- Reviewed topic balance: even grouping grading and assessment format together,
  no course has more than two questions of that topic. ANIS uses a room question
  as its negative example to avoid overconcentrating its questions on assessment.
- Read the **whole sheet**, including notes, syllabus, assessment and metadata,
  for each proposed not-answerable question. The related information and the exact
  missing fact are documented below and in each record's English `notes`.
- Agent-assisted content checks were followed by human author review: Bohdan
  explicitly confirmed that he checked the questions and authorized publication
  on 2026-11-19. This confirmation is separate from the automatic checks;
  passing tests or publication alone would not establish human sign-off.

Not-answerable audit:

| Question | Course | Related source content | Missing fact checked across the whole sheet |
|---|---|---|---|
| q004 | ZAP | PH names tests and an assignment. | Calendar date of the first test. |
| q008 | Programovanie | PH names a credit test; notes give weekly workload. | Credit-test duration in minutes. |
| q012 | Matematika I-HI | ZH gives the pass threshold. | Assessment room. |
| q016 | Jazyk Python | Lists language topics, libraries and books. | Compulsory editor/IDE. |
| q020 | Webové technológie | Notes allocate 48 hours to the project. | Submission deadline; workload is not a deadline. |
| q024 | ANIS | Describes contact teaching and laboratory work. | Exercise room number. |
| q028 | Manažment projektov | Describes project/presentation work and 10 hours of presentation preparation. | Presentation date/time. |
| q032 | Znalostné systémy | Moodle test is worth 10 points. | Number of questions; points are not a question count. |
| q036 | Riadenie IT prostredia | Outcomes mention a selected IT service-management tool. | Its version (the name is not specified either). |
| q040 | HIP | Completion/ZH identify a state exam; a change date is recorded separately. | State-exam calendar date; metadata is not an exam date. |

Three examples:
1. **q001 (answerable, sk)** — `kolko percent treba na zapocet zo ZAP?`
   - Course `65954478`; section `Priebežné hodnotenie (PH)`.
   - Quote: `min. 11% z 20%.`
   - Expected: `Na zápočet treba z priebežného hodnotenia získať aspoň 11 % z 20 %.`
2. **q022 (answerable, en)** — `Is the ANIS semester project solo or in a team?`
   - Course `65666517`; section `Priebežné hodnotenie (PH)`.
   - Quote: `semestrálneho zadania, ktoré je riešené v tímoch.`
   - Expected: `It is a team assignment.`
3. **q040 (not answerable, en)** — `What is the exact date of the HIP state exam?`
   - Course `69574272`; evidence `[]`, answer `null`.
   - Whole-sheet review found the exam type but no exam date. An evaluator should
     expect abstention, not treat `Dátum poslednej zmeny` as a scheduling fact.

Source caveats retained without editing data:
- Programovanie and Matematika I-HI list `Klasifikovaný zápočet` as completion,
  while generic ZH text mentions an exam. Selected questions do not resolve this
  ambiguity or invent a different completion rule. The mathematics threshold
  answer refers neutrally to final assessment.
- HIP completion identifies a state exam while PH also mentions a credit.
  q037 cites the explicit completion section for its classification.

Deviations from the task:
- No new question fields or source-data changes. `notes` is optional as specified
  by the contract; all forty delivered records include it.
- Added `--questions` for draft-file validation. Additional errors enforce the
  existing JSONL contract: unknown fields, duplicate JSON keys, non-JSON constants,
  blank/empty files and unsorted IDs. The validator supports small drafts; the
  complete 40/10/30+10/35+5 release profile is enforced by the dataset test, while
  per-course count deviations remain warnings as requested.
- The workflow also triggers when the workflow itself changes, following the
  existing backend workflow convention.
- Human sign-off and git publication were explicitly authorized. The branch and
  PR are published, and remote CI is green; no unrun check is claimed as passed.

Questions:
- None. Human review and publication approval were explicitly confirmed.
