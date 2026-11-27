"""Compare the embedding models on the evaluation questions: does the search find the right part
of the sheet?

    python scripts/compare_embeddings.py              # both models, both ways to send a question
    python scripts/compare_embeddings.py --no-cache   # ask the API again

Run from `backend/`. Needs GEMINI_API_KEY (environment or the repo's `.env`). Writes nothing to the
database. Vectors are cached in `scratch/embeddings/` (repo root, gitignored), so a re-run sends no
requests.

For every question the search ranks the chunks of its course (the same chunks the knowledge base
holds) by cosine similarity. A chunk is right when its section is an evidence section of the
question and it contains the evidence quote (in a long section cut into parts: the part with the
quote). Reported for each model and way of sending the question:
- hit@1 / hit@3 / hit@5 and MRR over the answerable questions;
- the best similarity found for answerable and for "Neviem" questions, and how many of all
  questions one similarity threshold would sort right (10 "Neviem" questions: a hint, not a tuned
  threshold).

The evaluation questions are test data: they are only measured here, never stored in the
knowledge base or sent with a prompt.
"""

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

from app import llm  # noqa: E402
from app.catalog import Catalog  # noqa: E402
from app.chunking import Chunk, chunk_sheet  # noqa: E402
from app.config import DEFAULT_MAIS_DATA_DIR, REPO_ROOT  # noqa: E402

QUESTIONS_FILE = REPO_ROOT / "data" / "eval" / "questions.jsonl"
CACHE_DIR = REPO_ROOT / "scratch" / "embeddings"
QUERY_TASKS: tuple[llm.QueryTask, ...] = ("question_answering", "retrieval_query")


@dataclass(frozen=True)
class Question:
    id: str
    course_id: str
    text: str
    answerable: bool
    language: str  # "sk" or "en": the language of the question
    evidence: list[dict[str, str]]  # [{section, quote}]


@dataclass(frozen=True)
class Ranked:
    question: Question
    rank: int | None  # 1-based rank of the first right chunk; None for "Neviem" questions
    top_similarity: float
    top_sections: list[str]  # sections of the 3 best chunks


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def load_questions(path: Path = QUESTIONS_FILE) -> list[Question]:
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            questions.append(
                Question(
                    id=raw["id"],
                    course_id=raw["course_id"],
                    text=raw["question"],
                    answerable=raw["answerable"],
                    language=raw["language"],
                    evidence=raw["evidence"],
                )
            )
    return questions


def right_chunks(chunks: Sequence[Chunk], evidence: list[dict[str, str]]) -> set[int]:
    """Indexes of the chunks that hold the evidence: right section and the quote inside; when no
    chunk contains a quote (it runs across two parts), every chunk of an evidence section."""
    sections = {item["section"] for item in evidence}
    quotes = [squash(item["quote"]) for item in evidence]
    in_section = [i for i, chunk in enumerate(chunks) if chunk.section in sections]
    with_quote = {i for i in in_section if any(q in squash(chunks[i].content) for q in quotes)}
    return with_quote or set(in_section)


def rank_question(
    question: Question,
    query_vector: Sequence[float],
    chunks: Sequence[Chunk],
    chunk_vectors: Sequence[Sequence[float]],
) -> Ranked:
    similarities = [sum(q * c for q, c in zip(query_vector, v, strict=True)) for v in chunk_vectors]
    order = sorted(range(len(chunks)), key=lambda i: similarities[i], reverse=True)
    rank = None
    if question.answerable:
        right = right_chunks(chunks, question.evidence)
        if not right:
            raise ValueError(f"{question.id}: no chunk of an evidence section")
        rank = next(position + 1 for position, i in enumerate(order) if i in right)
    return Ranked(
        question=question,
        rank=rank,
        top_similarity=similarities[order[0]],
        top_sections=[chunks[i].section for i in order[:3]],
    )


def best_threshold(ranked: Sequence[Ranked]) -> tuple[float, int]:
    """The similarity threshold that sorts the most questions right (answerable: top similarity at
    or above it; "Neviem": below it) and how many it sorts right."""
    best = (0.0, -1)
    for candidate in sorted({r.top_similarity for r in ranked}):
        right = sum((r.top_similarity >= candidate) == r.question.answerable for r in ranked)
        if right > best[1]:
            best = (candidate, right)
    return best


class Cache:
    """Vectors by (model, kind, input) in one JSON file per model."""

    def __init__(self, directory: Path, enabled: bool) -> None:
        self.directory = directory
        self.enabled = enabled

    def get_many(
        self, model: str, kind: str, inputs: Sequence[str], compute: Callable[[list[int]], list]
    ) -> list[list[float]]:
        path = self.directory / f"{model}.json"
        stored: dict[str, list[float]] = {}
        if self.enabled and path.exists():
            stored = json.loads(path.read_text(encoding="utf-8"))
        keys = [hashlib.sha256(f"{kind}\n{text}".encode()).hexdigest() for text in inputs]
        missing = [i for i, key in enumerate(keys) if key not in stored]
        if missing:
            for i, vector in zip(missing, compute(missing), strict=True):
                stored[keys[i]] = vector
            if self.enabled:
                self.directory.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(stored), encoding="utf-8")
        return [stored[key] for key in keys]


def evaluate(
    client: Any,
    model: str,
    task: llm.QueryTask,
    catalog: Catalog,
    questions: list[Question],
    cache: Cache,
) -> list[Ranked]:
    course_ids = sorted({q.course_id for q in questions})
    chunks = {cid: chunk_sheet(catalog.get_sheet(cid)) for cid in course_ids}
    ranked = []
    for course_id in course_ids:
        name = catalog.get_course(course_id).name
        documents = [llm.Document(f"{name} — {c.section}", c.content) for c in chunks[course_id]]
        doc_vectors = cache.get_many(
            model,
            "document",
            [f"{d.title}\n{d.text}" for d in documents],
            lambda idx, docs=documents: llm.embed_documents(client, model, [docs[i] for i in idx]),
        )
        course_questions = [q for q in questions if q.course_id == course_id]
        query_vectors = cache.get_many(
            model,
            f"query:{task}",
            [q.text for q in course_questions],
            lambda idx, qs=course_questions: llm.embed_queries(
                client, model, [qs[i].text for i in idx], task
            ),
        )
        for question, vector in zip(course_questions, query_vectors, strict=True):
            ranked.append(rank_question(question, vector, chunks[course_id], doc_vectors))
    return ranked


def report(name: str, ranked: list[Ranked]) -> str:
    answerable = [r for r in ranked if r.question.answerable]
    unanswerable = [r for r in ranked if not r.question.answerable]
    n = len(answerable)
    hits = [sum(r.rank <= k for r in answerable) for k in (1, 3, 5)]
    mrr = sum(1 / r.rank for r in answerable) / n
    threshold, sorted_right = best_threshold(ranked)

    def spread(rows: list[Ranked]) -> str:
        values = [r.top_similarity for r in rows]
        return f"{min(values):.3f} / {statistics.median(values):.3f} / {max(values):.3f}"

    return (
        f"| {name} | {hits[0]} z {n} | {hits[1]} z {n} | {hits[2]} z {n} | {mrr:.3f} "
        f"| {spread(answerable)} | {spread(unanswerable)} "
        f"| {sorted_right} z {len(ranked)} (≥ {threshold:.3f}) |"
    )


def misses(name: str, ranked: list[Ranked]) -> list[str]:
    return [
        f"- {name} {r.question.id} (rank {r.rank}): expected "
        f"{sorted({e['section'] for e in r.question.evidence})}, top 3 {r.top_sections}"
        for r in ranked
        if r.question.answerable and r.rank > 1
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-cache", action="store_true", help="ask the API again")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set (environment or .env in the repo root)")
        return 1

    client = llm.make_client(api_key)
    catalog = Catalog.load(DEFAULT_MAIS_DATA_DIR)
    questions = load_questions()
    cache = Cache(CACHE_DIR, enabled=not args.no_cache)
    answerable = sum(q.answerable for q in questions)
    print(
        f"{len(questions)} questions ({answerable} answerable, {len(questions) - answerable}"
        f" 'Neviem') on {len({q.course_id for q in questions})} courses\n"
    )
    print(
        "| model / question sent as | hit@1 | hit@3 | hit@5 | MRR "
        "| top similarity, answerable (min / median / max) | top similarity, 'Neviem' "
        "| one threshold sorts right |"
    )
    print("|---|---|---|---|---|---|---|---|")
    all_misses = []
    for model in llm.EMBED_MODELS:
        for task in QUERY_TASKS:
            name = f"{model} / {task}"
            ranked = evaluate(client, model, task, catalog, questions, cache)
            print(report(name, ranked))
            all_misses += misses(name, ranked)
    print("\nAnswerable questions whose right chunk was not first:")
    print("\n".join(all_misses) or "- none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
