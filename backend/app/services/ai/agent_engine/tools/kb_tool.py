from typing import Any

from app.services.ai.agent_engine.tools.base import BaseTool
from app.services.ai.knowledge_base.schemas import SearchRequest
from app.services.ai.knowledge_base.service import KnowledgeBaseService


class KBTool(BaseTool):
    """知识库搜索工具：从知识库中检索相关文档片段"""

    name = "kb_search"
    description = "在知识库中搜索与查询相关的文档内容，返回匹配的文本片段及来源文档名称"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "kb_id": {
                "type": "integer",
                "description": "知识库 ID",
            },
            "query": {
                "type": "string",
                "description": "搜索查询语句",
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量上限，默认为 3",
                "default": 3,
            },
        },
        "required": ["kb_id", "query"],
    }

    def __init__(
        self,
        kb_service: KnowledgeBaseService,
        tenant_id: int,
    ) -> None:
        self._kb_service = kb_service
        self._tenant_id = tenant_id

    async def execute(self, **kwargs: Any) -> str:
        kb_id: int = kwargs.get("kb_id", 0)
        query: str = kwargs.get("query", "")
        top_k: int = kwargs.get("top_k", 3)

        if not query.strip():
            return "错误：搜索查询不能为空"
        if not kb_id:
            return "错误：必须指定知识库 ID"

        req = SearchRequest(query=query, top_k=top_k)
        results = self._kb_service.search(
            tenant_id=self._tenant_id,
            kb_id=kb_id,
            req=req,
        )

        if not results:
            return f"在知识库 (ID={kb_id}) 中未找到与「{query}」相关的结果"

        lines = [f"在知识库中找到 {len(results)} 条相关结果："]
        for i, item in enumerate(results, 1):
            lines.append(
                f"\n--- 结果 {i} ---\n"
                f"文档：{item.doc_name}\n"
                f"相关度：{item.score:.4f}\n"
                f"内容：{item.content}\n"
            )
        return "\n".join(lines)
