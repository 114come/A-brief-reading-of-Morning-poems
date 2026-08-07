"""从 ECDICT 回填现有单词的词性(pos)与缺失音标(phonetic)

幂等：只为 pos 为空 或 phonetic 为空 的单词补充。
用法：cd backend && python scripts/backfill_pos_and_phonetic.py <ecdict.csv路径>
"""
import csv
import sys

import pymysql

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\op\AppData\Local\Temp\ecdict-full\stardict.csv"


def main() -> None:
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password="123456",
        database="lowcode_master", charset="utf8mb4",
    )
    cur = conn.cursor()

    # 收集需要回填的单词（pos 或 phonetic 为空）
    cur.execute("SELECT id, LOWER(word), pos, phonetic FROM english_words WHERE pos IS NULL OR phonetic IS NULL")
    rows = cur.fetchall()
    need_pos = {w.lower(): wid for wid, w, p, ph in rows if p is None}
    need_phonetic = {w.lower(): wid for wid, w, p, ph in rows if ph is None}
    print(f"need_pos={len(need_pos)} need_phonetic={len(need_phonetic)}")

    pos_updates = {}
    ph_updates = {}
    with open(SRC, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = (row.get("word") or "").strip().lower()
            if word in need_pos and (row.get("pos") or "").strip():
                pos_updates[word] = row["pos"].strip()
            if word in need_phonetic and (row.get("phonetic") or "").strip():
                ph_updates[word] = row["phonetic"].strip()
            if len(pos_updates) >= len(need_pos) and len(ph_updates) >= len(need_phonetic):
                break

    n_pos = 0
    for word, wid in need_pos.items():
        if word in pos_updates:
            cur.execute("UPDATE english_words SET pos=%s WHERE id=%s", (pos_updates[word], wid))
            n_pos += 1
    n_ph = 0
    for word, wid in need_phonetic.items():
        if word in ph_updates:
            cur.execute("UPDATE english_words SET phonetic=%s WHERE id=%s", (ph_updates[word], wid))
            n_ph += 1
    conn.commit()
    print(f"DONE. pos updated={n_pos} phonetic updated={n_ph}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
