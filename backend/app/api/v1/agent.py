import json
import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.dependencies import DbDep, UserDep
from app.core.exceptions import ValidationException
from app.core.response import UnifiedResponse
from app.services.ai.agent_engine.schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    ChatRequest,
    ConversationCreate,
    ConversationResponse,
)
from app.services.ai.agent_engine.service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["智能体"])


# ── Agent CRUD ────────────────────────────────────────────


@router.post("/", response_model=UnifiedResponse[Any])
def create_agent(
    data: AgentCreate,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    agent = service.create_agent(tenant_id=current_user.tenant_id, data=data)
    return UnifiedResponse.success(
        data=AgentResponse.model_validate(agent).model_dump(by_alias=True)
    )


@router.get("/", response_model=UnifiedResponse[Any])
def list_agents(
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    agents = service.list_agents(tenant_id=current_user.tenant_id)
    return UnifiedResponse.success(
        data=[AgentResponse.model_validate(a).model_dump(by_alias=True) for a in agents]
    )


@router.get("/{agent_id}", response_model=UnifiedResponse[Any])
def get_agent(
    agent_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    if not agent or agent.tenant_id != current_user.tenant_id:
        raise ValidationException("Agent 不存在")
    return UnifiedResponse.success(
        data=AgentResponse.model_validate(agent).model_dump(by_alias=True)
    )


@router.put("/{agent_id}", response_model=UnifiedResponse[Any])
def update_agent(
    agent_id: int,
    data: AgentUpdate,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    agent = service.update_agent(
        tenant_id=current_user.tenant_id, agent_id=agent_id, data=data
    )
    return UnifiedResponse.success(
        data=AgentResponse.model_validate(agent).model_dump(by_alias=True)
    )


@router.delete("/{agent_id}", response_model=UnifiedResponse[Any])
def delete_agent(
    agent_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    service.delete_agent(tenant_id=current_user.tenant_id, agent_id=agent_id)
    return UnifiedResponse.success(message="Agent 已删除")


# ── Conversation APIs ─────────────────────────────────────


@router.post("/{agent_id}/conversations", response_model=UnifiedResponse[Any])
def create_conversation(
    agent_id: int,
    data: ConversationCreate,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    conv = service.create_conversation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        agent_id=agent_id,
        title=data.title,
    )
    return UnifiedResponse.success(
        data=ConversationResponse.model_validate(conv).model_dump()
    )


@router.get("/{agent_id}/conversations", response_model=UnifiedResponse[Any])
def list_conversations(
    agent_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    # Verify agent ownership
    agent = service.get_agent(agent_id)
    if not agent or agent.tenant_id != current_user.tenant_id:
        raise ValidationException("Agent 不存在")
    convs = service.list_conversations(agent_id)
    # Enrich with message_count from Redis
    from app.services.ai.agent_engine.session_memory import SessionMemory

    result: list[dict[str, Any]] = []
    for conv in convs:
        conv_data = ConversationResponse.model_validate(conv).model_dump()
        try:
            mem = SessionMemory(conversation_id=conv.id)
            conv_data["message_count"] = len(mem.get_history())
        except Exception:
            conv_data["message_count"] = 0
        result.append(conv_data)
    return UnifiedResponse.success(data=result)


@router.get("/{agent_id}/conversations/{conv_id}", response_model=UnifiedResponse[Any])
def get_conversation_history(
    agent_id: int,
    conv_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    # Verify agent ownership
    agent = service.get_agent(agent_id)
    if not agent or agent.tenant_id != current_user.tenant_id:
        raise ValidationException("Agent 不存在")
    # Verify conversation belongs to agent
    conv = service.conv_repo.get_by_id(conv_id)
    if not conv or conv.agent_id != agent_id:
        raise ValidationException("会话不存在")
    try:
        history = service.get_conversation_history(conv_id)
    except Exception:
        history = []
    return UnifiedResponse.success(
        data={
            "conversation": ConversationResponse.model_validate(conv).model_dump(),
            "messages": history,
        }
    )


@router.delete("/{agent_id}/conversations/{conv_id}", response_model=UnifiedResponse[Any])
def delete_conversation(
    agent_id: int,
    conv_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = AgentService(db)
    service.delete_conversation(
        tenant_id=current_user.tenant_id, agent_id=agent_id, conv_id=conv_id
    )
    return UnifiedResponse.success(message="会话已删除")


# ── Chat API (SSE) ────────────────────────────────────────


@router.post("/{agent_id}/conversations/{conv_id}/chat", response_class=StreamingResponse)
async def chat(
    agent_id: int,
    conv_id: int,
    req: ChatRequest,
    current_user: UserDep,
    db: DbDep,
) -> StreamingResponse:
    service = AgentService(db)

    async def event_stream() -> Any:
        try:
            async for event in service.chat_stream(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                agent_id=agent_id,
                conversation_id=conv_id,
                message=req.message,
            ):
                yield f"event: {event['event']}\n"
                yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except ValidationException as e:
            yield f"event: error\ndata: {json.dumps({'message': e.message})}\n\n"
        except Exception:
            logger.exception("Chat stream error")
            yield f"event: error\ndata: {json.dumps({'message': '服务器内部错误'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
