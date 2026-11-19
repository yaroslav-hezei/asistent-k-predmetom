"""Validate evaluation questions against the committed HI Bc. MAIS sheets.

Standard library only. This checks structure and evidence, not the semantic truth
of answers or the absence of an answer: those require reading the whole sheet.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "65669424"
REQUIRED = {"id", "course_id", "language", "question", "answerable", "evidence", "answer"}
FIELDS = REQUIRED | {"notes"}


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def five_word_runs(value: str) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", value.casefold(), flags=re.UNICODE)
    return {tuple(words[i:i + 5]) for i in range(len(words) - 4)}


@dataclass(frozen=True)
class Diagnostic:
    line: int
    question_id: str
    message: str

    def format(self, level: str) -> str:
        return f"{level} line {self.line} [{self.question_id}]: {self.message}"


@dataclass
class Result:
    errors: list[Diagnostic] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        courses = Counter(q["course_id"] for q in self.questions if isinstance(q.get("course_id"), str))
        lines = [
            f"Questions: {len(self.questions)}",
            f"Answerable: {sum(q.get('answerable') is True for q in self.questions)}",
            f"Not answerable: {sum(q.get('answerable') is False for q in self.questions)}",
            f"sk: {sum(q.get('language') == 'sk' for q in self.questions)}",
            f"en: {sum(q.get('language') == 'en' for q in self.questions)}",
            "Questions per course:",
            *(f"  {course}: {count}" for course, count in sorted(courses.items())),
            f"Errors: {len(self.errors)}; warnings: {len(self.warnings)}",
        ]
        return "\n".join(lines)


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-JSON constant: {value}")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_file(questions: Path, data: Path) -> Result:
    result = Result()
    try:
        programs = json.loads((data / "programs.json").read_text(encoding="utf-8"))
        program = next(p for p in programs if p["program_id"] == PROGRAM_ID)
        eligible = {row["predmet_id"] for row in program["plan"] if row["type"] in {"P", "PV", "V"}}
    except (OSError, ValueError, TypeError, KeyError, StopIteration) as error:
        result.errors.append(Diagnostic(0, "<dataset>", f"Cannot read HI Bc. program: {error}"))
        eligible = set()
    try:
        lines = questions.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        result.errors.append(Diagnostic(0, "<dataset>", f"Cannot read questions: {error}"))
        return result
    if not lines:
        result.errors.append(Diagnostic(0, "<dataset>", "Question file must not be empty"))

    seen: set[str] = set()
    previous_id = ""
    course_context: dict[str, tuple[int, str]] = {}
    sheets: dict[str, tuple[dict[str, list[str]], set[tuple[str, ...]]] | str] = {}

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            result.errors.append(Diagnostic(line_number, "<unknown>", "Blank JSONL line is not allowed"))
            continue
        try:
            record = json.loads(line, parse_constant=_reject_constant, object_pairs_hook=_object)
        except ValueError as error:
            result.errors.append(Diagnostic(line_number, "<unknown>", f"Invalid JSON: {error}"))
            continue
        if not isinstance(record, dict):
            result.errors.append(Diagnostic(line_number, "<unknown>", "Question must be a JSON object"))
            continue
        result.questions.append(record)
        raw_id = record.get("id")
        question_id = raw_id if isinstance(raw_id, str) and raw_id.isprintable() else "<unknown>"

        def error(message: str) -> None:
            result.errors.append(Diagnostic(line_number, question_id, message))

        schema_start = len(result.errors)
        for name in sorted(REQUIRED - record.keys()):
            error(f"Missing field '{name}'")
        for name in sorted(record.keys() - FIELDS):
            error(f"Unknown field '{name}' (the question contract is fixed)")
        for name in ("id", "course_id", "language", "question"):
            if name in record and (not isinstance(record[name], str) or not record[name].strip()):
                error(f"Field '{name}' must be a non-empty string")
        if "answerable" in record and type(record["answerable"]) is not bool:
            error("Field 'answerable' must be a bool")
        if "evidence" in record and not isinstance(record["evidence"], list):
            error("Field 'evidence' must be a list")
        for name in ("answer", "notes"):
            if name in record and record[name] is not None and not isinstance(record[name], str):
                error(f"Field '{name}' must be a string or null")
        if len(result.errors) != schema_start:
            continue

        if not re.fullmatch(r"q[0-9]{3}", record["id"]) or record["id"] == "q000":
            error("ID must be q001 through q999")
        else:
            if record["id"] in seen:
                error(f"Duplicate id '{record['id']}'")
            if record["id"] < previous_id:
                error("Question ids must be sorted in ascending order")
            previous_id = record["id"]
            seen.add(record["id"])
        if record["language"] not in {"sk", "en"}:
            error("Language must be 'sk' or 'en'")
        course_id = record["course_id"]
        course_context.setdefault(course_id, (line_number, question_id))
        if record["answerable"]:
            if not record["evidence"]:
                error("Answerable question requires evidence")
            if not isinstance(record["answer"], str) or not record["answer"].strip():
                error("Answerable question requires a non-empty answer")
        else:
            if record["evidence"]:
                error("Not-answerable question must have empty evidence")
            if record["answer"] is not None:
                error("Not-answerable question must have answer: null")

        if course_id not in eligible:
            error(f"Course '{course_id}' is not in P / PV / V rows of HI Bc. program {PROGRAM_ID}")
            continue
        if course_id not in sheets:
            try:
                # Membership is checked first; untrusted ids cannot escape courses/.
                sheet = json.loads((data / "courses" / f"{course_id}.json").read_text(encoding="utf-8"))
                sections: dict[str, list[str]] = {}
                for section in sheet["sections"]:
                    if not isinstance(section["label"], str) or not isinstance(section["text"], str):
                        raise ValueError("Section label/text must be strings")
                    sections.setdefault(section["label"], []).append(collapse_whitespace(section["text"]))
                sheet_text = " ".join(f"{s['label']} {s['text']}" for s in sheet["sections"])
                sheets[course_id] = (sections, five_word_runs(sheet_text))
            except (OSError, ValueError, TypeError, KeyError) as problem:
                sheets[course_id] = f"Cannot read course sheet '{course_id}': {problem}"
        cached = sheets[course_id]
        if isinstance(cached, str):
            error(cached)
            continue
        sections, sheet_runs = cached
        for index, evidence in enumerate(record["evidence"], 1):
            prefix = f"Evidence {index}"
            if not isinstance(evidence, dict) or set(evidence) != {"section", "quote"}:
                error(f"{prefix} must be an object with exactly 'section' and 'quote'")
                continue
            if any(not isinstance(evidence[key], str) or not evidence[key].strip() for key in ("section", "quote")):
                error(f"{prefix} section and quote must be non-empty strings")
                continue
            label, quote = evidence["section"], evidence["quote"]
            if len(quote) > 300:
                error(f"{prefix} quote exceeds 300 characters")
            if label not in sections:
                error(f"{prefix} unknown section '{label}' in course {course_id}")
            elif not any(collapse_whitespace(quote) in value for value in sections[label]):
                error(f"{prefix} quote does not occur in section '{label}'")
        if five_word_runs(record["question"]) & sheet_runs:
            result.warnings.append(Diagnostic(line_number, question_id,
                                             "Question shares 5 or more consecutive words with its sheet"))

    course_counts = Counter(q["course_id"] for q in result.questions if isinstance(q.get("course_id"), str))
    for course_id, count in sorted(course_counts.items()):
        if count != 4:
            line_number, question_id = course_context.get(course_id, (0, "<unknown>"))
            result.warnings.append(Diagnostic(line_number, question_id,
                                             f"Course {course_id} has {count} question(s); expected 4"))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/mais/2026-27",
                        help="MAIS snapshot directory containing programs.json and courses/")
    parser.add_argument("--questions", type=Path, default=ROOT / "data/eval/questions.jsonl",
                        help="Question JSONL file to validate")
    args = parser.parse_args(argv)
    result = validate_file(args.questions, args.data)
    for diagnostic in result.errors:
        print(diagnostic.format("ERROR"))
    for diagnostic in result.warnings:
        print(diagnostic.format("WARNING"))
    print(result.summary())
    return int(bool(result.errors))


if __name__ == "__main__":
    raise SystemExit(main())
