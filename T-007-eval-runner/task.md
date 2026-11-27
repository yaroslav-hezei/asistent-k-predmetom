---
id: T-007
title: Evaluation runner — ask the 40 questions through the API and score the answers
assignee: BM
status: open          # open → changes → done | dropped
created: 2026-11-26
due:
---

# T-007 — Evaluation runner — ask the 40 questions through the API and score the answers

## Goal
Close the evaluation loop with one command. You built the 40 evaluation questions (T-003) and the scorer (T-005);
what is missing is the piece in between: a script that **asks the assistant** those 40 questions exactly the way a
student does — logs in with a test account and sends each question to our API — and writes the answers into the
results file that `score.py` reads. Then one command gives the numbers: how many answerable questions the assistant
answered, how many it wrongly refused ("Neviem"), how many unanswerable ones it invented an answer for, and whether
it cited the right part of the sheet.

Why it matters: the real assistant (search in the knowledge base + language model) is being built now. With this
runner, every change to it gets measured the same way, in a few minutes: which embedding model finds the right
sections better (the project will choose between two by these numbers), where to set the "Neviem" threshold, and
whether a change made things better or worse. The numbers also go into the final presentation as the measurable
quality of the MVP.

What you should be able to explain about your part: the runner tests the assistant **from the outside**, like a
user — through the public API with a normal login. It never reads the database, the knowledge base or the prompt,
and it never puts the evaluation questions anywhere the assistant could learn them from (decided: the evaluation set
is test data only; it is never loaded into the knowledge base or a prompt). Scoring is mechanical — the decision
(answered / "Neviem") and the citation (same section + overlapping quote); the wording of the answer is judged by a
person with `--show-answers`.

## Context
- **The API exists** (PR #13, in `main`): `POST /ask` answers a question about one course and stores it in a chat.
  It needs a login token. Exact shapes in "Contract". Interactive docs at `http://localhost:8000/docs`.
- **The answers are placeholders for now.** Until the real assistant is ready, `POST /ask` answers every question
  with the same sentence and **one real section of the course's MAIS sheet** (usually "Priebežné hodnotenie (PH)")
  as the source, quoted exactly; a question containing the word "neviem" gets "Neviem". So the scores of a run today
  are low and that is expected — the point now is that the whole chain works. (Your q001 should even score a full
  citation: its evidence is in the PH section of ZAP.) When the real assistant arrives, the runner must work
  unchanged.
- **Login** works like in the app: Supabase Auth checks e-mail + password and returns an **access token**; every
  request to our API sends `Authorization: Bearer <token>`. The token is valid for about one hour.
  Test accounts are in `backend/scripts/test_users.json` (public on purpose; self-registration is off). The runner
  uses **`student10@example.com`** by default (password: `passwords.student` in that file).
- **The language model has rate limits** on the free tier we develop on: the per-minute and per-day request limits
  of our Google project are visible only in Google AI Studio; outside sources mention about 15 requests per minute
  for the model we plan to use, but this is not confirmed. So the runner sends questions **one at a time with a
  pause** (default 5 s → 12 per minute) and **retries** when the API says it is overloaded.
- **Each question goes to a new chat** (`chat_id: null`), so questions never influence each other. Every run
  therefore creates 40 chats in the test account — the database is shared (development and the demo), so keep full
  runs few (see Notes); the test chats are cleared before the final test.
- **Results files**: the contract is in `data/eval/README.md` ("Results-file contract") — your own T-005 work.
  Real run results must **not** be committed into `data/eval/`; write them under `scratch/` (gitignored).
- **Rules from `AGENTS.md` that matter here:** never invent numbers — report what the run printed; secrets only in
  `.env`, never printed in logs, the report or a commit (the access token counts as a secret).

## Before you start
1. `git pull` on `main` (PR #13 must be in it: `backend/app/routers/chat.py` exists). Python 3.11+.
2. **Values from Yaroslav (privately, never into a file in the repo, a commit, an issue or a report):**
   `DATABASE_URL`, `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` for the repo-root `.env` (see `.env.example`).
   The backend needs the first two; the runner needs the last two to log in. Ask him in the chat before you start.
3. Set up and run the backend (`backend/README.md`, "Run"):
   ```
   cd backend
   python -m venv .venv
   .venv/Scripts/python.exe -m pip install -r requirements-dev.txt        # Linux/macOS: .venv/bin/python
   .venv/Scripts/python.exe -m uvicorn app.main:app --reload --env-file ../.env
   ```
   Check **before you write code**: `http://localhost:8000/docs` lists `POST /ask`.
4. Your agent's MCP tools are not needed for this task (Context7 helps for Python library docs if you use any).

## What to do
1. **`scripts/eval/run.py`** — the runner, **standard library only** (like `score.py`: `urllib.request`, `json`,
   `argparse`; no new dependency in `scripts/eval/requirements.txt`).
   - **Inputs:** the questions file (default `data/eval/questions.jsonl`), the API URL (default
     `http://localhost:8000`), the account e-mail (default `student10@example.com`), the password from
     `backend/scripts/test_users.json` (`passwords.student` / `passwords.vyucujuci` by the account's role in that
     file), `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` from the environment or from an env file (`--env-file`,
     default the repo-root `.env` if it exists; a minimal `KEY=VALUE` parser is enough — skip blank lines and `#`
     comments, strip optional quotes; real environment variables win over the file).
   - **Login:** `POST {SUPABASE_URL}/auth/v1/token?grant_type=password` (see Contract) → the access token. Wrong
     password / unknown account → a clear error and exit 1.
   - **Ask:** for each question, in file order, `POST {api}/ask` with `{"course_id", "question", "chat_id": null}`
     and the token. Wait `--delay` seconds (default 5) between questions.
   - **Retries:** on HTTP 429, 502, 503, 504 or a network error / timeout, wait and retry (10 s, 20 s, 40 s; then
     give up on that question). On 401 log in again once and retry. Any other error (400, 403, 404, 422, 500) → no
     retry. A question that finally fails gets **no** results line (the scorer counts it as `missing`) and is listed
     at the end with its error — never write a made-up result for it.
   - **Output:** a results file in the T-005 contract — one line per answered question:
     `{"id", "found", "answer", "sources": [{"section", "quote"}]}`, taken from the response's `answer`
     (`found`, `text` → `answer`, every source's `section` and `quote`). You may add extra keys the scorer ignores
     (e.g. `type` per source, `elapsed_ms`, `chat_id`). Default path
     `scratch/eval/results-<YYYYMMDD-HHMMSS>.jsonl` (create the folder); `--out` to choose. Write each line as soon as
     its answer arrives, so an interrupted run keeps what it has.
   - **Then score:** at the end, run the scorer on the results file (call `score.py`'s `main` or run it as a
     subprocess) and print its report; `--no-score` skips this. Also print a short run summary: questions sent,
     answered (`found: true`), "Neviem", failed, average and maximum response time.
   - **Options for quick runs:** `--only q001,q004` and `--limit N` (first N questions); `--show-answers` passed on to
     the scorer.
   - **Exit code:** 0 when the run finished (even with a poor score or some failed questions — the summary says so),
     1 on a login or input error, 2 on wrong arguments.
   - **Never print** the password, the token or the key — not in errors either (an error message from Supabase may be
     printed, the request headers never).
2. **Tests** `scripts/eval/tests/test_run.py` — no network, no real backend: start a small fake HTTP server in a
   thread (`http.server`) that imitates `/auth/v1/token` and `/ask`, or inject the HTTP function. Cover at least:
   the mapping response → results line (sheet sources, a `found: false` answer, a source with `section: null`);
   the results file passes `score.py`'s own reader (`read_results`); retry on 503 then success; a question that keeps
   failing is left out and listed; 401 → one new login; 422 → no retry; `--only` / `--limit`; the env-file parser;
   the token never appears in the output. Make the waits injectable so the tests do not sleep.
3. **README:** a section "Run the evaluation" in `data/eval/README.md` (next to the scorer's) — what the runner does,
   the environment it needs, the commands, how long a full run takes, where results go, that each run creates 40
   chats in the test account, and that results are not committed.
4. **CI:** `.github/workflows/eval.yml` already runs `pytest scripts/eval/tests` — your new tests must pass there.
   Do not add a CI step that calls the real API.

## Out of scope
- Any change in `backend/`, `frontend/`, `supabase/`, `data/mais/`, the questions file or `score.py`'s scoring rules.
  If you find a bug in `score.py`, describe it in the report (you may fix it in a separate commit if it is small,
  and say so).
- Deleting chats, creating accounts, a dedicated evaluation account — not now.
- Running against a deployed backend (none yet) — `--api` makes it possible later.
- Comparing runs or storing reports permanently (where they live is decided later).

## Files and folders
- New: `scripts/eval/run.py`, `scripts/eval/tests/test_run.py`.
- Change: `data/eval/README.md` (new section).
- Do not touch: see "Out of scope". Never commit `.env`, results or reports.

## Contract
- **Login (Supabase Auth):**
  ```
  POST {SUPABASE_URL}/auth/v1/token?grant_type=password
  headers: apikey: {SUPABASE_PUBLISHABLE_KEY}, Content-Type: application/json
  body:    {"email": "student10@example.com", "password": "<passwords.student>"}
  200 →    {"access_token": "<JWT>", "expires_in": 3600, …}       400 → wrong e-mail or password
  ```
- **`POST {api}/ask`** with `Authorization: Bearer <access_token>`:
  ```jsonc
  // request
  {"course_id": "65954478", "question": "kolko percent treba na zapocet zo ZAP?", "chat_id": null}
  // response (placeholder answer; ids shortened)
  {
    "chat_id": "3f1e…",
    "question": {"id": "a1…", "role": "user", "text": "kolko percent treba na zapocet zo ZAP?", …},
    "answer": {
      "id": "b2…", "role": "assistant", "found": true,
      "text": "Ukážková odpoveď: … [1].",
      "sources": [{"n": 1, "type": "sheet", "section": "Priebežné hodnotenie (PH)",
                   "quote": "Študent prospeje v PH a získa zápočet, keď splní podmienku získať min. 11% z 20%.\ntesty, zadanie",
                   "url": "https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId=65954478",
                   "question": null, "date": "2026-11-17T15:11:35Z",
                   "author": {"kind": "mais", "nickname": null}, "verified": true, "outdated": false}],
      "created_at": "2026-11-26T16:05:12.401234Z"
    }
  }
  // "Neviem": "answer": {"found": false, "text": null, "sources": [], …}
  ```
  Errors: 401 token missing / expired; 403 the account has no profile; 404 unknown course; 422 the question is shorter
  than 3 or longer than 1000 characters (after trimming); 503 the database or login is not configured. The real
  assistant may later answer 429 / 503 when the model is overloaded — handle them as in "What to do".
  `section` is `null` for sources that are not from the sheet (community answers, the teacher's note).
- **Results file:** the T-005 contract in `data/eval/README.md` — unchanged.
- **Env:** `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (existing names; the key is public but stays out of the repo).
- **New, you define:** the command-line options above (keep these names), the run summary format.

## Done when
- [ ] `python scripts/eval/run.py --limit 3` against the local backend writes 3 results lines and prints the
      scorer's report and the run summary.
- [ ] One full run of the 40 questions finishes; the report and the summary are pasted into your report as printed
      (expect low scores with the placeholder — that is fine; q001 should be `answered` with a `full` citation).
- [ ] `python scripts/eval/score.py --results <that file>` alone prints the same report.
- [ ] With the backend stopped, the run does not crash: questions fail after the retries, are listed, and the
      results file has only the successful ones.
- [ ] A wrong password → a clear message, exit 1, no secret printed.
- [ ] `pytest scripts/eval/tests` passes locally and in CI; `python scripts/eval/validate.py` still passes.
- [ ] `grep` of the run output and the results file for the token / key finds nothing (say how you checked).
- [ ] `data/eval/README.md` has the "Run the evaluation" section.

## How to verify
```
# terminal 1 — backend (see Before you start)
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --env-file ../.env

# terminal 2 — from the repo root
python -m pip install -r scripts/eval/requirements.txt
pytest scripts/eval/tests
python scripts/eval/validate.py
python scripts/eval/run.py --limit 3
python scripts/eval/run.py --only q001,q004 --show-answers
python scripts/eval/run.py                                   # the full run, ~4 minutes with the default pause
python scripts/eval/score.py --results scratch/eval/<the file>.jsonl
```
In the report list: the exact commands and their output (the full report of the 40-question run, the summary), the
number of full runs you made (each creates 40 chats in `student10`), the stopped-backend and wrong-password checks,
and every deviation from this brief with the reason.

## Notes
- **The database is shared.** Every question creates a real chat of `student10`. Develop with `--limit` / `--only`;
  do at most **two** full 40-question runs. Use only `student10`.
- The placeholder answers in about 0.1–1 s; the real assistant will take a few seconds per question — the default
  pause keeps a full run around 4–6 minutes.
- Python's `urllib` raises `HTTPError` for 4xx / 5xx responses — read the status code from it; set a timeout
  (e.g. 60 s) on every request.
- Windows: print UTF-8 safely (the scorer already does — reuse its approach) so Slovak characters do not crash the
  console.
- If something in this brief contradicts the code, do not guess: add a report round with `Status: blocked` and your
  questions.
- Branch `bm/eval-runner` from a fresh `main`; commit messages like `eval: runner (T-007)`; PR title
  `T-007: Evaluation runner`. Open the PR yourself, and push your report (`tasks/T-007-eval-runner/report.md`).
