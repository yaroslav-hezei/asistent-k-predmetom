---
id: T-001
title: MAIS scraper — course sheets and study plans to JSON
assignee: BM
status: open          # open → changes → done | dropped
created: 2026-11-15
due:
---

# T-001 — MAIS scraper — course sheets and study plans to JSON

## Goal
The assistant answers students' questions from the official course information sheets ("informačný list predmetu", IL)
published in MAIS. This task builds the script that downloads all sheets and study plans of FEI from the public
MAIS portal and turns them into structured JSON files. These files are the knowledge the assistant starts with:
the backend will load them into the database, cut them into pieces and quote them in answers — with the exact text,
the section it comes from, a link to the sheet and its date. So the JSON must keep **everything** the sheet says,
word for word, with the label of the section it belongs to. Whatever the scraper drops, the assistant can never answer.

## Context
- Source: the public MAIS portal `https://maisportal.tuke.sk/portal/`, no login. Pages are server-rendered HTML,
  no JavaScript needed. Navigation uses form POSTs and a session cookie (`JSESSIONID`); after a POST the server
  redirects to a GET of the same page. Start with a GET of `studijneProgramy.mais` to get the cookie; keep one
  HTTP session for the whole crawl.
- Study programs: page `studijneProgramy.mais`, form fields
  `zvolenaFakultaId` (FEI = `6878`), `zvolenyARKSId` (academic year, 2026/2027 = `64312664`),
  `zvolenaFormaStudia` (`DENNA`, `EXTERNA`), `zvolenyStupenStudia` (`PRVY`, `PRVY_PROFES_ORIENTOVANY`,
  `PRVY_A_DRUHY`, `DRUHY`, `TRETI`), `zvolenyStudijnyProgramStudiaId`, `akcia`.
  Changing a filter = POST with all fields and `akcia` = `zmen_fakultu` / `akademicky_rok` / `forma_studia` /
  `stupen_studia`; the response lists the programs in the `zvolenyStudijnyProgramStudiaId` select.
  Showing a plan = POST with `akcia=zobraz_studijny_program`.
- A plan page contains: the program header (Forma štúdia, Stupeň štúdia, Študijný odbor, Metóda, Dĺžka štúdia,
  Akademický rok), "Profil absolventa", one table per period (`1. rok ZS`, …) with the columns
  # / Kód / Názov / Ukončenie / Kredity / Typ (P, PV, V) / Profilový predmet / Rozsah výučby / Detail predmetu,
  credit rules between the tables ("V období od … je … potrebné úspešne absolvovať predmety za N kreditov"),
  and "Predmety štátnej skúšky" (different columns: # / Kód / Názov / Ukončenie / Kredity / Typ /
  Profilový predmet / Fakulta / Detail predmetu — no period, no hours). Each "Detail predmetu / IL" link carries a `predmetId`
  (`onclick="document.forms.detailForm.predmetId.value=65954478; …"`).
- A sheet opens with a plain GET in any session:
  `https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId=<predmetId>` (redirects to `report.htm`).
  This URL is also the source link the assistant shows to students — store it.
- `predmetId` is not the course code: ZAP has the code `26000629` and the `predmetId` `65954478` in 2026/2027.
  One course can appear in many programs; download each `predmetId` once.
- A sheet is a fixed form. Every label is a `<b>` element whose text ends with `:` (`Kód predmetu:`,
  `Podmienky na absolvovanie predmetu:`, `Priebežné hodnotenie (PH):`, `Stručná osnova predmetu:`,
  `Hodnotenie predmetov:`, `Zabezpečuje:`, `Dátum poslednej zmeny:`, …). The value is everything up to the next
  label. Values are often inside `<b>` too, so "bold" alone does not mean "label". Two tables sit inside:
  "Odporúčaný semester" (semester / program / degree / method — one row per program that uses the course) and
  the grade distribution (A, B, C, D, E, FX in %, plus "Celkový počet hodnotených študentov").
- Encoding trap: the sheet response does not declare a charset in the HTTP header. Decode it as UTF-8 explicitly;
  the default decoding produces mojibake (`Ã¡` instead of `á`).
- Scope: FEI, academic year 2026/2027, form `DENNA`, degrees `PRVY`, `PRVY_PROFES_ORIENTOVANY`, `DRUHY`
  (all Bc. and Ing. programs). For 2026/2027 FEI lists no programs for `EXTERNA` and none for `PRVY_A_DRUHY`.
  Reference numbers (counted on 2026-11-15): 15 + 1 + 16 = 32 programs. The regular period tables contain
  563 unique courses (Bc. 282, Bc. "PO" 39, Ing. 270 — they overlap). The "Predmety štátnej skúšky" tables add
  more (12 for the Bc. programs; Ing. not counted). Within one year a `predmetId` maps to exactly one course code.
- It is the university's live system: sequential requests only, a pause of at least 1 s, at most 3 retries per
  request with a growing pause. Download once into a local cache; re-parsing never touches the network.
- No backend and no database exist yet. The scraper is a standalone script and must not depend on them.

## What to do
1. `scripts/scraper/` — a CLI script with the options `--year`, `--faculty`, `--degree` (several), `--form`
   (several), `--out`, `--cache`, `--parse-only`. Defaults = the scope above.
2. Crawl: for each form × degree list the programs, open each plan, save the raw plan HTML to the cache.
3. Collect the unique `predmetId`s from all plans and download each sheet once into the cache.
   Already cached → skip, so a stopped run continues where it stopped.
4. Parse the cached HTML into the JSON files described in **Contract**.
5. Coverage check in the parser (see Contract). A sheet that fails it goes to `failures`, never silently to the output.
6. Write `manifest.json`. Exit with a non-zero code if anything failed.
7. Parser tests (pytest) on 2–3 saved sheets and one saved plan page as fixtures.
8. Run the full scrape once and commit the JSON output.

## Out of scope
- Database, chunking, embeddings, API — the backend does that from your JSON.
- Other faculties, other academic years, the external form, the PhD degree (`TRETI`): the options must allow them,
  but do not run them.
- English versions of the sheets, "Rozvrhy", "Miestnosti", anything behind a login.

## Files and folders
- New: `scripts/scraper/` — the script, `requirements.txt` (pinned versions, `pytest` included), `README.md` (how to install and run,
  how long a full run takes), `tests/` with `tests/fixtures/`.
- New: `data/mais/2026-27/` — the JSON output, committed.
- Raw HTML cache: `.cache/mais/`. Add `.cache/` to `.gitignore`. Raw HTML is never committed, except the test fixtures.
- Do not touch anything else (`AGENTS.md`, `docs/`, `.github/`, `scripts/setup_workspace.py`).

## Contract
The backend will read these files as they are. The field names below are fixed. If something does not fit,
it stays in `sections` / `full_text` and you describe it in the report; a new top-level field only after asking.

All files: UTF-8, `ensure_ascii=False`, indent 2. Text values verbatim from MAIS: whitespace inside a line collapsed
to one space, line breaks kept as `\n`, nothing else changed (no translation, no fixing of typos).

`data/mais/2026-27/manifest.json`
```json
{
  "source": "https://maisportal.tuke.sk/portal/",
  "scraped_at": "2026-11-16T10:00:00Z",
  "academic_year": "2026/2027",
  "faculty": "FEI",
  "degrees": ["PRVY", "PRVY_PROFES_ORIENTOVANY", "DRUHY"],
  "forms": ["DENNA"],
  "counts": {"programs": 0, "plan_rows": 0, "sheets": 0, "unique_course_codes": 0},
  "failures": [{"predmet_id": "…", "error": "…"}]
}
```

`data/mais/2026-27/programs.json` — a list, one object per program:
```json
{
  "program_id": "65669424",
  "name": "Hospodárska informatika",
  "code": "HI_Bc_D_sk",
  "form": "DENNA",
  "degree": "PRVY",
  "header": [{"label": "Študijný odbor", "text": "Informatika (2508R00)"}],
  "profile": "Hospodárska informatika na FEI TU v Košiciach predstavuje …",
  "plan": [
    {"period": "1. rok ZS", "code": "26000629", "name": "Základy algoritmizácie a programovania",
     "short_name": "ZAP", "completion": "Zápočet a skúška (ZS)", "credits": 5, "type": "P",
     "profile_course": "", "hours": "P-3 CL-2 za týždeň", "faculty": null, "predmet_id": "65954478", "block": "plan"}
  ],
  "rules": ["V období od 1. rok ZS do 1. rok ZS je pre postup do ďalšieho obobia štúdia potrebné úspešne absolvovať predmety za 18 kreditov."],
  "full_text": "… the whole plan section as plain text …"
}
```
`block` is `"plan"` for the period tables and `"state_exam"` for "Predmety štátnej skúšky". Any other kind of
table → its heading text as `block`, and mention it in the report. State-exam rows: `period` and `hours` are `null`,
the "Fakulta" column goes to `faculty` (regular rows: `faculty` is `null`). `programs.json` is sorted by form, degree
and program code; plan rows keep the order of the page.

`data/mais/2026-27/courses/<predmet_id>.json` — one file per sheet:
```json
{
  "predmet_id": "65954478",
  "code": "26000629",
  "name": "Základy algoritmizácie a programovania",
  "academic_year": "2026/2027",
  "source_url": "https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId=65954478",
  "fetched_at": "2026-11-16T10:03:12Z",
  "sections": [
    {"label": "Kód predmetu", "text": "26000629"},
    {"label": "Stručná osnova predmetu", "text": "1. Úvod do informatiky\n2. Algoritmus – definícia, …"}
  ],
  "fields": {
    "department": "Katedra počítačov a informatiky",
    "credits": 5,
    "recommended_semester": "ZS",
    "completion": "Zápočet a skúška",
    "last_changed": "2026-09-01",
    "approved_by": "osoba/osoby zodpovedné za študijný program"
  },
  "programs": [
    {"semester": "1.rok ZS", "program": "Hospodárska informatika (HI_Bc_D_sk)", "degree": "1.", "method": "Prezenčná"}
  ],
  "grades": {"total_students": 12286, "percent": {"A": 19, "B": 12, "C": 13, "D": 12, "E": 16, "FX": 28}},
  "teachers": ["doc. Ing. …, PhD.", "…"],
  "full_text": "… the whole sheet as plain text …",
  "unknown_labels": []
}
```
Where the values come from (sheet label → JSON):
- `code` ← "Kód predmetu", `name` ← "Názov predmetu".
- `fields.department` ← "Pracovisko"; `fields.credits` ← "Počet kreditov";
  `fields.recommended_semester` ← the first line of "Odporúčaný semester štúdia" (e.g. `ZS`);
  `fields.completion` ← "Spôsob hodnotenia a skončenia štúdia predmetu"; `fields.last_changed` ← "Dátum poslednej zmeny";
  `fields.approved_by` ← "Schválil".
- `programs` ← the "Odporúčaný semester" table (it sits inside the value of "Odporúčaný semester štúdia").
- `grades` ← "Hodnotenie predmetov": "Celkový počet hodnotených študentov" + the A–FX table.
- `teachers` ← "Zabezpečuje", one person per line.
- `fetched_at` ← the time the sheet was downloaded; store it with the cache (e.g. a small sidecar file),
  so that `--parse-only` reproduces it.

Rules:
- `sections` is the source of truth: **every** label of the sheet in the order of the sheet, with its verbatim value,
  including empty values (`"text": ""`) and labels the parser does not know. The two tables stay in `sections` as text
  and are additionally parsed into `programs` and `grades`.
- `fields` has exactly the keys shown. `fields`, `programs`, `grades` and `teachers` are parsed copies for convenience:
  a value that cannot be parsed is `null` (never guessed); the raw text stays in `sections`.
- `unknown_labels` lists labels that are not in the parser's known list. Expected empty; if not, list them in the report.
- Coverage check: the words of all `label` + `text` in `sections` must be exactly the words of `full_text`, in the same
  order — nothing lost, nothing added (the title "INFORMAČNÝ LIST PREDMETU" may be excluded). Describe in the report
  how you compare.
- Dates in `fields` as ISO `YYYY-MM-DD`, numbers as numbers, percentages without `%`.
- `courses/` is written in full on every run, so a re-run shows changed sheets as a normal git diff.

## Done when
- [ ] The full run for the scope finished: `failures` is empty, the counts in `manifest.json` match the reference
      numbers above (any difference explained in the report).
- [ ] Every sheet passes the coverage check; `unknown_labels` is empty everywhere, or every unknown label is listed
      and explained in the report.
- [ ] Control values: `courses/65954478.json` → `code` `26000629`, `fields.credits` 5, `grades.total_students` 12286,
      `grades.percent.FX` 28, `fields.last_changed` `2026-09-01`; `courses/65953562.json` (Programovanie) →
      `grades.total_students` 16748, `grades.percent.FX` 38. (Checked on 2026-11-15; if MAIS changed since, say so.)
- [ ] `--parse-only` rebuilds the same JSON from the cache without network access (only `scraped_at` may differ).
- [ ] `pytest scripts/scraper/tests` passes.
- [ ] No mojibake in the output: no `Ã` or `Å` in `data/mais/`.
- [ ] Raw HTML is not committed (only the fixtures); `.cache/` is in `.gitignore`.
- [ ] `scripts/scraper/README.md` says how to install, how to run, how long a full run takes.

## How to verify
Commands for Git Bash; in PowerShell use the equivalents.
```
pip install -r scripts/scraper/requirements.txt
python scripts/scraper/<script>.py                # full run, default scope
python scripts/scraper/<script>.py --parse-only   # rebuild from cache, no network
pytest scripts/scraper/tests
grep -rlE "Ã|Å" data/mais || echo "no mojibake"
git status --short                                # no .cache/ files
```
Put in the report: the counts from `manifest.json`, the run time, the control values, the size of `data/mais/`,
the list of unknown labels (if any), and how the coverage check compares.

## Notes
- If the HTML differs from this description, do not guess: add a report round with `Status: blocked` and your questions.
- Branch `bm/mais-scraper`; commit messages like `scraper: parse course sheets (T-001)`; PR title `T-001: MAIS scraper`.
