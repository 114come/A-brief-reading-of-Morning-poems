"""报告词库覆盖情况（输出到文件 report.txt，避免控制台编码问题）"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="lowcode_master", charset="utf8mb4",
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM english_words")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE example IS NOT NULL AND example != ''")
ex = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE example2 IS NOT NULL AND example2 != ''")
ex2 = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE pos IS NOT NULL")
pos = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM english_words WHERE phonetic IS NOT NULL")
ph = cur.fetchone()[0]
cur.execute(
    "SELECT b.code, COUNT(*), "
    "SUM(CASE WHEN w.example IS NOT NULL AND w.example != '' THEN 1 ELSE 0 END) "
    "FROM english_words w JOIN word_books b ON w.book_id=b.id "
    "GROUP BY b.code ORDER BY MIN(b.sort_order)"
)
per_book = cur.fetchall()
cur.close()
conn.close()

lines = [
    f"total={total}",
    f"example={ex} ({100*ex//total}%)",
    f"example2={ex2}",
    f"pos={pos} ({100*pos//total}%)",
    f"phonetic={ph} ({100*ph//total}%)",
    "",
    "per_book:",
]
for code, cnt, ex_cnt in per_book:
    lines.append(f"  {code}: {cnt} words, {ex_cnt} with example")
with open("scripts/report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written")
