"""Answering a question about a course.

PLACEHOLDER until the RAG step: no search, no language model. It answers with one real section of
the course's MAIS sheet, quoted exactly, so the chat screen can be built on real data. A question
with the word "neviem" gets the "Neviem" answer, so the screen for it can be built too.

The RAG step replaces only `answer_question`; the API and the stored chats stay the same.
"""

import re
from dataclasses import dataclass
from typing import Literal

from app.catalog import Sheet, SheetSection, normalize
from app.models.chat import Author, Source

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


@dataclass(frozen=True)
class Answer:
    found: bool  # False = "Neviem"
    text: str | None  # the answer with [n] citations; None when not found
    sources: list[Source]
    language: Literal["sk", "en"] | None  # language of the answer text


NOT_FOUND = Answer(found=False, text=None, sources=[], language=None)


def answer_question(sheet: Sheet, question: str) -> Answer:
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
