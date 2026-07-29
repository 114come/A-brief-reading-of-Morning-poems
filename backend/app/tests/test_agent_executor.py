"""Tests for ReActExecutor class."""

import json
from datetime import datetime
from typing import Any

import pytest

from app.services.ai.agent_engine.executor import ReActExecutor
from app.services.ai.agent_engine.models import Agent
from app.services.ai.agent_engine.session_memory import SessionMemory
from app.services.ai.agent_engine.tools import ToolRegistry
from app.services.ai.agent_engine.tools.calculator import CalculatorTool


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class MockAIService:
    """Mock AIService that returns pre-defined responses."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.call_count = 0

    async def chat_completion(
        self,
        tenant_id: int,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = self.responses[self.call_count]
        self.call_count += 1
        return response


class MockSessionMemory:
    """In-memory SessionMemory that does not require Redis."""

    def __init__(self, conversation_id: int = 1) -> None:
        self.conversation_id = conversation_id
        self._messages: list[dict[str, Any]] = []

    def push_message(
        self, role: str, content: str, name: str | None = None
    ) -> None:
        message: dict[str, Any] = {"role": role, "content": content}
        if name:
            message["name"] = name
        self._messages.append(message)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def trim(self, max_messages: int = 200) -> None:
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calculator_tool() -> CalculatorTool:
    """Ensure CalculatorTool is registered for testing."""
    # Register if not already registered
    existing = ToolRegistry.get("calculator")
    if existing is None:
        tool = CalculatorTool()
        ToolRegistry.register(tool)
        return tool
    return existing


@pytest.fixture
def tool_call_response() -> dict[str, Any]:
    """LLM response that requests a calculator tool call."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "我来计算 1+1。",
                    "tool_calls": [
                        {
                            "id": "call_calc_001",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": json.dumps({"expression": "1+1"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }


@pytest.fixture
def final_answer_response() -> dict[str, Any]:
    """LLM response with the final answer (no tool calls)."""
    return {
        "id": "chatcmpl-test2",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "1 + 1 = 2",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 150, "completion_tokens": 10, "total_tokens": 160},
    }


@pytest.fixture
def agent() -> Agent:
    """A minimal Agent instance for testing."""
    # Agent is a SQLAlchemy model, so we need to instantiate with kwargs
    agent = Agent(
        id=1,
        tenant_id=1,
        name="Test Agent",
        system_prompt="你是一个有帮助的助手。",
        model_config=json.dumps({"model": "gpt-4", "temperature": 0.7, "max_tokens": 1024}),
        tools_config=json.dumps(["calculator"]),
        max_iterations=5,
        is_active=True,
    )
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_stream_tool_call_then_answer(
    calculator_tool: CalculatorTool,
    tool_call_response: dict[str, Any],
    final_answer_response: dict[str, Any],
    agent: Agent,
) -> None:
    """Verify the full ReAct loop yields expected events in order."""
    ai_service = MockAIService(responses=[tool_call_response, final_answer_response])
    session_memory = MockSessionMemory(conversation_id=1)

    executor = ReActExecutor(ai_service=ai_service, session_memory=session_memory)
    events: list[dict[str, Any]] = []

    async for event in executor.execute_stream(tenant_id=1, agent=agent, message="1+1等于几？"):
        events.append(event)

    # Collect event types for assertion
    event_types = [e["event"] for e in events]

    # Verify event sequence
    assert "thinking" in event_types, "Expected at least one thinking event"
    assert "tool_call" in event_types, "Expected tool_call event"
    assert "tool_result" in event_types, "Expected tool_result event"
    assert "message" in event_types, "Expected message event"
    assert "done" in event_types, "Expected done event"

    # Verify thinking events exist
    thinking_events = [e for e in events if e["event"] == "thinking"]
    assert len(thinking_events) >= 2  # initial step + content thinking

    # Verify tool_call event details
    tool_call_events = [e for e in events if e["event"] == "tool_call"]
    assert len(tool_call_events) == 1
    assert tool_call_events[0]["data"]["tool"] == "calculator"
    assert tool_call_events[0]["data"]["args"]["expression"] == "1+1"

    # Verify tool_result event details
    tool_result_events = [e for e in events if e["event"] == "tool_result"]
    assert len(tool_result_events) == 1
    assert tool_result_events[0]["data"]["tool"] == "calculator"
    assert tool_result_events[0]["data"]["content"] == "2"
    assert isinstance(tool_result_events[0]["data"]["duration_ms"], int)

    # Verify message event details
    message_events = [e for e in events if e["event"] == "message"]
    assert len(message_events) == 1
    assert message_events[0]["data"]["content"] == "1 + 1 = 2"

    # Verify done event details
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    usage = done_events[0]["data"]["usage"]
    assert usage["total_tokens"] >= 0
    assert usage["steps"] >= 1

    # Verify session memory has user message and assistant message
    history = session_memory.get_history()
    assert len(history) >= 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "1+1等于几？"
    # Last message should be assistant with name
    assert history[-1]["role"] == "assistant"
    assert history[-1]["content"] == "1 + 1 = 2"
    assert history[-1].get("name") == "assistant"


@pytest.mark.asyncio
async def test_execute_stream_direct_answer_no_tool_calls(agent: Agent) -> None:
    """Verify executor works when no tool call is needed."""
    direct_response: dict[str, Any] = {
        "id": "chatcmpl-direct",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "你好！有什么可以帮你的吗？",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
    }

    ai_service = MockAIService(responses=[direct_response])
    session_memory = MockSessionMemory(conversation_id=1)

    executor = ReActExecutor(ai_service=ai_service, session_memory=session_memory)
    events: list[dict[str, Any]] = []

    async for event in executor.execute_stream(tenant_id=1, agent=agent, message="你好"):
        events.append(event)

    event_types = [e["event"] for e in events]

    assert "thinking" in event_types
    assert "tool_call" not in event_types, "Should not have tool_call for direct answer"
    assert "message" in event_types
    assert "done" in event_types

    message_events = [e for e in events if e["event"] == "message"]
    assert message_events[0]["data"]["content"] == "你好！有什么可以帮你的吗？"


@pytest.mark.asyncio
async def test_execute_stream_unknown_tool(agent: Agent) -> None:
    """Verify executor handles unknown tool gracefully."""
    response_with_unknown_tool: dict[str, Any] = {
        "id": "chatcmpl-unknown",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "让我使用未知工具。",
                    "tool_calls": [
                        {
                            "id": "call_unknown",
                            "type": "function",
                            "function": {
                                "name": "nonexistent_tool",
                                "arguments": "{}",
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
    }
    # After unknown tool, LLM gets the error and responds
    follow_up_response: dict[str, Any] = {
        "id": "chatcmpl-followup",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "抱歉，我使用的工具不可用。",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 10, "total_tokens": 130},
    }

    ai_service = MockAIService(responses=[response_with_unknown_tool, follow_up_response])
    session_memory = MockSessionMemory(conversation_id=1)

    executor = ReActExecutor(ai_service=ai_service, session_memory=session_memory)
    events: list[dict[str, Any]] = []

    async for event in executor.execute_stream(tenant_id=1, agent=agent, message="用未知工具"):
        events.append(event)

    event_types = [e["event"] for e in events]

    assert "error" in event_types, "Expected error event for unknown tool"
    assert "message" in event_types, "Expected message after error recovery"
    assert "done" in event_types

    error_events = [e for e in events if e["event"] == "error"]
    assert "未知工具" in error_events[0]["data"]["message"]


@pytest.mark.asyncio
async def test_execute_stream_max_iterations(agent: Agent) -> None:
    """Verify executor stops when max_iterations is reached."""
    # Create an agent with max_iterations=1 that always requests tool calls
    loop_agent = Agent(
        id=2,
        tenant_id=1,
        name="Loop Agent",
        system_prompt="你是一个有帮助的助手。",
        model_config=json.dumps({"model": "gpt-4"}),
        tools_config=json.dumps(["calculator"]),
        max_iterations=1,
        is_active=True,
    )

    always_tool_call: dict[str, Any] = {
        "id": "chatcmpl-loop",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "让我计算一下。",
                    "tool_calls": [
                        {
                            "id": "call_loop",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": json.dumps({"expression": "2+2"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
    }

    # max_iterations=1, so after the first tool call, there's no more iterations
    # The tool result message is appended, but the loop doesn't continue for another LLM call
    ai_service = MockAIService(responses=[always_tool_call])
    session_memory = MockSessionMemory(conversation_id=1)

    executor = ReActExecutor(ai_service=ai_service, session_memory=session_memory)
    events: list[dict[str, Any]] = []

    async for event in executor.execute_stream(tenant_id=1, agent=loop_agent, message="2+2等于几？"):
        events.append(event)

    event_types = [e["event"] for e in events]

    assert "tool_call" in event_types
    assert "tool_result" in event_types
    # Should hit max iterations since we had tool_call but no more LLM calls
    assert "error" in event_types, "Expected error for max iterations"
    assert "done" in event_types, "Expected done event"

    # Verify error message mentions max iterations
    error_events = [e for e in events if e["event"] == "error"]
    assert "步内完成" in error_events[0]["data"]["message"]


@pytest.mark.asyncio
async def test_execute_stream_llm_error(agent: Agent) -> None:
    """Verify executor handles LLM errors gracefully."""

    class FailingAIService:
        """AIService that always raises an exception."""

        async def chat_completion(
            self,
            tenant_id: int,
            model: str,
            messages: list[dict[str, str]],
            temperature: float | None = None,
            max_tokens: int | None = None,
            **kwargs: Any,
        ) -> dict[str, Any]:
            raise RuntimeError("LLM connection timeout")

    ai_service = FailingAIService()
    session_memory = MockSessionMemory(conversation_id=1)

    executor = ReActExecutor(ai_service=ai_service, session_memory=session_memory)
    events: list[dict[str, Any]] = []

    async for event in executor.execute_stream(tenant_id=1, agent=agent, message="测试错误"):
        events.append(event)

    event_types = [e["event"] for e in events]

    assert "error" in event_types, "Expected error event"
    error_events = [e for e in events if e["event"] == "error"]
    assert "LLM 调用失败" in error_events[0]["data"]["message"]
    assert "connection timeout" in error_events[0]["data"]["message"]
