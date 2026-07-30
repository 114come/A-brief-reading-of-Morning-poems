from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseLLMProvider(ABC):
    """LLM 提供商适配器基类"""

    def __init__(self, api_key: str, api_base: str | None = None) -> None:
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """非流式对话补全"""
        ...

    @abstractmethod
    async def chat_completion_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """流式对话补全，返回 SSE 数据块迭代器"""
        ...
