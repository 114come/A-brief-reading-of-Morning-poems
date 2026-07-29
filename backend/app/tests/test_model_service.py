from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.exceptions import ValidationException
from app.services.model.schemas import DataFieldCreate, DataModelCreate
from app.services.model.service import ModelService

TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


def test_create_model(db: Session) -> None:
    service = ModelService(db)
    data = DataModelCreate(
        name="商品",
        table_name="products",
        fields=[
            DataFieldCreate(name="title", label="标题", field_type="string"),
            DataFieldCreate(name="price", label="价格", field_type="number"),
        ],
    )
    model = service.create_model(tenant_id=1, data=data)
    assert model.table_name == "products"
    assert len(model.fields) == 2
    assert model.fields[0].db_column_type == "VARCHAR(255)"


def test_create_model_duplicate_table_name(db: Session) -> None:
    service = ModelService(db)
    data = DataModelCreate(
        name="商品",
        table_name="products",
        fields=[
            DataFieldCreate(name="title", label="标题", field_type="string"),
        ],
    )
    service.create_model(tenant_id=1, data=data)

    with pytest.raises(ValidationException, match="表名 products 已存在"):
        service.create_model(tenant_id=1, data=data)


def test_publish_model_not_found(db: Session) -> None:
    service = ModelService(db)
    tenant = MagicMock()
    with pytest.raises(ValidationException, match="模型不存在"):
        service.publish_model(model_id=999, tenant=tenant)


def test_publish_model_already_published(db: Session) -> None:
    service = ModelService(db)
    data = DataModelCreate(
        name="商品",
        table_name="published_products",
        fields=[
            DataFieldCreate(name="title", label="标题", field_type="string"),
        ],
    )
    model = service.create_model(tenant_id=1, data=data)
    model.status = "published"
    db.commit()

    tenant = MagicMock()
    with pytest.raises(ValidationException, match="模型已发布"):
        service.publish_model(model_id=model.id, tenant=tenant)
