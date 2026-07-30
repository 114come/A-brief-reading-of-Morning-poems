from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.ai.agent_engine.models import Agent
from app.services.ai.memory.models import AgentMemory
from app.services.ai.memory.repository import MemoryRepository
from app.services.tenant.models import Tenant

# 内存数据库用于测试
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
        name="内存租户",
        code="memory_test",
        db_name="tenant_memory_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def test_create_memory(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    memory = repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=10,
        memory_type="episodic",
        content="用户询问了天气情况",
        metadata='{"source": "chat"}',
    )

    assert memory.id is not None
    assert memory.tenant_id == tenant.id
    assert memory.agent_id == 1
    assert memory.conversation_id == 10
    assert memory.memory_type == "episodic"
    assert memory.content == "用户询问了天气情况"
    assert memory.metadata_ == '{"source": "chat"}'
    assert memory.created_at is not None


def test_list_by_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=10,
        memory_type="episodic",
        content="记忆A",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=11,
        memory_type="semantic",
        content="记忆B",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=2,
        conversation_id=12,
        memory_type="episodic",
        content="其他Agent的记忆",
    )

    # 只查询 agent_id=1 的，不限制 type
    memories = repo.list_by_agent(agent_id=1)
    assert len(memories) == 2
    contents = [m.content for m in memories]
    assert "记忆A" in contents
    assert "记忆B" in contents


def test_list_by_agent_with_type_filter(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=10,
        memory_type="episodic",
        content="情节记忆",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=11,
        memory_type="semantic",
        content="语义记忆",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=12,
        memory_type="episodic",
        content="另一个情节记忆",
    )

    episodic = repo.list_by_agent(agent_id=1, memory_type="episodic")
    assert len(episodic) == 2
    assert all(m.memory_type == "episodic" for m in episodic)

    semantic = repo.list_by_agent(agent_id=1, memory_type="semantic")
    assert len(semantic) == 1
    assert semantic[0].content == "语义记忆"


def test_list_by_agent_conv(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    # 同一个 agent 不同 conversation
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=100,
        memory_type="episodic",
        content="对话100的记忆1",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=100,
        memory_type="semantic",
        content="对话100的记忆2",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=200,
        memory_type="episodic",
        content="对话200的记忆",
    )

    # 按照 agent + conv 过滤
    memories = repo.list_by_agent_conv(agent_id=1, conv_id=100)
    assert len(memories) == 2
    contents = [m.content for m in memories]
    assert "对话100的记忆1" in contents
    assert "对话100的记忆2" in contents

    # 加上 type 过滤
    episodic = repo.list_by_agent_conv(
        agent_id=1, conv_id=100, memory_type="episodic"
    )
    assert len(episodic) == 1
    assert episodic[0].content == "对话100的记忆1"


def test_delete_memory(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    memory = repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=10,
        memory_type="episodic",
        content="待删除的记忆",
    )
    memory_id = memory.id

    # 删除存在的记录
    result = repo.delete(memory_id)
    assert result is True

    # 确认已删除
    fetched = repo.get_by_id(memory_id)
    assert fetched is None

    # 重复删除应返回 False
    assert repo.delete(memory_id) is False


def test_delete_by_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = MemoryRepository(db)

    # 为 agent 1 创建两条记忆
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=10,
        memory_type="episodic",
        content="记忆A",
    )
    repo.create(
        tenant_id=tenant.id,
        agent_id=1,
        conversation_id=11,
        memory_type="semantic",
        content="记忆B",
    )

    # 为 agent 2 创建一条记忆（不应被删除）
    repo.create(
        tenant_id=tenant.id,
        agent_id=2,
        conversation_id=20,
        memory_type="episodic",
        content="其他Agent的记忆",
    )

    # 删除 agent 1 的全部记忆
    repo.delete_by_agent(agent_id=1)

    # agent 1 的记忆应全部被删除
    agent1_memories = repo.list_by_agent(agent_id=1)
    assert len(agent1_memories) == 0

    # agent 2 的记忆应当保留
    agent2_memories = repo.list_by_agent(agent_id=2)
    assert len(agent2_memories) == 1
    assert agent2_memories[0].content == "其他Agent的记忆"
