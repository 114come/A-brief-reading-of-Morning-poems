from abc import ABC, abstractmethod
from typing import Any


class BaseNode(ABC):
    """Abstract base for all workflow node types."""

    node_type: str = ""

    @abstractmethod
    async def execute(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
        services: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the node and return its output dict."""
        ...
