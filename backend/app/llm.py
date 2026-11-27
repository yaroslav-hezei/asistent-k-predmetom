"""The Gemini models: every model name lives in this file (one place to switch).

Embeddings (the knowledge base) and the model that writes the answers (`generate_json`).

Two embedding models are candidates until the evaluation picks one (scripts/compare_embeddings.py).
They differ in how they are called, which this module hides:

- gemini-embedding-001 takes a `task_type` (document vs question) and returns one vector per text,
  but vectors shorter than 3072 numbers are not normalized: we normalize them here.
- gemini-embedding-2 has no `task_type`: the task is written into the text itself
  ("task: question answering | query: ...", "title: ... | text: ..."). Given a plain list of texts
  it returns ONE vector for all of them, so every text is sent as its own `Content`. Its vectors are
  normalized by the model.

The API key comes from GEMINI_API_KEY and is passed to the client explicitly.
"""

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from google import genai
from google.genai import types

EMBED_DIMENSIONS = 768  # = public.knowledge_chunks.embedding vector(768)
EMBED_BATCH_SIZE = 50  # texts per request

GEMINI_EMBEDDING_001 = "gemini-embedding-001"
GEMINI_EMBEDDING_2 = "gemini-embedding-2"
EMBED_MODELS = (GEMINI_EMBEDDING_001, GEMINI_EMBEDDING_2)

# How a question is sent. 001: its task_type; 2: the task name in the text prefix.
QueryTask = Literal["question_answering", "retrieval_query"]

# The model of the knowledge base, chosen on the evaluation questions (compare_embeddings.py).
# Changing it means embedding every chunk again: scripts/embed_chunks.py does it.
EMBED_MODEL = GEMINI_EMBEDDING_001
EMBED_QUERY_TASK: QueryTask = "question_answering"
QUERY_TASK_TYPE = {"question_answering": "QUESTION_ANSWERING", "retrieval_query": "RETRIEVAL_QUERY"}
QUERY_TASK_PREFIX = {"question_answering": "question answering", "retrieval_query": "search result"}

# The model that answers the questions; on the free tier 15 requests a minute, 500 a day.
ANSWER_MODEL = "gemini-3.5-flash-lite"
ANSWER_MAX_OUTPUT_TOKENS = 400

# Scripts: rate limits (429) and server errors are retried with a growing pause.
RETRY = types.HttpRetryOptions(
    attempts=6, initial_delay=2.0, max_delay=60.0, http_status_codes=[429, 500, 503]
)
# The API, where a student waits for the answer: a few short retries, then the caller gives up.
INTERACTIVE_RETRY = types.HttpRetryOptions(
    attempts=3, initial_delay=1.0, max_delay=8.0, http_status_codes=[429, 500, 503]
)
INTERACTIVE_TIMEOUT_MS = 30_000


@dataclass(frozen=True)
class Document:
    title: str  # e.g. "Základy algoritmizácie a programovania — Priebežné hodnotenie (PH)"
    text: str


@dataclass(frozen=True)
class Generation:
    data: dict[str, Any]  # the JSON object the model returned
    prompt_tokens: int | None
    output_tokens: int | None


def make_client(api_key: str, *, interactive: bool = False) -> genai.Client:
    """`interactive`: for the running API (short retries, 30 s timeout); scripts wait longer."""
    options = (
        types.HttpOptions(retry_options=INTERACTIVE_RETRY, timeout=INTERACTIVE_TIMEOUT_MS)
        if interactive
        else types.HttpOptions(retry_options=RETRY)
    )
    return genai.Client(api_key=api_key, http_options=options)


def generate_json(
    client: genai.Client, system: str, prompt: str, schema: dict[str, Any]
) -> Generation:
    """Ask the answering model for one JSON object of `schema`. Deterministic (temperature 0),
    minimal thinking (the model has no thinking budget 0), capped output. Raises the SDK's
    APIError when the request fails and ValueError when the reply is not a JSON object."""
    response = client.models.generate_content(
        model=ANSWER_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            max_output_tokens=ANSWER_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
            response_json_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
        ),
    )
    data = json.loads(response.text or "")
    if not isinstance(data, dict):
        raise ValueError("the model did not return a JSON object")
    usage = response.usage_metadata
    return Generation(
        data=data,
        prompt_tokens=usage.prompt_token_count if usage else None,
        output_tokens=usage.candidates_token_count if usage else None,
    )


def embed_documents(
    client: genai.Client, model: str, documents: Sequence[Document]
) -> list[list[float]]:
    """One normalized vector per document, in order."""
    if model == GEMINI_EMBEDDING_001:
        texts = [f"{doc.title}\n{doc.text}" for doc in documents]
        config = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT", output_dimensionality=EMBED_DIMENSIONS
        )
    elif model == GEMINI_EMBEDDING_2:
        texts = [f"title: {doc.title} | text: {doc.text}" for doc in documents]
        config = types.EmbedContentConfig(output_dimensionality=EMBED_DIMENSIONS)
    else:
        raise ValueError(f"unknown embedding model {model!r}")
    return _embed(client, model, texts, config)


def embed_queries(
    client: genai.Client,
    model: str,
    questions: Sequence[str],
    task: QueryTask = "question_answering",
) -> list[list[float]]:
    """One normalized vector per question, in order."""
    if model == GEMINI_EMBEDDING_001:
        texts = list(questions)
        config = types.EmbedContentConfig(
            task_type=QUERY_TASK_TYPE[task], output_dimensionality=EMBED_DIMENSIONS
        )
    elif model == GEMINI_EMBEDDING_2:
        texts = [f"task: {QUERY_TASK_PREFIX[task]} | query: {q}" for q in questions]
        config = types.EmbedContentConfig(output_dimensionality=EMBED_DIMENSIONS)
    else:
        raise ValueError(f"unknown embedding model {model!r}")
    return _embed(client, model, texts, config)


def normalize(vector: Sequence[float]) -> list[float]:
    length = math.sqrt(sum(v * v for v in vector))
    if length == 0:
        raise ValueError("cannot normalize a zero vector")
    return [v / length for v in vector]


def _embed(
    client: genai.Client, model: str, texts: list[str], config: types.EmbedContentConfig
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        # every text as its own Content: gemini-embedding-2 merges a plain list into one vector
        contents = [types.Content(parts=[types.Part(text=text)]) for text in batch]
        response = client.models.embed_content(model=model, contents=contents, config=config)
        embeddings = response.embeddings or []
        if len(embeddings) != len(batch):
            raise RuntimeError(f"{model}: {len(embeddings)} vectors for {len(batch)} texts")
        for embedding in embeddings:
            values = embedding.values or []
            if len(values) != EMBED_DIMENSIONS:
                raise RuntimeError(f"{model}: a vector of {len(values)} numbers")
            vectors.append(normalize(values))
    return vectors
