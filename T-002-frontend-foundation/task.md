---
id: T-002
title: Frontend foundation and the course picker
assignee: MP
status: done          # open → changes → done | dropped
created: 2026-11-18
due:
---

# T-002 — Frontend foundation and the course picker

## Goal
Build the frontend of the app: the Next.js project every other screen will live in, and its first real screen,
the **course picker** (screen 1 of the prototype, "O ktorom predmete sa chceš pýtať?"). A student opens the app,
finds a course by name or code, or sees "Moje predmety" for their program, year and semester, and clicks the
course they want to ask about. The data is real: the 32 FEI study programs and 563 courses of 2026/2027 scraped
from MAIS, served by our backend API, which already runs.

This task matters for two reasons. First, the course picker is the entry point of the product: every question a
student asks belongs to one course ("one chat = one course"), so without this screen nothing else can be used.
Second, the foundation you set up here (layout, design tokens, translations, the API client, generated types, CI)
is what the chat, community questions, notifications and the teacher screens will be built on — by you and by
others. Doing it well once saves everybody time later.

What you should be able to explain about your part: the frontend is only the user interface; it never reads the
database and contains no business logic. All data comes from the FastAPI backend over HTTP. The shape of that data
is defined once in the backend (Pydantic models → `backend/openapi.json`); the frontend **generates** its TypeScript
types from that file, so if the backend changes a field, the frontend build fails at every place that uses it,
instead of breaking silently in the browser. Every text in the interface comes from translation files (Slovak and
English), never from the code.

## Context
- **The product.** A web app where a student picks a course and asks a question about how the course really runs
  (grading, credit and exam conditions, workload, teachers). The assistant answers from the official course
  information sheet in MAIS and from answers of other students and teachers, always with a quote, source, date and
  author. If it does not know, it says "Neviem" and the student can publish the question to "Otázky komunity".
  Those parts come later; this task is the shell and the course picker.
- **Stack (decided).** Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui, Slovak and English UI.
  Backend: Python + FastAPI. Database: Supabase (Postgres) — not set up yet; the frontend will use Supabase **only to
  log in** (later), all data always goes through the FastAPI backend.
- **The backend is in `main`** (`backend/`, see `backend/README.md`). It needs Python **3.11+**
  (`CONTRIBUTING.md` still says 3.10+ — that is outdated; FastAPI no longer installs on 3.10). Run it locally:
  ```
  cd backend
  python -m venv .venv
  .venv/Scripts/python.exe -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
  .venv/Scripts/python.exe -m uvicorn app.main:app --reload       # http://localhost:8000/docs
  ```
  CORS already allows `http://localhost:3000` (the Next.js dev server). `/docs` shows every endpoint with examples.
- **The API you use** (details in `backend/openapi.json` and `/docs`):

  | Endpoint | Returns |
  |---|---|
  | `GET /programs` | all 32 study programs |
  | `GET /programs/{program_id}/courses?year=&semester=` | the courses of a program's study plan, optionally for one year and semester |
  | `GET /courses?q=` | courses whose name or code contain every word of `q` — case and diacritics are ignored (`zaklady prog` finds "Základy …"); without `q` all 563 |
  | `GET /courses/{course_id}` | one course; unknown id → 404 |
  | `GET /health` | `{"status": "ok"}` |

  Real examples (these values are checked by the backend tests):
  ```json
  // GET /courses/65954478
  {"id": "65954478", "code": "26000629", "name": "Základy algoritmizácie a programovania",
   "credits": 5, "semesters": ["ZS"]}

  // one item of GET /programs
  {"id": "65669424", "code": "HI_Bc_D_sk", "name": "Hospodárska informatika",
   "degree": "bc", "language": "sk", "method": "prezencna", "years": 3}

  // one item of GET /programs/65669424/courses?year=3&semester=ZS  (8 items in total)
  {"course": {"id": "69574272", "code": "26001478", "name": "Hospodárska informatika v praxi",
              "credits": 6, "semesters": ["ZS"]},
   "year": 3, "semester": "ZS", "type": "P", "state_exam": true}
  ```
  Facts about the data you need for the UI:
  - `degree`: `bc` (15 programs), `bc_po` (1 — Bc. professionally oriented, 4 years), `ing` (16).
  - Several programs share a name: "Informatika" exists as Slovak full-time, English and "kombinovaná" (method)
    variants. A program label must therefore show degree, and language / method when they are not the default —
    e.g. "Informatika (Bc.)", "Informatika (Bc., EN)", "Informatika (Bc., kombinovaná)".
  - `years`: Bc. 3, Ing. 2, the `bc_po` program 4 — use it for the year choice.
  - `semester`: `ZS` = winter, `LS` = summer.
  - Course and program names exist only in Slovak; they are data and are **not** translated in the English UI.
- **Three decisions for this task (decided):**
  1. **Types from OpenAPI:** generate them with `openapi-typescript` from `backend/openapi.json`; make requests with
     `openapi-fetch` (a small typed wrapper around `fetch`). Never write or edit API types by hand.
  2. **Translations:** `next-intl`, **without** the language in the URL (routes stay `/chat`, `/questions`, …).
     The language is switched with the SK | EN control at the bottom of the sidebar and remembered in a cookie.
     Default: Slovak.
  3. **"Moje predmety" without login:** login does not exist yet. For now the student chooses program, year and
     semester in a small dialog ("Zmeniť"), and the choice is saved in the browser (`localStorage`). Later, after
     login, the same choice will come from the user's profile — so build the choice as a reusable component that can
     move to a profile page; only the place where it is stored will change.
- **Design.** `docs/design/UI.md` (read it first) and `docs/design/screens/01-course-picker.png`. The prototype
  `docs/design/prototype-hifi.html` is the visual spec: re-create the look with Tailwind + shadcn/ui, do not copy its
  markup. Design tokens (colors, font Inter 400/500/600 at 15 px, sidebar 280 px, top bar 62 px, radii) are listed in
  `UI.md` — put them into the Tailwind / CSS theme once and use the token names, not raw hex values in components.
  The prototype covers desktop only; on mobile (390 px) the sidebar becomes a drawer and the content takes the full
  width.
- **Rules from `AGENTS.md` that matter here:** Next.js is UI only (no business logic, no direct DB access); generated
  types are never edited by hand; UI text only through i18n keys, Slovak and English; no secrets in the repo; UI work
  is checked with Playwright at 1440×900 and 390 px against `docs/design/screens/`.

## Before you start
This task depends on your tools. The setup is described in `CONTRIBUTING.md`; check every point **before** writing
code, and fix what is missing first.

1. **Workspace.** You ran `scripts/setup_workspace.py` once ("Join (once)" in `CONTRIBUTING.md`): `tasks/`,
   `me.md` and `CLAUDE.md` exist in your clone. Then `git pull` on `main` — the backend arrived there on 2026-11-18.
2. **Node.js** — the current LTS: `node -v`, `npm -v`.
3. **Python 3.11 or newer** — only to run the backend locally: `python --version` (Windows: `py --version`).
4. **MCP servers for your agent**, installed globally as in `CONTRIBUTING.md` → "Agent tools":
   - **Playwright** — your agent opens the app in a real browser, takes the screenshots for the report and compares
     them with `docs/design/screens/`. Without it you cannot meet "Done when".
   - **shadcn** — your agent adds shadcn/ui components with their current API instead of guessing from memory.
   - **Context7** — current docs for Next.js, next-intl, openapi-typescript / openapi-fetch and Tailwind; these
     libraries change often and an agent's memory of them is frequently outdated.

   Check: Claude Code `claude mcp list`, Codex `codex mcp list` → all three are listed and connected.
   If Playwright reports a missing browser, run `npx playwright install chromium` once.
5. **Ask your agent** to confirm that it sees all three tools before it starts. If a tool is missing, the agent
   must say so and not continue by guessing (`AGENTS.md` §8).

## What to do
1. **Project.** Create the Next.js app in `frontend/` (App Router, TypeScript, Tailwind, ESLint) and initialise
   shadcn/ui. Package manager: `npm`. Pin the Node.js version you use (the current LTS) in `package.json`
   `engines` and in `frontend/.nvmrc`.
2. **Theme.** The design tokens from `UI.md` as Tailwind theme values / CSS variables; font Inter.
3. **Translations.** `next-intl` without locale routing; messages in `frontend/messages/sk.json` and
   `frontend/messages/en.json`; the SK | EN switch in the sidebar sets the cookie and re-renders the page in that
   language. Every visible text of this task is a key in both files.
4. **API types and client.**
   - npm script `gen:api`: `openapi-typescript` reads `../backend/openapi.json` and writes
     `frontend/src/lib/api/schema.d.ts` (committed).
   - One client module `frontend/src/lib/api/client.ts` built with `openapi-fetch` and the generated types. The base
     URL comes from the environment variable `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`); document it in
     `frontend/.env.example`.
   - **All** requests go through this one module — components never call `fetch` directly. (Reason: when login
     arrives, the auth token will be added in this single place.)
5. **Layout** (shared by all pages, as on screen 1): the sidebar with the logo "Asistent k predmetom", "Nový chat",
   the navigation items "Asistent", "Otázky komunity", "Upozornenia", and the SK | EN switch at the bottom; the top bar
   with the page title. Things that need login or the database are **not** faked: no user name or avatar, no badge
   counts, no "História" list — leave them out until the data exists.
6. **Routes.**
   - `/` → redirect to `/chat`.
   - `/chat` — the course picker (below).
   - `/chat/new?course=<courseId>` — the empty chat of the chosen course: the chat header with the course name and
     code (from `GET /courses/{course_id}`) and a short translated note that asking questions is coming soon.
     Unknown course id → a translated "course not found" message with a link back to `/chat`.
     (Later this page gets the message composer; the header is reused by the real chat.)
   - `/questions` and `/notifications` — placeholder pages with the title and a translated "coming soon" text, so the
     navigation works.
7. **Course picker (`/chat`).**
   - Heading "O ktorom predmete sa chceš pýtať?" (translated).
   - **Search** by name or code using `GET /courses?q=`. Search after the user stops typing (~250–300 ms) and from
     2 characters; show the results as a list (course name, code, recommended semester); a translated message when
     nothing matches. Clicking a result → `/chat/new?course=<id>`. Keyboard: Enter on a result opens it.
   - **Moje predmety**: the line "Moje predmety · <program label> · <year>. roč., <semester> · Zmeniť" and the course
     cards of that program, year and semester from `GET /programs/{id}/courses?year=&semester=`. A card shows the
     course name and "<year>. roč., <semester>", as on the screen. Clicking a card → `/chat/new?course=<id>`.
     Nothing chosen yet → instead of the cards, a short translated invitation and a button that opens the dialog.
   - **The "Zmeniť" dialog**: choose the program (all 32, grouped Bc. / Bc. PO / Ing., labelled as in Context), the
     year (1 … `years` of the program) and the semester (ZS / LS); save to `localStorage`; the cards update at once.
     If the saved program no longer exists in `GET /programs`, treat it as "nothing chosen".
   - **Naposledy použité** from the prototype needs chat history (database) — leave it out for now.
   - The footer hint "Jeden chat = jeden predmet. …" (translated).
   - **Loading and errors**: show a loading state while data loads; if the backend is not reachable, show a
     translated error message — the page must not crash or stay blank.
8. **CI.** `.github/workflows/frontend.yml`, on pull requests and on pushes to `main` that touch `frontend/**` or
   `backend/openapi.json`: `npm ci`, lint, type check (`tsc --noEmit`), `npm run build`, and a check that
   `schema.d.ts` is up to date (run `gen:api`, then fail if git sees a change).
9. **`frontend/README.md`**: how to install and run the frontend together with the backend, the npm scripts,
   the environment variable, and how to regenerate the API types after a backend change.

## Out of scope
- Login, Supabase, user profiles, roles — later; do not install the Supabase client yet.
- The chat itself (asking a question, answers, sources, "Neviem"), community questions, notifications, history,
  the teacher screens — later tasks.
- Any change in `backend/`. If the API lacks something you need, do not work around it in the frontend: add a report
  round with `Status: blocked` and describe what is missing.
- Deployment (Vercel), dark mode, labels for the course type (P / PV / V) or state-exam courses on the cards.

## Files and folders
- New: `frontend/` (the whole app, including `messages/`, `src/lib/api/`, `.env.example`, `.nvmrc`, `README.md`).
- New: `.github/workflows/frontend.yml`.
- Do not touch: `backend/`, `data/`, `scripts/`, `docs/`, `AGENTS.md`, `CONTRIBUTING.md`, other workflows.
  The root `.gitignore` already ignores `node_modules/` and `.next/`.

## Contract
- **API:** exactly as in `backend/openapi.json` (endpoints and examples in Context). Types only from `gen:api`.
- **Environment variable (new, defined here):** `NEXT_PUBLIC_API_URL` — the backend base URL, default
  `http://localhost:8000`.
- **Generated types:** `frontend/src/lib/api/schema.d.ts`, written only by `npm run gen:api`.
- **The "Moje predmety" choice in the browser:** `localStorage` key `hip.myCourses`, value
  `{"programId": "65669424", "year": 3, "semester": "ZS"}`. Temporary — it will be replaced by the user profile.
- **Routes:** `/`, `/chat`, `/chat/new?course=<courseId>`, `/questions`, `/notifications`.
- **Translation keys:** you define them; group them by screen (e.g. `picker.title`, `layout.nav.questions`).

## Done when
- [ ] `frontend/` runs with `npm run dev` against the local backend; `/chat` shows real data.
- [ ] Search: `zaklady algoritmizacie` and `26000629` both find "Základy algoritmizácie a programovania";
      `xyzxyz` shows the "nothing found" message; one character does not search.
- [ ] Moje predmety: choosing "Hospodárska informatika (Bc.)", 3. ročník, ZS shows 8 cards, among them
      "Hospodárska informatika v praxi"; the choice survives a page reload.
- [ ] The program list shows 32 programs; the three "Informatika" Bc. variants are distinguishable.
- [ ] Clicking a course opens `/chat/new?course=<id>` with its name and code; an unknown id shows the
      "course not found" message.
- [ ] SK | EN switch: every text of the layout, the picker, the dialog and the placeholder pages changes language
      (course and program names stay Slovak); no hard-coded UI text in components.
- [ ] Backend stopped → a translated error message, no crash.
- [ ] All requests go through `src/lib/api/client.ts`; `schema.d.ts` is generated, not hand-written.
- [ ] Layout matches `01-course-picker.png` at 1440×900 (apart from the parts left out on purpose: user block,
      badge, "História", "Naposledy použité"); at 390 px the sidebar is a drawer and nothing overflows horizontally.
- [ ] `npm run lint`, `tsc --noEmit` and `npm run build` pass; CI on the PR is green.
- [ ] `frontend/README.md` explains install, run, scripts, env variable and type regeneration.

## How to verify
```
# terminal 1 — backend (see Context)
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload

# terminal 2 — frontend
cd frontend
npm ci
npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts   # types are up to date
npm run lint
npx tsc --noEmit
npm run build
npm run dev                                                       # http://localhost:3000
```
With Playwright take screenshots at 1440×900 and 390 px of: `/chat` with "Hospodárska informatika (Bc.)",
3. roč., ZS chosen; `/chat` with search results for `zaklady`; the "Zmeniť" dialog; `/chat` in English;
`/chat` with the backend stopped. Save them in this task folder, e.g. `tasks/T-002-frontend-foundation/screens/`,
and link them from the report. Put next to them `01-course-picker.png` and list the visible differences.

In the report also list: which agent you used and the output of `claude mcp list` / `codex mcp list`, the Node.js
and Next.js versions, the npm scripts, any shadcn/ui components you added, and every place where you deviated from
this brief and why.

## Notes
- Use the Context7 MCP for current Next.js / next-intl / openapi-typescript docs and the shadcn MCP for components —
  APIs change, do not rely on memory.
- If something in this brief contradicts the code or the design, do not guess: add a report round with
  `Status: blocked` and your questions.
- Branch `mp/frontend-foundation`; commit messages like `ui: course picker search (T-002)`;
  PR title `T-002: Frontend foundation and course picker`.
