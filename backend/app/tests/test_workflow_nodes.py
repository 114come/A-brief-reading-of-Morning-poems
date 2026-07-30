from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.knowledge_base.schemas import SearchResultItem
from app.services.ai.workflow.nodes.condition_node import ConditionNode
from app.services.ai.workflow.nodes.human_node import HumanReviewNode
from app.services.ai.workflow.nodes.kb_node import KBNode
from app.services.ai.workflow.nodes.llm_node import LLMNode
from app.services.ai.workflow.nodes.start_end import EndNode, StartNode
from app.services.ai.workflow.nodes.toolcall_node import ToolCallNode


# ── StartNode ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_node_returns_input() -> None:
    node = StartNode()
    context = {"input": {"key": "value"}}
    result = await node.execute({}, context, {})
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_start_node_empty_input() -> None:
    node = StartNode()
    result = await node.execute({}, {}, {})
    assert result == {}


# ── EndNode ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_node_renders_output_mapping() -> None:
    node = EndNode()
    config = {"output_mapping": {"result": "{{ llm1.content }}"}}
    context = {"outputs": {"llm1": {"content": "generated_text"}}}
    result = await node.execute(config, context, {})
    assert result == {"result": "generated_text"}


@pytest.mark.asyncio
async def test_end_node_empty_mapping() -> None:
    node = EndNode()
    result = await node.execute({}, {}, {})
    assert result == {}


# ── LLMNode ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_node_calls_chat_completion() -> None:
    node = LLMNode()
    mock_ai = AsyncMock()
    mock_ai.chat_completion.return_value = {
        "choices": [{"message": {"content": "Hello!"}}]
    }
    services = {"ai_service": mock_ai}
    config = {"prompt": "Say {{ name.content }}", "model": "gpt-4"}
    context = {"tenant_id": 1, "outputs": {"name": {"content": "hello"}}}

    result = await node.execute(config, context, services)
    assert result["content"] == "Hello!"
    mock_ai.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_node_json_parsed() -> None:
    node = LLMNode()
    mock_ai = AsyncMock()
    mock_ai.chat_completion.return_value = {
        "choices": [{"message": {"content": '{"answer": 42}'}}]
    }
    services = {"ai_service": mock_ai}
    config = {"prompt": "test", "model": "gpt-4"}
    result = await node.execute(config, {"tenant_id": 1}, services)
    assert result["parsed"] == {"answer": 42}


@pytest.mark.asyncio
async def test_llm_node_missing_service_raises() -> None:
    node = LLMNode()
    with pytest.raises(ValueError, match="ai_service is required"):
        await node.execute({"prompt": ""}, {"tenant_id": 1}, {})


# ── KBNode ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kb_node_returns_results() -> None:
    node = KBNode()
    mock_kb = MagicMock()
    mock_kb.search.return_value = [
        SearchResultItem(
            doc_id=1, doc_name="doc1", chunk_index=0,
            content="content1", score=0.95,
        ),
        SearchResultItem(
            doc_id=2, doc_name="doc2", chunk_index=1,
            content="content2", score=0.85,
        ),
    ]
    services = {"kb_service": mock_kb}
    config = {"query": "search {{ q.output }}", "kb_id": 1, "top_k": 3}
    context = {"tenant_id": 1, "outputs": {"q": {"output": "term"}}}

    result = await node.execute(config, context, services)
    assert len(result["results"]) == 2
    assert result["results"][0]["doc_name"] == "doc1"
    assert result["results"][0]["content"] == "content1"
    assert result["results"][1]["doc_name"] == "doc2"
    mock_kb.search.assert_called_once()


@pytest.mark.asyncio
async def test_kb_node_missing_service_raises() -> None:
    node = KBNode()
    with pytest.raises(ValueError, match="kb_service is required"):
        await node.execute({"query": ""}, {"tenant_id": 1}, {})


# ── ConditionNode ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_condition_node_true() -> None:
    node = ConditionNode()
    config = {"expression": "outputs.get('a', {}).get('value', 0) > 5"}
    context = {"outputs": {"a": {"value": 10}}}
    result = await node.execute(config, context, {})
    assert result["result"] is True


@pytest.mark.asyncio
async def test_condition_node_false() -> None:
    node = ConditionNode()
    config = {"expression": "outputs.get('a', {}).get('value', 0) > 5"}
    context = {"outputs": {"a": {"value": 1}}}
    result = await node.execute(config, context, {})
    assert result["result"] is False


@pytest.mark.asyncio
async def test_condition_node_default_true() -> None:
    """No expression means the default 'True' is evaluated."""
    node = ConditionNode()
    result = await node.execute({}, {}, {})
    assert result["result"] is True


# ── HumanReviewNode ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_human_node_templates_instructions() -> None:
    node = HumanReviewNode()
    config = {
        "instructions": "Please review {{ doc.content }}",
        "assignee_role": "admin",
    }
    context = {"outputs": {"doc": {"content": "report.pdf"}}}
    result = await node.execute(config, context, {})
    assert result["status"] == "pending"
    assert result["instructions"] == "Please review report.pdf"
    assert result["assignee_role"] == "admin"


@pytest.mark.asyncio
async def test_human_node_defaults() -> None:
    node = HumanReviewNode()
    result = await node.execute({}, {}, {})
    assert result["status"] == "pending"
    assert result["instructions"] == ""
    assert result["assignee_role"] == ""


# ── ToolCallNode ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toolcall_no_db() -> None:
    node = ToolCallNode()
    result = await node.execute({}, {}, {})
    assert result == {"error": "Database not available"}


@pytest.mark.asyncio
@patch(
    "app.services.ai.workflow.nodes.toolcall_node.get_model_definition",
    return_value=None,
)
async def test_toolcall_table_not_found(mock_get_def: MagicMock) -> None:
    node = ToolCallNode()
    config = {"operation": "query", "table_name": "nonexistent"}
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result == {"error": "Table 'nonexistent' not found"}
    mock_get_def.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ai.workflow.nodes.toolcall_node.query_model")
async def test_toolcall_query(mock_query: MagicMock) -> None:
    mock_query.return_value = ([{"id": 1, "title": "test"}], 1)
    node = ToolCallNode()
    config = {
        "operation": "query",
        "table_name": "products",
        "filters": {"status": "active"},
        "limit": 10,
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result["count"] == 1
    assert result["items"][0]["title"] == "test"
    mock_query.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ai.workflow.nodes.toolcall_node.insert_model")
async def test_toolcall_insert(mock_insert: MagicMock) -> None:
    mock_insert.return_value = {
        "item": {"id": 1, "title": "new item"},
        "operation": "insert",
    }
    node = ToolCallNode()
    config = {
        "operation": "insert",
        "table_name": "products",
        "data": {"title": "new item"},
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result["operation"] == "insert"
    assert result["item"]["title"] == "new item"
    mock_insert.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ai.workflow.nodes.toolcall_node.update_model")
async def test_toolcall_update(mock_update: MagicMock) -> None:
    mock_update.return_value = {
        "item": {"id": 1, "title": "updated"},
        "operation": "update",
    }
    node = ToolCallNode()
    config = {
        "operation": "update",
        "table_name": "products",
        "filters": {"id": 1},
        "data": {"title": "updated"},
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result["operation"] == "update"
    assert result["item"]["title"] == "updated"
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_toolcall_update_missing_id() -> None:
    node = ToolCallNode()
    config = {
        "operation": "update",
        "table_name": "products",
        "filters": {},
        "data": {"title": "updated"},
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result == {"error": "update requires filters.id"}


@pytest.mark.asyncio
@patch("app.services.ai.workflow.nodes.toolcall_node.delete_model")
async def test_toolcall_delete(mock_delete: MagicMock) -> None:
    mock_delete.return_value = {"operation": "delete", "id": 1}
    node = ToolCallNode()
    config = {
        "operation": "delete",
        "table_name": "products",
        "filters": {"id": 1},
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result["operation"] == "delete"
    assert result["id"] == 1
    mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_toolcall_delete_missing_id() -> None:
    node = ToolCallNode()
    config = {
        "operation": "delete",
        "table_name": "products",
        "filters": {},
    }
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result == {"error": "delete requires filters.id"}


@pytest.mark.asyncio
async def test_toolcall_unknown_operation() -> None:
    node = ToolCallNode()
    config = {"operation": "unknown_op", "table_name": "products"}
    context = {"tenant_id": 1}
    services = {"db": MagicMock()}
    result = await node.execute(config, context, services)
    assert result == {"error": "Unknown operation: unknown_op"}


# ── NODE_REGISTRY ────────────────────────────────────────────────────────────


def test_node_registry_contains_all_types() -> None:
    from app.services.ai.workflow.nodes import NODE_REGISTRY

    expected_types = {
        "start", "end", "llm", "kb", "condition", "human", "tool_call"
    }
    assert set(NODE_REGISTRY.keys()) == expected_types

    for node_type, node in NODE_REGISTRY.items():
        assert node.node_type == node_type
