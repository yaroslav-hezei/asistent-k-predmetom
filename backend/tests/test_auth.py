"""Login token check (app.auth) and the /me endpoints without a database."""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_MAIS_DATA_DIR, Settings
from app.main import create_app
from tests.jwt_helpers import JWK, make_key, make_token, make_verifier

USER = "6f1c2c1e-1111-4222-8333-444455556666"


def test_valid_token_gives_the_user_id():
    assert make_verifier().user_id(make_token(USER)) == USER


@pytest.mark.parametrize(
    ("token", "error"),
    [
        (lambda: make_token(USER, exp=int(time.time()) - 10), jwt.ExpiredSignatureError),
        (lambda: make_token(USER, aud="anon"), jwt.InvalidAudienceError),
        (
            lambda: make_token(USER, iss="https://other.supabase.co/auth/v1"),
            jwt.InvalidIssuerError,
        ),
        (lambda: make_token(None), jwt.MissingRequiredClaimError),
        # signed by another key under the same key id
        (lambda: make_token(USER, key=make_key("key-1")[0]), jwt.InvalidSignatureError),
        # a shared-secret token is never accepted, even with a known key id
        (lambda: make_token(USER, key="a" * 32, algorithm="HS256"), jwt.PyJWTError),
        (lambda: make_token(USER, kid="unknown"), jwt.PyJWKClientError),
    ],
    ids=["expired", "audience", "issuer", "no-sub", "signature", "hs256", "unknown-kid"],
)
def test_invalid_tokens_are_rejected(token, error):
    with pytest.raises(error):
        make_verifier().user_id(token())


def test_unknown_key_id_reloads_the_key_set_once():
    """Key rotation: a new key appears in the key set after the verifier cached the old set."""
    new_key, new_jwk = make_key("key-2")
    verifier = make_verifier(JWK)
    assert verifier.user_id(make_token(USER)) == USER
    verifier._jwks.jwks = {"keys": [JWK, new_jwk]}
    assert verifier.user_id(make_token(USER, key=new_key, kid="key-2")) == USER
    assert verifier._jwks.fetches == 2


@pytest.fixture
def client():
    settings = Settings(mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[])
    with TestClient(create_app(settings, verifier=make_verifier())) as test_client:
        yield test_client


def test_me_without_token_is_401(client):
    response = client.get("/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_invalid_token_is_401(client):
    response = client.get("/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_me_without_database_is_503(client):
    response = client.get("/me", headers={"Authorization": f"Bearer {make_token(USER)}"})
    assert response.status_code == 503


def test_me_without_login_configured_is_503():
    settings = Settings(mais_data_dir=DEFAULT_MAIS_DATA_DIR, frontend_origins=[])
    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/me", headers={"Authorization": f"Bearer {make_token(USER)}"})
    assert response.status_code == 503


def test_openapi_marks_me_as_protected(client):
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/me"]["get"]["security"] == [{"HTTPBearer": []}]
    assert "security" not in schema["paths"]["/courses"]["get"]
