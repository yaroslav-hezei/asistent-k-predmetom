"""Course catalogue read from the MAIS snapshot (`programs.json` + `courses/<predmetId>.json`).

Loaded once into memory at startup. Later the data will come from the database;
the API models in `app.models.catalog` stay the same.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.catalog import CourseSummary, Program, ProgramCourse, Semester

REGULAR_TYPES = ("P", "PV", "V")  # other plan rows (Prerekvizita, Zameniteľný) only link sheets

DEGREES = {"PRVY": "bc", "PRVY_PROFES_ORIENTOVANY": "bc_po", "DRUHY": "ing"}
METHODS = {"Prezenčná": "prezencna", "Kombinovaná": "kombinovana"}

# "3. rok ZS" in plans, "3.rok ZS" on sheets
PERIOD_RE = re.compile(r"^(\d+)\.\s*rok\s+(ZS|LS)$")

SEMESTER_ORDER = {"ZS": 0, "LS": 1}
DEGREE_ORDER = {"bc": 0, "bc_po": 1, "ing": 2}
LANGUAGE_ORDER = {"sk": 0, "en": 1}
METHOD_ORDER = {"prezencna": 0, "kombinovana": 1}


class CatalogDataError(ValueError):
    """The snapshot does not have the shape the catalogue expects."""


@dataclass(frozen=True)
class SheetSection:
    label: str  # e.g. "Priebežné hodnotenie (PH)"
    text: str  # may be empty: many labels on the sheet have no value


@dataclass(frozen=True)
class Sheet:
    """A course's information sheet: what the assistant quotes and links to."""

    course_id: str
    source_url: str  # permanent link to the sheet in MAIS
    fetched_at: datetime  # when the sheet was read from MAIS (MAIS has no reliable change date)
    sections: tuple[SheetSection, ...]  # in the order of the sheet


def normalize(text: str) -> str:
    """Lower case, no diacritics, single spaces.

    "Základy  ALGORITMIZÁCIE" -> "zaklady algoritmizacie"
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())


def parse_period(text: str) -> tuple[int, Semester]:
    match = PERIOD_RE.match(text.strip())
    if not match:
        raise CatalogDataError(f"unknown period format: {text!r}")
    return int(match.group(1)), match.group(2)  # type: ignore[return-value]


def parse_semesters(text: str) -> list[Semester]:
    """Sheet "Odporúčaný semester": "ZS", "LS" or "ZS, LS"."""
    parts = [part.strip() for part in text.split(",")]
    if not parts or any(part not in SEMESTER_ORDER for part in parts):
        raise CatalogDataError(f"unknown recommended semester: {text!r}")
    return sorted(set(parts), key=SEMESTER_ORDER.__getitem__)  # type: ignore[return-value]


class Catalog:
    def __init__(
        self,
        programs: list[Program],
        courses: dict[str, CourseSummary],
        program_courses: dict[str, list[ProgramCourse]],
        sheets: dict[str, Sheet],
    ) -> None:
        self._programs = programs
        self._sheets = sheets
        self._courses = courses
        self._program_courses = program_courses
        self._courses_by_name = sorted(courses.values(), key=lambda c: (normalize(c.name), c.code))
        self._search_keys = {c.id: f"{normalize(c.name)} {c.code}" for c in courses.values()}

    @classmethod
    def load(cls, data_dir: Path) -> "Catalog":
        programs_file = data_dir / "programs.json"
        if not programs_file.is_file():
            raise CatalogDataError(f"missing {programs_file}")
        raw_programs: list[dict[str, Any]] = json.loads(programs_file.read_text(encoding="utf-8"))

        sheets: dict[str, dict[str, Any]] = {}
        for raw in raw_programs:
            for row in raw["plan"]:
                if row["type"] in REGULAR_TYPES and row["predmet_id"] not in sheets:
                    sheet_file = data_dir / "courses" / f"{row['predmet_id']}.json"
                    if not sheet_file.is_file():
                        raise CatalogDataError(f"missing {sheet_file}")
                    sheets[row["predmet_id"]] = json.loads(sheet_file.read_text(encoding="utf-8"))

        courses = {pid: _course_from_sheet(sheet) for pid, sheet in sheets.items()}
        programs = [_program_from_raw(raw) for raw in raw_programs]
        programs.sort(
            key=lambda p: (
                DEGREE_ORDER[p.degree],
                normalize(p.name),
                LANGUAGE_ORDER[p.language],
                METHOD_ORDER[p.method],
            )
        )
        program_courses = {
            raw["program_id"]: _plan_from_raw(raw, courses, sheets) for raw in raw_programs
        }
        return cls(
            programs,
            courses,
            program_courses,
            {pid: _sheet_from_raw(sheet) for pid, sheet in sheets.items()},
        )

    def list_programs(self) -> list[Program]:
        return list(self._programs)

    def program_courses(
        self, program_id: str, year: int | None = None, semester: Semester | None = None
    ) -> list[ProgramCourse] | None:
        """None if the program does not exist."""
        plan = self._program_courses.get(program_id)
        if plan is None:
            return None
        return [
            item
            for item in plan
            if (year is None or item.year == year)
            and (semester is None or item.semester == semester)
        ]

    def get_course(self, course_id: str) -> CourseSummary | None:
        return self._courses.get(course_id)

    def get_sheet(self, course_id: str) -> Sheet | None:
        return self._sheets.get(course_id)

    def search_courses(self, query: str | None = None) -> list[CourseSummary]:
        """Every word of the query must appear in the name or code; case and diacritics ignored."""
        words = normalize(query or "").split()
        if not words:
            return list(self._courses_by_name)
        return [
            course
            for course in self._courses_by_name
            if all(word in self._search_keys[course.id] for word in words)
        ]


def _course_from_sheet(sheet: dict[str, Any]) -> CourseSummary:
    fields = sheet["fields"]
    return CourseSummary(
        id=sheet["predmet_id"],
        code=sheet["code"],
        name=sheet["name"],
        credits=fields["credits"],
        semesters=parse_semesters(fields["recommended_semester"]),
    )


def _sheet_from_raw(sheet: dict[str, Any]) -> Sheet:
    return Sheet(
        course_id=sheet["predmet_id"],
        source_url=sheet["source_url"],
        # "2026-11-17T15:11:35Z"; fromisoformat accepts "Z" only from Python 3.11
        fetched_at=datetime.fromisoformat(sheet["fetched_at"]),
        sections=tuple(SheetSection(s["label"], s["text"]) for s in sheet["sections"]),
    )


def _program_from_raw(raw: dict[str, Any]) -> Program:
    header = {item["label"]: item["text"] for item in raw["header"]}
    if raw["degree"] not in DEGREES:
        raise CatalogDataError(f"unknown degree {raw['degree']!r} in {raw['code']}")
    method = header.get("Metóda")
    if method not in METHODS:
        raise CatalogDataError(f"unknown method {method!r} in {raw['code']}")
    return Program(
        id=raw["program_id"],
        code=raw["code"],
        name=raw["name"],
        degree=DEGREES[raw["degree"]],
        # MAIS program codes end with the teaching language: HI_Bc_D_sk, INF_Bc_D_en, ApE_Bc_D_KM
        language="en" if raw["code"].endswith("_en") else "sk",
        method=METHODS[method],
        years=int(float(header["Dĺžka štúdia"])),
    )


def _plan_from_raw(
    raw: dict[str, Any],
    courses: dict[str, CourseSummary],
    sheets: dict[str, dict[str, Any]],
) -> list[ProgramCourse]:
    items: list[ProgramCourse] = []
    for row in raw["plan"]:
        if row["type"] not in REGULAR_TYPES:
            continue
        state_exam = row["block"] == "state_exam"
        if row["period"]:
            year, semester = parse_period(row["period"])
        elif state_exam:
            year, semester = _sheet_period(sheets[row["predmet_id"]], raw["code"])
        else:
            raise CatalogDataError(f"plan row without period: {raw['code']} {row['code']}")
        items.append(
            ProgramCourse(
                course=courses[row["predmet_id"]],
                year=year,
                semester=semester,
                type=row["type"],
                state_exam=state_exam,
            )
        )
    # by year and semester, state-exam courses last; sort is stable, so plan order is kept
    items.sort(key=lambda i: (i.year, SEMESTER_ORDER[i.semester], i.state_exam))
    return items


def _sheet_period(sheet: dict[str, Any], program_code: str) -> tuple[int, Semester]:
    """State-exam rows have no period in the plan; the sheet lists the semester per program."""
    for entry in sheet["programs"]:
        if entry["program"].endswith(f"({program_code})"):
            return parse_period(entry["semester"])
    raise CatalogDataError(f"sheet {sheet['predmet_id']} has no semester for {program_code}")
