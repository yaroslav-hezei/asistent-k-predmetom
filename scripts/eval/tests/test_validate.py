"""Tests of the dataset contract and validator diagnostics using tiny source fixtures."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_validate", ROOT / "scripts/eval/validate.py")
validate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate
SPEC.loader.exec_module(validate)


@pytest.fixture
def sources(tmp_path):
    data = tmp_path / "mais"
    courses = data / "courses"
    courses.mkdir(parents=True)
    # Include a state-exam course and a linked prerequisite. Only P/PV/V qualify.
    programs = [{"program_id": "65669424", "plan": [
        {"predmet_id": "101", "type": "P", "block": "plan"},
        {"predmet_id": "102", "type": "PV", "block": "plan"},
        {"predmet_id": "103", "type": "V", "block": "plan"},
        {"predmet_id": "104", "type": "P", "block": "state_exam"},
        {"predmet_id": "105", "type": "Prerekvizita", "block": "plan"},
        {"predmet_id": "106", "type": "Zameniteľný", "block": "plan"},
    ]}]
    (data / "programs.json").write_text(json.dumps(programs), encoding="utf-8")
    sheet = {"sections": [
        {"label": "Priebežné hodnotenie (PH)", "text": "Za projekt:\n  najmenej\t21 % zo 40 %."},
        {"label": "Stručná osnova predmetu", "text": "Matice a determinanty riešime na cvičení. " + "x" * 301},
        {"label": "Podmienky na absolvovanie predmetu", "text": ""},
    ]}
    for course in ("101", "102", "103", "104", "105", "106", "999"):
        (courses / f"{course}.json").write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")
    return data


@pytest.fixture
def question():
    return {
        "id": "q001", "course_id": "101", "language": "sk",
        "question": "kolko musim mat za projekt?", "answerable": True,
        "evidence": [{"section": "Priebežné hodnotenie (PH)", "quote": "najmenej 21 % zo 40 %."}],
        "answer": "Aspoň 21 % zo 40 %.", "notes": None,
    }


def run(tmp_path, sources, records):
    questions = tmp_path / "questions.jsonl"
    questions.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    return validate.validate_file(questions, sources)


def messages(result):
    return "\n".join(d.message for d in result.errors)


def test_real_set_contract_and_evidence():
    questions = ROOT / "data/eval/questions.jsonl"
    result = validate.validate_file(questions, ROOT / "data/mais/2026-27")
    assert result.errors == []
    assert result.warnings == []
    rows = result.questions
    assert len(rows) == 40
    assert [q["id"] for q in rows] == [f"q{i:03}" for i in range(1, 41)]
    counts = Counter(q["course_id"] for q in rows)
    assert len(counts) == 10 and set(counts.values()) == {4}
    assert {"65954478", "69574272"} <= set(counts)
    assert Counter(q["language"] for q in rows) == {"sk": 35, "en": 5}
    assert sum(q["answerable"] for q in rows) == 30
    for course in counts:
        assert Counter(q["answerable"] for q in rows if q["course_id"] == course) == {True: 3, False: 1}
    assert all(set(q) == validate.FIELDS for q in rows)


@pytest.mark.parametrize("field", sorted(validate.REQUIRED))
def test_missing_fields(tmp_path, sources, question, field):
    del question[field]
    result = run(tmp_path, sources, [question])
    assert f"Missing field '{field}'" in messages(result)
    assert all(d.line == 1 for d in result.errors)
    assert all(d.question_id == ("<unknown>" if field == "id" else "q001") for d in result.errors)


@pytest.mark.parametrize(("field", "value"), [
    ("id", 1), ("course_id", 101), ("language", ["sk"]), ("question", None),
    ("answerable", 1), ("evidence", {}), ("answer", 42), ("notes", False),
    ("id", ""), ("course_id", " "), ("question", "\t"),
])
def test_wrong_field_types(tmp_path, sources, question, field, value):
    question[field] = value
    result = run(tmp_path, sources, [question])
    assert f"Field '{field}' must be" in messages(result)
    assert result.errors[0].line == 1


def test_notes_may_be_omitted(tmp_path, sources, question):
    del question["notes"]
    assert run(tmp_path, sources, [question]).errors == []


def test_unknown_field_rejected(tmp_path, sources, question):
    question["topic"] = "grading"
    assert "Unknown field 'topic'" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize("bad_id", ["q000", "q1000", "Q001", "q01", "q１２３", "wrong"])
def test_invalid_id(tmp_path, sources, question, bad_id):
    question["id"] = bad_id
    assert "ID must be q001 through q999" in messages(run(tmp_path, sources, [question]))


def test_duplicate_id_reports_line_and_id(tmp_path, sources, question):
    result = run(tmp_path, sources, [question, question])
    duplicate = next(d for d in result.errors if "Duplicate id" in d.message)
    assert duplicate.line == 2 and duplicate.question_id == "q001"


def test_unsorted_ids(tmp_path, sources, question):
    other = deepcopy(question)
    question["id"], other["id"] = "q002", "q001"
    assert "sorted in ascending order" in messages(run(tmp_path, sources, [question, other]))


@pytest.mark.parametrize("course", ["999", "105", "106", "../../escape"])
def test_course_outside_eligible_rows(tmp_path, sources, question, course):
    question["course_id"] = course
    assert "not in P / PV / V rows" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize("course", ["101", "102", "103", "104"])
def test_p_pv_v_and_state_exam_courses_accepted(tmp_path, sources, question, course):
    question["course_id"] = course
    assert run(tmp_path, sources, [question]).errors == []


def test_missing_sheet(tmp_path, sources, question):
    (sources / "courses/101.json").unlink()
    result = run(tmp_path, sources, [question])
    assert "Cannot read course sheet '101'" in messages(result)
    assert result.errors[0].line == 1 and result.errors[0].question_id == "q001"


def test_invalid_language(tmp_path, sources, question):
    question["language"] = "uk"
    assert "Language must be 'sk' or 'en'" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize("answer", [None, "", "\t"])
def test_answerable_requires_answer(tmp_path, sources, question, answer):
    question["answer"] = answer
    assert "requires a non-empty answer" in messages(run(tmp_path, sources, [question]))


def test_answerable_requires_evidence(tmp_path, sources, question):
    question["evidence"] = []
    assert "Answerable question requires evidence" in messages(run(tmp_path, sources, [question]))


def test_not_answerable_rejects_evidence(tmp_path, sources, question):
    question.update(answerable=False, answer=None)
    assert "Not-answerable question must have empty evidence" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize("answer", ["Invented answer", ""])
def test_not_answerable_requires_null_answer(tmp_path, sources, question, answer):
    question.update(answerable=False, evidence=[], answer=answer)
    assert "Not-answerable question must have answer: null" in messages(run(tmp_path, sources, [question]))


def test_not_answerable_accepted(tmp_path, sources, question):
    question.update(answerable=False, evidence=[], answer=None,
                    notes="The fixture gives no project deadline.")
    assert run(tmp_path, sources, [question]).errors == []


@pytest.mark.parametrize("evidence", [None, "a quote", {}, {"section": "PH"},
                                       {"section": "PH", "quote": "x", "extra": 1}])
def test_evidence_shape(tmp_path, sources, question, evidence):
    question["evidence"] = [evidence]
    assert "must be an object with exactly 'section' and 'quote'" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize(("field", "value"), [("section", 2), ("quote", None),
                                             ("quote", "\n"), ("section", "")])
def test_evidence_field_types(tmp_path, sources, question, field, value):
    question["evidence"][0][field] = value
    assert "section and quote must be non-empty strings" in messages(run(tmp_path, sources, [question]))


def test_unknown_section(tmp_path, sources, question):
    question["evidence"][0]["section"] = "Wrong label"
    assert "unknown section 'Wrong label'" in messages(run(tmp_path, sources, [question]))


def test_quote_must_be_in_named_section(tmp_path, sources, question):
    question["evidence"][0]["section"] = "Podmienky na absolvovanie predmetu"
    assert "quote does not occur in section" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize(("section", "quote"), [
    ("Priebežné hodnotenie (PH)", "najmenej 22 %"),
    ("Priebežné hodnotenie (PH)", "Najmenej 21 %"),
    ("Stručná osnova predmetu", "riesime"),
])
def test_wrong_quote_case_and_diacritics_rejected(tmp_path, sources, question, section, quote):
    question["evidence"] = [{"section": section, "quote": quote}]
    assert "quote does not occur in section" in messages(run(tmp_path, sources, [question]))


@pytest.mark.parametrize("length", [300, 301])
def test_quote_length_boundary(tmp_path, sources, question, length):
    question["evidence"] = [{"section": "Stručná osnova predmetu", "quote": "x" * length}]
    result = run(tmp_path, sources, [question])
    assert ("quote exceeds 300 characters" in messages(result)) is (length > 300)
    assert bool(result.errors) is (length > 300)


def test_quote_whitespace_collapsed_both_ways(tmp_path, sources, question):
    question["evidence"][0]["quote"] = "projekt:\t najmenej\n21\u00a0 %  zo\r\n40 %."
    assert run(tmp_path, sources, [question]).errors == []


def test_copy_warning_is_case_insensitive_and_not_an_error(tmp_path, sources, question):
    question["question"] = "Matice, A DETERMINANTY riešime na skúške?"
    result = run(tmp_path, sources, [question])
    assert result.errors == []
    warning = next(d for d in result.warnings if "5 or more consecutive words" in d.message)
    assert warning.line == 1 and warning.question_id == "q001"


def test_four_shared_words_do_not_trigger_copy_warning(tmp_path, sources, question):
    question["question"] = "matice a determinanty riešime doma?"
    assert not any("consecutive words" in d.message for d in run(tmp_path, sources, [question]).warnings)


def test_course_count_warning_only(tmp_path, sources, question):
    result = run(tmp_path, sources, [question])
    assert result.errors == []
    assert any("Course 101 has 1 question(s); expected 4" in d.message for d in result.warnings)


@pytest.mark.parametrize(("line", "expected"), [
    ("{broken", "Invalid JSON"), ("null", "Question must be a JSON object"),
    ("[]", "Question must be a JSON object"), ("42", "Question must be a JSON object"),
    ("", "Blank JSONL line is not allowed"), ('{"id": NaN}', "Invalid JSON"),
    ('{"id":"q001","id":"q002"}', "Duplicate JSON key"),
])
def test_invalid_json_or_record(tmp_path, sources, line, expected):
    questions = tmp_path / "invalid.jsonl"
    questions.write_text(line + "\n", encoding="utf-8")
    result = validate.validate_file(questions, sources)
    assert expected in messages(result)
    assert result.errors[0].line == 1 and result.errors[0].question_id == "<unknown>"


def test_cli_exit_codes_and_summary(tmp_path, sources, question, capsys):
    path = tmp_path / "cli.jsonl"
    path.write_text(json.dumps(question), encoding="utf-8")
    args = ["--data", str(sources), "--questions", str(path)]
    assert validate.main(args) == 0  # The course-size warning is non-fatal.
    output = capsys.readouterr().out
    assert "WARNING line 1 [q001]" in output
    assert "Questions: 1" in output and "Answerable: 1" in output
    assert "Not answerable: 0" in output and "sk: 1" in output and "en: 0" in output
    question["evidence"][0]["quote"] = "invented"
    path.write_text(json.dumps(question), encoding="utf-8")
    assert validate.main(args) == 1
    assert "ERROR line 1 [q001]" in capsys.readouterr().out


def test_empty_file_is_an_error(tmp_path, sources):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    result = validate.validate_file(path, sources)
    assert "Question file must not be empty" in messages(result)


def test_validator_runs_with_standard_library_only():
    completed = subprocess.run([sys.executable, "-I", "-S", str(ROOT / "scripts/eval/validate.py")],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Questions: 40" in completed.stdout
