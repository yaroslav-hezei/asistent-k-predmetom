"""Score answer/abstention decisions and citations from local evaluation files.

Answer wording is not scored. No assistant, model, network or database is used.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

from validate import Diagnostic, _object, _reject_constant, collapse_whitespace

ROOT = Path(__file__).resolve().parents[2]
OUTCOMES = ("answered", "missed", "abstained", "invented", "missing")
CITATIONS = ("full", "partial", "none")


def context(record: dict[str, Any]) -> str:
    value = record.get("id")
    return value if isinstance(value, str) and value.isprintable() else "<unknown>"


def read_objects(path: Path, kind: str) -> tuple[list[tuple[int, dict]], list[Diagnostic]]:
    objects, errors = [], []
    try:
        with path.open(encoding="utf-8") as stream:
            lines = list(stream)
    except (OSError, UnicodeError) as problem:
        return [], [Diagnostic(0, "<unknown>", f"{kind}: cannot read {path}: {problem}")]
    for line, text in enumerate(lines, 1):
        if not text.strip():
            errors.append(Diagnostic(line, "<unknown>", f"{kind}: blank JSONL line"))
            continue
        try:
            record = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_object)
        except ValueError as problem:
            errors.append(Diagnostic(line, "<unknown>", f"{kind}: invalid JSON: {problem}"))
            continue
        if not isinstance(record, dict):
            errors.append(Diagnostic(line, "<unknown>", f"{kind}: expected a JSON object"))
            continue
        objects.append((line, record))
    return objects, errors


def read_questions(path: Path) -> tuple[list[dict], list[Diagnostic]]:
    objects, errors = read_objects(path, "Questions")
    questions, seen = [], set()
    required = {"id", "course_id", "language", "question", "answerable", "evidence", "answer"}
    for line, question in objects:
        start = len(errors)

        def error(message: str) -> None:
            errors.append(Diagnostic(line, context(question), "Questions: " + message))

        for key in sorted(required - question.keys()):
            error(f"missing key '{key}'")
        for key in ("id", "course_id", "language", "question"):
            if key in question and (not isinstance(question[key], str) or not question[key].strip()):
                error(f"'{key}' must be a non-empty string")
        if "answerable" in question and type(question["answerable"]) is not bool:
            error("'answerable' must be a boolean")
        if "evidence" in question and not isinstance(question["evidence"], list):
            error("'evidence' must be a list")
        for key in ("answer", "notes"):
            if key in question and question[key] is not None and not isinstance(question[key], str):
                error(f"'{key}' must be a string or null")
        if len(errors) != start:
            continue
        if not re.fullmatch(r"q[0-9]{3}", question["id"]) or question["id"] == "q000":
            error("id must be q001 through q999")
        if question["id"] in seen:
            error("duplicate id")
        seen.add(question["id"])
        if not re.fullmatch(r"[0-9]+", question["course_id"]):
            error("course_id must be a numeric MAIS identifier")
        if question["language"] not in {"sk", "en"}:
            error("language must be sk or en")
        if question["answerable"]:
            if not question["evidence"]:
                error("answerable question requires evidence")
            if not isinstance(question["answer"], str) or not question["answer"].strip():
                error("answerable question requires a non-empty answer")
        elif question["evidence"] or question["answer"] is not None:
            error("not-answerable question requires evidence: [] and answer: null")
        for index, evidence in enumerate(question["evidence"]):
            if not isinstance(evidence, dict) or any(
                not isinstance(evidence.get(key), str) or not evidence[key].strip()
                for key in ("section", "quote")
            ):
                error(f"evidence {index} requires non-empty section and quote strings")
        if len(errors) == start:
            questions.append(question)
    if not objects and not errors:
        errors.append(Diagnostic(0, "<unknown>", "Questions: file must not be empty"))
    return questions, errors


def read_results(path: Path, question_ids: set[str]) -> tuple[dict[str, dict], list[Diagnostic], list[Diagnostic]]:
    objects, errors = read_objects(path, "Results")
    results, warnings, seen = {}, [], set()
    for line, record in objects:
        start = len(errors)

        def error(message: str) -> None:
            errors.append(Diagnostic(line, context(record), "Results: " + message))

        for key in sorted({"id", "found", "answer", "sources"} - record.keys()):
            error(f"missing key '{key}'")
        if "id" in record:
            if not isinstance(record["id"], str):
                error("'id' must be a string")
            else:
                if record["id"] not in question_ids:
                    error(f"unknown id '{record['id']}'")
                if record["id"] in seen:
                    error(f"duplicate id '{record['id']}'")
                seen.add(record["id"])
        if "found" in record and type(record["found"]) is not bool:
            error("'found' must be a boolean")
        if "answer" in record:
            if record["answer"] is not None and not isinstance(record["answer"], str):
                error("'answer' must be a string or null")
            elif record.get("found") is True and (
                not isinstance(record["answer"], str) or not record["answer"].strip()
            ):
                error("found: true requires a non-empty answer")
        if "sources" in record:
            if not isinstance(record["sources"], list):
                error("'sources' must be a list")
            else:
                for index, source in enumerate(record["sources"]):
                    if not isinstance(source, dict):
                        error(f"source {index} must be an object")
                        continue
                    for key in sorted({"section", "quote"} - source.keys()):
                        error(f"source {index} missing key '{key}'")
                    if "section" in source and source["section"] is not None and not isinstance(source["section"], str):
                        error(f"source {index} section must be a string or null")
                    if "quote" in source and not isinstance(source["quote"], str):
                        error(f"source {index} quote must be a string")
        if len(errors) == start:
            # Metadata is deliberately ignored; keep only the scoring contract.
            results[record["id"]] = {"found": record["found"], "answer": record["answer"],
                                     "sources": [{"section": s["section"], "quote": s["quote"]}
                                                 for s in record["sources"]]}
            if not record["found"] and record["sources"]:
                warnings.append(Diagnostic(line, record["id"], "Sources on found: false are ignored"))
    return results, errors, warnings


def citation_matches(expected: dict, source: dict) -> bool:
    if source["section"] != expected["section"]:
        return False
    expected_quote = collapse_whitespace(expected["quote"])
    cited_quote = collapse_whitespace(source["quote"])
    return bool(cited_quote and expected_quote and
                (expected_quote in cited_quote or cited_quote in expected_quote))


def ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "percent": round(100 * numerator / denominator, 1) if denominator else 0.0}


def breakdown(rows: list[dict]) -> dict:
    counts = Counter(row["outcome"] for row in rows)
    return {"questions": len(rows), "outcomes": {key: counts[key] for key in OUTCOMES},
            "full": sum(row["citation"] == "full" for row in rows)}


def score_questions(questions: list[dict], results: dict[str, dict], names: dict[str, str],
                    warning_count: int = 0) -> dict:
    rows = []
    for question in questions:
        result = results.get(question["id"])
        if result is None:
            outcome = "missing"
        elif question["answerable"]:
            outcome = "answered" if result["found"] else "missed"
        else:
            outcome = "invented" if result["found"] else "abstained"
        matched, citation = [], None
        if outcome == "answered":
            matched = [i for i, evidence in enumerate(question["evidence"])
                       if any(citation_matches(evidence, source) for source in result["sources"])]
            citation = "full" if len(matched) == len(question["evidence"]) else "partial" if matched else "none"
        rows.append({"id": question["id"], "course_id": question["course_id"],
                     "language": question["language"], "answerable": question["answerable"],
                     "outcome": outcome, "citation": citation, "matched_evidence": matched})
    outcomes = breakdown(rows)["outcomes"]
    citations = Counter(row["citation"] for row in rows if row["outcome"] == "answered")
    answerable = sum(q["answerable"] for q in questions)
    not_answerable = len(questions) - answerable
    summary = {"questions": len(questions), "results": len(results), "missing": outcomes["missing"],
               "answerable": answerable, "not_answerable": not_answerable,
               "outcomes": outcomes, "citations": {key: citations[key] for key in CITATIONS},
               "decision_accuracy": ratio(outcomes["answered"] + outcomes["abstained"], len(questions)),
               "invented_rate": ratio(outcomes["invented"], not_answerable),
               "missed_rate": ratio(outcomes["missed"], answerable),
               "citation_accuracy": ratio(citations["full"], outcomes["answered"]),
               "overall_correct": ratio(outcomes["abstained"] + citations["full"], len(questions)),
               "warnings": warning_count}
    by_course = {course: {"name": names[course], **breakdown([r for r in rows if r["course_id"] == course])}
                 for course in sorted({q["course_id"] for q in questions})}
    by_language = {lang: breakdown([r for r in rows if r["language"] == lang]) for lang in ("sk", "en")}
    return {"summary": summary, "by_course": by_course, "by_language": by_language, "questions": rows}


def course_names(questions: list[dict], data: Path) -> tuple[dict[str, str], list[Diagnostic]]:
    names, warnings = {}, []
    for question in questions:
        course = question["course_id"]
        if course in names:
            continue
        try:
            name = json.loads((data / "courses" / f"{course}.json").read_text(encoding="utf-8"))["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name must be a non-empty string")
            names[course] = name
        except (OSError, ValueError, TypeError, KeyError):
            names[course] = course
            warnings.append(Diagnostic(0, question["id"], f"Course name unavailable for {course}; using its id"))
    return names, warnings


def percentage(metric: dict) -> str:
    return f"{metric['numerator']} / {metric['denominator']} ({metric['percent']:.1f} %)"


def shortened(value: str | None, limit: int) -> str:
    if value is None:
        return "(null)"
    value = collapse_whitespace(value)
    return value if len(value) <= limit else value[:limit - 3] + "..."


def render_report(report: dict, questions: list[dict], results: dict[str, dict], show_answers: bool) -> str:
    summary = report["summary"]
    counts, citations = summary["outcomes"], summary["citations"]
    lines = ["Evaluation report (decisions and citations; answer wording is not scored)",
             f"Questions: {summary['questions']}; results: {summary['results']}; missing: {summary['missing']}",
             "Decision outcomes: " + ", ".join(f"{key}={counts[key]}" for key in OUTCOMES),
             "Decision accuracy: " + percentage(summary["decision_accuracy"]),
             "Invented: " + percentage(summary["invented_rate"]),
             "Missed: " + percentage(summary["missed_rate"]),
             "Citations among answered: " + ", ".join(f"{key}={citations[key]}" for key in CITATIONS),
             "Citation accuracy: " + percentage(summary["citation_accuracy"]),
             "Overall correct: " + percentage(summary["overall_correct"]),
             f"Warnings: {summary['warnings']}", "", "By course:"]
    for course, group in report["by_course"].items():
        lines.append(f"  {course} | {group['name']} | questions={group['questions']} | " +
                     ", ".join(f"{key}={group['outcomes'][key]}" for key in OUTCOMES) + f" | full={group['full']}")
    lines.append("By language:")
    for language, group in report["by_language"].items():
        lines.append(f"  {language} | questions={group['questions']} | " +
                     ", ".join(f"{key}={group['outcomes'][key]}" for key in OUTCOMES) + f" | full={group['full']}")
    lines.extend(["", "Problems:"])
    question_map = {q["id"]: q for q in questions}
    problems = [r for r in report["questions"] if r["outcome"] != "abstained" and r["citation"] != "full"]
    if not problems:
        lines.append("  (none)")
    for row in problems:
        question, result = question_map[row["id"]], results.get(row["id"])
        course = row["course_id"]
        label = row["outcome"] + (f" / {row['citation']}" if row["citation"] else "")
        lines.extend([f"  {row['id']} | {course} {report['by_course'][course]['name']} | {row['language']} | {label}",
                      "    Question: " + question["question"], "    Expected evidence:"])
        lines.extend(f"      [{i}] {e['section']}: {collapse_whitespace(e['quote'])}"
                     for i, e in enumerate(question["evidence"]))
        if not question["evidence"]:
            lines.append("      (none)")
        lines.append("    Cited sources:")
        sources = result["sources"] if result else []
        lines.extend(f"      {s['section'] if s['section'] is not None else '<no section>'}: {shortened(s['quote'], 120)}"
                     for s in sources)
        if not sources:
            lines.append("      (none)")
        lines.append("    Assistant answer: " + shortened(result["answer"] if result else None, 200))
    if show_answers:
        lines.extend(["", "Answered questions: expected / actual wording (human review only)"])
        for row in report["questions"]:
            if row["outcome"] == "answered":
                lines.extend([f"  {row['id']}", "    Expected: " + question_map[row["id"]]["answer"],
                              "    Actual:   " + results[row["id"]]["answer"]])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=ROOT / "data/eval/questions.jsonl")
    parser.add_argument("--data", type=Path, default=ROOT / "data/mais/2026-27", help="Course names only")
    parser.add_argument("--json", type=Path, dest="json_path")
    parser.add_argument("--show-answers", action="store_true")
    args = parser.parse_args(argv)
    if args.json_path and args.json_path.resolve() in {args.results.resolve(), args.questions.resolve()}:
        parser.error("--json must not overwrite an input file")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    questions, errors = read_questions(args.questions)
    results, result_errors, warnings = read_results(args.results, {q["id"] for q in questions})
    errors.extend(result_errors)
    if errors:
        for error in sorted(errors, key=lambda item: item.line):
            print(error.format("ERROR"))
        return 1
    names, name_warnings = course_names(questions, args.data)
    warnings.extend(name_warnings)
    report = score_questions(questions, results, names, len(warnings))
    if args.json_path:
        try:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
        except OSError as problem:
            print(Diagnostic(0, "<unknown>", f"Cannot write report: {problem}").format("ERROR"))
            return 1
    for warning in warnings:
        print(warning.format("WARNING"))
    print(render_report(report, questions, results, args.show_answers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
