import json
import logging
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.services.ai.agent_engine.executor import ReActExecutor
from app.services.ai.agent_engine.models import Agent, AgentConversation
from app.services.ai.agent_engine.repository import AgentRepository, ConversationRepository
from app.services.ai.agent_engine.schemas import AgentCreate, AgentUpdate
from app.services.ai.agent_engine.session_memory import SessionMemory
from app.services.ai.service import AIService
from app.services.ai.knowledge_base.service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class AgentService:
    """Agent 业务逻辑层"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.conv_repo = ConversationRepository(db)
        self.ai_service = AIService(db)
        self.kb_service = KnowledgeBaseService(db)

    # ── Agent CRUD ─────────────────────────────────────────────

    def create_agent(self, tenant_id: int, data: AgentCreate) -> Agent:
        return self.agent_repo.create(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            model_config=json.dumps(data.config, ensure_ascii=False),
            tools_config=json.dumps(data.tools_config),
            max_iterations=data.max_iterations,
        )

    def get_agent(self, agent_id: int) -> Agent | None:
        return self.agent_repo.get_by_id(agent_id)

    def list_agents(self, tenant_id: int) -> list[Agent]:
        return self.agent_repo.list_by_tenant(tenant_id)

    def update_agent(self, tenant_id: int, agent_id: int, data: AgentUpdate) -> Agent:
        agent = self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValidationException("Agent 不存在")
        if agent.tenant_id != tenant_id:
            raise ValidationException("无权操作此 Agent")

        update_kw: dict[str, Any] = {}
        if data.name is not None:
            update_kw["name"] = data.name
        if data.description is not None:
            update_kw["description"] = data.description
        if data.system_prompt is not None:
            update_kw["system_prompt"] = data.system_prompt
        if data.config is not None:
            update_kw["model_config"] = json.dumps(data.config, ensure_ascii=False)
        if data.tools_config is not None:
            update_kw["tools_config"] = json.dumps(data.tools_config)
        if data.max_iterations is not None:
            update_kw["max_iterations"] = data.max_iterations
        if data.is_active is not None:
            update_kw["is_active"] = data.is_active

        updated = self.agent_repo.update(agent_id, **update_kw)
        if not updated:
            raise ValidationException("更新失败")
        return updated

    def delete_agent(self, tenant_id: int, agent_id: int) -> None:
        agent = self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValidationException("Agent 不存在")
        if agent.tenant_id != tenant_id:
            raise ValidationException("无权操作此 Agent")
        # Clean up Redis memory for all conversations
        convs = self.conv_repo.list_by_agent(agent_id)
        for conv in convs:
            mem = SessionMemory(conversation_id=conv.id)
            mem.clear()
        self.agent_repo.delete(agent_id)

    # ── Conversations ──────────────────────────────────────────

    def create_conversation(self, tenant_id: int, user_id: int, agent_id: int, title: str | None = None) -> AgentConversation:
        agent = self.agent_repo.get_by_id(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            raise ValidationException("Agent 不存在")
        return self.conv_repo.create(agent_id=agent_id, tenant_id=tenant_id, user_id=user_id, title=title)

    def list_conversations(self, agent_id: int) -> list[AgentConversation]:
        return self.conv_repo.list_by_agent(agent_id)

    def get_conversation_history(self, conversation_id: int) -> list[dict[str, Any]]:
        mem = SessionMemory(conversation_id=conversation_id)
        return mem.get_history()

    def delete_conversation(self, tenant_id: int, agent_id: int, conv_id: int) -> None:
        conv = self.conv_repo.get_by_id(conv_id)
        if not conv or conv.agent_id != agent_id:
            raise ValidationException("会话不存在")
        agent = self.agent_repo.get_by_id(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            raise ValidationException("无权操作")
        mem = SessionMemory(conversation_id=conv_id)
        mem.clear()
        self.conv_repo.delete(conv_id)

    # ── Chat ───────────────────────────────────────────────────

    async def chat_stream(self, tenant_id: int, user_id: int, agent_id: int, conversation_id: int, message: str) -> AsyncIterator[dict[str, Any]]:
        agent = self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValidationException("Agent 不存在")
        if agent.tenant_id != tenant_id:
            raise ValidationException("无权访问此 Agent")
        if not agent.is_active:
            raise ValidationException("Agent 已禁用")

        conv = self.conv_repo.get_by_id(conversation_id)
        if not conv or conv.agent_id != agent_id:
            raise ValidationException("会话不存在")

        session_memory = SessionMemory(conversation_id=conversation_id)
        executor = ReActExecutor(ai_service=self.ai_service, session_memory=session_memory)

        async for event in executor.execute_stream(tenant_id=tenant_id, agent=agent, message=message):
            yield event
