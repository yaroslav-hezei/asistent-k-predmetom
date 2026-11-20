"""Database: the migrations, the catalogue import and the app's connection pool.

These tests need TEST_DATABASE_URL: a throwaway local Postgres with the migrations applied
(`npx supabase@3.2.0 db start` from the repo root, see backend/README.md). Never point it at the
shared cloud database: the import rewrites the catalogue tables. Without the variable the tests are
skipped locally; in CI it is required.
"""

import os
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_MAIS_DATA_DIR, Settings
from app.main import create_app
from scripts.import_catalog import count_rows, import_catalog

HI_BC = "65669424"
ZAP = "65954478"
HIP = "69574272"

TABLES = {
    "programs",
    "courses",
    "program_courses",
    "profiles",
    "teacher_courses",
    "chats",
    "chat_messages",
    "questions",
    "answers",
    "answer_thanks",
    "course_notes",
    "notifications",
    "knowledge_chunks",
}


@pytest.fixture(scope="module")
def db_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI")
        pytest.skip("TEST_DATABASE_URL is not set")
    return url


@pytest.fixture(scope="module")
def conn(db_url):
    with psycopg.connect(db_url, autocommit=True) as connection:
        yield connection


def test_every_table_is_closed_to_the_data_api(conn):
    """RLS on, no privileges for anon / authenticated: the public key reads and writes nothing."""
    rows = conn.execute(
        """
        select c.relname,
               c.relrowsecurity,
               has_table_privilege('anon', c.oid, 'select, insert, update, delete'),
               has_table_privilege('authenticated', c.oid, 'select, insert, update, delete')
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind in ('r', 'p')
        """
    ).fetchall()
    assert {name for name, *_ in rows} == TABLES
    for name, rls, anon, authenticated in rows:
        assert rls, f"{name}: RLS is off"
        assert not anon, f"{name}: anon has privileges"
        assert not authenticated, f"{name}: authenticated has privileges"


def test_import_catalog_is_repeatable(conn):
    expected = {"programs": 32, "courses": 563, "program_courses": 1349}
    assert import_catalog(conn, DEFAULT_MAIS_DATA_DIR) == expected
    assert import_catalog(conn, DEFAULT_MAIS_DATA_DIR) == expected  # second run: no duplicates
    assert count_rows(conn) == expected


def test_imported_values(conn):
    assert conn.execute(
        "select code, name, credits, semesters, academic_year, sheet_changed_on, source_url"
        " from public.courses where id = %s",
        [ZAP],
    ).fetchone() == (
        "26000629",
        "Základy algoritmizácie a programovania",
        5,
        ["ZS"],
        "2026/2027",
        date(2026, 9, 1),
        f"https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId={ZAP}",
    )
    # sheets without "Dátum poslednej zmeny"
    assert conn.execute(
        "select count(*) from public.courses where sheet_changed_on is null"
    ).fetchone() == (24,)
    # a state-exam course placed by its sheet
    assert conn.execute(
        "select year, semester, type, state_exam from public.program_courses"
        " where program_id = %s and course_id = %s",
        [HI_BC, HIP],
    ).fetchall() == [(3, "ZS", "P", True)]


def test_app_opens_and_closes_the_pool(db_url):
    settings = Settings(
        mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[], database_url=db_url
    )
    with TestClient(create_app(settings)) as client:
        pool = client.app.state.db
        with pool.connection() as connection:
            assert connection.execute("select 1").fetchone() == (1,)
    assert pool.closed


def test_app_without_database_url_has_no_pool():
    settings = Settings(mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[])
    with TestClient(create_app(settings)) as client:
        assert client.app.state.db is None
        assert client.get("/courses/" + ZAP).status_code == 200
