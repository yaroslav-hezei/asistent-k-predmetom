# HIP frontend

The Next.js app renders the course picker and the login, and calls the FastAPI backend over HTTP.

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

## Login

Users log in with Supabase Auth (e-mail + password, test accounts only); all data still comes from our API.
To log in locally, copy `.env.example` to `.env.local` and fill in `NEXT_PUBLIC_SUPABASE_URL` and
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (public values, the same as `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` in the
repo-root `.env`), and start the backend with `--env-file ../.env` so it can check the tokens. Without these variables the
app runs, but nobody can log in. They are read at build time: change them, then restart `npm run dev` or rebuild.

- The session lives in cookies. `src/proxy.ts` refreshes it on every request (an access token is valid for about an hour).
- **Server code** (Server Components, Server Actions): `getMe()` from `@/lib/auth/me` gives the logged-in user's profile or
  `null`; `serverApi()` from `@/lib/api/server` calls the API with the user's token.
- **Client components**: `useMe()` from `@/components/me-provider`; the shared `api` client adds the token by itself.
- Log in and out with the server actions `signIn` / `signOut` from `@/lib/auth/actions`. Logging out ends only the
  session in this browser.
- Never decide who the user is from the Supabase session in the frontend; our API checks the token and answers `/me`.

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
