"""API models of the logged-in user.

They are the contract: OpenAPI and the frontend TypeScript types are generated from them.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.catalog import Semester


class Study(BaseModel):
    """Program, year and semester of a student: what "Moje predmety" shows."""

    program_id: str = Field(description="MAIS program id.", examples=["65669424"])
    year: int = Field(ge=1, le=6, description="Year of study.", examples=[3])
    semester: Semester


class Me(BaseModel):
    """The logged-in user's profile."""

    id: UUID = Field(description="User id (Supabase Auth).")
    nickname: str = Field(description="Shown as the author of questions and answers.")
    role: Literal["student", "vyucujuci"]
    study: Study | None = Field(description="Null when the user has not chosen it yet.")
