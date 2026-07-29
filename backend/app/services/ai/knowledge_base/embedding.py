import logging
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def get_bge_model() -> SentenceTransformer:
    """线程安全的懒加载单例 — 首次调用时下载 BGE 模型"""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                logger.info(
                    "Loading embedding model: %s (first call may download)",
                    settings.EMBEDDING_MODEL_NAME,
                )
                _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
                logger.info("Embedding model loaded")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量将文本编码为 768 维向量"""
    model = get_bge_model()
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,  # 归一化后可直接用内积 = cosine
    )
    return embeddings.tolist()
