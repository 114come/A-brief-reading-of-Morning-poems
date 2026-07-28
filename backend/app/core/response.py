from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class UnifiedResponse(BaseModel):
    code: int = 0
    data: Any = None
    message: str = "ok"

    @classmethod
    def success(cls, data: T | None = None, message: str = "ok") -> "UnifiedResponse":
        return cls(code=0, data=data, message=message)

    @classmethod
    def error(cls, code: int, message: str) -> "UnifiedResponse":
        return cls(code=code, data=None, message=message)
