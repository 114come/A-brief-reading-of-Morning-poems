import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    return payload


# ─── API Key 加密/解密 ───────────────────────────────────────────────


def _get_fernet() -> Fernet:
    """从配置的 ENCRYPTION_KEY 派生 Fernet 密钥"""
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_api_key(plain_text: str) -> str:
    """加密 API Key"""
    return _get_fernet().encrypt(plain_text.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    """解密 API Key"""
    return _get_fernet().decrypt(encrypted.encode()).decode()
