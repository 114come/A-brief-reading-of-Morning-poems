import logging

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.services.ai.agent_engine.repository import AgentRepository
from app.services.ai.memory.collector import MemoryCollector
from app.services.ai.memory.models import AgentMemory
from app.services.ai.memory.repository import MemoryRepository
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)


class MemoryService:
    """High-level memory operations with tenant-level access control."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.ai_service = AIService(db)
        self.repo = MemoryRepository(db)
        self.collector = MemoryCollector(db, self.ai_service)

    def list_memories(
        self,
        tenant_id: int,
        agent_id: int,
        memory_type: str | None = None,
    ) -> list[AgentMemory]:
        """List memories for an agent, optionally filtered by type."""
        return self.repo.list_by_agent(agent_id, memory_type)

    def delete_memory(self, tenant_id: int, memory_id: int) -> None:
        """Delete a single memory after verifying ownership via the agent's tenant."""
        mem = self.repo.get_by_id(memory_id)
        if not mem:
            raise ValidationException("记忆不存在")

        agent = AgentRepository(self.db).get_by_id(mem.agent_id)
        if not agent or agent.tenant_id != tenant_id:
            raise ValidationException("无权操作")

        self.repo.delete(memory_id)

    def clear_agent_memories(self, tenant_id: int, agent_id: int) -> None:
        """Delete all memories for an agent after verifying ownership."""
        agent = AgentRepository(self.db).get_by_id(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            raise ValidationException("无权操作")

        self.repo.delete_by_agent(agent_id)
