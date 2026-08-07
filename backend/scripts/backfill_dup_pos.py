"""回填重复词的 pos：把同词有 pos 的值复制到缺失的行"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root", password="123456",
    database="lowcode_master", charset="utf8mb4", autocommit=True,
)
cur = conn.cursor()
# 收集：每个缺 pos 的词，找同词已有 pos 的值
cur.execute(
    "SELECT w.word, w.id FROM english_words w "
    "WHERE w.pos IS NULL AND EXISTS (SELECT 1 FROM english_words w2 WHERE w2.word=w.word AND w2.pos IS NOT NULL)"
)
missing = cur.fetchall()
# 有 pos 的词（word -> pos，取第一个）
cur.execute("SELECT word, pos FROM english_words WHERE pos IS NOT NULL")
pos_by_word = {}
for word, pos in cur.fetchall():
    if word not in pos_by_word:
        pos_by_word[word] = pos

n = 0
for word, wid in missing:
    src = pos_by_word.get(word)
    if src:
        cur.execute("UPDATE english_words SET pos=%s WHERE id=%s", (src, wid))
        n += 1
print(f"backfilled {n} rows")
cur.close()
conn.close()
