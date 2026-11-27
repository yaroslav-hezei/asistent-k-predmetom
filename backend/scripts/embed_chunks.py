"""Give every knowledge-base chunk its vector (the re-embed script).

    python scripts/embed_chunks.py               # all chunks without a vector of the current model
    python scripts/embed_chunks.py --limit 500   # at most 500 chunks in this run
    python scripts/embed_chunks.py --dry-run     # only count the chunks without a vector

Run from `backend/` after `scripts/sync_sheet_chunks.py`. Needs DATABASE_URL and GEMINI_API_KEY
(environment or the repo's `.env`). The model is `app.llm.EMBED_MODEL`; chunks with no vector,
another model's vector, or a vector cleared after a text change are embedded. Every batch is
committed on its own: when a quota is reached the run stops with an error and the next run
continues where it stopped. Rate-limit answers (429) are retried with a growing pause.
"""

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app import llm  # noqa: E402
from app.config import REPO_ROOT  # noqa: E402
from app.knowledge import count_pending, embed_pending_chunks  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=None, help="at most this many chunks")
    parser.add_argument("--dry-run", action="store_true", help="only count, send nothing")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not database_url or (not api_key and not args.dry_run):
        print("DATABASE_URL and GEMINI_API_KEY must be set (environment or .env in the repo root)")
        return 1

    model = llm.EMBED_MODEL
    with psycopg.connect(database_url, connect_timeout=10, autocommit=True) as conn:
        pending = count_pending(conn, model)
        print(f"model {model}: {pending} chunks without its vector")
        if args.dry_run or pending == 0:
            return 0
        client = llm.make_client(api_key)
        target = pending if args.limit is None else min(pending, args.limit)
        stored = embed_pending_chunks(
            conn,
            lambda documents: llm.embed_documents(client, model, documents),
            model,
            limit=args.limit,
            on_batch=lambda done: print(f"  {done} / {target}", flush=True),
        )
        print(f"stored {stored} vectors; without a vector of {model}: {count_pending(conn, model)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
