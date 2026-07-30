"""Tests for memory schemas and agent schema memory_config extension."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.services.ai.memory.schemas import MemoryResponse
from app.services.ai.agent_engine.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
)


# ---------------------------------------------------------------------------
# MemoryResponse
# ---------------------------------------------------------------------------


class TestMemoryResponse:
    def test_has_all_fields_and_defaults(self):
        """memory_response_defaults: verify default conversation_id and metadata."""
        now = datetime.now()
        mem = MemoryResponse(
            id=1,
            agent_id=1,
            memory_type="short_term",
            content="Test memory content",
            created_at=now,
        )
        assert mem.id == 1
        assert mem.agent_id == 1
        assert mem.conversation_id is None
        assert mem.memory_type == "short_term"
        assert mem.content == "Test memory content"
        assert mem.metadata is None
        assert mem.created_at == now

    def test_metadata_as_dict(self):
        """memory_response_metadata_dict: accept already-parsed metadata."""
        now = datetime.now()
        mem = MemoryResponse(
            id=1,
            agent_id=1,
            memory_type="long_term",
            content="Important fact",
            metadata={"key": "value", "score": 0.95},
            created_at=now,
        )
        assert mem.metadata == {"key": "value", "score": 0.95}

    def test_conversation_id(self):
        """memory_response_conversation_id: optional conversation_id."""
        now = datetime.now()
        mem = MemoryResponse(
            id=1,
            agent_id=1,
            conversation_id=42,
            memory_type="short_term",
            content="Contextual memory",
            created_at=now,
        )
        assert mem.conversation_id == 42

    def test_parses_metadata_from_json_string(self):
        """memory_response_parse_json: str->dict via model_validate."""
        now = datetime.now()
        data = {
            "id": 1,
            "agent_id": 1,
            "memory_type": "short_term",
            "content": "Parsed memory",
            "metadata": '{"key": "value", "score": 0.95}',
            "created_at": now,
        }
        mem = MemoryResponse.model_validate(data)
        assert isinstance(mem.metadata, dict)
        assert mem.metadata["key"] == "value"
        assert mem.metadata["score"] == 0.95

    def test_handles_invalid_metadata_json(self):
        """memory_response_invalid_json: returns None for bad JSON."""
        now = datetime.now()
        data = {
            "id": 1,
            "agent_id": 1,
            "memory_type": "short_term",
            "content": "Bad metadata",
            "metadata": "not valid json",
            "created_at": now,
        }
        mem = MemoryResponse.model_validate(data)
        assert mem.metadata is None

    def test_already_parsed_dict_passthrough(self):
        """memory_response_already_parsed: dict input passes through unchanged."""
        now = datetime.now()
        data = {
            "id": 1,
            "agent_id": 1,
            "memory_type": "short_term",
            "content": "Dict metadata",
            "metadata": {"key": "value"},
            "created_at": now,
        }
        mem = MemoryResponse.model_validate(data)
        assert mem.metadata == {"key": "value"}

    def test_metadata_none_passthrough(self):
        """memory_response_none_metadata: None metadata stays None."""
        now = datetime.now()
        data = {
            "id": 1,
            "agent_id": 1,
            "memory_type": "short_term",
            "content": "No metadata",
            "metadata": None,
            "created_at": now,
        }
        mem = MemoryResponse.model_validate(data)
        assert mem.metadata is None


# ---------------------------------------------------------------------------
# AgentCreate — memory_config
# ---------------------------------------------------------------------------


class TestAgentCreateMemoryConfig:
    def test_default(self):
        """agent_create_memory_config_default: verify factory defaults."""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="You are helpful",
        )
        assert agent.memory_config == {
            "enabled": True,
            "short_term_interval": 5,
            "long_term_enabled": True,
        }

    def test_override(self):
        """agent_create_memory_config_override: custom memory_config."""
        agent = AgentCreate(
            name="Custom Agent",
            system_prompt="Be concise",
            memory_config={"enabled": False, "short_term_interval": 10},
        )
        assert agent.memory_config["enabled"] is False
        assert agent.memory_config["short_term_interval"] == 10

    def test_empty_dict(self):
        """agent_create_memory_config_empty: accepts empty dict."""
        agent = AgentCreate(
            name="Empty Config",
            system_prompt="Hello",
            memory_config={},
        )
        assert agent.memory_config == {}


# ---------------------------------------------------------------------------
# AgentUpdate — memory_config
# ---------------------------------------------------------------------------


class TestAgentUpdateMemoryConfig:
    def test_default_is_none(self):
        """agent_update_memory_config_none: defaults to None."""
        update = AgentUpdate()
        assert update.memory_config is None

    def test_set(self):
        """agent_update_memory_config_set: accepts custom config."""
        update = AgentUpdate(memory_config={"enabled": False})
        assert update.memory_config == {"enabled": False}

    def test_null_explicitly(self):
        """agent_update_memory_config_explicit_none: explicit None is valid."""
        update = AgentUpdate(memory_config=None)
        assert update.memory_config is None


# ---------------------------------------------------------------------------
# AgentResponse — memory_config parsing
# ---------------------------------------------------------------------------


class TestAgentResponseMemoryConfig:
    NOW = datetime.now()

    def _make_data(self, **overrides: object) -> dict:
        base = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Agent",
            "description": None,
            "system_prompt": "You are helpful",
            "model_config": '{"model": "gpt-4"}',
            "tools_config": '["llm"]',
            "memory_config": '{"enabled": true, "short_term_interval": 5}',
            "max_iterations": 10,
            "is_active": True,
            "created_at": self.NOW,
            "updated_at": self.NOW,
        }
        base.update(overrides)
        return base

    def test_parses_json_string(self):
        """agent_response_memory_config_parse: str->dict parsing."""
        data = self._make_data()
        response = AgentResponse.model_validate(data)
        assert isinstance(response.memory_config, dict)
        assert response.memory_config["enabled"] is True
        assert response.memory_config["short_term_interval"] == 5

    def test_handles_already_parsed_dict(self):
        """agent_response_memory_config_dict: already-parsed dict passes through."""
        data = self._make_data(
            memory_config={"enabled": False, "long_term_enabled": True},
        )
        response = AgentResponse.model_validate(data)
        assert response.memory_config == {
            "enabled": False,
            "long_term_enabled": True,
        }

    def test_handles_invalid_json(self):
        """agent_response_memory_config_invalid: falls back to {}."""
        data = self._make_data(memory_config="not json")
        response = AgentResponse.model_validate(data)
        assert isinstance(response.memory_config, dict)
        assert response.memory_config == {}

    def test_handles_none(self):
        """agent_response_memory_config_none: None raises ValidationError."""
        data = self._make_data(memory_config=None)
        with pytest.raises(ValidationError) as exc:
            AgentResponse.model_validate(data)
        assert "memory_config" in str(exc.value)

    def test_omitted_field_defaults(self):
        """agent_response_memory_config_omitted: defaults to {} for backwards compat."""
        data = self._make_data()
        data.pop("memory_config")
        response = AgentResponse.model_validate(data)
        assert isinstance(response.memory_config, dict)
        assert response.memory_config == {}
