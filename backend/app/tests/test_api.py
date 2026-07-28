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
