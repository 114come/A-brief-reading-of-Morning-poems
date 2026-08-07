"""全面数据质量审计：每本书字段完整度 + 异常数据排查"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="lowcode_master", charset="utf8mb4",
)
cur = conn.cursor()

lines = []

# 1. 每本书字段完整度
cur.execute("""
    SELECT b.code,
           COUNT(*) total,
           SUM(w.phonetic IS NOT NULL AND w.phonetic != '') ph,
           SUM(w.definition IS NOT NULL AND w.definition != '') def,
           SUM(w.pos IS NOT NULL AND w.pos != '') pos,
           SUM(w.example IS NOT NULL AND w.example != '') ex,
           SUM(w.example2 IS NOT NULL AND w.example2 != '') ex2,
           SUM(w.phrase IS NOT NULL AND w.phrase != '') phrase
    FROM english_words w JOIN word_books b ON w.book_id = b.id
    GROUP BY b.code ORDER BY MIN(b.sort_order)
""")
lines.append("== 每本书字段完整度 ==")
lines.append("code | total | 音标 | 释义 | 词性 | 例句1 | 例句2 | 短语")
for r in cur.fetchall():
    lines.append(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]}")

# 2. 异常数据
lines.append("")
lines.append("== 异常数据排查 ==")
cur.execute("SELECT COUNT(*) FROM english_words WHERE word IS NULL OR word = '' OR LENGTH(word) > 80")
lines.append(f"空/超长单词: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM english_words WHERE definition IS NULL OR definition = ''")
lines.append(f"空释义: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM english_words WHERE book_id IS NULL")
lines.append(f"无词书归属: {cur.fetchone()[0]}")
cur.execute("""
    SELECT COUNT(*) FROM (SELECT word FROM english_words GROUP BY tenant_id, book_id, word HAVING COUNT(*) > 1) t
""")
lines.append(f"同书重复词: {cur.fetchone()[0]}")
# 疑似乱码（常见乱码字节）
cur.execute("SELECT COUNT(*) FROM english_words WHERE definition LIKE '%\\ufffd%' OR word LIKE '%\\ufffd%'")
lines.append(f"含替换符(乱码): {cur.fetchone()[0]}")
# 音标缺失单词数
cur.execute("SELECT COUNT(*) FROM english_words WHERE phonetic IS NULL OR phonetic = ''")
lines.append(f"缺音标: {cur.fetchone()[0]}")
# 释义过短（可能残缺）
cur.execute("SELECT COUNT(*) FROM english_words WHERE CHAR_LENGTH(definition) < 2")
lines.append(f"释义过短(<2字符): {cur.fetchone()[0]}")

# 3. 释义质量抽样（各书抽几个，检查是否为纯英文无中文/纯中文无英文）
lines.append("")
lines.append("== 释义语言检查（抽样） ==")
cur.execute("""
    SELECT word, definition FROM english_words
    WHERE definition NOT REGEXP '[一-龥]' AND definition != ''
    LIMIT 5
""")
no_cn = cur.fetchall()
lines.append(f"无中文释义的词数量抽样: {len(no_cn)}")
for w, d in no_cn[:3]:
    lines.append(f"  {w}: {(d or '')[:40]}")

# 4. 例句长度检查（超短例句可能是垃圾）
lines.append("")
lines.append("== 例句质量（抽样） ==")
cur.execute("SELECT word, example FROM english_words WHERE example IS NOT NULL AND CHAR_LENGTH(example) < 8 LIMIT 5")
short_ex = cur.fetchall()
lines.append(f"超短例句数量抽样: {len(short_ex)}")
for w, e in short_ex[:3]:
    lines.append(f"  {w}: {(e or '')[:30]}")

cur.close()
conn.close()

with open(r"E:\20260718\backend\scripts\audit_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("written")
