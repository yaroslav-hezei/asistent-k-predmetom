"""The knowledge base (`public.knowledge_chunks`): the texts the assistant searches and quotes.

Every write to the knowledge base goes through this module: the MAIS sheets and the vectors now;
answers from "Otázky komunity", the teacher's notes and the invalidation of cached answers later.
No other code writes the table.
"""

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from psycopg import Connection

from app.chunking import Chunk
from app.llm import Document

# Only these sources get vectors: the answering model reads the whole sheet, so sheet chunks need
# none (10,981 of them would take 11 days of the free tier's 1,000 texts a day).
EMBEDDED_SOURCES = ("answer", "course_note")

# Chunks without a vector of `model` (none yet, another model's, or cleared after a text change).
SELECT_PENDING = """
select k.id, c.name, k.section, k.content, k.content_hash
from public.knowledge_chunks k
join public.courses c on c.id = k.course_id
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
            Document(title=f"{course} — {section}" if section else course, text=content)
            for _, course, section, content, _ in rows
        ]
        vectors = embed(documents)
        if len(vectors) != len(rows):
            raise RuntimeError(f"{len(vectors)} vectors for {len(rows)} chunks")
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(
                UPDATE_EMBEDDING,
                [
                    [_vector_literal(vector), model, chunk_id, chunk_hash]
                    for (chunk_id, _, _, _, chunk_hash), vector in zip(rows, vectors, strict=True)
                ],
            )
        stored += len(rows)
        if on_batch is not None:
            on_batch(stored)
    return stored


def _vector_literal(vector: Sequence[float]) -> str:
    """pgvector's text form: [0.1,0.2,...]."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"
