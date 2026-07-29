from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_master_db

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mock_tenant_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock tenant database creation to avoid MySQL dependency in tests."""

    def mock_create_tenant_database(tenant: object) -> None:
        pass

    monkeypatch.setattr(
        "app.services.tenant.service.create_tenant_database",
        mock_create_tenant_database,
    )


from app.main import app  # noqa: E402

app.dependency_overrides[get_master_db] = override_get_db
client = TestClient(app)


def _create_tenant_and_login(code: str) -> tuple[int, str]:
    payload = {
        "name": f"Model Test Tenant {code}",
        "code": code,
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": f"admin@{code}.com",
    }
    response = client.post("/api/v1/tenant/tenants", json=payload)
    assert response.status_code == 200, f"Create tenant failed: {response.text}"
    tenant_id = response.json()["data"]["tenant"]["id"]

    login_payload = {"username": "admin", "password": "admin123"}
    response = client.post(
        f"/api/v1/tenant/auth/login_with_tenant?tenant_code={code}",
        json=login_payload,
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["data"]["access_token"]
    return tenant_id, token


def test_create_model_api_unauthorized() -> None:
    payload = {
        "name": "商品",
        "table_name": "products",
        "fields": [
            {"name": "title", "label": "标题", "field_type": "string"},
            {"name": "price", "label": "价格", "field_type": "number"},
        ],
    }
    response = client.post("/api/v1/models", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 401000


def test_create_model_api() -> None:
    tenant_id, token = _create_tenant_and_login("create_model")
    payload = {
        "name": "商品",
        "table_name": "products",
        "fields": [
            {"name": "title", "label": "标题", "field_type": "string"},
            {"name": "price", "label": "价格", "field_type": "number"},
        ],
    }
    response = client.post(
        "/api/v1/models",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "商品"
    assert data["data"]["table_name"] == "products"


def test_list_models_api() -> None:
    tenant_id, token = _create_tenant_and_login("list_model")
    payload = {
        "name": "商品2",
        "table_name": "products2",
        "fields": [
            {"name": "title", "label": "标题", "field_type": "string"},
        ],
    }
    response = client.post(
        "/api/v1/models",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    response = client.get(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]) >= 1


def test_publish_model_api() -> None:
    tenant_id, token = _create_tenant_and_login("publish_model")
    payload = {
        "name": "可发布商品",
        "table_name": "publishable_products",
        "fields": [
            {"name": "title", "label": "标题", "field_type": "string"},
        ],
    }
    response = client.post(
        "/api/v1/models",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    model_id = response.json()["data"]["id"]

    with patch("app.services.model.service.get_tenant_engine", return_value=TEST_ENGINE):
        with patch("app.services.model.service.create_tenant_database"):
            response = client.post(
                f"/api/v1/models/{model_id}/publish",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["status"] == "published"
