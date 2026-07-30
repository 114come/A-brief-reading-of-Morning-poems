import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NodeDefinition(BaseModel):
    id: str
    type: str
    label: str
    position: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeDefinition(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    definition: dict[str, Any] = Field(
        default_factory=lambda: {"nodes": [], "edges": []}
    )


class WorkflowUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    definition: dict[str, Any] | None = None
    is_active: bool | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    description: str | None
    definition: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        """Parse JSON string fields from DB storage into Python objects.

        Handles definition (str->dict).
        """
        if isinstance(data, dict):
            definition_val = data.get("definition")
        else:
            definition_val = (
                getattr(data, "definition", None)
                if hasattr(data, "definition")
                else None
            )

        if isinstance(definition_val, str):
            try:
                parsed = json.loads(definition_val)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(data, dict):
                data["definition"] = parsed
            else:
                data.definition = parsed

        return data


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    status: str
    context: dict[str, Any]
    current_node_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        """Parse JSON string fields from DB storage into Python objects.

        Handles context (str->dict).
        """
        if isinstance(data, dict):
            context_val = data.get("context")
        else:
            context_val = (
                getattr(data, "context", None)
                if hasattr(data, "context")
                else None
            )

        if isinstance(context_val, str):
            try:
                parsed = json.loads(context_val)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(data, dict):
                data["context"] = parsed
            else:
                data.context = parsed

        return data


class WorkflowRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ApproveRequest(BaseModel):
    approved: bool
    comment: str | None = None
