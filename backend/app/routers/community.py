""" "Otázky komunity" and "Upozornenia": publish questions, answer, thank, notifications, badges.

Vectors (similar questions, the answers the assistant uses) need the model client; without
GEMINI_API_KEY everything still works, only "similar questions" is empty and the answers wait
for `scripts/embed_chunks.py`. A failed vector never fails the request: the text is stored first.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from google.genai import errors
from psycopg import Connection

from app import community, knowledge, llm
from app.auth import CurrentUserId
from app.db import Pool
from app.models.community import (
    Badges,
    CommunityAnswer,
    MarkRead,
    NewAnswer,
    NewQuestion,
    Notification,
    QuestionDetail,
    QuestionList,
    QuestionStatus,
    SimilarQuestion,
    SimilarQuestionsRequest,
    Thanks,
)
from app.models.me import Me
from app.profiles import get_profile
from app.routers.catalog import CatalogDep
from app.routers.chat import ModelDep
from app.routers.me import NO_PROFILE, NOT_LOGGED_IN

router = APIRouter(tags=["community"])
logger = logging.getLogger(__name__)

SIMILAR_LIMIT = 3
SIMILAR_MIN_SIMILARITY = 0.75
COURSE_NOT_FOUND = "Course not found."
QUESTION_NOT_FOUND = "Question not found."
ANSWER_NOT_FOUND = "Answer not found."
VECTOR_ERRORS = (errors.APIError, RuntimeError, ValueError)


def _profile(conn: Connection, user_id: str) -> Me:
    me = get_profile(conn, user_id)
    if me is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The account has no profile.")
    return me


def _question_vector(model: object | None, text: str) -> list[float] | None:
    if model is None:
        return None
    try:
        return llm.embed_queries(model, llm.EMBED_MODEL, [text], llm.EMBED_QUERY_TASK)[0]
    except VECTOR_ERRORS:
        logger.warning("no vector for a question", exc_info=True)
        return None


@router.post(
    "/questions/similar",
    summary="Questions of the course similar to a draft (before publishing)",
    description=(
        f"At most {SIMILAR_LIMIT} visible questions with a cosine similarity of at least"
        f" {SIMILAR_MIN_SIMILARITY}, the most similar first. Empty when the backend runs without"
        " the model."
    ),
    responses={**NOT_LOGGED_IN, **NO_PROFILE, 404: {"description": COURSE_NOT_FOUND}},
)
def similar(
    body: SimilarQuestionsRequest,
    user_id: CurrentUserId,
    pool: Pool,
    catalog: CatalogDep,
    model: ModelDep,
) -> list[SimilarQuestion]:
    if catalog.get_course(body.course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
    vector = _question_vector(model, body.text)
    if vector is None:
        return []
    with pool.connection() as conn:
        return community.similar_questions(
            conn,
            catalog,
            user_id=user_id,
            course_id=body.course_id,
            vector=vector,
            model=llm.EMBED_MODEL,
            limit=SIMILAR_LIMIT,
            min_similarity=SIMILAR_MIN_SIMILARITY,
        )


@router.post(
    "/questions",
    summary="Publish a question to 'Otázky komunity'",
    responses={
        **NOT_LOGGED_IN,
        **NO_PROFILE,
        404: {"description": COURSE_NOT_FOUND},
        422: {"description": "Invalid text, or source_message_id is not your assistant answer."},
    },
)
def publish(
    body: NewQuestion, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep, model: ModelDep
) -> QuestionDetail:
    if catalog.get_course(body.course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            question_id = community.create_question(
                conn,
                user_id=user_id,
                course_id=body.course_id,
                text=body.text,
                source_message_id=body.source_message_id,
            )
        except community.BadSourceMessage as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    vector = _question_vector(model, body.text)
    with pool.connection() as conn:
        if vector is not None:
            community.set_question_vector(conn, question_id, vector, llm.EMBED_MODEL)
        detail = community.get_question(conn, catalog, user_id=user_id, question_id=question_id)
    assert detail is not None
    return detail


@router.get(
    "/questions",
    summary="Questions of a course: one tab of 'Otázky komunity' and both counts",
    responses={**NOT_LOGGED_IN, **NO_PROFILE, 404: {"description": COURSE_NOT_FOUND}},
)
def list_questions(
    user_id: CurrentUserId,
    pool: Pool,
    catalog: CatalogDep,
    course_id: Annotated[str, Query(min_length=1, examples=["69574272"])],
    question_status: Annotated[QuestionStatus, Query(alias="status")] = "open",
) -> QuestionList:
    if catalog.get_course(course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, COURSE_NOT_FOUND)
    with pool.connection() as conn:
        _profile(conn, user_id)
        return community.list_questions(
            conn, catalog, user_id=user_id, course_id=course_id, status=question_status
        )


@router.get(
    "/questions/{question_id}",
    summary="A question with its answers",
    responses={**NOT_LOGGED_IN, **NO_PROFILE, 404: {"description": QUESTION_NOT_FOUND}},
)
def read_question(
    question_id: UUID, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep
) -> QuestionDetail:
    with pool.connection() as conn:
        _profile(conn, user_id)
        detail = community.get_question(conn, catalog, user_id=user_id, question_id=question_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, QUESTION_NOT_FOUND)
    return detail


@router.post(
    "/questions/{question_id}/answers",
    summary="Answer a question",
    description=(
        "The answer goes into the knowledge base at once: the assistant uses it for the next"
        " questions about the course, as 'Neoverené' until a teacher verifies it. A teacher of"
        " the course answers verified. The asker gets a notification."
    ),
    responses={
        **NOT_LOGGED_IN,
        403: {"description": "The account has no profile, or the question is your own."},
        404: {"description": QUESTION_NOT_FOUND},
    },
)
def answer(
    question_id: UUID,
    body: NewAnswer,
    user_id: CurrentUserId,
    pool: Pool,
    catalog: CatalogDep,
    model: ModelDep,
) -> CommunityAnswer:
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            result = community.add_answer(
                conn, user_id=user_id, question_id=question_id, text=body.text, now=_now()
            )
        except community.NotAllowed as error:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, QUESTION_NOT_FOUND)
    if model is not None:
        course = catalog.get_course(result.course_id)
        title = knowledge.chunk_title(course.name if course else "", None, result.question_text)
        try:
            [vector] = llm.embed_documents(
                model, llm.EMBED_MODEL, [llm.Document(title=title, text=body.text)]
            )
        except VECTOR_ERRORS:
            logger.warning("no vector for an answer; embed_chunks.py adds it", exc_info=True)
        else:
            with pool.connection() as conn:
                knowledge.store_vector(
                    conn, result.chunk_id, result.text_hash, vector, llm.EMBED_MODEL
                )
    return result.answer


@router.post(
    "/answers/{answer_id}/thanks",
    summary="'Poďakovať' for an answer (once per user; again is no error)",
    responses={
        **NOT_LOGGED_IN,
        403: {"description": "The account has no profile, or the answer is your own."},
        404: {"description": ANSWER_NOT_FOUND},
    },
)
def thank(answer_id: UUID, user_id: CurrentUserId, pool: Pool) -> Thanks:
    with pool.connection() as conn:
        _profile(conn, user_id)
        try:
            thanks = community.thank(conn, user_id=user_id, answer_id=answer_id)
        except community.NotAllowed as error:
            raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    if thanks is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ANSWER_NOT_FOUND)
    return thanks


@router.get(
    "/notifications",
    summary="The user's notifications, newest first (at most 50)",
    responses={**NOT_LOGGED_IN, **NO_PROFILE},
)
def notifications(user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> list[Notification]:
    with pool.connection() as conn:
        _profile(conn, user_id)
        return community.list_notifications(conn, catalog, user_id=user_id)


@router.post(
    "/notifications/read",
    summary="Mark notifications as read (all when `ids` is null); returns the new counts",
    responses={**NOT_LOGGED_IN, **NO_PROFILE},
)
def read_notifications(
    body: MarkRead, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep
) -> Badges:
    with pool.connection() as conn:
        me = _profile(conn, user_id)
        community.mark_read(conn, user_id=user_id, ids=body.ids, now=_now())
        return community.badges(conn, catalog, user_id=user_id, study=me.study)


@router.get(
    "/badges",
    summary="Counts for the sidebar: unread notifications and open questions of 'Moje predmety'",
    responses={**NOT_LOGGED_IN, **NO_PROFILE},
)
def badges(user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> Badges:
    with pool.connection() as conn:
        me = _profile(conn, user_id)
        return community.badges(conn, catalog, user_id=user_id, study=me.study)


def _now() -> datetime:
    return datetime.now(UTC)
