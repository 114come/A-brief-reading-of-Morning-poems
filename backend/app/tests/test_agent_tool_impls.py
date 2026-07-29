"""Agent tool implementation tests.

Tests for CalculatorTool and GetTimeTool which are stateless and registered
in the global ToolRegistry. LLMTool and KBTool require runtime dependency
injection and are tested separately via integration tests.
"""

import re

import pytest

from app.services.ai.agent_engine.tools.calculator import CalculatorTool
from app.services.ai.agent_engine.tools.get_time import GetTimeTool


# ──────────────────────────── CalculatorTool ────────────────────────────


@pytest.mark.asyncio
async def test_calculator_addition() -> None:
    """Simple addition should return the correct sum."""
    tool = CalculatorTool()
    result = await tool.execute(expression="3 + 5")
    assert result == "8"

    result = await tool.execute(expression="10 + 20 + 30")
    assert result == "60"


@pytest.mark.asyncio
async def test_calculator_complex() -> None:
    """Complex expressions with mixed operators should evaluate correctly."""
    tool = CalculatorTool()
    result = await tool.execute(expression="(3 + 5) * 2")
    assert result == "16"

    result = await tool.execute(expression="10 / 3")
    # Allow "3.33333" variants
    assert float(result) == pytest.approx(3.33333, rel=1e-4)

    result = await tool.execute(expression="2 ** 10")
    assert result == "1024"

    result = await tool.execute(expression="17 % 5")
    assert result == "2"

    result = await tool.execute(expression="100 // 7")
    assert result == "14"

    result = await tool.execute(expression="-5 + 3")
    assert result == "-2"


@pytest.mark.asyncio
async def test_calculator_invalid() -> None:
    """Invalid expressions should return error messages, not raise exceptions."""
    tool = CalculatorTool()

    # Empty expression
    result = await tool.execute(expression="")
    assert result.startswith("错误")

    # Syntax error
    result = await tool.execute(expression="3 + +")
    assert result.startswith("错误")

    # Using functions/variable names (potentially unsafe)
    result = await tool.execute(expression="__import__('os')")
    assert result.startswith("错误")

    result = await tool.execute(expression="open('/etc/passwd')")
    assert result.startswith("错误")

    # Using strings
    result = await tool.execute(expression="'hello' + ' world'")
    assert result.startswith("错误")

    # Using attributes
    result = await tool.execute(expression="(3).__class__")
    assert result.startswith("错误")


@pytest.mark.asyncio
async def test_calculator_tool_schema() -> None:
    """CalculatorTool.openai_schema() should return valid function-calling schema."""
    tool = CalculatorTool()
    schema = tool.openai_schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "calculator"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]

    params = schema["function"]["parameters"]
    assert params["type"] == "object"
    assert "expression" in params["properties"]
    assert params["properties"]["expression"]["type"] == "string"
    assert "expression" in params["required"]

    # Also verify name/description match
    assert tool.name == "calculator"
    assert tool.description


# ────────────────────────────── GetTimeTool ──────────────────────────────


@pytest.mark.asyncio
async def test_get_time() -> None:
    """GetTimeTool should return current Beijing time in the expected format."""
    tool = GetTimeTool()
    result = await tool.execute()

    # Pattern: YYYY-MM-DD HH:mm:ss (星期X)
    pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \([星期一二三四五六日]+\)$"
    assert re.match(pattern, result), f"Unexpected format: {result}"

    # Verify name and description exist
    assert tool.name == "get_time"
    assert tool.description
