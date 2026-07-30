import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=100)
    description: str | None = None
    system_prompt: str = Field(..., min_length=1)
    config: dict[str, Any] = Field(
        default_factory=lambda: {"model": "gpt-4", "temperature": 0.7},
        alias="model_config",
    )
    tools_config: list[str] = Field(
        default_factory=lambda: ["llm", "knowledge_base"]
    )
    max_iterations: int = Field(default=10, ge=1, le=100)
    memory_config: dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "short_term_interval": 5,
            "long_term_enabled": True,
        }
    )


class AgentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    system_prompt: str | None = None
    config: dict[str, Any] | None = Field(None, alias="model_config")
    tools_config: list[str] | None = None
    max_iterations: int | None = Field(None, ge=1, le=100)
    is_active: bool | None = None
    memory_config: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    tenant_id: int
    name: str
    description: str | None
    system_prompt: str
    config: dict[str, Any] = Field(alias="model_config")
    tools_config: list[str]
    memory_config: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        """Parse JSON string fields from DB storage into Python objects.

        Handles model_config (str->dict), tools_config (str->list), and
        memory_config (str->dict).
        """
        if isinstance(data, dict):
            model_config_val = data.get("model_config") or data.get("config")
            tools_config_val = data.get("tools_config")
            memory_config_val = data.get("memory_config")
        else:
            model_config_val = (
                getattr(data, "model_config", None)
                if hasattr(data, "model_config")
                else None
            )
            tools_config_val = (
                getattr(data, "tools_config", None)
                if hasattr(data, "tools_config")
                else None
            )
            memory_config_val = (
                getattr(data, "memory_config", None)
                if hasattr(data, "memory_config")
                else None
            )

        if isinstance(model_config_val, str):
            try:
                parsed = json.loads(model_config_val)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(data, dict):
                data["model_config"] = parsed
            else:
                data.model_config = parsed

        if isinstance(tools_config_val, str):
            try:
                parsed = json.loads(tools_config_val)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(data, dict):
                data["tools_config"] = parsed
            else:
                data.tools_config = parsed

        if isinstance(memory_config_val, str):
            try:
                parsed = json.loads(memory_config_val)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(data, dict):
                data["memory_config"] = parsed
            else:
                data.memory_config = parsed

        return data


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    tenant_id: int
    title: str | None = None
    status: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    stream: bool = True
