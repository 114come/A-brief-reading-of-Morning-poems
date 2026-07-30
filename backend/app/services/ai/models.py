from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMProvider(Base):
    """LLM 提供商配置（主库，按租户隔离）"""

    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="openai",
        comment="openai | claude | wenxin | qianwen | custom",
    )
    api_base: Mapped[str] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    models: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]",
        comment="JSON 数组，如 [\"gpt-4\", \"gpt-3.5-turbo\"]",
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
