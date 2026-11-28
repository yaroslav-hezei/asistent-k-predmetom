"""Database: the migrations, the catalogue import, the connection pool, test accounts, /me,
the chats, the knowledge base, "Otázky komunity" and the teacher's "Overovanie".

These tests need TEST_DATABASE_URL: a throwaway local Postgres with the migrations applied
(`npx supabase@3.2.0 db start` from the repo root, see backend/README.md). Never point it at the
shared cloud database: the import rewrites the catalogue tables. Without the variable the tests are
skipped locally; in CI it is required.
"""

import json
import os
import re
import uuid
from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import psycopg
import pytest
from fastapi.testclient import TestClient
from google.genai import errors, types

from app import llm
from app.catalog import Catalog
from app.chunking import Chunk, chunk_sheet
from app.config import DEFAULT_MAIS_DATA_DIR, Settings
from app.knowledge import (
    SyncCounts,
    count_pending,
    delete_course_note,
    embed_pending_chunks,
    search_answers,
    sync_sheet_chunks,
)
from app.main import create_app
from app.routers.chat import ASSISTANT_UNAVAILABLE
from scripts.create_test_users import find_user_id, load_accounts, save_profile
from scripts.import_catalog import count_rows, import_catalog
from scripts.sync_sheet_chunks import build_chunks, count_sheet_chunks, missing_courses
from tests.jwt_helpers import make_token, make_verifier
from tests.test_answerer import FakeClient

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
SHEET = ("sheet",)
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


def test_embed_pending_chunks(conn, db_url, catalogue):
    chunks = build_chunks(DEFAULT_MAIS_DATA_DIR)
    sync_sheet_chunks(conn, chunks)
    total = sum(map(len, chunks.values()))
    assert count_pending(conn, "fake", SHEET) == total
    # by default only community answers get vectors, never the sheets or the teachers' notes
    assert count_pending(conn, "fake") == 0
    assert embed_pending_chunks(conn, lambda documents: 1 / 0, "fake") == 0

    titles = []

    def embed(documents):
        titles.extend(d.title for d in documents)
        return [[0.0] * 767 + [1.0] for _ in documents]

    progress = []
    try:
        stored = embed_pending_chunks(
            conn,
            embed,
            "fake",
            batch_size=50,
            limit=120,
            on_batch=progress.append,
            source_types=SHEET,
        )
        assert (stored, progress) == (120, [50, 100, 120])
        assert count_pending(conn, "fake", SHEET) == total - 120
        assert titles[0].split(" — ")[0] and all(" — " in t for t in titles)  # course — section
        # the next run continues with the chunks still without a vector
        assert (
            embed_pending_chunks(conn, embed, "fake", batch_size=50, limit=10, source_types=SHEET)
            == 10
        )
        assert count_pending(conn, "fake", SHEET) == total - 130
        assert conn.execute(
            "select count(*), min(extensions.vector_dims(embedding))"
            " from public.knowledge_chunks where embed_model = 'fake'"
        ).fetchone() == (130, 768)
        with pytest.raises(RuntimeError, match="0 vectors for 1 chunks"):
            embed_pending_chunks(conn, lambda documents: [], "fake", limit=1, source_types=SHEET)
        with psycopg.connect(db_url) as not_autocommit, pytest.raises(ValueError):
            embed_pending_chunks(not_autocommit, embed, "fake", limit=1)
    finally:
        conn.execute(
            "update public.knowledge_chunks set embedding = null, embed_model = null"
            " where embed_model = 'fake'"
        )


@pytest.fixture
def model_app(db_url):
    """An app whose answering model is a fake that gives `reply`."""

    def make(reply):
        settings = Settings(
            mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[], database_url=db_url
        )
        app = create_app(settings, verifier=make_verifier(), model_client=FakeClient(reply))
        return TestClient(app)

    return make


def count_messages(conn, user_id):
    return conn.execute(
        "select count(*) from public.chats c join public.chat_messages m on m.chat_id = c.id"
        " where c.user_id = %s",
        [user_id],
    ).fetchone()[0]


def test_ask_with_the_model_and_when_it_fails(conn, student, model_app):
    sheet = Catalog.load(DEFAULT_MAIS_DATA_DIR).get_sheet(ZAP)
    n = next(i for i, c in enumerate(chunk_sheet(sheet), 1) if c.section == PH)
    reply = {"found": True, "answer": f"Treba aspoň 11 % z 20 % [{n}].", "language": "sk"}
    with model_app(reply) as client:
        response = ask(client, student, "kolko percent treba na zapocet?")
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert answer["found"] is True and answer["text"] == "Treba aspoň 11 % z 20 % [1]."
    assert [(s["n"], s["section"]) for s in answer["sources"]] == [(1, PH)]
    stored = count_messages(conn, student)

    failure = errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "x"}})
    with model_app(failure) as client:
        response = ask(client, student, "kolko percent treba na zapocet?")
    assert response.status_code == 503
    assert response.json()["detail"] == ASSISTANT_UNAVAILABLE
    assert count_messages(conn, student) == stored  # nothing stored, the question can be resent


# ---------------------------------------------------------------------------------------------
# "Otázky komunity": the loop Neviem → publish → another student answers → the assistant knows.
# ---------------------------------------------------------------------------------------------


class LoopModels:
    """A fake model: every text gets the same vector (all similarities 1.0); the answer cites the
    first community answer in the prompt, or is 'Neviem' when there is none."""

    def embed_content(self, *, model, contents, config):
        vector = [1.0] + [0.0] * 767
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=vector) for _ in contents]
        )

    def generate_content(self, *, model, contents, config):
        match = re.search(r'<zdroj n="(\d+)" typ="odpoveď', contents)
        if match is None:
            reply = {"language": "sk", "found": False, "answer": ""}
        else:
            reply = {
                "language": "sk",
                "found": True,
                "answer": f"Podľa odpovede študenta (neoverené) je projekt tímový [{match[1]}].",
            }
        usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=20)
        return SimpleNamespace(text=json.dumps(reply), usage_metadata=usage)


class LoopClient:
    models = LoopModels()


def community_user(conn, auth_user, account, study_of=None):
    data = dict(account)
    if study_of is not None:
        data["study"] = study_of["study"]
    user_id = auth_user(f"{uuid.uuid4().hex[:8]}-{account['email']}")
    data["nickname"] = f"{account['nickname']}-{user_id[:4]}"
    with conn.transaction():
        save_profile(conn, user_id, data)
    return user_id, data["nickname"]


def test_community_loop(conn, catalogue, auth_user, db_url):
    accounts = load_accounts()["accounts"]
    first, second = students()[0], students()[1]
    teacher_account = next(a for a in accounts if a["role"] == "vyucujuci")
    asker, _ = community_user(conn, auth_user, first)
    helper, helper_name = community_user(conn, auth_user, second, study_of=first)
    teacher, teacher_name = community_user(conn, auth_user, teacher_account)
    plan = Catalog.load(DEFAULT_MAIS_DATA_DIR).program_courses(
        first["study"]["program_id"], first["study"]["year"], first["study"]["semester"]
    )
    assert ZAP in {item.course.id for item in plan}  # a course of their "Moje predmety"
    question_text = "Môžem robiť semestrálny projekt sám, alebo len v tíme?"
    settings = Settings(
        mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[], database_url=db_url
    )
    app = create_app(settings, verifier=make_verifier(), model_client=LoopClient())
    with TestClient(app) as client:
        # 1. the assistant does not know → the asker publishes from the "Neviem" message
        neviem = ask(client, asker, question_text).json()
        assert neviem["answer"]["found"] is False
        published = client.post(
            "/questions",
            headers=bearer(asker),
            json={
                "course_id": ZAP,
                "text": question_text,
                "source_message_id": neviem["answer"]["id"],
            },
        )
        assert published.status_code == 200
        question = published.json()
        assert (question["status"], question["from_assistant"], question["mine"]) == (
            "open",
            True,
            True,
        )
        question_id = question["id"]
        other = client.post(
            "/questions",
            headers=bearer(helper),
            json={
                "course_id": ZAP,
                "text": "Iná otázka?",
                "source_message_id": neviem["answer"]["id"],
            },
        )
        assert other.status_code == 422  # not the helper's message

        # 2. the helper sees it: badge, the open tab, similar questions
        assert client.get("/badges", headers=bearer(helper)).json()["open_questions"] >= 1
        assert client.get("/badges", headers=bearer(asker)).json() == {
            "unread_notifications": 0,
            "open_questions": 0,  # own questions do not count
            "unverified_answers": 0,  # a student verifies nothing
        }
        listed = client.get(
            "/questions", headers=bearer(helper), params={"course_id": ZAP, "status": "open"}
        ).json()
        assert question_id in [item["id"] for item in listed["items"]]
        assert listed["counts"]["open"] >= 1
        # "Všetky moje predmety": the helper's study plan has ZAP, the teacher teaches it
        for user in (helper, teacher):
            mine = client.get("/questions", headers=bearer(user)).json()
            assert question_id in [item["id"] for item in mine["items"]]
            assert mine["counts"]["open"] >= 1
        own = client.get("/questions", headers=bearer(asker)).json()["items"]
        assert [item["mine"] for item in own if item["id"] == question_id] == [True]
        # without a study plan and courses to teach: nothing
        conn.execute(
            "update public.profiles set program_id = null, year = null, semester = null"
            " where id = %s",
            [helper],
        )
        assert client.get("/questions", headers=bearer(helper)).json() == {
            "items": [],
            "counts": {"open": 0, "answered": 0},
        }
        conn.execute(
            "update public.profiles set program_id = %s, year = %s, semester = %s where id = %s",
            [
                first["study"]["program_id"],
                first["study"]["year"],
                first["study"]["semester"],
                helper,
            ],
        )
        similar = client.post(
            "/questions/similar",
            headers=bearer(helper),
            json={"course_id": ZAP, "text": "Robí sa projekt v tíme?"},
        ).json()
        assert question_id in [item["id"] for item in similar]

        # 3. the asker cannot answer; the helper answers → knowledge base + notification
        own = client.post(
            f"/questions/{question_id}/answers", headers=bearer(asker), json={"text": "Neviem."}
        )
        assert own.status_code == 403
        answered = client.post(
            f"/questions/{question_id}/answers",
            headers=bearer(helper),
            json={"text": "  Projekt sa robí v tíme, tento rok po troch ľuďoch.  "},
        )
        assert answered.status_code == 200
        answer = answered.json()
        assert answer["text"] == "Projekt sa robí v tíme, tento rok po troch ľuďoch."
        assert (answer["verified"], answer["author"]) == (
            False,
            {"kind": "student", "nickname": helper_name},
        )
        assert conn.execute(
            "select content, embed_model, extensions.vector_dims(embedding)"
            " from public.knowledge_chunks where answer_id = %s",
            [answer["id"]],
        ).fetchone() == (answer["text"], llm.EMBED_MODEL, 768)
        assert client.get("/badges", headers=bearer(asker)).json()["unread_notifications"] == 1
        [notification] = client.get("/notifications", headers=bearer(asker)).json()
        assert notification["question"]["id"] == question_id
        assert notification["answer"]["author"]["nickname"] == helper_name
        assert notification["answer"]["text"] == answer["text"]
        assert notification["answer"]["verified"] is False
        assert notification["answer"]["thanked_by_me"] is False
        assert notification["chat_id"] == neviem["chat_id"]  # "Zobraziť v chate"
        assert notification["read"] is False

        # 4. thanks: once per user, never for one's own answer
        thanks = client.post(f"/answers/{answer['id']}/thanks", headers=bearer(asker))
        assert thanks.json() == {"thanks": 1, "thanked_by_me": True}
        again = client.post(f"/answers/{answer['id']}/thanks", headers=bearer(asker))
        assert again.json() == {"thanks": 1, "thanked_by_me": True}
        assert (
            client.post(f"/answers/{answer['id']}/thanks", headers=bearer(helper)).status_code
            == 403
        )

        # 5. a teacher of the course answers verified; verified answers come first
        verified = client.post(
            f"/questions/{question_id}/answers",
            headers=bearer(teacher),
            json={"text": "Áno, projekt je tímový."},
        ).json()
        assert (verified["verified"], verified["author"]["kind"]) == (True, "vyucujuci")
        detail = client.get(f"/questions/{question_id}", headers=bearer(asker)).json()
        assert detail["status"] == "answered" and detail["answer_count"] == 2
        assert [a["author"]["nickname"] for a in detail["answers"]] == [teacher_name, helper_name]
        assert detail["answers"][1]["thanked_by_me"] is True

        # 6. the same question again: the assistant answers from the community answer
        again = ask(client, asker, question_text, chat_id=neviem["chat_id"]).json()["answer"]
        assert again["found"] is True
        [source] = again["sources"]
        assert source["type"] == "answer" and source["question"]["id"] == question_id
        assert source["author"]["kind"] in ("student", "vyucujuci")
        assert source["quote"] in ("Áno, projekt je tímový.", answer["text"])

        # 7. notifications read
        read = client.post("/notifications/read", headers=bearer(asker), json={"ids": None})
        assert read.json()["unread_notifications"] == 0
        answered_tab = client.get(
            "/questions", headers=bearer(helper), params={"course_id": ZAP, "status": "answered"}
        ).json()
        assert question_id in [item["id"] for item in answered_tab["items"]]
        assert client.get(f"/questions/{uuid.uuid4()}", headers=bearer(asker)).status_code == 404


def test_community_without_the_model(conn, catalogue, auth_user, me_client):
    """No GEMINI_API_KEY: publishing and answering still work; no similar questions, no vectors."""
    asker, _ = community_user(conn, auth_user, students()[2])
    helper, _ = community_user(conn, auth_user, students()[3])
    question = me_client.post(
        "/questions", headers=bearer(asker), json={"course_id": ZAP, "text": "Je skúška ústna?"}
    ).json()
    assert question["from_assistant"] is False
    assert (
        me_client.post(
            "/questions/similar", headers=bearer(helper), json={"course_id": ZAP, "text": "Skúška?"}
        ).json()
        == []
    )
    answer = me_client.post(
        f"/questions/{question['id']}/answers", headers=bearer(helper), json={"text": "Písomná."}
    ).json()
    assert conn.execute(
        "select embedding is null from public.knowledge_chunks where answer_id = %s",
        [answer["id"]],
    ).fetchone() == (True,)
    assert count_pending(conn, llm.EMBED_MODEL) >= 1  # embed_chunks.py adds the vector later
    assert (
        me_client.post(
            "/questions", headers=bearer(asker), json={"course_id": "nope", "text": "Otázka?"}
        ).status_code
        == 404
    )


# ---------------------------------------------------------------------------------------------
# "Overovanie": a teacher of the course verifies, hides spam and writes the course's note.
# ---------------------------------------------------------------------------------------------


class NoteModels(LoopModels):
    """Like LoopModels, but the answer cites the teacher's note when the prompt has one."""

    def generate_content(self, *, model, contents, config):
        match = re.search(r'<zdroj n="(\d+)" typ="aktuálna informácia vyučujúceho"', contents)
        if match is None:
            return super().generate_content(model=model, contents=contents, config=config)
        reply = {
            "language": "sk",
            "found": True,
            "answer": f"Projekt sa odovzdáva v 13. týždni [{match[1]}].",
        }
        usage = SimpleNamespace(prompt_token_count=100, candidates_token_count=20)
        return SimpleNamespace(text=json.dumps(reply), usage_metadata=usage)


class NoteClient:
    models = NoteModels()


def test_teacher_verification(conn, catalogue, auth_user, db_url):
    teacher_account = next(a for a in load_accounts()["accounts"] if a["role"] == "vyucujuci")
    asker, _ = community_user(conn, auth_user, students()[4])
    helper, helper_name = community_user(conn, auth_user, students()[5])
    spammer, _ = community_user(conn, auth_user, students()[6])
    teacher, teacher_name = community_user(conn, auth_user, teacher_account)
    not_taught = conn.execute(
        "select id from public.courses where id not in"
        " (select course_id from public.teacher_courses where teacher_id = %s) limit 1",
        [teacher],
    ).fetchone()[0]
    settings = Settings(
        mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[], database_url=db_url
    )
    app = create_app(settings, verifier=make_verifier(), model_client=NoteClient())
    note_text = "Projekt sa odovzdáva v 13. týždni semestra."
    with TestClient(app) as client:

        def get(user, path):
            return client.get(path, headers=bearer(user))

        def post(user, path, body=None):
            return client.post(path, headers=bearer(user), json=body)

        def put_note(user, text, course_id=ZAP):
            return client.put(
                f"/courses/{course_id}/note", headers=bearer(user), json={"text": text}
            )

        question = post(
            asker, "/questions", {"course_id": ZAP, "text": "Kedy sa odovzdáva projekt?"}
        )
        question = question.json()
        path = f"/questions/{question['id']}"
        good = post(
            helper, f"{path}/answers", {"text": "Projekt sa odovzdáva v 13. týždni."}
        ).json()
        spam = post(spammer, f"{path}/answers", {"text": "Lacné hodinky na predaj!"}).json()

        try:
            # 1. the teacher's courses and the badge; a student has none
            courses = get(teacher, "/teacher/courses").json()
            assert len(courses) == 42
            names = [item["course"]["name"] for item in courses]
            assert names == sorted(names)
            assert next(c for c in courses if c["course"]["id"] == ZAP)["unverified_answers"] == 2
            assert get(teacher, "/badges").json()["unverified_answers"] == 2
            assert get(asker, "/teacher/courses").json() == []
            assert get(asker, "/badges").json()["unverified_answers"] == 0

            screen = get(teacher, f"/teacher/courses/{ZAP}").json()
            assert screen["course"]["id"] == ZAP and screen["note"] is None
            assert [a["id"] for a in screen["answers"]] == [good["id"], spam["id"]]  # oldest first
            assert screen["answers"][0]["question"] == {
                "id": question["id"],
                "text": question["text"],
            }
            assert screen["answers"][0]["author"] == {"kind": "student", "nickname": helper_name}

            # 2. only a teacher of the course
            assert get(asker, f"/teacher/courses/{ZAP}").status_code == 403
            assert get(teacher, f"/teacher/courses/{not_taught}").status_code == 403
            assert get(teacher, "/teacher/courses/nope").status_code == 404
            assert post(asker, f"/answers/{good['id']}/verify").status_code == 403
            assert post(helper, f"/answers/{spam['id']}/hide").status_code == 403
            assert post(asker, f"{path}/hide").status_code == 403
            assert put_note(asker, note_text).status_code == 403
            assert put_note(teacher, note_text, not_taught).status_code == 403
            assert put_note(teacher, note_text, "nope").status_code == 404
            assert post(teacher, f"/answers/{uuid.uuid4()}/verify").status_code == 404

            # 3. "Overiť": verified first, the assistant's source says so
            assert post(teacher, f"/answers/{good['id']}/verify").status_code == 204
            assert post(teacher, f"/answers/{good['id']}/verify").status_code == 204  # again
            detail = get(asker, path).json()
            assert [(a["id"], a["verified"]) for a in detail["answers"]] == [
                (good["id"], True),
                (spam["id"], False),
            ]
            verified_by = conn.execute(
                "select verified_by from public.answers where id = %s", [good["id"]]
            ).fetchone()[0]
            assert str(verified_by) == teacher
            assert [a["id"] for a in get(teacher, f"/teacher/courses/{ZAP}").json()["answers"]] == [
                spam["id"]
            ]

            # 4. "Zmazať": the spam answer is gone from the question, notifications, badges and
            # the assistant's sources
            assert get(asker, "/badges").json()["unread_notifications"] == 2
            assert post(teacher, f"/answers/{spam['id']}/hide").status_code == 204
            assert post(teacher, f"/answers/{spam['id']}/hide").status_code == 404  # hidden
            detail = get(asker, path).json()
            assert [a["id"] for a in detail["answers"]] == [good["id"]]
            assert detail["answer_count"] == 1
            notified = [n["answer"]["id"] for n in get(asker, "/notifications").json()]
            assert notified == [good["id"]]
            assert get(asker, "/badges").json()["unread_notifications"] == 1
            assert get(teacher, "/badges").json()["unverified_answers"] == 0
            assert get(teacher, f"/teacher/courses/{ZAP}").json()["answers"] == []
            assert post(asker, f"/answers/{spam['id']}/thanks").status_code == 404
            found = search_answers(conn, ZAP, [1.0] + [0.0] * 767, llm.EMBED_MODEL)
            assert [str(source.answer_id) for source in found] == [good["id"]]

            # 5. "Aktuálna informácia k predmetu": saved, replaced, used and cited by the assistant
            assert put_note(teacher, "   ").status_code == 422
            assert put_note(teacher, "Stará verzia.").status_code == 200
            saved = put_note(teacher, f"  {note_text} ").json()
            assert saved["text"] == note_text
            assert saved["author"] == {"kind": "vyucujuci", "nickname": teacher_name}
            assert conn.execute(
                "select content, embedding is null from public.knowledge_chunks"
                " where source_type = 'course_note' and course_id = %s",
                [ZAP],
            ).fetchall() == [(note_text, True)]
            assert get(teacher, f"/teacher/courses/{ZAP}").json()["note"] == saved

            answer = ask(client, asker, "Kedy sa odovzdáva projekt?").json()["answer"]
            assert answer["found"] is True
            assert answer["text"] == "Projekt sa odovzdáva v 13. týždni [1]."
            [source] = answer["sources"]
            assert (source["type"], source["quote"], source["section"], source["url"]) == (
                "course_note",
                note_text,
                None,
                None,
            )
            assert source["verified"] is True
            assert source["author"] == {"kind": "vyucujuci", "nickname": teacher_name}

            # 6. the note removed: no chunk, the assistant answers without it
            assert client.delete(f"/courses/{ZAP}/note", headers=bearer(teacher)).status_code == 204
            assert client.delete(f"/courses/{ZAP}/note", headers=bearer(teacher)).status_code == 204
            assert conn.execute(
                "select count(*) from public.knowledge_chunks where source_type = 'course_note'"
            ).fetchone() == (0,)
            assert get(teacher, f"/teacher/courses/{ZAP}").json()["note"] is None
            again = ask(client, asker, "Kedy sa odovzdáva projekt?").json()["answer"]
            assert [s["type"] for s in again["sources"]] == ["answer"]

            # 7. hiding the question hides it and its answers everywhere
            assert post(teacher, f"{path}/hide").status_code == 204
            assert post(teacher, f"{path}/hide").status_code == 404
            assert get(asker, path).status_code == 404
            assert get(asker, "/notifications").json() == []
            assert search_answers(conn, ZAP, [1.0] + [0.0] * 767, llm.EMBED_MODEL) == []
        finally:
            delete_course_note(conn, ZAP)
