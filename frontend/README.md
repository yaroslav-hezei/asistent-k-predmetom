# HIP frontend

The Next.js app renders the course picker and calls the FastAPI catalogue over HTTP.

## Local development

Install Node.js 26.13.1 (see `.nvmrc`) with npm and Python 3.11 or later. Start the backend in one terminal:

```sh
cd backend
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

On Windows, use `.venv/Scripts/python.exe` in the last two commands. FastAPI serves the catalogue at http://localhost:8000.

In another terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. If the backend URL differs, copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_URL`. The default is `http://localhost:8000`. The API must allow the frontend origin via CORS.

## npm scripts

| Script | Purpose |
| --- | --- |
| `dev` | Start the local development server. |
| `lint` | Run ESLint. |
| `typecheck` | Generate Next.js route types and run TypeScript without emitting files. |
| `build` | Create the production build. |
| `start` | Serve the production build. |
| `gen:api` | Generate the TypeScript API schema from the backend OpenAPI file. |

When the backend contract changes, regenerate its `backend/openapi.json` using the instructions in the backend README. Run `npm run gen:api` from `frontend/` and include the generated `src/lib/api/schema.d.ts` alongside the contract change. CI regenerates the schema and checks it for differences.
