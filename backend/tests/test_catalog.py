"""Catalogue API against the committed MAIS snapshot data/mais/2026-27.

The expected counts are those of this snapshot.
"""

import pytest
from fastapi.testclient import TestClient

from app.catalog import normalize, parse_period, parse_semesters
from app.main import create_app

HI_BC = "65669424"
ZAP = "65954478"
HIP = "69574272"


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_programs(client):
    programs = client.get("/programs").json()
    assert len(programs) == 32
    by_id = {p["id"]: p for p in programs}
    assert by_id[HI_BC] == {
        "id": HI_BC,
        "code": "HI_Bc_D_sk",
        "name": "Hospodárska informatika",
        "degree": "bc",
        "language": "sk",
        "method": "prezencna",
        "years": 3,
    }
    degrees = [p["degree"] for p in programs]
    assert (degrees.count("bc"), degrees.count("bc_po"), degrees.count("ing")) == (15, 1, 16)
    assert sum(p["language"] == "en" for p in programs) == 4
    assert sum(p["method"] == "kombinovana" for p in programs) == 3
    # Bc first; within one name the Slovak full-time variant first
    assert [p["code"] for p in programs[:2]] == ["ApE_Bc_D_sk", "ApE_Bc_D_KM"]


def test_all_courses(client):
    courses = client.get("/courses").json()
    assert len(courses) == 563
    assert len({c["id"] for c in courses}) == 563


def test_course_zap(client):
    response = client.get(f"/courses/{ZAP}")
    assert response.status_code == 200
    assert response.json() == {
        "id": ZAP,
        "code": "26000629",
        "name": "Základy algoritmizácie a programovania",
        "credits": 5,
        "semesters": ["ZS"],
    }


def test_course_both_semesters(client):
    courses = client.get("/courses").json()
    assert sum(c["semesters"] == ["ZS", "LS"] for c in courses) == 44


def test_unknown_ids_return_404(client):
    assert client.get("/courses/1").status_code == 404
    assert client.get("/programs/1/courses").status_code == 404


def test_hi_bc_year3_winter_includes_state_exam_course(client):
    response = client.get(f"/programs/{HI_BC}/courses", params={"year": 3, "semester": "ZS"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 8
    assert all(i["year"] == 3 and i["semester"] == "ZS" for i in items)
    hip = [i for i in items if i["course"]["id"] == HIP]
    assert hip == [
        {
            "course": {
                "id": HIP,
                "code": "26001478",
                "name": "Hospodárska informatika v praxi",
                "credits": 6,
                "semesters": ["ZS"],
            },
            "year": 3,
            "semester": "ZS",
            "type": "P",
            "state_exam": True,
        }
    ]
    # regular plan rows first, state-exam courses after them
    assert items[-1]["state_exam"] is True


def test_every_plan_row_has_year_and_semester(client):
    programs = client.get("/programs").json()
    total = 0
    for program in programs:
        items = client.get(f"/programs/{program['id']}/courses").json()
        total += len(items)
        assert all(i["year"] >= 1 and i["semester"] in ("ZS", "LS") for i in items)
    assert total == 1349  # all P / PV / V rows of all plans, state-exam tables included


def test_invalid_filters_return_422(client):
    assert client.get(f"/programs/{HI_BC}/courses", params={"year": 7}).status_code == 422
    assert client.get(f"/programs/{HI_BC}/courses", params={"semester": "XS"}).status_code == 422


@pytest.mark.parametrize(
    "query",
    ["zaklady algoritmizacie", "ZÁKLADY ALGORITMIZÁCIE", "algoritmizacie zaklady", "26000629"],
)
def test_search_finds_zap(client, query):
    ids = [c["id"] for c in client.get("/courses", params={"q": query}).json()]
    assert ZAP in ids


def test_search_no_match(client):
    assert client.get("/courses", params={"q": "xyzxyz"}).json() == []


def test_cors_allows_frontend_origin(client):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_helpers():
    assert normalize("Základy  ALGORITMIZÁCIE") == "zaklady algoritmizacie"
    assert parse_period("3. rok ZS") == (3, "ZS")
    assert parse_period("3.rok LS") == (3, "LS")
    assert parse_semesters("ZS, LS") == ["ZS", "LS"]
