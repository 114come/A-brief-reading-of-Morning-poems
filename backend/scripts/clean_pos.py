"""清洗 pos 为前端友好格式（中文词性）

ECDICT pos 形如 "n:100"/"j:100"/"noun/verb"：
  n/j/v/r/a 单字母 → 中文
  完整英文单词 → 中文
多词性用 / 连接。
"""
import pymysql

POS_MAP = {
    "n": "名词", "noun": "名词", "noun.": "名词",
    "v": "动词", "verb": "动词", "verb.": "动词", "vt": "及物动词", "vi": "不及物动词",
    "j": "形容词", "adj": "形容词", "adjective": "形容词", "adj.": "形容词",
    "r": "副词", "adv": "副词", "adverb": "副词", "adv.": "副词",
    "pron": "代词", "pronoun": "代词",
    "prep": "介词", "preposition": "介词",
    "conj": "连词", "conjunction": "连词",
    "art": "冠词", "article": "冠词",
    "num": "数词", "numeral": "数词",
    "int": "感叹词", "interj": "感叹词", "interjection": "感叹词",
    "aux": "助动词", "auxiliary": "助动词",
    "det": "限定词", "determiner": "限定词",
}


def clean_one(pos: str) -> str:
    parts = pos.split("/")
    cleaned = []
    for p in parts:
        p = p.strip()
        # 去掉 ":100" 频次后缀
        base = p.split(":")[0].strip()
        word = POS_MAP.get(base) or POS_MAP.get(base.lower()) or base
        if word not in cleaned:
            cleaned.append(word)
    return "/".join(cleaned)


def main() -> None:
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password="123456",
        database="lowcode_master", charset="utf8mb4", autocommit=True,
    )
    cur = conn.cursor()
    cur.execute("SELECT id, pos FROM english_words WHERE pos IS NOT NULL")
    rows = cur.fetchall()
    n = 0
    for wid, pos in rows:
        clean = clean_one(pos)
        if clean != pos:
            cur.execute("UPDATE english_words SET pos=%s WHERE id=%s", (clean, wid))
            n += 1
    print(f"cleaned {n} pos values")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
