# 开发实施清单（后续执行版）

> 更新日期：2026-02-14
> 执行原则：先修阻塞与一致性，再做前端闭环，再做可观测与数据源增强。

## 1. 规划合并结论

本清单综合以下文档并作为唯一执行主文档：
- `docs/todo.md`（阶段目标与 KPI）
- `docs/project-assessment.md`（已落地能力与修正项）
- `docs/hkma-endpoints.md`（HKMA 自动发现与标准化要求）
- 代码现状（2026-02-14）：前端首页/导航语义偏离“市场情报”，`/news`、`/daily-summary` 页面缺失。

## 2. 执行顺序（必须按序）

## 阶段 0：阻塞修复与一致性（立即执行）

- [x] `apps/api/app/services/seed.py`：修复 `TypeVar` 约束与 `_pick` 类型准确性问题。
- [x] `apps/api/tests/test_seed_utils.py`（新增）：补回归测试，覆盖 `_pick`/`_pick_many` 的稳定行为。
- [x] 前端语义回正：移除与项目无关的钱包文案与导航锚点。

验收：
- API 测试通过（至少覆盖 seed 回归测试）。
- 首页与导航均指向市场情报相关路由。

## 阶段 1：前端闭环（M1，优先级最高）

- [x] `apps/web/src/components/site-header.tsx`：导航补齐“今日新闻”“日报摘要”。
- [x] `apps/web/src/app/page.tsx`：恢复为市场情报首页，提供到 `events/news/search/daily-summary/research` 的入口。
- [x] `apps/web/src/app/news/page.tsx`（新增）：接 `GET /news/today`，支持 market/tickers/q/sort/limit。
- [x] `apps/web/src/app/daily-summary/page.tsx`（新增）：接 `POST /daily/summary`，展示答案+证据。
- [x] `apps/web/src/lib/api.ts`：新增 typed API 方法 `getHealth/getNewsToday/getDailySummary`。
- [x] `packages/shared/src/types.ts`：补 `HealthResponse`。
- [x] `apps/web/src/app/search/page.tsx`：增加跳转入口（新闻/日报）和错误提示优化。
- [x] `apps/web/src/app/research/page.tsx`、`apps/web/src/app/asset/[id]/page.tsx`：显式“演示数据”提示。

验收：
- 前端路由可用：`/news`、`/daily-summary`。
- 首页与导航语义一致，不再出现钱包产品文案。

## 阶段 2：可观测性与运行透明（M1 收尾）

- [x] `apps/api/app/models.py`：新增 `HealthResponse`、`RefreshReport`。
- [x] `apps/api/app/state.py`：增加刷新统计（live/seed/耗时/错误）。
- [x] `apps/api/app/services/ingestion.py`：`refresh_store` 返回结构化刷新报告。
- [x] `apps/api/app/api.py`：增强 `GET /health` 与 `POST /admin/refresh`。
- [x] `apps/api/tests/test_health_endpoint.py`（新增）：覆盖增强字段。

验收：
- `/health` 可返回 `ok/store_events/updated_at/vector_store_enabled/vector_store_ready`。
- `/admin/refresh` 返回可追踪刷新报告。

## 阶段 3：HKMA 自动化（M2）

- [x] `apps/api/app/sources/hkma_discovery.py`：文档递归发现与 API URL 抽取稳定化。
- [x] `apps/api/app/sources/hkma_catalog.py`：`Output Fields` + OpenAPI 摘要聚合。
- [x] 产物稳定生成并纳入版本控制：
- [x] `apps/api/app/sources/hkma_catalog.json`
- [x] `apps/api/app/sources/hkma_endpoints.env`
- [x] `apps/api/app/sources/hkma_units.json`
- [x] `apps/api/app/sources/hkma.py`：`record -> MetricPoint` 标准化落地。

验收：
- 发现脚本连续两次运行，除时间戳外产物一致。
- daily/monthly 关键字段可入统一 schema。

## 阶段 4：任务编排与向量可插拔（M3）

- [x] 异步分析任务接口：`POST /analysis/tasks`、`GET /analysis/tasks/{id}`、`GET /analysis/tasks`、`GET /analysis/tasks/stream`。
- [x] 向量后端可插拔：`VECTOR_BACKEND=chroma|simple`。
- [x] 前端 `search` 支持任务态（pending/running/completed）。

验收：
- 任务状态可追踪，前端可感知。
- simple/chroma 两后端行为一致性测试通过。

## 3. 本轮立即执行项（从上到下）

1. [x] 修 `seed.py` 类型与回归测试。
2. [x] 前端导航与首页语义回正。
3. [x] 新增 `/news`、`/daily-summary` 页面并接 API。
4. [x] 增补 shared 类型与 typed API helper。
5. [x] 前端演示数据提示补齐。

## 4. 里程碑状态跟踪

- [x] 阶段 0 完成
- [x] 阶段 1 完成
- [x] 阶段 2 完成
- [x] 阶段 3 完成
- [x] 阶段 4 完成
