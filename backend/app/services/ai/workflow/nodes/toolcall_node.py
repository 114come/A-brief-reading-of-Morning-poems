import json
from typing import Any

from app.services.ai.lowcode_tools import (
    delete_model,
    get_model_definition,
    insert_model,
    query_model,
    update_model,
)
from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.template import render_template


class ToolCallNode(BaseNode):
    """调用低代码动态 CRUD 工具节点"""

    node_type = "tool_call"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        operation = config.get("operation", "query")  # query / insert / update / delete
        table_name = render_template(config.get("table_name", ""), context)
        filters_str = render_template(
            json.dumps(config.get("filters", {})), context
        )
        data_str = render_template(json.dumps(config.get("data", {})), context)

        try:
            filters = (
                json.loads(filters_str)
                if isinstance(filters_str, str)
                else config.get("filters", {})
            )
            data = (
                json.loads(data_str)
                if isinstance(data_str, str)
                else config.get("data", {})
            )
        except json.JSONDecodeError:
            return {"error": "JSON parse error in config"}

        db = services.get("db")
        if not db:
            return {"error": "Database not available"}

        try:
            model_def = get_model_definition(
                db, table_name, context.get("tenant_id", 1)
            )
            if not model_def:
                return {"error": f"Table '{table_name}' not found"}

            if operation == "query":
                items, count = query_model(
                    db, model_def, filters, config.get("limit", 50)
                )
                return {"items": items, "count": count}

            elif operation == "insert":
                return insert_model(db, model_def, data)

            elif operation == "update":
                item_id = filters.get("id")
                if not item_id:
                    return {"error": "update requires filters.id"}
                return update_model(db, model_def, item_id, data)

            elif operation == "delete":
                item_id = filters.get("id")
                if not item_id:
                    return {"error": "delete requires filters.id"}
                return delete_model(db, model_def, item_id)

            return {"error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"error": str(e)}
