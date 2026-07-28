from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.tenant.service import TenantService

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


def test_create_tenant_with_admin(db: Session) -> None:
    service = TenantService(db)
    tenant, user = service.create_tenant(
        name="测试租户",
        code="test001",
        admin_username="admin",
        admin_password="admin123",
        admin_email="admin@test.com",
    )
    assert tenant.code == "test001"
    assert user.username == "admin"
    assert user.tenant_id == tenant.id


def test_authenticate_user(db: Session) -> None:
    service = TenantService(db)
    tenant, _ = service.create_tenant(
        name="测试租户",
        code="test002",
        admin_username="admin",
        admin_password="admin123",
        admin_email="admin@test.com",
    )
    authenticated = service.authenticate_user("admin", "admin123", tenant.id)
    assert authenticated is not None
    assert authenticated.username == "admin"


def test_authenticate_user_wrong_password(db: Session) -> None:
    service = TenantService(db)
    tenant, _ = service.create_tenant(
        name="测试租户",
        code="test003",
        admin_username="admin",
        admin_password="admin123",
        admin_email="admin@test.com",
    )
    authenticated = service.authenticate_user("admin", "wrongpassword", tenant.id)
    assert authenticated is None


def test_authenticate_user_nonexistent(db: Session) -> None:
    service = TenantService(db)
    tenant, _ = service.create_tenant(
        name="测试租户",
        code="test004",
        admin_username="admin",
        admin_password="admin123",
        admin_email="admin@test.com",
    )
    authenticated = service.authenticate_user("nobody", "admin123", tenant.id)
    assert authenticated is None


def test_create_user(db: Session) -> None:
    service = TenantService(db)
    tenant, _ = service.create_tenant(
        name="测试租户",
        code="test005",
        admin_username="admin",
        admin_password="admin123",
        admin_email="admin@test.com",
    )
    user = service.create_user(
        username="john",
        email="john@test.com",
        password="secret",
        tenant_id=tenant.id,
    )
    assert user.username == "john"
    assert user.email == "john@test.com"
    assert user.tenant_id == tenant.id
    assert user.is_superuser is False

    authenticated = service.authenticate_user("john", "secret", tenant.id)
    assert authenticated is not None
    assert authenticated.username == "john"
