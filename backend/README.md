# Backend — FastAPI

The API of the assistant. For now it serves the course catalogue from the committed MAIS snapshot
`data/mais/2026-27/` (loaded into memory at startup); the database comes later, the API stays the same.

## Run

From `backend/`, Python 3.11+ (CI uses 3.12):

```sh
python -m venv .venv
# Windows PowerShell: .venv/Scripts/python.exe instead of .venv/bin/python
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --reload     # http://localhost:8000/docs
```

## Check (the same as CI)

```sh
ruff check .
ruff format --check .
pytest
python scripts/export_openapi.py --check
```

## Environment variables

| Name | Default | Meaning |
|---|---|---|
| `MAIS_DATA_DIR` | `data/mais/2026-27` (repo root) | folder with `programs.json` and `courses/` |
| `FRONTEND_ORIGINS` | `http://localhost:3000` | comma-separated origins allowed by CORS |

## API contract

The Pydantic models in `app/models/` are the source of truth. `openapi.json` is generated from them and
committed; the frontend generates its TypeScript types from it. After changing a model or an endpoint:

```sh
python scripts/export_openapi.py
```

CI fails when `openapi.json` is out of date. Never edit `openapi.json` or the generated types by hand.

Catalogue endpoints (details and examples at `/docs` of a running server):

| Endpoint | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /programs` | all study programs (32) |
| `GET /programs/{program_id}/courses?year=&semester=` | courses of a program's study plan, optionally one year / semester |
| `GET /courses?q=` | courses whose name or code contain every word of `q` (case and diacritics ignored); all 563 without `q` |
| `GET /courses/{course_id}` | one course |

Data rules:

- The catalogue holds the 563 courses of the P / PV / V rows of all plans, state-exam tables included.
  Sheets linked only through `Prerekvizita` / `Zameniteľný` rows are not in the catalogue.
- Course credits and semesters come from the course information sheet. In 10 plan rows the plan's credits
  differ from the sheet; the API returns the sheet's value.
- State-exam rows have no period in the plan; their year and semester come from the sheet's
  "Odporúčaný semester" for that program (e.g. "Hospodárska informatika v praxi" → HI Bc., 3. rok ZS).
- Course and program names are Slovak only.
