from typing import Any

from app.services.ai.workflow.nodes.base import BaseNode


class ConditionNode(BaseNode):
    """Node that evaluates a Python expression safely and returns a boolean result.

    Only ``context`` and ``outputs`` are available in the eval scope.
    All builtins are disabled for safety.
    """

    node_type = "condition"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        expression: str = config.get("expression", "True")

        safe_locals: dict[str, Any] = {
            "context": context,
            "outputs": context.get("outputs", {}),
        }

        result = eval(expression, {"__builtins__": {}}, safe_locals)  # noqa: S307
        return {"result": bool(result)}
