"""The model's answer from the whole sheet (app.answerer) with a fake client: no network."""

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from app import llm
from app.answerer import (
    ANSWER_SCHEMA,
    LANGUAGE_REMINDER,
    NOT_FOUND,
    SYSTEM_INSTRUCTION,
    AnswerUnavailable,
    answer_question,
    build_prompt,
    renumber_citations,
    unsupported_numbers,
)
from app.catalog import Catalog
from app.chunking import chunk_sheet
from app.config import DEFAULT_MAIS_DATA_DIR
from app.knowledge import CommunitySource

ZAP = "65954478"
ZAP_NAME = "Základy algoritmizácie a programovania"
PH = "Priebežné hodnotenie (PH)"


class FakeModels:
    def __init__(self, reply):
        self.reply = reply  # a dict (sent as JSON), a raw string, or an exception
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        if isinstance(self.reply, Exception):
            raise self.reply
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        usage = SimpleNamespace(prompt_token_count=1900, candidates_token_count=40)
        return SimpleNamespace(text=text, usage_metadata=usage)


class FakeClient:
    def __init__(self, reply):
        self.models = FakeModels(reply)


@pytest.fixture(scope="module")
def zap():
    return Catalog.load(DEFAULT_MAIS_DATA_DIR).get_sheet(ZAP)


def ph_number(sheet):
    return next(n for n, c in enumerate(chunk_sheet(sheet), 1) if c.section == PH)


def test_prompt_numbers_every_chunk_of_the_sheet(zap):
    chunks = chunk_sheet(zap)
    prompt = build_prompt(ZAP_NAME, chunks, "kolko na zapocet?")
    assert prompt.startswith(f'Predmet: {ZAP_NAME}\n\nZdroje:\n<zdroj n="1" sekcia="Pracovisko">\n')
    assert prompt.count("<zdroj ") == prompt.count("\n</zdroj>") == len(chunks)
    assert f'<zdroj n="{len(chunks)}" ' in prompt
    assert f'<zdroj n="{ph_number(zap)}" sekcia="{PH}">\nŠtudent prospeje v PH' in prompt
    assert prompt.endswith(f"\n\nOtázka: kolko na zapocet?\n\n{LANGUAGE_REMINDER}")


def test_answer_cites_the_exact_sheet_text(zap):
    n = ph_number(zap)
    client = FakeClient(
        {"found": True, "answer": f"Treba aspoň 11 % z 20 % [{n}].", "language": "sk"}
    )
    answer = answer_question(client, ZAP_NAME, zap, "kolko percent treba na zapocet?")
    assert answer.found and answer.language == "sk"
    assert answer.text == "Treba aspoň 11 % z 20 % [1]."
    [source] = answer.sources
    ph_text = next(s.text for s in zap.sections if s.label == PH)
    assert (source.n, source.type, source.section, source.quote) == (1, "sheet", PH, ph_text)
    assert (source.url, source.date) == (zap.source_url, zap.fetched_at)
    assert source.author.kind == "mais" and source.verified and not source.outdated
    assert (answer.prompt_tokens, answer.output_tokens) == (1900, 40)

    model, contents, config = client.models.calls[0]
    assert model == llm.ANSWER_MODEL == "gemini-3.5-flash-lite"
    assert contents == build_prompt(ZAP_NAME, chunk_sheet(zap), "kolko percent treba na zapocet?")
    assert config.system_instruction == SYSTEM_INSTRUCTION
    assert config.response_json_schema == ANSWER_SCHEMA
    assert (config.temperature, config.max_output_tokens) == (0, 400)
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL


def test_citations_are_renumbered_in_order_of_appearance():
    text, cited = renumber_citations("A [3]. B [1, 3]. C [99]. D [3][3]; E [2;0].", 5)
    assert text == "A [1]. B [2][1]. C. D [1]; E [3]."
    assert cited == [3, 1, 2]


@pytest.mark.parametrize(
    "reply",
    [
        {"found": False, "answer": "", "language": "sk"},
        {"found": True, "answer": "Bez citácie.", "language": "sk"},
        {"found": True, "answer": "Len zlá citácia [999].", "language": "sk"},
    ],
)
def test_no_valid_citation_is_neviem(zap, reply):
    assert answer_question(FakeClient(reply), ZAP_NAME, zap, "kedy je prvy test?") == NOT_FOUND


def test_unknown_language_is_none(zap):
    reply = {"found": True, "answer": "Ok [1].", "language": "de"}
    assert answer_question(FakeClient(reply), ZAP_NAME, zap, "?").language is None


@pytest.mark.parametrize(
    "reply",
    [
        "not json",
        "[1, 2]",
        {"found": "yes", "answer": "x", "language": "sk"},
        {"answer": "x"},
        errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "x"}}),
        errors.ServerError(503, {"error": {"code": 503, "message": "busy", "status": "x"}}),
    ],
)
def test_a_failed_or_broken_reply_is_unavailable(zap, reply):
    with pytest.raises(AnswerUnavailable):
        answer_question(FakeClient(reply), ZAP_NAME, zap, "kolko na zapocet?")


@pytest.mark.parametrize(
    ("text", "sources", "unsupported"),
    [
        ("Predmet má 8 kreditov [1].", ["5"], ["8"]),
        ("Treba aspoň 11 % z 20 % [1].", ["min. 11% z 20%."], []),
        ("Zmena platí od 1. 9. 2026 [2].", ["Dátum: 01.09.2026"], []),
        ("Pozri zdroj [12].", ["bez čísel"], []),  # citations are not numbers of the answer
        ("V 2. ročníku [1].", ["bez čísel", "Programovanie 2"], []),  # e.g. from the course name
        ("Má 3 alebo 4 kredity [1].", ["4"], ["3"]),
    ],
)
def test_unsupported_numbers(text, sources, unsupported):
    assert unsupported_numbers(text, sources) == unsupported


def test_an_answer_with_a_made_up_number_is_neviem(zap, caplog):
    credits = next(n for n, c in enumerate(chunk_sheet(zap), 1) if c.section == "Počet kreditov")
    reply = {"found": True, "answer": f"Predmet má 8 kreditov [{credits}].", "language": "sk"}
    assert answer_question(FakeClient(reply), ZAP_NAME, zap, "kolko kreditov?") == NOT_FOUND
    assert "answer dropped: 8 not in its cited sources" in caplog.text

    reply["answer"] = f"Predmet má 5 kreditov [{credits}]."
    assert answer_question(FakeClient(reply), ZAP_NAME, zap, "kolko kreditov?").found


def community_answer(**changes):
    values = {
        "answer_id": uuid.UUID(int=1),
        "question_id": uuid.UUID(int=2),
        "question_text": 'Môžem robiť "projekt" sám?',
        "text": "Projekt sa robí v tíme, tento rok po 3 ľuďoch.",
        "role": "student",
        "nickname": "student02",
        "verified": False,
        "created_at": datetime(2026, 11, 27, 12, 0, tzinfo=UTC),
        "similarity": 0.81,
    }
    return CommunitySource(**{**values, **changes})


def test_community_answers_follow_the_sheet_in_the_prompt(zap):
    chunks = chunk_sheet(zap)
    teacher = community_answer(role="vyucujuci", nickname="vyucujuci01", verified=True)
    prompt = build_prompt(
        ZAP_NAME, chunks, "robi sa projekt v time?", [community_answer(), teacher]
    )
    first, second = len(chunks) + 1, len(chunks) + 2
    assert (
        f'<zdroj n="{first}" typ="odpoveď študenta" overené="nie"'
        " otázka=\"Môžem robiť 'projekt' sám?\">\nProjekt sa robí v tíme" in prompt
    )
    assert f'<zdroj n="{second}" typ="odpoveď vyučujúceho" overené="áno"' in prompt
    assert prompt.index(f'<zdroj n="{len(chunks)}" sekcia=') < prompt.index(f'<zdroj n="{first}"')


def test_a_cited_community_answer_becomes_an_answer_source(zap):
    n = len(chunk_sheet(zap)) + 1
    reply = {
        "found": True,
        "answer": f"Podľa odpovede študenta (neoverené) sa projekt robí v tíme po 3 [{n}].",
        "language": "sk",
    }
    answer = answer_question(
        FakeClient(reply), ZAP_NAME, zap, "robi sa projekt v time?", [community_answer()]
    )
    assert answer.found and answer.text.endswith("po 3 [1].")
    [source] = answer.sources
    assert (source.n, source.type, source.section, source.url) == (1, "answer", None, None)
    assert source.quote == "Projekt sa robí v tíme, tento rok po 3 ľuďoch."
    assert source.question.id == uuid.UUID(int=2)
    assert source.question.text == 'Môžem robiť "projekt" sám?'
    assert (source.author.kind, source.author.nickname) == ("student", "student02")
    assert source.verified is False and source.date == datetime(2026, 11, 27, 12, 0, tzinfo=UTC)

    # a number the cited community answer does not have is dropped like any other
    reply["answer"] = f"Projekt sa robí po 4 [{n}]."
    assert answer_question(FakeClient(reply), ZAP_NAME, zap, "?", [community_answer()]) == NOT_FOUND
