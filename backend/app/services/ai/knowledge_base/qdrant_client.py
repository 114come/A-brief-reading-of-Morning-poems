import logging
from typing import Any

from qdrant_client import QdrantClient as QdrantNativeClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """Qdrant LocalMode 管理器 — 持久化到磁盘文件"""

    def __init__(self, path: str | None = None) -> None:
        self.client = QdrantNativeClient(path=path or settings.QDRANT_STORAGE_PATH)
        self.vector_size = 768
        self.distance = Distance.COSINE

    def _collection_name(self, tenant_id: int) -> str:
        return f"kb_{tenant_id}"

    def ensure_collection(self, tenant_id: int) -> None:
        """确保租户的 collection 存在（幂等）"""
        name = self._collection_name(tenant_id)
        collections = self.client.get_collections().collections
        if not any(c.name == name for c in collections):
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self.distance,
                ),
            )
            logger.info("Created Qdrant collection: %s", name)

    def upsert_chunks(
        self,
        tenant_id: int,
        kb_id: int,
        doc_id: int,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None:
        """批量写入文档的所有 chunk 向量"""
        self.ensure_collection(tenant_id)
        name = self._collection_name(tenant_id)

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            points.append(
                qdrant_models.PointStruct(
                    id=doc_id * 1_000_000 + i,  # integer ID required by Qdrant local mode
                    vector=vector,
                    payload={
                        "doc_id": doc_id,
                        "kb_id": kb_id,
                        "chunk_index": i,
                        "content": chunk,
                    },
                )
            )

        self.client.upsert(collection_name=name, points=points)
        logger.info(
            "Upserted %d chunks for doc_id=%d in collection %s",
            len(points),
            doc_id,
            name,
        )

    def search(
        self,
        tenant_id: int,
        kb_id: int,
        vector: list[float],
        top_k: int = 5,
    ) -> list[Any]:
        """语义搜索，按 kb_id payload 过滤"""
        name = self._collection_name(tenant_id)
        try:
            result = self.client.query_points(
                collection_name=name,
                query=vector,
                query_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="kb_id",
                            match=qdrant_models.MatchValue(value=kb_id),
                        )
                    ]
                ),
                limit=top_k,
                with_payload=True,
            )
            return result.points
        except Exception:
            logger.warning(
                "Search failed for collection %s (may not exist yet)", name
            )
            return []

    def delete_document(self, tenant_id: int, doc_id: int) -> None:
        """删除文档的所有 chunk"""
        name = self._collection_name(tenant_id)
        try:
            self.client.delete(
                collection_name=name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="doc_id",
                                match=qdrant_models.MatchValue(value=doc_id),
                            )
                        ]
                    )
                ),
            )
        except Exception:
            logger.warning(
                "Delete failed for doc_id=%d in collection %s", doc_id, name
            )

    def delete_by_kb(self, tenant_id: int, kb_id: int) -> None:
        """删除知识库的所有 chunk"""
        name = self._collection_name(tenant_id)
        try:
            self.client.delete(
                collection_name=name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="kb_id",
                                match=qdrant_models.MatchValue(value=kb_id),
                            )
                        ]
                    )
                ),
            )
        except Exception:
            logger.warning(
                "Delete failed for kb_id=%d in collection %s", kb_id, name
            )


# Module-level singleton
_qdrant_manager: QdrantManager | None = None


def get_qdrant_manager() -> QdrantManager:
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager
