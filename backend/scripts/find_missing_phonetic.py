"""查找缺音标的词分布"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="lowcode_master", charset="utf8mb4",
)
cur = conn.cursor()
cur.execute("""
    SELECT b.code, COUNT(*) FROM english_words w JOIN word_books b ON w.book_id=b.id
    WHERE w.phonetic IS NULL OR w.phonetic = ''
    GROUP BY b.code ORDER BY COUNT(*) DESC
""")
rows = cur.fetchall()
cur.execute("SELECT word FROM english_words WHERE (phonetic IS NULL OR phonetic='') AND book_id IN (SELECT id FROM word_books WHERE code='kaoyan') LIMIT 10")
samples = cur.fetchall()
cur.close()
conn.close()
with open(r"E:\20260718\backend\scripts\missing_ph.txt", "w", encoding="utf-8") as f:
    f.write("== 缺音标分布 ==\n")
    for r in rows:
        f.write(f"  {r[0]}: {r[1]}\n")
    f.write("== kaoyan 缺音标抽样 ==\n")
    for r in samples:
        f.write(f"  {r[0]}\n")
print("written")
