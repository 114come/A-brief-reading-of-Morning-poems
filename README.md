# 朝词浅阅 · English Learning

> 一款纯净、高级的英语学习网站：**SRS 背单词 + 每日一读 + AI 学习日报**，桌面与移动端同样优雅。

瑞士水疗极简设计（Swiss Spa）——松柏绿品牌色、纯白/暖灰背景、Lucide 图标、克制协调的调色板。

---

## ✨ 功能

| 模块 | 说明 |
|---|---|
| **背单词 SRS** | 艾宾浩斯间隔复习（1→2→4→7→15 天），认识/不认识两键；8 本考试词书 + 日常口语精选共约 3.9 万词 |
| **每日一读** | 每天推送 1 篇适配词汇水平的短文（LLM 生成并缓存）；难度 3 档自适应；朗读/遮罩/全文翻译/划词查词；今日小测联动 SRS |
| **AI 学习日报** | 每日自动汇总学习数据，LLM 生成洞察与建议（无密钥时走内置降级模板） |
| **打卡闭环** | 背词完成自动打卡；连续打卡、学习数据总览 |
| **主题** | 浅色/深色切换，保存到 `localStorage`；全无衬线、响应式布局 |

## 🛠 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Vue Router（自研 CSS，无组件库）+ Lucide |
| 后端 | FastAPI + SQLAlchemy + Alembic + PyMySQL |
| 数据库 | MySQL 8（租户元数据 + 英语数据，`tenant_id` 隔离） |
| 其他 | Redis（可选，AI 会话用）、JWT 认证 |

## 📁 目录结构

```
├── backend/               # FastAPI 后端（含英语学习 API）
│   ├── alembic/           # 数据库迁移
│   ├── app/api/v1/english.py
│   ├── app/services/english/   # 英语业务（SRS/每日一读/AI日报）
│   └── scripts/           # 词库导入 / 数据走查等工具
├── english-learning/      # Vue 3 前端
│   ├── src/views/         # 首页 / 词笺 / 浅读 / 归处
│   └── deploy/            # 生产部署（nginx.conf / DEPLOY.md）
└── start.bat              # 一键启动脚本
```

## 🚀 快速开始

### 前置

- Python 3.11+ · Node 22+ · MySQL 8（运行在 3306）

### 一键启动（Windows）

双击根目录 `start.bat`，或命令行：

```bat
start.bat          # 检测并拉起 MySQL / 后端(8001) / 前端(5174)，自动开浏览器
start.bat nobrowser
```

> 首次启动后端会自动执行数据库迁移并播种：9 本词书 + 3.9 万词库 + 管理员账号。
> 若 MySQL 未运行，请**以管理员身份**运行本脚本。

### 手动启动

```bash
# 1. 配置后端
cd backend
cp .env.example .env     # 按需修改 MASTER_DB_* 等
python -m alembic upgrade head

# 2. 启动后端（端口 8001）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# 3. 启动前端（端口 5174，/api 已代理到 8001）
cd english-learning
npm install
npm run dev
```

访问 **http://localhost:5174**，登录 **english_admin / 123456**（或注册新账号）。

## ⚙️ LLM 配置（可选）

`backend/.env` 填入以下项可启用 **AI 学习日报 / 每日一读实时生成 / 例句翻译**；留空则走内置降级模板，功能不受影响：

```ini
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_PROVIDER_TYPE=custom
```

支持 DeepSeek / 通义千问 / 文心一言（详见 `.env.example` 注释）。

## 🧪 测试

```bash
# 后端（SRS / 每日一读 / AI日报 / 测试）
cd backend && python -m pytest app/tests/

# 前端 SRS 引擎状态机
cd english-learning && npm test
```

## 🚢 部署

生产部署（Nginx 托管前端 + 反向代理后端）见 [`english-learning/deploy/DEPLOY.md`](english-learning/deploy/DEPLOY.md)。

## 📖 数据来源

词库来自开源英汉词典 [ECDICT](https://github.com/skywind3000/ECDICT)（MIT 协议）。
