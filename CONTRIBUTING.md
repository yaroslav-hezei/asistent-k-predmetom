# Contributing — team setup

## How the workspace looks

```
code/                     ← clone of this repo: main + your topic branches
├── AGENTS.md             ← rules for coding agents
├── tasks/                ← branch `tasks`: your tasks, your reports, reviews (gitignored in main)
├── me.md                 ← your name, prefix, language (gitignored)
├── CLAUDE.md             ← only for Claude Code: loads AGENTS.md + me.md (gitignored)
├── .env                  ← secrets (gitignored)
└── scratch/              ← throwaway experiments (gitignored)
```

The repo is public, including the `tasks` branch: never put secrets or personal data into any file.

## Prerequisites

- git, Python 3.10+, Node.js (LTS) — Node is needed for the frontend and for the MCP servers below.
- A GitHub account with access to the repo: Yaroslav sends an invitation, accept it (e-mail or github.com/notifications).
- Your git identity:
  ```
  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"
  ```

## Join (once)

```
git clone https://github.com/yaroslav-hezei/asistent-k-predmetom.git code
cd code
python scripts/setup_workspace.py --prefix BM --name "Bohdan Muzhyla" --lang uk
```

Use your own prefix (`BM`, `MP`), name and the language your agent should talk to you in
(`uk`, `sk`, `en`, …). On Windows use `py` instead of `python` if needed.
The script creates `tasks/`, `me.md`, `CLAUDE.md`, `.env` and `scratch/`. It never overwrites existing files
and can be run again safely.

## Agent tools (MCP servers)

Install them **globally** (user-level), never as a config file inside the repo.

| Server | Why |
|---|---|
| Playwright | the agent opens the app in a real browser, takes screenshots, compares them with `docs/design/screens/`, checks desktop and mobile |
| shadcn | the agent uses current shadcn/ui components and their real APIs instead of outdated memory |
| Context7 | up-to-date docs for Next.js, FastAPI, Supabase, Tailwind |

**Claude Code** (stored in your personal settings, not in the repo):
```
claude mcp add playwright -- npx @playwright/mcp@latest
claude mcp add shadcn -- npx shadcn@latest mcp
claude mcp add context7 -- npx -y @upstash/context7-mcp
claude mcp list
```

**Codex** (writes to `~/.codex/config.toml`):
```
codex mcp add playwright -- npx @playwright/mcp@latest
codex mcp add shadcn -- npx shadcn@latest mcp
codex mcp add context7 -- npx -y @upstash/context7-mcp
codex mcp list
```

Do not use `shadcn mcp init --client …`: it writes a config file into the project folder.
If Playwright reports a missing browser, run `npx playwright install chromium` once.
On Windows, if a server does not start in Codex, use `cmd` as the command:
`command = "cmd"`, `args = ["/c", "npx", "@playwright/mcp@latest"]`.

Use Codex **locally** (CLI, IDE extension or app). Codex cloud tasks and `@codex` on GitHub do not see
your `me.md` or the `tasks/` folder.

## Every session

1. Open your agent in `code/`. Claude Code reads `CLAUDE.md` (→ `AGENTS.md` + `me.md`); Codex reads `AGENTS.md`.
2. First message: **"Check my tasks."** The agent pulls `tasks/`, finds your open task and briefs you.
3. Work in small steps: plan → your "yes" → build → the agent shows how it verified the result.
4. Open a pull request into `main` (title `T-NNN: …`), then the agent writes and pushes the report.
5. Tell Yaroslav in the chat that the report is pushed. The review comes back as `review.md` in the task folder.

## How tasks work (short)

```
tasks/T-007-chat-screen/
├── task.md      ← the brief: goal, context, what to do, done when, how to verify (written by Yaroslav)
├── report.md    ← your report, one round per review round (written by you / your agent)
└── review.md    ← the review: accepted or what to fix (written by Yaroslav)
```

Details: `tasks/README.md`.

## Useful commands (from `code/`)

```
git -C tasks pull --no-rebase        # get new tasks and reviews
git -C tasks log --oneline -5        # what changed recently
git switch main && git pull          # fresh main before a new branch
```

## Branches and pull requests

- Branch per task: `<your prefix in lowercase>/<topic>`, e.g. `bm/chat-screen`.
- Small pull requests into `main`; Yaroslav reviews and merges. Nobody can push to `main` directly.
- Commit messages reference the task: `ui: source card (T-007)`.
