"""The knowledge base (`public.knowledge_chunks`): the texts the assistant searches and quotes.

Every write to the knowledge base goes through this module: the MAIS sheets now; answers from
"Otázky komunity" and the teacher's notes later. Embeddings and the invalidation of cached answers
will live here too, so no other code writes the table.
"""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from psycopg import Connection

from app.chunking import Chunk

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
