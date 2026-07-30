import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbDep, UserDep
from app.core.exceptions import ValidationException
from app.core.response import UnifiedResponse
from app.services.ai.schemas import (
    ChatCompletionRequest,
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
)
from app.services.ai.service import AIService

router = APIRouter(prefix="/llm", tags=["LLM 网关"])


# ─── Provider CRUD ────────────────────────────────────────────────


@router.post("/providers/", response_model=UnifiedResponse[Any])
def create_provider(
    data: LLMProviderCreate,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = AIService(db)
    provider = service.create_provider(
        tenant_id=current_user.tenant_id, data=data
    )
    return UnifiedResponse.success(
        data={
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type,
        }
    )


@router.get("/providers/", response_model=UnifiedResponse[Any])
def list_providers(
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = AIService(db)
    providers = service.list_providers(current_user.tenant_id)
    return UnifiedResponse.success(
        data=[
            LLMProviderResponse.model_validate(p).model_dump()
            for p in providers
        ]
    )


@router.get("/providers/{provider_id}", response_model=UnifiedResponse[Any])
def get_provider(
    provider_id: int,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = AIService(db)
    provider = service.get_provider(provider_id)
    if not provider or provider.tenant_id != current_user.tenant_id:
        raise ValidationException("提供商不存在")
    return UnifiedResponse.success(
        data=LLMProviderResponse.model_validate(provider).model_dump()
    )


@router.put("/providers/{provider_id}", response_model=UnifiedResponse[Any])
def update_provider(
    provider_id: int,
    data: LLMProviderUpdate,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = AIService(db)
    provider = service.update_provider(
        current_user.tenant_id, provider_id, data
    )
    return UnifiedResponse.success(
        data={
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type,
        }
    )


@router.delete("/providers/{provider_id}", response_model=UnifiedResponse[Any])
def delete_provider(
    provider_id: int,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = AIService(db)
    service.delete_provider(current_user.tenant_id, provider_id)
    return UnifiedResponse.success(message="Provider deleted")


# ─── Chat / Completion ────────────────────────────────────────────


@router.post("/chat/completions", response_model=UnifiedResponse[Any])
async def chat_completion(
    req: ChatCompletionRequest,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    """非流式对话补全"""
    service = AIService(db)
    messages = [m.model_dump() for m in req.messages]
    result = await service.chat_completion(
        tenant_id=current_user.tenant_id,
        model=req.model,
        messages=messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    return UnifiedResponse.success(data=result)


@router.post("/chat/completions/stream")
async def chat_completion_stream(
    req: ChatCompletionRequest,
    request: Request,
    db: DbDep,
    current_user: UserDep,
) -> StreamingResponse:
    """流式对话补全（SSE）"""
    if not req.stream:
        raise ValidationException("请设置 stream=true 使用流式接口")

    service = AIService(db)
    messages = [m.model_dump() for m in req.messages]

    async def event_stream():
        async for chunk in service.chat_completion_stream(
            tenant_id=current_user.tenant_id,
            model=req.model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
