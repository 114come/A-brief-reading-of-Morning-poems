from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.ai.agent_engine.models import Agent, AgentConversation
from app.services.ai.agent_engine.repository import (
    AgentRepository,
    ConversationRepository,
)
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
        name="测试租户",
        code="test_agent",
        db_name="tenant_agent_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def test_create_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = AgentRepository(db)
    agent = repo.create(
        tenant_id=tenant.id,
        name="测试助手",
        description="一个测试用 Agent",
        system_prompt="你是一个测试助手",
        model_config="{}",
        tools_config="[]",
        max_iterations=10,
        is_active=True,
    )
    assert agent.id is not None
    assert agent.name == "测试助手"
    assert agent.tenant_id == tenant.id
    assert agent.system_prompt == "你是一个测试助手"
    assert agent.max_iterations == 10
    assert agent.is_active is True


def test_list_agents_by_tenant(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = AgentRepository(db)
    repo.create(
        tenant_id=tenant.id,
        name="助手A",
        system_prompt="提示A",
    )
    repo.create(
        tenant_id=tenant.id,
        name="助手B",
        system_prompt="提示B",
    )

    agents = repo.list_by_tenant(tenant.id)
    assert len(agents) == 2
    names = [a.name for a in agents]
    assert "助手A" in names
    assert "助手B" in names


def test_update_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = AgentRepository(db)
    agent = repo.create(
        tenant_id=tenant.id,
        name="旧名称",
        system_prompt="旧提示",
    )
    updated = repo.update(agent.id, name="新名称", system_prompt="新提示")
    assert updated is not None
    assert updated.name == "新名称"
    assert updated.system_prompt == "新提示"

    # 验证持久化
    fetched = repo.get_by_id(agent.id)
    assert fetched is not None
    assert fetched.name == "新名称"


def test_delete_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = AgentRepository(db)
    agent = repo.create(
        tenant_id=tenant.id,
        name="待删除助手",
        system_prompt="再见",
    )
    result = repo.delete(agent.id)
    assert result is True

    fetched = repo.get_by_id(agent.id)
    assert fetched is None

    # 重复删除应返回 False
    assert repo.delete(agent.id) is False


def test_delete_agent_cascades_conversations(db: Session) -> None:
    tenant = _create_tenant(db)
    agent_repo = AgentRepository(db)
    conv_repo = ConversationRepository(db)

    agent = agent_repo.create(
        tenant_id=tenant.id,
        name="级联测试助手",
        system_prompt="测试",
    )
    conv1 = conv_repo.create(
        agent_id=agent.id,
        tenant_id=tenant.id,
        user_id=1,
        title="对话1",
    )
    conv2 = conv_repo.create(
        agent_id=agent.id,
        tenant_id=tenant.id,
        user_id=1,
        title="对话2",
    )

    # 删除 Agent
    agent_repo.delete(agent.id)

    # 验证对话也被级联删除
    convs = conv_repo.list_by_agent(agent.id)
    assert len(convs) == 0

    # 验证通过 get_by_id 也找不到
    assert conv_repo.get_by_id(conv1.id) is None
    assert conv_repo.get_by_id(conv2.id) is None


def test_create_conversation(db: Session) -> None:
    tenant = _create_tenant(db)
    agent_repo = AgentRepository(db)
    agent = agent_repo.create(
        tenant_id=tenant.id,
        name="对话测试助手",
        system_prompt="测试",
    )
    conv_repo = ConversationRepository(db)
    conv = conv_repo.create(
        agent_id=agent.id,
        tenant_id=tenant.id,
        user_id=42,
        title="我的对话",
        status="active",
    )
    assert conv.id is not None
    assert conv.agent_id == agent.id
    assert conv.user_id == 42
    assert conv.title == "我的对话"
    assert conv.status == "active"


def test_list_conversations_by_agent(db: Session) -> None:
    tenant = _create_tenant(db)
    agent_repo = AgentRepository(db)
    agent = agent_repo.create(
        tenant_id=tenant.id,
        name="列表测试助手",
        system_prompt="测试",
    )
    conv_repo = ConversationRepository(db)
    conv_repo.create(
        agent_id=agent.id, tenant_id=tenant.id, user_id=1, title="对话A"
    )
    conv_repo.create(
        agent_id=agent.id, tenant_id=tenant.id, user_id=2, title="对话B"
    )

    convs = conv_repo.list_by_agent(agent.id)
    assert len(convs) == 2
    titles = [c.title for c in convs]
    assert "对话A" in titles
    assert "对话B" in titles


def test_update_conversation(db: Session) -> None:
    tenant = _create_tenant(db)
    agent_repo = AgentRepository(db)
    agent = agent_repo.create(
        tenant_id=tenant.id,
        name="更新对话助手",
        system_prompt="测试",
    )
    conv_repo = ConversationRepository(db)
    conv = conv_repo.create(
        agent_id=agent.id,
        tenant_id=tenant.id,
        user_id=1,
        title="原始标题",
        status="active",
    )
    updated = conv_repo.update(conv.id, title="新标题", status="archived")
    assert updated is not None
    assert updated.title == "新标题"
    assert updated.status == "archived"

    # 验证持久化
    fetched = conv_repo.get_by_id(conv.id)
    assert fetched is not None
    assert fetched.title == "新标题"
