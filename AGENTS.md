# AGENTS.md — HIP: AI assistant for course information

Rules for every coding agent (Claude Code, Codex, …) working in this repository.
One session = one person + their agent. Setup: `CONTRIBUTING.md`.

## 0. Where things live

| What | Where |
|---|---|
| Code | this repo: `main` + topic branches |
| Tasks, reports, reviews | branch `tasks`, checked out at `tasks/` (gitignored in `main`); rules in `tasks/README.md` |
| UI reference: prototype, screenshots, design tokens, changes after the test | `docs/design/` (start with `UI.md`) |
| Personal settings: name, prefix, language | `me.md` (gitignored) |
| Secrets | `.env` (gitignored), platform secrets |
| Throwaway experiments | `scratch/` (gitignored); real code never imports from it |

The repo is public, including the `tasks` branch: never write secrets or personal data into any file.

## 1. Work comes as tasks

- Every piece of work has a task: `tasks/T-NNN-<slug>/task.md`. Do what it says — nothing more, nothing less.
- Session start:
  1. `git -C tasks pull --no-rebase`.
  2. Find the tasks whose `assignee:` is your prefix (from `me.md`) and whose `status:` is `open` or `changes`.
  3. Read `task.md`; if `review.md` exists, its latest round says what to fix.
  4. Tell your human in 3–5 lines: what the task is, how you plan to do it, what is unclear.
- Unclear, or the task contradicts the code? Do not guess. Add a report round with `Status: blocked` and your
  questions (§2), push it and tell your human.
- Never edit `task.md` or `review.md`. Never touch another person's task folder.

## 2. Report

When the work is done and verified (§5), append a round to `tasks/T-NNN-<slug>/report.md`
(template: `tasks/_templates/report.md`). The report is append-only: one new round per review round.

```
git -C tasks pull --no-rebase
git -C tasks add T-NNN-<slug>/report.md
git -C tasks commit -m "report: T-NNN round N"
git -C tasks push
```

The report must let a reviewer check your work without asking you: what you did, which files, the exact
commands you ran and their results, screenshots, every deviation from the task, open questions.

## 3. Control

- The human decides, the agent proposes.
- Ask for an explicit "yes" before:
  1. any git write: commit, push, merge, branch delete — show the exact commands and files first;
  2. changing a shared contract (DB migrations, Pydantic API models, generated TS types, env variable names)
     beyond what the task allows.
- One "yes" covers exactly what you showed. Anything extra needs a new "yes".
- Never: `git reset --hard`, force-push, rebase `main`, push directly to `main` (it is protected),
  `git clean -x`, commit secrets or `me.md`, delete files you did not create.

## 4. Language

- Talk to the human in the language from `me.md`.
- Write code, comments, commits and reports in English.
- UI text is never hardcoded: always through i18n keys, Slovak and English.

## 5. Verification and honesty

- Nothing is done until it was run. Report how: test name, command and its result, or a Playwright screenshot.
- UI work: compare with `docs/design/screens/` using Playwright at desktop 1440×900 and mobile 390 px.
  The "changes after the test" in `docs/design/UI.md` override the prototype.
- Data work: report the number of rows and one control value.
- Separate facts from guesses. Never invent API fields, DB columns, library functions or numbers.
  If unsure, check the code, the docs (Context7 / shadcn MCP) or ask in the report.

## 6. Project rules

- **Next.js is UI only.** No business logic and no direct DB access in the frontend; all data goes through FastAPI.
- **Contract = code.** Pydantic models in the backend are the source of truth → OpenAPI → generated TS types.
  Never hand-edit generated types; regenerate them.
- Sources, dates, quotes and authors in answers are filled by code from metadata. The model only cites chunk numbers.
- Every write to the knowledge base (new answer, verification, teacher info) goes through one backend function
  (embedding + cache invalidation live there).
- Never cache a "Neviem" answer.
- Generated or seeded data is marked `testovacie = true`. Seeded answers must not invent facts about real courses.
- Secrets only in `.env` / platform secrets. Never print them in logs or chat.
- Model names only in `backend/.../llm.py` (one place to switch).

## 7. Git

- Branch per task from a fresh `main`: `<prefix-lowercase>/<topic>`, e.g. `bm/chat-screen`.
- Small PRs into `main`, title `T-NNN: <title>`, description from the PR template. Yaroslav reviews and merges.
- Commit messages: `<area>: <summary> (T-NNN)`, e.g. `ui: source card (T-007)`.
- No agent attribution: commit messages and PR descriptions carry no `Co-Authored-By` trailer,
  "Generated with …" line or any other AI/agent marker.
- `tasks` branch: `pull --no-rebase` → commit → push right away; never merged into anything.

## 8. Tools (MCP)

Installed per person, globally (see `CONTRIBUTING.md`). If a tool is missing, say so instead of guessing.

- **Playwright** — open the running app, take screenshots, compare with `docs/design/screens/`,
  check mobile and desktop. Use it to verify finished UI steps, not on every small edit.
- **shadcn** — look up and add shadcn/ui components with their current API. Prefer it over memory.
- **Context7** — current docs for Next.js, FastAPI, Supabase, Tailwind before using an API you are not sure about.
