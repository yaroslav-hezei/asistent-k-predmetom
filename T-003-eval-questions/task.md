---
id: T-003
title: Evaluation question set and its validator
assignee: BM
status: open          # open → changes → done | dropped
created: 2026-11-18
due:
---

# T-003 — Evaluation question set and its validator

## Goal
Create a small **test set of 40 student questions** about 10 courses of Hospodárska informatika (Bc.), each with
the correct answer and the exact place in the MAIS information sheet that proves it — or marked as "the sheet does
not answer this" — plus a **validator** script that checks the set is correct.

Why we need it: the assistant must answer only from the sources it has, quote the right place, and say "Neviem"
when the sheet does not contain the answer. Without a fixed set of questions with known answers we can only judge
it "by eye", and we cannot tell whether a change made it better or worse. This set is an **exam for the
assistant**: we know the right answers in advance, so we can grade it automatically, compare versions, and choose
the similarity threshold below which the assistant says "Neviem" instead of guessing. The course also requires us to
say how the success of our MVP is measured — answer quality on this set is one part of that answer.

What you should be able to explain about your part: why each question has its evidence (a quote and the section it
comes from), why some questions deliberately have **no** answer in the sheet, why questions are phrased the way
students write and not copied from the sheet, and why this set is never put into the assistant's knowledge.

## Context
- **How the assistant will answer** (being built now, not part of this task): the student picks one course and asks.
  The backend searches only in that course's knowledge (the MAIS sheet split into pieces, later also answers of
  students and teachers), sends the most relevant pieces to a language model, and the model answers only from them,
  citing which pieces it used. The quote, the source link and the date are filled in by code. If nothing relevant is
  found, or the model finds no answer in the pieces, the answer is "Neviem" and the student can publish the question
  to "Otázky komunity".
- **Two kinds of questions are therefore needed:**
  - *answerable* — the sheet contains the answer; the assistant should answer and quote that place;
  - *not answerable* — a realistic question the sheet does not answer (e.g. the date of the first test); the
    assistant should say "Neviem" and must not invent anything. These are as important as the first kind: they are
    what the "Neviem" threshold is tuned on, and they are exactly the questions that later go to "Otázky komunity".
- **This set is test data only.** One of the project's principles is that the assistant has no pre-written
  question–answer pairs and is never trained: all its knowledge lives in our database and comes from MAIS and from
  people. The evaluation set must never be loaded into the database or a prompt — it is only read by evaluation
  scripts. Say so in `data/eval/README.md`.
- **What students actually want to know** (from our survey and prototype test): how the course really runs —
  how it is graded (continuous assessment "PH" and final assessment "ZH", the % thresholds), whether there is a
  "zápočet" and an exam, what is taught, how demanding it is, who teaches it, which literature, whether lectures are
  on-site or distance. Students learn this mostly at the first lecture or from classmates; from MAIS only 2 z 16
  respondents.
- **The data** (your scraper's output, in `main`): `data/mais/2026-27/courses/<predmet_id>.json`. The source of truth
  is `sections` — every label of the sheet with its verbatim text. Hospodárska informatika Bc. is the program
  `65669424` in `data/mais/2026-27/programs.json`; its plan has **42 courses** in P / PV / V rows (30 of them P),
  state-exam table included. The backend can list them: `GET /programs/65669424/courses` (see `backend/README.md`).
- **Facts about the HI Bc. sheets** (checked on the 42 sheets):
  - "Podmienky na absolvovanie predmetu" is an **empty heading** in all 42 sheets; the conditions are in the next
    sections "Priebežné hodnotenie (PH)" and "Záverečné hodnotenie (ZH)" (e.g. ZAP: "Študent prospeje v PH a získa
    zápočet, keď splní podmienku získať min. 11% z 20%."). Use the label that really contains the text.
  - Always empty in all 42: "Druh, rozsah a metóda vzdelávacích činností", "Odporúčaný rozsah výučby (v hodinách)",
    "Odporúčané voliteľné súčasti programu". Often empty: "Podmieňujúce predmety" (38), "Stupeň štúdia" (25),
    "Poznámky" (15), the language section (11). PH is empty in 6 sheets, ZH in 2.
  - "Hodnotenie predmetov" holds the grade distribution (A–FX in %, number of graded students); "Zabezpečuje"
    the teachers; "Poznámky" often says whether lectures are distance or on-site.
  - The shortest sheets (about 2,600 characters) are "Aplikácie databázových systémov" and the "Bakalársky projekt"
    courses — they answer few questions; prefer courses with filled PH / ZH and notes.

## What to do
1. **Choose 10 courses** of HI Bc. (program `65669424`), spread over the three years. Must include
   "Základy algoritmizácie a programovania" (`65954478`) and "Hospodárska informatika v praxi" (`69574272`).
   Prefer P (mandatory) courses and sheets with filled PH / ZH. List the 10 with one line each on why you chose them
   in `data/eval/README.md`.
2. **Write 4 questions per course = 40**: 3 answerable + 1 not answerable per course (30 + 10).
   - **Language:** Slovak; exactly **5** of the 40 in English (foreign students ask in English, and the assistant
     must answer in the language of the question).
   - **Phrasing:** as a student would type it into a chat — short, informal, sometimes without diacritics, no
     sheet vocabulary copied. Good: "kolko percent treba na zapocet zo ZAP?", "Is the lecture online?".
     Bad: "Aké sú podmienky priebežného hodnotenia (PH) predmetu?" — it repeats the sheet's own words, so search
     finds it trivially and the test would overrate the assistant.
   - **Topics:** mix them — grading and thresholds, zápočet / skúška, content of the course, teachers, literature,
     distance or on-site lectures, grade distribution (e.g. how many fail). At most 2 questions of the same topic per
     course.
   - **Evidence (answerable):** one or more `{section, quote}` pairs — the section label exactly as in the sheet and
     the **shortest** verbatim passage that proves the answer (at most 300 characters each). Plus a short expected
     answer in the language of the question.
   - **Not answerable:** read the whole sheet and make sure it really does not contain the answer (also not
     partially). Typical: exact dates, rooms, whether attendance is checked (if not stated), how strict a teacher is,
     what the test looks like in detail.
   - You may use your agent to draft questions, but **you** check every quote and every "not answerable" against the
     sheet. In the report say how the questions were made.
3. **Validator** `scripts/eval/validate.py` (standard library only, Python 3.11+), run from the repository root:
   - reads `data/eval/questions.jsonl` and the sheets from `data/mais/2026-27/` (option `--data`);
   - **errors** (exit code 1, each with the line number and question id): invalid JSON line; missing field or wrong
     type; id not unique or not `q001`…`q999`; `course_id` without a sheet, or not in the P / PV / V rows of program
     `65669424`; `language` not `sk` / `en`; an answerable question without evidence or without `answer`;
     a not-answerable question with evidence or with an `answer`; a `section` that is not a label of that course's
     sheet; a `quote` that does not occur in that section's text; a quote longer than 300 characters.
     Quote matching: compare after collapsing every run of whitespace (spaces, line breaks) into one space;
     otherwise exactly — case and diacritics included.
   - **warnings** (printed, exit code stays 0): a question that shares 5 or more consecutive words with its course's
     sheet (a sign of copied wording); a course with a number of questions other than 4.
   - **summary** at the end: number of questions; answerable / not answerable; sk / en; questions per course.
4. **Tests** `scripts/eval/tests/` (pytest): the real set passes; small fixture lines for each kind of error are
   rejected with the right message; the whitespace rule for quotes works; the copy warning fires.
5. **CI** `.github/workflows/eval.yml`: on pull requests and pushes to `main` that touch `data/eval/**`,
   `scripts/eval/**` or `data/mais/**` — Python 3.12, `pytest scripts/eval/tests`, `python scripts/eval/validate.py`.
6. **`data/eval/README.md`**: what the set is for, that it is never part of the assistant's knowledge, the format,
   the 10 courses and why, how to add a question, how to run the validator.

## Out of scope
- Running the assistant, scoring its answers, choosing the threshold — that is a later step and uses your set.
- Questions about other programs, or questions whose answer is only in the study plan (`programs.json`), not in the
  sheet.
- Any change in `data/mais/`, `backend/`, `scripts/scraper/` or the database. If a sheet looks wrong, write it in
  the report; do not edit the data.

## Files and folders
- New: `data/eval/questions.jsonl`, `data/eval/README.md`.
- New: `scripts/eval/validate.py`, `scripts/eval/requirements.txt` (pinned `pytest` only), `scripts/eval/tests/`.
- New: `.github/workflows/eval.yml`.
- Do not touch anything else (`data/mais/`, `backend/`, `frontend/`, `scripts/scraper/`, `docs/`, `AGENTS.md`).

## Contract
`data/eval/questions.jsonl` — UTF-8, one JSON object per line, no blank lines, sorted by `id`. The fields are fixed;
a new field only after asking in a report round.

```json
{"id": "q001", "course_id": "65954478", "language": "sk",
 "question": "kolko percent treba na zapocet zo ZAP?",
 "answerable": true,
 "evidence": [{"section": "Priebežné hodnotenie (PH)",
               "quote": "Študent prospeje v PH a získa zápočet, keď splní podmienku získať min. 11% z 20%."}],
 "answer": "Na zápočet treba z priebežného hodnotenia získať aspoň 11 % z 20 %.",
 "notes": null}
{"id": "q004", "course_id": "65954478", "language": "sk",
 "question": "kedy je prvy test?",
 "answerable": false, "evidence": [], "answer": null,
 "notes": "The sheet names tests in PH but no dates."}
```
(The lines are wrapped here for reading; in the file each object is on one line.)

| Field | Type | Rule |
|---|---|---|
| `id` | string | `q001` … `q999`, unique |
| `course_id` | string | `predmet_id` of a HI Bc. course (P / PV / V row of program `65669424`) |
| `language` | `"sk"` \| `"en"` | the language of the question |
| `question` | string | as a student would write it |
| `answerable` | bool | does the sheet answer it |
| `evidence` | list of `{section, quote}` | answerable: at least one; not answerable: `[]` |
| `answer` | string \| null | answerable: a short correct answer in the question's language; not answerable: `null` |
| `notes` | string \| null | optional; for not answerable questions say what the sheet does contain, if relevant |

The first example uses the real ZAP sheet; check it again yourself before you use it.

## Done when
- [ ] `data/eval/questions.jsonl` has 40 questions: 10 courses × (3 answerable + 1 not answerable); exactly 5 in
      English; ZAP and HIP among the courses.
- [ ] `python scripts/eval/validate.py` → no errors; any remaining warnings are explained in the report.
- [ ] `pytest scripts/eval/tests` passes; CI on the PR is green.
- [ ] Every "not answerable" question was checked against the whole sheet (say how in the report).
- [ ] `data/eval/README.md` explains purpose, the "never in the knowledge base" rule, the format, the courses,
      how to add a question and how to run the validator.

## How to verify
```
python -m pip install -r scripts/eval/requirements.txt
python scripts/eval/validate.py          # errors → exit 1, then warnings and the summary
pytest scripts/eval/tests
```
Put in the report: the validator's summary output, the 10 courses with the reason for each, 3 example questions
(2 answerable, 1 not answerable) with their evidence, how the questions were written and checked, and every
deviation from this brief.

## Notes
- If something in this brief contradicts the data, do not guess: add a report round with `Status: blocked` and your
  questions.
- Branch `bm/eval-questions`; commit messages like `eval: question set for HI Bc. (T-003)`;
  PR title `T-003: Evaluation question set and validator`.
