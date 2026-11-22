# Review — T-004

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-22
Verdict: accepted

No report round was pushed to `tasks`, so this review is done from the code: branch `mp/login-ui` at `0cdebf5`.
PR #12 was opened by the reviewer so that CI runs.

Checked:
- The diff is 14 files, all under `frontend/` and all in the brief's file list (plus two small components,
  `account-marks.tsx` and `account-menu.tsx`). Nothing changed in `src/lib/supabase/`, `src/proxy.ts`,
  `src/lib/auth/`, `src/lib/api/`, `me-provider.tsx`, `backend/`, `supabase/`, `data/`, `scripts/`, `docs/` or the
  workflows.
- `npm ci`, `npm run gen:api` + `git diff --exit-code src/lib/api/schema.d.ts` (no diff), `npm run lint`,
  `npm run typecheck`, `npm run build` → all pass. CI `Frontend / check` on PR #12 → pass.
- `src/lib/demo-accounts.ts` against `backend/scripts/test_users.json` (compared by a script): the same 13 accounts
  (e-mail, nickname, role, year) and both passwords.
- Playwright against the production build and the local backend (shared database), at 1440×900 and with the
  "iPhone 13" profile (390 px): 86 checks, all of them pass. In short:
  - `/login`: card, logo, "Demo režim" box; the dropdown has 13 accounts (`student04 — 2. roč.`,
    `vyucujuci01 — vyučujúci`); choosing `student04` fills the e-mail and the password; "Prihlásiť sa" logs in and
    opens `/chat`. Wrong password → "Nesprávny e-mail alebo heslo.", the e-mail stays filled. The select, the inputs
    and the button are 44px high with 16px text (desktop and phone).
  - `student04`: sidebar row "S04 · student04 · Študent" next to SK | EN, top-bar avatar "S04"; the menu shows
    nickname, role and "Odhlásiť sa"; it opens with Enter and closes with Escape; log-out returns to `/chat` logged
    out.
  - "Moje predmety" from the profile without any dialog: "Hospodárska informatika (Bc.) · 2. roč., zimný semester",
    9 cards. "Zmeniť" → 3. ročník → "Uložiť": the cards change at once (8 cards); after a reload, and in a second
    browser logged in as `student04`, it is still 3. ročník. Then set back to 2. ročník, zimný semester, and
    checked after a reload. No `localStorage` is written while logged in.
  - Save errors, simulated in the browser: connection refused (= backend stopped) → "Výber štúdia sa nepodarilo
    uložiť. Skús to znova."; HTTP 422 → "Vybraný študijný program alebo ročník nie je platný."; the dialog stays
    open in both cases.
  - Logged out: the choice is saved in `localStorage` `hip.myCourses`; logging in as `student04` shows the profile
    (2. ročník), not the guest choice, and leaves `localStorage` as it was; after log-out the guest choice is back.
  - `vyucujuci01`: avatar "V01", "Vyučujúci", the "Moje predmety" invitation.
  - Phone: the drawer's close button, SK, EN, every navigation link, the avatar button, "Prihlásiť sa" and the menu
    item are all at least 44×44px; no horizontal scroll on `/login` or `/chat` (logged in and out, drawer, menu and
    dialog open); the menu and the dialog fit on the screen.
  - Tab icon: `<link rel="icon">` → `icon.svg`, `apple-touch-icon` present, `apple-icon.png` is 180×180; no 404
    and no console errors (apart from the two simulated save failures).
  - English: every new text on `/login` switches ("Demo mode", "Choose a test account", "Year 2", "teacher").
- Built and started without `frontend/.env.local`: the build passes, no login element anywhere, `/login`
  redirects to `/chat`, no page errors.
- Translations: 66 keys in both `sk.json` and `en.json`; no hard-coded UI text.
- The commit message follows the rules; no agent attribution.

Fix:
None for you. Notes for next time:
1. The report is part of the task (`AGENTS.md` §2). This time there was none, so nothing told the reviewer what
   you checked, what you changed in the shared database or what you decided differently from the brief — all of it
   had to be found again from the code. Next time push `report.md` (with the screenshots in `screens/`) and open
   the PR yourself, as the brief says.
2. `src/components/login-form.tsx` and `src/components/app-shell.tsx` lost two comments that explained *why* the
   code is the way it is: "16px text: iPhone Safari zooms into any input with a smaller font. 44px high: easy to
   tap." and the one-line description of `Account`. Keep comments like these when you change the code around them —
   without them the next person may "simplify" the 16px away. YH restores them in a follow-up PR.
3. Not your mistake, a gap in the brief: on `/login` a logged-out visitor sees "Prihlásiť sa" three times — the
   top-bar link, the sidebar link (both lead to the page they are already on) and the form button. YH hides the
   top-bar link on `/login` in the same follow-up PR.

Answers:
- none
