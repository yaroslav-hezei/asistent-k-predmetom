# tasks — briefs, reports, reviews

This branch is never merged into `main`. It is checked out at `code/tasks/` (`scripts/setup_workspace.py` does it).

## Layout

```
T-007-chat-screen/
├── task.md      ← the brief (Yaroslav)
├── report.md    ← the report, one round per review round (assignee / their agent)
└── review.md    ← the review, one round per report round (Yaroslav)
_templates/      ← copy from here
```

One author per file, so parallel work never conflicts. Never edit a file you are not the author of.

## Life of a task

1. Yaroslav pushes `T-NNN-<slug>/task.md` with `assignee:` and `status: open`, and tells you in the chat.
2. You (with your agent) do the work in a branch `<prefix>/<topic>` and open a PR into `main` titled `T-NNN: …`.
3. You append `## Round 1` to `report.md` (`Status: ready for review`) and push it.
   Questions before you can finish? Append a round with `Status: blocked` instead and push it.
4. Yaroslav appends the matching round to `review.md`:
   - `Verdict: accepted` → the PR gets merged, `status: done`;
   - `Verdict: changes needed` → `status: changes`, fix the listed points, then append `## Round 2` to `report.md`;
   - `Verdict: answers` → answers to a blocked round; continue.
5. A change to the brief after it was sent is added at the end of `task.md` as `## Update YYYY-MM-DD`.

`status` values in `task.md`: `open` → `changes` → `done` (or `dropped`). Only the author of `task.md` changes it.

## Commands (from `code/`)

```
git -C tasks pull --no-rebase
git -C tasks add T-NNN-<slug>/report.md
git -C tasks commit -m "report: T-NNN round N"
git -C tasks push
```

Commit messages: `task: T-NNN <title>`, `report: T-NNN round N`, `review: T-NNN round N`.
This branch is public: no secrets, no personal data.
