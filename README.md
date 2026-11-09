# 视频评分看板

公司内部 Web 看板，用于统计视频发布第 15 天的算法得分。本 PR 仅提供运行脚手架和健康检查，不建表、不创建用户、不执行飞书同步或算法计算。详细评分过程和算法配置将在后续 PR 通过后端权限依赖隔离。

## 环境

Python 3.11、Node.js 22.12+、MySQL 8。后端依赖在 requirements.txt 固定版本；前端使用 package-lock.json。禁止使用 SQLite。以下命令在仓库根目录执行，进入子目录的步骤除外。

## 1. MySQL

优先 Docker：复制根目录 `.env.example` 为 `.env`，替换所有密码与账号占位符，然后运行：

```sh
docker compose up -d mysql
docker compose ps
```

只启动 MySQL 一个服务，命名卷 mysql_data 持久化数据；已有本机 MySQL 占用端口时修改 MYSQL_PORT，并同步修改 DATABASE_URL。普通停止用 `docker compose down`，不要添加 `-v`。初始化变量仅在空数据卷首次启动时生效。

如果环境没有 Docker，安装 MySQL 8 Community Server，启动服务，通过 `mysql -u root -p` 登录，创建数据库 `appdb`（utf8mb4）及专用用户，授予该用户 appdb 的权限。账号和密码自行设置，不写入源码或提交到 Git。不要对已有实例重新初始化。

## 2. 环境文件

分别复制 `backend/.env.example`、`frontend/.env.example` 为同目录 `.env`。真实 `.env` 已被 Git 忽略，不得提交。

后端必须填写 DATABASE_URL 与随机 JWT_SECRET；数据库 URL 使用 mysql+pymysql 驱动，密码特殊字符须 URL 编码。CORS_ORIGINS 填前端访问来源（协议和域名，多个以逗号分隔），开发可用 `*`，上线前收紧。飞书凭证和 SEED_ADMIN_PASSWORD 本 PR 可留空，FEISHU_SYNC_ENABLED 保持 false。所有配置字段均有示例注释。

前端 VITE_API_BASE_URL 填后端地址，例如本地开发时自行填写本机 8000 端口地址。前端源码没有硬编码地址。临时公网环境填后端 HTTPS 地址；VITE_ALLOWED_HOSTS 填前端临时域名，不含协议。VITE_ 变量会进入浏览器，禁止放入密钥。

## 3. 启动后端

```sh
cd backend
python3.11 -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell 使用：.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows 创建虚拟环境时可用 `py -3.11 -m venv .venv`。访问后端地址的 `/api/health` 应返回 `{"status":"ok"}`。该接口仅检查应用存活，不证明数据库已连接。

在 backend 目录另开终端，激活相同环境验证真实数据库（不建表）：

```sh
python -c "from app.database import engine; from sqlalchemy import text; c=engine.connect(); print(c.execute(text('SELECT VERSION()')).scalar()); c.close()"
python -m pytest tests -q
```

## 4. 启动前端

另开终端：

```sh
cd frontend
npm ci
npm run dev
```

浏览器访问前端 5173 端口，应看到“项目初始化成功”和“后端状态：ok”。验证构建执行 `npm run build`。修改前端环境变量后需重启 Vite，修改后端环境变量后需重启后端。

## 5. 云端临时公网预览

在具备 Python 3.11、Node 和 MySQL 8 的 Codex 云端环境中重复以上步骤。MySQL 优先 Docker，不支持 Docker 时安装本机 MySQL 8 并创建 appdb。前后端裸跑，分别监听 `0.0.0.0:8000` 和 `0.0.0.0:5173`。

使用云端平台的端口转发功能分别暴露 8000 和 5173，取得两个临时 HTTPS 地址。将后端地址写入前端 VITE_API_BASE_URL，前端域名写入 VITE_ALLOWED_HOSTS，前端完整来源写入后端 CORS_ORIGINS，重启两个进程。用浏览器打开前端临时地址并检查状态；后端地址加 `/api/health` 可直接验收。不要暴露 MySQL 3306。地址到期后重新配置。

当前执行会话为本地 Windows，不提供 Codex 云端端口转发；实际云端验证结果与访问地址在 PR 描述中记录，未取得地址时不得声称通过验收。

## 目录

- backend/app/main.py：最小应用和健康接口；config.py：环境配置；database.py：engine 和 session 依赖。
- backend/app/{models,auth,sync,scoring,api}/：空包，后续 PR 实现。
- backend/alembic/：保留空目录，本 PR 无数据库迁移；backend/tests/：健康检查测试。
- frontend/src/{styles,components,views,api}/：最小样式令牌、空组件与视图目录、健康接口调用。
- STYLE_BRIEF.md：风格约束，完整设计在 PR-07 定稿。
- docker-compose.yml：仅 MySQL；docker-compose.prod.yml、DEPLOY.md、OPS.md：按约定保留空文件。

## 回滚

停止本 PR 启动的前后端进程，执行 `docker compose down` 停止本 PR 的 MySQL 容器，保留数据卷。未建表，无迁移可回滚。代码合并后如需回滚，通过独立分支 revert 合并提交并提交 PR，不直接推 main。
