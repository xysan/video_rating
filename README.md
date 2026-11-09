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

## PR-02：数据库迁移与管理员初始化

在 backend 目录激活虚拟环境，安装 requirements.txt 后运行：

```sh
python -m alembic upgrade head
python -m app.seed
```

种子脚本要求先在 backend/.env 中设置 SEED_ADMIN_PASSWORD，不设置会报错退出；UTF-8 编码最多 72 字节。只创建 admin 管理员，使用 bcrypt 加盐哈希；重复运行保留已有用户及密码，不创建业务数据。请勿将密码写入命令行或提交环境文件。

当前允许 SQLite 临时预览，DATABASE_URL 可设为 sqlite:///./dev.db，务必在 backend 目录运行命令。正式数据库仍使用 MySQL 8 的 mysql+pymysql 连接串；初始迁移明确指定 InnoDB、utf8mb4 和 utf8mb4_unicode_ci。SQLite 的枚举使用 CHECK 约束，MySQL 使用原生 ENUM；JSON 使用 SQLAlchemy JSON 类型。

四张业务表之外，Alembic 自动维护 alembic_version 迁移版本表，这是迁移工具元数据，不是业务表。项目仅有一个外键 scores.video_snapshot_id → video_snapshots.id，updated_by 不建外键。

全局上下文未规定字段长度和分数精度，本次采用整数主键、唯一字符串长度 191、名称长度 255、标题与配置值 TEXT、分数 DECIMAL(18,6)、发布日期 DATE、其余时间 DATETIME（由调用方统一提供 UTC）。description 和 updated_by 可空，其余字段非空。没有新增任何字段。

回滚命令为 `python -m alembic downgrade base`，会删除全部四张业务表及数据，请先备份；重新执行 upgrade head 可恢复空表结构。MySQL 实际迁移验证需可用的 MySQL 8 实例，SQLite 验证不代表 MySQL 实测通过。

## PR-04：飞书后台增量同步

安装更新后的 backend/requirements.txt 并重启后端。FEISHU_SYNC_ENABLED=true 时，启动 APScheduler interval 任务，间隔由 SYNC_INTERVAL_MINUTES 控制（正整数分钟）；首次定时执行在一个间隔之后。关闭此开关只关闭定时任务，管理员仍可手动同步。

管理员携带 Authorization: Bearer token 调用 POST /api/admin/sync/run，返回 202 表示后台已接收；已有任务运行时返回 409。GET /api/admin/sync/status 返回 running、started_at、finished_at、last_sync_at、success、fetched、inserted、updated、skipped、error。状态仅保存在当前进程，重启后清空，历史信息查看 Python logging 输出；last_sync_at 是最近一次完成时间，须结合 success 判断结果。

必须以单个 uvicorn worker 运行，避免多个进程重复调度；同进程定时及手动触发共享互斥状态。关闭进程会等待当前同步结束。无需新数据库表或迁移。

客户端每轮获取 tenant_access_token，按每页 500 条遍历 records/search，automatic_fields=true 获取 last_modified_time；不设置 view_id。每条记录以 feishu_record_id 查找并比较修改时间，同秒时另比较完整 raw_payload；没变化不更新 synced_at。每轮分页读取全表，但只写新增或变化的数据，不删除本地记录。整轮事务提交，任何分页、解析、写入失败会回滚本轮新增和更新并记录失败，后续调度继续运行。

当前真实表字段映射为 up主、标题、发布时间，可通过 FEISHU_UP_NAME_FIELD、FEISHU_TITLE_FIELD、FEISHU_PUBLISH_DATE_FIELD 配置。支持单值查找引用和富文本标题；缺少 UP 主、标题或发布时间的记录按用户确认的规则跳过并记录 record_id、原因和 skipped 数量；多值、格式错误或缺少修改时间时明确失败，不使用占位值。日期毫秒时间戳按 UTC+8 转换为发布日期，修改及同步时间按 UTC 保存。原始记录包含自动字段，完整保存到 raw_payload。

验证执行 `python -m pytest tests -q`。测试中的飞书响应和用户仅在 pytest 临时数据库使用，不会生成业务演示数据；测试进程关闭真实定时同步。回滚代码前关闭 FEISHU_SYNC_ENABLED 并停止后端；本 PR 无迁移，不删除已经同步的真实记录。
