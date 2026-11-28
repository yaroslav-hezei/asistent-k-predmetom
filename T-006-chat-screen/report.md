# Report — T-006

## Round 1 · 2026-11-28
Status: blocked
PR: pending (branch `mp/chat-screen`)

Did:
- Created a separate worktree from the local `origin/main` at `b960bda` because the T-004 worktree has local changes.
- Confirmed that the baseline contains the chat router and generated API types.

Verified:
- `git -C tasks pull --no-rebase` failed to connect to github.com:443. The local tasks checkout contains T-006.
- `python -m pip install -r requirements-dev.txt --disable-pip-version-check` could not download `google-genai==3.6.1` (WinError 10013).
- `python -c 'from app.main import app'` failed with `ModuleNotFoundError: No module named 'google'`.
- `codex mcp list` failed with `failed to resolve CODEX_HOME: Could not find home directory`.

Deviations from the task:
- The required live API and student05 baseline login checks are pending. No source code or shared database changes were made.

Questions:
- Can the backend dependencies be installed in the project venv from a terminal with PyPI access?

## Round 2 · 2026-11-28
Status: blocked
PR: pending (branch `mp/chat-screen`)

Verified:
- The installed dependencies now allow FastAPI to import. `app.openapi()` lists `/ask`, `/chats` and `/chats/{chat_id}`.
- `python -m pytest -q tests/test_chat.py`: 16 passed.
- `python -m uvicorn app.main:app --env-file ../../code/.env`: startup could not connect to Supabase Postgres on port 5432 (WinError 10013).
- `npm.cmd run dev -- --hostname localhost`: frontend ready. Playwright submitted the existing student05 demo login and received the translated sign-in failure.

Deviations from the task:
- The required live baseline is still blocked. No source code or shared database changes were made.

## Round 3 · 2026-11-28
Status: blocked
PR: pending (branch `mp/chat-screen`)

Verified:
- The externally started backend serves `http://localhost:8000/openapi.json` with all three chat routes.
- Playwright retries the student05 baseline login and remains at `/login` with the translated failure.
- Node fetch to the configured Supabase Auth health endpoint from the restricted frontend environment fails with `EACCES`.

Questions:
- Can the frontend also be started from the regular PowerShell terminal so the existing login can reach Supabase Auth?

## Round 4 · 2026-11-28
Status: ready for review
PR: pending (branch `mp/chat-screen`)

Did:
- Added new and saved chat pages, optimistic questions, a composer, and the found, unknown, login-required, unavailable, and missing-chat states.
- Rendered numbered references and exact API quotes, author/date/verification metadata, and the two source warnings. Reused the existing shadcn Button; added no registry components.
- Passed the course name from the page to AppShell through a pathname-scoped React context. The top bar keeps the title visible while the repeated course header is hidden at short viewport heights.
- Loaded GET /chats on the server once per request for the signed-in user. After POST /ask, the client replaces the new-chat URL and refreshes the router. The root layout refetches history; the picker uses the same cached request and takes the first four distinct courses.
- The history mark takes the first letter of up to three words with at least three letters (Unicode), then uppercases them. Examples: Hospodárska informatika v praxi → HIP; Základy algoritmizácie a programovania → ZAP; Analýza a návrh informačných systémov 1 → ANI.

Files:
- `frontend/src/app/chat/`, `frontend/src/app/layout.tsx`, `frontend/src/components/chat/`, `frontend/src/components/{app-shell,course-picker}.tsx`, `frontend/src/lib/{chat-history.ts,api/client.ts}`, `frontend/messages/{sk,en}.json`.

Verified:
- `npm.cmd ci --offline`: installed 601 packages. The shell uses Node v22.14.0; the project declares Node 26.
- `npm.cmd run gen:api` followed by `git diff --exit-code -- src/lib/api/schema.d.ts`: no schema changes.
- `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build`, `git diff --check`: passed.
- `python -m pytest -q tests/test_chat.py`: 16 passed. Live OpenAPI exposed all three routes, and Playwright verified successful student05 login before code changes.
- Real API: student05 created two test chats in the shared database. Základy algoritmizácie a programovania received two questions (grading and a question with “neviem”). Analýza a návrh informačných systémov 1 received one grading question. Verified persisted messages, active history, most recent course first, the citation highlight, and the MAIS link destination.
- Playwright POST /ask mocks: unverified student answer, verified teacher answer, teacher note, three source chips and an unmatched reference as text, 1500-character exact quote expansion/collapse, outdated sheet, and 401 draft retention after reload. Mocks used test-data labels and wrote no database records.
- At 390 px the composer text was 16 px and the send button 44 × 44 px. At a simulated 390 × 370 viewport, the 1000-character draft kept the button visible (bottom at 309 px). Checked `document.documentElement.scrollWidth <= innerWidth` in the desktop and mobile chat flows, including the expanded unbroken mock quote at 390 px. Verified Shift+Enter, Enter, minimum length, maximum length, disabled send while waiting, Slovak/English, drawer navigation, unknown UUID and both guest routes.
- Desktop (1440 × 900): [empty](screens/desktop-empty.png), [waiting](screens/desktop-waiting.png), [sheet](screens/desktop-sheet.png), [unknown](screens/desktop-neviem.png), [history](screens/desktop-history.png), [recent courses](screens/desktop-recent.png), [existing-chat guest](screens/desktop-login.png), [new-chat guest](screens/desktop-new-login.png), [missing chat](screens/desktop-not-found.png), [network error](screens/desktop-error.png), [English](screens/desktop-english.png), [community sources](screens/desktop-mocked-community.png), [outdated sheet](screens/desktop-mocked-outdated.png).
- Phone (390 px, iPhone 13-style Chromium emulation): [empty](screens/phone-empty.png), [waiting](screens/phone-waiting.png), [sheet](screens/phone-sheet.png), [unknown](screens/phone-neviem.png), [drawer](screens/phone-history.png), [recent courses](screens/phone-recent.png), [existing-chat guest](screens/phone-login.png), [new-chat guest](screens/phone-new-login.png), [missing chat](screens/phone-not-found.png), [network error](screens/phone-error.png), [English](screens/phone-english.png), [reduced viewport](screens/phone-reduced-viewport.png), [long quote](screens/phone-mocked-long-quote.png).

Deviations from the task:
- Simulated a refused POST /ask connection in Playwright while leaving the user's backend running. Tested the keyboard layout by reducing the viewport; a physical iPhone was unavailable.
- Playwright and Context7 responded. `codex mcp list` returned `failed to resolve CODEX_HOME: Could not find home directory`. No new shadcn registry component was needed.
- Used the locally available origin/main at b960bda. GitHub access via Git was unavailable in the sandbox, so the PR and CI are pending. Code and report await the explicit Git-write approval required by AGENTS.md.

Questions:
- None.
