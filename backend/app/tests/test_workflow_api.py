"""Tests for the workflow API routes."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

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

    def _mock_create_tenant_database(tenant: object) -> None:
        pass

    monkeypatch.setattr(
        "app.services.tenant.service.create_tenant_database",
        _mock_create_tenant_database,
    )


from app.main import app  # noqa: E402

app.dependency_overrides[get_master_db] = override_get_db
client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────


def _create_tenant_and_login(code: str) -> tuple[int, str]:
    """Create a tenant and return (tenant_id, access_token)."""
    payload = {
        "name": f"Workflow Test {code}",
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


def _create_workflow(token: str, name: str = "测试工作流") -> int:
    """Create a test workflow and return its ID."""
    payload = {
        "name": name,
        "description": "测试描述",
        "definition": {"nodes": [], "edges": []},
    }
    response = client.post(
        "/api/v1/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, f"Create workflow failed: {response.text}"
    data = response.json()
    assert data["code"] == 0, f"Expected code 0, got {data}"
    return data["data"]["id"]


# ── Workflow CRUD Tests ─────────────────────────────────────


class TestWorkflowCRUD:
    def test_create_workflow(self) -> None:
        _, token = _create_tenant_and_login("wf_create")
        wf_id = _create_workflow(token)
        assert wf_id > 0

    def test_list_workflows(self) -> None:
        _, token = _create_tenant_and_login("wf_list")
        _create_workflow(token, "A")
        _create_workflow(token, "B")

        response = client.get(
            "/api/v1/workflows",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 2

    def test_get_workflow(self) -> None:
        _, token = _create_tenant_and_login("wf_get")
        wf_id = _create_workflow(token)

        response = client.get(
            f"/api/v1/workflows/{wf_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试工作流"
        assert data["data"]["is_active"] is True
        assert data["data"]["definition"] == {"nodes": [], "edges": []}

    def test_get_workflow_not_found(self) -> None:
        _, token = _create_tenant_and_login("wf_get_nf")

        response = client.get(
            "/api/v1/workflows/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 422000
        assert "不存在" in data["message"]

    def test_update_workflow(self) -> None:
        _, token = _create_tenant_and_login("wf_update")
        wf_id = _create_workflow(token)

        payload = {"name": "更新工作流", "is_active": False}
        response = client.put(
            f"/api/v1/workflows/{wf_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "更新工作流"
        assert data["data"]["is_active"] is False

    def test_delete_workflow(self) -> None:
        _, token = _create_tenant_and_login("wf_delete")
        wf_id = _create_workflow(token)

        response = client.delete(
            f"/api/v1/workflows/{wf_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "工作流已删除"

        # Verify it is gone
        response = client.get(
            f"/api/v1/workflows/{wf_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert data["code"] == 422000


# ── Workflow Run Tests ──────────────────────────────────────


class TestWorkflowRun:
    def test_run_workflow(self) -> None:
        """Test running a simple start->end workflow via API."""
        _, token = _create_tenant_and_login("wf_run")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [{"source": "s1", "target": "e1"}],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Run Test", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "end": mock_end},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={"input": {"key": "value"}},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["workflow_id"] == wf_id
        assert data["data"]["status"] == "completed"
        assert data["data"]["id"] > 0

    def test_run_workflow_not_found(self) -> None:
        """Test running a non-existent workflow returns error."""
        _, token = _create_tenant_and_login("wf_run_nf")

        response = client.post(
            "/api/v1/workflows/99999/run",
            json={"input": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 422000

    def test_run_workflow_with_input_data(self) -> None:
        """Test running a workflow with input data preserved in context."""
        _, token = _create_tenant_and_login("wf_run_input")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [{"source": "s1", "target": "e1"}],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Input Test", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "end": mock_end},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={"input": {"key": "value"}},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "completed"
        assert data["data"]["context"].get("input") == {"key": "value"}


# ── Instance Tests ──────────────────────────────────────────


class TestWorkflowInstances:
    def test_list_instances_empty(self) -> None:
        """Test listing instances for a workflow with no runs."""
        _, token = _create_tenant_and_login("wf_inst_empty")
        wf_id = _create_workflow(token)

        response = client.get(
            f"/api/v1/workflows/{wf_id}/instances",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []

    def test_list_instances_after_run(self) -> None:
        """Test listing instances after running a workflow."""
        _, token = _create_tenant_and_login("wf_inst_list")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [{"source": "s1", "target": "e1"}],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Inst List", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "end": mock_end},
            clear=True,
        ):
            client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )

        response = client.get(
            f"/api/v1/workflows/{wf_id}/instances",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1

    def test_list_instances_workflow_not_found(self) -> None:
        """Test listing instances for a non-existent workflow."""
        _, token = _create_tenant_and_login("wf_inst_wf_nf")

        response = client.get(
            "/api/v1/workflows/99999/instances",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 422000

    def test_get_instance(self) -> None:
        """Test getting a workflow instance detail."""
        _, token = _create_tenant_and_login("wf_inst_get")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [{"source": "s1", "target": "e1"}],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Get Inst", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "end": mock_end},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        inst_id = response.json()["data"]["id"]

        response = client.get(
            f"/api/v1/workflows/instances/{inst_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["id"] == inst_id
        assert data["data"]["workflow_id"] == wf_id
        assert data["data"]["status"] == "completed"

    def test_get_instance_not_found(self) -> None:
        """Test getting a non-existent instance."""
        _, token = _create_tenant_and_login("wf_inst_nf")

        response = client.get(
            "/api/v1/workflows/instances/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 422000


# ── Approve Tests ───────────────────────────────────────────


class TestWorkflowApprove:
    def test_approve_human_review(self) -> None:
        """Test approving a human-review workflow."""
        _, token = _create_tenant_and_login("wf_approve")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "h1", "type": "human", "config": {"instructions": "Approve?"}},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "h1"},
                {"source": "h1", "target": "e1"},
            ],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Approve Test", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_human = AsyncMock()
        mock_human.execute.return_value = {
            "status": "pending",
            "instructions": "Approve?",
        }
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "human": mock_human, "end": mock_end},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.json()["code"] == 0
        inst_id = response.json()["data"]["id"]
        assert response.json()["data"]["status"] == "waiting_human"
        assert response.json()["data"]["current_node_id"] == "h1"

        # Approve the instance
        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "human": mock_human, "end": mock_end},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/instances/{inst_id}/approve",
                json={"approved": True, "comment": "Proceed"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "completed"

    def test_reject_human_review(self) -> None:
        """Test rejecting a human-review workflow."""
        _, token = _create_tenant_and_login("wf_reject")

        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "h1", "type": "human", "config": {"instructions": "Review?"}},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "h1"},
                {"source": "h1", "target": "e1"},
            ],
        }
        response = client.post(
            "/api/v1/workflows",
            json={"name": "Reject Test", "definition": definition},
            headers={"Authorization": f"Bearer {token}"},
        )
        wf_id = response.json()["data"]["id"]

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_human = AsyncMock()
        mock_human.execute.return_value = {
            "status": "pending",
            "instructions": "Review?",
        }

        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "human": mock_human},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/{wf_id}/run",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.json()["code"] == 0
        inst_id = response.json()["data"]["id"]
        assert response.json()["data"]["status"] == "waiting_human"

        # Reject the instance
        with patch.dict(
            "app.services.ai.workflow.executor.NODE_REGISTRY",
            {"start": mock_start, "human": mock_human},
            clear=True,
        ):
            response = client.post(
                f"/api/v1/workflows/instances/{inst_id}/approve",
                json={"approved": False, "comment": "Not ready"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "completed"

    def test_approve_instance_not_found(self) -> None:
        """Test approving a non-existent instance returns error."""
        _, token = _create_tenant_and_login("wf_app_nf")

        response = client.post(
            "/api/v1/workflows/instances/99999/approve",
            json={"approved": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 422000
