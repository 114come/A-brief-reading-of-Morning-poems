"""Tests for the agent engine API routes."""

import json
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_master_db

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mock_tenant_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock tenant database creation to avoid MySQL dependency in tests."""

    def mock_create_tenant_database(tenant: object) -> None:
        pass

    monkeypatch.setattr(
        "app.services.tenant.service.create_tenant_database",
        mock_create_tenant_database,
    )


from app.main import app  # noqa: E402

app.dependency_overrides[get_master_db] = override_get_db
client = TestClient(app)


def _create_tenant_and_login(code: str) -> tuple[int, str]:
    """Create a tenant and return (tenant_id, access_token)."""
    payload = {
        "name": f"Agent Test {code}",
        "code": code,
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": f"admin@{code}.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200, f"Create tenant failed: {response.text}"
    tenant_id = response.json()["data"]["tenant"]["id"]

    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post(
        f"/api/v1/tenant/auth/login_with_tenant?tenant_code={code}",
        json=login_payload,
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["data"]["access_token"]
    return tenant_id, token


def _create_agent(token: str) -> int:
    """Create a test agent and return its ID."""
    payload = {
        "name": "测试助手",
        "description": "一个测试用 Agent",
        "system_prompt": "你是一个测试助手",
        "model_config": {"model": "gpt-4", "temperature": 0.7},
        "tools_config": ["llm", "knowledge_base"],
        "max_iterations": 10,
    }
    response = client.post(
        "/api/v1/agents",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"Create agent failed: {response.text}"
    data = response.json()
    assert data["code"] == 0, f"Expected code 0, got {data}"
    return data["data"]["id"]


# ── Agent CRUD Tests ──────────────────────────────────────


def test_create_agent() -> None:
    """Test creating an agent via API."""
    _, token = _create_tenant_and_login("create_agent")
    agent_id = _create_agent(token)
    assert agent_id > 0


def test_list_agents() -> None:
    """Test listing agents for the tenant."""
    _, token = _create_tenant_and_login("list_agents")
    _create_agent(token)
    _create_agent(token)

    response = client.get(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]) >= 2


def test_get_agent() -> None:
    """Test getting a single agent by ID."""
    _, token = _create_tenant_and_login("get_agent")
    agent_id = _create_agent(token)

    response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试助手"
    # model_config is the alias for the config field
    assert data["data"]["model_config"]["model"] == "gpt-4"
    assert data["data"]["system_prompt"] == "你是一个测试助手"


def test_get_agent_not_found() -> None:
    """Test getting a non-existent agent returns error."""
    _, token = _create_tenant_and_login("get_agent_nf")

    response = client.get(
        "/api/v1/agents/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 422000
    assert "不存在" in data["message"]


def test_update_agent() -> None:
    """Test updating an agent."""
    _, token = _create_tenant_and_login("update_agent")
    agent_id = _create_agent(token)

    payload = {
        "name": "更新助手",
        "system_prompt": "新提示",
    }
    response = client.put(
        f"/api/v1/agents/{agent_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "更新助手"
    assert data["data"]["system_prompt"] == "新提示"


def test_delete_agent() -> None:
    """Test deleting an agent."""
    _, token = _create_tenant_and_login("delete_agent")
    agent_id = _create_agent(token)

    with patch("app.services.ai.agent_engine.service.SessionMemory"):
        response = client.delete(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "Agent 已删除"

    # Verify it's gone
    response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["code"] == 422000


# ── Conversation Tests ────────────────────────────────────


def test_create_conversation() -> None:
    """Test creating a conversation for an agent."""
    _, token = _create_tenant_and_login("create_conv")
    agent_id = _create_agent(token)

    response = client.post(
        f"/api/v1/agents/{agent_id}/conversations",
        json={"title": "测试对话"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["title"] == "测试对话"
    assert data["data"]["agent_id"] == agent_id
    assert data["data"]["status"] == "active"


@patch("app.services.ai.agent_engine.session_memory.SessionMemory")
def test_list_conversations(mock_session_memory: patch) -> None:
    """Test listing conversations with message_count from Redis mock."""
    # Mock Redis session memory to return 1 message
    mock_mem = mock_session_memory.return_value
    mock_mem.get_history.return_value = [{"role": "user", "content": "hi"}]

    _, token = _create_tenant_and_login("list_conv")
    agent_id = _create_agent(token)

    # Create a conversation first
    response = client.post(
        f"/api/v1/agents/{agent_id}/conversations",
        json={"title": "对话1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    # List conversations
    response = client.get(
        f"/api/v1/agents/{agent_id}/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]) >= 1
    # message_count comes from mocked Redis
    assert data["data"][0]["message_count"] == 1


@patch("app.services.ai.agent_engine.service.SessionMemory")
def test_get_conversation_history(mock_session_memory: patch) -> None:
    """Test getting conversation history (messages from Redis)."""
    mock_mem = mock_session_memory.return_value
    mock_mem.get_history.return_value = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
    ]

    _, token = _create_tenant_and_login("get_conv_hist")
    agent_id = _create_agent(token)

    # Create a conversation
    response = client.post(
        f"/api/v1/agents/{agent_id}/conversations",
        json={"title": "历史对话"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conv_id = response.json()["data"]["id"]

    # Get history
    response = client.get(
        f"/api/v1/agents/{agent_id}/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["messages"]) == 2
    assert data["data"]["messages"][0]["role"] == "user"
    assert data["data"]["messages"][1]["role"] == "assistant"


@patch("app.services.ai.agent_engine.service.SessionMemory")
def test_delete_conversation(mock_session_memory: patch) -> None:
    """Test deleting a conversation."""
    mock_mem = mock_session_memory.return_value
    mock_mem.clear.return_value = None

    _, token = _create_tenant_and_login("delete_conv")
    agent_id = _create_agent(token)

    # Create a conversation
    response = client.post(
        f"/api/v1/agents/{agent_id}/conversations",
        json={"title": "待删除会话"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conv_id = response.json()["data"]["id"]

    # Delete it
    response = client.delete(
        f"/api/v1/agents/{agent_id}/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "会话已删除"


# ── Chat SSE Test ─────────────────────────────────────────


def test_chat_returns_sse() -> None:
    """Test chat endpoint returns SSE events."""
    _, token = _create_tenant_and_login("chat_test")
    agent_id = _create_agent(token)

    # Create a conversation
    response = client.post(
        f"/api/v1/agents/{agent_id}/conversations",
        json={"title": "聊天会话"},
        headers={"Authorization": f"Bearer {token}"},
    )
    conv_id = response.json()["data"]["id"]

    # Mock AgentService.chat_stream to yield test events
    async def mock_chat_stream(  # type: ignore[misc]
        self: object,
        *args: object,
        **kwargs: object,
    ) -> object:
        yield {"event": "message", "data": {"content": "Hello, world!"}}
        yield {"event": "done", "data": {}}

    with patch(
        "app.services.ai.agent_engine.service.AgentService.chat_stream",
        mock_chat_stream,
    ):
        response = client.post(
            f"/api/v1/agents/{agent_id}/conversations/{conv_id}/chat",
            json={"message": "Hi"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    content = response.text
    assert "event: message" in content, f"SSE content missing event: message\n{content}"
    assert "Hello, world!" in content, f"SSE content missing Hello message\n{content}"
    assert "event: done" in content, f"SSE content missing event: done\n{content}"


# ── Memory Management Tests ───────────────────────────────


def test_list_memories_empty() -> None:
    """Test listing memories for an agent returns empty list initially."""
    _, token = _create_tenant_and_login("list_memories")
    agent_id = _create_agent(token)

    response = client.get(
        f"/api/v1/agents/{agent_id}/memories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"] == []


def test_delete_memory() -> None:
    """Test deleting a single memory by ID after creating it."""
    tenant_id, token = _create_tenant_and_login("del_memory")
    agent_id = _create_agent(token)

    # Directly insert a memory record via the test session so the API can delete it
    from app.services.ai.memory.repository import MemoryRepository

    db = TestSessionLocal()
    try:
        Base.metadata.create_all(bind=TEST_ENGINE)
        repo = MemoryRepository(db)
        mem = repo.create(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memory_type="test",
            content="test memory",
        )
        memory_id = mem.id
    finally:
        db.close()

    response = client.delete(
        f"/api/v1/agents/{agent_id}/memories/{memory_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "记忆已删除"


def test_clear_memories() -> None:
    """Test clearing all memories for an agent."""
    _, token = _create_tenant_and_login("clear_memories")
    agent_id = _create_agent(token)

    # Clear memories (should be a no-op on empty, no error)
    response = client.delete(
        f"/api/v1/agents/{agent_id}/memories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "记忆已清空"

    # Verify the list is still empty
    response = client.get(
        f"/api/v1/agents/{agent_id}/memories",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = response.json()
    assert data["code"] == 0
    assert data["data"] == []
