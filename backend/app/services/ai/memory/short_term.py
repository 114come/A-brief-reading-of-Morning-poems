import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.memory.repository import MemoryRepository

logger = logging.getLogger(__name__)


def _messages_to_text(messages: list[dict[str, str]]) -> str:
    """Format messages as 'role: content\\nrole: content\\n...'."""
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages)


class ShortTermMemory:
    """Short-term conversation memory backed by MySQL summaries."""

    def __init__(self, db: Session, ai_service: Any) -> None:
        self.db = db
        self.ai_service = ai_service
        self.repo = MemoryRepository(db)

    async def summarize_if_needed(
        self,
        tenant_id: int,
        agent_id: int,
        conv_id: int,
        messages: list[dict[str, str]],
        interval: int = 5,
    ) -> str | None:
        """Generate and store a summary when user message count is a multiple of *interval*.

        Returns the summary text if one was generated, or ``None`` if the interval
        condition was not met.
        """
        user_count = sum(1 for m in messages if m.get("role") == "user")
        if user_count == 0 or user_count % interval != 0:
            return None

        summary = await self._generate_summary(tenant_id, messages)
        self.repo.create(
            tenant_id=tenant_id,
            agent_id=agent_id,
            conversation_id=conv_id,
            memory_type="short_term_summary",
            content=summary,
        )
        return summary

    async def _generate_summary(
        self,
        tenant_id: int,
        messages: list[dict[str, str]],
    ) -> str:
        """Use the LLM to produce a concise conversation summary."""
        text = _messages_to_text(messages)
        prompt = (
            "Summarize the following conversation concisely, "
            "capturing key points and decisions:\n\n"
            f"{text}"
        )
        result = await self.ai_service.chat_completion(
            tenant_id=tenant_id,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return result["choices"][0]["message"]["content"]

    def get_recent(
        self,
        agent_id: int,
        conv_id: int,
        limit: int = 5,
    ) -> list[str]:
        """Retrieve recent summaries for a conversation."""
        memories = self.repo.list_by_agent_conv(
            agent_id=agent_id,
            conv_id=conv_id,
            memory_type="short_term_summary",
            limit=limit,
        )
        return [m.content for m in memories]
