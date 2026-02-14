# 开发实施清单（执行主文档）

> 更新日期：2026-02-13  
> 目标：把现有 TODO 与外部建议落成可执行开发任务，覆盖 API、前端、测试、验收。

## 0) 文档使用规则

- `docs/todo.md`：阶段目标、KPI、复盘口径（看板）。
- `docs/implementation-checklist.md`：具体执行项、文件改动、开发顺序（执行主文档）。
- 后续开发与排期以本文件为准；阶段是否完成以 `todo.md` 的 KPI 判定。

---

## 1) 外部建议评估（来自 `docs/others.md`）

### 1.1 可直接采纳

| 建议 | 结论 | 采纳方式 | 落地里程碑 |
|---|---|---|---|
| GitHub Actions 定时抓取 | 采纳 | 仅保留“定时执行 + 产物归档”，不做自动部署 | M2 |
| PostgreSQL 暂不引入 | 采纳 | 保持轻量，延后到能力扩展阶段 | M3 之后 |
| 宏观向功能优先级上调 | 采纳 | 增加日报、宏观日历、多市场联动分析 | M2 |
| 每日 Markdown 复盘报告 | 采纳 | 基于 `/daily/summary` 自动生成报告 | M2 |
| 轻量架构维持 | 采纳 | 不新增重型中间件，优先补闭环能力 | 全阶段 |

### 1.2 有条件采纳

| 建议 | 结论 | 条件 | 落地里程碑 |
|---|---|---|---|
| 用“内存+NumPy/JSON”替代 Chroma | 条件采纳 | 先做向量存储可插拔，再做召回率与延迟 A/B | M3 |
| 引入 notebooks | 条件采纳 | 先完成主流程闭环，再补研究型产物目录 | M2 末 |
| 文件系统主存储 | 条件采纳 | 仅用于报告与缓存，事件主数据先不一刀切迁移 | M2-M3 |

### 1.3 暂不采纳

| 建议 | 暂不采纳原因 |
|---|---|
| 立即移除 ChromaDB | 当前有检索召回 KPI，直接移除风险高 |
| 全量改为“内存+JSON” | 会削弱后续任务编排、审计、回放能力 |
| 把推送/回测完全降级为无价值 | 这些是可选能力，不应提前砍掉 |

---

## 2) 里程碑与执行任务

## M1：前端闭环与可观测性（1 周内）

### M1-A API 改动

- [ ] `apps/api/app/models.py`：新增 `HealthResponse`、`RefreshReport` 模型。
- [ ] `apps/api/app/state.py`：增加刷新统计字段（总量、live/seed、耗时、最近错误）。
- [ ] `apps/api/app/services/ingestion.py`：`refresh_store` 返回结构化刷新报告。
- [ ] `apps/api/app/api.py`：增强 `GET /health` 返回详情字段。
- [ ] `apps/api/app/api.py`：增强 `POST /admin/refresh` 返回刷新报告。
- [ ] `apps/api/app/config.py`：增加 `HEALTH_INCLUDE_DETAILS`（可选）控制健康详情输出。

### M1-B 前端改动

- [ ] `apps/web/src/components/site-header.tsx`：新增“今日新闻”“日报摘要”导航。
- [ ] `apps/web/src/app/news/page.tsx`（新增）：接入 `GET /news/today`，支持 market/ticker/keyword 过滤。
- [ ] `apps/web/src/app/daily-summary/page.tsx`（新增）：接入 `POST /daily/summary`，展示摘要与证据链。
- [ ] `apps/web/src/app/search/page.tsx`：增加“跳转日报/新闻”与错误提示细化。
- [ ] `apps/web/src/app/research/page.tsx`：增加“演示数据”提示。
- [ ] `apps/web/src/app/asset/[id]/page.tsx`：增加“演示行情”提示。
- [ ] `apps/web/src/lib/api.ts`：新增 typed 封装 `getHealth/getNewsToday/getDailySummary`。
- [ ] `packages/shared/src/types.ts`：补齐 `HealthResponse` 共享类型。
- [ ] `apps/web/src/components/ui/badge.tsx`：强化 seed 样式对比度。

### M1-C 测试与验收

- [ ] `apps/api/tests/test_health_endpoint.py`（新增）：覆盖健康检查新增字段。
- [ ] `apps/api/tests/test_daily_news.py`（扩展）：覆盖默认关注清单与过滤。
- [ ] `apps/api/tests/test_qa_endpoint.py`（扩展）：覆盖降级路径与错误处理。
- [ ] 手工回归：`/news`、`/daily-summary`、`/search` 跳转链路。
- [ ] 验收指标：
- [ ] `/daily/summary` 本地 P95：无缓存 <= 6s，命中缓存 <= 1.5s。
- [ ] 新闻页过滤交互响应 <= 300ms（本地）。

---

## M2：HKMA 自动化与宏观产物（1-2 周）

### M2-A HKMA 自动化

- [ ] `apps/api/app/sources/hkma_discovery.py`：提高解析稳定性，确保产物字段齐全。
- [ ] `apps/api/app/sources/hkma_catalog.py`：加强 schema 校验（字段缺失/类型异常）。
- [ ] `apps/api/app/sources/hkma.py`：完善 `record -> MetricPoint` 标准化。
- [ ] `apps/api/tools/hkma_discovery.py`：支持稳定 CLI 输出与错误码。
- [ ] 产物落库校验：
- [ ] `apps/api/app/sources/hkma_catalog.json`
- [ ] `apps/api/app/sources/hkma_endpoints.env`
- [ ] `apps/api/app/sources/hkma_units.json`

### M2-B 宏观报告与自动化

- [ ] `apps/api/app/services/analysis.py`：增加日报生成埋点（耗时/token/缓存命中）。
- [ ] `apps/api/app/api.py`：为日报输出补充元信息（如来源数、时间范围）。
- [ ] `apps/web/src/app/daily-summary/page.tsx`：支持导出 Markdown（或复制摘要）。
- [ ] `.github/workflows/daily_refresh.yml`（新增）：定时任务 + 手动触发 + 产物归档。
- [ ] `README.md`：补充 GitHub Actions 使用与 cron 时区说明。

### M2-C 测试与验收

- [ ] `apps/api/tests/test_hkma_discovery.py`（扩展）：验证 catalog/endpoints/units 结构。
- [ ] `apps/api/tests/test_hkma_source.py`（扩展）：验证 `MetricPoint` 字段完整性。
- [ ] 新增手工验证脚本：连续运行 discovery 两次，比较产物差异仅限时间戳。
- [ ] 验收指标：
- [ ] HKMA 三类产物稳定生成。
- [ ] RSS 成功率 >= 98%，去重后重复率 <= 5%。

---

## M3：任务编排与向量可插拔（2-4 周）

### M3-A 异步任务编排

- [ ] `apps/api/app/services/task_queue.py`（新增）：任务提交、去重、状态流转、错误回传。
- [ ] `apps/api/app/models.py`：新增任务模型（TaskStatus/TaskInfo/TaskList）。
- [ ] `apps/api/app/api.py`：新增任务接口：
- [ ] `POST /analysis/tasks`
- [ ] `GET /analysis/tasks/{id}`
- [ ] `GET /analysis/tasks`
- [ ] `GET /analysis/tasks/stream`（SSE）
- [ ] `apps/web/src/app/search/page.tsx`：接入异步任务提交与状态展示。

### M3-B 向量存储可插拔

- [ ] `apps/api/app/services/vector_store.py`：抽象接口层（Chroma 实现保留）。
- [ ] `apps/api/app/services/simple_vector_store.py`（新增）：内存/JSON 简化实现（实验用）。
- [ ] `apps/api/app/config.py`：增加 `VECTOR_BACKEND=chroma|simple` 开关。
- [ ] `apps/api/app/services/analysis.py`：统一从接口层调用检索，不关心具体后端。
- [ ] A/B 评估结论：若 simple 方案召回率不低于基线且性能达标，可作为默认轻量选项。

### M3-C 测试与验收

- [ ] `apps/api/tests/test_analysis_task_queue.py`（新增）：重复提交冲突、状态流转、完成回收。
- [ ] `apps/api/tests/test_vector_store_backends.py`（新增）：两种后端一致性与降级行为。
- [ ] 验收指标：
- [ ] 异步任务接口可用，前端可感知 pending/running/completed。
- [ ] 检索召回命中率不低于基线（20 条问题集）。

---

## 3) 文件级改动映射（索引）

| 文件 | 里程碑 | 说明 |
|---|---|---|
| `apps/api/app/api.py` | M1/M2/M3 | 健康检查、刷新报告、任务接口 |
| `apps/api/app/models.py` | M1/M3 | 健康模型、任务模型 |
| `apps/api/app/state.py` | M1 | 运行时状态扩展 |
| `apps/api/app/services/ingestion.py` | M1 | 刷新报告返回 |
| `apps/api/app/services/analysis.py` | M1/M2/M3 | 调用埋点、日报元信息、后端可插拔 |
| `apps/api/app/services/vector_store.py` | M3 | 向量后端抽象 |
| `apps/api/app/services/simple_vector_store.py` | M3 | 简化向量存储实现 |
| `apps/api/app/sources/hkma_discovery.py` | M2 | HKMA 自动发现稳定性 |
| `apps/api/app/sources/hkma.py` | M2 | HKMA 标准化 |
| `apps/web/src/components/site-header.tsx` | M1 | 导航入口 |
| `apps/web/src/app/news/page.tsx` | M1 | 今日新闻页 |
| `apps/web/src/app/daily-summary/page.tsx` | M1/M2 | 日报摘要页 |
| `apps/web/src/app/search/page.tsx` | M1/M3 | 问答联动、任务态 UI |
| `apps/web/src/lib/api.ts` | M1/M3 | typed API 封装 |
| `packages/shared/src/types.ts` | M1/M3 | 共享类型补齐 |
| `.github/workflows/daily_refresh.yml` | M2 | 定时自动化 |
| `README.md` | M2 | 自动化与配置文档 |

---

## 4) 开发顺序（建议）

- [ ] 第 1-2 天：完成 M1-A（API 可观测）
- [ ] 第 3-4 天：完成 M1-B（新闻页与日报页）
- [ ] 第 5 天：完成 M1-C（测试与回归）
- [ ] 第 6-9 天：完成 M2-A（HKMA 产物稳定）
- [ ] 第 10-11 天：完成 M2-B（日报自动化 + workflow）
- [ ] 第 12 天：完成 M2-C（验收）
- [ ] 第 13 天后：进入 M3（任务编排 + 向量可插拔）
