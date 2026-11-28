"""The teacher's "Overovanie": verify students' answers, hide spam, "Aktuálna informácia k
predmetu". Everything here is allowed only to a teacher of the course in question.

"Pridať odpoveď" (the teacher's own verified answer) is `POST /questions/{question_id}/answers`.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import teacher
from app.auth import CurrentUserId
from app.db import Pool
from app.models.teacher import CourseNote, NewCourseNote, TeacherCourse, Verification
from app.routers.catalog import CatalogDep
from app.routers.community import (
    ANSWER_NOT_FOUND,
    COURSE_NOT_FOUND,
    QUESTION_NOT_FOUND,
    _profile,
)
from app.routers.me import NO_PROFILE, NOT_LOGGED_IN

router = APIRouter(tags=["teacher"])

NOT_TEACHER = "You do not teach this course."
TEACHER_ONLY = {403: {"description": f"The account has no profile, or: {NOT_TEACHER}"}}


def _forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, NOT_TEACHER)


@router.get(
    "/teacher/courses",
    summary="The courses the user verifies, with their unverified answers",
    description="Sorted by course name; empty for a student.",
    responses={**NOT_LOGGED_IN, **NO_PROFILE},
)
def courses(user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> list[TeacherCourse]:
    with pool.connection() as conn:
        _profile(conn, user_id)
        return teacher.teacher_courses(conn, catalog, user_id=user_id)


@router.get(
    "/teacher/courses/{course_id}",
    summary="The Overovanie screen of a course: its note and the answers to verify",
    responses={**NOT_LOGGED_IN, **TEACHER_ONLY, 404: {"description": COURSE_NOT_FOUND}},
)
def read_verification(
    course_id: str, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep
) -> Verification:
    if catalog.get_course(course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            return teacher.verification(conn, catalog, user_id=user_id, course_id=course_id)
        except teacher.NotTeacher as error:
            raise _forbidden() from error


@router.put(
    "/courses/{course_id}/note",
    summary="Save the course's 'Aktuálna informácia k predmetu'",
    description=(
        "Replaces the course's note. The assistant uses it as verified, with priority over the"
        " MAIS sheet, from the next question on; the MAIS sheet itself does not change."
    ),
    responses={
        **NOT_LOGGED_IN,
        **TEACHER_ONLY,
        404: {"description": COURSE_NOT_FOUND},
        422: {"description": "Empty or too long text."},
    },
)
def save_note(
    course_id: str, body: NewCourseNote, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep
) -> CourseNote:
    if catalog.get_course(course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            return teacher.save_note(
                conn, user_id=user_id, course_id=course_id, text=body.text, now=_now()
            )
        except teacher.NotTeacher as error:
            raise _forbidden() from error


@router.delete(
    "/courses/{course_id}/note",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the course's 'Aktuálna informácia k predmetu' (no note is no error)",
    responses={**NOT_LOGGED_IN, **TEACHER_ONLY, 404: {"description": COURSE_NOT_FOUND}},
)
def delete_note(course_id: str, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> None:
    if catalog.get_course(course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            teacher.delete_note(conn, user_id=user_id, course_id=course_id)
        except teacher.NotTeacher as error:
            raise _forbidden() from error


@router.post(
    "/answers/{answer_id}/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="'Overiť': mark a student's answer as verified (again is no error)",
    description="The assistant shows it as Overené from the next question on.",
    responses={**NOT_LOGGED_IN, **TEACHER_ONLY, 404: {"description": ANSWER_NOT_FOUND}},
)
def verify(answer_id: UUID, user_id: CurrentUserId, pool: Pool) -> None:
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            found = teacher.verify_answer(conn, user_id=user_id, answer_id=answer_id, now=_now())
        except teacher.NotTeacher as error:
            raise _forbidden() from error
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ANSWER_NOT_FOUND)


@router.post(
    "/answers/{answer_id}/hide",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="'Zmazať': hide an answer as spam",
    description=(
        "The answer is no longer shown, counted, notified or used by the assistant;"
        " the row stays in the database."
    ),
    responses={**NOT_LOGGED_IN, **TEACHER_ONLY, 404: {"description": ANSWER_NOT_FOUND}},
)
def hide_answer(answer_id: UUID, user_id: CurrentUserId, pool: Pool) -> None:
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            found = teacher.hide_answer(conn, user_id=user_id, answer_id=answer_id, now=_now())
        except teacher.NotTeacher as error:
            raise _forbidden() from error
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ANSWER_NOT_FOUND)


@router.post(
    "/questions/{question_id}/hide",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hide a question as spam, with its answers",
    description=(
        "The question and its answers are no longer shown, counted, notified or used by the"
        " assistant; the rows stay in the database."
    ),
    responses={**NOT_LOGGED_IN, **TEACHER_ONLY, 404: {"description": QUESTION_NOT_FOUND}},
)
def hide_question(question_id: UUID, user_id: CurrentUserId, pool: Pool) -> None:
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            found = teacher.hide_question(
                conn, user_id=user_id, question_id=question_id, now=_now()
            )
        except teacher.NotTeacher as error:
            raise _forbidden() from error
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, QUESTION_NOT_FOUND)


def _now() -> datetime:
    return datetime.now(UTC)
