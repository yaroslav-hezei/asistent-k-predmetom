---
id: T-006
title: Chat screen — ask about a course, the answer with its sources, "Neviem", "História"
assignee: MP
status: done          # open → changes → done | dropped
created: 2026-11-26
due:
---

# T-006 — Chat screen — ask about a course, the answer with its sources, "Neviem", "História"

## Goal
Build the heart of the app: the screen where a student, after choosing a course, asks a question and gets an
answer. The answer is short text with numbered references [1], [2], and under it the **sources**: for each one the
exact quoted text, where it comes from (the MAIS information sheet, a student's answer, or the teacher's note), its
date, its author and whether it is official, verified or not verified. When the assistant does not know, it says
"Neviem" and offers to ask other students. The chat is saved: after a page reload, or later from "História" in the
sidebar, the student sees the same questions and answers.

Why it matters: this is the screen the whole project is about, and the screen the final test will spend most time
on. The prototype test (5 students, 12.11.) showed what makes an answer trustworthy for students: they want to see
the **exact text** from the sheet, not only a link; they want to see **who** wrote each source; and "Neoverené"
must be explained, because one tester read it as "wrong answer". These are the changes after the test in
`docs/design/UI.md`, and they override the prototype pictures.

What you should be able to explain about your part: the frontend never decides what the answer is or where it comes
from. It sends the question to our API (`POST /ask`) and shows what comes back. The text of the answer only
**cites numbers** ([1]); the sources themselves — quote, section, link, date, author, verified — are filled in by
the backend from stored data, never by the language model, so the model cannot invent a quote or a source. The
screen's job is to make this clear and readable: which part of the answer comes from which source, and how much a
source can be trusted.

## Context
- **The API exists** (PR #13 — merge commit in `main` before you start): `POST /ask`, `GET /chats`,
  `GET /chats/{chat_id}`. Exact shapes are in "Contract" below and in the generated types
  `src/lib/api/schema.d.ts` (already regenerated in PR #13). Interactive docs at `http://localhost:8000/docs`.
- **The answers are placeholders for now.** The real assistant (search in the knowledge base + language model) is
  being built on the backend in parallel. Until it is ready, `POST /ask` answers every question with the same
  sentence ("Ukážková odpoveď: …[1].") and one real section of the course's MAIS sheet as the source, quoted
  exactly. A question that contains the word **"neviem"** gets the "Neviem" answer — use it to build that state.
  When the real assistant arrives, nothing changes for the screen: same API, same shapes. Build for real answers:
  several paragraphs, several sources, sources of all three types.
- **Login is required to ask** (decided). Every chat endpoint needs the token; the shared `api` client adds it in
  the browser, `serverApi()` (`@/lib/api/server`) on the server. A logged-out visitor can still browse courses in the
  picker, but cannot ask and has no "História".
- **One chat = one course** (decided). A chat is created by the first question (`chat_id: null`); the response
  carries the new `chat_id`; every next question in the same chat sends that `chat_id`.
- **Dates.** The MAIS sheets have no reliable "last changed" date (MAIS rewrites it every year), so for a sheet the
  date is the day we read the sheet from MAIS, shown as **"stav k 17. 11. 2026"** (decided). For community answers
  and teacher notes it is the day (and time) they were written.
- **Outdated-sheet warning:** the API has the field (`outdated`), but the rule for it is not decided yet, so it is
  always `false` for now. Build the warning box anyway (screen 02) and test it with a mocked response (see "How to
  verify").
- **Design:**
  - `docs/design/screens/02-answer-with-source.png` — the answer, a reference chip [1], the warning box, "Zdroje" with
    a source card, the composer at the bottom, "AI sa môže mýliť. Overuj si informácie v zdroji." under it.
  - `docs/design/screens/03-neviem-publish.png` — the "Neviem" answer and the card "Opýtaj sa ostatných".
  - `docs/design/screens/05-student-answer.png` — a source from a student's answer, "Neoverené", the explanation line
    "Túto odpoveď napísal študent a zatiaľ ju neoveril vyučujúci."
  - "História" in the sidebar on all three screens; "Naposledy použité" on `01-course-picker.png`.
  - `docs/design/UI.md` — tokens (`warn-*`, `ok-*`, `unverified-*`, `official-*`, `fei-soft`, `fei-dark`), chat
    column 760px, radii, and the **changes after the test**, which override the pictures:
    1. show the **exact quote** (section + quoted text) under the answer, not only a link to MAIS;
    2. the **author** is visible on every source (MAIS, the student's nickname, or the teacher);
    3. (teacher screen, not this task);
    4. explain "Neoverené" with one short line.
- **What already exists in the frontend:** `/chat` = the course picker (`course-picker.tsx`); a card opens
  `/chat/new?course=<id>`, which today only shows the course and "čoskoro" (`src/app/chat/new/page.tsx`) — this is
  where the chat starts. `useMe()` gives the logged-in user or `null`. The sidebar and the top bar are in
  `src/components/app-shell.tsx`. UI text through `next-intl` (`messages/sk.json`, `messages/en.json`).
- **Rules from `AGENTS.md` that matter here:** Next.js is UI only — no business logic, all data through the API;
  generated API types are never edited by hand; UI text only through i18n keys in Slovak and English; check UI with
  Playwright at 1440×900 and 390 px.

## Before you start
1. `git pull` on `main` (PR #13 must be in it: `backend/app/routers/chat.py` exists), then `npm ci` in `frontend/`
   (no new packages in PR #13, but keep it clean). In `backend/`, reinstall the requirements into your venv
   (`.venv/Scripts/python.exe -m pip install -r requirements-dev.txt`).
2. Use the same `.env` (repo root) and `frontend/.env.local` you got for T-004 — no new variables.
3. Run the backend with the env file and the frontend:
   ```
   cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --env-file ../.env   # Linux/macOS: .venv/bin/python
   cd frontend && npm run dev                                                                   # http://localhost:3000
   ```
   Check **before you change anything**: `http://localhost:8000/docs` lists `POST /ask`, `GET /chats` and
   `GET /chats/{chat_id}`, and logging in to the app as `student05@example.com` works.
4. MCP tools: run `claude mcp list` (or `codex mcp list`) and check that **Playwright**, **shadcn** and **Context7**
   are connected (as in T-002 / T-004; install steps in `CONTRIBUTING.md`). Paste the output into the report.

## What to do
1. **Start a chat (`/chat/new?course=<id>`).** Replace the "čoskoro" text with the chat layout: the course header,
   an empty message area with one short hint ("Opýtaj sa čokoľvek o predmete …"), and the **composer** at the
   bottom of the column (see 4). The first question sends `POST /ask` with `chat_id: null`. When the answer comes,
   the URL becomes `/chat/<chat_id>` (use `router.replace` so "Back" does not return to the empty chat), and the
   new chat appears at the top of "História".
2. **Open a chat (`/chat/[chatId]`, new route).** Load `GET /chats/{chat_id}` on the server with `serverApi()`
   and show the course header and all messages, oldest first, scrolled to the newest. Next questions send
   `POST /ask` with this `chat_id` and the chat's `course.id`. A chat that does not exist or is not yours (404) →
   a "Chat sa nenašiel" message with a link back to `/chat`. A logged-out visitor → the login prompt (see 7).
3. **Messages.**
   - The user's question: a bubble on the right (as in the prototype).
   - The assistant's answer: the logo mark on the left and the text. Keep line breaks of the text. Replace every
     `[n]` in the text with a **reference chip** (small, `fei-soft` background, `fei-dark` number, as in screen 02).
     Clicking (tapping) a chip scrolls to source *n* of that answer and highlights it briefly. A `[n]` with no
     matching source stays plain text. Render the text as text — never as HTML (no `dangerouslySetInnerHTML`).
   - **While waiting** for an answer: the question appears at once, under it a "píše…" indicator; the composer is
     disabled. Answers take a few seconds with the real assistant.
   - **"Neviem"** (`found: false`): bold "Neviem." and the line from screen 03, then the card "Opýtaj sa ostatných"
     with its text and the two buttons "Zverejniť otázku" and "Upraviť text". **Publishing does not exist yet**
     (a later task): show both buttons **disabled** with one short line under them, e.g. "Zverejňovanie otázok
     pribudne čoskoro." No sources block for "Neviem".
4. **Composer.** A text area that grows with the text up to ~6 lines, then scrolls; placeholder "Opýtaj sa na
   predmet…"; a round send button (`fei`). **Enter** sends, **Shift+Enter** makes a new line (on desktop); on a
   phone the send button. The question is 3–1000 characters after trimming (the API's limit): the button is disabled
   below 3; at the limit stop typing and show a small counter in the last 100 characters. Text 16px (iPhone zooms into
   smaller inputs), button ≥ 44×44px. Under the composer: "AI sa môže mýliť. Overuj si informácie v zdroji."
   On a phone the composer stays at the bottom and stays visible when the keyboard opens.
5. **Sources ("Zdroje") under each answer** — one card per source, in the order of `n`:
   - Left: the number chip `n` and an icon by type (document for `sheet`, people for `answer`, a megaphone / info
     icon for `course_note` — from `lucide-react`).
   - Title by type: `sheet` → "Informačný list predmetu · MAIS"; `answer` → "Odpoveď študenta · Otázky komunity" or,
     when `author.kind` is `vyucujuci`, "Odpoveď vyučujúceho · Otázky komunity"; `course_note` → "Aktuálna
     informácia od vyučujúceho".
   - Second line: `sheet` → the section and "stav k <date>"; `answer` → the author's nickname, the date and time,
     and "na otázku „<question.text>“" cut with "…"; `course_note` → the teacher's nickname and the date.
   - Badge on the right: `sheet` → "Oficiálny dokument" (`official-*` tokens); `answer` and `course_note` →
     "Overené" (`ok-*`) when `verified`, otherwise "Neoverené" (`unverified-*`).
   - **The quote** (change 1 after the test): the `quote` text in the card, visually set apart (e.g. a left border),
     line breaks kept. Long quotes: show about 4 lines with "Zobraziť celý text" / "Skryť" (a real button).
   - `sheet` with a `url`: a link icon button that opens MAIS in a new tab (`target="_blank" rel="noopener noreferrer"`),
     with an accessible name ("Otvoriť v MAIS"). Other types: no link in this task (the community page comes later).
   - Dates in the UI language: `Intl.DateTimeFormat` with the current locale (`17. 11. 2026` in Slovak,
     `17 Nov 2026` in English is fine).
6. **Notes above "Zdroje"** (only when they apply):
   - **Outdated warning** (screen 02): when any `sheet` source has `outdated: true` — the box with the `warn-*`
     tokens and a warning icon: "Informačný list môže byť neaktuálny. Over si informácie na prvej prednáške alebo u
     vyučujúceho." (The prototype's "naposledy zmenený v roku 2017" cannot be used: we have no such date.)
   - **Unverified explanation** (change 4, screen 05): when any `answer` source has `verified: false` — the grey box
     (`unverified-*`) with a person icon: "Túto odpoveď napísal študent a zatiaľ ju neoveril vyučujúci."
7. **Login prompt.** Logged out on `/chat/new?course=…` or `/chat/<id>`: instead of the composer (and of the
   messages), a short line "Ak sa chceš opýtať, prihlás sa testovacím účtom." with a "Prihlásiť sa" button to
   `/login`. If the token expires while asking (`POST /ask` → 401): the same prompt, keep the typed question.
8. **Errors while asking.** Any failure except 401 (network, backend down, 5xx, 422): keep the question text in
   the composer, show a translated error near the composer ("Otázku sa nepodarilo odoslať. Skús to znova."), and
   remove the waiting indicator. No crash, no half-shown message.
9. **"História" in the sidebar** (desktop sidebar and the phone drawer), between the navigation and the user row,
   as in the screens: a "História" heading and the chats from `GET /chats` (newest first): a short course mark
   (see Notes) and the title cut with "…". The current chat is highlighted. Tapping opens `/chat/<id>` (and closes
   the drawer on a phone). Logged out → no "História". The list updates after a new chat is created and after each
   question (the asked chat moves to the top). Empty list → nothing (no heading).
10. **"Naposledy použité" in the course picker** (screen 01): for a logged-in user, up to 4 most recently used
    courses — the distinct courses of `GET /chats`, newest first — as cards like "Moje predmety"; a card opens a
    new chat for that course (`/chat/new?course=<id>`, as the other cards). Logged out or no chats → the section is
    not shown.
11. **Top bar.** On chat pages the top bar shows the course name (as in the prototype) instead of "Nový chat"; the
    "· 3. roč., ZS" part is not needed. How the page passes the name to `AppShell` is your choice — describe it in
    the report.
12. **Translations.** Every new text in `messages/sk.json` and `messages/en.json` under `chat.*` (and `layout.*`
    for "História"). Remove keys you no longer use (e.g. `chat.soon`).

## Out of scope
- Publishing a question, "similar questions", the community page, notifications, badge counts, the teacher's
  screens — later tasks (their API does not exist yet).
- Streaming the answer word by word (the API returns the whole answer; decided).
- Renaming or deleting chats, a "scroll to bottom" button, the "· 3. roč., ZS" part of the top bar.
- Any change in `backend/`, `supabase/`, `data/`, `scripts/`, `docs/`, CI workflows; anything under
  `src/lib/supabase/`, `src/proxy.ts`, `src/lib/auth/`, `src/components/me-provider.tsx`.
  In `src/lib/api/` you may only **add type aliases** to `client.ts` (like the existing `Course`, `Me`), e.g.
  `export type ChatMessage = components["schemas"]["ChatMessage"];`. If you think anything else there needs a change,
  add a report round with `Status: blocked` and describe why.

## Files and folders
- Change: `src/app/chat/new/page.tsx`, `src/components/app-shell.tsx` ("História", course name in the top bar),
  `src/components/course-picker.tsx` ("Naposledy použité"), `src/lib/api/client.ts` (type aliases only),
  `messages/sk.json`, `messages/en.json`, `src/app/globals.css` (only if a token from `UI.md` is missing).
- New: `src/app/chat/[chatId]/page.tsx`; components, for example `src/components/chat/` with `chat-view.tsx`,
  `message.tsx`, `answer-text.tsx` (the `[n]` chips), `source-card.tsx`, `composer.tsx`, `history.tsx`, and a small
  pure function for the course mark. The structure is your choice — keep each file focused.
- Do not touch: see "Out of scope". Never commit `.env` or `frontend/.env.local`.

## Contract
All of it exists (PR #13); nothing new on the backend. Types from `src/lib/api/schema.d.ts`.

- **`POST /ask`** — body `AskRequest`, response `AskResponse`:
  ```jsonc
  // request: the first question of a new chat
  {"course_id": "65954478", "question": "Ako sa hodnotí tento predmet?", "chat_id": null}
  // response (placeholder answer, ZAP; ids shortened)
  {
    "chat_id": "3f1e…",
    "question": {"id": "a1…", "role": "user", "text": "Ako sa hodnotí tento predmet?", "found": null,
                 "sources": [], "created_at": "2026-11-26T16:05:12.345678Z"},
    "answer": {
      "id": "b2…", "role": "assistant", "found": true,
      "text": "Ukážková odpoveď: asistent zatiaľ nevyhľadáva odpoveď na otázku, len ukazuje jednu časť informačného listu [1].",
      "sources": [{
        "n": 1, "type": "sheet", "section": "Priebežné hodnotenie (PH)",
        "quote": "Študent prospeje v PH a získa zápočet, keď splní podmienku získať min. 11% z 20%.\ntesty, zadanie",
        "url": "https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId=65954478",
        "question": null, "date": "2026-11-17T15:11:35Z",
        "author": {"kind": "mais", "nickname": null}, "verified": true, "outdated": false
      }],
      "created_at": "2026-11-26T16:05:12.401234Z"
    }
  }
  // the next question in the same chat
  {"course_id": "65954478", "question": "Neviem, kedy je skúška?", "chat_id": "3f1e…"}
  // → "answer": {"found": false, "text": null, "sources": [], …}
  ```
  Errors: 401 not logged in / token expired; 403 the account has no profile; 404 unknown course, or the chat does
  not exist / is not yours; 422 the question is shorter than 3 or longer than 1000 characters (after trimming), or
  the chat belongs to another course.
- **`GET /chats`** → `ChatSummary[]` (newest first, at most 50): `{id, course: CourseSummary, title, updated_at}`.
  `title` = the first question of the chat.
- **`GET /chats/{chat_id}`** → `Chat` = `ChatSummary` + `messages: ChatMessage[]` (oldest first). The messages and
  their sources are exactly what `POST /ask` returned, so the same rendering works for both.
- **`Source`** fields: `n` (cited as `[n]`), `type` (`sheet` | `answer` | `course_note`), `section` (sheet only),
  `quote`, `url` (sheet only), `question` (`{id, text}`, answer only), `date`, `author` (`{kind: mais | student |
  vyucujuci, nickname}`), `verified`, `outdated`.
- **`ChatMessage`**: `role` `user` | `assistant`; `text` (null for "Neviem"); `found` (null for user, false =
  "Neviem"); `sources`; `created_at`.
- **New, you define:** translation keys, component structure, the course-mark function (show it in the report).

## Done when
- [ ] Logged in as `student05`: from the picker, ZAP (`Základy algoritmizácie a programovania`) → `/chat/new` →
      "Ako sa hodnotí tento predmet?" → the question bubble, "píše…", then the answer with chip [1] and the source
      card: "Informačný list predmetu · MAIS", "Priebežné hodnotenie (PH) · stav k 17. 11. 2026", "Oficiálny
      dokument", the full quote, a working MAIS link. The URL is `/chat/<id>`.
- [ ] Tapping chip [1] scrolls to the source and highlights it.
- [ ] A second question with the word "neviem" in the same chat → "Neviem." + the "Opýtaj sa ostatných" card with
      disabled buttons and the "čoskoro" line; no sources.
- [ ] Reload → the same 4 messages; the chat is at the top of "História"; tapping it in "História" opens it.
- [ ] A second chat for another course → both in "História", newest first; "Naposledy použité" in the picker shows
      both courses.
- [ ] Mocked responses (see "How to verify") render correctly: a student answer (unverified) with the explanation
      line and "Neoverené"; a teacher's answer with "Overené"; a `course_note`; the outdated warning; three sources
      and chips [1] [2] [3] in one answer; a quote of 1500 characters (collapsed, "Zobraziť celý text" works).
- [ ] Logged out: `/chat/new?course=65954478` and `/chat/<id>` show the login prompt; no "História".
- [ ] `/chat/<id of another account's chat or a random uuid>` → "Chat sa nenašiel" with a link to `/chat`.
- [ ] Backend stopped → asking shows the translated error, the question stays in the composer, no crash.
- [ ] Composer: Enter sends, Shift+Enter new line, disabled below 3 characters and while waiting; 16px text;
      the send button ≥ 44×44px.
- [ ] Phone 390 px: no horizontal scroll on the chat (with long quotes and a long course name); the composer
      visible; chips and buttons tappable (≥ 44px tap area for buttons; chips may be smaller but have padding).
- [ ] SK | EN: every new text switches language; no hard-coded UI text.
- [ ] `npm run gen:api` gives no diff, `npm run lint`, `npm run typecheck`, `npm run build` pass; CI on the PR is green.

## How to verify
```
# terminal 1 — backend with the env file
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --env-file ../.env

# terminal 2 — frontend
cd frontend
npm ci
npm run gen:api && git diff --exit-code src/lib/api/schema.d.ts
npm run lint
npm run typecheck
npm run build
npm run dev                         # http://localhost:3000 (not 127.0.0.1: CORS allows only localhost)
```
**Real API** — with Playwright at **1440×900** and with the **"iPhone 13"** device profile (touch, mobile user
agent), logged in as `student05`: the empty new chat; waiting ("píše…"); the answer with its source; "Neviem";
the chat after reload with "História" (on the phone: the drawer open); "Naposledy použité" in the picker; the
logged-out login prompt; "Chat sa nenašiel"; the error with the backend stopped; the chat in English.

**Mocked responses** — the placeholder only returns sheet sources, so intercept the API in Playwright
(`page.route("**/ask", …)` and `page.route("**/chats/*", …)`) and return your own JSON built from the Contract
shapes. Mark every mocked text as test data, e.g. "Ukážková odpoveď študenta (testovacie údaje)" — never invent
facts about a real course. Cover: `type: "answer"` with `author.kind: "student"`, `verified: false`, a
`question` `{id, text}`; `type: "answer"` with `author.kind: "vyucujuci"`, `verified: true`; `type: "course_note"`;
a `sheet` with `outdated: true`; one answer with three sources; a 1500-character quote.

Save the screenshots in `tasks/T-006-chat-screen/screens/` and link them from the report. Also measure with
Playwright and list in the report at 390 px: the composer's font size and the send button's size, and
`document.documentElement.scrollWidth <= innerWidth` for each screenshot.

In the report also list: the output of `claude mcp list` / `codex mcp list`; how the course name reaches the top
bar; the course-mark function with 3 examples; how "História" is refreshed; the test chats you created in the
shared database (account, courses); every deviation from this brief with the reason.

## Notes
- **The database is shared** (development and the demo). Every question you ask is stored as a real chat of the
  test account. Ask only as **`student05`** and keep it to what you need for the checks; we clear the test chats
  before the final test. Do not ask as other accounts.
- **Course mark in "História"** (the prototype shows "HIP", "PA", "ZS"): our catalogue has only numeric course
  codes, so build the mark from the course name — the first letters of the words with 3 or more letters, up to 3,
  in upper case: "Hospodárska informatika v praxi" → "HIP", "Základy algoritmizácie a programovania" → "ZAP".
  Display only; never use it to identify a course.
- The placeholder answer is Slovak even for English questions; the real assistant answers in the language of the
  question. The UI language is independent of it.
- Use Context7 for Next.js (dynamic route params, `router.replace`, server components with `serverApi()`), and the
  shadcn MCP for any new component (`base-nova` style on Base UI) — do not rely on memory.
- If something in this brief contradicts the code or the design, do not guess: add a report round with
  `Status: blocked` and your questions.
- Branch `mp/chat-screen` from a fresh `main`; commit messages like `ui: source card (T-006)`; PR title
  `T-006: Chat screen`. Open the PR yourself, and **push your report** (`tasks/T-006-chat-screen/report.md`,
  template `tasks/_templates/report.md`) — the review starts from the report.
