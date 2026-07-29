import ast
from typing import Any

from app.services.ai.agent_engine.tools.base import BaseTool


# 安全数学运算允许的 AST 节点类型集合
_ALLOWED_NODES: tuple = (
    ast.Expression,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)


def safe_eval(expression: str) -> float | int:
    """使用 AST 安全解析并求值数学表达式。

    仅支持：
      - 四则运算：+, -, *, /, //
      - 取模：%
      - 幂运算：**
      - 一元正负号：+x, -x
      - 数字常量（整数和浮点数）

    不支持函数调用、变量、属性访问等任何可能产生副作用的语法。
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"表达式语法错误: {e}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(
                f"不支持的语法成分: {type(node).__name__}。"
                f"仅支持四则运算、取模和幂运算。"
            )
        # 确保常量均为数字类型，阻止字符串或其他非数值常量
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(
                f"不支持的常量类型: {type(node.value).__name__}。仅支持数字常量。"
            )

    # 空内置环境编译执行，杜绝任意代码执行
    code = compile(tree, "<string>", "eval")
    result = eval(code, {"__builtins__": {}}, {})  # noqa: S307
    return result


class CalculatorTool(BaseTool):
    """数学计算器工具：安全地计算数学表达式"""

    name = "calculator"
    description = "安全计算数学表达式，支持加(+)、减(-)、乘(*)、除(/)、整除(//)、取模(%)和幂(**)"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式，例如 \"(3 + 5) * 2\"",
            },
        },
        "required": ["expression"],
    }

    async def execute(self, **kwargs: Any) -> str:
        expression: str = kwargs.get("expression", "")
        if not expression.strip():
            return "错误：表达式不能为空"

        try:
            result = safe_eval(expression)
            # 整数则返回整数字符串，浮点数则去除末尾多余的 0
            if isinstance(result, float):
                formatted = f"{result:g}"
            else:
                formatted = str(result)
            return formatted
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e:
            return f"错误：{e}"
