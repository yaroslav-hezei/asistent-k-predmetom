"""Cutting a course's MAIS sheet into chunks for the knowledge base.

One sheet section = one chunk; a section longer than MAX_CHUNK_CHARS is cut into parts. Every chunk
is an exact piece of the sheet text: the assistant quotes it word for word and the section label
says where it comes from (the evaluation matches citations by section and quote).
"""

import math
from dataclasses import dataclass

from app.catalog import Sheet

MAX_CHUNK_CHARS = 1500

# Sections that say nothing about the course: the same text on every sheet of the faculty, or a
# misleading date (MAIS sets "Dátum poslednej zmeny" to the start of the year on every sheet).
SKIPPED_SECTIONS = frozenset({"Vysoká škola", "Fakulta", "Schválil", "Dátum poslednej zmeny"})

# Where a long section may be cut, best first: paragraph, line, sentence, clause, word.
BOUNDARIES = ("\n\n", "\n", ". ", "; ", ", ", " ")


@dataclass(frozen=True)
class Chunk:
    section: str  # the sheet section label, e.g. "Priebežné hodnotenie (PH)"
    chunk_index: int  # 0 for a whole section; 0, 1, 2, ... for the parts of a long one
    content: str  # exact text of the sheet


def chunk_sheet(sheet: Sheet) -> list[Chunk]:
    """The chunks of one sheet, in the order of the sheet. Empty and skipped sections give none."""
    chunks: list[Chunk] = []
    next_index: dict[str, int] = {}  # a label that repeats continues its numbering
    for section in sheet.sections:
        if section.label in SKIPPED_SECTIONS:
            continue
        for part in split_text(section.text):
            index = next_index.get(section.label, 0)
            chunks.append(Chunk(section=section.label, chunk_index=index, content=part))
            next_index[section.label] = index + 1
    return chunks


def split_text(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    """Cut text into parts of at most `limit` characters, of about equal length, at the best
    boundary available. Each part is an exact substring of `text` without outer whitespace;
    blank text gives no parts."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    target = math.ceil(len(text) / math.ceil(len(text) / limit))
    parts = []
    start = 0
    while len(text) - start > limit:
        end = _cut(text, start, target, limit)
        parts.append(text[start:end].strip())
        start = end
        while text[start].isspace():  # the remaining text is not blank: it ends with a non-space
            start += 1
    parts.append(text[start:])
    return parts


def _cut(text: str, start: int, target: int, limit: int) -> int:
    """End of the next part: the boundary nearest to start + target, at most start + limit and
    not before start + target / 2; a hard cut at start + limit when there is no boundary."""
    lowest = start + target // 2
    highest = start + limit
    goal = start + target
    for boundary in BOUNDARIES:
        best = None
        found = text.find(boundary, lowest, highest)
        while found != -1:
            end = found + len(boundary)
            if best is None or abs(end - goal) < abs(best - goal):
                best = end
            found = text.find(boundary, found + 1, highest)
        if best is not None:
            return best
    return highest
