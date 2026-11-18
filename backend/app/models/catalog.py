"""API models of the course catalogue.

They are the contract: OpenAPI and the frontend TypeScript types are generated from them.
"""

from typing import Literal

from pydantic import BaseModel, Field

Semester = Literal["ZS", "LS"]


class Health(BaseModel):
    status: Literal["ok"]


class CourseSummary(BaseModel):
    """A course as described by its MAIS information sheet."""

    id: str = Field(description="MAIS predmetId of the course sheet.", examples=["65954478"])
    code: str = Field(description="Course code.", examples=["26000629"])
    name: str = Field(examples=["Základy algoritmizácie a programovania"])
    credits: int = Field(description="Credits from the information sheet.", examples=[5])
    semesters: list[Semester] = Field(
        description="Recommended semester(s) from the information sheet.", examples=[["ZS"]]
    )


class Program(BaseModel):
    """A study program (FEI, denná forma, one academic year)."""

    id: str = Field(description="MAIS program id.", examples=["65669424"])
    code: str = Field(examples=["HI_Bc_D_sk"])
    name: str = Field(examples=["Hospodárska informatika"])
    degree: Literal["bc", "bc_po", "ing"] = Field(
        description="bc = 1st degree, bc_po = 1st degree professionally oriented, ing = 2nd degree."
    )
    language: Literal["sk", "en"] = Field(description="Teaching language of the program.")
    method: Literal["prezencna", "kombinovana"] = Field(description="Study method.")
    years: int = Field(description="Standard length of study in years.", examples=[3])


class ProgramCourse(BaseModel):
    """One course in a program's study plan, placed in a year and semester."""

    course: CourseSummary
    year: int = Field(description="Year of study.", examples=[3])
    semester: Semester = Field(
        description="Semester of the plan; for state-exam courses taken from the sheet."
    )
    type: Literal["P", "PV", "V"] = Field(
        description="P = povinný, PV = povinne voliteľný, V = výberový."
    )
    state_exam: bool = Field(description="True for courses from the state-exam table.")
