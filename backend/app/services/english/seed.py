"""英语学习种子数据：租户 + 词书 + 单词/文章

seed_english_tenant 幂等：english 租户已存在则补齐缺失的管理员。
seed_english_data 幂等：按 (tenant, word) upsert，已存在的单词会回填
词书归属、第二例句与短语搭配；词书按 (tenant, code) upsert。
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.english.models import (
    EnglishWord,
    EnglishWordBook,
)
from app.services.english.service import get_english_tenant
from app.services.tenant.repository import UserRepository
from app.services.tenant.service import TenantService

logger = logging.getLogger(__name__)

_BOOKS: list[dict] = [
    {"code": "primary_school", "name": "中小学", "sort_order": 1},
    {"code": "high_school", "name": "高中", "sort_order": 2},
    {"code": "cet4", "name": "四级", "sort_order": 3},
    {"code": "cet6", "name": "六级", "sort_order": 4},
    {"code": "kaoyan", "name": "考研", "sort_order": 5},
    {"code": "daily", "name": "日常口语", "sort_order": 6},
    {"code": "toefl", "name": "托福", "sort_order": 7},
    {"code": "ielts", "name": "雅思", "sort_order": 8},
    {"code": "gre", "name": "GRE", "sort_order": 9},
]


def seed_english_tenant(db: Session) -> None:
    """确保 english 专用租户及其管理员存在（幂等补齐）"""
    tenant = get_english_tenant(db)
    repo = UserRepository(db)
    if not repo.get_by_username("english_admin", tenant.id):
        TenantService(db).create_user(
            username="english_admin",
            email="admin@english.local",
            password=settings.SECRET_KEY or "english-admin",
            tenant_id=tenant.id,
            is_superuser=True,
        )
        logger.info("created english_admin for tenant %s", tenant.code)
    logger.info("english tenant ready")


def _upsert_books(db: Session, tenant_id: int) -> dict[str, EnglishWordBook]:
    """按 (tenant, code) upsert 词书，返回 code → 词书对象"""
    books: dict[str, EnglishWordBook] = {}
    for item in _BOOKS:
        book = (
            db.query(EnglishWordBook)
            .filter(EnglishWordBook.tenant_id == tenant_id, EnglishWordBook.code == item["code"])
            .first()
        )
        if book:
            book.name = item["name"]
            book.sort_order = item["sort_order"]
        else:
            book = EnglishWordBook(
                tenant_id=tenant_id,
                code=item["code"],
                name=item["name"],
                sort_order=item["sort_order"],
            )
            db.add(book)
            db.flush()
        books[item["code"]] = book
    db.commit()
    return books


def _upsert_words(db: Session, tenant_id: int, books: dict[str, EnglishWordBook]) -> None:
    for book_code, words in _WORDS_BY_BOOK.items():
        book = books[book_code]
        for item in words:
            existing = (
                db.query(EnglishWord)
                .filter(
                    EnglishWord.tenant_id == tenant_id,
                    EnglishWord.book_id == book.id,
                    EnglishWord.word == item["word"],
                )
                .first()
            )
            if existing:
                existing.book_id = book.id
                existing.phonetic = item.get("phonetic", existing.phonetic)
                existing.definition = item["definition"]
                existing.pos = item.get("pos", existing.pos)
                existing.example = item.get("example", existing.example)
                existing.example2 = item.get("example2", existing.example2)
                existing.phrase = item.get("phrase", existing.phrase)
                existing.level = item.get("level", existing.level)
                existing.tags = item.get("tags", existing.tags)
            else:
                db.add(
                    EnglishWord(
                        tenant_id=tenant_id,
                        book_id=book.id,
                        word=item["word"],
                        phonetic=item.get("phonetic"),
                        definition=item["definition"],
                        pos=item.get("pos"),
                        example=item.get("example"),
                        example2=item.get("example2"),
                        phrase=item.get("phrase"),
                        level=item.get("level"),
                        tags=item.get("tags"),
                    )
                )
    db.commit()


def seed_english_data(db: Session) -> None:
    tenant = get_english_tenant(db)
    tenant_id = tenant.id

    books = _upsert_books(db, tenant_id)
    _upsert_words(db, tenant_id, books)
    logger.info("seeded word books + words")

    # 阅读文章不再播种：每日一读由 LLM 按 (日期, 难度, 题材) 运行时生成

    db.commit()


# 每个词：word, phonetic, definition, example(句1), example2(句2), phrase(搭配), level, tags
_WORDS_BY_BOOK: dict[str, list[dict]] = {
    "primary_school": [
        {"word": "apple", "phonetic": "/ˈæpl/", "definition": "n. 苹果", "example": "I eat an apple every day.", "example2": "The apple is red and sweet.", "phrase": "an apple a day 一天一个苹果", "level": "中小学"},
        {"word": "book", "phonetic": "/bʊk/", "definition": "n. 书", "example": "This is my English book.", "example2": "She is reading a book.", "phrase": "read a book 读书", "level": "中小学"},
        {"word": "school", "phonetic": "/skuːl/", "definition": "n. 学校", "example": "We go to school by bus.", "example2": "Our school is very big.", "phrase": "go to school 上学", "level": "中小学"},
        {"word": "friend", "phonetic": "/frend/", "definition": "n. 朋友", "example": "Tom is my good friend.", "example2": "I play with my friends.", "phrase": "make friends 交朋友", "level": "中小学"},
        {"word": "family", "phonetic": "/ˈfæməli/", "definition": "n. 家庭", "example": "My family has four people.", "example2": "I love my family.", "phrase": "family member 家庭成员", "level": "中小学"},
        {"word": "teacher", "phonetic": "/ˈtiːtʃər/", "definition": "n. 老师", "example": "Our teacher is kind.", "example2": "The teacher writes on the board.", "phrase": "English teacher 英语老师", "level": "中小学"},
        {"word": "student", "phonetic": "/ˈstjuːdnt/", "definition": "n. 学生", "example": "She is a hard-working student.", "example2": "The students are in class.", "phrase": "a good student 好学生", "level": "中小学"},
        {"word": "water", "phonetic": "/ˈwɔːtər/", "definition": "n. 水 v. 浇水", "example": "I drink water after running.", "example2": "Please water the flowers.", "phrase": "drink water 喝水", "level": "中小学"},
        {"word": "milk", "phonetic": "/mɪlk/", "definition": "n. 牛奶", "example": "I drink milk every morning.", "example2": "The cat likes milk.", "phrase": "a glass of milk 一杯牛奶", "level": "中小学"},
        {"word": "food", "phonetic": "/fuːd/", "definition": "n. 食物", "example": "Chinese food is delicious.", "example2": "We need food and water.", "phrase": "fast food 快餐", "level": "中小学"},
        {"word": "money", "phonetic": "/ˈmʌni/", "definition": "n. 钱", "example": "I save money in a box.", "example2": "Money can't buy happiness.", "phrase": "make money 挣钱", "level": "中小学"},
        {"word": "time", "phonetic": "/taɪm/", "definition": "n. 时间", "example": "What time is it now?", "example2": "Time flies fast.", "phrase": "on time 准时", "level": "中小学"},
        {"word": "day", "phonetic": "/deɪ/", "definition": "n. 天；白天", "example": "Today is a sunny day.", "example2": "I study English every day.", "phrase": "every day 每天", "level": "中小学"},
        {"word": "home", "phonetic": "/həʊm/", "definition": "n. 家", "example": "I go home after school.", "example2": "There is no place like home.", "phrase": "go home 回家", "level": "中小学"},
        {"word": "happy", "phonetic": "/ˈhæpi/", "definition": "adj. 快乐的", "example": "I am happy today.", "example2": "She has a happy family.", "phrase": "happy birthday 生日快乐", "level": "中小学"},
        {"word": "big", "phonetic": "/bɪɡ/", "definition": "adj. 大的", "example": "The elephant is very big.", "example2": "We live in a big city.", "phrase": "big house 大房子", "level": "中小学"},
        {"word": "small", "phonetic": "/smɔːl/", "definition": "adj. 小的", "example": "The cat is small and cute.", "example2": "I have a small dog.", "phrase": "small size 小号", "level": "中小学"},
        {"word": "new", "phonetic": "/njuː/", "definition": "adj. 新的", "example": "I got a new bike.", "example2": "This is a new word.", "phrase": "new year 新年", "level": "中小学"},
        {"word": "old", "phonetic": "/əʊld/", "definition": "adj. 旧的；老的", "example": "This is an old book.", "example2": "My grandfather is old.", "phrase": "old friend 老朋友", "level": "中小学"},
        {"word": "eat", "phonetic": "/iːt/", "definition": "v. 吃", "example": "I eat breakfast at seven.", "example2": "What do you want to eat?", "phrase": "eat out 出去吃", "level": "中小学"},
        {"word": "drink", "phonetic": "/drɪŋk/", "definition": "v. 喝 n. 饮料", "example": "Drink more water every day.", "example2": "I drink tea in the afternoon.", "phrase": "drink tea 喝茶", "level": "中小学"},
        {"word": "run", "phonetic": "/rʌn/", "definition": "v. 跑", "example": "I run in the park.", "example2": "He can run very fast.", "phrase": "run fast 跑得快", "level": "中小学"},
        {"word": "read", "phonetic": "/riːd/", "definition": "v. 读；阅读", "example": "I like to read stories.", "example2": "She reads before bed.", "phrase": "read aloud 朗读", "level": "中小学"},
        {"word": "write", "phonetic": "/raɪt/", "definition": "v. 写", "example": "Please write your name.", "example2": "He writes a letter to me.", "phrase": "write down 写下", "level": "中小学"},
        {"word": "listen", "phonetic": "/ˈlɪsn/", "definition": "v. 听", "example": "Listen to the teacher.", "example2": "I listen to music.", "phrase": "listen to music 听音乐", "level": "中小学"},
        {"word": "speak", "phonetic": "/spiːk/", "definition": "v. 说；讲", "example": "Speak English in class.", "example2": "Can you speak slowly?", "phrase": "speak English 说英语", "level": "中小学"},
        {"word": "play", "phonetic": "/pleɪ/", "definition": "v. 玩；打（球）", "example": "We play games after school.", "example2": "He plays basketball well.", "phrase": "play football 踢足球", "level": "中小学"},
        {"word": "city", "phonetic": "/ˈsɪti/", "definition": "n. 城市", "example": "Shanghai is a big city.", "example2": "I live in the city.", "phrase": "city center 市中心", "level": "中小学"},
        {"word": "park", "phonetic": "/pɑːk/", "definition": "n. 公园", "example": "There is a park near my home.", "example2": "We fly kites in the park.", "phrase": "go to the park 去公园", "level": "中小学"},
        {"word": "weather", "phonetic": "/ˈweðər/", "definition": "n. 天气", "example": "The weather is nice today.", "example2": "How is the weather?", "phrase": "bad weather 坏天气", "level": "中小学"},
        {"word": "morning", "phonetic": "/ˈmɔːnɪŋ/", "definition": "n. 早晨", "example": "I get up early in the morning.", "example2": "Good morning, class!", "phrase": "in the morning 在早上", "level": "中小学"},
        {"word": "evening", "phonetic": "/ˈiːvnɪŋ/", "definition": "n. 晚上", "example": "We watch TV in the evening.", "example2": "Good evening, everyone.", "phrase": "in the evening 在晚上", "level": "中小学"},
        {"word": "learn", "phonetic": "/lɜːn/", "definition": "v. 学习", "example": "I learn English at school.", "example2": "We learn from our mistakes.", "phrase": "learn by heart 用心记住", "level": "中小学"},
        {"word": "help", "phonetic": "/help/", "definition": "v. 帮助 n. 帮助", "example": "Can you help me, please?", "example2": "She helps her mother cook.", "phrase": "help sb. do sth. 帮助某人做某事", "level": "中小学"},
    ],
    "high_school": [
        {"word": "ability", "phonetic": "/əˈbɪləti/", "definition": "n. 能力", "example": "She has the ability to lead.", "example2": "Everyone has the ability to learn.", "phrase": "the ability to do 做…的能力", "level": "高中"},
        {"word": "achieve", "phonetic": "/əˈtʃiːv/", "definition": "v. 实现；达到", "example": "Work hard to achieve your goal.", "example2": "He achieved great success.", "phrase": "achieve a goal 达成目标", "level": "高中"},
        {"word": "advice", "phonetic": "/ədˈvaɪs/", "definition": "n. 建议", "example": "Let me give you some advice.", "example2": "He took my advice.", "phrase": "take one's advice 采纳某人的建议", "level": "高中"},
        {"word": "allow", "phonetic": "/əˈlaʊ/", "definition": "v. 允许", "example": "My parents allow me to go out.", "example2": "Smoking is not allowed here.", "phrase": "allow sb. to do 允许某人做", "level": "高中"},
        {"word": "attend", "phonetic": "/əˈtend/", "definition": "v. 参加；出席", "example": "I will attend the meeting.", "example2": "She attends school every day.", "phrase": "attend a class 上课", "level": "高中"},
        {"word": "believe", "phonetic": "/bɪˈliːv/", "definition": "v. 相信", "example": "I believe you can do it.", "example2": "He believes in hard work.", "phrase": "believe in 信任", "level": "高中"},
        {"word": "choice", "phonetic": "/tʃɔɪs/", "definition": "n. 选择", "example": "You have a choice to make.", "example2": "It was a difficult choice.", "phrase": "make a choice 做选择", "level": "高中"},
        {"word": "compare", "phonetic": "/kəmˈpeər/", "definition": "v. 比较", "example": "Compare the two answers.", "example2": "Don't compare yourself with others.", "phrase": "compare with 与…相比", "level": "高中"},
        {"word": "decide", "phonetic": "/dɪˈsaɪd/", "definition": "v. 决定", "example": "I decided to study abroad.", "example2": "She decided not to go.", "phrase": "decide to do 决定做", "level": "高中"},
        {"word": "develop", "phonetic": "/dɪˈveləp/", "definition": "v. 发展；培养", "example": "Reading develops the mind.", "example2": "The city developed quickly.", "phrase": "develop a habit 养成习惯", "level": "高中"},
        {"word": "difficult", "phonetic": "/ˈdɪfɪkəlt/", "definition": "adj. 困难的", "example": "The exam was difficult.", "example2": "It is difficult to say no.", "phrase": "a difficult task 艰巨的任务", "level": "高中"},
        {"word": "discover", "phonetic": "/dɪˈskʌvər/", "definition": "v. 发现", "example": "Scientists discovered a new planet.", "example2": "I discovered the answer.", "phrase": "discover the truth 发现真相", "level": "高中"},
        {"word": "encourage", "phonetic": "/ɪnˈkʌrɪdʒ/", "definition": "v. 鼓励", "example": "Teachers encourage us to ask questions.", "example2": "Her words encouraged me.", "phrase": "encourage sb. to do 鼓励某人做", "level": "高中"},
        {"word": "environment", "phonetic": "/ɪnˈvaɪrənmənt/", "definition": "n. 环境", "example": "We should protect the environment.", "example2": "A quiet environment helps study.", "phrase": "protect the environment 保护环境", "level": "高中"},
        {"word": "experience", "phonetic": "/ɪkˈspɪəriəns/", "definition": "n. 经验；经历", "example": "She has teaching experience.", "example2": "It was a great experience.", "phrase": "gain experience 获得经验", "level": "高中"},
        {"word": "express", "phonetic": "/ɪkˈspres/", "definition": "v. 表达", "example": "Express your ideas clearly.", "example2": "He expressed his thanks.", "phrase": "express oneself 表达自己", "level": "高中"},
        {"word": "future", "phonetic": "/ˈfjuːtʃər/", "definition": "n. 未来", "example": "We should plan for the future.", "example2": "The future is bright.", "phrase": "in the future 在未来", "level": "高中"},
        {"word": "improve", "phonetic": "/ɪmˈpruːv/", "definition": "v. 提高；改善", "example": "Practice improves your English.", "example2": "The weather improved.", "phrase": "improve oneself 提升自己", "level": "高中"},
        {"word": "knowledge", "phonetic": "/ˈnɒlɪdʒ/", "definition": "n. 知识", "example": "Knowledge is power.", "example2": "She has wide knowledge.", "phrase": "book knowledge 书本知识", "level": "高中"},
        {"word": "language", "phonetic": "/ˈlæŋɡwɪdʒ/", "definition": "n. 语言", "example": "English is a useful language.", "example2": "Music is a universal language.", "phrase": "foreign language 外语", "level": "高中"},
        {"word": "necessary", "phonetic": "/ˈnesəsəri/", "definition": "adj. 必要的", "example": "Rest is necessary after work.", "example2": "It is necessary to practice.", "phrase": "if necessary 如有必要", "level": "高中"},
        {"word": "opportunity", "phonetic": "/ˌɒpəˈtjuːnəti/", "definition": "n. 机会", "example": "Don't miss this opportunity.", "example2": "The trip was a good opportunity.", "phrase": "seize the opportunity 抓住机会", "level": "高中"},
        {"word": "patient", "phonetic": "/ˈpeɪʃnt/", "definition": "adj. 耐心的 n. 病人", "example": "Be patient with your children.", "example2": "The doctor sees many patients.", "phrase": "be patient with 对…有耐心", "level": "高中"},
        {"word": "practical", "phonetic": "/ˈpræktɪkl/", "definition": "adj. 实际的；实用的", "example": "This course is very practical.", "example2": "We need a practical plan.", "phrase": "practical skills 实用技能", "level": "高中"},
        {"word": "prepare", "phonetic": "/prɪˈpeər/", "definition": "v. 准备", "example": "Prepare for the exam tonight.", "example2": "She prepared a gift.", "phrase": "prepare for 为…做准备", "level": "高中"},
        {"word": "purpose", "phonetic": "/ˈpɜːpəs/", "definition": "n. 目的", "example": "What is the purpose of the trip?", "example2": "He studied with a clear purpose.", "phrase": "on purpose 故意地", "level": "高中"},
        {"word": "realize", "phonetic": "/ˈrɪəlaɪz/", "definition": "v. 意识到；实现", "example": "I realized my mistake.", "example2": "She realized her dream.", "phrase": "realize one's dream 实现梦想", "level": "高中"},
        {"word": "require", "phonetic": "/rɪˈkwaɪər/", "definition": "v. 需要；要求", "example": "This task requires patience.", "example2": "Students are required to wear uniforms.", "phrase": "require sb. to do 要求某人做", "level": "高中"},
        {"word": "society", "phonetic": "/səˈsaɪəti/", "definition": "n. 社会", "example": "We live in a modern society.", "example2": "Technology changes society.", "phrase": "in society 在社会中", "level": "高中"},
        {"word": "succeed", "phonetic": "/səkˈsiːd/", "definition": "v. 成功", "example": "Hard work helps you succeed.", "example2": "She succeeded in passing the test.", "phrase": "succeed in doing 成功做成", "level": "高中"},
        {"word": "suppose", "phonetic": "/səˈpəʊz/", "definition": "v. 假设；认为", "example": "I suppose you are right.", "example2": "Suppose it rains tomorrow.", "phrase": "be supposed to 应该", "level": "高中"},
        {"word": "university", "phonetic": "/ˌjuːnɪˈvɜːsəti/", "definition": "n. 大学", "example": "She studies at a famous university.", "example2": "He wants to go to university.", "phrase": "attend university 上大学", "level": "高中"},
        {"word": "value", "phonetic": "/ˈvæljuː/", "definition": "n. 价值 v. 重视", "example": "Friendship has great value.", "example2": "I value your advice.", "phrase": "of great value 很有价值", "level": "高中"},
    ],
    "cet4": [
        {"word": "abandon", "phonetic": "/əˈbændən/", "definition": "v. 放弃；抛弃", "example": "He had to abandon the plan.", "example2": "The crew abandoned the sinking ship.", "phrase": "abandon hope 放弃希望", "level": "CET4", "tags": "高频"},
        {"word": "absorb", "phonetic": "/əbˈzɔːb/", "definition": "v. 吸收；使全神贯注", "example": "Plants absorb water from the soil.", "example2": "She was absorbed in the novel.", "phrase": "be absorbed in 全神贯注于", "level": "CET4"},
        {"word": "accompany", "phonetic": "/əˈkʌmpəni/", "definition": "v. 陪伴；伴随", "example": "I will accompany you to the station.", "example2": "Thunder accompanies lightning.", "phrase": "accompany sb. to 陪某人去", "level": "CET4"},
        {"word": "accurate", "phonetic": "/ˈækjərət/", "definition": "adj. 准确的", "example": "The data must be accurate.", "example2": "His description was accurate.", "phrase": "accurate information 准确信息", "level": "CET4"},
        {"word": "adapt", "phonetic": "/əˈdæpt/", "definition": "v. 适应；改编", "example": "It takes time to adapt to a new city.", "example2": "The film was adapted from a novel.", "phrase": "adapt to 适应", "level": "CET4"},
        {"word": "adjust", "phonetic": "/əˈdʒʌst/", "definition": "v. 调整", "example": "You can adjust the volume here.", "example2": "He adjusted to the new job.", "phrase": "adjust to 适应", "level": "CET4"},
        {"word": "admire", "phonetic": "/ədˈmaɪər/", "definition": "v. 钦佩；欣赏", "example": "I admire her courage.", "example2": "We admired the beautiful view.", "phrase": "admire sb. for 因…钦佩某人", "level": "CET4"},
        {"word": "affect", "phonetic": "/əˈfekt/", "definition": "v. 影响", "example": "The weather affects our mood.", "example2": "The decision affects everyone.", "phrase": "be affected by 受…影响", "level": "CET4", "tags": "高频"},
        {"word": "alternative", "phonetic": "/ɔːlˈtɜːnətɪv/", "definition": "n. 替代方案 adj. 可供选择的", "example": "We need an alternative route.", "example2": "There is no alternative but to wait.", "phrase": "an alternative to 替代方案", "level": "CET4"},
        {"word": "ambition", "phonetic": "/æmˈbɪʃn/", "definition": "n. 抱负；野心", "example": "Her ambition is to become a doctor.", "example2": "He has great ambitions.", "phrase": "achieve one's ambition 实现抱负", "level": "CET4"},
        {"word": "analyze", "phonetic": "/ˈænəlaɪz/", "definition": "v. 分析", "example": "We need to analyze the results.", "example2": "Scientists analyzed the data.", "phrase": "analyze the problem 分析问题", "level": "CET4", "tags": "高频"},
        {"word": "ancient", "phonetic": "/ˈeɪnʃənt/", "definition": "adj. 古代的", "example": "They visited ancient temples.", "example2": "We studied ancient history.", "phrase": "ancient times 古代", "level": "CET4"},
        {"word": "annual", "phonetic": "/ˈænjuəl/", "definition": "adj. 每年的", "example": "The annual meeting is in June.", "example2": "They held an annual festival.", "phrase": "annual report 年度报告", "level": "CET4"},
        {"word": "appreciate", "phonetic": "/əˈpriːʃieɪt/", "definition": "v. 感激；欣赏", "example": "I really appreciate your help.", "example2": "We appreciate good music.", "phrase": "appreciate doing 感激做", "level": "CET4", "tags": "高频"},
        {"word": "approach", "phonetic": "/əˈprəʊtʃ/", "definition": "n. 方法 v. 接近", "example": "We need a new approach to the problem.", "example2": "The bus is approaching.", "phrase": "approach to sth. 解决…的方法", "level": "CET4", "tags": "高频"},
        {"word": "appropriate", "phonetic": "/əˈprəʊpriət/", "definition": "adj. 恰当的", "example": "Wear appropriate clothes for the interview.", "example2": "The book is appropriate for children.", "phrase": "be appropriate for 适合", "level": "CET4"},
        {"word": "assess", "phonetic": "/əˈses/", "definition": "v. 评估", "example": "Teachers assess students' progress.", "example2": "We need to assess the damage.", "phrase": "assess the risk 评估风险", "level": "CET4"},
        {"word": "assume", "phonetic": "/əˈsjuːm/", "definition": "v. 假定；承担", "example": "Let's assume the story is true.", "example2": "He assumed responsibility.", "phrase": "assume that 假定", "level": "CET4"},
        {"word": "attach", "phonetic": "/əˈtætʃ/", "definition": "v. 附上；重视", "example": "Please attach the file to the email.", "example2": "She attaches great importance to health.", "phrase": "attach importance to 重视", "level": "CET4"},
        {"word": "attitude", "phonetic": "/ˈætɪtjuːd/", "definition": "n. 态度", "example": "A positive attitude matters.", "example2": "He has a bad attitude.", "phrase": "attitude towards 对…的态度", "level": "CET4", "tags": "高频"},
        {"word": "aware", "phonetic": "/əˈweər/", "definition": "adj. 意识到的", "example": "Be aware of the risks.", "example2": "He was aware of the danger.", "phrase": "be aware of 意识到", "level": "CET4"},
        {"word": "benefit", "phonetic": "/ˈbenɪfɪt/", "definition": "n. 利益 v. 有益于", "example": "Exercise benefits your health.", "example2": "Both sides benefit from the deal.", "phrase": "benefit from 从…获益", "level": "CET4", "tags": "高频"},
        {"word": "budget", "phonetic": "/ˈbʌdʒɪt/", "definition": "n. 预算", "example": "We have a limited budget.", "example2": "The trip was over budget.", "phrase": "on a budget 节省开支", "level": "CET4"},
        {"word": "capable", "phonetic": "/ˈkeɪpəbl/", "definition": "adj. 有能力的", "example": "She is capable of solving this.", "example2": "He is a capable leader.", "phrase": "be capable of 有能力做", "level": "CET4"},
        {"word": "challenge", "phonetic": "/ˈtʃælɪndʒ/", "definition": "n. 挑战 v. 向…挑战", "example": "Learning English is a challenge.", "example2": "He challenged me to a game.", "phrase": "face a challenge 面对挑战", "level": "CET4", "tags": "高频"},
        {"word": "commit", "phonetic": "/kəˈmɪt/", "definition": "v. 承诺；犯（错）", "example": "She committed herself to the project.", "example2": "He committed a mistake.", "phrase": "commit oneself to 致力于", "level": "CET4"},
        {"word": "community", "phonetic": "/kəˈmjuːnəti/", "definition": "n. 社区；团体", "example": "The community helped rebuild the school.", "example2": "She works for her community.", "phrase": "local community 当地社区", "level": "CET4", "tags": "高频"},
        {"word": "complex", "phonetic": "/ˈkɒmpleks/", "definition": "adj. 复杂的", "example": "It is a complex problem.", "example2": "The human brain is complex.", "phrase": "complex system 复杂系统", "level": "CET4"},
        {"word": "concentrate", "phonetic": "/ˈkɒnsntreɪt/", "definition": "v. 集中；专心", "example": "Concentrate on your work.", "example2": "I can't concentrate with the noise.", "phrase": "concentrate on 专注于", "level": "CET4"},
        {"word": "conclude", "phonetic": "/kənˈkluːd/", "definition": "v. 得出结论；结束", "example": "We concluded that he was right.", "example2": "The meeting concluded at noon.", "phrase": "conclude that 得出结论", "level": "CET4"},
        {"word": "confidence", "phonetic": "/ˈkɒnfɪdəns/", "definition": "n. 信心", "example": "Speak with confidence.", "example2": "She gained confidence from the win.", "phrase": "have confidence in 对…有信心", "level": "CET4", "tags": "高频"},
        {"word": "considerable", "phonetic": "/kənˈsɪdərəbl/", "definition": "adj. 相当大的", "example": "It took a considerable amount of time.", "example2": "He has considerable influence.", "phrase": "considerable amount 大量", "level": "CET4"},
        {"word": "constant", "phonetic": "/ˈkɒnstənt/", "definition": "adj. 持续的；不变的", "example": "She needs constant attention.", "example2": "The machine runs at a constant speed.", "phrase": "constant change 持续变化", "level": "CET4"},
        {"word": "consult", "phonetic": "/kənˈsʌlt/", "definition": "v. 咨询；查阅", "example": "Consult a doctor if you feel ill.", "example2": "He consulted the dictionary.", "phrase": "consult sb. about 就…咨询某人", "level": "CET4"},
        {"word": "contribute", "phonetic": "/kənˈtrɪbjuːt/", "definition": "v. 贡献；促成", "example": "Everyone can contribute ideas.", "example2": "Exercise contributes to good health.", "phrase": "contribute to 有助于", "level": "CET4", "tags": "高频"},
        {"word": "convince", "phonetic": "/kənˈvɪns/", "definition": "v. 使信服", "example": "I convinced him to stay.", "example2": "She convinced me of her honesty.", "phrase": "convince sb. of 使某人相信", "level": "CET4"},
        {"word": "create", "phonetic": "/kriˈeɪt/", "definition": "v. 创造；引起", "example": "The artist created a masterpiece.", "example2": "The plan created a lot of interest.", "phrase": "create jobs 创造就业", "level": "CET4"},
        {"word": "culture", "phonetic": "/ˈkʌltʃər/", "definition": "n. 文化", "example": "China has a rich culture.", "example2": "We learned about local culture.", "phrase": "culture shock 文化冲击", "level": "CET4", "tags": "高频"},
        {"word": "demand", "phonetic": "/dɪˈmɑːnd/", "definition": "n./v. 需求；要求", "example": "There is a high demand for engineers.", "example2": "The work demands great skill.", "phrase": "in demand 需求大", "level": "CET4"},
        {"word": "design", "phonetic": "/dɪˈzaɪn/", "definition": "n./v. 设计", "example": "She designs beautiful clothes.", "example2": "The building has a modern design.", "phrase": "by design 有意地", "level": "CET4"},
        {"word": "determine", "phonetic": "/dɪˈtɜːmɪn/", "definition": "v. 决定；测定", "example": "Your attitude determines your success.", "example2": "We determined the cost.", "phrase": "be determined to 决心", "level": "CET4"},
        {"word": "differ", "phonetic": "/ˈdɪfər/", "definition": "v. 不同", "example": "Their opinions differ.", "example2": "The two books differ in style.", "phrase": "differ from 与…不同", "level": "CET4"},
        {"word": "efficient", "phonetic": "/ɪˈfɪʃnt/", "definition": "adj. 高效的", "example": "This is an efficient method.", "example2": "The new engine is more efficient.", "phrase": "efficient way 高效方式", "level": "CET4"},
        {"word": "emphasize", "phonetic": "/ˈemfəsaɪz/", "definition": "v. 强调", "example": "The teacher emphasized the key points.", "example2": "He emphasized the importance of safety.", "phrase": "emphasize the importance 强调重要性", "level": "CET4"},
        {"word": "ensure", "phonetic": "/ɪnˈʃʊər/", "definition": "v. 确保", "example": "Please ensure the door is locked.", "example2": "Good planning ensures success.", "phrase": "ensure that 确保", "level": "CET4"},
        {"word": "estimate", "phonetic": "/ˈestɪmeɪt/", "definition": "v. 估计 n. 估价", "example": "We estimated the cost at 500 yuan.", "example2": "His estimate was too low.", "phrase": "rough estimate 粗略估计", "level": "CET4"},
        {"word": "evidence", "phonetic": "/ˈevɪdəns/", "definition": "n. 证据", "example": "There is no evidence of the crime.", "example2": "The evidence supports his story.", "phrase": "evidence for 关于…的证据", "level": "CET4"},
        {"word": "expand", "phonetic": "/ɪkˈspænd/", "definition": "v. 扩大；扩展", "example": "The company plans to expand.", "example2": "Water expands when heated.", "phrase": "expand the market 拓展市场", "level": "CET4"},
    ],
    "cet6": [
        {"word": "abstract", "phonetic": "/ˈæbstrækt/", "definition": "adj. 抽象的 n. 摘要", "example": "The idea is too abstract for children.", "example2": "Write an abstract of your paper.", "phrase": "abstract concept 抽象概念", "level": "CET6"},
        {"word": "academic", "phonetic": "/ˌækəˈdemɪk/", "definition": "adj. 学术的", "example": "He has a strong academic background.", "example2": "The article is too academic.", "phrase": "academic research 学术研究", "level": "CET6"},
        {"word": "accommodate", "phonetic": "/əˈkɒmədeɪt/", "definition": "v. 容纳；适应", "example": "The hotel can accommodate 200 guests.", "example2": "He accommodated to the new rules.", "phrase": "accommodate to 适应", "level": "CET6"},
        {"word": "accumulate", "phonetic": "/əˈkjuːmjəleɪt/", "definition": "v. 积累", "example": "Dust accumulated on the shelf.", "example2": "He accumulated a lot of experience.", "phrase": "accumulate wealth 积累财富", "level": "CET6"},
        {"word": "advocate", "phonetic": "/ˈædvəkeɪt/", "definition": "v. 提倡 n. 倡导者", "example": "Many experts advocate a balanced diet.", "example2": "She is an advocate of human rights.", "phrase": "advocate for 提倡", "level": "CET6"},
        {"word": "anticipate", "phonetic": "/ænˈtɪsɪpeɪt/", "definition": "v. 预期；预料", "example": "We anticipate a rise in prices.", "example2": "She anticipated his arrival.", "phrase": "anticipate doing 预期做", "level": "CET6"},
        {"word": "apparent", "phonetic": "/əˈpærənt/", "definition": "adj. 明显的；表面上的", "example": "It was apparent that she was tired.", "example2": "His apparent honesty fooled us.", "phrase": "apparent to 对…明显", "level": "CET6"},
        {"word": "arbitrary", "phonetic": "/ˈɑːbɪtrəri/", "definition": "adj. 任意的；武断的", "example": "The decision seemed arbitrary.", "example2": "He chose the numbers at random, quite arbitrarily.", "phrase": "arbitrary choice 随意选择", "level": "CET6"},
        {"word": "authentic", "phonetic": "/ɔːˈθentɪk/", "definition": "adj. 真实的；正宗的", "example": "We had authentic Chinese food.", "example2": "The signature is authentic.", "phrase": "authentic experience 真实体验", "level": "CET6"},
        {"word": "barrier", "phonetic": "/ˈbæriər/", "definition": "n. 障碍；屏障", "example": "Language is a barrier to communication.", "example2": "The mountains form a natural barrier.", "phrase": "barrier to 对…的障碍", "level": "CET6"},
        {"word": "campaign", "phonetic": "/kæmˈpeɪn/", "definition": "n. 运动；活动", "example": "They launched an ad campaign.", "example2": "The campaign against smoking worked.", "phrase": "election campaign 竞选活动", "level": "CET6"},
        {"word": "circumstance", "phonetic": "/ˈsɜːkəmstəns/", "definition": "n. 环境；情况", "example": "Under no circumstances give up.", "example2": "The circumstances have changed.", "phrase": "under the circumstances 在这种情况下", "level": "CET6"},
        {"word": "coincide", "phonetic": "/ˌkəʊɪnˈsaɪd/", "definition": "v. 同时发生；一致", "example": "My holiday coincides with hers.", "example2": "Their opinions coincide.", "phrase": "coincide with 与…一致", "level": "CET6"},
        {"word": "compensate", "phonetic": "/ˈkɒmpenseɪt/", "definition": "v. 补偿", "example": "The company compensated the workers.", "example2": "Nothing can compensate for the loss.", "phrase": "compensate for 补偿", "level": "CET6"},
        {"word": "comprehensive", "phonetic": "/ˌkɒmprɪˈhensɪv/", "definition": "adj. 全面的", "example": "The report is comprehensive.", "example2": "We offer comprehensive training.", "phrase": "comprehensive plan 全面计划", "level": "CET6"},
        {"word": "consequence", "phonetic": "/ˈkɒnsɪkwəns/", "definition": "n. 结果；后果", "example": "Think about the consequences.", "example2": "He faced the consequences of his actions.", "phrase": "as a consequence 结果", "level": "CET6"},
        {"word": "conventional", "phonetic": "/kənˈvenʃənl/", "definition": "adj. 传统的；常规的", "example": "This is a conventional method.", "example2": "She rejected conventional ideas.", "phrase": "conventional wisdom 传统观念", "level": "CET6"},
        {"word": "crucial", "phonetic": "/ˈkruːʃl/", "definition": "adj. 关键的", "example": "Timing is crucial in business.", "example2": "This decision is crucial to our plan.", "phrase": "be crucial to 对…至关重要", "level": "CET6"},
        {"word": "declare", "phonetic": "/dɪˈkleər/", "definition": "v. 宣布；申报", "example": "The government declared a holiday.", "example2": "He declared his income.", "phrase": "declare war 宣战", "level": "CET6"},
        {"word": "deliberate", "phonetic": "/dɪˈlɪbərət/", "definition": "adj. 故意的；深思熟虑的", "example": "It was a deliberate lie.", "example2": "He made a deliberate choice.", "phrase": "deliberate attempt 蓄意行为", "level": "CET6"},
        {"word": "deteriorate", "phonetic": "/dɪˈtɪəriəreɪt/", "definition": "v. 恶化", "example": "His health deteriorated quickly.", "example2": "The weather deteriorated.", "phrase": "deteriorate rapidly 迅速恶化", "level": "CET6"},
        {"word": "diminish", "phonetic": "/dɪˈmɪnɪʃ/", "definition": "v. 减少；降低", "example": "The pain diminished gradually.", "example2": "His influence diminished.", "phrase": "diminish the risk 降低风险", "level": "CET6"},
        {"word": "discrimination", "phonetic": "/dɪˌskrɪmɪˈneɪʃn/", "definition": "n. 歧视；区别", "example": "Racial discrimination is illegal.", "example2": "She faced discrimination at work.", "phrase": "discrimination against 对…的歧视", "level": "CET6"},
        {"word": "distinguish", "phonetic": "/dɪˈstɪŋɡwɪʃ/", "definition": "v. 区分；辨别", "example": "Can you distinguish the twins?", "example2": "He distinguished himself in sports.", "phrase": "distinguish between 区分", "level": "CET6"},
        {"word": "dominate", "phonetic": "/ˈdɒmɪneɪt/", "definition": "v. 支配；主导", "example": "One team dominated the game.", "example2": "Big companies dominate the market.", "phrase": "dominate the market 主导市场", "level": "CET6"},
        {"word": "eliminate", "phonetic": "/ɪˈlɪmɪneɪt/", "definition": "v. 消除；淘汰", "example": "We must eliminate the errors.", "example2": "He was eliminated in the first round.", "phrase": "eliminate poverty 消除贫困", "level": "CET6"},
        {"word": "enhance", "phonetic": "/ɪnˈhɑːns/", "definition": "v. 增强；提高", "example": "Reading enhances your vocabulary.", "example2": "The new system enhances efficiency.", "phrase": "enhance the ability 增强能力", "level": "CET6"},
        {"word": "evident", "phonetic": "/ˈevɪdənt/", "definition": "adj. 明显的", "example": "It was evident that she was upset.", "example2": "The damage is evident.", "phrase": "be evident that 很明显", "level": "CET6"},
        {"word": "exaggerate", "phonetic": "/ɪɡˈzædʒəreɪt/", "definition": "v. 夸大", "example": "He exaggerated the story.", "example2": "Don't exaggerate the problem.", "phrase": "exaggerate the importance 夸大重要性", "level": "CET6"},
        {"word": "exploit", "phonetic": "/ɪkˈsplɔɪt/", "definition": "v. 利用；剥削", "example": "We should exploit new resources.", "example2": "The workers were exploited.", "phrase": "exploit opportunities 利用机会", "level": "CET6"},
        {"word": "extensive", "phonetic": "/ɪkˈstensɪv/", "definition": "adj. 广泛的；大量的", "example": "He has extensive knowledge.", "example2": "The fire caused extensive damage.", "phrase": "extensive use 广泛使用", "level": "CET6"},
        {"word": "facilitate", "phonetic": "/fəˈsɪlɪteɪt/", "definition": "v. 促进；使便利", "example": "The bridge facilitates trade.", "example2": "Technology facilitates learning.", "phrase": "facilitate communication 促进沟通", "level": "CET6"},
        {"word": "identical", "phonetic": "/aɪˈdentɪkl/", "definition": "adj. 完全相同的", "example": "The twins look identical.", "example2": "Their answers were identical.", "phrase": "be identical to 与…完全相同", "level": "CET6"},
        {"word": "inherent", "phonetic": "/ɪnˈhɪərənt/", "definition": "adj. 固有的；内在的", "example": "Risk is inherent in business.", "example2": "There are inherent dangers in the job.", "phrase": "be inherent in 内在的", "level": "CET6"},
        {"word": "intricate", "phonetic": "/ˈɪntrɪkət/", "definition": "adj. 复杂精细的", "example": "The carpet has an intricate pattern.", "example2": "The story has an intricate plot.", "phrase": "intricate details 精细细节", "level": "CET6"},
        {"word": "legitimate", "phonetic": "/lɪˈdʒɪtɪmət/", "definition": "adj. 合法的；正当的", "example": "He has a legitimate reason.", "example2": "The company is a legitimate business.", "phrase": "legitimate right 合法权利", "level": "CET6"},
        {"word": "notorious", "phonetic": "/nəʊˈtɔːriəs/", "definition": "adj. 臭名昭著的", "example": "The area is notorious for crime.", "example2": "He is a notorious liar.", "phrase": "be notorious for 因…而臭名昭著", "level": "CET6"},
        {"word": "prevail", "phonetic": "/prɪˈveɪl/", "definition": "v. 盛行；占上风", "example": "Justice will prevail.", "example2": "This custom still prevails.", "phrase": "prevail over 胜过", "level": "CET6"},
        {"word": "resemble", "phonetic": "/rɪˈzembl/", "definition": "v. 相似", "example": "She resembles her mother.", "example2": "The two buildings resemble each other.", "phrase": "resemble each other 彼此相似", "level": "CET6"},
        {"word": "sophisticated", "phonetic": "/səˈfɪstɪkeɪtɪd/", "definition": "adj. 复杂的；老练的", "example": "The device is highly sophisticated.", "example2": "She has sophisticated taste.", "phrase": "sophisticated technology 尖端技术", "level": "CET6"},
        {"word": "substantial", "phonetic": "/səbˈstænʃl/", "definition": "adj. 大量的；实质的", "example": "They made substantial progress.", "example2": "It requires a substantial amount of money.", "phrase": "substantial evidence 充分证据", "level": "CET6"},
        {"word": "transcend", "phonetic": "/trænˈsend/", "definition": "v. 超越", "example": "Art transcends cultural boundaries.", "example2": "The film transcends time.", "phrase": "transcend boundaries 超越界限", "level": "CET6"},
        {"word": "verify", "phonetic": "/ˈverɪfaɪ/", "definition": "v. 核实；验证", "example": "Please verify the information.", "example2": "The results were verified by experts.", "phrase": "verify the facts 核实事实", "level": "CET6"},
        {"word": "vulnerable", "phonetic": "/ˈvʌlnərəbl/", "definition": "adj. 脆弱的；易受伤的", "example": "Children are vulnerable to disease.", "example2": "The system is vulnerable to attack.", "phrase": "be vulnerable to 易受…影响", "level": "CET6"},
    ],
    "kaoyan": [
        {"word": "abolish", "phonetic": "/əˈbɒlɪʃ/", "definition": "v. 废除", "example": "The old law was abolished.", "example2": "Many hope to abolish the fee.", "phrase": "abolish the system 废除制度", "level": "考研"},
        {"word": "abundant", "phonetic": "/əˈbʌndənt/", "definition": "adj. 丰富的；充裕的", "example": "The region is abundant in resources.", "example2": "We have abundant evidence.", "phrase": "be abundant in 富于", "level": "考研"},
        {"word": "accelerate", "phonetic": "/əkˈseləreɪt/", "definition": "v. 加速", "example": "The car accelerated quickly.", "example2": "Economic growth is accelerating.", "phrase": "accelerate the pace 加快步伐", "level": "考研"},
        {"word": "acknowledge", "phonetic": "/əkˈnɒlɪdʒ/", "definition": "v. 承认；致谢", "example": "He acknowledged his mistake.", "example2": "She acknowledged my help.", "phrase": "acknowledge the fact 承认事实", "level": "考研"},
        {"word": "adequate", "phonetic": "/ˈædɪkwət/", "definition": "adj. 足够的；适当的", "example": "We have adequate time.", "example2": "The supply is adequate for the demand.", "phrase": "adequate to 足以", "level": "考研"},
        {"word": "adverse", "phonetic": "/ˈædvɜːs/", "definition": "adj. 不利的；相反的", "example": "Adverse weather delayed the flight.", "example2": "It had an adverse effect on sales.", "phrase": "adverse effect 不利影响", "level": "考研"},
        {"word": "aggregate", "phonetic": "/ˈæɡrɪɡət/", "definition": "n. 总数 adj. 总的", "example": "The aggregate of the losses was huge.", "example2": "We look at aggregate data.", "phrase": "in aggregate 总体而言", "level": "考研"},
        {"word": "alleviate", "phonetic": "/əˈliːvieɪt/", "definition": "v. 减轻；缓解", "example": "The medicine alleviated the pain.", "example2": "The policy helps alleviate poverty.", "phrase": "alleviate the burden 减轻负担", "level": "考研"},
        {"word": "ambiguous", "phonetic": "/æmˈbɪɡjuəs/", "definition": "adj. 模棱两可的", "example": "The wording is ambiguous.", "example2": "He gave an ambiguous answer.", "phrase": "ambiguous statement 含糊其辞", "level": "考研"},
        {"word": "ample", "phonetic": "/ˈæmpl/", "definition": "adj. 充足的；宽敞的", "example": "There is ample time to finish.", "example2": "The room has ample space.", "phrase": "ample evidence 充足证据", "level": "考研"},
        {"word": "animate", "phonetic": "/ˈænɪmeɪt/", "definition": "v. 使有生气 adj. 有生命的", "example": "The discussion animated the class.", "example2": "Animate beings need air.", "phrase": "animate the debate 活跃讨论", "level": "考研"},
        {"word": "apprehend", "phonetic": "/ˌæprɪˈhend/", "definition": "v. 理解；逮捕", "example": "She apprehended the danger.", "example2": "The police apprehended the thief.", "phrase": "apprehend the meaning 理解含义", "level": "考研"},
        {"word": "ascertain", "phonetic": "/ˌæsəˈteɪn/", "definition": "v. 查明；确定", "example": "We need to ascertain the facts.", "example2": "It is hard to ascertain the truth.", "phrase": "ascertain the cause 查明原因", "level": "考研"},
        {"word": "assent", "phonetic": "/əˈsent/", "definition": "n./v. 同意；赞成", "example": "He gave his assent to the plan.", "example2": "She assented to the proposal.", "phrase": "with the assent of 经…同意", "level": "考研"},
        {"word": "bewilder", "phonetic": "/bɪˈwɪldər/", "definition": "v. 使迷惑", "example": "The maze bewildered the visitors.", "example2": "I was bewildered by the news.", "phrase": "be bewildered by 被…弄糊涂", "level": "考研"},
        {"word": "candid", "phonetic": "/ˈkændɪd/", "definition": "adj. 坦率的", "example": "She gave a candid opinion.", "example2": "He was candid about his failures.", "phrase": "to be candid 坦白说", "level": "考研"},
        {"word": "coherent", "phonetic": "/kəʊˈhɪərənt/", "definition": "adj. 连贯的；一致的", "example": "He gave a coherent explanation.", "example2": "The essay lacks a coherent structure.", "phrase": "coherent argument 连贯论证", "level": "考研"},
        {"word": "compatible", "phonetic": "/kəmˈpætəbl/", "definition": "adj. 兼容的；合得来的", "example": "The software is compatible with Windows.", "example2": "They are compatible partners.", "phrase": "be compatible with 与…兼容", "level": "考研"},
        {"word": "conform", "phonetic": "/kənˈfɔːm/", "definition": "v. 遵守；符合", "example": "The product conforms to safety standards.", "example2": "Students must conform to the rules.", "phrase": "conform to 符合", "level": "考研"},
        {"word": "conspicuous", "phonetic": "/kənˈspɪkjuəs/", "definition": "adj. 显眼的；明显的", "example": "Her red coat is conspicuous.", "example2": "He was conspicuous for his absence.", "phrase": "conspicuous by 因…而显眼", "level": "考研"},
        {"word": "deduce", "phonetic": "/dɪˈdjuːs/", "definition": "v. 推断", "example": "We deduced the answer from the clues.", "example2": "From the facts, I deduce he left.", "phrase": "deduce from 从…推断", "level": "考研"},
        {"word": "deficit", "phonetic": "/ˈdefɪsɪt/", "definition": "n. 赤字；亏空", "example": "The country has a trade deficit.", "example2": "The budget deficit is growing.", "phrase": "trade deficit 贸易逆差", "level": "考研"},
        {"word": "deviate", "phonetic": "/ˈdiːvieɪt/", "definition": "v. 偏离", "example": "The plane deviated from its course.", "example2": "He never deviates from his principles.", "phrase": "deviate from 偏离", "level": "考研"},
        {"word": "dilemma", "phonetic": "/dɪˈlemə/", "definition": "n. 困境；两难", "example": "She faced a dilemma.", "example2": "He was in a dilemma about the offer.", "phrase": "in a dilemma 处于两难", "level": "考研"},
        {"word": "disperse", "phonetic": "/dɪˈspɜːs/", "definition": "v. 分散；驱散", "example": "The crowd dispersed quickly.", "example2": "The wind dispersed the clouds.", "phrase": "disperse the crowd 驱散人群", "level": "考研"},
        {"word": "diverse", "phonetic": "/daɪˈvɜːs/", "definition": "adj. 多样的", "example": "The city has a diverse culture.", "example2": "They held diverse opinions.", "phrase": "diverse backgrounds 多元背景", "level": "考研"},
        {"word": "elaborate", "phonetic": "/ɪˈlæbərət/", "definition": "adj. 精心制作的 v. 详细说明", "example": "She gave an elaborate explanation.", "example2": "Please elaborate on your idea.", "phrase": "elaborate on 详细阐述", "level": "考研"},
        {"word": "eloquent", "phonetic": "/ˈeləkwənt/", "definition": "adj. 雄辩的；有说服力的", "example": "He is an eloquent speaker.", "example2": "Her speech was eloquent.", "phrase": "eloquent speech 雄辩的演讲", "level": "考研"},
        {"word": "explicit", "phonetic": "/ɪkˈsplɪsɪt/", "definition": "adj. 明确的；直率的", "example": "He gave explicit instructions.", "example2": "The rules are explicit.", "phrase": "explicit statement 明确声明", "level": "考研"},
        {"word": "feasible", "phonetic": "/ˈfiːzəbl/", "definition": "adj. 可行的", "example": "The plan is feasible.", "example2": "We found a feasible solution.", "phrase": "feasible plan 可行计划", "level": "考研"},
        {"word": "formidable", "phonetic": "/ˈfɔːmɪdəbl/", "definition": "adj. 强大的；难对付的", "example": "They faced a formidable opponent.", "example2": "The task is formidable.", "phrase": "formidable challenge 艰巨挑战", "level": "考研"},
        {"word": "hamper", "phonetic": "/ˈhæmpər/", "definition": "v. 妨碍；阻碍", "example": "The rain hampered the rescue.", "example2": "Lack of funds hampered progress.", "phrase": "hamper progress 阻碍进展", "level": "考研"},
        {"word": "hypothesis", "phonetic": "/haɪˈpɒθəsɪs/", "definition": "n. 假设", "example": "The experiment tested a hypothesis.", "example2": "His hypothesis proved wrong.", "phrase": "test a hypothesis 检验假设", "level": "考研"},
        {"word": "implicit", "phonetic": "/ɪmˈplɪsɪt/", "definition": "adj. 含蓄的；暗示的", "example": "There is an implicit agreement.", "example2": "Her words carried an implicit warning.", "phrase": "implicit in 蕴含于", "level": "考研"},
        {"word": "indispensable", "phonetic": "/ˌɪndɪˈspensəbl/", "definition": "adj. 不可或缺的", "example": "Water is indispensable to life.", "example2": "She is indispensable to the team.", "phrase": "be indispensable to 对…不可或缺", "level": "考研"},
        {"word": "inevitable", "phonetic": "/ɪnˈevɪtəbl/", "definition": "adj. 不可避免的", "example": "Change is inevitable.", "example2": "It was an inevitable result.", "phrase": "inevitable consequence 必然结果", "level": "考研"},
        {"word": "intact", "phonetic": "/ɪnˈtækt/", "definition": "adj. 完好无损的", "example": "The building survived intact.", "example2": "His reputation remained intact.", "phrase": "keep intact 保持完好", "level": "考研"},
        {"word": "intrinsic", "phonetic": "/ɪnˈtrɪnsɪk/", "definition": "adj. 固有的；内在的", "example": "Learning has intrinsic value.", "example2": "The intrinsic quality matters.", "phrase": "intrinsic value 内在价值", "level": "考研"},
        {"word": "meticulous", "phonetic": "/məˈtɪkjələs/", "definition": "adj. 一丝不苟的", "example": "He is meticulous in his work.", "example2": "The report was meticulously prepared.", "phrase": "meticulous attention 细致关注", "level": "考研"},
        {"word": "notion", "phonetic": "/ˈnəʊʃn/", "definition": "n. 概念；观念", "example": "He has a clear notion of justice.", "example2": "She rejected the old notion.", "phrase": "notion of 关于…的观念", "level": "考研"},
        {"word": "paradox", "phonetic": "/ˈpærədɒks/", "definition": "n. 悖论；矛盾", "example": "It is a paradox that he is both popular and lonely.", "example2": "The idea sounds like a paradox.", "phrase": "ironic paradox 讽刺的矛盾", "level": "考研"},
        {"word": "persuade", "phonetic": "/pəˈsweɪd/", "definition": "v. 说服", "example": "He persuaded me to join.", "example2": "She persuaded him of the truth.", "phrase": "persuade sb. to do 说服某人做", "level": "考研"},
        {"word": "plausible", "phonetic": "/ˈplɔːzəbl/", "definition": "adj. 貌似合理的", "example": "It sounds like a plausible excuse.", "example2": "Her explanation is plausible.", "phrase": "plausible reason 貌似合理的理由", "level": "考研"},
        {"word": "profound", "phonetic": "/prəˈfaʊnd/", "definition": "adj. 深刻的；深远的", "example": "The event had profound effects.", "example2": "He is a profound thinker.", "phrase": "profound insight 深刻见解", "level": "考研"},
        {"word": "stringent", "phonetic": "/ˈstrɪndʒənt/", "definition": "adj. 严格的；严厉的", "example": "The safety rules are stringent.", "example2": "The bank has stringent standards.", "phrase": "stringent measures 严厉措施", "level": "考研"},
        {"word": "sustain", "phonetic": "/səˈsteɪn/", "definition": "v. 维持；支撑", "example": "The body needs food to sustain life.", "example2": "He sustained the argument.", "phrase": "sustain development 维持发展", "level": "考研"},
        {"word": "terminate", "phonetic": "/ˈtɜːmɪneɪt/", "definition": "v. 终止；结束", "example": "The contract was terminated.", "example2": "The meeting terminated at noon.", "phrase": "terminate a contract 终止合同", "level": "考研"},
        {"word": "undermine", "phonetic": "/ˌʌndəˈmaɪn/", "definition": "v. 削弱；破坏", "example": "The rumor undermined his reputation.", "example2": "Stress undermines health.", "phrase": "undermine authority 削弱权威", "level": "考研"},
    ],
    "daily": [
        {"word": "awesome", "phonetic": "/ˈɔːsəm/", "definition": "adj. 太棒了；令人惊叹的", "example": "That movie was awesome!", "example2": "You did an awesome job.", "phrase": "awesome idea 好主意", "level": "日常口语"},
        {"word": "bother", "phonetic": "/ˈbɒðər/", "definition": "v. 打扰；麻烦", "example": "Sorry to bother you.", "example2": "Don't bother about it.", "phrase": "sorry to bother 抱歉打扰", "level": "日常口语"},
        {"word": "brunch", "phonetic": "/brʌntʃ/", "definition": "n. 早午餐", "example": "Let's have brunch on Sunday.", "example2": "We ordered brunch at the cafe.", "phrase": "have brunch 吃早午餐", "level": "日常口语"},
        {"word": "candidate", "phonetic": "/ˈkændɪdət/", "definition": "n. 候选人", "example": "She is a strong candidate.", "example2": "There are three candidates.", "phrase": "a candidate for 候选人", "level": "日常口语"},
        {"word": "crazy", "phonetic": "/ˈkreɪzi/", "definition": "adj. 疯狂的；着迷的", "example": "Are you crazy?", "example2": "I'm crazy about football.", "phrase": "crazy about 对…着迷", "level": "日常口语"},
        {"word": "definitely", "phonetic": "/ˈdefɪnətli/", "definition": "adv. 肯定地；当然", "example": "I will definitely come.", "example2": "That's definitely a good idea.", "phrase": "definitely agree 完全同意", "level": "日常口语"},
        {"word": "delicious", "phonetic": "/dɪˈlɪʃəs/", "definition": "adj. 美味的", "example": "The soup is delicious.", "example2": "Thanks for the delicious dinner.", "phrase": "delicious food 美味食物", "level": "日常口语"},
        {"word": "fine", "phonetic": "/faɪn/", "definition": "adj. 好的；健康的", "example": "I'm fine, thank you.", "example2": "Everything is fine.", "phrase": "I'm fine 我很好", "level": "日常口语"},
        {"word": "guess", "phonetic": "/ɡes/", "definition": "v. 猜 n. 猜测", "example": "Guess what I found!", "example2": "It's just a guess.", "phrase": "guess what 你猜怎么着", "level": "日常口语"},
        {"word": "hang out", "phonetic": "/hæŋ aʊt/", "definition": "v. 闲逛；一起玩", "example": "Let's hang out this weekend.", "example2": "We hung out at the mall.", "phrase": "hang out with 和…出去玩", "level": "日常口语"},
        {"word": "hurry", "phonetic": "/ˈhʌri/", "definition": "v. 赶紧 n. 匆忙", "example": "Hurry up, we're late!", "example2": "He left in a hurry.", "phrase": "hurry up 快点", "level": "日常口语"},
        {"word": "maybe", "phonetic": "/ˈmeɪbi/", "definition": "adv. 也许；可能", "example": "Maybe we can meet later.", "example2": "Maybe he is right.", "phrase": "maybe not 也许不是", "level": "日常口语"},
        {"word": "miss", "phonetic": "/mɪs/", "definition": "v. 想念；错过", "example": "I miss my family.", "example2": "Don't miss the bus!", "phrase": "miss the chance 错过机会", "level": "日常口语"},
        {"word": "offer", "phonetic": "/ˈɒfər/", "definition": "v. 提供；提出", "example": "He offered me a ride.", "example2": "She offered her help.", "phrase": "offer to do 主动提出做", "level": "日常口语"},
        {"word": "order", "phonetic": "/ˈɔːdər/", "definition": "v. 点餐；命令 n. 订单", "example": "I'd like to order a pizza.", "example2": "Can we order now?", "phrase": "order food 点餐", "level": "日常口语"},
        {"word": "really", "phonetic": "/ˈrɪəli/", "definition": "adv. 真的；确实", "example": "I really like this place.", "example2": "Really? That's great!", "phrase": "really good 真的很好", "level": "日常口语"},
        {"word": "recommend", "phonetic": "/ˌrekəˈmend/", "definition": "v. 推荐", "example": "Can you recommend a restaurant?", "example2": "I recommend this book.", "phrase": "recommend doing 推荐做", "level": "日常口语"},
        {"word": "schedule", "phonetic": "/ˈʃedjuːl/", "definition": "n. 时间表 v. 安排", "example": "My schedule is full.", "example2": "The meeting is scheduled for 9.", "phrase": "on schedule 准时", "level": "日常口语"},
        {"word": "sorry", "phonetic": "/ˈsɒri/", "definition": "adj. 抱歉的", "example": "I'm sorry for being late.", "example2": "Sorry, I didn't hear you.", "phrase": "sorry to hear 很遗憾听到", "level": "日常口语"},
        {"word": "tired", "phonetic": "/ˈtaɪəd/", "definition": "adj. 疲劳的", "example": "I'm tired after work.", "example2": "You look tired today.", "phrase": "be tired of 厌倦", "level": "日常口语"},
        {"word": "together", "phonetic": "/təˈɡeðər/", "definition": "adv. 一起", "example": "Let's study together.", "example2": "We worked together on it.", "phrase": "get together 聚会", "level": "日常口语"},
        {"word": "travel", "phonetic": "/ˈtrævl/", "definition": "v./n. 旅行", "example": "I love to travel.", "example2": "Travel broadens the mind.", "phrase": "travel around 环游", "level": "日常口语"},
        {"word": "weekend", "phonetic": "/ˌwiːkˈend/", "definition": "n. 周末", "example": "What are you doing this weekend?", "example2": "We camped last weekend.", "phrase": "at the weekend 在周末", "level": "日常口语"},
        {"word": "wonder", "phonetic": "/ˈwʌndər/", "definition": "v. 想知道 n. 奇迹", "example": "I wonder if it will rain.", "example2": "It's a wonder you arrived.", "phrase": "no wonder 难怪", "level": "日常口语"},
        {"word": "absolutely", "phonetic": "/ˈæbsəluːtli/", "definition": "adv. 绝对地；当然", "example": "Absolutely! I agree.", "example2": "It's absolutely perfect.", "phrase": "absolutely right 完全正确", "level": "日常口语"},
        {"word": "appointment", "phonetic": "/əˈpɔɪntmənt/", "definition": "n. 约会；预约", "example": "I have a doctor's appointment.", "example2": "Please make an appointment.", "phrase": "make an appointment 预约", "level": "日常口语"},
        {"word": "brilliant", "phonetic": "/ˈbrɪliənt/", "definition": "adj. 极好的；杰出的", "example": "That's a brilliant idea!", "example2": "She is a brilliant student.", "phrase": "brilliant performance 出色表现", "level": "日常口语"},
        {"word": "cheerful", "phonetic": "/ˈtʃɪəfl/", "definition": "adj. 快乐的；兴高采烈的", "example": "She always looks cheerful.", "example2": "He is in a cheerful mood.", "phrase": "cheerful mood 愉快的心情", "level": "日常口语"},
        {"word": "convenient", "phonetic": "/kənˈviːniənt/", "definition": "adj. 方便的", "example": "The store is very convenient.", "example2": "Is it convenient for you?", "phrase": "convenient to 对…方便", "level": "日常口语"},
        {"word": "embarrassed", "phonetic": "/ɪmˈbærəst/", "definition": "adj. 尴尬的", "example": "I felt embarrassed by my mistake.", "example2": "She was embarrassed to speak.", "phrase": "feel embarrassed 感到尴尬", "level": "日常口语"},
        {"word": "favorite", "phonetic": "/ˈfeɪvərɪt/", "definition": "n./adj. 最爱", "example": "What's your favorite food?", "example2": "This is my favorite season.", "phrase": "favorite thing 最爱之物", "level": "日常口语"},
        {"word": "promise", "phonetic": "/ˈprɒmɪs/", "definition": "v./n. 承诺；诺言", "example": "I promise to call you.", "example2": "He kept his promise.", "phrase": "keep a promise 遵守诺言", "level": "日常口语"},
        {"word": "suggestion", "phonetic": "/səˈdʒestʃən/", "definition": "n. 建议", "example": "Do you have any suggestions?", "example2": "Thanks for the suggestion.", "phrase": "a good suggestion 好建议", "level": "日常口语"},
        {"word": "umbrella", "phonetic": "/ʌmˈbrelə/", "definition": "n. 雨伞", "example": "Take an umbrella, it may rain.", "example2": "I left my umbrella at home.", "phrase": "open an umbrella 撑伞", "level": "日常口语"},
        {"word": "unbelievable", "phonetic": "/ˌʌnbɪˈliːvəbl/", "definition": "adj. 难以置信的", "example": "The story is unbelievable.", "example2": "It's unbelievable how fast time flies.", "phrase": "absolutely unbelievable 简直难以置信", "level": "日常口语"},
    ],
}
