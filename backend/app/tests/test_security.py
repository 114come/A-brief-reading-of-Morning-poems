from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    plain = "mysecret123"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token() -> None:
    data = {"sub": "user_123", "tenant_id": "tenant_001"}
    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    payload = decode_token(token)
    assert payload["sub"] == "user_123"
    assert payload["tenant_id"] == "tenant_001"


def test_create_access_token_default_expiry() -> None:
    data = {"sub": "user_123"}
    before = datetime.now(timezone.utc).replace(microsecond=0)
    token = create_access_token(data)
    after = datetime.now(timezone.utc).replace(microsecond=0)
    payload = decode_token(token)
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected_min = before + timedelta(minutes=30)
    expected_max = after + timedelta(minutes=30, seconds=1)
    assert expected_min <= exp <= expected_max


def test_decode_tampered_token() -> None:
    data = {"sub": "user_123"}
    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    # Tamper with the signature portion
    tampered_token = token[:-5] + "XXXXX"
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(tampered_token)


def test_decode_expired_token() -> None:
    data = {"sub": "user_123"}
    token = create_access_token(data, expires_delta=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
