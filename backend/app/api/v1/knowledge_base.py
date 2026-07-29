import logging
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_master_db
from app.core.dependencies import UserDep
from app.core.exceptions import ValidationException
from app.core.response import UnifiedResponse
from app.services.ai.knowledge_base.schemas import (
    DocumentDetailResponse,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.ai.knowledge_base.service import KnowledgeBaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


@router.post("/", response_model=UnifiedResponse[Any])
def create_kb(
    data: KnowledgeBaseCreate,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    kb = service.create_kb(tenant_id=current_user.tenant_id, data=data)
    return UnifiedResponse.success(
        data=KnowledgeBaseResponse.model_validate(kb).model_dump()
    )


@router.get("/", response_model=UnifiedResponse[Any])
def list_kbs(
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    kbs = service.list_kbs(tenant_id=current_user.tenant_id)
    return UnifiedResponse.success(
        data=[KnowledgeBaseResponse.model_validate(kb).model_dump() for kb in kbs]
    )


@router.get("/{kb_id}", response_model=UnifiedResponse[Any])
def get_kb(
    kb_id: int,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    kb = service.get_kb(kb_id)
    if not kb or kb.tenant_id != current_user.tenant_id:
        raise ValidationException("知识库不存在")
    return UnifiedResponse.success(
        data=KnowledgeBaseResponse.model_validate(kb).model_dump()
    )


@router.put("/{kb_id}", response_model=UnifiedResponse[Any])
def update_kb(
    kb_id: int,
    data: KnowledgeBaseUpdate,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    kb = service.update_kb(
        tenant_id=current_user.tenant_id, kb_id=kb_id, data=data
    )
    return UnifiedResponse.success(
        data=KnowledgeBaseResponse.model_validate(kb).model_dump()
    )


@router.delete("/{kb_id}", response_model=UnifiedResponse[Any])
def delete_kb(
    kb_id: int,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    service.delete_kb(tenant_id=current_user.tenant_id, kb_id=kb_id)
    return UnifiedResponse.success(message="知识库已删除")


# ── Document APIs ──────────────────────────────────────────


@router.post("/{kb_id}/documents", response_model=UnifiedResponse[Any])
def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: UserDep = None,  # type: ignore[assignment]
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    if not file.filename:
        raise ValidationException("请选择文件")
    file_bytes = file.file.read()
    service = KnowledgeBaseService(db)
    doc = service.upload_document(
        tenant_id=current_user.tenant_id,
        kb_id=kb_id,
        filename=file.filename,
        file_bytes=file_bytes,
    )
    return UnifiedResponse.success(
        data=DocumentResponse.model_validate(doc).model_dump()
    )


@router.get("/{kb_id}/documents", response_model=UnifiedResponse[Any])
def list_documents(
    kb_id: int,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    docs = service.list_documents(kb_id=kb_id)
    # Verify ownership
    kb = service.get_kb(kb_id)
    if not kb or kb.tenant_id != current_user.tenant_id:
        raise ValidationException("知识库不存在")
    return UnifiedResponse.success(
        data=[DocumentResponse.model_validate(d).model_dump() for d in docs]
    )


@router.get("/{kb_id}/documents/{doc_id}", response_model=UnifiedResponse[Any])
def get_document(
    kb_id: int,
    doc_id: int,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    kb = service.get_kb(kb_id)
    if not kb or kb.tenant_id != current_user.tenant_id:
        raise ValidationException("知识库不存在")
    doc = service.get_document(doc_id)
    if not doc or doc.kb_id != kb_id:
        raise ValidationException("文档不存在")
    content = service.get_document_content(doc_id)
    resp = DocumentDetailResponse(
        **DocumentResponse.model_validate(doc).model_dump(), content=content
    )
    return UnifiedResponse.success(data=resp.model_dump())


@router.delete("/{kb_id}/documents/{doc_id}", response_model=UnifiedResponse[Any])
def delete_document(
    kb_id: int,
    doc_id: int,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    service.delete_document(
        tenant_id=current_user.tenant_id, kb_id=kb_id, doc_id=doc_id
    )
    return UnifiedResponse.success(message="文档已删除")


# ── Search API ─────────────────────────────────────────────


@router.post("/{kb_id}/search", response_model=UnifiedResponse[Any])
def search_kb(
    kb_id: int,
    req: SearchRequest,
    current_user: UserDep,
    db: Session = Depends(get_master_db),
) -> UnifiedResponse[Any]:
    service = KnowledgeBaseService(db)
    results = service.search(
        tenant_id=current_user.tenant_id, kb_id=kb_id, req=req
    )
    return UnifiedResponse.success(
        data=SearchResponse(results=[r.model_dump() for r in results]).model_dump()
    )
