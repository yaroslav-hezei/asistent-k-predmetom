"""Login tokens for tests: signed with keys generated here, like Supabase signs them (ES256).

The verifier gets the matching key set directly instead of downloading it from Supabase.
"""

import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.auth import TokenVerifier

SUPABASE_URL = "https://example-project.supabase.co"
ISSUER = SUPABASE_URL + "/auth/v1"


class StaticJWKClient(jwt.PyJWKClient):
    """A PyJWKClient that serves a fixed key set (counting the "downloads")."""

    def __init__(self, jwks: dict[str, Any]) -> None:
        super().__init__("https://example.invalid/auth/v1/.well-known/jwks.json")
        self.jwks = jwks
        self.fetches = 0

    def fetch_data(self) -> Any:
        self.fetches += 1
        return self.jwks


def make_key(kid: str) -> tuple[ec.EllipticCurvePrivateKey, dict[str, Any]]:
    """A private key and its public JWK, as Supabase publishes it."""
    private = ec.generate_private_key(ec.SECP256R1())
    public = jwt.algorithms.ECAlgorithm.to_jwk(private.public_key(), as_dict=True)
    return private, {**public, "kid": kid, "alg": "ES256", "use": "sig"}


KEY, JWK = make_key("key-1")


def make_verifier(*jwks: dict[str, Any]) -> TokenVerifier:
    return TokenVerifier(SUPABASE_URL, StaticJWKClient({"keys": list(jwks or [JWK])}))


def make_token(
    sub: str | None,
    *,
    key: Any = KEY,
    kid: str = "key-1",
    algorithm: str = "ES256",
    **claims: Any,
) -> str:
    """A token like Supabase issues for a logged-in user; `claims` override or add claims,
    `sub=None` leaves the claim out."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    if sub is not None:
        payload["sub"] = sub
    payload.update(claims)
    return jwt.encode(payload, key, algorithm=algorithm, headers={"kid": kid})
