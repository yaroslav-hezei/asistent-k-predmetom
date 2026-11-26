"""API models of the chat with the assistant: a question, the answer and its sources.

They are the contract: OpenAPI and the frontend TypeScript types are generated from them.
Sources, quotes, dates and authors are filled by code from stored data, never by the model;
the model only cites sources by their number.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.models.catalog import CourseSummary

QUESTION_MIN = 3
QUESTION_MAX = 1000  # the same limit as a question published to "Otázky komunity"
TITLE_MAX = 200


class Author(BaseModel):
    """Who wrote the source: the official MAIS sheet, a student or a teacher."""

    kind: Literal["mais", "student", "vyucujuci"]
    nickname: str | None = Field(description="Null for the MAIS sheet.", examples=["tomas_r"])


class QuestionRef(BaseModel):
    """The community question a community answer belongs to."""

    id: UUID
    text: str = Field(examples=["Môžem robiť semestrálny projekt sám, alebo len v tíme?"])


class Source(BaseModel):
    """One source under an answer. The answer text cites it as [n]."""

    n: int = Field(ge=1, description="Number cited in the answer text as [n].", examples=[1])
    type: Literal["sheet", "answer", "course_note"] = Field(
        description=(
            "sheet = MAIS information sheet; answer = an answer from Otázky komunity;"
            " course_note = the teacher's Aktuálna informácia k predmetu."
        )
    )
    section: str | None = Field(
        description="Sheet section label; null for other types.",
        examples=["Priebežné hodnotenie (PH)"],
    )
    quote: str = Field(description="Exact stored text the answer relies on.")
    url: str | None = Field(
        description="Sheet: link to the sheet in MAIS. Null for other types.",
        examples=["https://maisportal.tuke.sk/portal/tlacPredmetuOSP.mais?predmetId=65954478"],
    )
    question: QuestionRef | None = Field(
        description="Type answer: the community question it answers. Null for other types."
    )
    date: datetime = Field(
        description=(
            "Sheet: when the sheet was read from MAIS (MAIS has no reliable change date),"
            " shown as 'stav k …'. Answer and course note: when it was written."
        )
    )
    author: Author
    verified: bool = Field(
        description=(
            "True for the sheet and the teacher's note; for a community answer:"
            " verified by a teacher (Overené) or not (Neoverené)."
        )
    )
    outdated: bool = Field(
        description="Sheet: show the outdated-sheet warning. Always false until its rule is set."
    )


class ChatMessage(BaseModel):
    """A question of the user or an answer of the assistant."""

    id: UUID
    role: Literal["user", "assistant"]
    text: str | None = Field(
        description=(
            "User: the question. Assistant: the answer with [n] citations;"
            " null when found is false (the frontend shows its own 'Neviem' text)."
        )
    )
    found: bool | None = Field(
        description="Assistant only: false = 'Neviem', offer 'Zverejniť otázku'. Null for user."
    )
    sources: list[Source] = Field(description="Assistant only; empty for user and for 'Neviem'.")
    created_at: datetime


QuestionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=QUESTION_MIN, max_length=QUESTION_MAX),
]


class AskRequest(BaseModel):
    course_id: str = Field(
        min_length=1, description="MAIS id of the course, as in /courses.", examples=["65954478"]
    )
    question: QuestionText = Field(examples=["Ako sa hodnotí tento predmet?"])
    chat_id: UUID | None = Field(
        default=None, description="Continue this chat; null starts a new chat for the course."
    )


class AskResponse(BaseModel):
    chat_id: UUID = Field(description="The chat the question went to (new or continued).")
    question: ChatMessage
    answer: ChatMessage


class ChatSummary(BaseModel):
    """A chat in "História": one chat = one course."""

    id: UUID
    course: CourseSummary
    title: str = Field(description=f"The first question, cut to {TITLE_MAX} characters.")
    updated_at: datetime = Field(description="Time of the last question.")


class Chat(ChatSummary):
    messages: list[ChatMessage] = Field(description="Oldest first.")
