"""Course catalogue endpoints: programs, their study plans, course search."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.catalog import Catalog
from app.models.catalog import CourseSummary, Program, ProgramCourse, Semester

router = APIRouter(tags=["catalog"])


def get_catalog(request: Request) -> Catalog:
    return request.app.state.catalog


CatalogDep = Annotated[Catalog, Depends(get_catalog)]


@router.get("/programs", summary="List study programs")
def list_programs(catalog: CatalogDep) -> list[Program]:
    return catalog.list_programs()


@router.get("/programs/{program_id}/courses", summary="Courses in a program's study plan")
def list_program_courses(
    program_id: str,
    catalog: CatalogDep,
    year: Annotated[int | None, Query(ge=1, le=4, description="Year of study.")] = None,
    semester: Annotated[Semester | None, Query(description="ZS or LS.")] = None,
) -> list[ProgramCourse]:
    courses = catalog.program_courses(program_id, year=year, semester=semester)
    if courses is None:
        raise HTTPException(status_code=404, detail="Program not found")
    return courses


@router.get("/courses", summary="Search courses by name or code")
def search_courses(
    catalog: CatalogDep,
    q: Annotated[
        str | None,
        Query(description="Words to find in the name or code; case and diacritics are ignored."),
    ] = None,
) -> list[CourseSummary]:
    return catalog.search_courses(q)


@router.get("/courses/{course_id}", summary="One course")
def get_course(course_id: str, catalog: CatalogDep) -> CourseSummary:
    course = catalog.get_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
