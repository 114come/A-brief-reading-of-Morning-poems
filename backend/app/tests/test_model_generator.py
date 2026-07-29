from datetime import datetime
from typing import Any

from fastapi import APIRouter
from fastapi.routing import APIRoute
from pydantic import BaseModel
from sqlalchemy import BigInteger, Boolean, Column, DateTime, DECIMAL, JSON, String, Text

from app.services.model.generator import (
    generate_crud_router,
    generate_pydantic_schemas,
    generate_sqlalchemy_model,
)
from app.services.model.models import DataField, DataModel


def test_generate_sqlalchemy_model() -> None:
    model_def = DataModel(
        id=1,
        table_name="test_products",
        fields=[
            DataField(name="title", db_column_type="VARCHAR(100)"),
            DataField(name="price", db_column_type="DECIMAL(10,2)"),
            DataField(name="is_active", db_column_type="TINYINT(1)"),
        ],
    )
    DynamicModel = generate_sqlalchemy_model(model_def)
    assert DynamicModel.__tablename__ == "test_products"
    assert hasattr(DynamicModel, "title")
    assert hasattr(DynamicModel, "price")
    assert hasattr(DynamicModel, "is_active")
    assert hasattr(DynamicModel, "id")
    assert hasattr(DynamicModel, "created_at")
    assert hasattr(DynamicModel, "updated_at")


def test_generate_sqlalchemy_model_column_types() -> None:
    model_def = DataModel(
        id=2,
        table_name="test_all_types",
        fields=[
            DataField(name="col_varchar", db_column_type="VARCHAR(255)"),
            DataField(name="col_text", db_column_type="TEXT"),
            DataField(name="col_decimal", db_column_type="DECIMAL(19,4)"),
            DataField(name="col_bigint", db_column_type="BIGINT"),
            DataField(name="col_tinyint", db_column_type="TINYINT(1)"),
            DataField(name="col_date", db_column_type="DATE"),
            DataField(name="col_datetime", db_column_type="DATETIME"),
            DataField(name="col_json", db_column_type="JSON"),
            DataField(name="col_unknown", db_column_type="UNKNOWN"),
        ],
    )
    DynamicModel = generate_sqlalchemy_model(model_def)
    columns: dict[str, Column[Any]] = {
        "col_varchar": getattr(DynamicModel, "col_varchar"),
        "col_text": getattr(DynamicModel, "col_text"),
        "col_decimal": getattr(DynamicModel, "col_decimal"),
        "col_bigint": getattr(DynamicModel, "col_bigint"),
        "col_tinyint": getattr(DynamicModel, "col_tinyint"),
        "col_date": getattr(DynamicModel, "col_date"),
        "col_datetime": getattr(DynamicModel, "col_datetime"),
        "col_json": getattr(DynamicModel, "col_json"),
        "col_unknown": getattr(DynamicModel, "col_unknown"),
    }

    assert isinstance(columns["col_varchar"].type, String)
    assert isinstance(columns["col_text"].type, Text)
    assert isinstance(columns["col_decimal"].type, DECIMAL)
    assert isinstance(columns["col_bigint"].type, BigInteger)
    assert isinstance(columns["col_tinyint"].type, Boolean)
    assert isinstance(columns["col_date"].type, DateTime)
    assert isinstance(columns["col_datetime"].type, DateTime)
    assert isinstance(columns["col_json"].type, JSON)
    assert isinstance(columns["col_unknown"].type, String)


def test_generate_pydantic_schemas() -> None:
    model_def = DataModel(
        id=3,
        table_name="test_orders",
        fields=[
            DataField(name="customer", field_type="string", db_column_type="VARCHAR(100)"),
            DataField(name="amount", field_type="number", db_column_type="DECIMAL(10,2)"),
            DataField(name="quantity", field_type="integer", db_column_type="BIGINT"),
            DataField(name="shipped", field_type="boolean", db_column_type="TINYINT(1)"),
            DataField(name="metadata", field_type="json", db_column_type="JSON"),
        ],
    )
    CreateSchema, ResponseSchema = generate_pydantic_schemas(model_def)

    assert issubclass(CreateSchema, BaseModel)
    assert issubclass(ResponseSchema, BaseModel)
    assert CreateSchema.__name__ == "test_orders_create"
    assert ResponseSchema.__name__ == "test_orders_response"

    # Test CreateSchema fields
    create_fields = CreateSchema.model_fields
    assert "customer" in create_fields
    assert "amount" in create_fields
    assert "quantity" in create_fields
    assert "shipped" in create_fields
    assert "metadata" in create_fields
    assert "id" not in create_fields

    # Test ResponseSchema fields
    response_fields = ResponseSchema.model_fields
    assert "id" in response_fields
    assert "created_at" in response_fields
    assert "updated_at" in response_fields
    assert "customer" in response_fields

    # Test instantiation
    create_data: Any = CreateSchema(customer="Alice", amount=99.99, quantity=2, shipped=True)
    assert create_data.customer == "Alice"
    assert create_data.amount == 99.99

    response_data: Any = ResponseSchema(
        id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        customer="Alice",
        amount=99.99,
        quantity=2,
        shipped=True,
        metadata={"key": "value"},
    )
    assert response_data.id == 1


def test_generate_crud_router() -> None:
    model_def = DataModel(
        id=4,
        name="TestArticles",
        table_name="test_articles",
        fields=[
            DataField(name="title", field_type="string", db_column_type="VARCHAR(200)"),
        ],
    )
    DynamicModel = generate_sqlalchemy_model(model_def)
    CreateSchema, ResponseSchema = generate_pydantic_schemas(model_def)
    router = generate_crud_router(model_def, DynamicModel, CreateSchema, ResponseSchema)

    assert isinstance(router, APIRouter)
    assert router.prefix == "/dynamic/test_articles"
    assert model_def.name in router.tags

    routes = router.routes
    route_info: list[tuple[str, str]] = []
    for route in routes:
        if isinstance(route, APIRoute) and route.methods is not None:
            for method in route.methods:
                route_info.append((method, route.path))

    methods = [method for method, _ in route_info]
    assert "POST" in methods
    assert "GET" in methods
    assert "PUT" in methods
    assert "DELETE" in methods

    # Check paths include the parameterized route
    paths = [path for _, path in route_info]
    assert "/dynamic/test_articles/" in paths
    assert "/dynamic/test_articles/{item_id}" in paths
