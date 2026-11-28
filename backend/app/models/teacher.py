"""API models of the teacher's screen "Overovanie": the courses a teacher verifies, the answers
waiting for "Overiť" and the course's "Aktuálna informácia k predmetu".

They are the contract: OpenAPI and the frontend TypeScript types are generated from them.
A teacher never edits a student's answer: they verify it, hide it as spam, or add their own
answer (`POST /questions/{question_id}/answers`, verified from the start).
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.models.catalog import CourseSummary
from app.models.chat import Author, QuestionRef

NOTE_MIN = 1
NOTE_MAX = 4000  # the database limit of course_notes.text

NoteText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=NOTE_MIN, max_length=NOTE_MAX)
]


class TeacherCourse(BaseModel):
    """A course the teacher verifies ('Predmet:' on the Overovanie screen)."""

    course: CourseSummary
    unverified_answers: int = Field(ge=0, description="Answers waiting for 'Overiť'.")


class AnswerToVerify(BaseModel):
    """A student's answer waiting for the teacher: 'Overiť', 'Pridať odpoveď' or 'Zmazať'."""

    id: UUID
    question: QuestionRef = Field(description="The community question it answers.")
    text: str
    author: Author
    created_at: datetime


class CourseNote(BaseModel):
    """'Aktuálna informácia k predmetu': the assistant uses it as verified, with priority over the
    MAIS sheet, from the next question on. The MAIS sheet itself does not change."""

    text: str
    author: Author = Field(description="The teacher who saved it last.")
    updated_at: datetime


class NewCourseNote(BaseModel):
    text: NoteText = Field(
        examples=["Semestrálny projekt sa robí v tímoch po troch. Odovzdanie je v 13. týždni."]
    )


class Verification(BaseModel):
    """Everything the Overovanie screen shows for one course."""

    course: CourseSummary
    note: CourseNote | None = Field(description="Null when the course has no note.")
    answers: list[AnswerToVerify] = Field(description="'Odpovede na overenie', oldest first.")
