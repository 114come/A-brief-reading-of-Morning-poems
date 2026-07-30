from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.knowledge_base.schemas import SearchResultItem
from app.services.ai.workflow.nodes.condition_node import ConditionNode
from app.services.ai.workflow.nodes.human_node import HumanReviewNode
from app.services.ai.workflow.nodes.kb_node import KBNode
from app.services.ai.workflow.nodes.llm_node import LLMNode
from app.services.ai.workflow.nodes.start_end import EndNode, StartNode


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


# ── NODE_REGISTRY ────────────────────────────────────────────────────────────


def test_node_registry_contains_all_types() -> None:
    from app.services.ai.workflow.nodes import NODE_REGISTRY

    expected_types = {"start", "end", "llm", "kb", "condition", "human"}
    assert set(NODE_REGISTRY.keys()) == expected_types

    for node_type, node in NODE_REGISTRY.items():
        assert node.node_type == node_type
