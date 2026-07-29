from datetime import datetime

import pytest
from pydantic import ValidationError

from app.services.ai.agent_engine.schemas import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    ConversationCreate,
    ConversationResponse,
    ChatRequest,
)


class TestAgentCreate:
    def test_defaults(self):
        """test_agent_create_defaults: verify defaults"""
        agent = AgentCreate(
            name="Test Agent",
            system_prompt="You are a helpful assistant",
        )
        assert agent.name == "Test Agent"
        assert agent.description is None
        assert agent.system_prompt == "You are a helpful assistant"
        assert agent.config == {"model": "gpt-4", "temperature": 0.7}
        assert agent.tools_config == ["llm", "knowledge_base"]
        assert agent.max_iterations == 10

    def test_overrides_defaults(self):
        agent = AgentCreate(
            name="Custom Agent",
            system_prompt="Be concise",
            config={"model": "claude-3", "temperature": 0.5},
            tools_config=["llm"],
            max_iterations=20,
        )
        assert agent.config == {"model": "claude-3", "temperature": 0.5}
        assert agent.tools_config == ["llm"]
        assert agent.max_iterations == 20

    def test_validates_name_max_length(self):
        with pytest.raises(ValidationError):
            AgentCreate(
                name="x" * 101,
                system_prompt="You are helpful",
            )

    def test_validates_system_prompt_min_length(self):
        with pytest.raises(ValidationError):
            AgentCreate(
                name="Test Agent",
                system_prompt="",
            )

    def test_validates_max_iterations_range(self):
        with pytest.raises(ValidationError):
            AgentCreate(
                name="Test Agent",
                system_prompt="You are helpful",
                max_iterations=0,
            )
        with pytest.raises(ValidationError):
            AgentCreate(
                name="Test Agent",
                system_prompt="You are helpful",
                max_iterations=101,
            )


class TestAgentUpdate:
    def test_all_optional(self):
        """test_agent_update_all_optional: verify all fields optional"""
        update = AgentUpdate()
        assert update.name is None
        assert update.description is None
        assert update.system_prompt is None
        assert update.config is None
        assert update.tools_config is None
        assert update.max_iterations is None
        assert update.is_active is None

    def test_partial_update(self):
        update = AgentUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None

    def test_validates_name_length(self):
        with pytest.raises(ValidationError):
            AgentUpdate(name="x" * 101)

    def test_validates_max_iterations_range(self):
        with pytest.raises(ValidationError):
            AgentUpdate(max_iterations=0)
        with pytest.raises(ValidationError):
            AgentUpdate(max_iterations=101)


class TestAgentResponse:
    def test_parses_json_fields(self):
        """test_agent_response_parses_json_fields: str->dict/list parsing"""
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Agent",
            "description": "A test agent",
            "system_prompt": "You are helpful",
            "model_config": '{"model": "gpt-4", "temperature": 0.7}',
            "tools_config": '["llm", "knowledge_base"]',
            "max_iterations": 10,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = AgentResponse.model_validate(data)
        assert isinstance(response.config, dict)
        assert response.config["model"] == "gpt-4"
        assert isinstance(response.tools_config, list)
        assert "llm" in response.tools_config

    def test_handles_invalid_json(self):
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Agent",
            "description": None,
            "system_prompt": "You are helpful",
            "model_config": "not valid json",
            "tools_config": "also not json",
            "max_iterations": 10,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = AgentResponse.model_validate(data)
        assert response.config == {}
        assert response.tools_config == []

    def test_handles_already_parsed(self):
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Agent",
            "description": None,
            "system_prompt": "You are helpful",
            "model_config": {"model": "claude"},
            "tools_config": ["llm"],
            "max_iterations": 10,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = AgentResponse.model_validate(data)
        assert response.config == {"model": "claude"}
        assert response.tools_config == ["llm"]


class TestConversationCreate:
    def test_optional_title(self):
        """test_conversation_create: optional title"""
        conv = ConversationCreate()
        assert conv.title is None
        conv = ConversationCreate(title="My Chat")
        assert conv.title == "My Chat"


class TestConversationResponse:
    def test_has_message_count_default(self):
        """test_conversation_response: has message_count default 0"""
        now = datetime.now()
        conv = ConversationResponse(
            id=1,
            agent_id=1,
            tenant_id=1,
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert conv.message_count == 0

    def test_with_title(self):
        now = datetime.now()
        conv = ConversationResponse(
            id=1,
            agent_id=1,
            tenant_id=1,
            title="My Conversation",
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert conv.title == "My Conversation"


class TestChatRequest:
    def test_basic_validation(self):
        """test_chat_request: basic validation"""
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.stream is True
        req = ChatRequest(message="Hello", stream=False)
        assert req.stream is False

    def test_empty_message_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long_raises(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 10001)
