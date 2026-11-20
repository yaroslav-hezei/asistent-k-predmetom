# Review — T-002

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-20
Verdict: accepted

Checked:
- Branch `mp/frontend-foundation` at `403e03c` (one commit), checked out locally. The diff is `frontend/` and
  `.github/workflows/frontend.yml` only; nothing changed in `backend/`, `data/`, `scripts/`, `docs/`, `AGENTS.md`,
  `CONTRIBUTING.md`.
- From `frontend/` (Node 24.16 locally; CI uses `.nvmrc` 26.13.1, the current LTS): `npm ci` → ok, 4 moderate
  advisories, all in `minimatch` under `@ts-morph/common` (a dependency of the shadcn CLI, not shipped to the browser);
  `npm run gen:api` → `schema.d.ts` unchanged; `npm run lint` → exit 0; `npm run typecheck` → exit 0;
  `npm run build` → exit 0.
- Browser checks with Playwright (Edge) against `next start` and the backend, at 1440×900 and 390×844 —
  52 checks, all passed except the two font checks (1 below):
  - `/` → `/chat`; one character sends no request; fast typing sends one request;
  - `zaklady algoritmizacie` and `26000629` find "Základy algoritmizácie a programovania"; `xyzxyz` → the
    "nothing found" message; Enter on a focused result opens `/chat/new?course=65954478` with name and code;
    an unknown or missing id → "Predmet sa nenašiel.";
  - the dialog lists 32 programs grouped Bc. 15 / Bc. PO 1 / Ing. 16; the three Bc. Informatika variants read
    "Informatika (Bc.)", "Informatika (Bc., kombinovaná)", "Informatika (Bc., EN)"; the year options follow `years`;
  - HI Bc., 3., ZS → 8 cards including "Hospodárska informatika v praxi"; `hip.myCourses` =
    `{"programId":"65669424","year":3,"semester":"ZS"}`; the choice survives a reload; a saved program that does
    not exist → the invitation; clicking a card opens its course;
  - EN: layout, picker, dialog, placeholders and the course page are translated, `<html lang="en">`, course names
    stay Slovak, no Slovak UI text left; switching back to SK works;
  - 390 px: the sidebar is a drawer that navigates and closes; no horizontal overflow in the picker, search, dialog
    and error states;
  - backend stopped: picker, search and course page show the translated error; no page errors anywhere.
- `messages/sk.json` and `messages/en.json` have the same 45 keys; no hard-coded UI text in components.
- All requests go through `src/lib/api/client.ts`, the server-side request of `/chat/new` included. No business
  logic, no Supabase.
- Layout against `01-course-picker.png`: sidebar 280 px, top bar, title, search, the "Moje predmety" line and the
  3-column grid match. The differences are the ones listed in your report, plus the font.
- `frontend/README.md` covers install, run, scripts, the env variable and type regeneration. The commit message
  follows the rules; no agent attribution.

Fix:
None for you. The two points below are small; YH fixes them in a follow-up PR, so the task does not go back and
forth. Read them anyway — they are what to watch for next time.
1. `frontend/src/app/layout.tsx:10,13,23` — the page is rendered in **Geist**, not Inter. `shadcn init` added
   `Geist` from `next/font/google`; `geist.variable` sets `--font-sans` on `<html>` and overrides
   `--font-sans: "Inter"` from `globals.css`. The `@fontsource/inter` files are loaded but not used: the computed
   `font-family` of `body` is `Geist, "Geist Fallback"`. A screenshot comparison catches this only if you look at the
   letters; when a design token matters, check the computed style in the browser (`getComputedStyle`).
   Fix: remove the Geist import and its class; Inter then comes from the theme.
2. `frontend/package.json:40` — `"engines": {"node": "26.13.1"}` pins one patch release: every other 26.x prints an
   engine warning, and the hosting platform reads `engines.node` to choose the Node version. Keep the exact version
   in `.nvmrc` (CI) and use the major range `"26.x"` in `engines`.

Accepted as reported, no change: semester names written out on the cards ("zimný semester" instead of "ZS"; it
reads well in English too), the footer hint about starting a new chat, the Lucide icons, and the parts left out on
purpose.

Answers:
- none. PR: YH opened #7 from your branch so that CI runs; CI passed (Node 26.13.1) and it is merged into `main` as `78d7774`. Nothing to do for you.
