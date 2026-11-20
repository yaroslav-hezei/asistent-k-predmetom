"""Load the course catalogue from the MAIS snapshot into the database.

    python scripts/import_catalog.py                      # data/mais/2026-27
    python scripts/import_catalog.py --data-dir <folder>

Run from `backend/` after the migrations are applied. DATABASE_URL comes from the environment or
from the repo's `.env`. Safe to run again: programs and courses are upserted and the study plans
are replaced in one transaction. Programs and courses are never deleted, and nothing users wrote
is touched.

The rows are built by `app.catalog.Catalog`, the same code that serves the catalogue API, so the
database and the API always agree.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.catalog import Catalog  # noqa: E402
from app.config import DEFAULT_MAIS_DATA_DIR, REPO_ROOT  # noqa: E402

UPSERT_PROGRAM = """
insert into public.programs (id, code, name, degree, language, method, years, academic_year)
values (%(id)s, %(code)s, %(name)s, %(degree)s, %(language)s, %(method)s, %(years)s,
        %(academic_year)s)
on conflict (id) do update set
    code = excluded.code, name = excluded.name, degree = excluded.degree,
    language = excluded.language, method = excluded.method, years = excluded.years,
    academic_year = excluded.academic_year
"""

UPSERT_COURSE = """
insert into public.courses
    (id, code, name, credits, semesters, academic_year, source_url, sheet_changed_on, fetched_at)
values (%(id)s, %(code)s, %(name)s, %(credits)s, %(semesters)s, %(academic_year)s,
        %(source_url)s, %(sheet_changed_on)s, %(fetched_at)s)
on conflict (id) do update set
    code = excluded.code, name = excluded.name, credits = excluded.credits,
    semesters = excluded.semesters, academic_year = excluded.academic_year,
    source_url = excluded.source_url, sheet_changed_on = excluded.sheet_changed_on,
    fetched_at = excluded.fetched_at
"""

INSERT_PLAN_ROW = """
insert into public.program_courses (program_id, course_id, year, semester, type, state_exam)
values (%(program_id)s, %(course_id)s, %(year)s, %(semester)s, %(type)s, %(state_exam)s)
"""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_rows(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Rows for programs, courses and program_courses, built from the snapshot."""
    catalog = Catalog.load(data_dir)

    academic_years = {
        raw["program_id"]: {item["label"]: item["text"] for item in raw["header"]}["Akademický rok"]
        for raw in read_json(data_dir / "programs.json")
    }
    programs = [
        {**program.model_dump(), "academic_year": academic_years[program.id]}
        for program in catalog.list_programs()
    ]

    courses = []
    for course in catalog.search_courses():
        sheet = read_json(data_dir / "courses" / f"{course.id}.json")
        last_changed = sheet["fields"].get("last_changed")
        courses.append(
            {
                **course.model_dump(),
                "academic_year": sheet["academic_year"],
                "source_url": sheet["source_url"],
                "sheet_changed_on": date.fromisoformat(last_changed) if last_changed else None,
                "fetched_at": datetime.fromisoformat(sheet["fetched_at"].replace("Z", "+00:00")),
            }
        )

    plan = [
        {
            "program_id": program["id"],
            "course_id": item.course.id,
            "year": item.year,
            "semester": item.semester,
            "type": item.type,
            "state_exam": item.state_exam,
        }
        for program in programs
        for item in catalog.program_courses(program["id"]) or []
    ]
    return {"programs": programs, "courses": courses, "program_courses": plan}


def import_catalog(conn: psycopg.Connection, data_dir: Path) -> dict[str, int]:
    """Write the snapshot into the database in one transaction; return the row counts written."""
    rows = build_rows(data_dir)
    program_ids = [program["id"] for program in rows["programs"]]
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(UPSERT_PROGRAM, rows["programs"])
        cur.executemany(UPSERT_COURSE, rows["courses"])
        cur.execute("delete from public.program_courses where program_id = any(%s)", [program_ids])
        cur.executemany(INSERT_PLAN_ROW, rows["program_courses"])
    return {table: len(table_rows) for table, table_rows in rows.items()}


def count_rows(conn: psycopg.Connection) -> dict[str, int]:
    return {
        table: conn.execute(f"select count(*) from public.{table}").fetchone()[0]
        for table in ("programs", "courses", "program_courses")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_MAIS_DATA_DIR)
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set (environment or .env in the repo root)")
        return 1

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        written = import_catalog(conn, args.data_dir)
        in_db = count_rows(conn)
    for table, count in written.items():
        print(f"{table}: wrote {count}, in the database {in_db[table]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
