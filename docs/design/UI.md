# UI reference

The hi-fi prototype in this folder is the **visual spec** for the frontend. It was tested with 5 students
on 2026-11-12. It is static HTML/CSS — re-implement the look with Next.js + Tailwind + shadcn/ui;
do not copy its markup into the app.

## Files

| File | What |
|---|---|
| `prototype-hifi.html` | all 7 screens in one page; each screen is a `.frame` of 1440×900 |
| `screens/01-course-picker.png` … `screens/07-teacher-verification.png` | screenshots of the frames, one per screen (see the Screenshot column in "Screens → routes"); the reference for Playwright comparisons |

All texts in the prototype are illustrative. The answer text on screen 2 is a placeholder,
not the real HIP information sheet.

## Changes after the prototype test — they override the prototype

1. **Exact quote.** Under an answer, show the quoted text from the information sheet (section + quote),
   not only a link to MAIS.
2. **Author is always visible** on every source and answer: MAIS (official sheet), student nickname, or teacher.
3. **Teachers do not edit student answers.** On the verification screen, replace "Opraviť" with
   "Pridať odpoveď": the teacher adds their own verified answer; the student answer stays as it was.
   Keep "Overiť" and "Zmazať" (hide spam).
4. **Explain "Neoverené"** with one short line, e.g. "Odpoveď napísal študent, vyučujúci ju zatiaľ neoveril."
   One of five testers read "Neoverené" as "wrong answer".

## Screens → routes (proposal)

| # | Screen | Route | Screenshot |
|---|---|---|---|
| 1 | New chat — course picker (search, "Moje predmety", recently used) | `/chat` | `screens/01-course-picker.png` |
| 2 | Chat — answer with source, date and outdated-sheet warning | `/chat/[chatId]` | `screens/02-answer-with-source.png` |
| 3 | Chat — "Neviem" + "Zverejniť otázku" | `/chat/[chatId]` (state of an answer) | `screens/03-neviem-publish.png` |
| 4 | Community questions — open / answered tabs, answer form | `/questions` | `screens/04-community-questions.png` |
| 5 | Chat — same question again, answered from a student answer (unverified) | `/chat/[chatId]` | `screens/05-student-answer.png` |
| 6 | Notifications — "someone answered your question" | `/notifications` | `screens/06-notifications.png` |
| 7 | Teacher — verification + "Aktuálna informácia k predmetu" | `/verification` (role `vyucujuci`) | `screens/07-teacher-verification.png` |

Shared layout (sidebar + top bar) lives in the root layout. UI texts in Slovak and English through i18n keys.

## Design tokens (from the prototype CSS)

| Token | Value | Use |
|---|---|---|
| `fei` | `#EAAA00` | primary — FEI TUKE color, Pantone 124 C |
| `fei-dark` | `#8A6400` | links, reference numbers |
| `fei-soft` | `#FDF3D6` | reference chips, "Nová" badge background |
| `on-fei` | `#1F1B0E` | text on yellow |
| `bg` | `#FAFAF8` | page background |
| `sidebar` | `#F2F2EF` | sidebar background |
| `line` / `line-strong` | `#E4E4DF` / `#D5D5CF` | borders |
| `text` / `muted` | `#1F2126` / `#6B6E75` | text |
| `warn-bg` / `warn-border` / `warn-text` | `#FDEEE6` / `#F2BFA3` / `#9A3D12` | outdated-sheet warning |
| `ok-bg` / `ok-text` | `#E3F1E4` / `#2E6B34` | "Overené" |
| `unverified-bg` / `unverified-text` | `#EEEEEA` / `#4E5058` | "Neoverené" |
| `official-bg` / `official-text` | `#E6EDF7` / `#244E8A` | "Oficiálny dokument" |

Font: Inter (400 / 500 / 600), base 15px. Layout: sidebar 280px, top bar 62px, chat column 760px,
list pages 840px. Radii: 8–10px for buttons and chips, 12–14px for cards, 16–18px for the composer and bubbles.

## Responsive

The prototype covers desktop only (1440×900). Mobile (390px) and tablet are a frontend decision:
the sidebar becomes a drawer, the chat column takes the full width. Verify both with Playwright.
