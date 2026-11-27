"""Embedding calls (app.llm) and the comparison metrics, with a fake client: no network."""

import math

import pytest
from google.genai import types

from app import llm
from app.chunking import Chunk
from scripts.compare_embeddings import Question, Ranked, best_threshold, rank_question, right_chunks


class FakeModels:
    """Returns for text number i of a request the vector (3, 4 + i, 0, ...): not normalized."""

    def __init__(self, short_by: int = 0) -> None:
        self.calls: list[tuple[str, list[str], types.EmbedContentConfig]] = []
        self.short_by = short_by

    def embed_content(self, *, model, contents, config):
        texts = [content.parts[0].text for content in contents]
        self.calls.append((model, texts, config))
        vectors = [[3.0, 4.0 + i] + [0.0] * (llm.EMBED_DIMENSIONS - 2) for i in range(len(texts))]
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=v) for v in vectors[self.short_by :]]
        )


class FakeClient:
    def __init__(self, short_by: int = 0) -> None:
        self.models = FakeModels(short_by)


DOC = llm.Document(title="ZAP — Priebežné hodnotenie (PH)", text="min. 11% z 20%")


def test_documents_for_001_carry_the_title_and_task_type():
    client = FakeClient()
    [vector] = llm.embed_documents(client, llm.GEMINI_EMBEDDING_001, [DOC])
    model, texts, config = client.models.calls[0]
    assert model == "gemini-embedding-001"
    assert texts == ["ZAP — Priebežné hodnotenie (PH)\nmin. 11% z 20%"]
    assert (config.task_type, config.output_dimensionality) == ("RETRIEVAL_DOCUMENT", 768)
    assert vector[:2] == pytest.approx([0.6, 0.8])  # normalized here
    assert math.fsum(v * v for v in vector) == pytest.approx(1.0)


def test_documents_for_2_use_the_text_prefix_and_no_task_type():
    client = FakeClient()
    llm.embed_documents(client, llm.GEMINI_EMBEDDING_2, [DOC])
    _, texts, config = client.models.calls[0]
    assert texts == ["title: ZAP — Priebežné hodnotenie (PH) | text: min. 11% z 20%"]
    assert (config.task_type, config.output_dimensionality) == (None, 768)


@pytest.mark.parametrize(
    ("model", "task", "text", "task_type"),
    [
        ("gemini-embedding-001", "question_answering", "kolko na zapocet?", "QUESTION_ANSWERING"),
        ("gemini-embedding-001", "retrieval_query", "kolko na zapocet?", "RETRIEVAL_QUERY"),
        (
            "gemini-embedding-2",
            "question_answering",
            "task: question answering | query: kolko na zapocet?",
            None,
        ),
        (
            "gemini-embedding-2",
            "retrieval_query",
            "task: search result | query: kolko na zapocet?",
            None,
        ),
    ],
)
def test_queries(model, task, text, task_type):
    client = FakeClient()
    llm.embed_queries(client, model, ["kolko na zapocet?"], task)
    _, texts, config = client.models.calls[0]
    assert texts == [text]
    assert config.task_type == task_type


def test_batches_keep_the_order():
    client = FakeClient()
    docs = [llm.Document("t", f"text {i}") for i in range(120)]
    vectors = llm.embed_documents(client, llm.GEMINI_EMBEDDING_001, docs)
    assert [len(texts) for _, texts, _ in client.models.calls] == [50, 50, 20]
    assert len(vectors) == 120
    # the third text of the last batch: (3, 4 + 2) normalized
    assert vectors[102][:2] == pytest.approx([3 / math.hypot(3, 6), 6 / math.hypot(3, 6)])


def test_a_missing_vector_is_an_error():
    with pytest.raises(RuntimeError, match="1 vectors for 2 texts"):
        llm.embed_documents(FakeClient(short_by=1), llm.GEMINI_EMBEDDING_2, [DOC, DOC])


def test_unknown_model_and_zero_vector():
    with pytest.raises(ValueError):
        llm.embed_documents(FakeClient(), "text-embedding-004", [DOC])
    with pytest.raises(ValueError):
        llm.normalize([0.0, 0.0])


CHUNKS = [
    Chunk("Priebežné hodnotenie (PH)", 0, "Zápočet: min. 11% z 20%."),
    Chunk("Stručná osnova predmetu", 0, "Premenné, cykly"),
    Chunk("Stručná osnova predmetu", 1, "Podprogramy a funkcie, rekurzia"),
]


def question(answerable=True, section="Stručná osnova predmetu", quote="funkcie, rekurzia"):
    evidence = [{"section": section, "quote": quote}] if answerable else []
    return Question("q", "1", "rekurzia?", answerable, "sk", evidence)


def test_right_chunk_is_the_part_with_the_quote():
    assert right_chunks(CHUNKS, question().evidence) == {2}
    # a quote found in no part: every part of the section counts
    assert right_chunks(CHUNKS, question(quote="nikde").evidence) == {1, 2}


def test_rank_and_threshold():
    vectors = [[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]]
    ranked = rank_question(question(), [0.0, 1.0], CHUNKS, vectors)
    assert (ranked.rank, ranked.top_similarity) == (1, 1.0)
    assert ranked.top_sections == [
        "Stručná osnova predmetu",
        "Stručná osnova predmetu",
        "Priebežné hodnotenie (PH)",
    ]
    second = rank_question(question(), [0.6, 0.8], CHUNKS, vectors)
    assert second.rank == 2
    neviem = Ranked(question(answerable=False), None, 0.5, [])
    assert best_threshold([ranked, second, neviem]) == (pytest.approx(1.0), 3)
