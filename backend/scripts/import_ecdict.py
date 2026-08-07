"""从 ECDICT 开源词库导入各级别全部单词（MIT 协议，数据源 skywind3000/ECDICT）

策略：每本书保存完整的本级大纲词表，同一单词可出现在多本书（按 tag 归属）：
  中小学 = 所有 zk 词
  高中   = 所有 gk 词
  四级   = 所有 cet4 词
  六级   = 所有 cet6 词
  考研   = 所有 ky 词
  日常口语 = 无对应标签，保持精选词

已存在的 (tenant, book, word) 跳过保留（幂等）。
用法：cd backend && python scripts/import_ecdict.py <ecdict.csv 路径>
"""
import csv
import sys

import pymysql

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\op\AppData\Local\Temp\ecdict-repo\ecdict.csv"

BOOK_RULES = [
    ("primary_school", "中小学", "zk"),
    ("high_school", "高中", "gk"),
    ("cet4", "四级", "cet4"),
    ("cet6", "六级", "cet6"),
    ("kaoyan", "考研", "ky"),
    ("toefl", "托福", "toefl"),
    ("ielts", "雅思", "ielts"),
    ("gre", "GRE", "gre"),
]


def main() -> None:
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password="123456",
        database="lowcode_master", charset="utf8mb4",
    )
    cur = conn.cursor()

    cur.execute("SELECT id FROM tenants WHERE code='english'")
    row = cur.fetchone()
    if not row:
        print("english tenant not found!")
        return
    tenant_id = row[0]

    cur.execute("SELECT code, id FROM word_books WHERE tenant_id=%s", (tenant_id,))
    book_ids = {code: bid for code, bid in cur.fetchall()}

    # 每本书已存在的 (word) 小写集合
    existing = {}
    for code, _name, _tag in BOOK_RULES:
        cur.execute(
            "SELECT LOWER(word) FROM english_words WHERE tenant_id=%s AND book_id=%s",
            (tenant_id, book_ids[code]),
        )
        existing[code] = {r[0] for r in cur.fetchall()}
    print(f"tenant={tenant_id} existing_per_book=" + str({k: len(v) for k, v in existing.items()}))

    # 读取 CSV，按 tag 分配到各书
    assigned = {code: [] for code, _name, _tag in BOOK_RULES}
    with open(SRC, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tags = (row.get("tag") or "").split()
            if not tags:
                continue
            word = (row.get("word") or "").strip()
            if not word:
                continue
            translation = (row.get("translation") or "").strip()
            if not translation:
                continue
            phonetic = (row.get("phonetic") or "").strip() or None
            for code, _name, tag in BOOK_RULES:
                if tag in tags and word.lower() not in existing[code]:
                    assigned[code].append((word, phonetic, translation))

    # 批量插入
    total_inserted = 0
    for code, name, _tag in BOOK_RULES:
        words = assigned[code]
        if not words:
            continue
        book_id = book_ids[code]
        rows = [(tenant_id, book_id, w, ph, tr, name) for w, ph, tr in words]
        sql = (
            "INSERT INTO english_words (tenant_id, book_id, word, phonetic, definition, level, "
            "example, example2, phrase, tags, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL, NOW(), NOW()) "
            "ON DUPLICATE KEY UPDATE word=word"
        )
        for i in range(0, len(rows), 500):
            cur.executemany(sql, rows[i : i + 500])
        conn.commit()
        print(f"  {name}({code}): +{len(words)}")
        total_inserted += len(words)

    print(f"DONE. inserted {total_inserted} words.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
