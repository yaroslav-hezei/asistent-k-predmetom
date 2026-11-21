"""Create the test accounts in Supabase Auth and their profiles.

    python scripts/create_test_users.py

Run from `backend/` after the migrations and the catalogue import. Needs DATABASE_URL, SUPABASE_URL
and SUPABASE_SECRET_KEY (environment or the repo's `.env`). The secret key is for this script only;
the running backend never needs it.

The accounts and their demo passwords are listed in `scripts/test_users.json`. The login screen
shows the passwords ("demo režim"), so they are not secrets. Safe to run again: an existing
account is kept as it is (its password too); its profile and teacher courses are reset to the
list. Every profile is marked `testovacie = true`.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.config import REPO_ROOT  # noqa: E402

ACCOUNTS_FILE = Path(__file__).with_name("test_users.json")
HTTP_TIMEOUT_S = 15

UPSERT_PROFILE = """
insert into public.profiles (id, nickname, role, program_id, year, semester, testovacie)
values (%(id)s, %(nickname)s, %(role)s, %(program_id)s, %(year)s, %(semester)s, true)
on conflict (id) do update set
    nickname = excluded.nickname, role = excluded.role, program_id = excluded.program_id,
    year = excluded.year, semester = excluded.semester, testovacie = true
"""


def load_accounts(path: Path = ACCOUNTS_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_user_id(conn: psycopg.Connection, email: str) -> str | None:
    row = conn.execute(
        "select id::text from auth.users where lower(email) = lower(%s)", [email]
    ).fetchone()
    return row[0] if row else None


def create_auth_user(supabase_url: str, secret_key: str, email: str, password: str) -> str:
    """Create a confirmed email + password account through the Auth admin API; return its id."""
    request = urllib.request.Request(
        supabase_url.rstrip("/") + "/auth/v1/admin/users",
        data=json.dumps({"email": email, "password": password, "email_confirm": True}).encode(),
        headers={"apikey": secret_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
            return json.loads(response.read())["id"]
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")[:300]
        raise RuntimeError(f"creating {email} failed: HTTP {error.code} {body}") from None


def program_course_ids(conn: psycopg.Connection, program_id: str) -> list[str]:
    rows = conn.execute(
        "select distinct course_id from public.program_courses where program_id = %s order by 1",
        [program_id],
    ).fetchall()
    if not rows:
        raise RuntimeError(f"program {program_id} has no courses: import the catalogue first")
    return [row[0] for row in rows]


def save_profile(conn: psycopg.Connection, user_id: str, account: dict[str, Any]) -> int:
    """Upsert the profile and replace the teacher's courses; return the number of courses."""
    study = account.get("study") or {}
    conn.execute(
        UPSERT_PROFILE,
        {
            "id": user_id,
            "nickname": account["nickname"],
            "role": account["role"],
            "program_id": study.get("program_id"),
            "year": study.get("year"),
            "semester": study.get("semester"),
        },
    )
    conn.execute("delete from public.teacher_courses where teacher_id = %s", [user_id])
    courses = []
    if account.get("courses_of_program"):
        courses = program_course_ids(conn, account["courses_of_program"])
        with conn.cursor() as cur:
            cur.executemany(
                "insert into public.teacher_courses (teacher_id, course_id) values (%s, %s)",
                [(user_id, course_id) for course_id in courses],
            )
    return len(courses)


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    names = ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SECRET_KEY")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        print("missing (environment or .env in the repo root):", ", ".join(missing))
        return 1
    database_url, supabase_url, secret_key = (os.environ[name] for name in names)

    data = load_accounts()
    created = existing = 0
    # autocommit: each account's profile is committed on its own (`conn.transaction()` below)
    with psycopg.connect(database_url, connect_timeout=10, autocommit=True) as conn:
        for account in data["accounts"]:
            user_id = find_user_id(conn, account["email"])
            if user_id is None:
                password = data["passwords"][account["role"]]
                user_id = create_auth_user(supabase_url, secret_key, account["email"], password)
                created += 1
            else:
                existing += 1
            with conn.transaction():
                courses = save_profile(conn, user_id, account)
            print(f"{account['email']}: {account['role']}, {courses} teacher courses")
        profiles = conn.execute(
            "select role, count(*) from public.profiles where testovacie group by role order by 1"
        ).fetchall()
        teacher_rows = conn.execute("select count(*) from public.teacher_courses").fetchone()[0]
    print(f"accounts: created {created}, already existed {existing}")
    print("test profiles in the database:", dict(profiles), "| teacher_courses rows:", teacher_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
