import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.workflow.executor import WorkflowExecutor


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_instance(definition: dict, context: str = "{}") -> MagicMock:
    """Create a mock WorkflowInstance with the given definition and context."""
    instance = MagicMock()
    instance.workflow = MagicMock()
    instance.workflow.definition = json.dumps(definition)
    instance.context = context
    instance.status = "pending"
    instance.started_at = None
    instance.completed_at = None
    instance.current_node_id = None
    return instance


# ── DAG Validation ─────────────────────────────────────────────────────────────


class TestDagValidation:
    def test_acyclic_dag_passes(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
                {"source": "n1", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        # Should not raise
        executor._validate_dag()

    def test_dag_detects_cycle(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
                {"source": "n1", "target": "e1"},
                {"source": "e1", "target": "s1"},  # cycle
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        with pytest.raises(ValueError, match="DAG contains a cycle"):
            executor._validate_dag()

    def test_dag_detects_self_loop(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
                {"source": "n1", "target": "n1"},  # self-loop
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        with pytest.raises(ValueError, match="DAG contains a cycle"):
            executor._validate_dag()

    def test_dag_empty_graph_passes(self) -> None:
        definition = {"nodes": [], "edges": []}
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        # Single node with no edges is trivially acyclic
        executor._validate_dag()


# ── Start Node ─────────────────────────────────────────────────────────────────


class TestStartNode:
    def test_no_start_node_raises(self) -> None:
        definition = {
            "nodes": [{"id": "n1", "type": "llm"}],
            "edges": [],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        with pytest.raises(ValueError, match="No start node found"):
            executor._find_start_node()

    def test_finds_start_node(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
            ],
            "edges": [],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = executor._find_start_node()
        assert node["id"] == "s1"


# ── find_next ──────────────────────────────────────────────────────────────────


class TestFindNext:
    def test_no_outgoing_returns_none(self) -> None:
        definition = {
            "nodes": [{"id": "n1", "type": "end"}],
            "edges": [],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "n1", "type": "end"}
        assert executor._find_next(node, {}) is None

    def test_condition_true_branch(self) -> None:
        definition = {
            "nodes": [{"id": "c1", "type": "condition"}],
            "edges": [
                {"source": "c1", "target": "true_node", "label": "true"},
                {"source": "c1", "target": "false_node", "label": "false"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "c1", "type": "condition"}
        assert executor._find_next(node, {"result": True}) == "true_node"

    def test_condition_false_branch(self) -> None:
        definition = {
            "nodes": [{"id": "c1", "type": "condition"}],
            "edges": [
                {"source": "c1", "target": "true_node", "label": "true"},
                {"source": "c1", "target": "false_node", "label": "false"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "c1", "type": "condition"}
        assert executor._find_next(node, {"result": False}) == "false_node"

    def test_condition_default_false_on_no_result(self) -> None:
        definition = {
            "nodes": [{"id": "c1", "type": "condition"}],
            "edges": [
                {"source": "c1", "target": "true_node", "label": "true"},
                {"source": "c1", "target": "false_node", "label": "false"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "c1", "type": "condition"}
        # No "result" key -> falsy -> false branch
        assert executor._find_next(node, {}) == "false_node"

    def test_condition_no_matching_branch_returns_none(self) -> None:
        definition = {
            "nodes": [{"id": "c1", "type": "condition"}],
            "edges": [
                {"source": "c1", "target": "yes_node", "label": "yes"},
                {"source": "c1", "target": "no_node", "label": "no"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "c1", "type": "condition"}
        # Branch labels are "yes"/"no", not "true"/"false" -> no match
        assert executor._find_next(node, {"result": True}) is None

    def test_non_condition_returns_first_outgoing(self) -> None:
        definition = {
            "nodes": [{"id": "s1", "type": "start"}, {"id": "n1", "type": "llm"}],
            "edges": [
                {"source": "s1", "target": "n1"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        node = {"id": "s1", "type": "start"}
        assert executor._find_next(node, {}) == "n1"


# ── Full Execution ─────────────────────────────────────────────────────────────


class TestExecute:
    @pytest.mark.asyncio
    async def test_simple_linear_execution(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm", "config": {"prompt": "hi", "model": "gpt"}},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
                {"source": "n1", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)

        mock_start = AsyncMock()
        mock_start.execute.return_value = {"input": "hello"}
        mock_llm = AsyncMock()
        mock_llm.execute.return_value = {"content": "Generated text"}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {"result": "done"}

        patches = {
            "start": mock_start,
            "end": mock_end,
            "llm": mock_llm,
        }

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", patches, clear=True):
            executor = WorkflowExecutor(instance, {"ai_service": MagicMock()})
            await executor.execute({"input": "hello"})

        assert instance.status == "completed"
        assert instance.started_at is not None
        assert instance.completed_at is not None

        # Verify execution order via context outputs
        context = json.loads(instance.context)
        assert "s1" in context["outputs"]
        assert "n1" in context["outputs"]
        assert "e1" in context["outputs"]

        # Verify node execution
        mock_start.execute.assert_awaited_once()
        mock_llm.execute.assert_awaited_once()
        mock_end.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_with_unknown_node_type_fails(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "x1", "type": "unknown_type"},
            ],
            "edges": [
                {"source": "s1", "target": "x1"},
            ],
        }
        instance = _make_instance(definition)

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", {"start": mock_start}, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.execute()

        assert instance.status == "failed"
        # context should be set before returning
        assert instance.context is not None

    @pytest.mark.asyncio
    async def test_execute_node_error_caught(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
            ],
        }
        instance = _make_instance(definition)

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_llm = AsyncMock()
        mock_llm.execute.side_effect = RuntimeError("LLM failure")

        patches = {"start": mock_start, "llm": mock_llm}

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", patches, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.execute()

        assert instance.status == "failed"
        context = json.loads(instance.context)
        assert "error" in context["outputs"]["n1"]
        assert "LLM failure" in context["outputs"]["n1"]["error"]

    @pytest.mark.asyncio
    async def test_execute_with_condition_branching(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "c1", "type": "condition", "config": {"expression": "True"}},
                {"id": "true_branch", "type": "llm"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "c1"},
                {"source": "c1", "target": "true_branch", "label": "true"},
                {"source": "c1", "target": "e1", "label": "false"},
                {"source": "true_branch", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_condition = AsyncMock()
        mock_condition.execute.return_value = {"result": True}
        mock_llm = AsyncMock()
        mock_llm.execute.return_value = {"content": "branch output"}
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        patches = {
            "start": mock_start,
            "condition": mock_condition,
            "llm": mock_llm,
            "end": mock_end,
        }

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", patches, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.execute()

        assert instance.status == "completed"
        # Condition was evaluated, and the true branch was taken
        mock_condition.execute.assert_awaited_once()
        mock_llm.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_human_review_pauses_execution(self) -> None:
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
        instance = _make_instance(definition)

        mock_start = AsyncMock()
        mock_start.execute.return_value = {}
        mock_human = AsyncMock()
        mock_human.execute.return_value = {
            "status": "pending",
            "instructions": "Approve?",
        }
        mock_end = AsyncMock()
        mock_end.execute.return_value = {}

        patches = {"start": mock_start, "human": mock_human, "end": mock_end}

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", patches, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.execute()

        assert instance.status == "waiting_human"
        assert instance.current_node_id == "h1"
        # End node should NOT have been executed
        mock_end.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_cyclic_fails(self) -> None:
        definition = {
            "nodes": [
                {"id": "s1", "type": "start"},
                {"id": "n1", "type": "llm"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "s1", "target": "n1"},
                {"source": "n1", "target": "e1"},
                {"source": "e1", "target": "s1"},
            ],
        }
        instance = _make_instance(definition)
        executor = WorkflowExecutor(instance, {})
        # validate_dag is called first in execute, so it should raise
        with pytest.raises(ValueError, match="DAG contains a cycle"):
            await executor.execute()


# ── Resume After Review ────────────────────────────────────────────────────────


class TestResumeAfterReview:
    @pytest.mark.asyncio
    async def test_resume_approved_continues(self) -> None:
        definition = {
            "nodes": [
                {"id": "h1", "type": "human"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "h1", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)
        instance.status = "waiting_human"
        instance.current_node_id = "h1"
        instance.context = json.dumps({"outputs": {}, "input": {}})

        mock_end = AsyncMock()
        mock_end.execute.return_value = {"result": "done"}

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", {"end": mock_end}, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.resume_after_review(approved=True, comment="Looks good")

        assert instance.status == "completed"
        context = json.loads(instance.context)
        h1_output = context["outputs"]["h1"]
        assert h1_output["approved"] is True
        assert h1_output["comment"] == "Looks good"

    @pytest.mark.asyncio
    async def test_resume_rejected_completes(self) -> None:
        definition = {
            "nodes": [
                {"id": "h1", "type": "human"},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "h1", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)
        instance.status = "waiting_human"
        instance.current_node_id = "h1"
        instance.context = json.dumps({"outputs": {}, "input": {}})

        executor = WorkflowExecutor(instance, {})
        await executor.resume_after_review(approved=False)

        assert instance.status == "completed"
        # End node should not be executed when rejected
        context = json.loads(instance.context)
        assert context["outputs"]["h1"]["approved"] is False

    @pytest.mark.asyncio
    async def test_resume_not_waiting_raises(self) -> None:
        instance = _make_instance({"nodes": [], "edges": []})
        instance.status = "running"
        executor = WorkflowExecutor(instance, {})
        with pytest.raises(ValueError, match="Not in waiting_human status"):
            await executor.resume_after_review(approved=True)

    @pytest.mark.asyncio
    async def test_resume_no_current_node_fails(self) -> None:
        instance = _make_instance({"nodes": [], "edges": []})
        instance.status = "waiting_human"
        instance.current_node_id = None
        executor = WorkflowExecutor(instance, {})
        await executor.resume_after_review(approved=True)
        assert instance.status == "failed"

    @pytest.mark.asyncio
    async def test_resume_approved_human_in_continuation(self) -> None:
        """When resume hits another human node, it pauses again."""
        definition = {
            "nodes": [
                {"id": "h1", "type": "human"},
                {"id": "h2", "type": "human", "config": {"instructions": "Review again"}},
                {"id": "e1", "type": "end"},
            ],
            "edges": [
                {"source": "h1", "target": "h2"},
                {"source": "h2", "target": "e1"},
            ],
        }
        instance = _make_instance(definition)
        instance.status = "waiting_human"
        instance.current_node_id = "h1"
        instance.context = json.dumps({"outputs": {}, "input": {}})

        mock_h2 = AsyncMock()
        mock_h2.execute.return_value = {
            "status": "pending",
            "instructions": "Review again",
        }
        mock_end = AsyncMock()

        patches = {"human": mock_h2, "end": mock_end}

        with patch.dict("app.services.ai.workflow.executor.NODE_REGISTRY", patches, clear=True):
            executor = WorkflowExecutor(instance, {})
            await executor.resume_after_review(approved=True)

        assert instance.status == "waiting_human"
        assert instance.current_node_id == "h2"
        mock_end.execute.assert_not_awaited()
