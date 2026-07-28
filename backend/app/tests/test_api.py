import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_master_db
from app.main import app

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_master_db] = override_get_db
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_tenant_api():
    payload = {
        "name": "API测试租户",
        "code": "api_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@api.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["tenant"]["code"] == "api_test"


def test_create_tenant_api_duplicate_code():
    payload = {
        "name": "Duplicate Tenant",
        "code": "dup_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@dup.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    assert response.json()["code"] == 0

    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 422000
    assert "已存在" in data["message"]


def test_login_with_tenant_api():
    # Create tenant first
    payload = {
        "name": "Login Test Tenant",
        "code": "login_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@login.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200

    # Login
    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=login_test",
        json=login_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


def test_login_with_tenant_wrong_password():
    # Create tenant first
    payload = {
        "name": "Wrong Password Tenant",
        "code": "wrong_pwd_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@wrong.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200

    # Login with wrong password
    login_payload = {"username": "admin", "password": "wrongpassword"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=wrong_pwd_test",
        json=login_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 401000
    assert "用户名或密码错误" in data["message"]


def test_login_with_tenant_nonexistent():
    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=nonexistent",
        json=login_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 401000
    assert "租户不存在" in data["message"]


def test_login_deprecated():
    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post("/api/v1/tenant/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 422000
    assert "login_with_tenant" in data["message"]


def test_create_role_by_superuser():
    payload = {
        "name": "Role Test Tenant",
        "code": "role_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@role.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    tenant_id = response.json()["data"]["tenant"]["id"]

    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=role_test",
        json=login_payload,
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    role_payload = {
        "name": "Test Role",
        "code": "test_role",
        "tenant_id": tenant_id,
    }
    response = client.post(
        "/api/v1/tenant/roles",
        json=role_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Test Role"


def test_create_role_by_unauthorized_user():
    payload = {
        "name": "Role Deny Tenant",
        "code": "role_deny_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@deny.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    tenant_id = response.json()["data"]["tenant"]["id"]

    db = TestSessionLocal()
    from app.core.security import get_password_hash
    from app.services.tenant.models import User

    user = User(
        tenant_id=tenant_id,
        username="regular",
        email="regular@deny.com",
        password_hash=get_password_hash("regular123"),
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.close()

    login_payload = {"username": "regular", "password": "regular123"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=role_deny_test",
        json=login_payload,
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    role_payload = {
        "name": "Denied Role",
        "code": "denied_role",
        "tenant_id": tenant_id,
    }
    response = client.post(
        "/api/v1/tenant/roles",
        json=role_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 403000
    assert "缺少权限" in data["message"]


def test_create_role_by_authorized_user():
    payload = {
        "name": "Role Grant Tenant",
        "code": "role_grant_test",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@grant.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200
    tenant_id = response.json()["data"]["tenant"]["id"]

    db = TestSessionLocal()
    from app.core.security import get_password_hash
    from app.services.tenant.models import Permission, Role, RolePermission, User, UserRole

    user = User(
        tenant_id=tenant_id,
        username="authorized",
        email="authorized@grant.com",
        password_hash=get_password_hash("auth123"),
        is_superuser=False,
    )
    db.add(user)
    db.flush()

    permission = Permission(
        code="role:create",
        name="创建角色",
        resource="role",
        action="create",
    )
    db.add(permission)
    db.flush()

    role = Role(
        tenant_id=tenant_id,
        name="Role Manager",
        code="role_manager",
    )
    db.add(role)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
    db.close()

    login_payload = {"username": "authorized", "password": "auth123"}
    response = client.post(
        "/api/v1/tenant/auth/login_with_tenant?tenant_code=role_grant_test",
        json=login_payload,
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    role_payload = {
        "name": "Authorized Role",
        "code": "authorized_role",
        "tenant_id": tenant_id,
    }
    response = client.post(
        "/api/v1/tenant/roles",
        json=role_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Authorized Role"
