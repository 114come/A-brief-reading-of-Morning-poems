import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.services.ai.workflow.models import Workflow, WorkflowInstance
from app.services.ai.workflow.repository import (
    WorkflowInstanceRepository,
    WorkflowRepository,
)
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
        code="test_workflow",
        db_name="tenant_workflow_test",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="enc",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


# --- WorkflowRepository Tests ---


def test_create_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = WorkflowRepository(db)
    workflow = repo.create(
        tenant_id=tenant.id,
        name="Test Workflow",
        description="A test workflow",
        definition=json.dumps({"nodes": [], "edges": []}),
        is_active=True,
    )
    assert workflow.id is not None
    assert workflow.name == "Test Workflow"
    assert workflow.tenant_id == tenant.id
    assert workflow.is_active is True


def test_get_workflow_by_id(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = WorkflowRepository(db)
    created = repo.create(
        tenant_id=tenant.id,
        name="Find Me",
        definition="{}",
    )
    fetched = repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Find Me"

    # Non-existent ID returns None
    assert repo.get_by_id(9999) is None


def test_list_workflows_by_tenant(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = WorkflowRepository(db)
    repo.create(
        tenant_id=tenant.id,
        name="Workflow A",
        definition="{}",
    )
    repo.create(
        tenant_id=tenant.id,
        name="Workflow B",
        definition="{}",
    )

    workflows = repo.list_by_tenant(tenant.id)
    assert len(workflows) == 2
    names = [w.name for w in workflows]
    assert "Workflow A" in names
    assert "Workflow B" in names


def test_update_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = WorkflowRepository(db)
    workflow = repo.create(
        tenant_id=tenant.id,
        name="Old Name",
        description="Old description",
        definition="{}",
    )
    updated = repo.update(
        workflow.id,
        name="New Name",
        description="New description",
    )
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "New description"

    # Verify persistence
    fetched = repo.get_by_id(workflow.id)
    assert fetched is not None
    assert fetched.name == "New Name"

    # Update non-existent returns None
    assert repo.update(9999, name="Ghost") is None


def test_delete_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    repo = WorkflowRepository(db)
    workflow = repo.create(
        tenant_id=tenant.id,
        name="To Delete",
        definition="{}",
    )
    result = repo.delete(workflow.id)
    assert result is True

    fetched = repo.get_by_id(workflow.id)
    assert fetched is None

    # Repeat delete returns False
    assert repo.delete(workflow.id) is False


def test_delete_workflow_cascades_instances(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    inst_repo = WorkflowInstanceRepository(db)

    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="Cascade Test",
        definition="{}",
    )
    inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=1,
        context="{}",
    )
    inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=2,
        context="{}",
    )

    # Delete workflow
    wf_repo.delete(workflow.id)

    # Verify instances are cascaded
    instances = inst_repo.list_by_workflow(workflow.id)
    assert len(instances) == 0


# --- WorkflowInstanceRepository Tests ---


def test_create_instance(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="Instance Test",
        definition="{}",
    )
    inst_repo = WorkflowInstanceRepository(db)
    instance = inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=42,
        status="pending",
        context='{"input": "test"}',
    )
    assert instance.id is not None
    assert instance.workflow_id == workflow.id
    assert instance.triggered_by == 42
    assert instance.status == "pending"


def test_get_instance_by_id(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="Get Instance",
        definition="{}",
    )
    inst_repo = WorkflowInstanceRepository(db)
    created = inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=1,
        context="{}",
    )
    fetched = inst_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # Non-existent returns None
    assert inst_repo.get_by_id(9999) is None


def test_list_instances_by_workflow(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="List Instances",
        definition="{}",
    )
    inst_repo = WorkflowInstanceRepository(db)
    inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=1,
        context="{}",
    )
    inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=2,
        context="{}",
    )

    instances = inst_repo.list_by_workflow(workflow.id)
    assert len(instances) == 2


def test_update_instance_status(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="Status Update",
        definition="{}",
    )
    inst_repo = WorkflowInstanceRepository(db)
    instance = inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=1,
        status="pending",
        context="{}",
    )

    updated = inst_repo.update_status(instance.id, "running")
    assert updated is not None
    assert updated.status == "running"

    # Verify persistence
    fetched = inst_repo.get_by_id(instance.id)
    assert fetched is not None
    assert fetched.status == "running"

    # Non-existent returns None
    assert inst_repo.update_status(9999, "completed") is None


def test_update_instance_context(db: Session) -> None:
    tenant = _create_tenant(db)
    wf_repo = WorkflowRepository(db)
    workflow = wf_repo.create(
        tenant_id=tenant.id,
        name="Context Update",
        definition="{}",
    )
    inst_repo = WorkflowInstanceRepository(db)
    instance = inst_repo.create(
        workflow_id=workflow.id,
        tenant_id=tenant.id,
        triggered_by=1,
        context="{}",
    )

    updated = inst_repo.update_context(
        instance.id, {"key": "value", "count": 42}
    )
    assert updated is not None

    # Verify persistence - context stored as JSON string
    fetched = inst_repo.get_by_id(instance.id)
    assert fetched is not None
    parsed = json.loads(fetched.context)
    assert parsed == {"key": "value", "count": 42}

    # Non-existent returns None
    assert inst_repo.update_context(9999, {"data": "x"}) is None
