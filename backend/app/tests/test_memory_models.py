from app.services.ai.memory.models import AgentMemory


def test_agent_memory_model_attributes() -> None:
    """Verify all AgentMemory fields exist."""
    assert AgentMemory.__tablename__ == "agent_memories"
    columns = {c.name for c in AgentMemory.__table__.columns}
    expected = {
        "id",
        "tenant_id",
        "agent_id",
        "conversation_id",
        "memory_type",
        "content",
        "metadata",
        "created_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"


def test_agent_memory_defaults() -> None:
    """Verify default values for AgentMemory fields."""
    # Nullable fields should have no default
    assert AgentMemory.__table__.columns["conversation_id"].nullable is True
    assert AgentMemory.__table__.columns["metadata"].nullable is True
    # NOT NULL fields
    assert AgentMemory.__table__.columns["tenant_id"].nullable is False
    assert AgentMemory.__table__.columns["agent_id"].nullable is False
    assert AgentMemory.__table__.columns["memory_type"].nullable is False
    assert AgentMemory.__table__.columns["content"].nullable is False
    assert AgentMemory.__table__.columns["created_at"].nullable is False
    # Indexed fields
    assert AgentMemory.__table__.columns["tenant_id"].index is True
    assert AgentMemory.__table__.columns["agent_id"].index is True
    assert AgentMemory.__table__.columns["conversation_id"].index is True
