import pytest
import numpy as np
from app.services.ai.knowledge_base.qdrant_client import QdrantManager


@pytest.fixture
def qdrant():
    """Use :memory: mode for tests"""
    mgr = QdrantManager(path=":memory:")
    yield mgr
    mgr.client.close()


def test_ensure_collection(qdrant):
    qdrant.ensure_collection(tenant_id=1)
    collections = qdrant.client.get_collections().collections
    names = [c.name for c in collections]
    assert "kb_1" in names


def test_upsert_and_search(qdrant):
    qdrant.ensure_collection(tenant_id=1)
    chunks = ["hello world", "foo bar baz", "python programming"]
    # Create random 768-dim vectors for testing
    vectors = [np.random.rand(768).tolist() for _ in range(3)]
    qdrant.upsert_chunks(tenant_id=1, kb_id=1, doc_id=1, chunks=chunks, vectors=vectors)

    # Search with first vector
    results = qdrant.search(tenant_id=1, kb_id=1, vector=vectors[0], top_k=2)
    assert len(results) == 2
    assert results[0].payload["doc_id"] == 1
    assert results[0].payload["content"] == "hello world"


def test_search_empty_collection(qdrant):
    qdrant.ensure_collection(tenant_id=2)
    vec = np.random.rand(768).tolist()
    results = qdrant.search(tenant_id=2, kb_id=99, vector=vec, top_k=5)
    assert results == []


def test_delete_document(qdrant):
    qdrant.ensure_collection(tenant_id=1)
    chunks = ["doc1 text", "doc2 text"]
    vectors = [np.random.rand(768).tolist() for _ in range(2)]
    qdrant.upsert_chunks(tenant_id=1, kb_id=1, doc_id=1, chunks=chunks, vectors=vectors)

    # Search before delete - should find results
    results = qdrant.search(tenant_id=1, kb_id=1, vector=vectors[0], top_k=5)
    assert len(results) == 2

    qdrant.delete_document(tenant_id=1, doc_id=1)
    results = qdrant.search(tenant_id=1, kb_id=1, vector=vectors[0], top_k=5)
    assert len(results) == 0


def test_delete_by_kb(qdrant):
    qdrant.ensure_collection(tenant_id=1)
    chunks = ["kb text"]
    vectors = [np.random.rand(768).tolist()]
    qdrant.upsert_chunks(tenant_id=1, kb_id=10, doc_id=1, chunks=chunks, vectors=vectors)

    qdrant.delete_by_kb(tenant_id=1, kb_id=10)
    results = qdrant.search(tenant_id=1, kb_id=10, vector=vectors[0], top_k=5)
    assert len(results) == 0
