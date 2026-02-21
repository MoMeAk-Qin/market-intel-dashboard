# Market Intel Dashboard

多资产市场情报系统（港股/美股/外汇/贵金属/利率），提供事件聚合、行情快照、检索增强分析与前端可视化。

- 前端：Next.js 15 + React 19（`apps/web`）
- 后端：FastAPI + uv（`apps/api`）
- 共享类型：`packages/shared`

## 当前状态（2026-02-14）

已完成阶段：0~5。当前主线进入阶段 99 与阶段 6~10。

- 已完成：阻塞修复、新闻闭环、前端对接、HKMA 标准化、任务编排、真实行情接入、Quote 模型统一、E2E 行情链路。
- 进行中：阶段99（静态类型告警收口）。
- 待执行：阶段6~10（pgvector 优化、Research 真实化、未上市情报、关联分析、多模型与定时报告）。

开发计划唯一入口：`docs/todo.md`

## 关键能力（当前可用）

1. Dashboard 摘要、事件流检索与筛选（支持 `origin=live|seed|all`）。
2. 资产详情链路：`quote/series/chart/profile/events`，支持真实行情优先与回退。
3. `/qa` 与 `/analysis`：检索增强 + Qwen（有 Key 时），无 Key 时 QA 回退为规则摘要。
4. `/analysis/tasks` 异步任务与 SSE 流式状态订阅。
5. `/news/today` 与 `/daily/summary` 支持关注清单默认过滤。

## 能力边界（请先了解）

1. `/research/company/{ticker}` 目前仍是过渡实现（研究卡片+示例报告），阶段7会升级为真实研究链路。
2. 向量后端支持 `simple|chroma|pgvector`，其中 `pgvector` 为可选开关能力，阶段6继续完善索引与运维脚本。
3. Seed 与 Live 数据会并存；前后端正持续推进来源显式化（`source_type`）。

## 快速开始

以下命令均在仓库根目录执行。

### 1) 依赖要求

- Node.js（建议 20+）
- pnpm 9
- uv
- Python 3.12（强制，见 `apps/api/pyproject.toml`）

### 2) 安装依赖

```bash
pnpm i
uv sync --project apps/api
```

### 3) 启动

```bash
pnpm dev
```

- Web: [http://localhost:3000](http://localhost:3000)
- API: [http://localhost:4000](http://localhost:4000)

补充：默认配置即可本地运行；如需启用 LLM/向量增强，请设置环境变量（见下文）。

## 常用命令

```bash
# 仅启动 API
pnpm dev:api

# 仅启动 Web
pnpm dev:web

# 后端测试
uv run --project apps/api pytest

# 前端契约测试
pnpm -C apps/web test:contract

# 前端 lint
pnpm lint

# Push 前轻量审查（pre-push 也会自动触发）
pnpm review:light

# 阶段结束深度审查
pnpm review:deep -- --stage=8

# 发布前全链路审查
pnpm review:release
```

## 周期代码审查（单人 Lite）

```bash
# 首次启用本地 pre-push 钩子
git config core.hooksPath .githooks
```

审查节奏：

1. 每次 push 前：轻量审查（自动触发 `pnpm review:light`）。
2. 每个阶段结束：执行 `pnpm review:deep -- --stage=<phase>` 并归档报告。
3. 发布前：执行 `pnpm review:release`，通过后再发布。

报告归档路径：

- 深度审查：`docs/reviews/deep/`
- 发布审查：`docs/reviews/release/`

## 关键环境变量

参考：`apps/api/.env.example`、`apps/web/.env.example`

后端常用项：

- `DASHSCOPE_API_KEY`：启用 Qwen/embedding（`/analysis` 强依赖）。
- `VECTOR_BACKEND=chroma|simple|pgvector`：向量检索后端。
- `PGVECTOR_DSN` / `PGVECTOR_TABLE`：`pgvector` 后端配置。
- `ENABLE_LIVE_SOURCES`：是否开启实时源抓取。
- `WATCHLIST_MARKETS` / `WATCHLIST_TICKERS` / `WATCHLIST_KEYWORDS`：默认关注清单。
- `ANALYSIS_CACHE_TTL_SECONDS`：分析缓存 TTL。

前端常用项：

- `NEXT_PUBLIC_API_BASE_URL`（默认 `http://localhost:4000`）
- `NEXT_PUBLIC_APP_TIMEZONE`（默认 `Asia/Hong_Kong`）

## API 概览

### 系统与摘要

- `GET /health`
- `GET /dashboard/summary?date=YYYY-MM-DD`
- `POST /admin/refresh`

### 事件

- `GET /events`
- `GET /events/{event_id}`

### 资产

- `GET /assets/{asset_id}/quote`
- `GET /assets/{asset_id}/series?range=1D|1W|1M|1Y`
- `GET /assets/{asset_id}/chart?range=1D|1W|1M|1Y`
- `GET /assets/{asset_id}/events?range=1D|1W|1M|1Y`
- `GET /assets/{asset_id}/profile?range=1D|1W|1M|1Y`

### 研究与分析

- `GET /research/company/{ticker}`
- `POST /qa`
- `POST /analysis`
- `POST /analysis/tasks`
- `GET /analysis/tasks`
- `GET /analysis/tasks/{task_id}`
- `GET /analysis/tasks/stream`

### 新闻与日报

- `GET /news/today`
- `POST /daily/summary`

## 目录结构

```text
apps/web          Next.js 15 + React 19 前端
apps/api          FastAPI 服务与数据采集
packages/shared   前后端共享类型
docs              规划、路线图、评估与 TODO
```

## 文档协作规则（必须）

1. 开发计划与状态只在 `docs/todo.md` 维护（Single Source of Truth）。
2. 执行任务时必须同步参看：
   - `docs/master-plan-v2.md`（目标边界与验收口径）
   - `docs/implementation-roadmap-v2.md`（文件级步骤）
   - `docs/feasibility-assessment.md`（风险与前提）
3. 若文档冲突，按 `docs/todo.md` 中“AI Agent 同步参看规则”处理。

## 数据源与补充文档

- 数据源映射：`docs/data-sources.md`
- HKMA 端点梳理：`docs/hkma-endpoints.md`
- 架构说明：`docs/architecture.md`

## 下一步（与 TODO 一致）

1. 阶段99：静态类型告警收口并纳入 CI。
2. 阶段6：Postgres + pgvector 索引优化与运维脚本。
3. 阶段7：Research 页面真实数据链路。
4. 阶段8~10：未上市情报、关联分析、多模型与定时报告。
