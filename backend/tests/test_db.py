"""Database: the migrations, the catalogue import, the connection pool, test accounts, /me,
the chats and the sheet chunks of the knowledge base.

These tests need TEST_DATABASE_URL: a throwaway local Postgres with the migrations applied
(`npx supabase@3.2.0 db start` from the repo root, see backend/README.md). Never point it at the
shared cloud database: the import rewrites the catalogue tables. Without the variable the tests are
skipped locally; in CI it is required.
"""

import os
import uuid
from dataclasses import replace
from datetime import date

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.chunking import Chunk
from app.config import DEFAULT_MAIS_DATA_DIR, Settings
from app.knowledge import SyncCounts, sync_sheet_chunks
from app.main import create_app
from scripts.create_test_users import find_user_id, load_accounts, save_profile
from scripts.import_catalog import count_rows, import_catalog
from scripts.sync_sheet_chunks import build_chunks, count_sheet_chunks, missing_courses
from tests.jwt_helpers import make_token, make_verifier

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


# ---------------------------------------------------------------------------------------------
# Test accounts and /me. Auth users are inserted straight into auth.users of the local database
# (the Auth API is not running there); everything after that is the real code.
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def auth_user(conn):
    """Create rows in auth.users; delete them (and, by cascade, their profiles) afterwards."""
    created = []

    def create(email):
        user_id = str(uuid.uuid4())
        conn.execute("insert into auth.users (id, email) values (%s, %s)", [user_id, email])
        created.append(user_id)
        return user_id

    yield create
    for user_id in created:
        conn.execute("delete from auth.users where id = %s", [user_id])


@pytest.fixture
def catalogue(conn):
    if count_rows(conn)["programs"] == 0:
        import_catalog(conn, DEFAULT_MAIS_DATA_DIR)


def account(role):
    """The first account of a role from scripts/test_users.json."""
    return next(a for a in load_accounts()["accounts"] if a["role"] == role)


def test_test_users_file():
    data = load_accounts()
    roles = [a["role"] for a in data["accounts"]]
    assert (roles.count("student"), roles.count("vyucujuci")) == (10, 3)
    assert len({a["email"] for a in data["accounts"]}) == 13
    assert len({a["nickname"] for a in data["accounts"]}) == 13
    assert set(data["passwords"]) == {"student", "vyucujuci"}


def test_save_profile_of_student_and_teacher(conn, catalogue, auth_user):
    student, teacher = account("student"), account("vyucujuci")
    student_id = auth_user(student["email"])
    teacher_id = auth_user(teacher["email"])
    assert find_user_id(conn, student["email"].upper()) == student_id

    with conn.transaction():
        assert save_profile(conn, student_id, student) == 0
        assert save_profile(conn, teacher_id, teacher) == 42  # all courses of HI Bc.
    with conn.transaction():  # again: no duplicates
        assert save_profile(conn, teacher_id, teacher) == 42
    assert conn.execute(
        "select nickname, role, program_id, year, semester, testovacie from public.profiles"
        " where id = %s",
        [student_id],
    ).fetchone() == (student["nickname"], "student", HI_BC, 1, "ZS", True)
    assert conn.execute(
        "select role, program_id from public.profiles where id = %s", [teacher_id]
    ).fetchone() == ("vyucujuci", None)
    assert conn.execute(
        "select count(*) from public.teacher_courses where teacher_id = %s", [teacher_id]
    ).fetchone() == (42,)


@pytest.fixture
def me_client(db_url):
    settings = Settings(
        mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[], database_url=db_url
    )
    with TestClient(create_app(settings, verifier=make_verifier())) as client:
        yield client


def bearer(user_id):
    return {"Authorization": f"Bearer {make_token(user_id)}"}


def test_me_read_and_update(conn, catalogue, auth_user, me_client):
    student = account("student")
    user_id = auth_user(student["email"])
    with conn.transaction():
        save_profile(conn, user_id, student)

    response = me_client.get("/me", headers=bearer(user_id))
    assert response.status_code == 200
    assert response.json() == {
        "id": user_id,
        "nickname": student["nickname"],
        "role": "student",
        "study": {"program_id": HI_BC, "year": 1, "semester": "ZS"},
    }

    response = me_client.patch(
        "/me", headers=bearer(user_id), json={"program_id": HI_BC, "year": 3, "semester": "LS"}
    )
    assert response.status_code == 200
    assert response.json()["study"] == {"program_id": HI_BC, "year": 3, "semester": "LS"}
    assert me_client.get("/me", headers=bearer(user_id)).json()["study"]["year"] == 3

    for body in (
        {"program_id": "999", "year": 1, "semester": "ZS"},  # unknown program
        {"program_id": HI_BC, "year": 4, "semester": "ZS"},  # HI Bc. has 3 years
        {"program_id": HI_BC, "year": 1, "semester": "XX"},
    ):
        response = me_client.patch("/me", headers=bearer(user_id), json=body)
        assert response.status_code == 422, body
    assert me_client.get("/me", headers=bearer(user_id)).json()["study"]["year"] == 3


def test_me_of_an_account_without_profile_is_403(auth_user, me_client):
    user_id = auth_user("no-profile@example.com")
    assert me_client.get("/me", headers=bearer(user_id)).status_code == 403
    response = me_client.patch(
        "/me", headers=bearer(user_id), json={"program_id": HI_BC, "year": 1, "semester": "ZS"}
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------------------------
# Chats: /ask stores the question and the answer; /chats and /chats/{id} read them back.
# ---------------------------------------------------------------------------------------------


def students():
    return [a for a in load_accounts()["accounts"] if a["role"] == "student"]


@pytest.fixture
def student(conn, catalogue, auth_user):
    """A logged-in student with a profile: the first student of test_users.json."""
    data = students()[0]
    user_id = auth_user(data["email"])
    with conn.transaction():
        save_profile(conn, user_id, data)
    return user_id


def ask(client, user_id, question, course_id=ZAP, chat_id=None):
    body = {"course_id": course_id, "question": question, "chat_id": chat_id}
    return client.post("/ask", headers=bearer(user_id), json=body)


def test_ask_stores_the_chat_and_reads_it_back(conn, student, me_client):
    first = ask(me_client, student, "  Ako sa hodnotí tento predmet?  ")
    assert first.status_code == 200
    chat_id = first.json()["chat_id"]
    question, answer = first.json()["question"], first.json()["answer"]
    assert question["role"] == "user" and question["text"] == "Ako sa hodnotí tento predmet?"
    assert question["found"] is None and question["sources"] == []
    assert answer["role"] == "assistant" and answer["found"] is True and "[1]" in answer["text"]
    assert answer["sources"][0]["section"] == "Priebežné hodnotenie (PH)"

    second = ask(me_client, student, "Neviem, kedy je skúška?", chat_id=chat_id)
    assert second.status_code == 200
    assert second.json()["chat_id"] == chat_id
    neviem = second.json()["answer"]
    assert neviem["found"] is False and neviem["text"] is None and neviem["sources"] == []

    chats = me_client.get("/chats", headers=bearer(student)).json()
    assert [chat["id"] for chat in chats] == [chat_id]
    assert chats[0]["title"] == "Ako sa hodnotí tento predmet?"
    assert chats[0]["course"]["code"] == "26000629"
    assert chats[0]["updated_at"] == second.json()["question"]["created_at"]

    chat = me_client.get(f"/chats/{chat_id}", headers=bearer(student)).json()
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant", "user", "assistant"]
    assert chat["messages"][0] == question
    assert chat["messages"][1] == answer  # the sources are stored exactly as they were shown
    assert chat["messages"][3] == neviem
    assert conn.execute(
        "select content, language, found from public.chat_messages where id = %s", [neviem["id"]]
    ).fetchone() == ("Neviem", None, False)


def test_one_chat_per_course_newest_first(student, me_client):
    zap = ask(me_client, student, "Ako sa hodnotí tento predmet?").json()["chat_id"]
    hip = ask(me_client, student, "Ako sa hodnotí tento predmet?", course_id=HIP).json()["chat_id"]
    assert zap != hip
    chats = me_client.get("/chats", headers=bearer(student)).json()
    assert [chat["id"] for chat in chats] == [hip, zap]
    assert ask(me_client, student, "A skúška?", chat_id=zap).status_code == 200
    chats = me_client.get("/chats", headers=bearer(student)).json()
    assert [chat["id"] for chat in chats] == [zap, hip]


def test_ask_errors_store_nothing(conn, student, auth_user, me_client):
    chat_id = ask(me_client, student, "Ako sa hodnotí tento predmet?").json()["chat_id"]
    assert ask(me_client, student, "Ako sa hodnotí?", course_id="999").status_code == 404
    assert ask(me_client, student, "Ako sa hodnotí?", chat_id=str(uuid.uuid4())).status_code == 404
    response = ask(me_client, student, "Ako sa hodnotí?", course_id=HIP, chat_id=chat_id)
    assert response.status_code == 422
    assert ask(me_client, student, "  a  ").status_code == 422
    assert me_client.get("/chats/not-a-uuid", headers=bearer(student)).status_code == 422

    # another student sees nothing of it and cannot write into it
    other_data = students()[1]
    other = auth_user(other_data["email"])
    with conn.transaction():
        save_profile(conn, other, other_data)
    assert me_client.get("/chats", headers=bearer(other)).json() == []
    assert me_client.get(f"/chats/{chat_id}", headers=bearer(other)).status_code == 404
    assert ask(me_client, other, "Ako sa hodnotí?", chat_id=chat_id).status_code == 404

    # an account without a profile
    nobody = auth_user("no-profile-chat@example.com")
    assert ask(me_client, nobody, "Ako sa hodnotí?").status_code == 403
    assert me_client.get("/chats", headers=bearer(nobody)).status_code == 403
    assert me_client.get(f"/chats/{chat_id}", headers=bearer(nobody)).status_code == 403

    assert conn.execute(
        "select count(*) from public.chats c join public.chat_messages m on m.chat_id = c.id"
        " where c.user_id in (%s, %s, %s)",
        [student, other, nobody],
    ).fetchone() == (2,)


PH = "Priebežné hodnotenie (PH)"
FAKE_EMBEDDING = "[" + ",".join(["0.01"] * 768) + "]"


def zap_rows(conn):
    """ZAP's sheet chunks: (section, chunk_index) -> (content, has embedding, embed_model)."""
    rows = conn.execute(
        "select section, chunk_index, content, embedding is not null, embed_model"
        " from public.knowledge_chunks where source_type = 'sheet' and course_id = %s",
        [ZAP],
    ).fetchall()
    return {(section, index): rest for section, index, *rest in rows}


def test_sync_sheet_chunks(conn, catalogue):
    chunks = build_chunks(DEFAULT_MAIS_DATA_DIR)
    total = sum(map(len, chunks.values()))
    assert (len(chunks), total) == (563, 10_981)
    assert missing_courses(conn, list(chunks)) == []
    assert missing_courses(conn, ["not-a-course"]) == ["not-a-course"]

    first = sync_sheet_chunks(conn, chunks)  # the database may hold them from an earlier run
    assert first.deleted == 0 and first.inserted + first.updated + first.unchanged == total
    assert sync_sheet_chunks(conn, chunks) == SyncCounts(0, 0, 0, unchanged=total)
    assert count_sheet_chunks(conn) == total
    ph_text = next(c.content for c in chunks[ZAP] if c.section == PH)
    assert zap_rows(conn)[(PH, 0)] == [ph_text, False, None]

    zap = chunks[ZAP]
    conn.execute(
        "update public.knowledge_chunks set embedding = %s::extensions.vector, embed_model = 'test'"
        " where source_type = 'sheet' and course_id = %s",
        [FAKE_EMBEDDING, ZAP],
    )
    dropped = next(c for c in zap if c.section == "Poznámky")
    changed = [
        replace(c, content=c.content + " (zmena)") if c.section == PH else c
        for c in zap
        if c != dropped
    ] + [Chunk(section="Nová sekcia", chunk_index=0, content="nový text")]
    try:
        assert sync_sheet_chunks(conn, {ZAP: changed}) == SyncCounts(
            inserted=1, updated=1, deleted=1, unchanged=len(zap) - 2
        )
        rows = zap_rows(conn)
        assert rows[(PH, 0)] == [ph_text + " (zmena)", False, None]  # new text, no embedding
        assert rows[("Počet kreditov", 0)][1:] == [True, "test"]  # unchanged keeps its embedding
        assert ("Poznámky", 0) not in rows
        assert rows[("Nová sekcia", 0)] == ["nový text", False, None]
        assert count_sheet_chunks(conn) == total  # other courses untouched
    finally:
        sync_sheet_chunks(conn, {ZAP: zap})
        conn.execute(
            "update public.knowledge_chunks set embedding = null, embed_model = null"
            " where source_type = 'sheet' and course_id = %s and embed_model = 'test'",
            [ZAP],
        )
    assert sync_sheet_chunks(conn, chunks) == SyncCounts(0, 0, 0, unchanged=total)
