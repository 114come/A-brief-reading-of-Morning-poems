"""Agent tool implementation tests.

Tests for CalculatorTool and GetTimeTool which are stateless and registered
in the global ToolRegistry. LLMTool and KBTool require runtime dependency
injection and are tested separately via integration tests.

Lowcode CRUD tools (LowcodeQueryTool, LowcodeInsertTool, LowcodeUpdateTool,
LowcodeDeleteTool) require a DB session + tenant_id and are tested here using
an in-memory SQLite database.
"""

import re

import pytest
from sqlalchemy.orm import Session

from app.services.ai.agent_engine.tools.calculator import CalculatorTool
from app.services.ai.agent_engine.tools.get_time import GetTimeTool
from app.services.ai.agent_engine.tools.lowcode_tool import (
    LowcodeDeleteTool,
    LowcodeInsertTool,
    LowcodeQueryTool,
    LowcodeUpdateTool,
)
from app.services.model.models import DataModel


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


# ────────────────────────── Lowcode CRUD Tools ──────────────────────────


@pytest.fixture
def db_session() -> Session:
    """Create an in-memory SQLite session for lowcode tool tests."""
    from sqlalchemy import create_engine

    from app.core.database import Base

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def lowcode_models(db_session: Session) -> tuple[DataModel, type]:
    """Seed a DataModel + DataField row and create the dynamic table."""
    from app.services.model.generator import generate_sqlalchemy_model
    from app.services.model.models import DataField, DataModel

    model = DataModel(
        tenant_id=1,
        name="员工入职",
        table_name="employee_onboarding",
        description="员工入职登记表",
        json_schema='{"type":"object"}',
        status="published",
    )
    db_session.add(model)
    db_session.flush()

    fields = [
        DataField(
            model_id=model.id,
            name="name",
            label="姓名",
            field_type="string",
            db_column_type="VARCHAR(100)",
            sort_order=1,
        ),
        DataField(
            model_id=model.id,
            name="department",
            label="部门",
            field_type="string",
            db_column_type="VARCHAR(100)",
            sort_order=2,
        ),
        DataField(
            model_id=model.id,
            name="age",
            label="年龄",
            field_type="integer",
            db_column_type="BIGINT",
            sort_order=3,
        ),
    ]
    for f in fields:
        db_session.add(f)
    db_session.commit()

    DynamicModel = generate_sqlalchemy_model(model)
    from app.core.database import Base

    Base.metadata.create_all(bind=db_session.get_bind())

    return model, DynamicModel


@pytest.mark.asyncio
async def test_lowcode_query_no_records(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """Querying an empty table should return a 'not found' message."""
    tool = LowcodeQueryTool(db=db_session, tenant_id=1)
    result = await tool.execute(table_name="employee_onboarding")
    assert "未找到匹配的记录" in result


@pytest.mark.asyncio
async def test_lowcode_insert(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """Inserting a record should return success with the new ID."""
    _, DynamicModel = lowcode_models
    tool = LowcodeInsertTool(db=db_session, tenant_id=1)
    result = await tool.execute(
        table_name="employee_onboarding",
        data={"name": "张三", "department": "技术部", "age": 30},
    )
    assert "成功插入" in result
    assert "ID=1" in result

    # Verify the record is actually in the database
    record = db_session.query(DynamicModel).first()
    assert record is not None
    assert record.name == "张三"
    assert record.department == "技术部"


@pytest.mark.asyncio
async def test_lowcode_query_with_records(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """After inserting records, query returns them."""
    tool_ins = LowcodeInsertTool(db=db_session, tenant_id=1)
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "张三", "department": "技术部", "age": 30},
    )
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "李四", "department": "市场部", "age": 25},
    )

    tool_q = LowcodeQueryTool(db=db_session, tenant_id=1)
    result = await tool_q.execute(table_name="employee_onboarding")
    assert "2 条记录" in result
    assert "张三" in result
    assert "李四" in result


@pytest.mark.asyncio
async def test_lowcode_query_with_filters(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """Filtering should return only matching records."""
    tool_ins = LowcodeInsertTool(db=db_session, tenant_id=1)
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "张三", "department": "技术部", "age": 30},
    )
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "李四", "department": "市场部", "age": 25},
    )

    tool_q = LowcodeQueryTool(db=db_session, tenant_id=1)
    result = await tool_q.execute(
        table_name="employee_onboarding",
        filters={"department": "技术部"},
    )
    assert "1 条记录" in result
    assert "张三" in result
    assert "李四" not in result


@pytest.mark.asyncio
async def test_lowcode_update(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """Updating a record should change its values."""
    tool_ins = LowcodeInsertTool(db=db_session, tenant_id=1)
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "张三", "department": "技术部"},
    )

    tool_up = LowcodeUpdateTool(db=db_session, tenant_id=1)
    result = await tool_up.execute(
        table_name="employee_onboarding",
        record_id=1,
        data={"department": "市场部"},
    )
    assert "成功更新" in result

    _, DynamicModel = lowcode_models
    record = db_session.query(DynamicModel).filter_by(id=1).first()
    assert record is not None
    assert record.department == "市场部"


@pytest.mark.asyncio
async def test_lowcode_delete(
    db_session: Session, lowcode_models: tuple[DataModel, type]
) -> None:
    """Deleting a record should remove it from the database."""
    _, DynamicModel = lowcode_models
    tool_ins = LowcodeInsertTool(db=db_session, tenant_id=1)
    await tool_ins.execute(
        table_name="employee_onboarding",
        data={"name": "张三", "department": "技术部"},
    )

    tool_del = LowcodeDeleteTool(db=db_session, tenant_id=1)
    result = await tool_del.execute(
        table_name="employee_onboarding", record_id=1
    )
    assert "成功删除" in result

    record = db_session.query(DynamicModel).filter_by(id=1).first()
    assert record is None


@pytest.mark.asyncio
async def test_lowcode_table_not_found(db_session: Session) -> None:
    """Querying a non-existent table should return an error."""
    tool = LowcodeQueryTool(db=db_session, tenant_id=1)
    result = await tool.execute(table_name="nonexistent_table")
    assert result.startswith("错误")


@pytest.mark.asyncio
async def test_lowcode_schema() -> None:
    """All lowcode tools should produce valid OpenAI function-calling schemas."""
    # Schema can be generated without a DB session — purely class-level data
    for cls in (
        LowcodeQueryTool,
        LowcodeInsertTool,
        LowcodeUpdateTool,
        LowcodeDeleteTool,
    ):
        tool = cls(db=None, tenant_id=0)  # type: ignore[arg-type]
        schema = tool.openai_schema()
        assert schema["type"] == "function"
        assert isinstance(schema["function"]["name"], str)
        assert len(schema["function"]["name"]) > 0
        assert isinstance(schema["function"]["description"], str)
        assert len(schema["function"]["description"]) > 0
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "table_name" in params["properties"]
        assert "table_name" in params["required"]
