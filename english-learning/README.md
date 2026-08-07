# 朝词浅阅（English Learning Website）

一个 PC 端英语学习网站：背单词、每日一读、学习打卡。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router（自研 CSS，无组件库） |
| 后端 | 复用仓库现有 FastAPI（`backend/`），新增 `/api/v1/english/*` |
| 数据库 | MySQL（现有 `lowcode_master`），英语数据在 master 库 + `tenant_id` 隔离 |

## 功能

- 固定顶部导航：Logo → 主导航（首页/词笺/浅读/归处）→ 留白 → 主题切换 → 账号区
- 浅色/深色主题，切换结果保存 `localStorage`（`english-theme`），刷新不重置
- 已登录头像下拉菜单（鼠标离开 1.5s 自动收起，含分隔线）：我的生词本 / 我的收藏 / 阅读笔记 / 打卡数据 / 账号设置 / 退出登录
- 游客访问私有页面弹出「需要登录」弹窗（不跳转）
- 页面内 Tab：背单词（每日学习/查看词库/单词测试/生词本/词库设置）、每日一读（今日一读/历史存档）、学习中心（每日打卡/学习数据总览/AI 学习日报）
- SPA 无刷新跳转

## 每日一读

轻量日常任务，每天推送 1 篇适配你词汇水平的短文（120-280 词），与每日背单词并行：

- **LLM 实时生成**：DeepSeek 按（日期×难度×题材）生成并缓存，读时秒开、历史永久存档可回看
- **难度 3 档自适应**：基础/四级/高阶，默认按背诵目标自动适配（答题正确率 <55% 降档、>85% 升档），可手动切换并立即重派今日文章
- **题材每日轮换**：趣味科普 / 生活故事 / 影视文摘 / 短句美文 / 应试短文
- **阅读工具**：朗读全文 + 语速（慢/标准/快）、遮罩模式（隐藏英文看中文自测）、全文翻译对照、划词查词
- **今日小测**：4-6 题文章词汇题（英译中/中译英/听音选义/单词填空），答对升级 SRS 间隔、答错自动收进生词库
- **生词联动**：划词收藏/答题做错的词汇自动进入主词书 SRS 新词流程，次日出现在背单词队列；标记熟词进黑名单不再重复收录
- **专项训练**：单词测试页新增「今日阅读生词专项训练」模式
- **打卡闭环**：完成今日一读打卡 → 阅读时长/篇数埋点 → AI 学习日报新增「每日一读」板块（完成状态/难度/正确率/新增生词/高频易错词）

## 背单词 SRS 系统

固定艾宾浩斯间隔复习（1→2→4→7→15 天），仅「认识/不认识」两个按钮：

- **每日流程**：先复习到期旧词 → 复习队列清空后解锁今日新词 → 全部完成自动打卡
- **继续学习**：学完一轮后弹窗询问「是否继续」，继续则从剩余未学词池再取一批新词（无每日上限），日统计按多轮累加
- **认识**：升级间隔（1→2→4→7→15），走完 15 天标记「已掌握」，不再复习
- **不认识**：间隔重置 1 天、次日复习、自动加入生词本；新词当天重复推送最多 3 次
- **新手引导**：首次进入背单词选目标（中小学/高中/四级/六级/考研/日常口语）→ 主词书 → 每日新词数（10/20/30/50）→ 发音
- **查看词库**：词库浏览按首字母 A-Z 分组，可给单词打分类标签（核心/常用/拓展），按分类筛选
- **按类型背诵**：背单词时选择分类，新词池只从该分类抽取；学习中也随时可切换分类重新选词
- **完整词库**：8 本考试词书（中小学/高中/四级/六级/考研/托福/雅思/GRE）+ 日常口语精选，共约 3.9 万词
  - 覆盖：音标 98%、词性 96%、例句 23%（核心考试词优先，例句来自词典 API 抓取）

## 词库数据来源

词库单词来自开源英汉词典数据 [ECDICT](https://github.com/skywind3000/ECDICT)（MIT 协议），
按其考试标签导入完整大纲词表。重新导入：

```bash
# 1. 下载 ecdict.csv（约 66MB）
git clone --depth 1 --filter=blob:none --sparse https://github.com/skywind3000/ECDICT
cd ECDICT && git sparse-checkout set --no-cone ecdict.csv

# 2. 导入（幂等，已存在的词跳过）
cd backend && python scripts/import_ecdict.py <ecdict.csv路径>
```
- **游客模式**：数据存浏览器 localStorage，登录后可一键同步到云端
- **断签**：到期词一次性按到期日升序复习，间隔不重置，连续打卡清零
- **清除数据**：词库设置 / 账号设置里可清除，回到全新状态

## 测试

```bash
# 后端英语服务（pytest：SRS/每日一读/AI日报/测试）
cd backend && python -m pytest app/tests/test_english_srs.py app/tests/test_daily_reading.py app/tests/test_daily_summary.py app/tests/test_english_test.py

# 前端 SRS 引擎状态机（vitest）
cd english-learning && npm test

# 引擎独立验证（Node 24 原生剥离 TS）
cd english-learning && npm run test:srs
```

## 路由

`/home` `/word` `/word/notebook` `/reading` `/reading/note`
`/study-center` `/study-center/checkin` `/collect` `/login` `/register` `/user/setting`

## 本地启动

### 1. 后端（FastAPI，端口 8001）

```bash
cd backend
# 安装依赖（已含 sentence-transformers 等）
pip install -e ".[dev]"
# 数据库迁移（新增英语表 + users.nickname/avatar）
alembic upgrade head
# 启动（首次启动自动创建 english 租户并播种示例单词/文章）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

> 需要本机 MySQL 运行（3306），`backend/.env` 配置 `MASTER_DB_*`。
> 登录/注册接口：`POST /api/v1/english/auth/register`（公开）、登录复用
> `POST /api/v1/tenant/auth/login_with_tenant?tenant_code=english`。

### 2. 前端（Vite，端口 5174）

```bash
cd english-learning
npm install
npm run dev   # http://localhost:5174
```

`vite.config.ts` 已将 `/api` 代理到 `http://localhost:8001`。

## 后端新增接口

统一响应包裹 `{ code, data, message }`，业务错误为 HTTP 200 + 非零 `code`。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/english/auth/register` | 公开，注册并返回令牌 |
| POST | `/api/v1/english/auth/refresh` | 公开，刷新令牌 |
| GET/PUT | `/api/v1/english/auth/profile` | 用户资料 |
| GET | `/api/v1/english/words` | 单词列表（公开，登录后带标记） |
| GET | `/api/v1/english/words/lookup` | 划词快速查询 |
| GET/POST | `/api/v1/english/wordbook` | 生词本列表/添加 |
| PUT/DELETE | `/api/v1/english/wordbook/{id}` | 生词本状态/移除 |
| GET | `/api/v1/english/daily-reading/today` | 今日一读（首次触发 LLM 生成文章） |
| PUT | `/api/v1/english/daily-reading/level` | 难度模式切换（自动/基础/四级/高阶） |
| GET | `/api/v1/english/daily-reading/quiz` | 今日小测出题（4-6 题） |
| POST | `/api/v1/english/daily-reading/quiz` | 提交小测答案（SRS 联动） |
| POST | `/api/v1/english/daily-reading/words` | 收集阅读生词（入 SRS 新词流程） |
| PUT | `/api/v1/english/daily-reading/words/blacklist` | 熟词黑名单 |
| POST | `/api/v1/english/daily-reading/complete` | 完成今日一读打卡 |
| GET | `/api/v1/english/daily-reading/archive` | 历史存档 |
| GET/POST/PUT/DELETE | `/api/v1/english/reading/notes` | 阅读笔记 |
| GET/POST/DELETE | `/api/v1/english/collections` | 统一收藏 |
| POST | `/api/v1/english/checkin` | 每日打卡 |
| GET | `/api/v1/english/checkin/stats` | 打卡统计 |
| GET | `/api/v1/english/study/stats` | 学习数据总览 |
