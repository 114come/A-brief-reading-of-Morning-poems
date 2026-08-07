"""用 free dictionary API 并发为缺失例句的单词补全 例句/音标/词性

并发 worker 大幅提速（API 支持并发请求）。
幂等：只为 example 为空的单词抓取。
用法：cd backend && python scripts/enrich_examples_concurrent.py [limit] [workers]
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pymysql

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 8

DB = dict(host="127.0.0.1", port=3306, user="root", password="123456",
          database="lowcode_master", charset="utf8mb4", autocommit=True)


def fetch(word: str) -> tuple[str, dict | None]:
    """抓取单个单词（带重试）；返回 (word, info or None)"""
    for attempt in range(3):
        try:
            out = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "15",
                 f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"],
                capture_output=True, timeout=20,
            )
            code = out.returncode
            if code == 0:
                break
            time.sleep(1 + attempt)
        except Exception:
            if attempt == 2:
                return word, None
            time.sleep(1 + attempt)
    try:
        data = json.loads(out.stdout.decode("utf-8", errors="replace"))
        if not isinstance(data, list) or not data:
            return word, None
        entry = data[0]
        phonetic = entry.get("phonetic")
        pos_parts = []
        examples = []
        for meaning in entry.get("meanings", []):
            p = meaning.get("partOfSpeech")
            if p and p not in pos_parts:
                pos_parts.append(p)
            for d in meaning.get("definitions", []):
                if d.get("example"):
                    examples.append(d["example"])
        info = {
            "phonetic": phonetic,
            "pos": ("/".join(pos_parts))[:95] if pos_parts else None,
            "example": examples[0] if examples else None,
            "example2": examples[1] if len(examples) > 1 else None,
        }
        return word, info
    except Exception:
        return word, None
        data = json.loads(out.stdout.decode("utf-8", errors="replace"))
        if not isinstance(data, list) or not data:
            return word, None
        entry = data[0]
        phonetic = entry.get("phonetic")
        pos_parts = []
        examples = []
        for meaning in entry.get("meanings", []):
            p = meaning.get("partOfSpeech")
            if p and p not in pos_parts:
                pos_parts.append(p)
            for d in meaning.get("definitions", []):
                if d.get("example"):
                    examples.append(d["example"])
        info = {
            "phonetic": phonetic,
            "pos": ("/".join(pos_parts))[:95] if pos_parts else None,
            "example": examples[0] if examples else None,
            "example2": examples[1] if len(examples) > 1 else None,
        }
        return word, info
    except Exception:
        return word, None


def main() -> None:
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    # 本轮目标：先补例句为 0 的 gre，再补覆盖不足的 ielts
    cur.execute(
        "SELECT w.id, w.word FROM english_words w "
        "JOIN word_books b ON w.book_id = b.id "
        "WHERE w.example IS NULL "
        "AND b.code IN ('gre','ielts') "
        "ORDER BY FIELD(b.code,'gre','ielts'), w.id "
        "LIMIT %s",
        (LIMIT,),
    )
    rows = cur.fetchall()
    print(f"words to enrich: {len(rows)}", flush=True)
    if not rows:
        print("nothing to do", flush=True)
        return
    conn.close()

    updated = 0
    failed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch, word): (wid, word) for wid, word in rows}
        for fut in as_completed(futures):
            wid, word = futures[fut]
            try:
                _word, info = fut.result()
            except Exception:
                info = None
            if not info or not info["example"]:
                failed += 1
                continue
            # 每个 worker 用独立连接更新，避免共享连接竞争
            conn = pymysql.connect(**DB)
            cur = conn.cursor()
            sets = ["example=%s"]
            params = [info["example"]]
            if info["example2"]:
                sets.append("example2=%s")
                params.append(info["example2"])
            if info["pos"]:
                sets.append("pos=%s")
                params.append(info["pos"])
            if info["phonetic"]:
                sets.append("phonetic=%s")
                params.append(info["phonetic"])
            params.append(wid)
            cur.execute(f"UPDATE english_words SET {', '.join(sets)} WHERE id=%s", params)
            conn.close()
            updated += 1
            if updated % 200 == 0:
                elapsed = time.time() - t0
                print(f"  ...{updated} updated in {elapsed:.0f}s", flush=True)

    print(f"DONE. updated={updated} failed={failed} elapsed={time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
