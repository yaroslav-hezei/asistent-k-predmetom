"""Answering a question about a course from its MAIS information sheet.

`answer_question`: the whole sheet goes to the answering model as numbered chunks (the same chunks
as the knowledge base, `app.chunking`); the model answers in a few sentences and cites chunk numbers
as [n], or says it does not know. The model never writes a source: this code turns the cited
numbers into sources with the exact chunk text, the MAIS link and the date the sheet was read, and
renumbers the citations 1, 2, ... in the order they appear. An answer without a valid citation is
"Neviem", and so is an answer with a number that none of its cited sources contains (a number
the model made up must never reach a student).

`placeholder_answer`: used when the backend runs without GEMINI_API_KEY (local development, CI):
no model, one real section of the sheet quoted exactly; a question with the word "neviem" gets the
"Neviem" answer, so the chat screen can be built without the model.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from google.genai import errors

from app import llm
from app.catalog import Sheet, SheetSection, normalize
from app.chunking import Chunk, chunk_sheet
from app.models.chat import Author, Source

SYSTEM_INSTRUCTION = """\
You answer students' questions about one university course at the Technical University of Košice \
(TUKE, FEI). The sources are the parts of the course's official information sheet from MAIS \
("informačný list predmetu"), written in Slovak, each as <zdroj n="..." sekcia="...">text</zdroj>.

Rules:
- Use only facts written in the text of the sources. Never use outside knowledge and never guess: \
no invented dates, numbers, names, rooms or rules.
- The number n of a source is only its label for citing: it is never a fact about the course \
(not a number of credits, hours, points or a semester).
- After each sentence that uses a source, cite it by its n in square brackets, e.g. [3]. Cite \
only sources that really say it.
- If the sources do not answer the question itself, set "found" to false and leave "answer" empty, \
even when they mention the topic (e.g. the sheet names tests but gives no date for them).
- Language: a question in Slovak or Czech gets a Slovak answer ("language": "sk"); a question in \
any other language gets an English answer ("language": "en"). Decide the language first. In an \
English answer write English sentences in your own words: never copy the Slovak text of a \
source.
- Be short: 1 to 4 sentences of plain text, no lists, no headings, no greeting.
- Abbreviations on the sheet: PH = priebežné hodnotenie (assessment during the semester, needed \
for the zápočet), ZH = záverečné hodnotenie (the final exam). "min. 21% z 40%" means: this part \
is worth 40 % of the course's points and the student needs at least 21 % of them.
- Questions how much one needs (for the zápočet, the exam, to pass the course) are answered by \
the thresholds in PH and ZH.
"""

# "language" first: the model decides the language before it writes the answer.
ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "language": {"type": "string", "enum": ["sk", "en"]},
        "found": {
            "type": "boolean",
            "description": "true only when the sources answer the question",
        },
        "answer": {
            "type": "string",
            "description": "the answer with [n] citations; empty when found is false",
        },
    },
    "required": ["language", "found", "answer"],
}

LANGUAGE_REMINDER = (
    "Answer language: Slovak if the question is in Slovak or Czech, otherwise English."
)

logger = logging.getLogger(__name__)

# [3], [1, 3], [1; 3]
CITATION = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
NUMBER = re.compile(r"\d+")

# The placeholder quotes the first of these sections that has text.
PREFERRED_SECTIONS = (
    "Priebežné hodnotenie (PH)",
    "Záverečné hodnotenie (ZH)",
    "Spôsob hodnotenia a skončenia štúdia predmetu",
    "Výsledky vzdelávania",
)
PLACEHOLDER_TEXT = (
    "Ukážková odpoveď: asistent zatiaľ nevyhľadáva odpoveď na otázku,"
    " len ukazuje jednu časť informačného listu [1]."
)


class AnswerUnavailable(Exception):
    """The model could not be asked (limit, network, server) or returned no usable answer."""


@dataclass(frozen=True)
class Answer:
    found: bool  # False = "Neviem"
    text: str | None  # the answer with [n] citations; None when not found
    sources: list[Source]
    language: Literal["sk", "en"] | None  # language of the answer text
    prompt_tokens: int | None = None  # what the model call used (none for the placeholder)
    output_tokens: int | None = None


NOT_FOUND = Answer(found=False, text=None, sources=[], language=None)


def answer_question(client: Any, course_name: str, sheet: Sheet, question: str) -> Answer:
    """The model's answer from the whole sheet. Raises AnswerUnavailable."""
    chunks = chunk_sheet(sheet)
    if not chunks:
        return NOT_FOUND
    try:
        generation = llm.generate_json(
            client, SYSTEM_INSTRUCTION, build_prompt(course_name, chunks, question), ANSWER_SCHEMA
        )
    except (errors.APIError, ValueError) as error:
        raise AnswerUnavailable(str(error)) from error
    return read_answer(generation, chunks, sheet, course_name)


def build_prompt(course_name: str, chunks: Sequence[Chunk], question: str) -> str:
    # the number apart from the text: "[8] Počet kreditov: 5" made the model answer "8 credits"
    sources = "\n".join(
        f'<zdroj n="{n}" sekcia="{chunk.section}">\n{chunk.content}\n</zdroj>'
        for n, chunk in enumerate(chunks, 1)
    )
    return (
        f"Predmet: {course_name}\n\nZdroje:\n{sources}\n\nOtázka: {question}\n\n{LANGUAGE_REMINDER}"
    )


def read_answer(
    generation: llm.Generation, chunks: Sequence[Chunk], sheet: Sheet, course_name: str = ""
) -> Answer:
    """Turn the model's JSON into an Answer: sources from the cited chunks, citations renumbered."""
    data = generation.data
    found, text, language = data.get("found"), data.get("answer"), data.get("language")
    if not isinstance(found, bool) or not isinstance(text, str):
        raise AnswerUnavailable("the model's reply does not have the expected fields")
    if not found:
        return NOT_FOUND
    text, cited = renumber_citations(text, len(chunks))
    if not cited or not text:
        return NOT_FOUND  # an answer that cites nothing is not grounded in the sheet
    unsupported = unsupported_numbers(
        text, [chunks[index - 1].content for index in cited] + [course_name]
    )
    if unsupported:
        logger.warning("answer dropped: %s not in its cited sources", ", ".join(unsupported))
        return NOT_FOUND
    sources = [
        Source(
            n=n,
            type="sheet",
            section=chunks[index - 1].section,
            quote=chunks[index - 1].content,
            url=sheet.source_url,
            question=None,
            date=sheet.fetched_at,
            author=Author(kind="mais", nickname=None),
            verified=True,
            outdated=False,
        )
        for n, index in enumerate(cited, 1)
    ]
    return Answer(
        found=True,
        text=text,
        sources=sources,
        language=language if language in ("sk", "en") else None,
        prompt_tokens=generation.prompt_tokens,
        output_tokens=generation.output_tokens,
    )


def unsupported_numbers(text: str, sources: Sequence[str]) -> list[str]:
    """Numbers of the answer (citations aside) that no source contains, compared by value
    ("01" = "1"). Numbers of the question do not count: "Is it 8 credits?" must not let
    an 8 through."""
    known = {int(number) for source in sources for number in NUMBER.findall(source)}
    return sorted(
        {number for number in NUMBER.findall(CITATION.sub("", text)) if int(number) not in known},
        key=int,
    )


def renumber_citations(text: str, chunk_count: int) -> tuple[str, list[int]]:
    """Citations renumbered 1, 2, ... in order of first appearance; numbers outside 1..chunk_count
    dropped; [1, 3] written as [1][3]. Returns the new text and the cited chunk numbers (1-based)
    in the new order."""
    cited: list[int] = []

    def replace(match: re.Match[str]) -> str:
        new = []
        for number in (int(part) for part in re.split(r"[,;]", match.group(1))):
            if 1 <= number <= chunk_count:
                if number not in cited:
                    cited.append(number)
                marker = f"[{cited.index(number) + 1}]"
                if marker not in new:
                    new.append(marker)
        return "".join(new)

    text = CITATION.sub(replace, text)
    text = re.sub(r"(\[\d+\])(?:\1)+", r"\1", text)  # [1][1] -> [1]
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)  # space left before a dropped citation
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text, cited


def placeholder_answer(sheet: Sheet, question: str) -> Answer:
    if re.search(r"\bneviem\b", normalize(question)):
        return NOT_FOUND
    section = _placeholder_section(sheet)
    if section is None:
        return NOT_FOUND
    source = Source(
        n=1,
        type="sheet",
        section=section.label,
        quote=section.text,
        url=sheet.source_url,
        question=None,
        date=sheet.fetched_at,
        author=Author(kind="mais", nickname=None),
        verified=True,
        outdated=False,
    )
    return Answer(found=True, text=PLACEHOLDER_TEXT, sources=[source], language="sk")


def _placeholder_section(sheet: Sheet) -> SheetSection | None:
    with_text = [s for s in sheet.sections if s.text.strip()]
    for label in PREFERRED_SECTIONS:
        for section in with_text:
            if section.label == label:
                return section
    return with_text[0] if with_text else None
