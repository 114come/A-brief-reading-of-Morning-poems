import json
import logging
import time
from typing import Any, AsyncIterator

from app.services.ai.agent_engine.models import Agent
from app.services.ai.agent_engine.session_memory import SessionMemory
from app.services.ai.agent_engine.tools.registry import ToolRegistry
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)


class ReActExecutor:
    """ReAct 执行器：推理 -> 行动 -> 观察循环"""

    def __init__(
        self,
        ai_service: AIService,
        session_memory: SessionMemory,
    ) -> None:
        self.ai_service = ai_service
        self.session_memory = session_memory

    async def execute_stream(
        self,
        tenant_id: int,
        agent: Agent,
        message: str,
        system_prompt_override: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute the ReAct loop, yielding SSE event dicts."""
        # Parse config
        model_config = (
            json.loads(agent.model_config)
            if isinstance(agent.model_config, str)
            else agent.model_config
        )
        tools_config = (
            json.loads(agent.tools_config)
            if isinstance(agent.tools_config, str)
            else agent.tools_config
        )
        model = model_config.get("model", "gpt-4")
        temperature = model_config.get("temperature")
        max_tokens = model_config.get("max_tokens")

        # Get enabled tools
        tool_schemas = ToolRegistry.all_schemas(tools_config)

        # Build messages
        history = self.session_memory.get_history()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt_override or agent.system_prompt},
            *history,
            {"role": "user", "content": message},
        ]

        self.session_memory.push_message("user", message)

        total_tokens = 0
        iterations = 0

        while iterations < agent.max_iterations:
            iterations += 1
            yield {"event": "thinking", "data": {"content": f"思考中...（第{iterations}步）"}}

            try:
                response = await self.ai_service.chat_completion(
                    tenant_id=tenant_id,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.exception("LLM call failed")
                yield {"event": "error", "data": {"message": f"LLM 调用失败: {e}"}}
                break

            total_tokens += response.get("usage", {}).get("total_tokens", 0)
            choice = response["choices"][0]
            msg = choice["message"]
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")

            if content:
                yield {"event": "thinking", "data": {"content": content}}

            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    try:
                        tool_args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        tool_args = {}

                    yield {"event": "tool_call", "data": {"tool": tool_name, "args": tool_args}}

                    # Execute tool
                    tool_impl = ToolRegistry.get(tool_name)
                    if tool_impl:
                        try:
                            start = time.time()
                            tool_result = await tool_impl.execute(**tool_args)
                            duration = int((time.time() - start) * 1000)
                            yield {
                                "event": "tool_result",
                                "data": {
                                    "tool": tool_name,
                                    "content": tool_result[:500],
                                    "duration_ms": duration,
                                },
                            }
                        except Exception as e:
                            logger.exception("Tool %s failed", tool_name)
                            tool_result = f"执行失败: {e}"
                            yield {
                                "event": "tool_result",
                                "data": {
                                    "tool": tool_name,
                                    "content": tool_result,
                                    "duration_ms": 0,
                                },
                            }
                    else:
                        tool_result = f"未知工具: {tool_name}"
                        yield {"event": "error", "data": {"message": tool_result}}

                    # Append assistant message with tool_call, then tool result
                    messages.append(
                        {
                            "role": "assistant",
                            "content": content or "",
                            "tool_calls": [
                                {
                                    "id": tc.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": func.get("arguments", ""),
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": tool_result,
                        }
                    )
            else:
                if content:
                    yield {"event": "message", "data": {"content": content}}
                self.session_memory.push_message(
                    "assistant", content or "", name="assistant" if content else None
                )
                yield {
                    "event": "done",
                    "data": {"usage": {"total_tokens": total_tokens, "steps": iterations}},
                }
                return

        yield {
            "event": "error",
            "data": {"message": f"无法在 {agent.max_iterations} 步内完成"},
        }
        yield {
            "event": "done",
            "data": {"usage": {"total_tokens": total_tokens, "steps": iterations}},
        }
