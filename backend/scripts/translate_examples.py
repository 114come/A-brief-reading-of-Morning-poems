"""批量翻译英文例句为中文（题型E例句填空用）

读取 llm_providers 表中优先级最高的国内 provider（deepseek/qwen/wenxin/custom，
兼容 OpenAI 接口），对 example/example2 已有但 example_cn/example2_cn 为空
的单词批量翻译。幂等、增量、限速。

前置：先通过 POST /api/v1/llm/providers 配置一个国内 LLM provider（english 租户）。
用法：cd backend && python scripts/translate_examples.py [limit]
"""
import asyncio
import json
import os
import sys

# 确保 backend 根目录在 sys.path（脚本位于 backend/scripts/ 下）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

from app.core.database import MasterSessionLocal
from app.core.security import decrypt_api_key
from app.services.ai.models import LLMProvider
from app.services.ai.service import PROVIDER_ADAPTERS

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 500
BATCH = 15  # 每批翻译条数
TRANSLATE_SYSTEM = (
    "你是专业的英译中翻译助手。把用户给出的英文例句逐条翻译成自然、准确的中文。"
    "只输出 JSON 数组，每个元素是 {index: 原序号, text: 中文翻译}，不要输出其他内容。"
)


def get_configured_provider(db) -> tuple[LLMProvider, type] | None:
    """优先用 .env 配置的 LLM；否则找 english 租户下优先级最高的国内 provider"""
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

    from app.core.config import settings

    if settings.LLM_API_KEY:
        # 用 .env 配置构造 provider
        provider = LLMProvider(
            id=0, tenant_id=0, name="env-llm",
            provider_type=settings.LLM_PROVIDER_TYPE,
            api_base=settings.LLM_BASE_URL or None,
            api_key_encrypted=settings.LLM_API_KEY,  # 脚本里直接明文用
            models=settings.LLM_MODEL,  # 单模型
            priority=0, is_active=True,
        )
        adapter_cls = PROVIDER_ADAPTERS.get(settings.LLM_PROVIDER_TYPE)
        if adapter_cls:
            return provider, adapter_cls

    from app.services.tenant.repository import TenantRepository

    tenant = TenantRepository(db).get_by_code("english")
    if not tenant:
        return None
    providers = (
        db.query(LLMProvider)
        .filter(LLMProvider.tenant_id == tenant.id, LLMProvider.is_active == True)  # noqa: E712
        .order_by(LLMProvider.priority)
        .all()
    )
    for p in providers:
        adapter_cls = PROVIDER_ADAPTERS.get(p.provider_type)
        if adapter_cls and p.provider_type in ("deepseek", "qwen", "wenxin", "custom", "openai"):
            return p, adapter_cls
    return None


async def translate_batch(provider: LLMProvider, adapter_cls: type, sentences: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """批量翻译一条例句；返回 (word_id, 原文, 中文)"""
    if not sentences:
        return []
    # env provider 的 key 是明文；DB provider 的 key 是加密的
    from app.core.config import settings

    if provider.id == 0 and settings.LLM_API_KEY:
        api_key = settings.LLM_API_KEY
    else:
        api_key = decrypt_api_key(provider.api_key_encrypted)
    adapter = adapter_cls(api_key=api_key, api_base=provider.api_base)
    # model: DB 里是 JSON 数组字符串（["deepseek-chat"]），env 里是裸字符串（deepseek-chat）
    if provider.models:
        try:
            parsed = json.loads(provider.models)
            model = parsed[0] if isinstance(parsed, list) and parsed else str(provider.models)
        except (json.JSONDecodeError, TypeError):
            model = str(provider.models)
    else:
        model = ""
    if not model:
        return []
    # 组装 user 消息：每行 "序号. 英文"（序号 1..N）
    prompt_lines = [f"{i}. {s}" for i, (_wid, s) in enumerate(sentences, start=1)]
    try:
        result = await adapter.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {"role": "user", "content": "\n".join(prompt_lines)},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        # adapter 返回 OpenAI 格式 {choices:[{message:{content}}]}
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = result.get("content") or result.get("message", {}).get("content", "")
        # 提取 JSON 数组
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            return []
        arr = json.loads(content[start : end + 1])
        by_idx = {int(item["index"]): item["text"] for item in arr if "index" in item and "text" in item}
        out = []
        for i, (wid, sent) in enumerate(sentences, start=1):
            if i in by_idx and by_idx[i]:
                out.append((wid, sent, by_idx[i]))
        return out
    except Exception as e:
        print(f"  translate error: {e}", flush=True)
        return []


async def main_async() -> None:
    db = MasterSessionLocal()
    try:
        cfg = get_configured_provider(db)
        if not cfg:
            print("未配置国内 LLM provider！请先通过 /api/v1/llm/providers 配置（english 租户）。", flush=True)
            return
        provider, adapter_cls = cfg
        print(f"使用 provider: {provider.name} ({provider.provider_type})", flush=True)

        # 取需要翻译的词（example_cn 为空但有例句），限速控制总量
        from sqlalchemy import text

        sql = text("""
            SELECT id, example, example2 FROM english_words
            WHERE example IS NOT NULL AND example != ''
              AND (example_cn IS NULL OR example2_cn IS NULL)
            LIMIT :lim
        """)
        rows = db.execute(sql, {"lim": LIMIT}).fetchall()
        print(f"待翻译单词: {len(rows)}", flush=True)

        n = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            sentences = []
            for r in batch:
                wid, ex1, ex2 = r[0], r[1], r[2]
                if ex1:
                    sentences.append((wid, ex1))
                if ex2:
                    sentences.append((wid, ex2))
            results = await translate_batch(provider, adapter_cls, sentences)
            # 按 word_id 分组写回（example→example_cn，example2→example2_cn）
            for wid, orig, cn in results:
                col = "example_cn"
                for r in batch:
                    _wid, _e1, _e2 = r[0], r[1], r[2]
                    if _wid == wid and orig == _e2:
                        col = "example2_cn"
                        break
                db.execute(text(f"UPDATE english_words SET {col}=:cn WHERE id=:wid"), {"cn": cn, "wid": wid})
            db.commit()
            n += len(results)
            print(f"  ...已翻译 {n} 条 ({i+BATCH}/{len(rows)})", flush=True)
            await asyncio.sleep(0.5)  # 国内 LLM 限速

        print(f"DONE. 翻译 {n} 条例句。", flush=True)
    finally:
        db.close()


def main() -> None:
    # 确保可以从 backend 目录导入 app
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
