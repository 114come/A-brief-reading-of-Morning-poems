from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.agent_engine.models import Agent, AgentConversation


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> Agent:
        agent = Agent(**kwargs)
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get_by_id(self, agent_id: int) -> Agent | None:
        return self.db.query(Agent).filter(Agent.id == agent_id).first()

    def list_by_tenant(self, tenant_id: int) -> list[Agent]:
        return (
            self.db.query(Agent)
            .filter(Agent.tenant_id == tenant_id)
            .order_by(Agent.created_at.desc())
            .all()
        )

    def update(self, agent_id: int, **kwargs: Any) -> Agent | None:
        agent = self.get_by_id(agent_id)
        if not agent:
            return None
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def delete(self, agent_id: int) -> bool:
        agent = self.get_by_id(agent_id)
        if not agent:
            return False
        self.db.delete(agent)
        self.db.commit()
        return True


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> AgentConversation:
        conv = AgentConversation(**kwargs)
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_by_id(self, conv_id: int) -> AgentConversation | None:
        return (
            self.db.query(AgentConversation)
            .filter(AgentConversation.id == conv_id)
            .first()
        )

    def list_by_agent(self, agent_id: int) -> list[AgentConversation]:
        return (
            self.db.query(AgentConversation)
            .filter(AgentConversation.agent_id == agent_id)
            .order_by(AgentConversation.created_at.desc())
            .all()
        )

    def list_by_tenant(self, tenant_id: int) -> list[AgentConversation]:
        return (
            self.db.query(AgentConversation)
            .filter(AgentConversation.tenant_id == tenant_id)
            .order_by(AgentConversation.created_at.desc())
            .all()
        )

    def update(self, conv_id: int, **kwargs: Any) -> AgentConversation | None:
        conv = self.get_by_id(conv_id)
        if not conv:
            return None
        for key, value in kwargs.items():
            if hasattr(conv, key):
                setattr(conv, key, value)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete(self, conv_id: int) -> bool:
        conv = self.get_by_id(conv_id)
        if not conv:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True
