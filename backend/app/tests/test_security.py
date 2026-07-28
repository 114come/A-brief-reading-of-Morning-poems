from datetime import timedelta

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
