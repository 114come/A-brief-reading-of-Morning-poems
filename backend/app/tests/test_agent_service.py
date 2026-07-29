from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.exceptions import ValidationException
from app.services.ai.agent_engine.schemas import AgentCreate, AgentUpdate
from app.services.ai.agent_engine.service import AgentService
from app.services.tenant.models import Tenant

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
        code="test_agent_svc",
        db_name="tenant_agent_svc_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _make_service(db: Session) -> AgentService:
    return AgentService(db=db)


def test_create_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    service = _make_service(db)

    data = AgentCreate(
        name="测试助手",
        description="一个测试用 Agent",
        system_prompt="你是一个测试助手",
        max_iterations=10,
    )
    agent = service.create_agent(tenant_id=tenant.id, data=data)

    assert agent.id is not None
    assert agent.name == "测试助手"
    assert agent.tenant_id == tenant.id
    assert agent.system_prompt == "你是一个测试助手"
    assert agent.max_iterations == 10
    assert agent.is_active is True


def test_update_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    service = _make_service(db)

    data = AgentCreate(name="旧名称", system_prompt="旧提示")
    agent = service.create_agent(tenant_id=tenant.id, data=data)

    update_data = AgentUpdate(
        name="新名称",
        system_prompt="新提示",
        max_iterations=20,
    )
    updated = service.update_agent(
        tenant_id=tenant.id, agent_id=agent.id, data=update_data
    )

    assert updated.name == "新名称"
    assert updated.system_prompt == "新提示"
    assert updated.max_iterations == 20

    # Verify persistence via fresh query
    fetched = service.get_agent(agent.id)
    assert fetched is not None
    assert fetched.name == "新名称"


def test_list_agents(db: Session) -> None:
    tenant = _create_tenant(db)
    service = _make_service(db)

    service.create_agent(
        tenant_id=tenant.id,
        data=AgentCreate(name="助手A", system_prompt="提示A"),
    )
    service.create_agent(
        tenant_id=tenant.id,
        data=AgentCreate(name="助手B", system_prompt="提示B"),
    )

    agents = service.list_agents(tenant_id=tenant.id)
    assert len(agents) == 2
    names = [a.name for a in agents]
    assert "助手A" in names
    assert "助手B" in names


def test_delete_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    service = _make_service(db)

    data = AgentCreate(name="待删除助手", system_prompt="再见")
    agent = service.create_agent(tenant_id=tenant.id, data=data)

    service.delete_agent(tenant_id=tenant.id, agent_id=agent.id)

    fetched = service.get_agent(agent.id)
    assert fetched is None


def test_create_conversation(db: Session) -> None:
    tenant = _create_tenant(db)
    service = _make_service(db)

    data = AgentCreate(name="对话测试助手", system_prompt="测试")
    agent = service.create_agent(tenant_id=tenant.id, data=data)

    conv = service.create_conversation(
        tenant_id=tenant.id,
        user_id=42,
        agent_id=agent.id,
        title="我的对话",
    )

    assert conv.id is not None
    assert conv.agent_id == agent.id
    assert conv.user_id == 42
    assert conv.title == "我的对话"


@patch("app.services.ai.agent_engine.service.SessionMemory")
def test_delete_agent_cleans_conversations(
    mock_session_memory: MagicMock, db: Session
) -> None:
    mock_mem_instance = MagicMock()
    mock_session_memory.return_value = mock_mem_instance

    tenant = _create_tenant(db)
    service = _make_service(db)

    agent = service.create_agent(
        tenant_id=tenant.id,
        data=AgentCreate(name="清理测试助手", system_prompt="测试"),
    )

    conv1 = service.create_conversation(
        tenant_id=tenant.id, user_id=1, agent_id=agent.id, title="对话1"
    )
    conv2 = service.create_conversation(
        tenant_id=tenant.id, user_id=2, agent_id=agent.id, title="对话2"
    )

    # Verify conversations exist before delete
    assert len(service.list_conversations(agent.id)) == 2

    service.delete_agent(tenant_id=tenant.id, agent_id=agent.id)

    # Agent should be gone
    assert service.get_agent(agent.id) is None

    # Conversations should be cascade-deleted from DB
    convs = service.list_conversations(agent.id)
    assert len(convs) == 0

    # SessionMemory.clear should have been called for each conversation
    assert mock_mem_instance.clear.call_count == 2
