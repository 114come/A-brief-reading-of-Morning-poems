"""Tests for ShortTermMemory and its helper ``_messages_to_text``."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm import Session

from app.services.ai.memory.short_term import ShortTermMemory, _messages_to_text


# ---------------------------------------------------------------------------
# _messages_to_text
# ---------------------------------------------------------------------------

class TestMessagesToText:
    """Unit tests for the ``_messages_to_text`` formatting function."""

    def test_basic(self) -> None:
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        expected = "user: Hello\nassistant: Hi there"
        assert _messages_to_text(messages) == expected

    def test_single_message(self) -> None:
        messages = [{"role": "user", "content": "Only me"}]
        assert _messages_to_text(messages) == "user: Only me"

    def test_empty_list(self) -> None:
        assert _messages_to_text([]) == ""

    def test_multi_line_content(self) -> None:
        messages = [
            {"role": "user", "content": "Line one\nLine two"},
        ]
        expected = "user: Line one\nLine two"
        assert _messages_to_text(messages) == expected

    def test_system_role(self) -> None:
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
        ]
        expected = "system: You are helpful.\nuser: Hi"
        assert _messages_to_text(messages) == expected


# ---------------------------------------------------------------------------
# ShortTermMemory
# ---------------------------------------------------------------------------

class FakeAIService:
    """AIService stand-in that returns a canned LLM response."""

    def __init__(self) -> None:
        self.chat_completion = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "Test summary."}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        )


class FakeMemoryRepo:
    """In-memory replacement for MemoryRepository."""

    def __init__(self) -> None:
        self.records: list = []

    def create(self, **kwargs: object) -> object:
        obj = type("Memory", (), {"id": 1, **kwargs})()
        self.records.append(obj)
        return obj

    def list_by_agent_conv(
        self,
        agent_id: int,
        conv_id: int,
        memory_type: str | None = None,
        limit: int = 5,
    ) -> list:
        results = [
            r
            for r in self.records
            if r.agent_id == agent_id
            and r.conversation_id == conv_id
            and (memory_type is None or r.memory_type == memory_type)
        ]
        return results[:limit]


@pytest.fixture
def memory() -> ShortTermMemory:
    fake_ai = FakeAIService()
    mem = ShortTermMemory(db=None, ai_service=fake_ai)  # type: ignore[arg-type]
    mem.repo = FakeMemoryRepo()  # type: ignore[assignment]
    return mem


class TestShortTermMemory:
    """Tests for ``ShortTermMemory``."""

    @pytest.mark.asyncio
    async def test_summarize_if_needed_interval_hit(self, memory: ShortTermMemory) -> None:
        """5 user messages triggers a summary."""
        messages = [{"role": "user", "content": str(i)} for i in range(5)]
        result = await memory.summarize_if_needed(
            tenant_id=1,
            agent_id=1,
            conv_id=1,
            messages=messages,
            interval=5,
        )
        assert result == "Test summary."
        assert len(memory.repo.records) == 1
        assert memory.repo.records[0].memory_type == "short_term_summary"
        assert memory.repo.records[0].content == "Test summary."

    @pytest.mark.asyncio
    async def test_summarize_if_needed_interval_miss(self, memory: ShortTermMemory) -> None:
        """4 user messages does NOT trigger a summary when interval=5."""
        messages = [{"role": "user", "content": str(i)} for i in range(4)]
        result = await memory.summarize_if_needed(
            tenant_id=1,
            agent_id=1,
            conv_id=1,
            messages=messages,
            interval=5,
        )
        assert result is None
        assert len(memory.repo.records) == 0

    @pytest.mark.asyncio
    async def test_summarize_if_needed_empty_messages(self, memory: ShortTermMemory) -> None:
        """No messages returns None."""
        result = await memory.summarize_if_needed(
            tenant_id=1,
            agent_id=1,
            conv_id=1,
            messages=[],
            interval=5,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_if_needed_no_user_messages(self, memory: ShortTermMemory) -> None:
        """Only non-user messages should not trigger a summary."""
        messages = [{"role": "assistant", "content": "Hello"} for _ in range(5)]
        result = await memory.summarize_if_needed(
            tenant_id=1,
            agent_id=1,
            conv_id=1,
            messages=messages,
            interval=5,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_if_needed_calls_llm_with_correct_prompt(
        self, memory: ShortTermMemory
    ) -> None:
        """Verify the LLM is called with the summarization prompt."""
        messages = [{"role": "user", "content": "Hello"}]
        await memory.summarize_if_needed(
            tenant_id=42,
            agent_id=1,
            conv_id=1,
            messages=messages,
            interval=1,
        )
        call_args = memory.ai_service.chat_completion.call_args
        assert call_args is not None
        assert call_args.kwargs["tenant_id"] == 42
        assert call_args.kwargs["model"] == "gpt-4o-mini"
        sent_prompt = call_args.kwargs["messages"][0]["content"]
        assert "Summarize" in sent_prompt
        assert "user: Hello" in sent_prompt

    @pytest.mark.asyncio
    async def test_summarize_if_needed_default_interval(self, memory: ShortTermMemory) -> None:
        """Default interval of 5 works correctly."""
        messages = [{"role": "user", "content": str(i)} for i in range(10)]
        result = await memory.summarize_if_needed(
            tenant_id=1,
            agent_id=1,
            conv_id=1,
            messages=messages,
        )
        # 10 % 5 == 0 -> should trigger
        assert result == "Test summary."
        assert len(memory.repo.records) == 1

    def test_get_recent(self, memory: ShortTermMemory) -> None:
        """get_recent returns summaries in insertion order."""
        memory.repo.create(
            tenant_id=1,
            agent_id=1,
            conversation_id=1,
            memory_type="short_term_summary",
            content="Summary 1",
        )
        memory.repo.create(
            tenant_id=1,
            agent_id=1,
            conversation_id=1,
            memory_type="short_term_summary",
            content="Summary 2",
        )
        results = memory.get_recent(agent_id=1, conv_id=1, limit=5)
        assert results == ["Summary 1", "Summary 2"]

    def test_get_recent_empty(self, memory: ShortTermMemory) -> None:
        """get_recent returns empty list when no summaries exist."""
        assert memory.get_recent(agent_id=1, conv_id=1) == []

    def test_get_recent_limit(self, memory: ShortTermMemory) -> None:
        """get_recent respects the limit parameter."""
        for i in range(10):
            memory.repo.create(
                tenant_id=1,
                agent_id=1,
                conversation_id=1,
                memory_type="short_term_summary",
                content=f"Summary {i}",
            )
        results = memory.get_recent(agent_id=1, conv_id=1, limit=3)
        assert len(results) == 3
