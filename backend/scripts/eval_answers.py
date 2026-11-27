"""Ask the answering model the evaluation questions directly and score the answers.

    python scripts/eval_answers.py                  # all 40 questions (about 3 minutes)
    python scripts/eval_answers.py --ids q001,q004  # only these

Run from `backend/`. Needs GEMINI_API_KEY (environment or the repo's `.env`). No API, login or
database: each question goes to `app.answerer.answer_question` with its course's sheet, at most
REQUESTS_PER_MINUTE a minute (the free tier allows 15). The answers are written to
`scratch/eval/answers-<time>.jsonl` (repo root, gitignored) in the results format of
`scripts/eval/score.py`, which then prints the report. Also printed: time and tokens per answer.

Every run spends one request of the day's limit per question (500 a day on the free tier). The
whole path through the API, with login, is the evaluation runner of `scripts/eval/` (T-007); this
script is the quick loop for tuning the prompt.
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

from app import llm  # noqa: E402
from app.answerer import AnswerUnavailable, answer_question  # noqa: E402
from app.catalog import Catalog  # noqa: E402
from app.config import DEFAULT_MAIS_DATA_DIR, REPO_ROOT  # noqa: E402
from scripts.compare_embeddings import load_questions  # noqa: E402

REQUESTS_PER_MINUTE = 14
# Letters of Slovak that English never uses: an "English" answer with them copied Slovak text.
SLOVAK_LETTERS = re.compile(r"[áäčďéíĺľňóôŕšťúýž]", re.IGNORECASE)
OUT_DIR = REPO_ROOT / "scratch" / "eval"
SCORER = REPO_ROOT / "scripts" / "eval" / "score.py"
# Paid prices of the answering model per 1 M tokens (aistudio.google.com/docs/pricing,
# checked 2026-11-26): only to show what an answer would cost on the paid tier.
PAID_INPUT_PER_M = 0.30
PAID_OUTPUT_PER_M = 2.50


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ids", help="comma-separated question ids (default: all)")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")  # does not override variables already set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set (environment or .env in the repo root)")
        return 1

    questions = load_questions()
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q.id in wanted]
    catalog = Catalog.load(DEFAULT_MAIS_DATA_DIR)
    client = llm.make_client(api_key)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"answers-{datetime.now():%Y%m%d-%H%M%S}.jsonl"

    seconds, prompt_tokens, output_tokens, failed = [], [], [], []
    wrong_language: list[str] = []
    answered = 0
    gap = 60 / REQUESTS_PER_MINUTE
    with out.open("w", encoding="utf-8") as results:
        for number, question in enumerate(questions, 1):
            started = time.monotonic()
            course = catalog.get_course(question.course_id)
            try:
                answer = answer_question(
                    client, course.name, catalog.get_sheet(question.course_id), question.text
                )
            except AnswerUnavailable as error:
                failed.append(question.id)
                print(f"{number:>2} {question.id} FAILED: {str(error)[:120]}")
            else:
                took = time.monotonic() - started
                seconds.append(took)
                if answer.prompt_tokens is not None:
                    prompt_tokens.append(answer.prompt_tokens)
                if answer.output_tokens is not None:
                    output_tokens.append(answer.output_tokens)
                record = {
                    "id": question.id,
                    "found": answer.found,
                    "answer": answer.text,
                    "sources": [{"section": s.section, "quote": s.quote} for s in answer.sources],
                }
                results.write(json.dumps(record, ensure_ascii=False) + "\n")
                results.flush()
                if answer.found:
                    answered += 1
                    looks_slovak = bool(SLOVAK_LETTERS.search(answer.text or ""))
                    if answer.language != question.language or (
                        question.language == "en" and looks_slovak
                    ):
                        wrong_language.append(question.id)
                decision = "found" if answer.found else "Neviem"
                print(f"{number:>2} {question.id} {took:4.1f}s {decision}")
            if number < len(questions):
                time.sleep(max(0.0, gap - (time.monotonic() - started)))

    print(f"\nanswers: {out}")
    print(
        f"answer language: {answered - len(wrong_language)} z {answered} answered right"
        + (f"; wrong: {', '.join(wrong_language)}" if wrong_language else "")
    )
    if failed:
        print(f"failed ({len(failed)}), not in the file: {', '.join(failed)}")
    if seconds:
        print(
            f"seconds per answer: median {statistics.median(seconds):.1f}, max {max(seconds):.1f}"
        )
    if prompt_tokens and output_tokens:
        cost = (
            statistics.mean(prompt_tokens) * PAID_INPUT_PER_M / 1e6
            + statistics.mean(output_tokens) * PAID_OUTPUT_PER_M / 1e6
        )
        print(
            f"tokens per answer: prompt median {statistics.median(prompt_tokens):.0f}"
            f" (max {max(prompt_tokens)}), output median {statistics.median(output_tokens):.0f};"
            f" on the paid tier about ${cost:.4f} per answer"
        )
    print()
    return subprocess.call([sys.executable, str(SCORER), "--results", str(out)])


if __name__ == "__main__":
    sys.exit(main())
