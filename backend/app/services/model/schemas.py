from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataFieldCreate(BaseModel):
    name: str = Field(..., max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    label: str = Field(..., max_length=200)
    field_type: str = Field(..., pattern=r"^(string|text|number|integer|boolean|date|datetime|file|json)$")
    constraints: dict[str, Any] | None = None
    sort_order: int = 0


class DataFieldResponse(DataFieldCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    db_column_type: str
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def parse_constraints(cls, data: Any) -> Any:
        """当 constraints 是 JSON 字符串时（从数据库读取），自动解析为 dict"""
        if isinstance(data, dict):
            constraints = data.get("constraints")
        else:
            constraints = getattr(data, "constraints", None) if hasattr(data, "constraints") else None

        if isinstance(constraints, str):
            import json
            try:
                parsed = json.loads(constraints)
                if isinstance(data, dict):
                    data["constraints"] = parsed
                else:
                    data.constraints = parsed
            except json.JSONDecodeError:
                pass  # 保持原样，让 Pydantic 验证失败

        return data


class DataModelCreate(BaseModel):
    name: str = Field(..., max_length=100)
    table_name: str = Field(..., max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    description: str | None = None
    fields: list[DataFieldCreate]


class DataModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    name: str
    table_name: str
    description: str | None
    status: str
    fields: list[DataFieldResponse]
    created_at: datetime


class DataModelPublish(BaseModel):
    model_id: int
