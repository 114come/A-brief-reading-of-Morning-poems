import json
from typing import Any

from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.template import render_template


class LLMNode(BaseNode):
    """Node that calls an LLM via AIService.chat_completion."""

    node_type = "llm"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        prompt_template: str = config.get("prompt", "")
        prompt = render_template(prompt_template, context)

        ai_service = services.get("ai_service")
        if ai_service is None:
            raise ValueError("ai_service is required for LLMNode")

        tenant_id: int = context.get("tenant_id", 0)
        model: str = config.get("model", "gpt-4")
        temperature: float | None = config.get("temperature")
        max_tokens: int | None = config.get("max_tokens")

        response = await ai_service.chat_completion(
            tenant_id=tenant_id,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content: str = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        result: dict[str, Any] = {"content": content}
        try:
            parsed = json.loads(content)
            result["parsed"] = parsed
        except (json.JSONDecodeError, ValueError):
            pass

        return result
