from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    description: str | None
    doc_count: int
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kb_id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    content: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResultItem(BaseModel):
    doc_id: int
    doc_name: str
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
