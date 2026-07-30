import json
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.ai.workflow.models import Workflow, WorkflowInstance
from app.services.ai.workflow.schemas import WorkflowCreate, WorkflowUpdate
from app.services.ai.workflow.service import WorkflowService
from app.services.tenant.models import Tenant

# In-memory SQLite database for testing
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


def _create_tenant(db: Session) -> Tenant:
    tenant = Tenant(
        name="test_tenant",
        code="test_service",
        db_name="tenant_service_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


# ── Workflow CRUD Tests ────────────────────────────────────────────────────────


class TestWorkflowCRUD:
    def test_create_workflow(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        data = WorkflowCreate(
            name="Test Workflow",
            description="A test workflow",
            definition={"nodes": [], "edges": []},
        )
        workflow = service.create_workflow(tenant.id, data)

        assert workflow.id is not None
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert workflow.tenant_id == tenant.id
        assert workflow.is_active is True

    def test_create_workflow_default_definition(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        data = WorkflowCreate(name="Minimal")
        workflow = service.create_workflow(tenant.id, data)

        assert workflow.name == "Minimal"
        parsed = json.loads(workflow.definition)
        assert parsed == {"nodes": [], "edges": []}

    def test_get_workflow(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        created = service.create_workflow(
            tenant.id, WorkflowCreate(name="Find Me")
        )

        # Found by correct tenant
        fetched = service.get_workflow(tenant.id, created.id)
        assert fetched is not None
        assert fetched.name == "Find Me"

        # Non-existent ID
        assert service.get_workflow(tenant.id, 9999) is None

        # Wrong tenant
        assert service.get_workflow(9999, created.id) is None

    def test_list_workflows(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        service.create_workflow(tenant.id, WorkflowCreate(name="A"))
        service.create_workflow(tenant.id, WorkflowCreate(name="B"))

        workflows = service.list_workflows(tenant.id)
        assert len(workflows) == 2

        # Other tenant sees nothing
        assert service.list_workflows(9999) == []

    def test_update_workflow(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        created = service.create_workflow(
            tenant.id, WorkflowCreate(name="Old Name")
        )

        updated = service.update_workflow(
            tenant.id,
            created.id,
            WorkflowUpdate(name="New Name", is_active=False),
        )
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.is_active is False

        # Verify persistence
        fetched = service.get_workflow(tenant.id, created.id)
        assert fetched is not None
        assert fetched.name == "New Name"

    def test_update_workflow_wrong_tenant(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        created = service.create_workflow(
            tenant.id, WorkflowCreate(name="Tenant-scoped")
        )

        result = service.update_workflow(
            9999, created.id, WorkflowUpdate(name="Hacked")
        )
        assert result is None

        # Verify original unchanged
        fetched = service.get_workflow(tenant.id, created.id)
        assert fetched is not None
        assert fetched.name == "Tenant-scoped"

    def test_update_workflow_non_existent(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        result = service.update_workflow(
            tenant.id, 9999, WorkflowUpdate(name="Ghost")
        )
        assert result is None

    def test_update_workflow_definition(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        created = service.create_workflow(
            tenant.id, WorkflowCreate(name="Update Def")
        )

        new_def = {"nodes": [{"id": "n1", "type": "start"}]}
        updated = service.update_workflow(
            tenant.id,
            created.id,
            WorkflowUpdate(definition=new_def),
        )
        assert updated is not None
        parsed = json.loads(updated.definition)
        assert parsed["nodes"][0]["id"] == "n1"

    def test_delete_workflow(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        created = service.create_workflow(
            tenant.id, WorkflowCreate(name="To Delete")
        )

        # Wrong tenant
        assert service.delete_workflow(9999, created.id) is False

        # Success
        assert service.delete_workflow(tenant.id, created.id) is True

        # Verify gone
        assert service.get_workflow(tenant.id, created.id) is None

        # Delete again returns False
        assert service.delete_workflow(tenant.id, created.id) is False

    def test_delete_workflow_non_existent(self, db: Session) -> None:
        tenant = _create_tenant(db)
        service = WorkflowService(db)

        assert service.delete_workflow(tenant.id, 9999) is False


# ── Workflow Execution Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_simple_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    definition = {
        "nodes": [
            {"id": "s1", "type": "start"},
            {"id": "e1", "type": "end"},
        ],
        "edges": [
            {"source": "s1", "target": "e1"},
        ],
    }
    wf = service.create_workflow(
        tenant.id,
        WorkflowCreate(name="Simple", definition=definition),
    )

    mock_start = AsyncMock()
    mock_start.execute.return_value = {}
    mock_end = AsyncMock()
    mock_end.execute.return_value = {}

    with patch.dict(
        "app.services.ai.workflow.executor.NODE_REGISTRY",
        {"start": mock_start, "end": mock_end},
        clear=True,
    ):
        instance = await service.run_workflow(
            tenant.id, wf.id, triggered_by=1, input_data={"key": "value"}
        )

    assert instance.id is not None
    assert instance.workflow_id == wf.id
    assert instance.tenant_id == tenant.id
    assert instance.triggered_by == 1
    assert instance.status == "completed"
    assert instance.started_at is not None
    assert instance.completed_at is not None
    mock_start.execute.assert_awaited_once()
    mock_end.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_workflow_not_found(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    with pytest.raises(ValueError, match="Workflow not found"):
        await service.run_workflow(tenant.id, 9999, triggered_by=1)


@pytest.mark.asyncio
async def test_run_workflow_wrong_tenant(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    wf = service.create_workflow(
        tenant.id, WorkflowCreate(name="Tenant-specific")
    )

    with pytest.raises(ValueError, match="Workflow not found"):
        await service.run_workflow(9999, wf.id, triggered_by=1)


@pytest.mark.asyncio
async def test_run_human_review_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    definition = {
        "nodes": [
            {"id": "s1", "type": "start"},
            {
                "id": "h1",
                "type": "human",
                "config": {"instructions": "Please review"},
            },
            {"id": "e1", "type": "end"},
        ],
        "edges": [
            {"source": "s1", "target": "h1"},
            {"source": "h1", "target": "e1"},
        ],
    }
    wf = service.create_workflow(
        tenant.id,
        WorkflowCreate(name="With Review", definition=definition),
    )

    mock_start = AsyncMock()
    mock_start.execute.return_value = {}
    mock_human = AsyncMock()
    mock_human.execute.return_value = {
        "status": "pending",
        "instructions": "Please review",
    }
    mock_end = AsyncMock()

    with patch.dict(
        "app.services.ai.workflow.executor.NODE_REGISTRY",
        {"start": mock_start, "human": mock_human, "end": mock_end},
        clear=True,
    ):
        instance = await service.run_workflow(tenant.id, wf.id, triggered_by=1)

    assert instance.status == "waiting_human"
    assert instance.current_node_id == "h1"
    mock_end.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_instance(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    definition = {
        "nodes": [
            {"id": "s1", "type": "start"},
            {"id": "h1", "type": "human"},
            {"id": "e1", "type": "end"},
        ],
        "edges": [
            {"source": "s1", "target": "h1"},
            {"source": "h1", "target": "e1"},
        ],
    }
    wf = service.create_workflow(
        tenant.id,
        WorkflowCreate(name="Approve Test", definition=definition),
    )

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
        # Run to get waiting_human
        instance = await service.run_workflow(tenant.id, wf.id, triggered_by=1)

    assert instance.status == "waiting_human"

    # Now approve
    with patch.dict(
        "app.services.ai.workflow.executor.NODE_REGISTRY",
        {"start": mock_start, "human": mock_human, "end": mock_end},
        clear=True,
    ):
        result = await service.approve_instance(
            tenant.id, instance.id, approved=True, comment="Proceed"
        )

    assert result.status == "completed"


@pytest.mark.asyncio
async def test_approve_instance_rejected(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    definition = {
        "nodes": [
            {"id": "s1", "type": "start"},
            {"id": "h1", "type": "human"},
            {"id": "e1", "type": "end"},
        ],
        "edges": [
            {"source": "s1", "target": "h1"},
            {"source": "h1", "target": "e1"},
        ],
    }
    wf = service.create_workflow(
        tenant.id,
        WorkflowCreate(name="Reject Test", definition=definition),
    )

    mock_start = AsyncMock()
    mock_start.execute.return_value = {}
    mock_human = AsyncMock()
    mock_human.execute.return_value = {
        "status": "pending",
        "instructions": "Approve?",
    }

    with patch.dict(
        "app.services.ai.workflow.executor.NODE_REGISTRY",
        {"start": mock_start, "human": mock_human},
        clear=True,
    ):
        instance = await service.run_workflow(tenant.id, wf.id, triggered_by=1)

    assert instance.status == "waiting_human"

    with patch.dict(
        "app.services.ai.workflow.executor.NODE_REGISTRY",
        {"start": mock_start, "human": mock_human},
        clear=True,
    ):
        result = await service.approve_instance(
            tenant.id, instance.id, approved=False, comment="Not ready"
        )

    assert result.status == "completed"


@pytest.mark.asyncio
async def test_approve_instance_not_found(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    with pytest.raises(ValueError, match="Instance not found"):
        await service.approve_instance(tenant.id, 9999, approved=True)


# ── Instance Query Tests ───────────────────────────────────────────────────────


def test_list_and_get_instances(db: Session) -> None:
    tenant = _create_tenant(db)
    service = WorkflowService(db)

    definition = {
        "nodes": [
            {"id": "s1", "type": "start"},
            {"id": "e1", "type": "end"},
        ],
        "edges": [
            {"source": "s1", "target": "e1"},
        ],
    }
    wf = service.create_workflow(
        tenant.id,
        WorkflowCreate(name="Instance Query", definition=definition),
    )

    # No instances yet
    instances = service.list_instances(wf.id)
    assert instances == []

    # Create an instance via repo directly (simulating what run_workflow does)
    from app.services.ai.workflow.repository import WorkflowInstanceRepository
    inst_repo = WorkflowInstanceRepository(service.db)
    inst_repo.create(
        workflow_id=wf.id,
        tenant_id=tenant.id,
        triggered_by=1,
        context="{}",
    )
    inst_repo.create(
        workflow_id=wf.id,
        tenant_id=tenant.id,
        triggered_by=2,
        context="{}",
    )

    instances = service.list_instances(wf.id)
    assert len(instances) == 2

    # Get single instance
    fetched = service.get_instance(instances[0].id)
    assert fetched is not None
    assert fetched.workflow_id == wf.id

    # Non-existent
    assert service.get_instance(9999) is None
