from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from app.api.v1.dynamic import register_dynamic_routers
from app.services.model.models import DataField, DataModel


@pytest.fixture
def mock_app() -> FastAPI:
    return FastAPI()


@pytest.fixture
def published_model() -> DataModel:
    return DataModel(
        id=1,
        name="TestProduct",
        table_name="test_products",
        status="published",
        fields=[
            DataField(name="title", field_type="string", db_column_type="VARCHAR(100)"),
        ],
    )


@pytest.fixture
def draft_model() -> DataModel:
    return DataModel(
        id=2,
        name="TestDraft",
        table_name="test_drafts",
        status="draft",
        fields=[
            DataField(name="name", field_type="string", db_column_type="VARCHAR(100)"),
        ],
    )


def test_register_dynamic_routers_with_published_models(
    mock_app: FastAPI,
    published_model: DataModel,
) -> None:
    """已发布模型应被注册为动态路由"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [published_model]

    mock_router = MagicMock()

    with patch("app.api.v1.dynamic.Session", return_value=mock_db):
        with patch(
            "app.api.v1.dynamic.generate_sqlalchemy_model", return_value=MagicMock()
        ) as mock_gen_model:
            with patch(
                "app.api.v1.dynamic.generate_pydantic_schemas",
                return_value=(MagicMock(), MagicMock()),
            ) as mock_gen_schema:
                with patch(
                    "app.api.v1.dynamic.generate_crud_router", return_value=mock_router
                ) as mock_gen_router:
                    with patch.object(
                        mock_app, "include_router"
                    ) as mock_include_router:
                        register_dynamic_routers(mock_app)

    mock_gen_model.assert_called_once_with(published_model)
    mock_gen_schema.assert_called_once_with(published_model)
    mock_gen_router.assert_called_once()
    mock_include_router.assert_called_once_with(mock_router, prefix="/api/v1")
    mock_db.close.assert_called_once()


def test_register_dynamic_routers_skips_draft_models(
    mock_app: FastAPI,
    draft_model: DataModel,
) -> None:
    """草稿状态模型不应被注册"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    with patch("app.api.v1.dynamic.Session", return_value=mock_db):
        with patch("app.api.v1.dynamic.generate_sqlalchemy_model") as mock_gen_model:
            with patch(
                "app.api.v1.dynamic.generate_pydantic_schemas"
            ) as mock_gen_schema:
                with patch(
                    "app.api.v1.dynamic.generate_crud_router"
                ) as mock_gen_router:
                    with patch.object(
                        mock_app, "include_router"
                    ) as mock_include_router:
                        register_dynamic_routers(mock_app)

    mock_gen_model.assert_not_called()
    mock_gen_schema.assert_not_called()
    mock_gen_router.assert_not_called()
    mock_include_router.assert_not_called()
    mock_db.close.assert_called_once()


def test_register_dynamic_routers_continues_on_single_failure(
    mock_app: FastAPI,
    published_model: DataModel,
) -> None:
    """单个模型注册失败不应阻止其他模型注册"""
    model_ok = DataModel(
        id=2,
        name="GoodModel",
        table_name="good_models",
        status="published",
        fields=[
            DataField(name="name", field_type="string", db_column_type="VARCHAR(100)"),
        ],
    )
    model_bad = DataModel(
        id=3,
        name="BadModel",
        table_name="bad_models",
        status="published",
        fields=[
            DataField(name="name", field_type="string", db_column_type="VARCHAR(100)"),
        ],
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [model_bad, model_ok]

    mock_router = MagicMock()

    def side_effect_gen(model_def: DataModel) -> MagicMock:
        if model_def.table_name == "bad_models":
            raise ValueError("Simulated generation failure")
        return MagicMock()

    with patch("app.api.v1.dynamic.Session", return_value=mock_db):
        with patch(
            "app.api.v1.dynamic.generate_sqlalchemy_model", side_effect=side_effect_gen
        ):
            with patch(
                "app.api.v1.dynamic.generate_pydantic_schemas",
                return_value=(MagicMock(), MagicMock()),
            ):
                with patch(
                    "app.api.v1.dynamic.generate_crud_router", return_value=mock_router
                ):
                    with patch.object(
                        mock_app, "include_router"
                    ) as mock_include_router:
                        register_dynamic_routers(mock_app)

    # 只有 good_models 被注册，bad_models 失败被跳过
    assert mock_include_router.call_count == 1
    mock_include_router.assert_called_once_with(mock_router, prefix="/api/v1")
    mock_db.close.assert_called_once()


def test_register_dynamic_routers_empty_published_models(mock_app: FastAPI) -> None:
    """没有已发布模型时不应注册任何路由"""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    with patch("app.api.v1.dynamic.Session", return_value=mock_db):
        with patch("app.api.v1.dynamic.generate_sqlalchemy_model") as mock_gen_model:
            with patch(
                "app.api.v1.dynamic.generate_pydantic_schemas"
            ) as mock_gen_schema:
                with patch(
                    "app.api.v1.dynamic.generate_crud_router"
                ) as mock_gen_router:
                    with patch.object(
                        mock_app, "include_router"
                    ) as mock_include_router:
                        register_dynamic_routers(mock_app)

    mock_gen_model.assert_not_called()
    mock_gen_schema.assert_not_called()
    mock_gen_router.assert_not_called()
    mock_include_router.assert_not_called()
    mock_db.close.assert_called_once()
