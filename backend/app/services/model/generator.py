from datetime import datetime
from typing import Any, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import BigInteger, Boolean, Column, DateTime, DECIMAL, JSON, String, Text, func

from app.core.database import Base
from app.core.dependencies import TenantDbDep, UserDep
from app.core.response import UnifiedResponse
from app.services.model.models import DataField, DataModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _parse_mysql_type(db_column_type: str) -> tuple[str, list[int]]:
    """解析 MySQL 类型字符串，如 VARCHAR(100) → ('VARCHAR', [100])"""
    if "(" in db_column_type:
        base_type = db_column_type.split("(")[0]
        args_str = db_column_type.split("(")[1].rstrip(")")
        args = [int(x.strip()) for x in args_str.split(",")]
        return base_type, args
    return db_column_type, []


def _get_sqlalchemy_column(field: DataField) -> Column[Any]:
    """根据 DataField 生成对应的 SQLAlchemy Column"""
    base_type, args = _parse_mysql_type(field.db_column_type)

    if base_type == "VARCHAR" and args:
        return Column(String(args[0]), nullable=True)
    if base_type == "DECIMAL" and len(args) == 2:
        return Column(DECIMAL(args[0], args[1]), nullable=True)
    if base_type == "TINYINT" and args and args[0] == 1:
        return Column(Boolean, default=True, nullable=True)
    if base_type == "JSON":
        return Column(JSON, nullable=True)
    if base_type == "TEXT":
        return Column(Text, nullable=True)
    if base_type in ("DATE", "DATETIME"):
        return Column(DateTime, nullable=True)
    if base_type == "BIGINT":
        return Column(BigInteger, nullable=True)

    return Column(String(255), nullable=True)


def generate_sqlalchemy_model(model_def: DataModel) -> type[Base]:
    """根据 DataModel 定义，运行时生成 SQLAlchemy Model 类"""
    table_name = model_def.table_name

    attrs: dict[str, Any] = {
        "__tablename__": table_name,
        "__table_args__": {"extend_existing": True},
        "id": Column(BigInteger, primary_key=True, autoincrement=True),
        "created_at": Column(DateTime, default=func.now(), nullable=False),
        "updated_at": Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False),
    }

    for field in model_def.fields:
        attrs[field.name] = _get_sqlalchemy_column(field)

    return type(table_name, (Base,), attrs)


def _get_pydantic_field_type(field_type: str | None) -> tuple[Any, Any]:
    """将 field_type 映射为 Pydantic 字段类型和默认值"""
    if field_type in ("string", "text", "file"):
        return (str | None, None)
    if field_type == "number":
        return (float | None, None)
    if field_type == "integer":
        return (int | None, None)
    if field_type == "boolean":
        return (bool | None, None)
    if field_type in ("date", "datetime"):
        return (datetime | None, None)
    if field_type in ("object", "array", "json"):
        return (dict | list | None, None)
    return (str | None, None)


class ResponseBase(BaseModel):
    """Pydantic 基类：支持 from_attributes=True，允许从 ORM 对象验证"""
    model_config = ConfigDict(from_attributes=True)


def generate_pydantic_schemas(
    model_def: DataModel,
) -> tuple[type[BaseModel], type[BaseModel]]:
    """根据 DataModel 定义，运行时生成 Pydantic Create / Response Schema"""
    fields: dict[str, Any] = {}
    for field in model_def.fields:
        fields[field.name] = _get_pydantic_field_type(field.field_type)

    CreateSchema = create_model(
        f"{model_def.table_name}_create",
        __base__=BaseModel,
        **fields,
    )

    response_fields: dict[str, Any] = {
        "id": (int, ...),
        "created_at": (datetime, ...),
        "updated_at": (datetime, ...),
    }
    response_fields.update(fields)

    ResponseSchema = create_model(
        f"{model_def.table_name}_response",
        __base__=ResponseBase,
        **response_fields,
    )

    return CreateSchema, ResponseSchema


def generate_crud_router(
    model_def: DataModel,
    DynamicModel: type[Base],
    CreateSchema: type[SchemaT],
    ResponseSchema: type[SchemaT],
) -> APIRouter:
    """根据 DataModel 定义，动态生成标准 CRUD FastAPI Router"""
    router = APIRouter(prefix=f"/dynamic/{model_def.table_name}", tags=[model_def.name])

    @router.post("/", response_model=UnifiedResponse[Any])
    def create(data: CreateSchema, db: TenantDbDep, current_user: UserDep) -> UnifiedResponse[Any]:
        obj = DynamicModel(**data.model_dump(exclude_unset=True))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return UnifiedResponse.success(data=ResponseSchema.model_validate(obj).model_dump())

    @router.get("/", response_model=UnifiedResponse[Any])
    def list_items(
        db: TenantDbDep,
        current_user: UserDep,
        skip: int = 0,
        limit: int = 100,
    ) -> UnifiedResponse[Any]:
        items = db.query(DynamicModel).offset(skip).limit(limit).all()
        return UnifiedResponse.success(
            data=[ResponseSchema.model_validate(item).model_dump() for item in items]
        )

    @router.get("/{item_id}", response_model=UnifiedResponse[Any])
    def get_item(item_id: int, db: TenantDbDep, current_user: UserDep) -> UnifiedResponse[Any]:
        item = db.query(DynamicModel).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return UnifiedResponse.success(data=ResponseSchema.model_validate(item).model_dump())

    @router.put("/{item_id}", response_model=UnifiedResponse[Any])
    def update(item_id: int, data: CreateSchema, db: TenantDbDep, current_user: UserDep) -> UnifiedResponse[Any]:
        item = db.query(DynamicModel).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return UnifiedResponse.success(data=ResponseSchema.model_validate(item).model_dump())

    @router.delete("/{item_id}", response_model=UnifiedResponse[Any])
    def delete(item_id: int, db: TenantDbDep, current_user: UserDep) -> UnifiedResponse[Any]:
        item = db.query(DynamicModel).filter_by(id=item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        db.delete(item)
        db.commit()
        return UnifiedResponse.success(message="Deleted successfully")

    return router
