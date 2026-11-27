"""Chats with the assistant (`public.chats`, `public.chat_messages`): one chat = one course.

Every answer is stored with its sources exactly as they were shown, so "História" shows the same
answer later even if the knowledge base has changed since.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.answerer import Answer
from app.models.chat import TITLE_MAX, ChatMessage, Source

# chat_messages.content must not be empty; a "Neviem" answer has no text of its own (the frontend
# shows its translated text), so this is stored instead and never returned.
NOT_FOUND_CONTENT = "Neviem"
HISTORY_LIMIT = 50


@dataclass(frozen=True)
class ChatRow:
    id: UUID
    course_id: str
    title: str
    updated_at: datetime


def find_chat(conn: Connection, chat_id: UUID, user_id: str) -> ChatRow | None:
    """The user's chat; None when it does not exist or belongs to someone else."""
    row = conn.execute(
        "select id, course_id, title, updated_at from public.chats where id = %s and user_id = %s",
        [chat_id, user_id],
    ).fetchone()
    return ChatRow(*row) if row else None


def list_chats(conn: Connection, user_id: str) -> list[ChatRow]:
    """The user's most recent chats, newest first."""
    rows = conn.execute(
        "select id, course_id, title, updated_at from public.chats where user_id = %s"
        " order by updated_at desc limit %s",
        [user_id, HISTORY_LIMIT],
    ).fetchall()
    return [ChatRow(*row) for row in rows]


def list_messages(conn: Connection, chat_id: UUID) -> list[ChatMessage]:
    rows = conn.execute(
        "select id, role, content, found, sources, created_at from public.chat_messages"
        " where chat_id = %s order by created_at, role desc",  # same time: 'user' first
        [chat_id],
    ).fetchall()
    return [_message(*row) for row in rows]


def save_exchange(
    conn: Connection,
    *,
    user_id: str,
    course_id: str,
    chat_id: UUID | None,
    question: str,
    asked_at: datetime,
    answer: Answer,
    answered_at: datetime,
) -> tuple[UUID, ChatMessage, ChatMessage]:
    """Store a question and its answer; chat_id None starts a new chat titled by the question.
    Returns the chat id and both stored messages. Run it in one transaction."""
    if chat_id is None:
        row = conn.execute(
            "insert into public.chats (user_id, course_id, title, updated_at)"
            " values (%s, %s, %s, %s) returning id",
            [user_id, course_id, question[:TITLE_MAX], asked_at],
        ).fetchone()
        assert row is not None
        chat_id = row[0]
    else:
        conn.execute("update public.chats set updated_at = %s where id = %s", [asked_at, chat_id])
    question_message = _insert(conn, chat_id, "user", question, None, None, None, asked_at)
    answer_message = _insert(
        conn,
        chat_id,
        "assistant",
        answer.text if answer.found and answer.text else NOT_FOUND_CONTENT,
        answer.language,
        answer.found,
        answer.sources,
        answered_at,
    )
    return chat_id, question_message, answer_message


def _insert(
    conn: Connection,
    chat_id: UUID,
    role: str,
    content: str,
    language: str | None,
    found: bool | None,
    sources: list[Source] | None,
    created_at: datetime,
) -> ChatMessage:
    stored_sources = None
    if sources is not None:
        stored_sources = Jsonb([source.model_dump(mode="json") for source in sources])
    row = conn.execute(
        "insert into public.chat_messages"
        " (chat_id, role, content, language, found, sources, created_at)"
        " values (%s, %s, %s, %s, %s, %s, %s)"
        " returning id, role, content, found, sources, created_at",
        [chat_id, role, content, language, found, stored_sources, created_at],
    ).fetchone()
    assert row is not None
    return _message(*row)


def _message(
    id: UUID, role: str, content: str, found: bool | None, sources: Any, created_at: datetime
) -> ChatMessage:
    return ChatMessage(
        id=id,
        role=role,  # type: ignore[arg-type]
        text=None if found is False else content,
        found=found,
        sources=[Source.model_validate(source) for source in sources or []],
        created_at=created_at,
    )
