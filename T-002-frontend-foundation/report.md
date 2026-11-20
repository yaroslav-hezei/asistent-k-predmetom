# Report — T-002

## Round 1 · 2026-11-20

Status: ready for review  
PR: pending (branch `mp/frontend-foundation`)

### Did

- Created the Next.js App Router frontend with TypeScript, Tailwind, Inter, and shadcn/ui components (Button, Dialog, Native Select, Sheet).
- Added the shared responsive navigation, cookie-backed Slovak and English translations, course picker, course-specific chat placeholder, and community and notification placeholders.
- Connected search, study plans, and course detail to FastAPI through one typed `openapi-fetch` client. The study choice persists under `hip.myCourses`.
- Added frontend CI and documented local setup, the API URL, scripts, and schema regeneration.

### Files

- `frontend/` contains the app, translations, generated OpenAPI types, configuration, and README.
- `.github/workflows/frontend.yml` runs the frontend checks on relevant pull requests and pushes to main.
- `screens/` contains the design reference and Playwright screenshots.

### Verified

- Codex reported the following through `codex mcp list`. Playwright was used for live browser checks, shadcn for registry components, and Context7 for Next.js, next-intl, and OpenAPI documentation.

  ```text
  Name        Command  Args                      Env  Cwd  Status   Auth
  context7    npx      -y @upstash/context7-mcp  -    -    enabled  Unsupported
  playwright  npx      @playwright/mcp@latest    -    -    enabled  Unsupported
  shadcn      npx      shadcn@latest mcp         -    -    enabled  Unsupported
  ```

- Node.js 26.13.1, npm 10.9.2, Next.js 16.4.6, Python 3.12.10. Frontend scripts are `dev`, `lint`, `typecheck`, `build`, `start`, and `gen:api`.
- From `backend/`, `..\scratch\t002-venv\Scripts\python.exe -m pytest -q` passed all 16 tests. The same interpreter ran `-m uvicorn app.main:app --host 127.0.0.1 --port 8000`. HTTP checks returned 32 rows from `GET /programs`, 563 from `GET /courses`, and 8 from `GET /programs/65669424/courses?year=3&semester=ZS`. The plan included course 69574272, Hospodárska informatika v praxi.
- From `frontend/`, `npm ci`, `npm run lint`, `npm run typecheck` (includes `tsc --noEmit`), and `npm run build` all exited 0. `npm run gen:api` reproduced the same SHA-256 hash for `src/lib/api/schema.d.ts`. npm reported four moderate findings in the dependency graph rooted at shadcn tooling.
- With `npm run dev -- --hostname 127.0.0.1`, Playwright opened `http://localhost:3000/`, confirmed the redirect, checked that one character issues zero searches, and found the expected course for `zaklady algoritmizacie` and `26000629`. It checked the empty result for `xyzxyz`, keyboard activation, course name and code, the unknown-course message, both placeholder routes, and locale switching including the HTML language.
- Playwright counted all 32 programs and distinguished the three Bc. Informatika variants. It selected Hospodárska informatika (Bc.), year 3, winter semester, verified eight cards after saving and again after a reload, and tested fallback for a missing saved program.
- At 390 px, Playwright opened and closed the drawer, changed language within it, and confirmed no horizontal document overflow in the picker, search, dialog, and error states. With FastAPI stopped, the picker, search, and chat showed translated errors with zero uncaught page errors.
- GitHub PR CI is pending publication.

| State | Desktop 1440×900 | Mobile 390×844 |
| --- | --- | --- |
| Selected plan | [Picker](screens/desktop-picker.png) | [Picker](screens/mobile-picker.png) |
| Search | [Search](screens/desktop-search.png) | [Search](screens/mobile-search.png) |
| Study dialog | [Dialog](screens/desktop-dialog.png) | [Dialog](screens/mobile-dialog.png) |
| English | [English](screens/desktop-english.png) | [English](screens/mobile-english.png) |
| FastAPI stopped | [Offline](screens/desktop-backend-offline.png) | [Offline](screens/mobile-backend-offline.png) |
| Navigation | | [Drawer](screens/mobile-navigation.png) |

### Deviations from the task

- The [desktop design reference](screens/01-course-picker.png) shows three illustrative cards. The live plan shows eight API courses in three columns, with translated semester names. The hint describes starting a new chat, which is the course-switching action implemented here.
- The prototype includes sample history, recently used courses, a badge, profile details, a desktop sidebar toggle, and a prototype watermark. These are absent in the implementation. The mobile drawer uses the same navigation and language controls as the desktop sidebar.
- The sidebar icons use Lucide equivalents. The desktop sidebar, top-bar height, course picker width, card grid, and FEI theme follow the design reference.

### Questions

- None. Commit, push, and PR publication await approval.
