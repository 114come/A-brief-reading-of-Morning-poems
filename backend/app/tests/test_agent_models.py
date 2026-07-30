from app.services.ai.agent_engine.models import Agent, AgentConversation


def test_agent_model_attributes() -> None:
    """Verify all Agent fields exist."""
    assert Agent.__tablename__ == "agents"
    columns = {c.name for c in Agent.__table__.columns}
    expected = {
        "id",
        "tenant_id",
        "name",
        "description",
        "system_prompt",
        "model_config",
        "tools_config",
        "max_iterations",
        "is_active",
        "memory_config",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"


def test_agent_conversation_model_attributes() -> None:
    """Verify all AgentConversation fields exist."""
    assert AgentConversation.__tablename__ == "agent_conversations"
    columns = {c.name for c in AgentConversation.__table__.columns}
    expected = {
        "id",
        "agent_id",
        "tenant_id",
        "user_id",
        "title",
        "status",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"


def test_agent_defaults() -> None:
    """Verify default values for Agent fields."""
    assert Agent.__table__.columns["max_iterations"].default.arg == 10
    assert Agent.__table__.columns["is_active"].default.arg is True
    assert Agent.__table__.columns["model_config"].default.arg == "{}"
    assert Agent.__table__.columns["tools_config"].default.arg == "[]"
    assert Agent.__table__.columns["memory_config"].default.arg == "{}"


def test_agent_conversation_defaults() -> None:
    """Verify default values for AgentConversation fields."""
    assert AgentConversation.__table__.columns["status"].default.arg == "active"
