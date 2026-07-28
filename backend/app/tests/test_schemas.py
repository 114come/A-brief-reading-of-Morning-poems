from datetime import datetime
from typing import Any

from app.services.tenant.schemas import (
    PermissionCreate,
    RoleCreate,
    TenantCreate,
    TenantResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)


def test_tenant_create_schema() -> None:
    data: dict[str, Any] = {
        "name": "测试租户",
        "code": "test001",
        "admin_username": "admin",
        "admin_password": "secret123",
        "admin_email": "admin@test.com",
    }
    t = TenantCreate(**data)
    assert t.name == "测试租户"
    assert t.code == "test001"
    assert t.admin_username == "admin"
    assert t.admin_password == "secret123"
    assert t.admin_email == "admin@test.com"


def test_user_create_schema() -> None:
    data: dict[str, Any] = {
        "username": "john",
        "email": "john@example.com",
        "password": "secret123",
        "tenant_id": 1,
    }
    u = UserCreate(**data)
    assert u.username == "john"
    assert u.email == "john@example.com"
    assert u.password == "secret123"
    assert u.tenant_id == 1
    assert u.is_superuser is False


def test_user_login_schema() -> None:
    data: dict[str, Any] = {"username": "admin", "password": "secret"}
    login = UserLogin(**data)
    assert login.username == "admin"
    assert login.password == "secret"


def test_tenant_response_schema() -> None:
    data: dict[str, Any] = {
        "id": 1,
        "name": "Test Tenant",
        "code": "test001",
        "status": "active",
        "db_name": "db_test001",
        "created_at": datetime.now(),
    }
    t = TenantResponse(**data)
    assert t.id == 1
    assert t.status == "active"
    assert t.db_name == "db_test001"


def test_user_response_schema() -> None:
    data: dict[str, Any] = {
        "id": 1,
        "username": "john",
        "email": "john@example.com",
        "tenant_id": 1,
        "is_superuser": False,
        "is_active": True,
        "created_at": datetime.now(),
    }
    u = UserResponse(**data)
    assert u.id == 1
    assert u.is_active is True


def test_token_response_schema() -> None:
    data: dict[str, Any] = {"access_token": "abc", "refresh_token": "def"}
    token = TokenResponse(**data)
    assert token.access_token == "abc"
    assert token.refresh_token == "def"
    assert token.token_type == "bearer"


def test_role_create_schema() -> None:
    data: dict[str, Any] = {
        "name": "Admin",
        "code": "admin",
        "description": "Administrator role",
        "tenant_id": 1,
    }
    r = RoleCreate(**data)
    assert r.name == "Admin"
    assert r.code == "admin"
    assert r.description == "Administrator role"
    assert r.tenant_id == 1


def test_role_create_schema_optional_description() -> None:
    data: dict[str, Any] = {"name": "User", "code": "user", "tenant_id": 1}
    r = RoleCreate(**data)
    assert r.description is None


def test_permission_create_schema() -> None:
    data: dict[str, Any] = {
        "code": "user:read",
        "name": "Read User",
        "resource": "user",
        "action": "read",
    }
    p = PermissionCreate(**data)
    assert p.code == "user:read"
    assert p.name == "Read User"
    assert p.resource == "user"
    assert p.action == "read"
