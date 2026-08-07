"""验证大词库：words 接口完整性 + onboarding 批量初始化"""
import json
import time
import urllib.request

BASE = "http://localhost:8001/api/v1/english"


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
    # 注册新用户
    u = "lib" + str(time.time_ns())[-6:]
    r = call("POST", "/auth/register", {"username": u, "email": u + "@t.com", "password": "secret123"})
    print("register:", r["code"])
    token = r["data"]["access_token"]

    # 六级书
    books = call("GET", "/srs/books")["data"]
    cet6 = [b for b in books if b["code"] == "cet6"][0]
    print("cet6 book:", cet6["name"], cet6["word_count"], "words")

    # words 接口拉全
    t0 = time.time()
    words = call("GET", "/words", token=token, q=f"?book_id={cet6['id']}&limit=20000")["data"]
    print(f"  /words returned {len(words)} (expect {cet6['word_count']}), {time.time()-t0:.1f}s")
    if words:
        w = words[0]
        print("  sample:", w["word"], "| def:", (w["definition"] or "")[:30], "| ph:", bool(w["phonetic"]))

    # onboarding 初始化六级书（5400+ 记忆行）
    t0 = time.time()
    r = call("POST", "/srs/onboarding", {"target": "cet6", "book_id": cet6["id"], "daily_new_words": 10, "pronunciation": "us", "autoplay": False}, token)
    print("onboarding:", r["code"], f"{time.time()-t0:.1f}s")
    state = call("GET", "/srs/state", token=token, q=f"?book_id={cet6['id']}")["data"]
    print("  memory rows after onboarding:", len(state["memory"]))
    print("  all status0:", all(m["status"] == 0 for m in state["memory"]))


if __name__ == "__main__":
    main()
