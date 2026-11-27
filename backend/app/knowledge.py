"""The knowledge base (`public.knowledge_chunks`): the texts the assistant searches and quotes.

Every write to the knowledge base goes through this module: the MAIS sheets, the answers from
"Otázky komunity" and the vectors; the teacher's notes and the invalidation of cached answers later.
No other code writes the table.
"""

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from psycopg import Connection

from app.chunking import Chunk
from app.llm import Document

# Only these sources get vectors: the answering model reads the whole sheet, so sheet chunks need
# none (10,981 of them would take 11 days of the free tier's 1,000 texts a day).
EMBEDDED_SOURCES = ("answer", "course_note")

# Chunks without a vector of `model` (none yet, another model's, or cleared after a text change).
SELECT_PENDING = """
select k.id, c.name, k.section, q.text, k.content, k.content_hash
from public.knowledge_chunks k
join public.courses c on c.id = k.course_id
left join public.answers a on a.id = k.answer_id
left join public.questions q on q.id = a.question_id
where k.embed_model is distinct from %s and k.source_type = any(%s)
order by k.course_id, k.source_type, k.section, k.chunk_index
limit %s
"""

COUNT_PENDING = """
select count(*) from public.knowledge_chunks
where embed_model is distinct from %s and source_type = any(%s)
"""

# The hash check skips a chunk whose text changed while its vector was being computed.
UPDATE_EMBEDDING = """
update public.knowledge_chunks
set embedding = %s::extensions.vector, embed_model = %s
where id = %s and content_hash = %s
"""

Embedder = Callable[[Sequence[Document]], list[list[float]]]

SELECT_SHEET_CHUNKS = """
select id, course_id, section, chunk_index, content_hash
from public.knowledge_chunks
where source_type = 'sheet' and course_id = any(%s)
"""

INSERT_SHEET_CHUNK = """
insert into public.knowledge_chunks
    (course_id, source_type, section, chunk_index, content, content_hash)
values (%s, 'sheet', %s, %s, %s, %s)
"""

# A changed text loses its embedding: the old vector describes the old text.
UPDATE_CHUNK_TEXT = """
update public.knowledge_chunks
set content = %s, content_hash = %s, embedding = null, embed_model = null
where id = %s
"""

DELETE_CHUNK = "delete from public.knowledge_chunks where id = %s"


@dataclass(frozen=True)
class SyncCounts:
    inserted: int
    updated: int  # the text changed: new text, embedding cleared
    deleted: int
    unchanged: int


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sync_sheet_chunks(
    conn: Connection, chunks_by_course: Mapping[str, Sequence[Chunk]]
) -> SyncCounts:
    """Make the stored sheet chunks of these courses equal to `chunks_by_course`, in one
    transaction.

    New chunks are stored without an embedding; a chunk whose text changed gets the new text and
    loses its embedding (the embedding step fills both again); chunks the sheet no longer has are
    deleted. Unchanged chunks keep their embedding and are not written. Courses missing from the
    mapping are not touched. The courses must exist in `public.courses`.
    """
    wanted = {
        (course_id, chunk.section, chunk.chunk_index): chunk
        for course_id, chunks in chunks_by_course.items()
        for chunk in chunks
    }
    inserts, updates, deletes = [], [], []
    unchanged = 0
    with conn.transaction():
        stored = conn.execute(SELECT_SHEET_CHUNKS, [list(chunks_by_course)]).fetchall()
        stored_keys = set()
        for chunk_id, course_id, section, chunk_index, stored_hash in stored:
            key = (course_id, section, chunk_index)
            stored_keys.add(key)
            chunk = wanted.get(key)
            if chunk is None:
                deletes.append([chunk_id])
            elif content_hash(chunk.content) != stored_hash:
                updates.append([chunk.content, content_hash(chunk.content), chunk_id])
            else:
                unchanged += 1
        for (course_id, section, chunk_index), chunk in wanted.items():
            if (course_id, section, chunk_index) not in stored_keys:
                inserts.append(
                    [course_id, section, chunk_index, chunk.content, content_hash(chunk.content)]
                )
        with conn.cursor() as cur:
            if deletes:
                cur.executemany(DELETE_CHUNK, deletes)
            if updates:
                cur.executemany(UPDATE_CHUNK_TEXT, updates)
            if inserts:
                cur.executemany(INSERT_SHEET_CHUNK, inserts)
    return SyncCounts(
        inserted=len(inserts), updated=len(updates), deleted=len(deletes), unchanged=unchanged
    )


def count_pending(
    conn: Connection, model: str, source_types: Sequence[str] = EMBEDDED_SOURCES
) -> int:
    """Chunks of `source_types` that have no vector of `model`."""
    return conn.execute(COUNT_PENDING, [model, list(source_types)]).fetchone()[0]


def embed_pending_chunks(
    conn: Connection,
    embed: Embedder,
    model: str,
    *,
    batch_size: int = 100,
    limit: int | None = None,
    on_batch: Callable[[int], None] | None = None,
    source_types: Sequence[str] = EMBEDDED_SOURCES,
) -> int:
    """Give every chunk without a vector of `model` its vector; return how many were stored.

    `embed` turns documents (title = course name and section, text = the chunk) into vectors of
    `model`. Works in batches, each committed on its own, so an interrupted run (a daily quota
    reached, a network error) keeps what it stored and the next run continues where it stopped.
    `conn` must be in autocommit mode for that. `limit` caps the chunks of this run.
    """
    if not conn.autocommit:
        raise ValueError("embed_pending_chunks needs a connection in autocommit mode")
    stored = 0
    while limit is None or stored < limit:
        size = batch_size if limit is None else min(batch_size, limit - stored)
        rows = conn.execute(SELECT_PENDING, [model, list(source_types), size]).fetchall()
        if not rows:
            break
        documents = [
            Document(title=chunk_title(course, section, question), text=content)
            for _, course, section, question, content, _ in rows
        ]
        vectors = embed(documents)
        if len(vectors) != len(rows):
            raise RuntimeError(f"{len(vectors)} vectors for {len(rows)} chunks")
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(
                UPDATE_EMBEDDING,
                [
                    [vector_literal(vector), model, chunk_id, chunk_hash]
                    for (chunk_id, *_, chunk_hash), vector in zip(rows, vectors, strict=True)
                ],
            )
        stored += len(rows)
        if on_batch is not None:
            on_batch(stored)
    return stored


def vector_literal(vector: Sequence[float]) -> str:
    """pgvector's text form: [0.1,0.2,...]."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


INSERT_ANSWER_CHUNK = """
insert into public.knowledge_chunks (course_id, source_type, answer_id, content, content_hash)
values (%s, 'answer', %s, %s, %s)
returning id
"""

HAS_ANSWER_VECTORS = """
select exists (
    select 1 from public.knowledge_chunks
    where course_id = %s and source_type = 'answer' and embed_model = %s
)
"""

# Visible answers of the course, the most similar to the question first.
SEARCH_ANSWERS = """
select a.id, q.id, q.text, a.text, p.role, p.nickname, a.verified_at is not null, a.created_at,
       1 - (k.embedding operator(extensions.<=>) %(vector)s::extensions.vector) as similarity
from public.knowledge_chunks k
join public.answers a on a.id = k.answer_id
join public.questions q on q.id = a.question_id
join public.profiles p on p.id = a.author_id
where k.source_type = 'answer' and k.course_id = %(course_id)s and k.embed_model = %(model)s
  and a.hidden_at is null and q.hidden_at is null
order by k.embedding operator(extensions.<=>) %(vector)s::extensions.vector
limit %(limit)s
"""


@dataclass(frozen=True)
class CommunitySource:
    """A community answer the assistant may use, with what is shown about it."""

    answer_id: UUID
    question_id: UUID
    question_text: str
    text: str
    role: str  # the author's role: "student" | "vyucujuci"
    nickname: str
    verified: bool
    created_at: datetime
    similarity: float


def chunk_title(course_name: str, section: str | None, question_text: str | None) -> str:
    """The title a chunk is embedded with: the course and the sheet section, or the course and
    the question an answer answers (an answer like "v tíme po troch" means nothing alone)."""
    detail = section or question_text
    return f"{course_name} — {detail}" if detail else course_name


def add_answer_chunk(
    conn: Connection, *, course_id: str, answer_id: UUID, text: str
) -> tuple[UUID, str]:
    """A community answer as a knowledge chunk, without a vector yet; returns the chunk id and the
    text hash for `store_vector`. Run it in the transaction that stores the answer, so the
    assistant can use the answer as soon as it exists."""
    text_hash = content_hash(text)
    row = conn.execute(INSERT_ANSWER_CHUNK, [course_id, answer_id, text, text_hash]).fetchone()
    assert row is not None
    return row[0], text_hash


def store_vector(
    conn: Connection, chunk_id: UUID, text_hash: str, vector: Sequence[float], model: str
) -> bool:
    """Store a chunk's vector; False when the chunk is gone or its text changed meanwhile."""
    cursor = conn.execute(UPDATE_EMBEDDING, [vector_literal(vector), model, chunk_id, text_hash])
    return cursor.rowcount == 1


def has_answer_vectors(conn: Connection, course_id: str, model: str) -> bool:
    """Whether the course has community answers with vectors of `model` (else /ask need not
    embed the question at all)."""
    return conn.execute(HAS_ANSWER_VECTORS, [course_id, model]).fetchone()[0]


def search_answers(
    conn: Connection,
    course_id: str,
    vector: Sequence[float],
    model: str,
    *,
    limit: int = 5,
    min_similarity: float = 0.0,
) -> list[CommunitySource]:
    """The visible community answers of the course most similar to `vector` (a question)."""
    rows = conn.execute(
        SEARCH_ANSWERS,
        {"vector": vector_literal(vector), "course_id": course_id, "model": model, "limit": limit},
    ).fetchall()
    return [CommunitySource(*row) for row in rows if row[-1] >= min_similarity]
