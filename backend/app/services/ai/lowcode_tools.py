"""Lowcode dynamic CRUD helper utilities for ToolCall nodes and other consumers."""

from typing import Any

from sqlalchemy.orm import Session

from app.services.model.generator import generate_sqlalchemy_model
from app.services.model.models import DataModel
from app.services.model.repository import DataModelRepository


def get_model_definition(
    db: Session, table_name: str, tenant_id: int
) -> DataModel | None:
    """Look up a DataModel definition by table_name and tenant_id."""
    repo = DataModelRepository(db)
    return repo.get_by_table_name(table_name, tenant_id)


def build_dynamic_model(model_def: DataModel) -> type:
    """Generate a runtime SQLAlchemy model class from a DataModel definition."""
    return generate_sqlalchemy_model(model_def)


def query_model(
    db: Session,
    model_def: DataModel,
    filters: dict[str, Any] | None = None,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Query records from a dynamic model with optional filters."""
    DynamicModel = build_dynamic_model(model_def)
    q = db.query(DynamicModel)
    if filters:
        for key, value in filters.items():
            if hasattr(DynamicModel, key):
                q = q.filter(getattr(DynamicModel, key) == value)
    items = q.limit(limit).all()
    return [row_to_dict(item) for item in items], len(items)


def insert_model(
    db: Session, model_def: DataModel, data: dict[str, Any]
) -> dict[str, Any]:
    """Insert a record into a dynamic model."""
    DynamicModel = build_dynamic_model(model_def)
    obj = DynamicModel(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {"item": row_to_dict(obj), "operation": "insert"}


def update_model(
    db: Session,
    model_def: DataModel,
    item_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Update a record in a dynamic model by id."""
    DynamicModel = build_dynamic_model(model_def)
    obj = db.query(DynamicModel).filter_by(id=item_id).first()
    if not obj:
        return {"error": f"Item {item_id} not found"}
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    db.commit()
    return {"item": row_to_dict(obj), "operation": "update"}


def delete_model(
    db: Session, model_def: DataModel, item_id: int
) -> dict[str, Any]:
    """Delete a record from a dynamic model by id."""
    DynamicModel = build_dynamic_model(model_def)
    obj = db.query(DynamicModel).filter_by(id=item_id).first()
    if not obj:
        return {"error": f"Item {item_id} not found"}
    db.delete(obj)
    db.commit()
    return {"operation": "delete", "id": item_id}


def row_to_dict(item: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain dict."""
    d: dict[str, Any] = {}
    for col in item.__table__.columns:
        d[col.name] = getattr(item, col.name, None)
    if d.get("created_at"):
        d["created_at"] = str(d["created_at"])
    if d.get("updated_at"):
        d["updated_at"] = str(d["updated_at"])
    return d
