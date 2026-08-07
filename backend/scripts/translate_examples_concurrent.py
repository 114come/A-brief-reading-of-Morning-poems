"""批量翻译英文例句为中文（并发版，题型E例句填空用）

并发 worker 逐句翻译（不批量等全部），单句超时 20s，失败跳过不阻塞。
读取 .env 的 LLM_API_KEY/BASE_URL/MODEL（国内模型，OpenAI 兼容）。
幂等：example_cn 已有则跳过；可中断续跑。
用法：cd backend && python scripts/translate_examples_concurrent.py [limit] [workers]
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 6

DB = dict(host="127.0.0.1", port=3306, user="root", password="123456",
          database="lowcode_master", charset="utf8mb4", autocommit=True)

SYSTEM = "你是专业的英译中翻译助手。把用户给出的英文例句翻译成自然、准确的中文。只输出JSON数组，每元素 {index, text}。"


def fetch_translation(api_key: str, base_url: str, model: str, index: int, sentence: str) -> tuple[int, str, str]:
    """翻译单句；返回 (index, 原句, 中文)。失败返回 (index, 原句, '')"""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"1. {sentence}"},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    })
    url = (base_url or "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions"
    try:
        out = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "20", url,
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {api_key}",
             "-d", body],
            capture_output=True, timeout=25,
        )
        data = json.loads(out.stdout.decode("utf-8", errors="replace"))
        content = data["choices"][0]["message"]["content"]
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1:
            return index, sentence, ""
        arr = json.loads(content[start : end + 1])
        text = arr[0].get("text", "") if arr else ""
        return index, sentence, text
    except Exception:
        return index, sentence, ""


def main() -> None:
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, example, example2 FROM english_words "
        "WHERE example IS NOT NULL AND example != '' "
        "AND (example_cn IS NULL OR example2_cn IS NULL) LIMIT %s",
        (LIMIT,),
    )
    rows = cur.fetchall()
    print(f"待翻译单词: {len(rows)}", flush=True)
    if not rows:
        print("nothing to do", flush=True)
        return
    conn.close()

    # 确保从 backend/.env 读取（脚本可能从任意 cwd 运行）
    from dotenv import load_dotenv

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(backend_dir, ".env"))

    from app.core.config import settings

    api_key = settings.LLM_API_KEY
    base_url = settings.LLM_BASE_URL
    model = settings.LLM_MODEL
    if not api_key or not model:
        print("请先在 .env 配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL", flush=True)
        return

    # 构造任务列表：(word_id, 原始例句, 是example还是example2)
    tasks = []
    for wid, ex1, ex2 in rows:
        if ex1:
            tasks.append((wid, ex1, "example_cn"))
        if ex2:
            tasks.append((wid, ex2, "example2_cn"))
    print(f"共 {len(tasks)} 条例句待翻译", flush=True)

    updated = 0
    failed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {}
        for idx, (wid, sent, col) in enumerate(tasks):
            futures[pool.submit(fetch_translation, api_key, base_url, model, idx, sent)] = (wid, sent, col)
        for fut in as_completed(futures):
            wid, sent, col = futures[fut]
            try:
                _idx, _sent, cn = fut.result()
            except Exception:
                cn = ""
            if not cn:
                failed += 1
                continue
            conn = pymysql.connect(**DB)
            cur = conn.cursor()
            cur.execute(f"UPDATE english_words SET {col}=%s WHERE id=%s", (cn, wid))
            conn.close()
            updated += 1
            if updated % 200 == 0:
                print(f"  ...已翻译 {updated} 条 ({time.time()-t0:.0f}s)", flush=True)

    print(f"DONE. 翻译 {updated} 条例句, 失败 {failed}, 耗时 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
