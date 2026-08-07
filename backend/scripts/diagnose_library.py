"""诊断当前词库内容完整度"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="lowcode_master", charset="utf8mb4",
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM english_words")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE phonetic IS NOT NULL")
with_phonetic = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE example IS NOT NULL")
with_example = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE level IS NOT NULL")
with_level = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE tags IS NOT NULL")
with_tags = cur.fetchone()[0]
print(f"total={total}")
print(f"with_phonetic={with_phonetic} ({100*with_phonetic//total}%)")
print(f"with_example={with_example}")
print(f"with_level={with_level}")
print(f"with_tags={with_tags}")
conn.close()
