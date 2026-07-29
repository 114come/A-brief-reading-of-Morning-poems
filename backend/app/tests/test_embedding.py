import numpy as np
import pytest
from app.services.ai.knowledge_base.embedding import embed_texts


@pytest.mark.slow
def test_embed_texts():
    texts = ["hello world", "test"]
    vectors = embed_texts(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    assert all(isinstance(v, float) for v in vectors[0])


def test_embed_texts_mocked(mocker):
    """Test with mocked SentenceTransformer to avoid model download"""
    mock_model = mocker.MagicMock()
    mock_model.encode.return_value = np.array([[0.1] * 768, [0.2] * 768])
    mocker.patch(
        "app.services.ai.knowledge_base.embedding.get_bge_model",
        return_value=mock_model,
    )
    texts = ["hello", "world"]
    vectors = embed_texts(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 768
