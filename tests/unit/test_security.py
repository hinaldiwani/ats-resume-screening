"""
tests/unit/test_security.py

Unit tests for password hashing, JWT token creation, token decoding,
token expiry, and signature validation in app/core/security.py.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    ExpiredSignatureError,
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()



def test_password_hashing_and_verification():
    raw_password = "SecretPassword123"
    hashed = hash_password(raw_password)

    # Hash should not equal plain password
    assert hashed != raw_password
    # Hash should be valid bcrypt
    assert hashed.startswith(("$2b$", "$2a$"))

    # Correct password verifies

    assert verify_password(raw_password, hashed) is True
    # Wrong password fails
    assert verify_password("WrongPassword123", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token(subject="42", expires_minutes=15)
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert "exp" in payload
    # exp should be in future
    now_ts = datetime.now(timezone.utc).timestamp()
    assert payload["exp"] > now_ts


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="42")
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"
    assert "exp" in payload
    now_ts = datetime.now(timezone.utc).timestamp()
    assert payload["exp"] > now_ts


def test_token_expiry_raises_jwt_error():
    # Create an expired token (expired 5 minutes ago)
    expired_token = create_access_token(subject="42", expires_minutes=-5)

    with pytest.raises((JWTError, ExpiredSignatureError)):
        decode_token(expired_token)


def test_token_invalid_signature_raises_jwt_error():
    # Encode with different secret key
    fake_token = jwt.encode(
        {"sub": "42", "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        "wrong-secret-key-1234567890",
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(JWTError):
        decode_token(fake_token)


def test_token_malformed_string_raises_jwt_error():
    with pytest.raises(JWTError):
        decode_token("not.a.valid.jwt.token")


def test_timezone_aware_utc_timestamp_accuracy():
    """Verifies that token exp is stamped in true UTC epoch seconds without timezone skew."""
    now_utc = datetime.now(timezone.utc)
    token = create_access_token(subject="100", expires_minutes=30)
    payload = decode_token(token)

    expected_exp_approx = int((now_utc + timedelta(minutes=30)).timestamp())
    # Should match within a small epsilon (<= 2 seconds)
    assert abs(payload["exp"] - expected_exp_approx) <= 2
