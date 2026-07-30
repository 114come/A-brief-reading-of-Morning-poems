import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMProviderCreate(BaseModel):
    name: str = Field(..., max_length=100)
    provider_type: str = Field(
        ..., pattern=r"^(openai|claude|wenxin|qianwen|custom)$"
    )
    api_base: str | None = None
    api_key: str = Field(..., min_length=1, max_length=500)
    models: list[str] = Field(default_factory=list)
    priority: int = 0
    is_active: bool = True


class LLMProviderUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    provider_type: str | None = Field(
        None, pattern=r"^(openai|claude|wenxin|qianwen|custom)$"
    )
    api_base: str | None = None
    api_key: str | None = Field(None, min_length=1, max_length=500)
    models: list[str] | None = None
    priority: int | None = None
    is_active: bool | None = None


class LLMProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    provider_type: str
    api_base: str | None
    models: list[str] = Field(default_factory=list)
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_models(cls, data: Any) -> Any:
        """当 models 是 JSON 字符串时（从数据库读取），自动解析为 list"""
        if isinstance(data, dict):
            models_val = data.get("models")
        else:
            models_val = getattr(data, "models", None) if hasattr(data, "models") else None

        if isinstance(models_val, str):
            try:
                parsed = json.loads(models_val)
                if isinstance(data, dict):
                    data["models"] = parsed
                else:
                    data.models = parsed
            except json.JSONDecodeError:
                if isinstance(data, dict):
                    data["models"] = []
                else:
                    data.models = []

        return data


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., max_length=100)
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=128000)
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None
