"""Tests for MemoryCollector.build_context formatting."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.ai.memory.collector import MemoryCollector


@pytest.fixture
def collector() -> MemoryCollector:
    """Return a MemoryCollector with all internal dependencies mocked."""
    col = MemoryCollector(db=MagicMock(), ai_service=MagicMock())  # type: ignore[arg-type]
    col.long_term = MagicMock()
    col.short_term = MagicMock()
    return col


class TestBuildContext:
    """Verifies build_context output formatting."""

    def test_both_facts_and_summaries(self, collector: MemoryCollector) -> None:
        """When both long-term facts and short-term summaries exist,
        both sections should appear in the output."""
        collector.long_term.search.return_value = [
            "User likes Python",
            "Project is a web app",
        ]
        collector.short_term.get_recent.return_value = [
            "Discussed authentication",
            "Chose FastAPI",
        ]

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="Python",
        )

        assert "【相关记忆】" in result
        assert "- User likes Python" in result
        assert "- Project is a web app" in result
        assert "【历史摘要】" in result
        assert "- Discussed authentication" in result
        assert "- Chose FastAPI" in result

    def test_only_facts(self, collector: MemoryCollector) -> None:
        """When only long-term facts exist, only the facts section is shown."""
        collector.long_term.search.return_value = [
            "User likes Python",
        ]
        collector.short_term.get_recent.return_value = []

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="Python",
        )

        assert "【相关记忆】" in result
        assert "【历史摘要】" not in result

    def test_only_summaries(self, collector: MemoryCollector) -> None:
        """When only short-term summaries exist, only the summaries section is shown."""
        collector.long_term.search.return_value = []
        collector.short_term.get_recent.return_value = [
            "Discussed authentication",
        ]

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="Python",
        )

        assert "【相关记忆】" not in result
        assert "【历史摘要】" in result

    def test_neither_facts_nor_summaries(self, collector: MemoryCollector) -> None:
        """When neither facts nor summaries exist, an empty string is returned."""
        collector.long_term.search.return_value = []
        collector.short_term.get_recent.return_value = []

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="Python",
        )

        assert result == ""

    def test_multiple_facts_no_summaries(self, collector: MemoryCollector) -> None:
        """Multiple facts produce one bullet per fact."""
        collector.long_term.search.return_value = [
            "Fact one",
            "Fact two",
            "Fact three",
        ]
        collector.short_term.get_recent.return_value = []

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="test",
        )

        assert "- Fact one" in result
        assert "- Fact two" in result
        assert "- Fact three" in result
        # One bullet per fact with a newline between them
        assert result.count("- ") == 3

    def test_query_is_passed_to_long_term_search(self, collector: MemoryCollector) -> None:
        """The query parameter should be relayed to long_term.search."""
        collector.long_term.search.return_value = []
        collector.short_term.get_recent.return_value = []

        collector.build_context(
            tenant_id=42, agent_id=7, conversation_id=99, query="authentication",
        )

        collector.long_term.search.assert_called_once_with(42, 7, "authentication")
        collector.short_term.get_recent.assert_called_once_with(7, 99)

    def test_context_ordering(self, collector: MemoryCollector) -> None:
        """Facts section should appear before summaries section."""
        collector.long_term.search.return_value = ["Some fact"]
        collector.short_term.get_recent.return_value = ["Some summary"]

        result = collector.build_context(
            tenant_id=1, agent_id=1, conversation_id=1, query="test",
        )

        facts_pos = result.index("【相关记忆】")
        summary_pos = result.index("【历史摘要】")
        assert facts_pos < summary_pos, "Facts should come before summaries"
