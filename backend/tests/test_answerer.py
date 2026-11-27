"""The model's answer from the whole sheet (app.answerer) with a fake client: no network."""

import json
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
)
from app.catalog import Catalog
from app.chunking import chunk_sheet
from app.config import DEFAULT_MAIS_DATA_DIR

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
