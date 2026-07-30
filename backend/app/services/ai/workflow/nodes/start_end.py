from typing import Any

from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.template import render_template


class StartNode(BaseNode):
    """Entry-point node that returns the workflow input."""

    node_type = "start"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        return dict(context.get("input", {}))


class EndNode(BaseNode):
    """Terminal node that renders output_mapping templates into the final result."""

    node_type = "end"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        output_mapping: dict[str, str] = config.get("output_mapping", {})
        result: dict[str, Any] = {}
        for key, tmpl in output_mapping.items():
            result[key] = render_template(tmpl, context)
        return result
