from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class UnifiedResponse(BaseModel, Generic[T]):
    code: int = 0
    data: T | None = None
    message: str = "ok"

    @classmethod
    def success(cls, data: T | None = None, message: str = "ok") -> "UnifiedResponse[T]":
        return cls(code=0, data=data, message=message)

    @classmethod
    def error(cls, code: int, message: str) -> "UnifiedResponse[Any]":
        return cls(code=code, data=None, message=message)
