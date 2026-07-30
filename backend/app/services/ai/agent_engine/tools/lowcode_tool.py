"""Lowcode CRUD tools for Agent.

Provides tools to query, insert, update, and delete records in lowcode
dynamic data tables. Each tool requires a SQLAlchemy Session and tenant_id
at instantiation (runtime dependency injection).
"""

from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.agent_engine.tools.base import BaseTool


class LowcodeQueryTool(BaseTool):
    """查询低代码动态表中的数据"""

    name = "query_data"
    description = "查询低代码平台中某个数据表的数据，支持按字段过滤。可用于查询业务数据。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "数据库表名（如 employee_onboarding）",
            },
            "filters": {
                "type": "object",
                "description": "过滤条件，如 {\"department\": \"技术部\"}",
                "default": {},
            },
            "limit": {
                "type": "integer",
                "description": "返回条数上限",
                "default": 20,
            },
        },
        "required": ["table_name"],
    }

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, **kwargs: Any) -> str:
        from app.services.model.generator import generate_sqlalchemy_model
        from app.services.model.repository import DataModelRepository

        table_name: str = kwargs.get("table_name", "")
        filters: dict | None = kwargs.get("filters") or {}
        limit: int = kwargs.get("limit", 20)

        repo = DataModelRepository(self.db)
        model_def = repo.get_by_table_name(table_name, self.tenant_id)
        if not model_def:
            return f"错误：数据表 '{table_name}' 不存在"

        DynamicModel = generate_sqlalchemy_model(model_def)
        q = self.db.query(DynamicModel)
        if filters:
            for key, value in filters.items():
                if hasattr(DynamicModel, key):
                    q = q.filter(getattr(DynamicModel, key) == value)
        items = q.limit(limit).all()

        if not items:
            return f"在 '{table_name}' 中未找到匹配的记录"

        lines = [f"找到 {len(items)} 条记录："]
        for item in items:
            parts = []
            for col in item.__table__.columns:
                val = getattr(item, col.name, None)
                if val is not None and col.name not in ("created_at", "updated_at"):
                    parts.append(f"{col.name}={val}")
            lines.append(f"  [{item.id}] " + ", ".join(parts))
        return "\n".join(lines)


class LowcodeInsertTool(BaseTool):
    """向低代码动态表中插入数据"""

    name = "insert_data"
    description = "向低代码平台的数据表中插入一条新记录"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "数据库表名",
            },
            "data": {
                "type": "object",
                "description": "要插入的数据，如 {\"name\": \"张三\", \"department\": \"技术部\"}",
            },
        },
        "required": ["table_name", "data"],
    }

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, **kwargs: Any) -> str:
        from app.services.model.generator import generate_sqlalchemy_model
        from app.services.model.repository import DataModelRepository

        table_name: str = kwargs.get("table_name", "")
        data: dict = kwargs.get("data", {})

        repo = DataModelRepository(self.db)
        model_def = repo.get_by_table_name(table_name, self.tenant_id)
        if not model_def:
            return f"错误：数据表 '{table_name}' 不存在"

        DynamicModel = generate_sqlalchemy_model(model_def)
        obj = DynamicModel(**data)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)

        return f"成功插入记录到 '{table_name}'，ID={obj.id}"


class LowcodeUpdateTool(BaseTool):
    """更新低代码动态表中的数据"""

    name = "update_data"
    description = "更新低代码平台数据表中的一条记录"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "数据库表名",
            },
            "record_id": {
                "type": "integer",
                "description": "要更新的记录 ID",
            },
            "data": {
                "type": "object",
                "description": "要更新的数据，如 {\"name\": \"李四\", \"department\": \"市场部\"}",
            },
        },
        "required": ["table_name", "record_id", "data"],
    }

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, **kwargs: Any) -> str:
        from app.services.model.generator import generate_sqlalchemy_model
        from app.services.model.repository import DataModelRepository

        table_name: str = kwargs.get("table_name", "")
        record_id: int = kwargs.get("record_id", 0)
        data: dict = kwargs.get("data", {})

        repo = DataModelRepository(self.db)
        model_def = repo.get_by_table_name(table_name, self.tenant_id)
        if not model_def:
            return f"错误：数据表 '{table_name}' 不存在"

        DynamicModel = generate_sqlalchemy_model(model_def)
        obj = self.db.query(DynamicModel).filter_by(id=record_id).first()
        if not obj:
            return f"错误：在 '{table_name}' 中未找到 ID={record_id} 的记录"

        for key, value in data.items():
            if hasattr(DynamicModel, key):
                setattr(obj, key, value)
        self.db.commit()

        return f"成功更新 '{table_name}' 中 ID={record_id} 的记录"


class LowcodeDeleteTool(BaseTool):
    """删除低代码动态表中的数据"""

    name = "delete_data"
    description = "删除低代码平台数据表中的一条记录"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "数据库表名",
            },
            "record_id": {
                "type": "integer",
                "description": "要删除的记录 ID",
            },
        },
        "required": ["table_name", "record_id"],
    }

    def __init__(self, db: Session, tenant_id: int) -> None:
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, **kwargs: Any) -> str:
        from app.services.model.generator import generate_sqlalchemy_model
        from app.services.model.repository import DataModelRepository

        table_name: str = kwargs.get("table_name", "")
        record_id: int = kwargs.get("record_id", 0)

        repo = DataModelRepository(self.db)
        model_def = repo.get_by_table_name(table_name, self.tenant_id)
        if not model_def:
            return f"错误：数据表 '{table_name}' 不存在"

        DynamicModel = generate_sqlalchemy_model(model_def)
        obj = self.db.query(DynamicModel).filter_by(id=record_id).first()
        if not obj:
            return f"错误：在 '{table_name}' 中未找到 ID={record_id} 的记录"

        self.db.delete(obj)
        self.db.commit()

        return f"成功删除 '{table_name}' 中 ID={record_id} 的记录"
