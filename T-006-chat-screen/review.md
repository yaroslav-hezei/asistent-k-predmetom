# Review — T-006

<!-- Append-only. One round per report round. -->

## Round 1 · 2026-11-28
Verdict: accepted

This round answers report rounds 1–4 (rounds 1–3 were blocked on the local environment and were resolved before
round 4). Reviewed: PR #23 at `d660e60` (`ui: chat screen (T-006)` + the merge of `main` into the branch).

Checked:
- The diff against `main` is 17 files, all under `frontend/` and all in the brief's file list (plus
  `chat-notice.tsx`, `course-title.tsx` and `src/lib/chat-history.ts`). Nothing changed in `backend/`, `supabase/`,
  `data/`, `scripts/`, `docs/`, the workflows, `src/lib/supabase/`, `src/proxy.ts`, `src/lib/auth/` or
  `me-provider.tsx`; `src/lib/api/client.ts` only got the three type aliases. No new dependencies.
- The merge of `main` keeps everything of PR #19–#22: the merged `messages/sk.json` and `en.json` are exactly
  `main` plus your `chat`, `layout.history` and `picker.recentCourses` (compared by a script).
- `npm run gen:api` (no diff), `npm run lint`, `npm run typecheck`, `npm run build` → pass. CI on PR #23 → pass.
- No agent attribution in the commits; no secrets.
- Playwright against the production build, the local backend and the shared database, logged in as `student05`
  (1440×900 and 390 px), with the real assistant (Gemini), not the placeholder:
  - ZAP from "Naposledy použité" → `/chat/new` → "Ako sa hodnotí tento predmet?" → the answer with [1] [2] [3] and
    three cards "Informačný list predmetu · MAIS", "stav k 17. 11. 2026", "Oficiálny dokument", exact quotes, the
    MAIS link (`…tlacPredmetuOSP.mais?predmetId=65954478`); the URL becomes `/chat/<id>`; the new chat is first in
    "História".
  - Chip [1] → source 1 highlighted.
  - "Neviem, kedy je skúška?" → "Neviem." + "Opýtaj sa ostatných" with both buttons disabled and the "čoskoro" line.
  - Reload → 4 messages, the chat highlighted at the top of "História"; console clean.
  - Mocked `/ask` (test data only): an unverified student answer with the explanation line, a teacher's verified
    answer, a `course_note`, an outdated sheet with the warning, chips [1]–[4], `[9]` without a source left as text,
    a long quote collapsed with "Zobraziť celý text". Aborted `/ask` → "Otázku sa nepodarilo odoslať…", the question
    stays in the composer.
  - Composer: disabled below 3 characters, Shift+Enter makes a new line, Enter sends, 16 px text, send button
    44 × 44 px.
  - 390 px: `scrollWidth` 390 = `innerWidth`, the composer visible. EN: the chat texts switch.
  - Random uuid → "Chat sa nenašiel." with the link back. Logged out: `/chat/<id>` and `/chat/new?course=…` → the
    login prompt, no "História".

Fix:
1. `frontend/src/components/chat/source-card.tsx:20–23` — the date of an `answer` source is formatted without a
   time zone, so the server (UTC on Vercel) and the browser (Europe/Bratislava) write different hours and React
   throws hydration error #418 when a chat with a community answer is opened. Reproduced by running the frontend
   with `TZ=UTC`. **We fix it ourselves** in our next PR (format with `timeZone: "Europe/Bratislava"`, as the
   sheet date already does); nothing to do for you.
2. Next time fill in the PR description from the template (what changed, how it was verified) — PR #23 has the
   empty template. The report covered it this time.

Answers:
- Rounds 1 and 3 (installing the backend dependencies, starting the frontend from a normal terminal): resolved by
  you in round 4 — nothing open.
- The Node version: CI uses `.nvmrc` (26); Node 22 locally is fine for this code.
