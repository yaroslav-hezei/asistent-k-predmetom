"""Chat without a database: the placeholder answer, the request model, login on the endpoints.

The endpoints with a database (stored chats, ownership) are tested in test_db.py.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.answerer import PLACEHOLDER_TEXT, answer_question
from app.catalog import Catalog, Sheet, SheetSection
from app.config import DEFAULT_MAIS_DATA_DIR, Settings
from app.main import create_app
from app.models.chat import AskRequest
from tests.jwt_helpers import make_token, make_verifier

ZAP = "65954478"
USER = "6f1c2c1e-1111-4222-8333-444455556666"


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load(DEFAULT_MAIS_DATA_DIR)


def test_every_catalogue_course_has_its_sheet(catalog):
    courses = catalog.search_courses()
    assert len(courses) == 563
    assert all(catalog.get_sheet(course.id) is not None for course in courses)
    assert catalog.get_sheet("999") is None


def test_sheet_of_zap(catalog):
    sheet = catalog.get_sheet(ZAP)
    assert sheet.source_url.endswith(f"tlacPredmetuOSP.mais?predmetId={ZAP}")
    assert sheet.fetched_at == datetime(2026, 11, 17, 15, 11, 35, tzinfo=UTC)
    labels = [section.label for section in sheet.sections]
    assert labels[0] == "Vysoká škola"
    assert "Priebežné hodnotenie (PH)" in labels


def test_placeholder_quotes_a_real_section_exactly(catalog):
    sheet = catalog.get_sheet(ZAP)
    answer = answer_question(sheet, "Ako sa hodnotí tento predmet?")
    assert answer.found
    assert answer.text == PLACEHOLDER_TEXT
    assert "[1]" in answer.text
    assert answer.language == "sk"
    [source] = answer.sources
    section = next(s for s in sheet.sections if s.label == "Priebežné hodnotenie (PH)")
    assert source.n == 1
    assert source.type == "sheet"
    assert source.section == section.label
    assert source.quote == section.text
    assert source.url == sheet.source_url
    assert source.date == sheet.fetched_at
    assert source.author.kind == "mais" and source.author.nickname is None
    assert source.verified and not source.outdated
    assert source.question is None


@pytest.mark.parametrize("question", ["Neviem?", "neviem", "Čo ak NEVIEM odpoveď"])
def test_placeholder_neviem(catalog, question):
    answer = answer_question(catalog.get_sheet(ZAP), question)
    assert not answer.found
    assert answer.text is None and answer.sources == [] and answer.language is None


def test_placeholder_word_must_match_whole(catalog):
    assert answer_question(catalog.get_sheet(ZAP), "Nevieme, kedy je skúška?").found


def test_placeholder_falls_back_to_first_section_with_text():
    sheet = Sheet(
        course_id="1",
        source_url="https://example.invalid/1",
        fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
        sections=(SheetSection("Forma výučby", ""), SheetSection("Poznámky", "Text poznámky.")),
    )
    assert answer_question(sheet, "Otázka?").sources[0].quote == "Text poznámky."
    empty = Sheet("2", "https://example.invalid/2", sheet.fetched_at, (SheetSection("A", " "),))
    assert not answer_question(empty, "Otázka?").found


def test_ask_request_strips_and_limits_the_question():
    assert AskRequest(course_id=ZAP, question="  Kedy je skúška?  ").question == "Kedy je skúška?"
    for question in ("  a  ", "x" * 1001):
        with pytest.raises(ValidationError):
            AskRequest(course_id=ZAP, question=question)
    assert AskRequest(course_id=ZAP, question="abc").chat_id is None


@pytest.fixture
def client():
    settings = Settings(mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[])
    with TestClient(create_app(settings, verifier=make_verifier())) as test_client:
        yield test_client


ENDPOINTS = [
    ("post", "/ask", {"course_id": ZAP, "question": "Ako sa hodnotí tento predmet?"}),
    ("get", "/chats", None),
    ("get", "/chats/6f1c2c1e-0000-4000-8000-000000000000", None),
]


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_chat_endpoints_need_login(client, method, path, body):
    response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_chat_endpoints_without_database_are_503(client, method, path, body):
    headers = {"Authorization": f"Bearer {make_token(USER)}"}
    assert client.request(method, path, json=body, headers=headers).status_code == 503


def test_openapi_marks_chat_endpoints_as_protected(client):
    paths = client.get("/openapi.json").json()["paths"]
    for operation in (
        paths["/ask"]["post"],
        paths["/chats"]["get"],
        paths["/chats/{chat_id}"]["get"],
    ):
        assert operation["security"] == [{"HTTPBearer": []}]
