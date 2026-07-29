"""Tests for Redis-backed agent session memory."""

from __future__ import annotations

from typing import Any

from app.services.ai.agent_engine.session_memory import SessionMemory, _key


# ---------------------------------------------------------------------------
# FakeRedis – a dict-based mock for the Redis commands we need
# ---------------------------------------------------------------------------

class FakeRedis:
    """In-memory mock of the small Redis surface used by ``SessionMemory``.

    Only implements ``rpush``, ``lrange``, ``llen``, ``ltrim``, ``delete``,
    and ``expire``.  ``expire`` is a no-op (we verify TTL separately via
    integration or config tests).
    """

    def __init__(self) -> None:
        self._store: dict[str, list[str]] = {}

    # ---- commands used by SessionMemory ------------------------------------

    def rpush(self, key: str, value: str) -> int:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(value)
        return len(self._store[key])

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        lst = self._store.get(key, [])
        if end == -1:
            end = len(lst) - 1
        return lst[start : end + 1]

    def llen(self, key: str) -> int:
        return len(self._store.get(key, []))

    def ltrim(self, key: str, start: int, end: int) -> None:
        lst = self._store.get(key, [])
        if end == -1:
            end = len(lst) - 1
        self._store[key] = lst[start : end + 1]

    def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    def expire(self, key: str, _seconds: int) -> int:
        # No-op — TTL is covered by config integration tests.
        return 1 if key in self._store else 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_memory(conversation_id: int = 1) -> tuple[SessionMemory, FakeRedis]:
    """Return a ``SessionMemory`` wired to a fresh ``FakeRedis``."""
    fake = FakeRedis()
    mem = SessionMemory(conversation_id, redis_client=fake)  # type: ignore[arg-type]
    return mem, fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSessionMemory:
    """Suite of tests for ``SessionMemory``."""

    def test_push_and_get_history(self) -> None:
        """Pushing messages and retrieving them returns messages in FIFO order."""
        mem, _ = make_memory()

        mem.push_message("user", "Hello")
        mem.push_message("assistant", "Hi there!")
        mem.push_message("user", "How are you?", name="test_tool")

        history = mem.get_history()
        assert len(history) == 3

        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert "name" not in history[0]

        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"

        assert history[2]["role"] == "user"
        assert history[2]["content"] == "How are you?"
        assert history[2]["name"] == "test_tool"

    def test_get_history_empty(self) -> None:
        """Getting history for a conversation with no messages returns empty list."""
        mem, _ = make_memory(conversation_id=99)
        assert mem.get_history() == []

    def test_clear(self) -> None:
        """Clearing a session removes all messages."""
        mem, _ = make_memory()

        mem.push_message("user", "Hello")
        mem.push_message("assistant", "World")
        assert len(mem.get_history()) == 2

        mem.clear()
        assert mem.get_history() == []

    def test_clear_empty(self) -> None:
        """Clearing an already empty session does not raise."""
        mem, _ = make_memory(conversation_id=42)
        mem.clear()  # should not raise
        assert mem.get_history() == []

    def test_trim(self) -> None:
        """Trimming keeps only the most recent *max_messages* messages."""
        mem, _ = make_memory()

        # Push 10 messages
        for i in range(10):
            mem.push_message("user", str(i))

        # Trim to last 3
        mem.trim(max_messages=3)

        history = mem.get_history()
        assert len(history) == 3
        assert [m["content"] for m in history] == ["7", "8", "9"]

    def test_trim_does_nothing_when_under_limit(self) -> None:
        """Trimming with max_messages larger than current length is a no-op."""
        mem, _ = make_memory()

        for i in range(5):
            mem.push_message("user", str(i))

        mem.trim(max_messages=10)
        assert len(mem.get_history()) == 5
