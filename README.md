# Market Intel Dashboard

港股 / 美股 / 外汇 / 贵金属 / 债市分析系统 MVP。包含 Dashboard、Event Hub、Asset Detail、Research、Search & Q&A 五个页面，前端通过 `NEXT_PUBLIC_API_BASE_URL` 连接后端接口。后端基于 Python（FastAPI），支持每日早晚两次更新的免费数据源测试版。

## 快速开始

> 推荐 Python 3.12（本项目依赖 ChromaDB，当前与 Python 3.12 兼容性最佳）

```bash
pnpm i
uv sync --project apps/api
pnpm dev
```

- Web: http://localhost:3000
- API: http://localhost:4000

## 目录结构

```
apps/web        Next.js App Router + React Query
apps/api        FastAPI (免费数据源测试版)
packages/shared 共享类型与 schema

## 数据源映射

详见 `docs/data-sources.md`。

## 观测与重试

日志默认写入 `apps/api/data/api.log`，HTTP 请求重试次数与退避时间可在 `apps/api/.env.example` 中调整。
```

## API 列表

- `GET /health`
- `GET /dashboard/summary?date=YYYY-MM-DD`
- `GET /events`（支持 `origin=live|seed|all`）
- `GET /events/:id`
- `GET /assets/:assetId/chart?range=1D|1W|1M|1Y`
- `GET /assets/:assetId/events?range=1D|1W|1M|1Y`
- `GET /research/company/:ticker`
- `GET /news/today`
- `POST /qa`
- `POST /analysis`
- `POST /daily/summary`
- `POST /admin/refresh`

## 环境变量

- `apps/web/.env.example`
- `apps/api/.env.example`

### `/analysis`（检索增强信源分析）

- LLM：默认使用 DashScope 的 OpenAI 兼容模式调用 Qwen（需 `DASHSCOPE_API_KEY`）
- 检索增强：默认启用 Chroma 本地向量库（目录 `apps/api/data/chroma`）
  - Embedding 使用 DashScope 文本向量（默认 `text-embedding-v4`，需 `DASHSCOPE_API_KEY`）
  - 若未配置 `DASHSCOPE_API_KEY`，`/analysis` 将直接报错（无法调用 LLM/embedding）

## 数据更新策略

- 时区：Asia/Hong_Kong
- 早/晚各一次（默认 08:30 / 18:30）
- 可通过 `ENABLE_LIVE_SOURCES=true` 启用 RSS 采集

## HKMA 自动发现工具

```bash
uv run --project apps/api apps/api/tools/hkma_discovery.py
```

- 入口：HKMA apidocs Market Data and Statistics
- 输出：
  - `apps/api/app/sources/hkma_catalog.json`
  - `apps/api/app/sources/hkma_endpoints.env`
  - `apps/api/app/sources/hkma_units.json`

## TODO

- 接入 Postgres + pgvector 作为持久化存储
- 增加向量检索与多维过滤策略
- 引入真实行情与财务数据数据源
