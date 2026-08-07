"""用 free dictionary API 为缺失例句的单词补全 例句/音标/词性

幂等：只为 example/example2/phrase/pos 为空 且是考试核心词 的单词抓取。
API: https://api.dictionaryapi.dev （免费，无 key，限流需控制速率）
用法：cd backend && python scripts/enrich_examples.py [limit]
"""
import json
import subprocess
import sys
import time

import pymysql

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 2000


def fetch(word: str) -> dict | None:
    """用 curl 抓取（urllib 在本机 SSL 有问题）"""
    try:
        out = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15",
             f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"],
            capture_output=True, timeout=20,
        )
        out.stdout = out.stdout.decode("utf-8", errors="replace")
        data = json.loads(out.stdout)
        if not isinstance(data, list) or not data:
            return None
        entry = data[0]
        phonetic = entry.get("phonetic")
        pos_parts = []
        examples = []
        definitions = []
        for meaning in entry.get("meanings", []):
            p = meaning.get("partOfSpeech")
            if p and p not in pos_parts:
                pos_parts.append(p)
            for d in meaning.get("definitions", []):
                if d.get("example"):
                    examples.append(d["example"])
                if d.get("definition"):
                    definitions.append(d["definition"])
        return {
            "phonetic": phonetic,
            "pos": ("/".join(pos_parts))[:95] if pos_parts else None,
            "example": examples[0] if examples else None,
            "example2": examples[1] if len(examples) > 1 else None,
            "definition_en": definitions[0] if definitions else None,
        }
    except Exception:
        return None


def main() -> None:
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password="123456",
        database="lowcode_master", charset="utf8mb4", autocommit=True,
    )
    cur = conn.cursor()
    # 补缺例句的考试核心词（有音标/词性优先，说明是常见词）
    cur.execute(
        "SELECT id, word FROM english_words "
        "WHERE example IS NULL "
        "ORDER BY (pos IS NOT NULL) DESC, id LIMIT %s", (LIMIT,),
    )
    rows = cur.fetchall()
    print(f"words to enrich: {len(rows)}")
    if not rows:
        print("nothing to do")
        return

    updated = 0
    failed = 0
    for wid, word in rows:
        info = fetch(word)
        if not info:
            failed += 1
            continue
        sets = []
        params = []
        for col in ("example", "example2", "pos", "phonetic"):
            val = info.get(col)
            if val:
                sets.append(f"{col}=%s")
                params.append(val)
        if not sets:
            failed += 1
            continue
        params.append(wid)
        cur.execute(f"UPDATE english_words SET {', '.join(sets)} WHERE id=%s", params)
        updated += 1
        if updated % 50 == 0:
            print(f"  ...{updated} updated", flush=True)
        time.sleep(0.12)  # 限流

    conn.commit()
    print(f"DONE. updated={updated} failed={failed}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
