from typing import Any

from app.services.ai.knowledge_base.schemas import SearchRequest
from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.template import render_template


class KBNode(BaseNode):
    """Node that searches a knowledge base via KnowledgeBaseService.search."""

    node_type = "kb"

    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        query_template: str = config.get("query", "")
        query = render_template(query_template, context)

        kb_service = services.get("kb_service")
        if kb_service is None:
            raise ValueError("kb_service is required for KBNode")

        tenant_id: int = context.get("tenant_id", 0)
        kb_id: int = config.get("kb_id", 0)
        top_k: int = config.get("top_k", 5)

        req = SearchRequest(query=query, top_k=top_k)
        results = kb_service.search(
            tenant_id=tenant_id, kb_id=kb_id, req=req
        )

        return {
            "results": [
                {
                    "doc_name": r.doc_name,
                    "content": r.content,
                    "score": r.score,
                }
                for r in results
            ]
        }
