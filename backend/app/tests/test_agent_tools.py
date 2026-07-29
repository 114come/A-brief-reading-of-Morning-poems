import pytest
from typing import Any

from app.services.ai.agent_engine.tools import BaseTool, ToolRegistry


class EchoTool(BaseTool):
    """测试用工具：回显输入"""
    name = "echo"
    description = "Echo back the input message"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Message to echo"}
        },
        "required": ["message"],
    }

    async def execute(self, **kwargs: Any) -> str:
        return kwargs.get("message", "")


class AddTool(BaseTool):
    """测试用工具：两数相加"""
    name = "add"
    description = "Add two numbers"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    }

    async def execute(self, **kwargs: Any) -> str:
        return str(kwargs.get("a", 0) + kwargs.get("b", 0))


@pytest.mark.asyncio
async def test_base_tool_openai_schema() -> None:
    """Verify openai_schema returns correct function calling format and execute works."""
    tool = EchoTool()
    schema = tool.openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"
    assert schema["function"]["description"] == "Echo back the input message"
    assert "parameters" in schema["function"]

    # Also verify execute works
    result = await tool.execute(message="hello")
    assert result == "hello"

    result = await tool.execute(message="world")
    assert result == "world"


def test_tool_registry_register_and_get() -> None:
    """Verify register and get methods."""
    ToolRegistry._tools.clear()

    tool = EchoTool()
    ToolRegistry.register(tool)

    retrieved = ToolRegistry.get("echo")
    assert retrieved is tool

    missing = ToolRegistry.get("nonexistent")
    assert missing is None


def test_tool_registry_get_enabled() -> None:
    """Verify get_enabled filters by name list."""
    ToolRegistry._tools.clear()

    ToolRegistry.register(EchoTool())
    ToolRegistry.register(AddTool())

    enabled = ToolRegistry.get_enabled(["echo"])
    assert len(enabled) == 1
    assert enabled[0].name == "echo"

    enabled = ToolRegistry.get_enabled(["echo", "add"])
    assert len(enabled) == 2

    enabled = ToolRegistry.get_enabled(["nonexistent"])
    assert len(enabled) == 0


def test_tool_registry_all_schemas() -> None:
    """Verify all_schemas returns list of schemas for enabled tools."""
    ToolRegistry._tools.clear()

    ToolRegistry.register(EchoTool())
    ToolRegistry.register(AddTool())

    schemas = ToolRegistry.all_schemas(["echo", "add"])
    assert len(schemas) == 2

    names = [s["function"]["name"] for s in schemas]
    assert "echo" in names
    assert "add" in names
