from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.memory.models import AgentMemory


class MemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> AgentMemory:
        # Map 'metadata' → 'metadata_' since the model uses metadata_ as the
        # Python attribute name (with "metadata" as the DB column name).
        if "metadata" in kwargs and "metadata_" not in kwargs:
            kwargs["metadata_"] = kwargs.pop("metadata")

        memory = AgentMemory(**kwargs)
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def get_by_id(self, memory_id: int) -> AgentMemory | None:
        return (
            self.db.query(AgentMemory)
            .filter(AgentMemory.id == memory_id)
            .first()
        )

    def list_by_agent(
        self,
        agent_id: int,
        memory_type: str | None = None,
        limit: int = 50,
    ) -> list[AgentMemory]:
        q = self.db.query(AgentMemory).filter(AgentMemory.agent_id == agent_id)
        if memory_type:
            q = q.filter(AgentMemory.memory_type == memory_type)
        return q.order_by(AgentMemory.created_at.desc()).limit(limit).all()

    def list_by_agent_conv(
        self,
        agent_id: int,
        conv_id: int,
        memory_type: str | None = None,
        limit: int = 5,
    ) -> list[AgentMemory]:
        q = self.db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id,
            AgentMemory.conversation_id == conv_id,
        )
        if memory_type:
            q = q.filter(AgentMemory.memory_type == memory_type)
        return q.order_by(AgentMemory.created_at.desc()).limit(limit).all()

    def delete(self, memory_id: int) -> bool:
        memory = self.get_by_id(memory_id)
        if not memory:
            return False
        self.db.delete(memory)
        self.db.commit()
        return True

    def delete_by_agent(self, agent_id: int) -> None:
        self.db.query(AgentMemory).filter(
            AgentMemory.agent_id == agent_id
        ).delete()
        self.db.commit()
