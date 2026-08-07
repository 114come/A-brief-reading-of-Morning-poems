# 朝词浅阅 - 生产部署指南

## 架构

```
浏览器
  │  :80 (nginx)
  ▼
Nginx ── 静态文件 ──▶ dist/ (Vue 生产包)
  │  /api/ 反向代理
  ▼
FastAPI (uvicorn, 127.0.0.1:8001)
  ▼
MySQL (lowcode_master, 3306)
```

## 前置条件

- Node.js 18+（构建前端）
- Python 3.11+（后端，已用 `E:\20260718\venv`）
- MySQL 8.0（运行中，3306）
- Nginx（可选，见下文「无 Nginx 快速上线」）

## 部署步骤

### 1. 构建前端

```bash
cd E:\20260718\english-learning
npm run build        # 产物在 dist/
```

或双击 `deploy/build-and-preview.bat`。

### 2. 启动后端

```bash
cd E:\20260718\backend
E:\20260718\venv\Scripts\python.exe -m alembic upgrade head
E:\20260718\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

或双击 `deploy/start-backend.bat`。

> 首次启动自动完成：播种 9 本词书 + 3.9 万词库 + english_admin 管理员。

### 3. 配置 Nginx（推荐）

复制 `deploy/nginx.conf` 到 Nginx 配置目录，修改 `server_name`/`root` 路径后：

```bash
nginx -t                    # 测试配置
nginx                       # 启动
```

访问 `http://localhost` 即上线。

### 4. 无 Nginx 快速上线

如果暂时不想装 Nginx，直接用 Vite 预览 + 后端：

```bash
# 终端1：后端
cd E:\20260718\backend
E:\20260718\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 终端2：前端预览（vite preview 默认 4173）
cd E:\20260718\english-learning
npm run preview
```

但 preview 的 `/api` 不代理后端，需改 `vite.config.ts` 的 `preview.proxy` 或直接用 nginx。

## 数据

| 项 | 说明 |
|---|---|
| 词库 | 9 本词书，38,898 词 |
| 音标 | 98% |
| 词性 | 96%（中文） |
| 例句 | 核心词持续扩充中 |
| 管理员 | english_admin / 123456（登录后可改） |

## 常见问题

**Q: 数据库被重置，词库没了怎么办？**
```bash
cd E:\20260718\backend
E:\20260718\venv\Scripts\python.exe -m alembic upgrade head
# 重启后端（自动播种词书+精选词）
# 然后重新导入完整词库：
E:\20260718\venv\Scripts\python.exe scripts\import_ecdict.py
E:\20260718\venv\Scripts\python.exe scripts\backfill_pos_and_phonetic.py
E:\20260718\venv\Scripts\python.exe scripts\clean_pos.py
E:\20260718\venv\Scripts\python.exe scripts\backfill_dup_pos.py
```

**Q: 想让局域网/其他设备访问？**
后端 `--host 0.0.0.0`，nginx `server_name` 改为本机 IP；MySQL 需允许远程连接（生产不建议，用密码保护）。

**Q: 想要 HTTPS？**
在 nginx 配置 SSL 证书（如 certbot / 云厂商免费证书），把 80 重定向到 443。
