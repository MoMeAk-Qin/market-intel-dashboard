# Market Intel Dashboard

港股 / 美股 / 外汇 / 贵金属 / 债市分析系统 MVP。包含 Dashboard、Event Hub、Asset Detail、Research、Search & Q&A 五个页面，前端通过 `NEXT_PUBLIC_API_BASE_URL` 连接后端接口，数据完全由 mock 生成。

## 快速开始

```bash
pnpm i
pnpm dev
```

- Web: http://localhost:3000
- API: http://localhost:4000

## 目录结构

```
apps/web        Next.js App Router + React Query
apps/api        Fastify API (mock data)
packages/shared 共享类型与 schema
```

## API 列表

- `GET /health`
- `GET /dashboard/summary?date=YYYY-MM-DD`
- `GET /events`
- `GET /events/:id`
- `GET /assets/:assetId/chart?range=1D|1W|1M|1Y`
- `GET /assets/:assetId/events?range=1D|1W|1M|1Y`
- `GET /research/company/:ticker`
- `POST /qa`

## 环境变量

- `apps/web/.env.example`
- `apps/api/.env.example`

## TODO

- 接入 Postgres + pgvector 作为持久化存储
- 增加向量检索与多维过滤策略
- 引入真实行情与财务数据数据源
