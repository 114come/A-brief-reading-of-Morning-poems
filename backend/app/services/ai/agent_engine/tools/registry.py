from typing import Any

from app.services.ai.agent_engine.tools.base import BaseTool


class ToolRegistry:
    """全局工具注册中心"""

    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        return cls._tools.get(name)

    @classmethod
    def get_enabled(cls, names: list[str]) -> list[BaseTool]:
        return [t for n, t in cls._tools.items() if n in names]

    @classmethod
    def all_schemas(cls, names: list[str]) -> list[dict[str, Any]]:
        return [t.openai_schema() for t in cls.get_enabled(names)]
