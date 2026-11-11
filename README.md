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

## PR-05：配置化评分

在 backend 目录依次执行 `python -m alembic upgrade head`、`python -m app.scoring.initialize_configs`。初始化只写入用户确认的权重、分值、阈值及字段映射，不覆盖已有配置，也不生成 UP 主基线。config_value 保持 TEXT，内容为 JSON。新增唯一约束迁移禁止同一视频同一算法版本产生重复评分，若历史有重复则迁移失败，不擅自删除数据。

管理员在 Swagger 调用 GET /api/admin/configs 或 PUT /api/admin/configs/{config_key}。请求体格式为 `{"config_value": JSON值, "description": "说明"}`；例如 weight_play 的值为 0.4。UP 主基线键为 up_standards_{up_name}，值含 play、interact、jump_3s、progress、convert 五个升序五元素数组；反向指标也按升序输入。member 无权访问这些接口。

所有数值规则初始化清单见 backend/app/scoring/initial_rules.json；该文件仅用于显式初始化及输入校验，实际计算只读数据库，缺少配置时报错。没有真实 UP 主基线时跳过评分。metric_fields 可配置飞书字段名；当前难度、效率、投流比例未确认来源，映射保持 null，算法按原规则返回 partial_success，不猜测字段。

同步成功后自动后台评分，也可运行 `python -m app.scoring.task` 计算已同步快照。默认算法版本 v1.0，默认筛选发布满 15 天的视频；无变化跳过，输入或相关配置变化则更新原评分。score_detail 保存完整分项、加减分、缺失项及计算配置快照，未提供 member 明细接口。

本 PR 回滚迁移：`python -m alembic downgrade 92bc01ba8d6d`，仅移除评分唯一约束，保留表与记录。迁移须先备份；SQLite 正反向验证不代表 MySQL 8 已完成实测。

## PR-06：看板、评分查询与管理

所有接口使用 Authorization: Bearer token。GET /api/member/dashboard 返回 top_videos 与 videos；近 30 天按北京时间今天及前 29 个自然日的发布日期筛选，使用 >= 起始日期、< 明天的区间，不对数据库日期列套函数。排行榜仅取有评分的视频，最多五条且不返回 BV；卡片保留 bv_id，score > 85 时 is_high_score=true。尚未评分返回 null，不补造得分。

GET /api/member/scores 与 GET /api/admin/scores 支持 page、page_size（1–100）、up_name、date_from、date_to、director。日期为 YYYY-MM-DD、结束日期包含当天，编导按实际字段解析后精确匹配。多算法版本取最近计算的评分；日期/UP 在 SQL 筛选，嵌套编导在应用层筛选后分页，数据量增长时需优化这一部分。管理员额外获得完整 raw_payload、score_detail；成员仅投影允许的 JSON 子字段，不查询这两项敏感信息。snapshot_play_count 是飞书快照播放量，play_count 是缓存实时播放量。

GET /api/admin/users 不返回密码哈希；PUT /api/admin/users/{user_id}/role 请求体为 {"role":"admin"} 或 {"role":"member"}，权限变更下一次请求生效。GET /api/admin/export/csv 下载 UTF-8 BOM CSV，包含评分与快照核心指标，转义公式前缀。算法配置继续使用 /api/admin/configs。

BILIBILI_CACHE_ENABLED 默认 true：启动时后台刷新，之后每 15 分钟刷新，最多 4 个并发请求。BV 优先取真实字段 BV号，缺失则解析标题链接；编导取真实字段 编导。缓存仅存在 VIDEO_CACHE 字典，重启丢失；不写库。每轮缓存以成功结果替换，失败视频记录日志且缓存字段返回 null。ranking_status 仅包含 B站响应的 current_rank 与 historical_rank，不推断热门/每周必看标签。B站接口失败或限制请求时不进行绕过。

本 PR 无数据库迁移；回滚代码并重启即可清除缓存。继续使用单 worker，避免重复抓取。pytest 中禁用真实定时抓取，HTTP mock 仅用于测试。

管理员批量基线导入：POST /api/admin/configs/import-standards 接收 JSON 数组，每项包含 up_name 和五个维度的升序五元素数组；重复 UP、非法值会整批拒绝。返回 imported/created/updated，存在则更新并记录操作者。导入后下一次同步将按配置变化重算，也可执行 `python -m app.scoring.task` 立即计算。Dashboard 无评分时返回 null，按发布日期降序。


## PR-07：前端设计系统与登录骨架

前端运行 `npm ci`、`npm run dev`，访问 http://localhost:5173/login 。API 地址继续通过 frontend/.env 的 VITE_API_BASE_URL 配置；本地后端必须启动，并通过 CORS_ORIGINS 放行前端地址。运行 `npm test` 验证会话与路由，`npm run build` 验证生产构建。

登录先请求 /api/auth/login，再调用 /api/me 获取真实角色；token 仅保存在当前标签页的 sessionStorage，通过 Authorization: Bearer 请求头发送。401 清除当前会话并跳转登录；普通成员无法进入 /admin 路由。前端守卫仅控制导航，数据访问继续由后端权限依赖校验。

五个业务路由当前仅显示页面标题。ECharts 已锁定依赖，业务图表在后续 PR 实现。GlassPanel、AppButton、AppInput、AppLayout 位于 components/ui；色彩、圆角、模糊、阴影集中在 tokens.css。页面最多两块独立玻璃区域，控件使用实底；背景光斑固定，无滚动动画，尊重 reduced-motion 设置。html/body 无外层滚动，小尺寸页面内容区域允许滚动，避免遮挡表单。

品牌图形使用公司提供的“组合logo/图形.png”，原样复制至 public/brand/mark.png；英文展示字体为 Google Fonts Syne 600，字体网络不可用时回退 sans-serif，中文正文使用系统黑体。后续页面复用现有 Token 与组件，不新增独立颜色体系。

本次无数据库或后端变更。回滚前端代码与 package-lock.json 后执行 npm ci 并重启 Vite 即可。


## PR-08：沉浸式数据看板

访问 /member/dashboard（管理员首页 /admin/dashboard 复用同一视图），读取 GET /api/member/dashboard。顶部排行榜最多展示五条真实已评分作品，数量不足不补数据；下方展示近 30 天视频，按发布日期降序排列。无分数显示“数据采集中”，缓存互动指标缺失显示破折号，缺失或加载失败的封面使用文字占位。

页面采用上下约 40%/60% 分区和横向卡片轨道，每 7 秒自动前进一组、到末尾循环；按钮支持上一组、下一组、暂停，轨道支持方向键与触控。鼠标悬停、键盘焦点进入时暂停，触控/滚轮交互停止自动播放；减少动态效果偏好下停用自动播放和呼吸动画。数据每分钟刷新，失败保留上次成功内容并提示重试，卸载页面取消请求和计时器。高分依据 is_high_score 或实际分数 >= 85 判断。

复用 GlassPanel、AppButton，新增 VideoCard、VideoCover；当前没有现成 MetricCard。仅侧栏与排行榜使用背景模糊，重复视频卡片使用 GlassPanel 的实底变体，避免大量模糊层。新增金银铜排名语义色及高分阴影集中在 tokens.css。未启用额外大图轮播，优先保证两大模块完整可见。

验证：npm test、npm run build；浏览器实测 1440×900 与 1920×1080 页面尺寸无纵向溢出、卡片内容完整，暂停/翻页/末尾循环正常。当前真实接口返回 24 部视频、2 条排行榜记录，该数量随日期和同步变化。测试中的数据仅供单元测试，不写数据库。未进行云端公网部署；本地地址 http://localhost:5173/member/dashboard 。回滚本次前端代码并重启即可，无数据库迁移。


## 业务优化：筛选、编辑与导出

评分接口支持重复查询参数 up_names、directors，以及 is_published_15_days、sort_by、sort_order。GET /api/scores/filters 返回可选名称。GET /api/admin/scores/export 使用同一筛选条件导出全部匹配结果，format 为 csv 或 xlsx，表头为中文，导出不受当前分页限制。成员查询仅投影允许的 JSON 子字段，不读取评分明细或整包原始数据。

PUT /api/admin/videos/{id}/extras 接收 difficulty（S/A/B 或 null）、efficiency（现有五种时效状态或 null）、traffic_ratio（0—1 或 null）。快照更新与 v1.0 重算在同一事务提交；未满配置日龄、缺基线或缺核心指标时失败并回滚。管理员附加属性保存在原始包内并在后续飞书同步时保留。更改这些字段必须通过此接口，不能只修改浏览器状态。

设置页使用文字数字表单编辑嵌套规则；新增 UP 基线包含五个维度、每维 P10/P25/P50/P75/P95。保存调用 PUT /api/admin/configs/{key} 并刷新数据库列表。用户角色修改继续调用已有持久化接口。数据导出已移到视频得分页。

看板支持图标按钮切换浏览器原生全屏并隐藏侧栏。轨道前后克隆卡片组，滚动结束后无动画归位；点击播放后每 7 秒前进一张，支持暂停，悬停暂缓播放，减少动态偏好下使用即时切换。卡片无内部滚动条，长标题最多两行并可悬浮查看，无编导不显示该段文字。

本地 .env 已连接 MySQL 8；真实数据库验证涵盖筛选、排序、两种导出、同值配置保存及独立会话读取。回归测试仍含隔离 SQLite 测试库，不代表全部场景均已在 MySQL 实测。本轮没有数据库结构迁移。回滚代码需保留管理员附加字段备份，旧同步代码不识别其保留策略。当前未完成浏览器视觉验收和云端预览。


### 视频得分页交互重构

筛选项即时生效，变更后重置到第一页并取消上一请求；保留重置。UP 主、编导复用 AppMultiSelect，支持搜索、标签移除、复选、Escape 与外部点击关闭。操作区集中放置日龄、排序和导出，窄屏折行。明细弹窗连续展示基线快照、逐维公式推导和加减分汇总，附加属性独立编辑，保存与取消固定在底栏；保存继续调用真实重算接口。看板卡片按视口宽度切换可见数量并保持封面比例。本次自动化测试和构建通过，未进行浏览器截图或实际屏幕尺寸验收。


### 本轮设置与明细展示验收

设置页按制作难度、固定得分、权重三组排列，支持基线增删改和用户角色持久化。得分页采用自定义日期与选择面板，管理员明细按保存的算法快照展示公式；编辑数据保存后更新评分和推导。配置修改不会立即批量重算已有得分。

本轮验证：后端 pytest 49 项通过，前端测试 27 项通过，npm run build 通过。浏览器视觉复核和云端公网预览尚未完成。本地预览：http://localhost:5173；后端文档：http://localhost:8000/docs。
