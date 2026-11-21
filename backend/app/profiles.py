"""Profiles of users (`public.profiles`), one per Supabase Auth account."""

from psycopg import Connection

from app.models.me import Me, Study


class UnknownProgram(ValueError):
    """The program does not exist, or it has fewer years than requested."""


def get_profile(conn: Connection, user_id: str) -> Me | None:
    row = conn.execute(
        "select id, nickname, role, program_id, year, semester from public.profiles where id = %s",
        [user_id],
    ).fetchone()
    if row is None:
        return None
    user, nickname, role, program_id, year, semester = row
    study = None
    if program_id is not None:
        study = Study(program_id=program_id, year=year, semester=semester)
    return Me(id=user, nickname=nickname, role=role, study=study)


def set_study(conn: Connection, user_id: str, study: Study) -> None:
    """Store program, year and semester. Raises UnknownProgram for a program that does not exist
    or a year beyond the program's length."""
    row = conn.execute(
        "select years from public.programs where id = %s", [study.program_id]
    ).fetchone()
    if row is None:
        raise UnknownProgram(f"Unknown program {study.program_id}.")
    if study.year > row[0]:
        raise UnknownProgram(f"Program {study.program_id} has {row[0]} years.")
    conn.execute(
        "update public.profiles set program_id = %s, year = %s, semester = %s where id = %s",
        [study.program_id, study.year, study.semester, user_id],
    )
