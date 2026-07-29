"""Redis-backed session memory for agent conversations.

Stores conversation message history in Redis lists with TTL-based expiration.
Key format: ``agent:session:{conversation_id}``
"""

from __future__ import annotations

import json
from typing import Any

import redis as redis_lib

from app.core.config import settings

_REDIS_CLIENT: redis_lib.Redis | None = None


def get_redis_client() -> redis_lib.Redis:
    """Return a lazy-singleton Redis client using the global ``settings.REDIS_URL``."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis_lib.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _REDIS_CLIENT


def _key(conversation_id: int) -> str:
    return f"agent:session:{conversation_id}"


class SessionMemory:
    """Manage conversation message history in a Redis list.

    Each element is a JSON-encoded message dict.  The list is kept in FIFO
    order (newest at the tail).  A TTL is set on every write operation to
    keep the key from living past ``settings.AGENT_SESSION_TTL``.
    """

    def __init__(self, conversation_id: int, redis_client: redis_lib.Redis | None = None) -> None:
        self.conversation_id = conversation_id
        self._redis = redis_client or get_redis_client()

    # -- public helpers -------------------------------------------------------

    def push_message(self, role: str, content: str, name: str | None = None) -> None:
        """Append a single message to the session history.

        Parameters
        ----------
        role:
            Message role (e.g. ``"user"``, ``"assistant"``, ``"system"``).
        content:
            Message text content.
        name:
            Optional tool name (for tool role messages).
        """
        message: dict[str, Any] = {"role": role, "content": content}
        if name:
            message["name"] = name
        self._redis.rpush(_key(self.conversation_id), json.dumps(message, ensure_ascii=False))
        self._redis.expire(_key(self.conversation_id), settings.AGENT_SESSION_TTL)

    def get_history(self) -> list[dict[str, Any]]:
        """Return all messages in FIFO order as parsed dicts."""
        raw = self._redis.lrange(_key(self.conversation_id), 0, -1)
        return [json.loads(item) for item in raw]

    def clear(self) -> None:
        """Delete the entire session history for this conversation."""
        self._redis.delete(_key(self.conversation_id))

    def trim(self, max_messages: int = 200) -> None:
        """Keep only the most recent *max_messages* messages, discarding older ones.

        Operates as a FIFO trim: the head of the list (oldest messages) is
        removed so that only the tail remains.
        """
        current_len = self._redis.llen(_key(self.conversation_id))
        if current_len > max_messages:
            self._redis.ltrim(_key(self.conversation_id), current_len - max_messages, -1)
        self._redis.expire(_key(self.conversation_id), settings.AGENT_SESSION_TTL)
