import hashlib
import json
import logging
from typing import Any

from qdrant_client.http.models import Distance, PointStruct, VectorParams
from sqlalchemy.orm import Session

from app.services.ai.knowledge_base.embedding import embed_texts
from app.services.ai.knowledge_base.qdrant_client import get_qdrant_manager
from app.services.ai.memory.repository import MemoryRepository

logger = logging.getLogger(__name__)


def _fact_id(agent_id: int, conv_id: int, index: int) -> int:
    """Deterministic positive int suitable for Qdrant ``PointStruct.id``."""
    raw = hashlib.sha256(f"{agent_id}_{conv_id}_{index}".encode()).hexdigest()
    return int(raw, 16) % (2**63)


class LongTermMemory:
    """Long-term memory backed by Qdrant vector search + MySQL references."""

    def __init__(self, db: Session, ai_service: Any) -> None:
        self.db = db
        self.ai_service = ai_service
        self.repo = MemoryRepository(db)
        self.qdrant = get_qdrant_manager()

    def _collection(self, tenant_id: int) -> str:
        return f"mem_{tenant_id}"

    def _ensure_collection(self, tenant_id: int) -> None:
        """Create the Qdrant collection for *tenant_id* if it does not exist."""
        name = self._collection(tenant_id)
        collections = self.qdrant.client.get_collections().collections
        if not any(c.name == name for c in collections):
            self.qdrant.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self.qdrant.vector_size,
                    distance=self.qdrant.distance,
                ),
            )
            logger.info("Created Qdrant memory collection: %s", name)

    async def extract_and_store(
        self,
        tenant_id: int,
        agent_id: int,
        conv_id: int,
        messages: list[dict[str, str]],
    ) -> None:
        """Extract facts from *messages* via LLM, embed them, and persist to
        Qdrant + store a reference row in MySQL.
        """
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        prompt = (
            "Extract key facts and information from the following conversation. "
            "Return each fact as a separate line, with no numbering or bullets:\n\n"
            f"{text}"
        )
        result = await self.ai_service.chat_completion(
            tenant_id=tenant_id,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        facts_text = result["choices"][0]["message"]["content"]
        facts = [line.strip() for line in facts_text.split("\n") if line.strip()]

        if not facts:
            return

        # Embed facts and store in Qdrant
        vectors = embed_texts(facts)
        self._ensure_collection(tenant_id)
        collection_name = self._collection(tenant_id)

        points = [
            PointStruct(
                id=_fact_id(agent_id, conv_id, i),
                vector=vector,
                payload={
                    "agent_id": agent_id,
                    "conversation_id": conv_id,
                    "content": fact,
                },
            )
            for i, (fact, vector) in enumerate(zip(facts, vectors, strict=True))
        ]

        self.qdrant.client.upsert(collection_name=collection_name, points=points)
        logger.info(
            "Stored %d facts in Qdrant for agent_id=%d conv_id=%d",
            len(facts),
            agent_id,
            conv_id,
        )

        # Reference row in MySQL
        self.repo.create(
            tenant_id=tenant_id,
            agent_id=agent_id,
            conversation_id=conv_id,
            memory_type="long_term_fact",
            content=facts_text,
            metadata=json.dumps({"fact_count": len(facts)}),
        )

    def search(
        self,
        tenant_id: int,
        agent_id: int,
        query: str,
        top_k: int = 5,
    ) -> list[str]:
        """Semantic search over long-term memory. Returns matching fact strings."""
        vector = embed_texts([query])[0]
        collection_name = self._collection(tenant_id)

        try:
            result = self.qdrant.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=top_k,
                with_payload=True,
            )
            return [
                p.payload["content"]
                for p in result.points
                if p.payload and "content" in p.payload
            ]
        except Exception:
            logger.warning(
                "Memory search failed for collection %s (may not exist yet)",
                collection_name,
            )
            return []
