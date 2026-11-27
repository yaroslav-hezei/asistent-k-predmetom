# Backend — FastAPI

The API of the assistant. For now it serves the course catalogue from the committed MAIS snapshot
`data/mais/2026-27/` (loaded into memory at startup). The database (Supabase Postgres) holds a copy
of the catalogue and, step by step, everything else; the catalogue API stays the same.

## Run

From `backend/`, Python 3.11+ (CI uses 3.12):

```sh
python -m venv .venv
# Windows PowerShell: .venv/Scripts/python.exe instead of .venv/bin/python
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --reload --env-file ../.env    # http://localhost:8000/docs
```

Without `DATABASE_URL` (no `.env`, or the variable empty) the backend starts without a database and
still serves the catalogue. With it, the backend connects at startup and stops with an error if the
database is not reachable.

## Check (the same as CI)

```sh
ruff check .
ruff format --check .
pytest
python scripts/export_openapi.py --check
```

The database tests in `tests/test_db.py` run only with `TEST_DATABASE_URL` (see "Database");
without it they are skipped locally. CI always runs them.

## Environment variables

Put them into `.env` in the repo root (template: `.env.example`). Never commit `.env`.

| Name | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | none (no database) | Postgres connection string of the shared Supabase project: Dashboard → **Connect** → **Session pooler** |
| `SUPABASE_URL` | none (nobody can log in) | `https://<project-ref>.supabase.co`; login tokens are verified with the project's public keys |
| `SUPABASE_PUBLISHABLE_KEY` | — | not used by the backend: the public key the browser logs in with (safe to show) |
| `SUPABASE_SECRET_KEY` | — | **only** for `scripts/create_test_users.py`; the running backend never needs it |
| `GEMINI_API_KEY` | none (placeholder answers) | Gemini API key (Google AI Studio → API keys): the answers of `/ask` and the scripts that call the model. Without it `/ask` gives the placeholder answer — enough to build the frontend |
| `MAIS_DATA_DIR` | `data/mais/2026-27` (repo root) | folder with `programs.json` and `courses/` |
| `FRONTEND_ORIGINS` | `http://localhost:3000` | comma-separated origins allowed by CORS |
| `TEST_DATABASE_URL` | none (tests skipped) | tests only: a throwaway **local** database, never the cloud one |

## Database

Supabase Postgres. The schema lives in SQL migrations in `supabase/migrations/` (repo root); never
change tables by hand in the dashboard.

- **Connection:** use the Session pooler string (port 5432). The direct connection is IPv6 only on
  the free plan, and the Transaction pooler (6543) does not support prepared statements.
- **Data API closed:** the browser never reads the database; it gets everything from this backend.
  Every table has row-level security enabled with no policies and no privileges for the `anon` /
  `authenticated` roles, so the public Supabase key cannot read or write anything. A new table in a
  later migration must do the same — `tests/test_db.py` fails otherwise.
- **Catalogue in the database:** `python scripts/import_catalog.py` (from `backend/`) copies the MAIS
  snapshot into `programs`, `courses` and `program_courses` (32 / 563 / 1349 rows). Safe to run again;
  it never deletes programs or courses.
- **Sheets in the knowledge base:** `python scripts/sync_sheet_chunks.py` (from `backend/`, after the
  catalogue import) cuts every course's MAIS sheet into chunks (`app/chunking.py`: one section = one
  chunk, sections over 1,500 characters in parts, each chunk the exact sheet text; "Vysoká škola",
  "Fakulta", "Schválil" and "Dátum poslednej zmeny" are left out) and stores them in
  `knowledge_chunks` without embeddings: 10,981 chunks of 563 sheets. Safe to run again: unchanged
  chunks keep their embeddings, a changed text loses its embedding. `--dry-run` counts the changes
  and writes nothing. Every write to `knowledge_chunks` goes through `app/knowledge.py`.
- **Vectors:** `python scripts/embed_chunks.py` (after the sync) gives every chunk without a vector
  of the current model (`app/llm.py`: `EMBED_MODEL`, 768 numbers) its vector through the Gemini API.
  Each batch is committed on its own: when a quota stops the run, the next run continues where it
  stopped. `--limit N` caps one run, `--dry-run` only counts. Needs `GEMINI_API_KEY`.
  `python scripts/compare_embeddings.py` compares the embedding models on the 40 evaluation
  questions (writes nothing to the database).

## Answers

`POST /ask` answers from the course's whole MAIS sheet (`app/answerer.py`): every chunk of the sheet
goes to the answering model (`app/llm.py`: `ANSWER_MODEL`) as a numbered source; the model answers in
1–4 sentences in the language of the question (Slovak for Slovak or Czech, otherwise English) and
cites sources as [n], or says it does not know (`found: false`, "Neviem"). The model never writes a
source: the code turns the cited numbers into sources with the exact sheet text, the MAIS link and the
date the sheet was read, and renumbers the citations 1, 2, …; an answer that cites nothing is
"Neviem". When the model is not available (rate limit, network), `/ask` answers 503 and stores
nothing.

- **Free tier:** 15 answers a minute and 500 a day for the whole project.
- **Evaluation:** `python scripts/eval_answers.py` asks the 40 evaluation questions directly (no API,
  login or database; at most 14 a minute, about 3 minutes, 40 of the day's 500 requests), writes
  `scratch/eval/answers-<time>.jsonl` and runs `scripts/eval/score.py` on it; it also prints the
  answer language check, time and tokens per answer. `--ids q001,q004` runs only some questions.

Local database for the tests (needs Docker; run from the repo root):

```sh
npx supabase@3.2.0 db start      # Postgres on 127.0.0.1:54322 with Supabase's roles and auth schema
npx supabase@3.2.0 db push       # apply the migrations (local by default)
# then, from backend/:
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres pytest
npx supabase@3.2.0 stop          # when done
```

Apply new migrations to the shared cloud database only after the pull request is merged; Yaroslav
does it.

## Login

Supabase Auth, email + password, test accounts only (no registration). The frontend logs in with
Supabase and sends `Authorization: Bearer <access token>`; endpoints that need a user (now `/me`)
answer 401 without a valid token.

- **Token check** (`app/auth.py`): the token is a JWT signed with the project's asymmetric key
  (ES256). The backend downloads the public keys from `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`
  (cached 5 minutes, reloaded once for an unknown key id) and checks signature, issuer
  (`<SUPABASE_URL>/auth/v1`), audience (`authenticated`) and expiry. Tokens signed with a shared
  secret (HS256) are never accepted. The user id is the `sub` claim = `profiles.id`.
- **Test accounts:** `python scripts/create_test_users.py` (from `backend/`, after the catalogue
  import) creates the accounts of `scripts/test_users.json` in Supabase Auth and their profiles
  (`testovacie = true`): 10 students of Hospodárska informatika (Bc.) and 3 teachers who verify all
  42 courses of that program. The demo passwords in that file are shown on the login screen; they
  are not secrets. Safe to run again. Needs `SUPABASE_SECRET_KEY`.
- **Registration is off** in the Supabase project (Authentication → "Allow new users to sign up"):
  accounts exist only through the script.

## API contract

The Pydantic models in `app/models/` are the source of truth. `openapi.json` is generated from them and
committed; the frontend generates its TypeScript types from it. After changing a model or an endpoint:

```sh
python scripts/export_openapi.py
```

CI fails when `openapi.json` is out of date. Never edit `openapi.json` or the generated types by hand.

Endpoints (details and examples at `/docs` of a running server):

| Endpoint | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /programs` | all study programs (32) |
| `GET /programs/{program_id}/courses?year=&semester=` | courses of a program's study plan, optionally one year / semester |
| `GET /courses?q=` | courses whose name or code contain every word of `q` (case and diacritics ignored); all 563 without `q` |
| `GET /courses/{course_id}` | one course |
| `GET /me` | the logged-in user: id, nickname, role, study (program, year, semester) — needs a token |
| `PATCH /me` | set program, year and semester of the logged-in user — needs a token |
| `POST /ask` | ask about a course: stores the question and the answer in a chat (new one when `chat_id` is null) — needs a token; the answering model reads the course's whole MAIS sheet and cites it as [n] (see "Answers"); 503 when the model is not available; without `GEMINI_API_KEY` a placeholder answer |
| `GET /chats` | the logged-in user's chats for "História", newest first (at most 50) — needs a token |
| `GET /chats/{chat_id}` | one chat of the logged-in user with its messages and their sources — needs a token |

Data rules:

- The catalogue holds the 563 courses of the P / PV / V rows of all plans, state-exam tables included.
  Sheets linked only through `Prerekvizita` / `Zameniteľný` rows are not in the catalogue.
- Course credits and semesters come from the course information sheet. In 10 plan rows the plan's credits
  differ from the sheet; the API returns the sheet's value.
- State-exam rows have no period in the plan; their year and semester come from the sheet's
  "Odporúčaný semester" for that program (e.g. "Hospodárska informatika v praxi" → HI Bc., 3. rok ZS).
- Course and program names are Slovak only.
