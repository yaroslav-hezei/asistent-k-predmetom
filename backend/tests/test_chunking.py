"""Cutting the MAIS sheets into knowledge-base chunks (no database).

The expected counts are those of the committed snapshot data/mais/2026-27.
"""

import re
from datetime import UTC, datetime

import pytest

from app.catalog import Catalog, Sheet, SheetSection
from app.chunking import MAX_CHUNK_CHARS, SKIPPED_SECTIONS, Chunk, chunk_sheet, split_text
from app.config import DEFAULT_MAIS_DATA_DIR

ZAP = "65954478"
LONG_ONE_LINE = "65888543"  # its "Stručná osnova predmetu" is one line of 3320 characters


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_sheet(*sections: tuple[str, str]) -> Sheet:
    return Sheet(
        course_id="1",
        source_url="https://example.invalid/sheet",
        fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
        sections=tuple(SheetSection(label, text) for label, text in sections),
    )


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load(DEFAULT_MAIS_DATA_DIR)


def test_short_section_is_one_exact_chunk():
    sheet = make_sheet(("Priebežné hodnotenie (PH)", "Zápočet: min. 21 bodov z 40."))
    assert chunk_sheet(sheet) == [
        Chunk(
            section="Priebežné hodnotenie (PH)",
            chunk_index=0,
            content="Zápočet: min. 21 bodov z 40.",
        )
    ]


def test_skipped_and_empty_sections_give_no_chunks():
    sheet = make_sheet(
        ("Vysoká škola", "Technická univerzita v Košiciach"),
        ("Fakulta", "Fakulta elektrotechniky a informatiky"),
        ("Schválil", "osoba/osoby zodpovedné za študijný program"),
        ("Dátum poslednej zmeny", "01.09.2026"),
        ("Podmienky na absolvovanie predmetu", ""),
        ("Poznámky", "  \n "),
        ("Počet kreditov", "6"),
    )
    assert [c.section for c in chunk_sheet(sheet)] == ["Počet kreditov"]


def test_repeated_label_continues_its_numbering():
    sheet = make_sheet(("Poznámky", "prvá"), ("Poznámky", "druhá"))
    assert [(c.section, c.chunk_index, c.content) for c in chunk_sheet(sheet)] == [
        ("Poznámky", 0, "prvá"),
        ("Poznámky", 1, "druhá"),
    ]


def test_split_prefers_sentence_ends_and_keeps_parts_balanced():
    sentence = "Toto je jedna veta o obsahu predmetu, ktorá má presne takúto dĺžku. "
    text = (sentence * 40).strip()  # ~2,700 characters, no line breaks
    parts = split_text(text)
    assert len(parts) == 2
    assert all(part.endswith(".") for part in parts)
    assert abs(len(parts[0]) - len(parts[1])) <= len(sentence)
    assert squash(" ".join(parts)) == squash(text)


def test_split_without_any_boundary_cuts_hard():
    text = "x" * (MAX_CHUNK_CHARS * 2 + 1)
    parts = split_text(text)
    assert all(len(part) <= MAX_CHUNK_CHARS for part in parts)
    assert "".join(parts) == text


def test_long_one_line_section_is_cut_into_exact_parts(catalog):
    sheet = catalog.get_sheet(LONG_ONE_LINE)
    text = next(s.text for s in sheet.sections if s.label == "Stručná osnova predmetu")
    chunks = [c for c in chunk_sheet(sheet) if c.section == "Stručná osnova predmetu"]
    assert len(text) == 3320 and "\n" not in text
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    for chunk in chunks:
        assert chunk.content in text
        assert len(chunk.content) <= MAX_CHUNK_CHARS
    assert squash(" ".join(c.content for c in chunks)) == squash(text)


def test_zap_ph_chunk_is_the_exact_sheet_text(catalog):
    sheet = catalog.get_sheet(ZAP)
    ph = next(s.text for s in sheet.sections if s.label == "Priebežné hodnotenie (PH)")
    chunks = [c for c in chunk_sheet(sheet) if c.section == "Priebežné hodnotenie (PH)"]
    assert [(c.chunk_index, c.content) for c in chunks] == [(0, ph)]


def test_every_catalogue_sheet(catalog):
    """All 563 sheets: every chunk is exact sheet text within the limit, nothing is lost."""
    total = 0
    for course in catalog.search_courses():
        sheet = catalog.get_sheet(course.id)
        chunks = chunk_sheet(sheet)
        total += len(chunks)
        keys = [(c.section, c.chunk_index) for c in chunks]
        assert len(keys) == len(set(keys)), course.id
        for section in sheet.sections:
            parts = [c.content for c in chunks if c.section == section.label]
            if section.label in SKIPPED_SECTIONS or not section.text.strip():
                assert parts == [], (course.id, section.label)
                continue
            assert parts, (course.id, section.label)
            for part in parts:
                assert part in section.text
                assert 0 < len(part) <= MAX_CHUNK_CHARS
            assert squash(" ".join(parts)) == squash(section.text), (course.id, section.label)
    # 13,132 non-empty sections - 2,228 skipped + 77 extra parts of the 66 long sections
    assert total == 10_981
