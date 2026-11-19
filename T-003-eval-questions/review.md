# Review — T-003

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-19
Verdict: accepted

Checked:
- PR #4 at `4a67baf`, checked out locally. The diff is the 6 new files only; nothing changed in `data/mais/`,
  `backend/`, `scripts/scraper/`, `docs/`, `AGENTS.md`.
- `python scripts/eval/validate.py` (Python 3.14) → exit 0; the summary is identical to the report
  (40 questions, 30 answerable / 10 not, sk 35 / en 5, 4 per course, 0 errors, 0 warnings).
- `python -m pytest scripts/eval/tests -q` → 77 passed.
- CI `Evaluation questions / validate` on `4a67baf` → success.
- Validator against the brief: every required error and warning is there, with line number and id; quote matching
  collapses whitespace and is otherwise exact; only P / PV / V rows of `65669424` count (state-exam table included);
  standard library only. The extra errors (unknown field, duplicate key, unsorted ids, blank line) follow the
  contract — accepted. `--questions` — accepted.
- Content: read the whole sheet of all 10 courses and checked all 40 questions by hand. 29 of 30 expected answers are
  correct and proved by their quote (q031: see 1 below). All 10 not-answerable questions are really not answered by
  the sheet, also not partially. Longest quote 121 characters; at most 2 questions of one topic per course.
- Commit message and PR title follow the rules; no agent attribution.

Fix:
None for you. The four points below were fixed by YH in a follow-up PR #5, so that this task does not go
back and forth. Read them anyway — they are what to watch for next time.
1. q031 — the expected answer was incomplete. The literature of Znalostné systémy lists **two** books by Machová:
   "Znalostné systémy v otázkach a odpovediach" (Elfa, 2005) and "Znalostné systémy" (TU Košice, 2011). An assistant
   that names both would have been graded against an answer that knows only one. Now the answer names both, with two
   evidence items.
2. q015, q027, q039 — the question contained an author or a title that a student can know only by reading the sheet:
   "Python for Everybody", "Sabol", "Norman". This is the "sheet vocabulary copied" case from the brief: search finds
   the line by that exact word, so the test overrates the assistant. The rule: a name in a question is fine when a
   student can know it without the sheet, e.g. a teacher of the course — that is why q007 ("Biňas") and q031
   ("Machová") stay, both are in "Zabezpečuje". Rewritten: q015 "z akych knih sa mam ucit python?", q027 "ma Babic
   nejaku knihu k manazmentu projektov?" (Babič teaches the course and co-wrote the book), q039 "z coho sa mam ucit
   na HIP?"; answers and evidence updated, one evidence item per book. The rule is now in `data/eval/README.md`.
3. `data/eval/README.md` — removed the paragraph about "this Windows workstation" and `.venv` (local setup) and the
   paragraph about the sign-off (it belongs to the report; in the README it would become untrue with the first edit
   by someone else).
4. `scripts/eval/validate.py` — on Windows, with the output redirected to a file or a pipe and without `-X utf8`,
   the validator crashed with `UnicodeEncodeError` on the first message with diacritics instead of printing it.
   Now stdout is switched to UTF-8 in `main()`; test `test_cli_prints_diacritics_to_a_pipe` covers it.

Answers:
- none
