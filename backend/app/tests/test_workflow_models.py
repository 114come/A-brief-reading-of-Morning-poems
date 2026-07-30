from app.services.ai.workflow.models import Workflow, WorkflowInstance


def test_workflow_model_attributes() -> None:
    """Verify all Workflow fields exist."""
    assert Workflow.__tablename__ == "workflows"
    columns = {c.name for c in Workflow.__table__.columns}
    expected = {
        "id",
        "tenant_id",
        "name",
        "description",
        "definition",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"


def test_workflow_instance_attributes() -> None:
    """Verify all WorkflowInstance fields exist."""
    assert WorkflowInstance.__tablename__ == "workflow_instances"
    columns = {c.name for c in WorkflowInstance.__table__.columns}
    expected = {
        "id",
        "workflow_id",
        "tenant_id",
        "triggered_by",
        "status",
        "context",
        "current_node_id",
        "started_at",
        "completed_at",
        "created_at",
    }
    assert columns == expected, f"Missing columns: {expected - columns}"


def test_workflow_defaults() -> None:
    """Verify default values for Workflow fields."""
    assert Workflow.__table__.columns["is_active"].default.arg is True
