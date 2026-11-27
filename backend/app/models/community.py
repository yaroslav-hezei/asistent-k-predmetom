"""API models of "Otázky komunity" and "Upozornenia": questions people publish, their answers,
"Poďakovať" and the notifications.

They are the contract: OpenAPI and the frontend TypeScript types are generated from them.
A question is open while it has no visible answer; the status is derived, never stored.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.models.catalog import CourseSummary
from app.models.chat import QUESTION_MAX, QUESTION_MIN, Author

ANSWER_MIN = 1
ANSWER_MAX = 4000  # the database limit of answers.text

QuestionStatus = Literal["open", "answered"]

QuestionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=QUESTION_MIN, max_length=QUESTION_MAX),
]
AnswerText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=ANSWER_MIN, max_length=ANSWER_MAX)
]


class NewQuestion(BaseModel):
    course_id: str = Field(min_length=1, examples=["69574272"])
    text: QuestionText = Field(examples=["Môžem robiť semestrálny projekt sám, alebo len v tíme?"])
    source_message_id: UUID | None = Field(
        default=None,
        description="The assistant's 'Neviem' message the question is published from, if any.",
    )


class SimilarQuestionsRequest(BaseModel):
    course_id: str = Field(min_length=1, examples=["69574272"])
    text: QuestionText = Field(examples=["Robí sa projekt v tíme?"])


class QuestionSummary(BaseModel):
    """A question in the lists of "Otázky komunity"."""

    id: UUID
    course: CourseSummary
    text: str
    author: Author = Field(description="Who asked: a student or a teacher, with the nickname.")
    created_at: datetime
    status: QuestionStatus = Field(description="open = no visible answer yet.")
    answer_count: int = Field(ge=0, description="Visible answers.")
    from_assistant: bool = Field(
        description="Published from the assistant's 'Neviem' ('Asistent nenašiel odpoveď')."
    )
    mine: bool = Field(description="The logged-in user asked it.")


class QuestionCounts(BaseModel):
    open: int = Field(ge=0)
    answered: int = Field(ge=0)


class QuestionList(BaseModel):
    items: list[QuestionSummary] = Field(description="Newest first, at most 100.")
    counts: QuestionCounts = Field(description="Both tabs of the course, whatever `status` is.")


class SimilarQuestion(QuestionSummary):
    similarity: float = Field(ge=-1, le=1, description="Cosine similarity of the two questions.")


class CommunityAnswer(BaseModel):
    id: UUID
    text: str
    author: Author = Field(description="student or vyucujuci (a teacher), with the nickname.")
    verified: bool = Field(
        description="Overené: a teacher's own answer, or a student's answer a teacher verified."
    )
    created_at: datetime
    thanks: int = Field(ge=0, description="How many people said 'Poďakovať'.")
    thanked_by_me: bool
    mine: bool = Field(description="The logged-in user wrote it.")


class QuestionDetail(QuestionSummary):
    answers: list[CommunityAnswer] = Field(
        description="Visible answers: verified first, then the most thanked, then the oldest."
    )


class NewAnswer(BaseModel):
    text: AnswerText = Field(examples=["Projekt sa robí v tíme, tento rok po troch ľuďoch."])


class Thanks(BaseModel):
    thanks: int = Field(ge=0)
    thanked_by_me: bool


class NotificationAnswer(BaseModel):
    id: UUID
    text: str
    author: Author
    verified: bool
    thanked_by_me: bool


class Notification(BaseModel):
    """'Someone answered your question'."""

    id: UUID
    type: Literal["question_answered"]
    question: QuestionSummary
    answer: NotificationAnswer | None = Field(description="Null if the answer was removed.")
    chat_id: UUID | None = Field(
        description=(
            "The user's chat the question was published from ('Zobraziť v chate'); null when"
            " the question was written directly or the chat was deleted."
        )
    )
    created_at: datetime
    read: bool


class MarkRead(BaseModel):
    ids: list[UUID] | None = Field(
        default=None, description="Notifications to mark as read; null marks all of them."
    )


class Badges(BaseModel):
    """Counts for the sidebar."""

    unread_notifications: int = Field(ge=0)
    open_questions: int = Field(
        ge=0,
        description=(
            "Open questions of the courses of the user's study plan ('Moje predmety'),"
            " without the user's own; 0 when the plan is not set."
        ),
    )
