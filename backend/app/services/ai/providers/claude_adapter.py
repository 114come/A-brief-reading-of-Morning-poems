import json
from typing import Any, AsyncIterator

import httpx

from app.services.ai.providers.base import BaseLLMProvider


class ClaudeAdapter(BaseLLMProvider):
    """Anthropic Claude 适配器"""

    API_BASE = "https://api.anthropic.com/v1"

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        url = (self.api_base or self.API_BASE).rstrip("/") + "/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # 将 OpenAI 格式的消息转为 Claude 格式
        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        body: dict[str, Any] = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens or 4096,
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            raw = resp.json()

        # 转为 OpenAI 兼容格式
        return {
            "id": raw.get("id", ""),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": raw.get("content", [{}])[0].get("text", ""),
                    },
                    "finish_reason": raw.get("stop_reason", "stop"),
                }
            ],
            "usage": {
                "input_tokens": raw.get("usage", {}).get("input_tokens", 0),
                "output_tokens": raw.get("usage", {}).get("output_tokens", 0),
            },
        }

    async def chat_completion_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        url = (self.api_base or self.API_BASE).rstrip("/") + "/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        system = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        body: dict[str, Any] = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        # Claude SSE 事件，转为 OpenAI SSE 格式
                        event_data = json.loads(data)
                        if event_data.get("type") == "content_block_delta":
                            delta_text = event_data.get("delta", {}).get("text", "")
                            if delta_text:
                                openai_chunk = {
                                    "id": event_data.get("id", ""),
                                    "model": model,
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": delta_text},
                                            "finish_reason": None,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                        elif event_data.get("type") == "message_stop":
                            yield "data: [DONE]\n\n"
