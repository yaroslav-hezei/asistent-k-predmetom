""" "Otázky komunity" and "Upozornenia" in the database: questions, answers, "Poďakovať",
notifications and the sidebar counts.

A question is open while it has no visible answer (status derived, never stored). Hidden questions
and answers (spam, hidden by a teacher) are never shown or counted. An answer reaches the
knowledge base through `app.knowledge`, in the same transaction that stores it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import Connection

from app import knowledge
from app.catalog import Catalog
from app.models.chat import Author
from app.models.community import (
    Badges,
    CommunityAnswer,
    Notification,
    NotificationAnswer,
    QuestionCounts,
    QuestionDetail,
    QuestionList,
    QuestionStatus,
    QuestionSummary,
    SimilarQuestion,
    Thanks,
)
from app.models.me import Study

LIST_LIMIT = 100
NOTIFICATIONS_LIMIT = 50


class NotAllowed(Exception):
    """The user may not do this (answer or thank their own text)."""


class BadSourceMessage(ValueError):
    """source_message_id is not an assistant message of the user's chat for that course."""


# Visible questions with their visible answer count; filtered by the caller's where clause.
QUESTIONS = """
with visible as (
    select q.id, q.course_id, q.text, p.nickname, p.role, q.created_at,
           (select count(*) from public.answers a
            where a.question_id = q.id and a.hidden_at is null) as answer_count,
           q.source_message_id is not null as from_assistant,
           q.author_id = %(user_id)s as mine,
           q.author_id
    from public.questions q
    join public.profiles p on p.id = q.author_id
    where q.hidden_at is null
)
select id, course_id, text, nickname, role, created_at, answer_count, from_assistant, mine
from visible
"""


# A notification about an answer a teacher hid as spam is neither shown nor counted.
NOT_ABOUT_HIDDEN_ANSWER = (
    "not exists (select 1 from public.answers h where h.id = n.answer_id"
    " and h.hidden_at is not null)"
)

# "Odpovede na overenie": visible, not yet verified answers (only students' answers are ever
# unverified) of visible questions in the courses the teacher teaches; one course when
# %(course_id)s is not null. Oldest first.
UNVERIFIED_ANSWERS = """
select a.id, a.text, p.nickname, p.role, a.created_at, q.id as question_id, q.text as question,
       q.course_id
from public.answers a
join public.questions q on q.id = a.question_id
join public.profiles p on p.id = a.author_id
join public.teacher_courses t on t.course_id = q.course_id and t.teacher_id = %(teacher_id)s
where a.verified_at is null and a.hidden_at is null and q.hidden_at is null
  and (%(course_id)s::text is null or q.course_id = %(course_id)s)
order by a.created_at
"""


@dataclass(frozen=True)
class NewAnswerResult:
    answer: CommunityAnswer
    chunk_id: UUID  # its knowledge chunk, still without a vector
    text_hash: str
    question_text: str
    course_id: str


def author(role: str, nickname: str) -> Author:
    return Author(kind="vyucujuci" if role == "vyucujuci" else "student", nickname=nickname)


def _summary(catalog: Catalog, row: Sequence[Any]) -> QuestionSummary | None:
    question_id, course_id, text, nickname, role, created_at, count, from_assistant, mine = row[:9]
    course = catalog.get_course(course_id)
    if course is None:  # every question's course is in the catalogue; skip if it ever is not
        return None
    return QuestionSummary(
        id=question_id,
        course=course,
        text=text,
        author=author(role, nickname),
        created_at=created_at,
        status="answered" if count > 0 else "open",
        answer_count=count,
        from_assistant=from_assistant,
        mine=mine,
    )


def create_question(
    conn: Connection,
    *,
    user_id: str,
    course_id: str,
    text: str,
    source_message_id: UUID | None,
) -> UUID:
    """Publish a question. Raises BadSourceMessage for a source message that is not an assistant
    message in one of the user's chats about the same course."""
    if source_message_id is not None:
        row = conn.execute(
            "select 1 from public.chat_messages m join public.chats c on c.id = m.chat_id"
            " where m.id = %s and m.role = 'assistant' and c.user_id = %s and c.course_id = %s",
            [source_message_id, user_id, course_id],
        ).fetchone()
        if row is None:
            raise BadSourceMessage("The message is not an assistant answer in your chat.")
    row = conn.execute(
        "insert into public.questions (course_id, author_id, text, source_message_id)"
        " values (%s, %s, %s, %s) returning id",
        [course_id, user_id, text, source_message_id],
    ).fetchone()
    assert row is not None
    return row[0]


def set_question_vector(
    conn: Connection, question_id: UUID, vector: Sequence[float], model: str
) -> None:
    conn.execute(
        "update public.questions set embedding = %s::extensions.vector, embed_model = %s"
        " where id = %s",
        [knowledge.vector_literal(vector), model, question_id],
    )


def similar_questions(
    conn: Connection,
    catalog: Catalog,
    *,
    user_id: str,
    course_id: str,
    vector: Sequence[float],
    model: str,
    limit: int,
    min_similarity: float,
) -> list[SimilarQuestion]:
    """Visible questions of the course with a vector of `model`, the most similar first."""
    rows = conn.execute(
        "select q.id, q.course_id, q.text, p.nickname, p.role, q.created_at,"
        " (select count(*) from public.answers a"
        "  where a.question_id = q.id and a.hidden_at is null),"
        " q.source_message_id is not null, q.author_id = %(user_id)s,"
        " 1 - (q.embedding operator(extensions.<=>) %(vector)s::extensions.vector)"
        " from public.questions q join public.profiles p on p.id = q.author_id"
        " where q.hidden_at is null and q.course_id = %(course_id)s and q.embed_model = %(model)s"
        " order by q.embedding operator(extensions.<=>) %(vector)s::extensions.vector"
        " limit %(limit)s",
        {
            "user_id": user_id,
            "vector": knowledge.vector_literal(vector),
            "course_id": course_id,
            "model": model,
            "limit": limit,
        },
    ).fetchall()
    similar = []
    for row in rows:
        summary = _summary(catalog, row)
        if summary is not None and row[9] >= min_similarity:
            similar.append(SimilarQuestion(**summary.model_dump(), similarity=round(row[9], 4)))
    return similar


def plan_course_ids(catalog: Catalog, study: Study | None) -> list[str]:
    """The courses of the user's study plan ("Moje predmety"); none when it is not set."""
    if study is None:
        return []
    plan = catalog.program_courses(study.program_id, study.year, study.semester) or []
    return sorted({item.course.id for item in plan})


def my_course_ids(
    conn: Connection, catalog: Catalog, *, user_id: str, study: Study | None
) -> list[str]:
    """The courses of "Všetky moje predmety": the user's study plan and the courses they teach."""
    taught = conn.execute(
        "select course_id from public.teacher_courses where teacher_id = %s", [user_id]
    ).fetchall()
    return sorted(set(plan_course_ids(catalog, study)) | {row[0] for row in taught})


def list_questions(
    conn: Connection,
    catalog: Catalog,
    *,
    user_id: str,
    course_ids: Sequence[str],
    status: QuestionStatus,
) -> QuestionList:
    """One tab of the questions of these courses, newest first, and the counts of both tabs."""
    condition = "answer_count = 0" if status == "open" else "answer_count > 0"
    ids = list(course_ids)
    rows = conn.execute(
        QUESTIONS + f" where course_id = any(%(ids)s) and {condition}"
        " order by created_at desc limit %(limit)s",
        {"user_id": user_id, "ids": ids, "limit": LIST_LIMIT},
    ).fetchall()
    open_count, answered = conn.execute(
        "select count(*) filter (where answer_count = 0), count(*) filter (where answer_count > 0)"
        " from (" + QUESTIONS + " where course_id = any(%(ids)s)) counted",
        {"user_id": user_id, "ids": ids},
    ).fetchone()
    items = [s for s in (_summary(catalog, row) for row in rows) if s is not None]
    return QuestionList(items=items, counts=QuestionCounts(open=open_count, answered=answered))


def get_question(
    conn: Connection, catalog: Catalog, *, user_id: str, question_id: UUID
) -> QuestionDetail | None:
    """The visible question with its visible answers; None when missing or hidden."""
    row = conn.execute(
        QUESTIONS + " where id = %(question_id)s",
        {"user_id": user_id, "question_id": question_id},
    ).fetchone()
    summary = _summary(catalog, row) if row else None
    if summary is None:
        return None
    rows = conn.execute(
        "select a.id, a.text, p.nickname, p.role, a.verified_at is not null, a.created_at,"
        " (select count(*) from public.answer_thanks t where t.answer_id = a.id),"
        " exists (select 1 from public.answer_thanks t"
        "  where t.answer_id = a.id and t.user_id = %(user_id)s),"
        " a.author_id = %(user_id)s"
        " from public.answers a join public.profiles p on p.id = a.author_id"
        " where a.question_id = %(question_id)s and a.hidden_at is null"
        " order by a.verified_at is null, 7 desc, a.created_at",
        {"user_id": user_id, "question_id": question_id},
    ).fetchall()
    answers = [
        CommunityAnswer(
            id=answer_id,
            text=text,
            author=author(role, nickname),
            verified=verified,
            created_at=created_at,
            thanks=thanks,
            thanked_by_me=thanked,
            mine=mine,
        )
        for answer_id, text, nickname, role, verified, created_at, thanks, thanked, mine in rows
    ]
    return QuestionDetail(**summary.model_dump(), answers=answers)


def add_answer(
    conn: Connection, *, user_id: str, question_id: UUID, text: str, now: datetime
) -> NewAnswerResult | None:
    """Store an answer, its knowledge chunk (no vector yet) and a notification for the asker, in
    the caller's transaction. A teacher of the course answers verified. None when the question
    is missing or hidden; NotAllowed for the asker's own question."""
    row = conn.execute(
        "select q.course_id, q.author_id, q.text from public.questions q"
        " where q.id = %s and q.hidden_at is null",
        [question_id],
    ).fetchone()
    if row is None:
        return None
    course_id, asker_id, question_text = row
    if str(asker_id) == str(user_id):
        raise NotAllowed("You cannot answer your own question.")
    nickname, role = conn.execute(
        "select nickname, role from public.profiles where id = %s", [user_id]
    ).fetchone()
    teaches = (
        conn.execute(
            "select 1 from public.teacher_courses where teacher_id = %s and course_id = %s",
            [user_id, course_id],
        ).fetchone()
        is not None
    )
    answer_id, created_at = conn.execute(
        "insert into public.answers"
        " (question_id, author_id, text, kind, verified_at, verified_by, created_at)"
        " values (%s, %s, %s, %s, %s, %s, %s) returning id, created_at",
        [
            question_id,
            user_id,
            text,
            "teacher" if teaches else "student",
            now if teaches else None,
            user_id if teaches else None,
            now,
        ],
    ).fetchone()
    chunk_id, text_hash = knowledge.add_answer_chunk(
        conn, course_id=course_id, answer_id=answer_id, text=text
    )
    conn.execute(
        "insert into public.notifications (user_id, type, question_id, answer_id, created_at)"
        " values (%s, 'question_answered', %s, %s, %s)",
        [asker_id, question_id, answer_id, now],
    )
    answer = CommunityAnswer(
        id=answer_id,
        text=text,
        author=author(role, nickname),
        verified=teaches,
        created_at=created_at,
        thanks=0,
        thanked_by_me=False,
        mine=True,
    )
    return NewAnswerResult(answer, chunk_id, text_hash, question_text, course_id)


def thank(conn: Connection, *, user_id: str, answer_id: UUID) -> Thanks | None:
    """'Poďakovať' once per user and answer (again is no error). None when the answer is missing
    or hidden; NotAllowed for the user's own answer."""
    row = conn.execute(
        "select a.author_id from public.answers a join public.questions q on q.id = a.question_id"
        " where a.id = %s and a.hidden_at is null and q.hidden_at is null",
        [answer_id],
    ).fetchone()
    if row is None:
        return None
    if str(row[0]) == str(user_id):
        raise NotAllowed("You cannot thank your own answer.")
    conn.execute(
        "insert into public.answer_thanks (answer_id, user_id) values (%s, %s)"
        " on conflict do nothing",
        [answer_id, user_id],
    )
    count = conn.execute(
        "select count(*) from public.answer_thanks where answer_id = %s", [answer_id]
    ).fetchone()[0]
    return Thanks(thanks=count, thanked_by_me=True)


def list_notifications(conn: Connection, catalog: Catalog, *, user_id: str) -> list[Notification]:
    rows = conn.execute(
        "select n.id, n.type, n.question_id, n.created_at, n.read_at is not null,"
        " a.id, p.nickname, p.role, a.text, a.verified_at is not null,"
        " exists (select 1 from public.answer_thanks t"
        "  where t.answer_id = a.id and t.user_id = %(user_id)s),"
        " c.id"
        " from public.notifications n"
        " join public.questions q on q.id = n.question_id and q.hidden_at is null"
        " left join public.answers a on a.id = n.answer_id and a.hidden_at is null"
        " left join public.profiles p on p.id = a.author_id"
        " left join public.chat_messages m on m.id = q.source_message_id"
        " left join public.chats c on c.id = m.chat_id and c.user_id = %(user_id)s"
        " where n.user_id = %(user_id)s and "
        + NOT_ABOUT_HIDDEN_ANSWER
        + " order by n.created_at desc limit %(limit)s",
        {"user_id": user_id, "limit": NOTIFICATIONS_LIMIT},
    ).fetchall()
    question_ids = list({row[2] for row in rows})
    questions = {}
    if question_ids:
        for row in conn.execute(
            QUESTIONS + " where id = any(%(ids)s)", {"user_id": user_id, "ids": question_ids}
        ).fetchall():
            summary = _summary(catalog, row)
            if summary is not None:
                questions[summary.id] = summary
    notifications = []
    for row in rows:
        notification_id, kind, question_id, created_at, read = row[:5]
        answer_id, nickname, role, text, verified, thanked, chat_id = row[5:]
        question = questions.get(question_id)
        if question is None:
            continue
        answer = None
        if answer_id is not None:
            answer = NotificationAnswer(
                id=answer_id,
                text=text,
                author=author(role, nickname),
                verified=verified,
                thanked_by_me=thanked,
            )
        notifications.append(
            Notification(
                id=notification_id,
                type=kind,
                question=question,
                answer=answer,
                chat_id=chat_id,
                created_at=created_at,
                read=read,
            )
        )
    return notifications


def mark_read(conn: Connection, *, user_id: str, ids: list[UUID] | None, now: datetime) -> int:
    """Mark the user's notifications as read (all when `ids` is None); returns how many."""
    if ids is None:
        cursor = conn.execute(
            "update public.notifications set read_at = %s where user_id = %s and read_at is null",
            [now, user_id],
        )
    else:
        cursor = conn.execute(
            "update public.notifications set read_at = %s"
            " where user_id = %s and read_at is null and id = any(%s)",
            [now, user_id, ids],
        )
    return cursor.rowcount


def badges(conn: Connection, catalog: Catalog, *, user_id: str, study: Study | None) -> Badges:
    unread = conn.execute(
        "select count(*) from public.notifications n"
        " join public.questions q on q.id = n.question_id and q.hidden_at is null"
        " where n.user_id = %s and n.read_at is null and " + NOT_ABOUT_HIDDEN_ANSWER,
        [user_id],
    ).fetchone()[0]
    open_questions = 0
    course_ids = plan_course_ids(catalog, study)
    if course_ids:
        open_questions = conn.execute(
            "select count(*) from (" + QUESTIONS + " where course_id = any(%(ids)s)"
            " and answer_count = 0 and not mine) counted",
            {"user_id": user_id, "ids": course_ids},
        ).fetchone()[0]
    return Badges(
        unread_notifications=unread,
        open_questions=open_questions,
        unverified_answers=unverified_count(conn, user_id=user_id),
    )


def unverified_count(conn: Connection, *, user_id: str) -> int:
    """Visible unverified answers in the courses the user teaches (0 for a student)."""
    return conn.execute(
        "select count(*) from (" + UNVERIFIED_ANSWERS + ") pending",
        {"teacher_id": user_id, "course_id": None},
    ).fetchone()[0]
