"""Tests for LongTermMemory."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from qdrant_client.http.models import Distance, PointStruct, Record

from app.services.ai.memory.long_term import LongTermMemory, _fact_id
from app.services.ai.memory.short_term import _messages_to_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_qdrant_client() -> object:
    """Return a QdrantClient stand-in backed by in-memory dicts.

    Supports only the methods that ``LongTermMemory`` uses.
    """

    class FakeQdrantClient:
        def __init__(self) -> None:
            self.collections: set[str] = set()
            self.points: dict[str, list[Record]] = {}

        def get_collections(self) -> object:
            return type(
                "CollectionsResult",
                (),
                {
                    "collections": [
                        type("Collection", (), {"name": c})()
                        for c in self.collections
                    ]
                },
            )()

        def create_collection(self, collection_name: str, **kwargs: object) -> None:
            self.collections.add(collection_name)

        def upsert(self, collection_name: str, points: list[PointStruct]) -> None:
            if collection_name not in self.points:
                self.points[collection_name] = []
            for pt in points:
                self.points[collection_name].append(
                    Record(
                        id=pt.id,
                        payload=pt.payload,
                        vector=pt.vector,
                    )
                )

        def query_points(
            self,
            collection_name: str,
            query: list[float],
            limit: int = 5,
            with_payload: bool = True,
        ) -> object:
            stored = self.points.get(collection_name, [])
            scored = sorted(stored, key=lambda r: -sum(r.vector or [0]))[:limit]
            return type(
                "QueryResult",
                (),
                {"points": scored},
            )()

    return FakeQdrantClient()


@pytest.fixture
def memory() -> LongTermMemory:
    fake_ai = type(
        "FakeAI",
        (),
        {"chat_completion": AsyncMock(
            return_value={
                "choices": [{"message": {"content": "User likes dogs."}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            }
        )},
    )()
    mem = LongTermMemory(db=None, ai_service=fake_ai)  # type: ignore[arg-type]

    # Swap in a fake memory repo
    fake_repo = type(
        "FakeRepo",
        (),
        {
            "records": [],
            "create": lambda self, **kw: (
                self.records.append(kw)
            ),
        },
    )()
    mem.repo = fake_repo  # type: ignore[assignment]

    # Wire the Qdrant manager with a fake client
    fake_client = make_fake_qdrant_client()
    mem.qdrant.client = fake_client  # type: ignore[assignment]
    mem.qdrant.vector_size = 4  # small test dimension
    mem.qdrant.distance = Distance.COSINE

    return mem


# ---------------------------------------------------------------------------
# _fact_id
# ---------------------------------------------------------------------------

class TestFactId:
    def test_deterministic(self) -> None:
        assert _fact_id(1, 2, 3) == _fact_id(1, 2, 3)

    def test_different_agent(self) -> None:
        assert _fact_id(1, 2, 3) != _fact_id(2, 2, 3)

    def test_different_index(self) -> None:
        assert _fact_id(1, 2, 3) != _fact_id(1, 2, 4)

    def test_positive_int(self) -> None:
        assert isinstance(_fact_id(1, 2, 3), int)
        assert _fact_id(1, 2, 3) > 0


# ---------------------------------------------------------------------------
# _collection
# ---------------------------------------------------------------------------

class TestCollection:
    def test_returns_expected_name(self) -> None:
        mem = LongTermMemory(db=None, ai_service=None)  # type: ignore[arg-type]
        assert mem._collection(1) == "mem_1"
        assert mem._collection(42) == "mem_42"


# ---------------------------------------------------------------------------
# _ensure_collection
# ---------------------------------------------------------------------------

class TestEnsureCollection:
    def test_creates_when_missing(self, memory: LongTermMemory) -> None:
        memory._ensure_collection(1)
        assert "mem_1" in memory.qdrant.client.collections

    def test_skips_when_exists(self, memory: LongTermMemory) -> None:
        memory._ensure_collection(1)
        memory._ensure_collection(1)  # second call should not raise
        assert len(memory.qdrant.client.collections) == 1

    def test_multiple_tenants(self, memory: LongTermMemory) -> None:
        memory._ensure_collection(1)
        memory._ensure_collection(2)
        assert "mem_1" in memory.qdrant.client.collections
        assert "mem_2" in memory.qdrant.client.collections


# ---------------------------------------------------------------------------
# extract_and_store
# ---------------------------------------------------------------------------

class TestExtractAndStore:
    @pytest.mark.asyncio
    async def test_extracts_and_stores_facts(self, memory: LongTermMemory) -> None:
        messages = [
            {"role": "user", "content": "I love dogs"},
            {"role": "assistant", "content": "That's great!"},
        ]

        # Override AI mock to return 2 facts
        memory.ai_service.chat_completion = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": "User loves dogs.\nUser is happy."}}
                ],
                "usage": {},
            }
        )

        with patch(
            "app.services.ai.memory.long_term.embed_texts",
            return_value=[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
        ):
            await memory.extract_and_store(
                tenant_id=1,
                agent_id=1,
                conv_id=1,
                messages=messages,
            )

        # Qdrant should have 2 points
        collection = memory.qdrant.client.points.get("mem_1", [])
        assert len(collection) == 2

        # MySQL should have 1 reference record
        assert len(memory.repo.records) == 1
        assert memory.repo.records[0]["memory_type"] == "long_term_fact"

    @pytest.mark.asyncio
    async def test_calls_llm_with_extract_prompt(self, memory: LongTermMemory) -> None:
        messages = [{"role": "user", "content": "Tell me about AI"}]

        with patch(
            "app.services.ai.memory.long_term.embed_texts",
            return_value=[[0.1, 0.2, 0.3, 0.4]],
        ):
            await memory.extract_and_store(
                tenant_id=1, agent_id=1, conv_id=1, messages=messages
            )

        call_args = memory.ai_service.chat_completion.call_args
        assert call_args is not None
        assert "Extract" in call_args.kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_no_facts_no_store(self, memory: LongTermMemory) -> None:
        """When LLM returns empty text, nothing is stored."""
        memory.ai_service.chat_completion = AsyncMock(
            return_value={
                "choices": [{"message": {"content": ""}}],
                "usage": {},
            }
        )
        await memory.extract_and_store(
            tenant_id=1, agent_id=1, conv_id=1, messages=[]
        )
        assert len(memory.qdrant.client.points.get("mem_1", [])) == 0
        assert len(memory.repo.records) == 0

    @pytest.mark.asyncio
    async def test_ensure_collection_called(self, memory: LongTermMemory) -> None:
        """Collection should be created if it doesn't exist."""
        messages = [{"role": "user", "content": "Hello"}]

        with patch(
            "app.services.ai.memory.long_term.embed_texts",
            return_value=[[0.1, 0.2, 0.3, 0.4]],
        ):
            assert "mem_1" not in memory.qdrant.client.collections
            await memory.extract_and_store(
                tenant_id=1, agent_id=1, conv_id=1, messages=messages
            )
            assert "mem_1" in memory.qdrant.client.collections


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_returns_matching_facts(self, memory: LongTermMemory) -> None:
        """search returns facts stored in Qdrant."""
        # Pre-populate Qdrant
        with patch(
            "app.services.ai.memory.long_term.embed_texts",
            side_effect=[
                [[0.1, 0.2, 0.3, 0.4]],  # for the fact embedding
                [[0.1, 0.2, 0.3, 0.4]],  # for the search query embedding
            ],
        ):
            memory._ensure_collection(1)
            memory.qdrant.client.upsert(
                "mem_1",
                [
                    PointStruct(
                        id=1,
                        vector=[0.1, 0.2, 0.3, 0.4],
                        payload={"agent_id": 1, "content": "User likes dogs"},
                    ),
                    PointStruct(
                        id=2,
                        vector=[0.5, 0.6, 0.7, 0.8],
                        payload={"agent_id": 1, "content": "User is a developer"},
                    ),
                ],
            )

            results = memory.search(tenant_id=1, agent_id=1, query="dogs", top_k=2)

        assert len(results) > 0
        assert isinstance(results[0], str)

    def test_returns_empty_when_no_collection(self, memory: LongTermMemory) -> None:
        """Search on a non-existent collection returns empty list."""
        with patch(
            "app.services.ai.memory.long_term.embed_texts",
            return_value=[[0.1, 0.2, 0.3, 0.4]],
        ):
            results = memory.search(tenant_id=999, agent_id=1, query="anything")
        assert results == []
