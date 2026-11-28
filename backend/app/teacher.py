"""The teacher's work in the database: verify a student's answer, hide spam, the course's
"Aktuálna informácia k predmetu".

A teacher acts only in the courses assigned to them (`public.teacher_courses`). Hiding keeps the
row (hidden_at / hidden_by): a hidden question or answer is never shown, counted, notified or
used by the assistant. The note is written through `app.knowledge`, the only writer of the
knowledge base.
"""

from datetime import datetime
from uuid import UUID

from psycopg import Connection

from app import knowledge
from app.catalog import Catalog
from app.community import UNVERIFIED_ANSWERS, author
from app.models.chat import QuestionRef
from app.models.teacher import AnswerToVerify, CourseNote, TeacherCourse, Verification


class NotTeacher(Exception):
    """The user does not teach the course."""


def teaches(conn: Connection, user_id: str, course_id: str) -> bool:
    return (
        conn.execute(
            "select 1 from public.teacher_courses where teacher_id = %s and course_id = %s",
            [user_id, course_id],
        ).fetchone()
        is not None
    )


def teacher_courses(conn: Connection, catalog: Catalog, *, user_id: str) -> list[TeacherCourse]:
    """The user's courses with their unverified answers, by course name; empty for a student."""
    course_ids = [
        row[0]
        for row in conn.execute(
            "select course_id from public.teacher_courses where teacher_id = %s", [user_id]
        ).fetchall()
    ]
    pending: dict[str, int] = {}
    for row in conn.execute(
        UNVERIFIED_ANSWERS, {"teacher_id": user_id, "course_id": None}
    ).fetchall():
        pending[row[7]] = pending.get(row[7], 0) + 1
    courses = [
        TeacherCourse(course=course, unverified_answers=pending.get(course_id, 0))
        for course_id in course_ids
        if (course := catalog.get_course(course_id)) is not None
    ]
    return sorted(courses, key=lambda item: item.course.name)


def verification(
    conn: Connection, catalog: Catalog, *, user_id: str, course_id: str
) -> Verification:
    """The Overovanie screen of one course. Raises NotTeacher; the course must exist."""
    if not teaches(conn, user_id, course_id):
        raise NotTeacher(course_id)
    course = catalog.get_course(course_id)
    assert course is not None
    rows = conn.execute(
        UNVERIFIED_ANSWERS, {"teacher_id": user_id, "course_id": course_id}
    ).fetchall()
    answers = [
        AnswerToVerify(
            id=answer_id,
            question=QuestionRef(id=question_id, text=question),
            text=text,
            author=author(role, nickname),
            created_at=created_at,
        )
        for answer_id, text, nickname, role, created_at, question_id, question, _ in rows
    ]
    return Verification(course=course, note=course_note(conn, course_id), answers=answers)


def course_note(conn: Connection, course_id: str) -> CourseNote | None:
    note = knowledge.get_course_note(conn, course_id)
    if note is None:
        return None
    return CourseNote(
        text=note.text, author=author(note.role, note.nickname), updated_at=note.updated_at
    )


def save_note(
    conn: Connection, *, user_id: str, course_id: str, text: str, now: datetime
) -> CourseNote:
    """Store the course's note (the assistant uses it from the next question). Raises
    NotTeacher."""
    if not teaches(conn, user_id, course_id):
        raise NotTeacher(course_id)
    knowledge.set_course_note(conn, course_id=course_id, author_id=user_id, text=text, now=now)
    note = course_note(conn, course_id)
    assert note is not None
    return note


def delete_note(conn: Connection, *, user_id: str, course_id: str) -> None:
    """Remove the course's note (no note is no error). Raises NotTeacher."""
    if not teaches(conn, user_id, course_id):
        raise NotTeacher(course_id)
    knowledge.delete_course_note(conn, course_id)


def _answer_course(conn: Connection, answer_id: UUID) -> str | None:
    """The course of a visible answer of a visible question; None when missing or hidden."""
    row = conn.execute(
        "select q.course_id from public.answers a join public.questions q on q.id = a.question_id"
        " where a.id = %s and a.hidden_at is null and q.hidden_at is null",
        [answer_id],
    ).fetchone()
    return row[0] if row else None


def verify_answer(conn: Connection, *, user_id: str, answer_id: UUID, now: datetime) -> bool:
    """'Overiť': mark a student's answer as verified (again is no error). False when the answer
    is missing or hidden; raises NotTeacher."""
    course_id = _answer_course(conn, answer_id)
    if course_id is None:
        return False
    if not teaches(conn, user_id, course_id):
        raise NotTeacher(course_id)
    conn.execute(
        "update public.answers set verified_at = %s, verified_by = %s"
        " where id = %s and verified_at is null",
        [now, user_id, answer_id],
    )
    return True


def hide_answer(conn: Connection, *, user_id: str, answer_id: UUID, now: datetime) -> bool:
    """'Zmazať': hide an answer as spam. False when it is missing or already hidden; raises
    NotTeacher."""
    course_id = _answer_course(conn, answer_id)
    if course_id is None:
        return False
    if not teaches(conn, user_id, course_id):
        raise NotTeacher(course_id)
    conn.execute(
        "update public.answers set hidden_at = %s, hidden_by = %s where id = %s",
        [now, user_id, answer_id],
    )
    return True


def hide_question(conn: Connection, *, user_id: str, question_id: UUID, now: datetime) -> bool:
    """Hide a question as spam, and with it its answers. False when it is missing or already
    hidden; raises NotTeacher."""
    row = conn.execute(
        "select course_id from public.questions where id = %s and hidden_at is null",
        [question_id],
    ).fetchone()
    if row is None:
        return False
    if not teaches(conn, user_id, row[0]):
        raise NotTeacher(row[0])
    conn.execute(
        "update public.questions set hidden_at = %s, hidden_by = %s where id = %s",
        [now, user_id, question_id],
    )
    return True
