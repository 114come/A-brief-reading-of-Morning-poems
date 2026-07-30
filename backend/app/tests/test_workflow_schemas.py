from datetime import datetime

import pytest
from pydantic import ValidationError

from app.services.ai.workflow.schemas import (
    ApproveRequest,
    EdgeDefinition,
    NodeDefinition,
    WorkflowCreate,
    WorkflowInstanceResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowUpdate,
)


class TestNodeDefinition:
    def test_required_fields(self):
        """test_node_definition_required_fields: verify id, type, label required"""
        node = NodeDefinition(id="node1", type="start", label="Start Node")
        assert node.id == "node1"
        assert node.type == "start"
        assert node.label == "Start Node"
        assert node.position == {}
        assert node.config == {}

    def test_with_position_and_config(self):
        node = NodeDefinition(
            id="node2",
            type="llm",
            label="LLM Call",
            position={"x": 100, "y": 200},
            config={"model": "gpt-4", "temperature": 0.7},
        )
        assert node.position == {"x": 100, "y": 200}
        assert node.config == {"model": "gpt-4", "temperature": 0.7}


class TestEdgeDefinition:
    def test_required_fields(self):
        """test_edge_definition_required_fields: verify id, source, target required"""
        edge = EdgeDefinition(id="edge1", source="node1", target="node2")
        assert edge.id == "edge1"
        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.label is None

    def test_with_label(self):
        edge = EdgeDefinition(
            id="edge2", source="node1", target="node3", label="on success"
        )
        assert edge.label == "on success"


class TestWorkflowCreate:
    def test_defaults(self):
        """test_workflow_create_defaults: verify defaults"""
        wf = WorkflowCreate(name="Test Workflow")
        assert wf.name == "Test Workflow"
        assert wf.description is None
        assert wf.definition == {"nodes": [], "edges": []}

    def test_with_description_and_definition(self):
        wf = WorkflowCreate(
            name="My Workflow",
            description="A test workflow",
            definition={
                "nodes": [
                    {"id": "n1", "type": "start", "label": "Start"}
                ],
                "edges": [],
            },
        )
        assert wf.description == "A test workflow"
        assert len(wf.definition["nodes"]) == 1

    def test_validates_name_max_length(self):
        with pytest.raises(ValidationError):
            WorkflowCreate(name="x" * 101)

    def test_validates_name_required(self):
        with pytest.raises(ValidationError):
            WorkflowCreate()


class TestWorkflowUpdate:
    def test_all_optional(self):
        """test_workflow_update_all_optional: verify all fields optional"""
        update = WorkflowUpdate()
        assert update.name is None
        assert update.description is None
        assert update.definition is None
        assert update.is_active is None

    def test_partial_update(self):
        update = WorkflowUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None

    def test_validates_name_length(self):
        with pytest.raises(ValidationError):
            WorkflowUpdate(name="x" * 101)


class TestWorkflowResponse:
    def test_parses_json_definition(self):
        """test_workflow_response_parses_json: str->dict parsing"""
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Workflow",
            "description": "A test workflow",
            "definition": '{"nodes": [], "edges": []}',
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = WorkflowResponse.model_validate(data)
        assert isinstance(response.definition, dict)
        assert response.definition == {"nodes": [], "edges": []}

    def test_handles_invalid_json(self):
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Workflow",
            "description": None,
            "definition": "not valid json",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = WorkflowResponse.model_validate(data)
        assert response.definition == {}

    def test_handles_already_parsed_dict(self):
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Test Workflow",
            "description": None,
            "definition": {"nodes": [], "edges": []},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = WorkflowResponse.model_validate(data)
        assert response.definition == {"nodes": [], "edges": []}

    def test_from_attributes(self):
        """test_workflow_response_from_attributes: verify ConfigDict works"""
        now = datetime.now()
        data = {
            "id": 1,
            "tenant_id": 1,
            "name": "Attr Workflow",
            "description": "from attrs",
            "definition": {"nodes": [{"id": "n1"}]},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = WorkflowResponse.model_validate(data)
        assert response.name == "Attr Workflow"
        assert len(response.definition["nodes"]) == 1


class TestWorkflowInstanceResponse:
    def test_parses_json_context(self):
        """test_workflow_instance_response_parses_json: str->dict parsing"""
        now = datetime.now()
        data = {
            "id": 1,
            "workflow_id": 1,
            "status": "running",
            "context": '{"key": "value", "count": 42}',
            "current_node_id": "n1",
            "started_at": now,
            "completed_at": None,
            "created_at": now,
        }
        response = WorkflowInstanceResponse.model_validate(data)
        assert isinstance(response.context, dict)
        assert response.context == {"key": "value", "count": 42}

    def test_handles_invalid_json_context(self):
        now = datetime.now()
        data = {
            "id": 1,
            "workflow_id": 1,
            "status": "pending",
            "context": "not valid json",
            "current_node_id": None,
            "started_at": None,
            "completed_at": None,
            "created_at": now,
        }
        response = WorkflowInstanceResponse.model_validate(data)
        assert response.context == {}

    def test_handles_already_parsed_dict(self):
        now = datetime.now()
        data = {
            "id": 1,
            "workflow_id": 1,
            "status": "completed",
            "context": {"result": "success"},
            "current_node_id": None,
            "started_at": now,
            "completed_at": now,
            "created_at": now,
        }
        response = WorkflowInstanceResponse.model_validate(data)
        assert response.context == {"result": "success"}


class TestWorkflowRunRequest:
    def test_defaults(self):
        """test_workflow_run_request_defaults: empty input dict"""
        req = WorkflowRunRequest()
        assert req.input == {}

    def test_with_input(self):
        req = WorkflowRunRequest(input={"user_input": "hello"})
        assert req.input == {"user_input": "hello"}


class TestApproveRequest:
    def test_required_approved(self):
        """test_approve_request_required: approved required, comment optional"""
        req = ApproveRequest(approved=True)
        assert req.approved is True
        assert req.comment is None

    def test_not_approved(self):
        req = ApproveRequest(approved=False)
        assert req.approved is False

    def test_with_comment(self):
        req = ApproveRequest(approved=True, comment="Looks good")
        assert req.comment == "Looks good"
