"""Synthetic scorer regressions and baselines built from the real question set."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_score", ROOT / "scripts/eval/score.py")
score = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = score
sys.path.insert(0, str(ROOT / "scripts/eval"))
try:
    SPEC.loader.exec_module(score)
finally:
    sys.path.pop(0)

PH = "Priebežné hodnotenie (PH)"
ZH = "Záverečné hodnotenie (ZH)"


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def question(identifier="q001", answerable=True, language="sk", course="101", evidence=None):
    return {"id": identifier, "course_id": course, "language": language,
            "question": "koľko treba na zápočet?", "answerable": answerable,
            "evidence": (evidence if evidence is not None else [{"section": PH, "quote": "min. 21% zo 40%."}]) if answerable else [],
            "answer": "Aspoň 21 % zo 40 %." if answerable else None, "notes": "Synthetic test question."}


def result(identifier="q001", found=True, sources=None):
    return {"id": identifier, "found": found, "answer": "Syntetická odpoveď." if found else None,
            "sources": sources if sources is not None else ([{"section": PH, "quote": "min. 21% zo 40%."}] if found else []),
            "testovacie": True}


@pytest.fixture
def files(tmp_path):
    data = tmp_path / "mais"
    (data / "courses").mkdir(parents=True)
    for course, name in (("101", "Skúšobný predmet"), ("102", "Druhý skúšobný predmet")):
        (data / "courses" / f"{course}.json").write_text(json.dumps({"name": name}, ensure_ascii=False), encoding="utf-8")
    questions, results = tmp_path / "questions.jsonl", tmp_path / "results.jsonl"
    write_jsonl(questions, [question()])
    write_jsonl(results, [result()])
    return questions, results, data


def arguments(files, *extra):
    questions, results, data = files
    return ["--questions", str(questions), "--results", str(results), "--data", str(data), *extra]


def load_report(files):
    questions, errors = score.read_questions(files[0])
    assert errors == []
    results, errors, warnings = score.read_results(files[1], {q["id"] for q in questions})
    assert errors == []
    names, name_warnings = score.course_names(questions, files[2])
    return score.score_questions(questions, results, names, len(warnings + name_warnings))


@pytest.mark.parametrize(("answerable", "found", "outcome", "citation"), [
    (True, True, "answered", "full"), (True, False, "missed", None),
    (False, True, "invented", None), (False, False, "abstained", None),
])
def test_each_decision(files, answerable, found, outcome, citation):
    write_jsonl(files[0], [question(answerable=answerable)])
    write_jsonl(files[1], [result(found=found)])
    report = load_report(files)
    assert report["questions"][0]["outcome"] == outcome
    assert report["questions"][0]["citation"] == citation
    assert report["summary"]["outcomes"][outcome] == 1


def test_empty_results_are_all_missing(files, capsys):
    files[1].write_text("", encoding="utf-8")
    report = load_report(files)
    assert report["summary"]["missing"] == 1
    assert report["summary"]["results"] == 0
    assert report["summary"]["overall_correct"]["percent"] == 0.0
    assert report["questions"][0]["citation"] is None
    assert score.main(arguments(files)) == 0
    assert "missing=1" in capsys.readouterr().out


@pytest.mark.parametrize(("section", "quote", "expected"), [
    (PH, "Podmienka: min. 21% zo 40%. Hotovo.", True),
    (PH, "21% zo 40%", True),
    (PH, "min. 21% zo 40%.", True),
    (ZH, "min. 21% zo 40%.", False),
    (PH + " ", "min. 21% zo 40%.", False),
    (None, "min. 21% zo 40%.", False),
    (PH, "", False), (PH, "\n\t\u00a0", False),
    (PH, "min.\n21%\u00a0zo\t40%.", True),
    (PH, "min.\u202821% zo 40%.", True),
    (PH, "Min. 21% zo 40%.", False),
    (PH, "min. 22% zo 40%.", False),
])
def test_citation_rules(files, section, quote, expected):
    write_jsonl(files[1], [result(sources=[{"section": section, "quote": quote}])])
    row = load_report(files)["questions"][0]
    assert row["citation"] == ("full" if expected else "none")
    assert row["matched_evidence"] == ([0] if expected else [])


def test_diacritics_and_punctuation_are_exact(files):
    write_jsonl(files[0], [question(evidence=[{"section": PH, "quote": "Práca, skúška."}])])
    for quote in ("Praca, skúška.", "Práca; skúška."):
        write_jsonl(files[1], [result(sources=[{"section": PH, "quote": quote}])])
        assert load_report(files)["questions"][0]["citation"] == "none"


def test_multiple_evidence_and_sources_are_independent(files):
    write_jsonl(files[0], [question(evidence=[{"section": PH, "quote": "min. 21% zo 40%."},
                                             {"section": ZH, "quote": "min. 31% zo 60%."}])])
    report = load_report(files)
    assert report["questions"][0]["citation"] == "partial"
    assert report["questions"][0]["matched_evidence"] == [0]
    write_jsonl(files[1], [result(sources=[{"section": ZH, "quote": "min. 31% zo 60%."},
                                          {"section": PH, "quote": "min. 21% zo 40%."}])])
    assert load_report(files)["questions"][0]["matched_evidence"] == [0, 1]
    assert load_report(files)["questions"][0]["citation"] == "full"


def test_one_source_can_match_multiple_expected_items(files):
    write_jsonl(files[0], [question(evidence=[{"section": PH, "quote": "zápočet"},
                                             {"section": PH, "quote": "21%"}])])
    write_jsonl(files[1], [result(sources=[{"section": PH, "quote": "Na zápočet treba 21%."}])])
    assert load_report(files)["questions"][0]["citation"] == "full"


def test_false_found_sources_ignored_but_warned(files, capsys):
    write_jsonl(files[1], [result(found=False, sources=[{"section": PH, "quote": "min. 21% zo 40%."}])])
    assert score.main(arguments(files)) == 0
    output = capsys.readouterr().out
    assert "WARNING line 1 [q001]: Sources on found: false are ignored" in output
    report = load_report(files)
    assert report["summary"]["warnings"] == 1
    assert report["questions"][0]["outcome"] == "missed"
    assert report["questions"][0]["matched_evidence"] == []


@pytest.mark.parametrize("key", ["id", "found", "answer", "sources"])
def test_missing_result_key(files, key, capsys, tmp_path):
    row = result()
    del row[key]
    write_jsonl(files[1], [row])
    target = tmp_path / "report.json"
    assert score.main(arguments(files, "--json", str(target))) == 1
    output = capsys.readouterr().out
    assert "ERROR line 1 [" in output and f"missing key '{key}'" in output
    assert "Evaluation report" not in output
    assert not target.exists()


@pytest.mark.parametrize(("key", "value", "message"), [
    ("id", 1, "'id' must be a string"),
    ("found", 1, "'found' must be a boolean"),
    ("found", "false", "'found' must be a boolean"),
    ("answer", 2, "'answer' must be a string or null"),
    ("answer", None, "requires a non-empty answer"),
    ("answer", " ", "requires a non-empty answer"),
    ("sources", {}, "'sources' must be a list"),
    ("sources", [None], "source 0 must be an object"),
    ("sources", [{"quote": "x"}], "source 0 missing key 'section'"),
    ("sources", [{"section": PH}], "source 0 missing key 'quote'"),
    ("sources", [{"section": False, "quote": "x"}], "section must be a string or null"),
    ("sources", [{"section": PH, "quote": None}], "quote must be a string"),
])
def test_wrong_result_types(files, key, value, message, capsys):
    row = result()
    row[key] = value
    write_jsonl(files[1], [row])
    assert score.main(arguments(files)) == 1
    output = capsys.readouterr().out
    assert "ERROR line 1 [" in output and message in output


@pytest.mark.parametrize(("bad_line", "message"), [
    ("{broken", "invalid JSON"), ("[]", "expected a JSON object"),
    ("null", "expected a JSON object"), ("", "blank JSONL line"),
    ('{"id":"q001","id":"q002"}', "Duplicate JSON key"),
    ('{"id":NaN}', "Non-JSON constant"),
])
def test_invalid_json_has_correct_line(files, bad_line, message, capsys):
    files[1].write_text(json.dumps(result()) + "\n" + bad_line + "\n", encoding="utf-8")
    assert score.main(arguments(files)) == 1
    output = capsys.readouterr().out
    assert "ERROR line 2 [<unknown>]" in output and message in output
    assert "Evaluation report" not in output


def test_duplicate_and_unknown_ids_and_all_errors(files, capsys):
    files[1].write_text(json.dumps(result()) + "\n" + json.dumps(result()) + "\n" +
                        json.dumps(result("q999")) + "\n\n{broken\n", encoding="utf-8")
    assert score.main(arguments(files)) == 1
    output = capsys.readouterr().out
    assert "ERROR line 2 [q001]: Results: duplicate id" in output
    assert "ERROR line 3 [q999]: Results: unknown id" in output
    assert "ERROR line 4 [<unknown>]: Results: blank" in output
    assert "ERROR line 5 [<unknown>]: Results: invalid JSON" in output
    assert output.index("line 2") < output.index("line 3") < output.index("line 4") < output.index("line 5")


def test_extra_keys_are_ignored(files):
    row = result()
    row["runner_metadata"] = {"model": "synthetic-test", "attempt": 1}
    row["sources"][0].update(type="sheet", metadata={"rank": 1})
    write_jsonl(files[1], [row])
    parsed, errors, _ = score.read_results(files[1], {"q001"})
    assert errors == []
    assert set(parsed["q001"]) == {"found", "answer", "sources"}
    assert set(parsed["q001"]["sources"][0]) == {"section", "quote"}
    assert load_report(files)["questions"][0]["citation"] == "full"


def test_synthetic_mixed_report(files, tmp_path, capsys):
    qs = [question(f"q{i:03}", answerable=i not in (5, 6),
                   language="en" if i in (2, 6) else "sk", course="101" if i <= 3 else "102")
          for i in range(1, 8)]
    qs[1]["evidence"].append({"section": ZH, "quote": "min. 31% zo 60%."})
    write_jsonl(files[0], qs)
    write_jsonl(files[1], [result("q001"), result("q002"), result("q003", sources=[]),
                          result("q004", found=False), result("q005", found=False), result("q006")])
    target = tmp_path / "nested/report.json"
    assert score.main(arguments(files, "--json", str(target), "--show-answers")) == 0
    report = json.loads(target.read_text(encoding="utf-8"))
    assert set(report) == {"summary", "by_course", "by_language", "questions"}
    summary = report["summary"]
    assert summary["questions"] == 7 and summary["results"] == 6 and summary["missing"] == 1
    assert summary["outcomes"] == {"answered": 3, "missed": 1, "abstained": 1, "invented": 1, "missing": 1}
    assert summary["citations"] == {"full": 1, "partial": 1, "none": 1}
    assert summary["decision_accuracy"] == {"numerator": 4, "denominator": 7, "percent": 57.1}
    assert summary["citation_accuracy"] == {"numerator": 1, "denominator": 3, "percent": 33.3}
    assert summary["overall_correct"] == {"numerator": 2, "denominator": 7, "percent": 28.6}
    assert summary["invented_rate"]["denominator"] == 2
    assert summary["missed_rate"]["denominator"] == 5
    assert report["by_course"]["101"]["name"] == "Skúšobný predmet"
    assert report["by_course"]["101"]["outcomes"]["answered"] == 3
    assert report["by_language"]["en"]["outcomes"]["invented"] == 1
    assert set(report["questions"][0]) == {"id", "course_id", "language", "answerable", "outcome", "citation", "matched_evidence"}
    output = capsys.readouterr().out
    assert "Overall correct: 2 / 7 (28.6 %)" in output
    assert "Citation accuracy: 1 / 3 (33.3 %)" in output
    problems = output.split("Problems:\n")[1].split("Answered questions:")[0]
    for identifier in ("q002", "q003", "q004", "q006", "q007"):
        assert identifier in problems
    assert "q001" not in problems and "q005" not in problems
    assert output.count("    Expected:") == 3 and output.count("    Actual:") == 3


@pytest.mark.parametrize("perfect", [True, False])
def test_real_set_baselines(tmp_path, perfect, capsys):
    questions = [json.loads(line) for line in (ROOT / "data/eval/questions.jsonl").read_text(encoding="utf-8").splitlines()]
    records = [{"id": q["id"], "found": q["answerable"] if perfect else False,
                "answer": q["answer"] if perfect else None,
                "sources": q["evidence"] if perfect else [], "testovacie": True} for q in questions]
    results, target = tmp_path / "baseline.jsonl", tmp_path / "report.json"
    write_jsonl(results, records)
    assert score.main(["--results", str(results), "--json", str(target)]) == 0
    summary = json.loads(target.read_text(encoding="utf-8"))["summary"]
    assert summary["questions"] == 40 and summary["results"] == 40
    assert summary["outcomes"]["invented"] == 0
    if perfect:
        assert summary["overall_correct"] == {"numerator": 40, "denominator": 40, "percent": 100.0}
        assert summary["citations"]["full"] == 30
        assert "Problems:\n  (none)" in capsys.readouterr().out
    else:
        assert summary["outcomes"] == {"answered": 0, "missed": 30, "abstained": 10, "invented": 0, "missing": 0}
        assert summary["citation_accuracy"] == {"numerator": 0, "denominator": 0, "percent": 0.0}
        assert summary["overall_correct"]["percent"] == 25.0


def test_answer_wording_is_not_scored(files):
    row = result()
    row["answer"] = "Deliberately unrelated synthetic wording."
    write_jsonl(files[1], [row])
    assert load_report(files)["summary"]["overall_correct"]["percent"] == 100.0


def test_missing_course_names_do_not_affect_scores(files, capsys):
    (files[2] / "courses/101.json").unlink()
    report = load_report(files)
    assert report["summary"]["overall_correct"]["percent"] == 100.0
    assert report["by_course"]["101"]["name"] == "101"
    assert score.main(arguments(files)) == 0
    assert "Course name unavailable" in capsys.readouterr().out


def test_invalid_input_keeps_existing_json_report(files, tmp_path, capsys):
    target = tmp_path / "existing.json"
    target.write_text("previous report", encoding="utf-8")
    files[1].write_text("{broken\n", encoding="utf-8")
    assert score.main(arguments(files, "--json", str(target))) == 1
    assert target.read_text(encoding="utf-8") == "previous report"


def test_wrong_cli_arguments_exit_two(files):
    with pytest.raises(SystemExit) as error:
        score.main([])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        score.main(arguments(files, "--json", str(files[1])))
    assert error.value.code == 2


def test_redirected_utf8_and_standard_library_only(files, tmp_path):
    write_jsonl(files[1], [result(sources=[])])
    environment = os.environ.copy()
    environment.update(PYTHONIOENCODING="cp1251", PYTHONUTF8="0")
    target = tmp_path / "stdout.txt"
    with target.open("wb") as stream:
        completed = subprocess.run([sys.executable, "-S", str(ROOT / "scripts/eval/score.py"),
                                    *arguments(files), "--show-answers"], stdout=stream,
                                   stderr=subprocess.PIPE, env=environment)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    text = target.read_bytes().decode("utf-8")
    assert "Skúšobný predmet" in text and "koľko treba na zápočet?" in text
    assert "Priebežné hodnotenie (PH)" in text


def test_problem_previews_are_shortened(files, capsys):
    row = result(sources=[{"section": None, "quote": "z" * 500}])
    row["answer"] = "a" * 500
    write_jsonl(files[1], [row])
    assert score.main(arguments(files)) == 0
    output = capsys.readouterr().out
    assert "z" * 117 + "..." in output and "z" * 118 not in output
    assert "a" * 197 + "..." in output and "a" * 198 not in output


@pytest.mark.parametrize("bad_question", [None, {"id": "q001"}, question(evidence=[]),
                                          {**question(), "answerable": 1}])
def test_invalid_questions_fail_without_report(files, bad_question, capsys):
    write_jsonl(files[0], [bad_question])
    assert score.main(arguments(files)) == 1
    assert "Evaluation report" not in capsys.readouterr().out
