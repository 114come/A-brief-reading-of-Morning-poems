from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.models import LLMProvider


class LLMProviderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> LLMProvider:
        provider = LLMProvider(**kwargs)
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def get_by_id(self, provider_id: int) -> LLMProvider | None:
        return self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()

    def list_by_tenant(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> list[LLMProvider]:
        return (
            self.db.query(LLMProvider)
            .filter(LLMProvider.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_active_by_tenant(self, tenant_id: int) -> list[LLMProvider]:
        return (
            self.db.query(LLMProvider)
            .filter(
                LLMProvider.tenant_id == tenant_id,
                LLMProvider.is_active == True,  # noqa: E712
            )
            .order_by(LLMProvider.priority.asc())
            .all()
        )

    def update(self, provider_id: int, **kwargs: Any) -> LLMProvider | None:
        provider = self.get_by_id(provider_id)
        if not provider:
            return None
        for key, value in kwargs.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def delete(self, provider_id: int) -> bool:
        provider = self.get_by_id(provider_id)
        if not provider:
            return False
        self.db.delete(provider)
        self.db.commit()
        return True
