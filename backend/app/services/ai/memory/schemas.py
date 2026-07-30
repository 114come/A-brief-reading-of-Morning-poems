import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryResponse(BaseModel):
    """Schema for agent memory records returned from the API.

    The ``metadata`` field accepts a JSON string (from the DB column stored as
    ``metadata_`` on the ORM model) or an already-parsed ``dict``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    conversation_id: int | None = None
    memory_type: str
    content: str
    metadata: dict[str, Any] | None = Field(default=None)
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_metadata_json(cls, data: Any) -> Any:
        """Parse metadata (str -> dict) from a DB JSON string.

        Handles both plain dict input (with ``metadata`` or ``metadata_`` keys)
        and ORM model instances where the column is exposed via the
        ``metadata_`` Python attribute (SQLAlchemy uses ``metadata_`` to avoid
        clashing with ``declarative_base().metadata``).
        """
        if isinstance(data, dict):
            raw = data.get("metadata") or data.get("metadata_")
            if isinstance(raw, str):
                try:
                    data["metadata"] = json.loads(raw)
                except json.JSONDecodeError:
                    data["metadata"] = None
            return data

        # ORM-like object — convert to a flat dict so Pydantic can extract
        # fields by name without ambiguity around ``metadata_``.
        if hasattr(data, "metadata_"):
            raw = getattr(data, "metadata_", None)
            if raw is not None:
                if isinstance(raw, str):
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        parsed = None
                else:
                    parsed = raw
                return {
                    "id": data.id,
                    "agent_id": data.agent_id,
                    "conversation_id": data.conversation_id,
                    "memory_type": data.memory_type,
                    "content": data.content,
                    "metadata": parsed,
                    "created_at": data.created_at,
                }
        return data
