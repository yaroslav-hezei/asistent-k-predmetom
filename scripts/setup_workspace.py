#!/usr/bin/env python3
"""One-time setup of your local workspace. Run from the repo root:

    python scripts/setup_workspace.py --prefix BM --name "Bohdan Muzhyla" --lang uk

Creates (never overwrites, safe to run again):
    tasks/      git worktree of the branch `tasks` (your tasks, reports, reviews)
    me.md       your name, prefix and language for the agent
    CLAUDE.md   for Claude Code: loads AGENTS.md and me.md
    .env        local secrets (empty)
    scratch/    throwaway experiments

All of them are gitignored. Only the Python standard library and git are required.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_BRANCH = "tasks"
PREFIX_RE = re.compile(r"^[A-Z]{2,4}$")

ME_TEMPLATE = """# me.md — personal settings (gitignored, never commit)

name: {name}
prefix: {prefix}
language: {lang}   # language the agent uses when talking to me; files stay in English

style:
- Be direct and point out weak spots.
- Explain the code I will have to defend, in simple terms.
"""

CLAUDE_TEMPLATE = """@AGENTS.md
@me.md
"""


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    print("$ git " + " ".join(args))
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, encoding="utf-8", capture_output=True)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if check and result.returncode != 0:
        print(result.stderr.rstrip(), file=sys.stderr)
        sys.exit(f"\nFAILED: git {' '.join(args)}")
    return result


def quiet_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, encoding="utf-8", capture_output=True)


def write_new(path: Path, text: str) -> None:
    if path.exists():
        print(f"{path.name} already exists — keeping it")
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"created {path.name}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prefix", required=True, help="your 2–4 letter prefix, e.g. BM")
    p.add_argument("--name", required=True, help='your name, e.g. "Bohdan Muzhyla"')
    p.add_argument("--lang", default="en", help="language the agent talks to you in (default: en)")
    a = p.parse_args()

    prefix = a.prefix.upper()
    if not PREFIX_RE.match(prefix):
        sys.exit("prefix must be 2–4 capital letters, e.g. BM")

    if not (ROOT / ".git").exists():
        sys.exit(f"{ROOT} is not the root of a git clone — clone the repo first (see CONTRIBUTING.md)")
    for key in ("user.name", "user.email"):
        if not quiet_git("config", key).stdout.strip():
            sys.exit(f'git {key} is not set. Run: git config --global {key} "..."')

    # tasks/ — worktree of the branch `tasks`
    tasks = ROOT / "tasks"
    if tasks.exists():
        print("tasks/ already exists — keeping it")
    else:
        git("fetch", "origin", TASKS_BRANCH)
        if quiet_git("rev-parse", "--verify", "--quiet", f"refs/heads/{TASKS_BRANCH}").returncode == 0:
            git("worktree", "add", "tasks", TASKS_BRANCH)
        else:
            git("worktree", "add", "--track", "-b", TASKS_BRANCH, "tasks", f"origin/{TASKS_BRANCH}")

    write_new(ROOT / "me.md", ME_TEMPLATE.format(name=a.name, prefix=prefix, lang=a.lang))
    write_new(ROOT / "CLAUDE.md", CLAUDE_TEMPLATE)
    env = ROOT / ".env"
    if not env.exists() and (ROOT / ".env.example").exists():
        shutil.copyfile(ROOT / ".env.example", env)
        print("created .env from .env.example")
    else:
        write_new(env, "# secrets go here; never commit this file\n")
    (ROOT / "scratch").mkdir(exist_ok=True)

    # make sure personal files are really ignored
    for f in ("me.md", "CLAUDE.md", ".env", "tasks/", "scratch/"):
        if quiet_git("check-ignore", "-q", f).returncode != 0:
            print(f"WARNING: {f} is NOT ignored by git — tell Yaroslav", file=sys.stderr)

    if shutil.which("node") is None:
        print("WARNING: Node.js not found — needed for the frontend and the MCP servers", file=sys.stderr)

    print(
        "\nDone.\n"
        "Next:\n"
        "  1. Install the MCP servers (CONTRIBUTING.md → Agent tools).\n"
        "  2. Open your agent in this folder and say: \"Check my tasks.\"\n"
    )


if __name__ == "__main__":
    main()
