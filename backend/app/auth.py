"""Who is calling: verify the login token the frontend sends.

The frontend logs in with Supabase Auth and sends `Authorization: Bearer <access token>` with every
request that needs a user. The token is a JWT signed with the project's asymmetric key (ES256); the
public keys are published at `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. The backend checks the
signature locally — no call to Supabase per request — plus issuer, audience and expiry. The user's
id is the `sub` claim; it is the id of the row in `auth.users` and in `public.profiles`.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

AUDIENCE = "authenticated"  # tokens of logged-in users
# Asymmetric algorithms only: a token signed with a shared secret (HS256) is never accepted.
ALGORITHMS = ["ES256", "RS256"]
# Supabase caches the key set for 10 minutes and asks clients not to cache it longer.
JWKS_CACHE_S = 300
JWKS_TIMEOUT_S = 10


class TokenVerifier:
    def __init__(self, supabase_url: str, jwks_client: jwt.PyJWKClient | None = None) -> None:
        self.issuer = supabase_url.rstrip("/") + "/auth/v1"
        # Unknown `kid` (key rotation) → the client reloads the key set once, at most every 30 s.
        self._jwks = jwks_client or jwt.PyJWKClient(
            self.issuer + "/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=JWKS_CACHE_S,
            timeout=JWKS_TIMEOUT_S,
        )

    def user_id(self, token: str) -> str:
        """The user id of a valid token. Raises `jwt.PyJWTError` for any invalid token and
        `jwt.PyJWKClientConnectionError` when the key set cannot be loaded."""
        signing_key = self._jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            issuer=self.issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return claims["sub"]


bearer = HTTPBearer(auto_error=False, description="Supabase access token of the logged-in user.")


def current_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """FastAPI dependency: the id of the logged-in user, or 401."""
    verifier: TokenVerifier | None = request.app.state.auth
    if verifier is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Login is not configured.")
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Not logged in.", {"WWW-Authenticate": "Bearer"}
        )
    try:
        return verifier.user_id(credentials.credentials)
    except jwt.PyJWKClientConnectionError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Login keys cannot be loaded."
        ) from error
    except jwt.PyJWTError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token.",
            {"WWW-Authenticate": "Bearer"},
        ) from error


CurrentUserId = Annotated[str, Depends(current_user_id)]
