import json
import logging
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.core.security import decrypt_api_key, encrypt_api_key
from app.services.ai.models import LLMProvider
from app.services.ai.providers import ClaudeAdapter, OpenAIAdapter
from app.services.ai.providers.base import BaseLLMProvider
from app.services.ai.repository import LLMProviderRepository
from app.services.ai.schemas import LLMProviderCreate, LLMProviderUpdate

logger = logging.getLogger(__name__)

# 提供商类型 → 适配器类映射
PROVIDER_ADAPTERS: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIAdapter,
    "wenxin": OpenAIAdapter,  # 文心兼容 OpenAI 接口
    "qianwen": OpenAIAdapter,  # 通义兼容 OpenAI 接口
    "custom": OpenAIAdapter,
    "claude": ClaudeAdapter,
}


class AIService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.provider_repo = LLMProviderRepository(db)

    # ─── Provider CRUD ──────────────────────────────────────────

    def create_provider(self, tenant_id: int, data: LLMProviderCreate) -> LLMProvider:
        provider = self.provider_repo.create(
            tenant_id=tenant_id,
            name=data.name,
            provider_type=data.provider_type,
            api_base=data.api_base,
            api_key_encrypted=encrypt_api_key(data.api_key),
            models=json.dumps(data.models),
            priority=data.priority,
            is_active=data.is_active,
        )
        return provider

    def update_provider(
        self, tenant_id: int, provider_id: int, data: LLMProviderUpdate
    ) -> LLMProvider:
        provider = self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValidationException("提供商不存在")
        if provider.tenant_id != tenant_id:
            raise ValidationException("无权操作此提供商")

        update_kw: dict[str, Any] = {}
        if data.name is not None:
            update_kw["name"] = data.name
        if data.provider_type is not None:
            update_kw["provider_type"] = data.provider_type
        if data.api_base is not None:
            update_kw["api_base"] = data.api_base
        if data.api_key is not None:
            update_kw["api_key_encrypted"] = encrypt_api_key(data.api_key)
        if data.models is not None:
            update_kw["models"] = json.dumps(data.models)
        if data.priority is not None:
            update_kw["priority"] = data.priority
        if data.is_active is not None:
            update_kw["is_active"] = data.is_active

        updated = self.provider_repo.update(provider_id, **update_kw)
        if not updated:
            raise ValidationException("更新失败")
        return updated

    def delete_provider(self, tenant_id: int, provider_id: int) -> None:
        provider = self.provider_repo.get_by_id(provider_id)
        if not provider:
            raise ValidationException("提供商不存在")
        if provider.tenant_id != tenant_id:
            raise ValidationException("无权操作此提供商")
        self.provider_repo.delete(provider_id)

    def get_provider(self, provider_id: int) -> LLMProvider | None:
        return self.provider_repo.get_by_id(provider_id)

    def list_providers(self, tenant_id: int) -> list[LLMProvider]:
        return self.provider_repo.list_by_tenant(tenant_id)

    # ─── LLM 调用 ───────────────────────────────────────────────

    def _get_adapter(self, provider: LLMProvider) -> BaseLLMProvider:
        """根据 provider 类型创建适配器实例"""
        adapter_cls = PROVIDER_ADAPTERS.get(provider.provider_type)
        if not adapter_cls:
            raise ValidationException(f"不支持的提供商类型: {provider.provider_type}")
        api_key = decrypt_api_key(provider.api_key_encrypted)
        models_list: list[str] = json.loads(provider.models) if provider.models else []
        api_base = provider.api_base
        return adapter_cls(api_key=api_key, api_base=api_base)

    def _find_provider_for_model(
        self, tenant_id: int, model: str
    ) -> LLMProvider:
        """根据模型名称查找可用的提供商（按优先级排序，支持 fallback）"""
        providers = self.provider_repo.list_active_by_tenant(tenant_id)
        if not providers:
            raise ValidationException("没有可用的 LLM 提供商，请先配置")

        # 优先匹配模型名
        for p in providers:
            models_list: list[str] = json.loads(p.models) if p.models else []
            if model in models_list:
                return p

        # fallback: 返回第一个活跃提供商
        logger.warning("模型 %s 未找到精确匹配，使用默认提供商", model)
        return providers[0]

    async def chat_completion(
        self,
        tenant_id: int,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """非流式对话补全"""
        provider = self._find_provider_for_model(tenant_id, model)
        adapter = self._get_adapter(provider)
        try:
            return await adapter.chat_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.exception("LLM 调用失败: provider=%s, model=%s", provider.name, model)
            raise ValidationException(f"LLM 调用失败: {e}") from e

    async def chat_completion_stream(
        self,
        tenant_id: int,
        model: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """流式对话补全"""
        provider = self._find_provider_for_model(tenant_id, model)
        adapter = self._get_adapter(provider)
        try:
            async for chunk in adapter.chat_completion_stream(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
        except Exception as e:
            logger.exception("LLM 流式调用失败: provider=%s, model=%s", provider.name, model)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
