import logging
import os
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.services.ai.knowledge_base.chunker import fixed_length_chunk
from app.services.ai.knowledge_base.embedding import embed_texts
from app.services.ai.knowledge_base.models import Document, KnowledgeBase
from app.services.ai.knowledge_base.qdrant_client import get_qdrant_manager
from app.services.ai.knowledge_base.repository import (
    DocumentRepository,
    KnowledgeBaseRepository,
)
from app.services.ai.knowledge_base.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    SearchRequest,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.qdrant = get_qdrant_manager()

    # ── KB CRUD ──────────────────────────────────────────────

    def create_kb(self, tenant_id: int, data: KnowledgeBaseCreate) -> KnowledgeBase:
        return self.kb_repo.create(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )

    def get_kb(self, kb_id: int) -> KnowledgeBase | None:
        return self.kb_repo.get_by_id(kb_id)

    def list_kbs(self, tenant_id: int) -> list[KnowledgeBase]:
        return self.kb_repo.list_by_tenant(tenant_id)

    def update_kb(
        self, tenant_id: int, kb_id: int, data: KnowledgeBaseUpdate
    ) -> KnowledgeBase:
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise ValidationException("知识库不存在")
        if kb.tenant_id != tenant_id:
            raise ValidationException("无权操作此知识库")
        kwargs: dict[str, Any] = {}
        if data.name is not None:
            kwargs["name"] = data.name
        if data.description is not None:
            kwargs["description"] = data.description
        updated = self.kb_repo.update(kb_id, **kwargs)
        if not updated:
            raise ValidationException("更新失败")
        return updated

    def delete_kb(self, tenant_id: int, kb_id: int) -> None:
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise ValidationException("知识库不存在")
        if kb.tenant_id != tenant_id:
            raise ValidationException("无权操作此知识库")
        self.qdrant.delete_by_kb(tenant_id, kb_id)
        self.kb_repo.delete(kb_id)

    # ── Document CRUD ────────────────────────────────────────

    def list_documents(self, kb_id: int) -> list[Document]:
        return self.doc_repo.list_by_kb(kb_id)

    def get_document(self, doc_id: int) -> Document | None:
        return self.doc_repo.get_by_id(doc_id)

    def upload_document(
        self, tenant_id: int, kb_id: int, filename: str, file_bytes: bytes
    ) -> Document:
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise ValidationException("知识库不存在")

        # Normalize file type
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        allowed_types = {"pdf", "docx", "txt", "md"}
        if ext not in allowed_types:
            raise ValidationException(f"不支持的文件类型: .{ext}")

        # Save file to disk
        upload_dir = os.path.join(
            settings.UPLOAD_STORAGE_PATH, str(tenant_id)
        )
        os.makedirs(upload_dir, exist_ok=True)

        doc = self.doc_repo.create(
            kb_id=kb_id,
            tenant_id=tenant_id,
            filename=filename,
            file_type=ext,
            file_size=len(file_bytes),
            file_path="",  # will update after save
            status="pending",
        )

        file_path = os.path.join(upload_dir, f"{doc.id}_{filename}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Update file_path
        self.doc_repo.update(doc.id, file_path=file_path)

        # Process document synchronously
        try:
            self._process_document(doc.id, file_path, ext)
            self.kb_repo.update_doc_count(kb_id)
        except Exception as e:
            logger.exception("Document processing failed: doc_id=%d", doc.id)
            self.doc_repo.update(doc.id, status="failed", error_message=str(e))
            self.db.refresh(doc)

        self.db.refresh(doc)
        return doc

    def delete_document(self, tenant_id: int, kb_id: int, doc_id: int) -> None:
        doc = self.doc_repo.get_by_id(doc_id)
        if not doc or doc.kb_id != kb_id:
            raise ValidationException("文档不存在")
        # Verify ownership via KB
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise ValidationException("无权操作此文档")

        # Delete from Qdrant
        self.qdrant.delete_document(tenant_id, doc_id)

        # Delete file
        if doc.file_path and os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        self.doc_repo.delete(doc_id)
        self.kb_repo.update_doc_count(kb_id)

    # ── Processing Pipeline ──────────────────────────────────

    def _process_document(
        self, doc_id: int, file_path: str, file_type: str
    ) -> None:
        """文档处理流水线：解析 → 分块 → Embedding → 写入 Qdrant"""
        self.doc_repo.update(doc_id, status="processing")

        # 1. Parse text
        text = self._parse_file(file_path, file_type)
        if not text.strip():
            raise ValidationException("文档内容为空")

        # 2. Chunk
        chunks = fixed_length_chunk(
            text,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )

        # 3. Embedding
        vectors = embed_texts(chunks)

        # 4. Store in Qdrant (get kb_id from doc)
        doc = self.doc_repo.get_by_id(doc_id)
        if not doc:
            raise ValidationException("文档已不存在")
        self.qdrant.upsert_chunks(
            tenant_id=doc.tenant_id,
            kb_id=doc.kb_id,
            doc_id=doc_id,
            chunks=chunks,
            vectors=vectors,
        )

        # 5. Update status
        self.doc_repo.update(doc_id, status="ready", chunk_count=len(chunks))

    def _parse_file(self, file_path: str, file_type: str) -> str:
        """根据文件类型选择解析器"""
        if file_type == "txt":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if file_type == "md":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        if file_type == "docx":
            from docx import Document as DocxDocument

            docx = DocxDocument(file_path)
            return "\n".join(p.text for p in docx.paragraphs)

        if file_type == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)

        raise ValidationException(f"不支持的文件类型: {file_type}")

    # ── Search ───────────────────────────────────────────────

    def search(
        self, tenant_id: int, kb_id: int, req: SearchRequest
    ) -> list[SearchResultItem]:
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb or kb.tenant_id != tenant_id:
            raise ValidationException("知识库不存在")

        # 1. Embed the query
        query_vector = embed_texts([req.query])[0]

        # 2. Search Qdrant
        hits = self.qdrant.search(
            tenant_id=tenant_id,
            kb_id=kb_id,
            vector=query_vector,
            top_k=req.top_k,
        )

        # 3. Map results (look up doc names)
        doc_ids = {h.payload["doc_id"] for h in hits}
        docs_map: dict[int, str] = {}
        for did in doc_ids:
            doc = self.doc_repo.get_by_id(did)
            if doc:
                docs_map[did] = doc.filename

        results = []
        for hit in hits:
            results.append(
                SearchResultItem(
                    doc_id=hit.payload["doc_id"],
                    doc_name=docs_map.get(hit.payload["doc_id"], "Unknown"),
                    chunk_index=hit.payload["chunk_index"],
                    content=hit.payload["content"],
                    score=hit.score,
                )
            )
        return results

    def get_document_content(self, doc_id: int) -> str | None:
        """获取文档原始内容（用于详情页预览）"""
        doc = self.doc_repo.get_by_id(doc_id)
        if not doc or not doc.file_path:
            return None
        if not os.path.exists(doc.file_path):
            return None
        return self._parse_file(doc.file_path, doc.file_type)
