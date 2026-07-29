from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.knowledge_base.models import Document, KnowledgeBase


class KnowledgeBaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> KnowledgeBase:
        kb = KnowledgeBase(**kwargs)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def get_by_id(self, kb_id: int) -> KnowledgeBase | None:
        return self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()

    def list_by_tenant(self, tenant_id: int) -> list[KnowledgeBase]:
        return (
            self.db.query(KnowledgeBase)
            .filter(KnowledgeBase.tenant_id == tenant_id)
            .order_by(KnowledgeBase.created_at.desc())
            .all()
        )

    def update(self, kb_id: int, **kwargs: Any) -> KnowledgeBase | None:
        kb = self.get_by_id(kb_id)
        if not kb:
            return None
        for key, value in kwargs.items():
            if hasattr(kb, key):
                setattr(kb, key, value)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def delete(self, kb_id: int) -> bool:
        kb = self.get_by_id(kb_id)
        if not kb:
            return False
        self.db.delete(kb)
        self.db.commit()
        return True

    def update_doc_count(self, kb_id: int) -> None:
        """计算并更新知识库中的文档数量"""
        from sqlalchemy import func as sa_func
        count = (
            self.db.query(sa_func.count(Document.id))
            .filter(Document.kb_id == kb_id)
            .scalar()
        ) or 0
        self.db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).update(
            {"doc_count": count}
        )
        self.db.commit()


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> Document:
        doc = Document(**kwargs)
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_id(self, doc_id: int) -> Document | None:
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def list_by_kb(self, kb_id: int) -> list[Document]:
        return (
            self.db.query(Document)
            .filter(Document.kb_id == kb_id)
            .order_by(Document.created_at.desc())
            .all()
        )

    def update(self, doc_id: int, **kwargs: Any) -> Document | None:
        doc = self.get_by_id(doc_id)
        if not doc:
            return None
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, doc_id: int) -> bool:
        doc = self.get_by_id(doc_id)
        if not doc:
            return False
        self.db.delete(doc)
        self.db.commit()
        return True
