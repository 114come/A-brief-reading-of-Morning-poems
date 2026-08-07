"""单词测试出题服务

两大模块（单选/填空）× 5 题型 × 3 出题模式，题目实时动态生成，不存储。
- A 英译中单选 / B 中译英单选 / C 听音选义
- D 单词填空（前端按长度遮蔽）/ E 例句填空（挖核心词）
- 出题来源：today（当日新词+复习词）/ book（词库学习中词）/ wordbook（生词本薄弱词）
"""
import random
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.services.english.repository import EnglishRepository
from app.services.tenant.models import User

CHOICE_TYPES = ("a", "b", "c")
FILL_TYPES = ("d", "e")
ALL_TYPES = ("a", "b", "c", "d", "e")


class TestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EnglishRepository(db)

    # ── 出题来源 ──────────────────────────────────────────────────
    def _pick_word_ids(self, user: User, book_id: int, mode: str, count: int, prioritize_wrong: bool) -> list[int]:
        """返回按题型需要选中的 word_id 列表"""
        if mode == "today":
            # 当日新词+复习词：从今日会话推导
            today = date.today()
            session = self.repo.get_session(user.id, book_id, today)
            word_ids: list[int] = []
            if session:
                state = session.state or {}
                word_ids = list(state.get("review_queue", [])) + list(state.get("new_queue", []))
                # 已完成：用已答数量对应的词（从记忆 next_review_date 今天推导复习词，new 无法精确还原）
            # 兜底：复习队列 + 今日新增词（next_review_date=today 且 status>=1）
            if not word_ids:
                mem = self.repo.list_memory(user.id, book_id)
                word_ids = [m.word_id for m in mem if m.status == 1 and m.next_review_date and m.next_review_date <= today]
            return word_ids[:count] if word_ids else []

        if mode == "book":
            mem = self.repo.list_memory(user.id, book_id)
            learning = [m for m in mem if m.status == 1]
            if prioritize_wrong:
                learning.sort(key=lambda m: -m.wrong_count)
            else:
                random.shuffle(learning)
            return [m.word_id for m in learning[:count]]

        if mode == "wordbook":
            ids = self.repo.list_wordbook_word_ids(user.id, book_id)
            if prioritize_wrong:
                mem = {m.word_id: m for m in self.repo.list_memory(user.id, book_id)}
                ids.sort(key=lambda wid: -(mem[wid].wrong_count if wid in mem else 0))
            else:
                random.shuffle(ids)
            return ids[:count]

        if mode == "reading_new":
            # 今日阅读生词专项训练：当日新增生词；为空则最近 7 天并集
            from datetime import timedelta

            today = date.today()
            recent = self.repo.list_daily_reading_recent(user.id, 10)
            today_record = next((r for r in recent if r.reading_date == today), None)
            pool: list[int] = list(today_record.new_word_ids or []) if today_record else []
            if not pool:
                cutoff = today - timedelta(days=7)
                for r in recent:
                    if r.reading_date >= cutoff:
                        pool += list(r.new_word_ids or [])
            pool = list(dict.fromkeys(pool))
            random.shuffle(pool)
            return pool[:count]

        raise ValidationException("不支持的出题模式")

    # ── 干扰项 ────────────────────────────────────────────────────
    def _distractors(self, book_id: int, correct: str, field: str, n: int = 3) -> list[str]:
        """从同词书随机取 n 个不同干扰项（释义或单词）"""
        book = self.repo.get_book(book_id)
        if not book:
            return []
        words = self.repo.list_words(book.tenant_id, book_id, limit=300)
        pool = []
        for w in words:
            val = getattr(w, field, None)
            if val and val != correct and val not in pool:
                pool.append(val)
        random.shuffle(pool)
        return pool[:n]

    def _options_with_correct(self, correct: str, distractors: list[str]) -> list[str]:
        options = [correct] + distractors[:3]
        random.shuffle(options)
        return options

    # ── 生成题目 ──────────────────────────────────────────────────
    def generate(self, user: User, book_id: int, module: str, question_type: str, mode: str, count: int) -> dict:
        if question_type not in ALL_TYPES:
            raise ValidationException("不支持的题型")
        if module == "choice" and question_type not in CHOICE_TYPES:
            raise ValidationException("单选模块不支持该题型")
        if module == "fill" and question_type not in FILL_TYPES:
            raise ValidationException("填空模块不支持该题型")

        count = min(max(count, 1), 100)
        word_ids = self._pick_word_ids(user, book_id, mode, count, prioritize_wrong=True)

        # 若不足，book 模式回退：同词书任意学习中词补足（wordbook 模式仅生词本内词，不补）
        if len(word_ids) < count and mode == "book":
            all_ids = self.repo.list_book_word_ids(book_id)
            extra = [i for i in all_ids if i not in word_ids]
            random.shuffle(extra)
            word_ids += extra[: count - len(word_ids)]

        if not word_ids:
            raise ValidationException("该模式下暂无可用单词")

        questions = []
        for wid in word_ids[:count]:
            word = self.repo.get_word(wid)
            if not word:
                continue
            q = self._build_question(word, question_type)
            if q:
                questions.append(q)

        return {
            "questions": questions,
            "mode": mode,
            "module": module,
            "question_type": question_type,
            "total": len(questions),
        }

    def _build_question(self, word, qtype: str) -> dict | None:
        base = {
            "word_id": word.id,
            "word": word.word,
            "phonetic": word.phonetic,
            "definition": word.definition,
            "pos": word.pos,
        }
        if qtype == "a":  # 英译中：展示单词，选中文释义
            distractors = self._distractors(word.book_id, word.definition, "definition")
            if len(distractors) < 3:
                return None  # 词太少无法出题
            return {**base, "type": "a", "show": "word", "options": self._options_with_correct(word.definition, distractors), "answer": word.definition}
        if qtype == "b":  # 中译英：展示释义，选单词
            distractors = self._distractors(word.book_id, word.word, "word")
            if len(distractors) < 3:
                return None
            return {**base, "type": "b", "show": "definition", "options": self._options_with_correct(word.word, distractors), "answer": word.word}
        if qtype == "c":  # 听音选义：隐藏单词，听音频选释义
            distractors = self._distractors(word.book_id, word.definition, "definition")
            if len(distractors) < 3:
                return None
            return {**base, "type": "c", "show": "audio", "options": self._options_with_correct(word.definition, distractors), "answer": word.definition}
        if qtype == "d":  # 单词填空：中文释义，输入单词
            return {**base, "type": "d", "mask": self._mask_word(word.word), "answer": word.word.lower()}
        if qtype == "e":  # 例句填空：英文例句挖空 + 中文句意
            example = word.example or word.example2
            if not example:
                return None
            example_cn = word.example_cn or word.example2_cn or word.definition
            return {
                **base,
                "type": "e",
                "example_en": example,
                "example_cn": example_cn,
                "answer": word.word.lower(),
            }
        return None

    @staticmethod
    def _mask_word(word: str) -> str:
        """遮蔽规则：≤3 不遮（调用方跳过）；4-6 遮中间2；≥7 遮中间3-4"""
        n = len(word)
        if n <= 3:
            return word
        if n <= 6:
            start = (n - 2) // 2
            end = start + 2
        else:
            start = (n - 3) // 2
            end = start + 3
        return word[:start] + "_" * (end - start) + word[end:]
