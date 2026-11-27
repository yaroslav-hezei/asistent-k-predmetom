"""Chat with the assistant: ask a question about a course, read the user's chats."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from psycopg import Connection

from app.answerer import answer_question
from app.auth import CurrentUserId
from app.chats import find_chat, list_chats, list_messages, save_exchange
from app.db import Pool
from app.models.chat import AskRequest, AskResponse, Chat, ChatSummary
from app.profiles import get_profile
from app.routers.catalog import CatalogDep
from app.routers.me import NO_PROFILE, NOT_LOGGED_IN

router = APIRouter(tags=["chat"])

CHAT_NOT_FOUND = "Chat not found."


@router.post(
    "/ask",
    summary="Ask a question about a course",
    description=(
        "Stores the question and the answer in a chat: a new one when `chat_id` is null."
        " Until the RAG step the answer is a placeholder: one real section of the course's"
        " MAIS sheet; a question with the word 'neviem' gets the 'Neviem' answer."
    ),
    responses={
        **NOT_LOGGED_IN,
        **NO_PROFILE,
        404: {"description": "Unknown course, or the chat does not exist / is not yours."},
        422: {"description": "Invalid question, or the chat belongs to another course."},
    },
)
def ask(body: AskRequest, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> AskResponse:
    sheet = catalog.get_sheet(body.course_id)
    if sheet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    with pool.connection() as conn:
        _require_profile(conn, user_id)
        if body.chat_id is not None:
            chat = find_chat(conn, body.chat_id, user_id)
            if chat is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, CHAT_NOT_FOUND)
            if chat.course_id != body.course_id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT, "The chat belongs to another course."
                )
    # answered outside the database transaction: a real answer takes seconds
    asked_at = datetime.now(UTC)
    answer = answer_question(sheet, body.question)
    answered_at = datetime.now(UTC)
    with pool.connection() as conn:
        chat_id, question, reply = save_exchange(
            conn,
            user_id=user_id,
            course_id=body.course_id,
            chat_id=body.chat_id,
            question=body.question,
            asked_at=asked_at,
            answer=answer,
            answered_at=answered_at,
        )
    return AskResponse(chat_id=chat_id, question=question, answer=reply)


@router.get(
    "/chats",
    summary="The user's chats for 'História', newest first (at most 50)",
    responses={**NOT_LOGGED_IN, **NO_PROFILE},
)
def read_chats(user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> list[ChatSummary]:
    with pool.connection() as conn:
        _require_profile(conn, user_id)
        rows = list_chats(conn, user_id)
    summaries = []
    for row in rows:
        course = catalog.get_course(row.course_id)
        if course is not None:  # every chat's course is in the catalogue; skip if it ever is not
            summaries.append(
                ChatSummary(id=row.id, course=course, title=row.title, updated_at=row.updated_at)
            )
    return summaries


@router.get(
    "/chats/{chat_id}",
    summary="One chat with its messages",
    responses={
        **NOT_LOGGED_IN,
        **NO_PROFILE,
        404: {"description": "The chat does not exist or is not yours."},
    },
)
def read_chat(chat_id: UUID, user_id: CurrentUserId, pool: Pool, catalog: CatalogDep) -> Chat:
    with pool.connection() as conn:
        _require_profile(conn, user_id)
        row = find_chat(conn, chat_id, user_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, CHAT_NOT_FOUND)
        messages = list_messages(conn, chat_id)
    course = catalog.get_course(row.course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CHAT_NOT_FOUND)
    return Chat(
        id=row.id, course=course, title=row.title, updated_at=row.updated_at, messages=messages
    )


def _require_profile(conn: Connection, user_id: str) -> None:
    if get_profile(conn, user_id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The account has no profile.")
