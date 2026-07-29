from typing import Any

from app.services.ai.agent_engine.tools.base import BaseTool
from app.services.ai.service import AIService


class LLMTool(BaseTool):
    """LLM 对话工具：调用大模型进行文本生成"""

    name = "llm"
    description = "向大语言模型发送提示词并获取回复，适用于文本生成、问答、翻译等任务"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "发送给 LLM 的提示词内容",
            },
        },
        "required": ["prompt"],
    }

    def __init__(
        self,
        ai_service: AIService,
        tenant_id: int,
        model: str = "gpt-4o",
    ) -> None:
        self._ai_service = ai_service
        self._tenant_id = tenant_id
        self._model = model

    async def execute(self, **kwargs: Any) -> str:
        prompt: str = kwargs.get("prompt", "")
        if not prompt.strip():
            return "错误：提示词不能为空"

        result = await self._ai_service.chat_completion(
            tenant_id=self._tenant_id,
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        # result is a dict from chat_completion, extract the content
        content = result.get("content", "")
        if not content:
            # Fallback: try choices[0].message.content
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
        return str(content) if content else "错误：LLM 返回了空结果"
