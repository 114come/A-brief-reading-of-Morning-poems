"""上线前全量 API 走查"""
import json
import time
import urllib.request

BASE = "http://localhost:8001/api/v1/english"
PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name} {detail}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


def call(method, path, body=None, token=None, q=""):
    req = urllib.request.Request(BASE + path + q, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


def main():
    # 注册
    u = "golive" + str(time.time_ns())[-6:]
    r = call("POST", "/auth/register", {"username": u, "email": u + "@t.com", "password": "secret123"})
    check("register", r["code"] == 0)
    token = r["data"]["access_token"]

    # 词书（游客 + 登录）
    r = call("GET", "/srs/books")
    check("books public", r["code"] == 0 and len(r["data"]) == 9, f"({len(r['data'])} books)")
    books = r["data"]
    cet6 = [b for b in books if b["code"] == "cet6"][0]

    # 单词列表（含 pos/phonetic/例句）
    r = call("GET", "/words", token=token, q=f"?book_id={cet6['id']}&limit=5")
    check("words list", r["code"] == 0 and len(r["data"]) == 5, f"({len(r['data'])} words)")
    if r["data"]:
        w = r["data"][0]
        check("word has pos", bool(w.get("pos")), f"({w['word']} pos={w.get('pos')})")
        check("word has phonetic", bool(w.get("phonetic")), f"({w['word']})")

    # onboarding 六级
    r = call("POST", "/srs/onboarding", {"target": "cet6", "book_id": cet6["id"], "daily_new_words": 10, "pronunciation": "us", "autoplay": False}, token)
    check("onboarding", r["code"] == 0)
    state = call("GET", "/srs/state", token=token, q=f"?book_id={cet6['id']}")["data"]
    check("state memory init", len(state["memory"]) == cet6["word_count"], f"({len(state['memory'])} rows)")

    # SRS state save / categories / tag
    r = call("PUT", "/srs/tag", {"book_id": cet6["id"], "word_id": state["memory"][0]["word_id"], "tag": "core"}, token)
    check("set tag", r["code"] == 0)
    r = call("GET", "/srs/categories", token=token, q=f"?book_id={cet6['id']}")
    check("categories", r["code"] == 0 and any(c["count"] > 0 for c in r["data"]))

    # 阅读 / 笔记
    r = call("GET", "/reading/articles", token=token)
    check("articles", r["code"] == 0 and len(r["data"]) == 5)
    aid = r["data"][0]["id"]
    r = call("POST", "/reading/notes", {"article_id": aid, "content": "test note"}, token)
    check("note create", r["code"] == 0)
    r = call("GET", "/reading/notes", token=token)
    check("note list", r["code"] == 0 and len(r["data"]) >= 1)

    # 收藏 / 生词本 / 打卡 / 统计
    r = call("POST", "/collections", {"item_type": "reading", "item_id": aid}, token)
    check("collection", r["code"] == 0)
    r = call("GET", "/wordbook", token=token, q=f"?book_id={cet6['id']}")
    check("wordbook list", r["code"] == 0)
    r = call("GET", "/srs/stats", token=token)
    check("srs stats", r["code"] == 0)
    r = call("GET", "/checkin/stats", token=token)
    check("checkin stats", r["code"] == 0)
    r = call("GET", "/study/stats", token=token)
    check("study stats", r["code"] == 0)

    # 游客词库回退
    r = call("GET", "/words?book_id=3&limit=2")
    check("guest words fallback", r["code"] == 0 and len(r["data"]) == 2)

    # 刷新令牌
    r = call("POST", "/auth/refresh", {"refresh_token": token})
    check("refresh with access-token rejected", r["code"] != 0)

    print(f"\nPASS={PASS} FAIL={FAIL}")


if __name__ == "__main__":
    main()
