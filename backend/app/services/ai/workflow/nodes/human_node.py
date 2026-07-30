from typing import Any

from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.template import render_template


class HumanReviewNode(BaseNode):
    """Node that pauses execution for human review."""

    node_type = "human"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        instructions_template: str = config.get("instructions", "")
        instructions = render_template(instructions_template, context)

        return {
            "status": "pending",
            "instructions": instructions,
            "assignee_role": config.get("assignee_role", ""),
        }
