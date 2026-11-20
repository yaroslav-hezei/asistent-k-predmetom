"""The logged-in user: profile and "Moje predmety" choice."""

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUserId
from app.db import Pool
from app.models.me import Me, Study
from app.profiles import UnknownProgram, get_profile, set_study

router = APIRouter(tags=["me"])

NOT_LOGGED_IN = {401: {"description": "Missing, invalid or expired token."}}
NO_PROFILE = {403: {"description": "The account has no profile."}}


@router.get("/me", summary="The logged-in user", responses={**NOT_LOGGED_IN, **NO_PROFILE})
def read_me(user_id: CurrentUserId, pool: Pool) -> Me:
    with pool.connection() as conn:
        me = get_profile(conn, user_id)
    if me is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The account has no profile.")
    return me


@router.patch(
    "/me",
    summary="Set program, year and semester of the logged-in user",
    responses={**NOT_LOGGED_IN, **NO_PROFILE, 422: {"description": "Unknown program or year."}},
)
def update_me(study: Study, user_id: CurrentUserId, pool: Pool) -> Me:
    with pool.connection() as conn:
        if get_profile(conn, user_id) is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "The account has no profile.")
        try:
            set_study(conn, user_id, study)
        except UnknownProgram as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        me = get_profile(conn, user_id)
    if me is None:  # cannot happen: the profile was there a moment ago
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The account has no profile.")
    return me
