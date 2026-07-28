from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.tenant.models import Tenant, User
from app.services.tenant.repository import TenantRepository, UserRepository

# 内存数据库用于测试
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


def test_create_tenant(db: Session) -> None:
    repo = TenantRepository(db)
    tenant = repo.create(
        name="测试租户",
        code="test001",
        db_name="tenant_test001",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    assert tenant.id is not None
    assert tenant.code == "test001"


def test_get_tenant_by_code(db: Session) -> None:
    repo = TenantRepository(db)
    repo.create(
        name="测试租户",
        code="test001",
        db_name="tenant_test001",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    found = repo.get_by_code("test001")
    assert found is not None
    assert found.name == "测试租户"
