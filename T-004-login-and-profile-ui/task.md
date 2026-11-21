---
id: T-004
title: Login screen, the user in the layout, "Moje predmety" from the profile
assignee: MP
status: open          # open → changes → done | dropped
created: 2026-11-21
due: 2026-11-25
---

# T-004 — Login screen, the user in the layout, "Moje predmety" from the profile

## Goal
Make login a finished part of the app. Login already **works**: a test account can log in and out, the app knows
who is logged in on every page, and every request to our API carries the user's token. What is missing is the part
people see and touch: a proper login screen with a quick way to pick a demo account, the logged-in user shown in the
layout as in the prototype (avatar, name, role, a menu to log out), and "Moje predmety" that comes from the user's
profile instead of the browser. All of it must work as well on a phone as on a laptop — the final test with real
students will happen largely on phones.

Why it matters: the final test of the course uses pre-made test accounts — every tester gets one ("you are
student04") — so the login screen is the first thing each tester sees, often on a phone; if it is awkward, the test
starts badly. And once a student is logged in, the app should already know their study program, year and semester,
so "Moje predmety" shows their courses without any setup.

What you should be able to explain about your part: the frontend only shows the user; it never decides who the user
is. Supabase Auth checks the password and gives the browser a token (kept in a cookie). Our backend checks that token
and answers `GET /me` with the profile. The frontend reads the profile through a ready-made helper (`useMe()`) and
saves changes through the API (`PATCH /me`). The demo passwords on the login screen are public on purpose: the test
accounts contain no real data and self-registration is switched off.

## Context
- **What already exists in `main`** (PR #9 backend, PR #10 frontend — read `frontend/README.md`, section "Login"):
  - `/login` — a minimal working page: e-mail, password, "Prihlásiť sa", error messages
    (`src/app/login/page.tsx`, `src/components/login-form.tsx`). A logged-in user who opens `/login` is sent to `/chat`.
  - The sidebar (and the phone drawer) shows the nickname, the role and "Odhlásiť sa", or "Prihlásiť sa" when
    nobody is logged in (`Account` in `src/components/app-shell.tsx`). This is a placeholder you replace.
  - `useMe()` (from `@/components/me-provider`) in client components → the logged-in user's profile (`Me`, see
    Contract) or `null`. It is loaded once per page on the server by the root layout.
  - The shared API client `api` (`@/lib/api/client`) adds the user's token to every request in the browser by itself.
    You do not handle tokens anywhere.
  - Server actions `signIn` / `signOut` (`@/lib/auth/actions`): `signIn` is used by the login form
    (`useActionState`), `signOut` by a `<form action={signOut}>`. Log-out ends only the session in this browser
    (the same test account stays logged in on other devices — on purpose, for demos).
  - The phone basics on `/login` are already right; keep them: inputs with 16px text (iPhone Safari zooms into any
    input with smaller text), 44px high inputs and button, `type="email"` + `autocomplete="username"`,
    `autocomplete="current-password"`, the e-mail stays filled after a failed attempt.
- **Test accounts** — `backend/scripts/test_users.json` (public; the passwords are shown on the login screen by
  decision): 10 students `student01@example.com` … `student10@example.com` (all Hospodárska informatika Bc., ZS;
  01–03 → 1. ročník, 04–06 → 2. ročník, 07–10 → 3. ročník) and 3 teachers `vyucujuci01@example.com` …
  `vyucujuci03@example.com` (no study program; they verify all 42 courses of that program). One password per role
  (`passwords.student`, `passwords.vyucujuci` in that file). Self-registration is off; no password reset in the MVP.
- **Decisions for this task (decided):**
  1. **Demo accounts on the login screen as a dropdown** "Vyber testovací účet": choosing an account fills the
     e-mail and the password; the user can still type them by hand. The list and the two passwords live in one
     frontend constant copied from `test_users.json` (they are public, and the frontend must not read files of the
     backend). Reason: a tester on a phone should not have to type `student04@example.com` and a password.
  2. **User block as in the prototype**: avatar (initials), nickname, role, in the sidebar's bottom row next to
     SK | EN; and the avatar on the right of the top bar. **Log out** is in a small menu that opens from the top-bar
     avatar (nickname, role, "Odhlásiť sa"). Reason: on a phone the top bar is always visible, so logging out does
     not require opening the drawer.
  3. **"Moje predmety" from the profile** for a logged-in user; for a logged-out visitor it stays in `localStorage`
     exactly as now (key `hip.myCourses`). The two are never merged: when logged in, the profile wins.
  4. **No page requires login** in this task. A logged-out visitor can still use the course picker as now.
- **Design.** `docs/design/UI.md` (tokens, the "changes after the test") and `docs/design/screens/01-course-picker.png`
  (the user block bottom-left "JM · Jakub M. · Študent" with SK | EN, the avatar "JM" top-right). The prototype has
  **no login screen**: build it from the same tokens (see "What to do" 1). Avatar style from the prototype CSS
  (`docs/design/prototype-hifi.html`, class `.avatar`): circle 34px (32px in the top bar), background `#2A2C33`,
  text `#F2F2EF`, 13px, weight 600 — add the two colors as theme tokens, do not hard-code hex values in components.
- **Rules from `AGENTS.md` that matter here:** Next.js is UI only; all data through the API; UI text only through
  i18n keys in Slovak and English; generated API types are never edited by hand; no secrets in the repo; check UI
  with Playwright at 1440×900 and 390 px.

## Before you start
1. `git pull` on `main` (login arrived on 2026-11-21), then `npm ci` in `frontend/` (two new packages:
   `@supabase/ssr`, `@supabase/supabase-js`).
2. **Values from Yaroslav (privately, never into a file in the repo, a commit, an issue or a report):**
   `DATABASE_URL` and `SUPABASE_URL` for the repo-root `.env` (the backend needs them for `/me`), and
   `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` for `frontend/.env.local` (see
   `frontend/.env.example`). Ask him in the chat before you start.
3. Run the backend with the env file so it can check tokens and read profiles:
   ```
   cd backend
   .venv/Scripts/python.exe -m uvicorn app.main:app --reload --env-file ../.env    # Linux/macOS: .venv/bin/python
   ```
   Then `npm run dev` in `frontend/`. Check that logging in as `student01@example.com` works **before** you change
   anything. `NEXT_PUBLIC_*` values are read when the dev server starts: restart it after editing `.env.local`.
4. Your agent's MCP tools (Playwright, shadcn, Context7) are connected — as in T-002.

## What to do
1. **Login screen (`/login`).** Restyle the page and the form into a centered card (max. ~400px wide):
   - The logo mark and "Asistent k predmetom" as in the sidebar, the title "Prihlásenie", one short line under it.
   - **A "demo režim" box** above the fields, in the `fei-soft` background: one sentence that the app is in a test
     run and the user logs in with the test account they were given, and the dropdown **"Vyber testovací účet"**.
     Items: `student01 — 1. roč.` … `student10 — 3. roč.`, then `vyucujuci01 — vyučujúci` … `vyucujuci03`
     (the words through i18n). Choosing an item fills e-mail and password. Use the existing `NativeSelect`
     component (a real `<select>`: on phones it opens the system picker). Height 44px, text 16px.
   - The e-mail and password fields, the button and the error messages as now (keep the phone basics listed in
     Context). The top bar shows the title "Prihlásenie" on this page.
   - The demo list: a new constant `src/lib/demo-accounts.ts` with the 13 accounts (e-mail, nickname, role, year)
     and the two passwords, with a comment that it must match `backend/scripts/test_users.json`.
2. **User block in the sidebar** (desktop sidebar and the phone drawer): replace the placeholder `Account` with the
   prototype's bottom row — avatar, nickname (one line, cut with "…" if long), role under it ("Študent" /
   "Vyučujúci"), SK | EN on the right. Logged out: in the same row, a "Prihlásiť sa" link (icon + text) instead of
   avatar and name. Login not configured (no Supabase variables): no account part at all, as now.
3. **Avatar in the top bar** (right side, on every page, desktop and phone): logged in → the avatar button opens a
   menu with the nickname, the role and **"Odhlásiť sa"** (calls `signOut`). Logged out → a small "Prihlásiť sa" link
   button instead of the avatar. Add the shadcn/ui `dropdown-menu` component through the shadcn MCP (the project
   uses the `base-nova` style on Base UI — let the MCP pick the matching variant). The menu must work with touch,
   with the keyboard (Enter / Escape) and have an accessible name ("Účet" / "Account").
4. **Initials** for the avatar, one small function used in both places: the first letter of the nickname in upper
   case plus its trailing number if it has one — `student04` → `S04`, `vyucujuci01` → `V01`; without a trailing
   number the first letters of the first two words (`Jakub M.` → `JM`) or the first two letters (`jakub` → `JA`).
5. **"Moje predmety" from the profile** (`src/components/course-picker.tsx`):
   - Logged in (`useMe()` is not null): the choice is `me.study` (`program_id`, `year`, `semester`). Check it against
     `GET /programs` as the code does now for `localStorage` (unknown program or year → treat as "nothing chosen").
     "Zmeniť" opens the same `StudyDialog`; "Uložiť" sends `PATCH /me` with `{program_id, year, semester}` through
     `api`. On success: update the cards at once and call `router.refresh()` (from `next/navigation`) so the
     profile in the layout is reloaded. On an error: keep the dialog open and show a translated error in it
     (a 422 means the API refused the program or year; any other failure → "could not be saved, try again").
     While saving, disable "Uložiť".
   - A teacher has `study: null`: they see the same invitation and can choose a program — it is saved to their
     profile the same way (the API allows it for every role).
   - Logged out: exactly as now (`localStorage`, key `hip.myCourses`). Do not read or write `localStorage` for a
     logged-in user.
6. **Phone details** (width 390 px):
   - Every button and link in the sidebar, the drawer and the top bar is at least 44×44px to tap — in particular
     the drawer's close "×" and the SK | EN buttons, which are about 28px now. On desktop they may stay compact.
   - Nothing overflows horizontally on `/login`, `/chat` (logged in and out), with the dialog and with the menu open.
   - The avatar menu and the dialog fit on the screen.
7. **Tab icon.** The app has no favicon (the browser asks for `/favicon.ico` and gets 404). Add `src/app/icon.svg` —
   the logo mark (the book icon on a rounded `fei` square, as in the sidebar) — and `src/app/apple-icon.png`
   (180×180, the same mark) for "Add to home screen" on iPhone. Use the Next.js App Router file conventions (check
   them in Context7), not a hand-written `<link>`.
8. **Translations.** Every new text in `messages/sk.json` and `messages/en.json`, under `auth.*` (login screen, demo
   box, account menu) and `picker.*` (save errors). Remove keys you no longer use.

## Out of scope
- Anything under `src/lib/supabase/`, `src/proxy.ts`, `src/lib/auth/`, `src/lib/api/` and `src/components/me-provider.tsx`
  — the login plumbing. If you think it needs a change, do not change it: add a report round with
  `Status: blocked` and describe why.
- Protecting pages (redirects to `/login`), roles in the navigation (the teacher's "Overovanie" item), badge counts,
  "História", "Naposledy použité" — later tasks, the API for them does not exist yet.
- Registration, password reset, profile pages, changing the nickname.
- Any change in `backend/`, `supabase/`, `data/`, `scripts/`, `docs/`, CI workflows.

## Files and folders
- Change: `src/app/login/page.tsx`, `src/components/login-form.tsx`, `src/components/app-shell.tsx`,
  `src/components/course-picker.tsx` (and `study-dialog.tsx` only if the error message needs a place there),
  `messages/sk.json`, `messages/en.json`, `src/app/globals.css` (avatar tokens).
- New: `src/lib/demo-accounts.ts`, `src/components/ui/dropdown-menu.tsx` (via shadcn MCP), small components you need
  (e.g. `src/components/avatar.tsx`, `src/components/account-menu.tsx`), `src/app/icon.svg`, `src/app/apple-icon.png`.
- Do not touch: see "Out of scope". Never commit `.env` or `frontend/.env.local` (both are gitignored).

## Contract
All of it exists; nothing new on the backend.
- **`GET /me`** → `Me`; **`PATCH /me`** with body `Study` → `Me`. Types from the generated
  `src/lib/api/schema.d.ts` (`Me` is exported from `@/lib/api/client`):
  ```json
  // Me (GET /me for student01)
  {"id": "<uuid>", "nickname": "student01", "role": "student",
   "study": {"program_id": "65669424", "year": 1, "semester": "ZS"}}
  // Me for a teacher
  {"id": "<uuid>", "nickname": "vyucujuci01", "role": "vyucujuci", "study": null}
  // PATCH /me body (Study)
  {"program_id": "65669424", "year": 3, "semester": "ZS"}
  ```
  Errors: 401 not logged in / token invalid; 403 the account has no profile; 422 unknown program, or a year beyond the
  program's length, or an invalid body.
- **`useMe()`** → `Me | null` (client components). Do not call `GET /me` yourself.
- **`signIn`** (`(state, formData) → {error, email} | null`, redirects to `/chat` on success) and **`signOut`**
  (form action, redirects to `/chat`) from `@/lib/auth/actions` — use as they are. Form field names: `email`,
  `password`. Error keys: `auth.errors.invalid | failed | unavailable`.
- **`authConfigured`** from `@/lib/supabase/config` — false when the Supabase variables are missing: hide every
  login-related element then.
- **Env (exist):** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- **`localStorage` key `hip.myCourses`** — unchanged, logged-out visitors only.
- **New, you define:** `src/lib/demo-accounts.ts` (shape up to you, show it in the report), translation keys.

## Done when
- [ ] `/login` at 1440×900 and 390 px: card, logo, "demo režim" box with the dropdown; choosing `student04 — 2. roč.`
      fills e-mail and password, "Prihlásiť sa" logs in and opens `/chat`.
- [ ] Wrong password → the translated error, the e-mail stays filled; inputs 16px text, inputs / select / button
      ≥ 44px high.
- [ ] Logged in as `student04`: sidebar bottom row shows avatar `S04`, "student04", "Študent", SK | EN; the top bar
      shows the avatar; its menu shows nickname, role and "Odhlásiť sa"; log-out returns to `/chat` logged out.
- [ ] Logged in as `vyucujuci01`: avatar `V01`, role "Vyučujúci"; "Moje predmety" shows the invitation.
- [ ] Logged in as `student04`: "Moje predmety" shows "Hospodárska informatika (Bc.) · 2. roč., zimný semester"
      and its cards without opening any dialog. "Zmeniť" → 3. ročník → "Uložiť": the cards change, and after a page
      reload (and in another browser logged in as the same account) the choice is still 3. ročník — it is in the
      profile. Then set it back to 2. ročník, ZS (see Notes).
- [ ] Logged out: "Moje predmety" still works from `localStorage` as before; logging in does not copy that choice
      into the profile.
- [ ] Saving with the backend stopped → a translated error in the dialog, no crash.
- [ ] Phone 390 px: drawer close "×", SK | EN, avatar button, menu items, "Prihlásiť sa" — all ≥ 44×44px; no
      horizontal scroll on `/login` and `/chat` (logged in / out, dialog open, menu open).
- [ ] The tab shows the icon; no 404 for the icon in the browser console.
- [ ] SK | EN: every new text switches language; no hard-coded UI text.
- [ ] Without `frontend/.env.local` the app still builds and runs, with no login elements.
- [ ] `npm run gen:api` gives no diff, `npm run lint`, `npm run typecheck`, `npm run build` pass; CI on the PR is green.

## How to verify
```
# terminal 1 — backend with the env file (see Before you start)
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
With Playwright, at **1440×900** and at **390 px** (use a phone device profile, e.g. "iPhone 13": it also emulates
touch and a mobile user agent), take screenshots of: `/login` empty; `/login` with `student04` chosen in the
dropdown; `/login` with the wrong-password error; `/chat` logged in as `student04` (sidebar, or drawer open on the
phone); the open avatar menu; the "Zmeniť" dialog; `/chat` logged in as `vyucujuci01`; `/chat` logged out; `/login`
in English. Save them in `tasks/T-004-login-and-profile-ui/screens/` and link them from the report.

Also measure with Playwright and list in the report: the height of every button / link / input on `/login` and in
the drawer at 390 px, the font size of the inputs, and `document.documentElement.scrollWidth <= innerWidth` for each
screenshot.

In the report also list: the shape of `demo-accounts.ts`, the shadcn components you added, the profile changes you
made in the shared database while testing and that you set them back, and every deviation from this brief with the
reason.

## Notes
- **The database is shared** (development and the demo): `PATCH /me` changes the real profile of a test account.
  Test "Zmeniť" with `student04` only, and at the end set it back to Hospodárska informatika (Bc.), 2. ročník,
  zimný semester. Do not change other accounts' profiles.
- Never paste `DATABASE_URL` or any key into the report, a screenshot or a commit; the publishable key and the
  project URL are public values but still stay out of the repo (they live in `.env.local`).
- If a real iPhone is at hand, a quick check on it is welcome (`npm run dev -- -H 0.0.0.0` does not help on its own:
  CORS and the cookies are set up for `localhost`) — otherwise it is checked after deployment; Playwright's device
  profile is enough for this task.
- Use Context7 for Next.js (file conventions for icons, `router.refresh`) and the shadcn MCP for the dropdown menu —
  do not rely on memory.
- If something in this brief contradicts the code or the design, do not guess: add a report round with
  `Status: blocked` and your questions.
- Branch `mp/login-ui`; commit messages like `ui: account menu (T-004)`; PR title
  `T-004: Login screen, user in the layout, Moje predmety from the profile`. Open the PR yourself.
