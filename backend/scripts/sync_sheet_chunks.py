"""Put the MAIS sheets of the catalogue into the knowledge base as chunks (no embeddings yet).

    python scripts/sync_sheet_chunks.py                      # data/mais/2026-27
    python scripts/sync_sheet_chunks.py --data-dir <folder>
    python scripts/sync_sheet_chunks.py --dry-run            # count the changes, write nothing

Run from `backend/` after `scripts/import_catalog.py`. DATABASE_URL comes from the environment or
from the repo's `.env`. Safe to run again: unchanged chunks are not written and keep their
embeddings, changed ones get the new text without an embedding, chunks the sheets no longer have
are deleted. Only sheet chunks of the catalogue's courses are touched.
"""

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.catalog import Catalog  # noqa: E402
from app.chunking import Chunk, chunk_sheet  # noqa: E402
from app.config import DEFAULT_MAIS_DATA_DIR, REPO_ROOT  # noqa: E402
from app.knowledge import SyncCounts, sync_sheet_chunks  # noqa: E402


def build_chunks(data_dir: Path) -> dict[str, list[Chunk]]:
    """The chunks of every catalogue course's sheet, by course id."""
    catalog = Catalog.load(data_dir)
    chunks = {}
    for course in catalog.search_courses():
        sheet = catalog.get_sheet(course.id)
        if sheet is None:  # every catalogue course has a sheet; the loader guarantees it
            raise ValueError(f"course {course.id} has no sheet")
        chunks[course.id] = chunk_sheet(sheet)
    return chunks


def missing_courses(conn: psycopg.Connection, course_ids: list[str]) -> list[str]:
    found = {
        row[0]
        for row in conn.execute(
            "select id from public.courses where id = any(%s)", [course_ids]
        ).fetchall()
    }
    return sorted(set(course_ids) - found)


def count_sheet_chunks(conn: psycopg.Connection) -> int:
    return conn.execute(
        "select count(*) from public.knowledge_chunks where source_type = 'sheet'"
    ).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_MAIS_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="count the changes, write nothing")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (environment or .env in the repo root)")
        return 1

    chunks = build_chunks(args.data_dir)
    print(f"{len(chunks)} courses, {sum(map(len, chunks.values()))} chunks from the sheets")
    with psycopg.connect(database_url, connect_timeout=10) as conn:
        missing = missing_courses(conn, list(chunks))
        if missing:
            print(f"{len(missing)} courses are not in the database: run scripts/import_catalog.py")
            return 1
        counts = SyncCounts(0, 0, 0, 0)
        with conn.transaction():
            counts = sync_sheet_chunks(conn, chunks)
            if args.dry_run:
                raise psycopg.Rollback()
        in_db = count_sheet_chunks(conn)
    prefix = "dry run, nothing written — would be " if args.dry_run else ""
    print(
        f"{prefix}inserted {counts.inserted}, updated {counts.updated},"
        f" deleted {counts.deleted}, unchanged {counts.unchanged};"
        f" sheet chunks in the database: {in_db}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
