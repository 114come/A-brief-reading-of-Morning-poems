from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.memory.short_term import ShortTermMemory
from app.services.ai.memory.long_term import LongTermMemory
from app.services.ai.service import AIService


class MemoryCollector:
    """Orchestrates short-term summarization, long-term fact extraction,
    and context building for agent conversations."""

    def __init__(self, db: Session, ai_service: AIService) -> None:
        self.short_term = ShortTermMemory(db, ai_service)
        self.long_term = LongTermMemory(db, ai_service)

    async def collect(
        self,
        tenant_id: int,
        agent_id: int,
        conversation_id: int,
        messages: list[dict[str, Any]],
        interval: int = 5,
    ) -> None:
        """Trigger short-term summarization if the message interval is met."""
        await self.short_term.summarize_if_needed(
            tenant_id, agent_id, conversation_id, messages, interval,
        )

    async def collect_long_term(
        self,
        tenant_id: int,
        agent_id: int,
        conversation_id: int,
        messages: list[dict[str, Any]],
    ) -> None:
        """Extract and store long-term facts from a conversation turn."""
        await self.long_term.extract_and_store(
            tenant_id, agent_id, conversation_id, messages,
        )

    def build_context(
        self,
        tenant_id: int,
        agent_id: int,
        conversation_id: int,
        query: str,
    ) -> str:
        """Combine long-term facts and short-term summaries into a
        context string for the LLM."""
        try:
            parts: list[str] = []
            facts = self.long_term.search(tenant_id, agent_id, query)
            if facts:
                parts.append("【相关记忆】\n" + "\n".join(f"- {f}" for f in facts))
            summaries = self.short_term.get_recent(agent_id, conversation_id)
            if summaries:
                parts.append("【历史摘要】\n" + "\n".join(f"- {s}" for s in summaries))
            return "\n\n".join(parts)
        except Exception:
            return ""
