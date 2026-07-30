"""Tests for MemoryService (list/delete operations with SQLite fixture)."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.exceptions import ValidationException
from app.services.ai.agent_engine.models import Agent
from app.services.ai.agent_engine.repository import AgentRepository
from app.services.ai.memory.models import AgentMemory
from app.services.ai.memory.repository import MemoryRepository
from app.services.ai.memory.service import MemoryService
from app.services.tenant.models import Tenant

# In-memory SQLite engine for tests
TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


def _create_tenant(db: Session) -> Tenant:
    tenant = Tenant(
        name="测试租户",
        code="memory_svc_test",
        db_name="tenant_memory_svc_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _create_agent(db: Session, tenant_id: int, name: str = "测试助手") -> Agent:
    repo = AgentRepository(db)
    return repo.create(
        tenant_id=tenant_id,
        name=name,
        description="测试用 Agent",
        system_prompt="你是一个测试助手",
        model_config="{}",
        tools_config="[]",
        max_iterations=10,
        is_active=True,
    )


class TestListMemories:
    def test_list_memories_empty(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        svc = MemoryService(db)

        memories = svc.list_memories(tenant_id=tenant.id, agent_id=agent.id)
        assert memories == []

    def test_list_memories_all_types(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        repo = MemoryRepository(db)

        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="摘要1",
        )
        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=2,
            memory_type="long_term_fact", content="事实1",
        )

        svc = MemoryService(db)
        memories = svc.list_memories(tenant_id=tenant.id, agent_id=agent.id)
        assert len(memories) == 2

    def test_list_memories_filter_by_type(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        repo = MemoryRepository(db)

        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="摘要1",
        )
        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=2,
            memory_type="long_term_fact", content="事实1",
        )

        svc = MemoryService(db)
        summaries = svc.list_memories(
            tenant_id=tenant.id, agent_id=agent.id, memory_type="short_term_summary",
        )
        assert len(summaries) == 1
        assert summaries[0].content == "摘要1"

        facts = svc.list_memories(
            tenant_id=tenant.id, agent_id=agent.id, memory_type="long_term_fact",
        )
        assert len(facts) == 1
        assert facts[0].content == "事实1"

    def test_list_memories_other_agent_not_included(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent_a = _create_agent(db, tenant.id, name="AgentA")
        agent_b = _create_agent(db, tenant.id, name="AgentB")
        repo = MemoryRepository(db)

        repo.create(
            tenant_id=tenant.id, agent_id=agent_a.id, conversation_id=1,
            memory_type="short_term_summary", content="AgentA的记忆",
        )
        repo.create(
            tenant_id=tenant.id, agent_id=agent_b.id, conversation_id=1,
            memory_type="short_term_summary", content="AgentB的记忆",
        )

        svc = MemoryService(db)
        memories = svc.list_memories(tenant_id=tenant.id, agent_id=agent_a.id)
        assert len(memories) == 1
        assert memories[0].content == "AgentA的记忆"


class TestDeleteMemory:
    def test_delete_memory_success(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        repo = MemoryRepository(db)
        memory = repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="待删除",
        )

        svc = MemoryService(db)
        svc.delete_memory(tenant_id=tenant.id, memory_id=memory.id)

        # Verify it's gone
        assert repo.get_by_id(memory.id) is None

    def test_delete_memory_not_found(self, db: Session) -> None:
        tenant = _create_tenant(db)
        svc = MemoryService(db)

        with pytest.raises(ValidationException, match="记忆不存在"):
            svc.delete_memory(tenant_id=tenant.id, memory_id=9999)

    def test_delete_memory_wrong_tenant(self, db: Session) -> None:
        tenant_a = _create_tenant(db)
        # Use a different tenant_id for the call
        tenant_b_id = 9999

        agent = _create_agent(db, tenant_a.id)
        repo = MemoryRepository(db)
        memory = repo.create(
            tenant_id=tenant_a.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="无权删除",
        )

        svc = MemoryService(db)
        with pytest.raises(ValidationException, match="无权操作"):
            svc.delete_memory(tenant_id=tenant_b_id, memory_id=memory.id)

    def test_delete_memory_agent_does_not_exist(self, db: Session) -> None:
        tenant = _create_tenant(db)
        repo = MemoryRepository(db)
        # Create a memory referencing a non-existent agent
        memory = repo.create(
            tenant_id=tenant.id, agent_id=9999, conversation_id=1,
            memory_type="short_term_summary", content="孤儿记忆",
        )

        svc = MemoryService(db)
        with pytest.raises(ValidationException, match="无权操作"):
            svc.delete_memory(tenant_id=tenant.id, memory_id=memory.id)


class TestClearAgentMemories:
    def test_clear_agent_memories_success(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        repo = MemoryRepository(db)

        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="摘要1",
        )
        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=2,
            memory_type="long_term_fact", content="事实1",
        )

        svc = MemoryService(db)
        svc.clear_agent_memories(tenant_id=tenant.id, agent_id=agent.id)

        remaining = repo.list_by_agent(agent_id=agent.id)
        assert len(remaining) == 0

    def test_clear_agent_memories_wrong_tenant(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent = _create_agent(db, tenant.id)
        repo = MemoryRepository(db)
        repo.create(
            tenant_id=tenant.id, agent_id=agent.id, conversation_id=1,
            memory_type="short_term_summary", content="摘要1",
        )

        svc = MemoryService(db)
        with pytest.raises(ValidationException, match="无权操作"):
            svc.clear_agent_memories(tenant_id=9999, agent_id=agent.id)

    def test_clear_agent_memories_does_not_affect_other_agents(self, db: Session) -> None:
        tenant = _create_tenant(db)
        agent_a = _create_agent(db, tenant.id, name="AgentA")
        agent_b = _create_agent(db, tenant.id, name="AgentB")
        repo = MemoryRepository(db)

        repo.create(
            tenant_id=tenant.id, agent_id=agent_a.id, conversation_id=1,
            memory_type="short_term_summary", content="AgentA的记忆",
        )
        repo.create(
            tenant_id=tenant.id, agent_id=agent_b.id, conversation_id=1,
            memory_type="short_term_summary", content="AgentB的记忆",
        )

        svc = MemoryService(db)
        svc.clear_agent_memories(tenant_id=tenant.id, agent_id=agent_a.id)

        agent_a_memories = repo.list_by_agent(agent_id=agent_a.id)
        assert len(agent_a_memories) == 0

        agent_b_memories = repo.list_by_agent(agent_id=agent_b.id)
        assert len(agent_b_memories) == 1
        assert agent_b_memories[0].content == "AgentB的记忆"
