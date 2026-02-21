# TODO 清单（唯一开发计划入口，v2.2）

> 更新日期：2026-02-14
> 说明：后续开发计划、阶段状态、验收结果仅维护在本文件。
> 重要：执行任何任务时，必须同步参看 `docs/master-plan-v2.md`、`docs/implementation-roadmap-v2.md`、`docs/feasibility-assessment.md`。

---

## 0. 使用规则

1. 本文件是 Single Source of Truth，其他规划文档不再维护勾选状态。
2. 新需求先写入对应阶段任务（带编号），再开始开发。
3. 每次提交后必须回写任务状态（`[ ]` -> `[x]`）并补一句结果备注。
4. 开发执行时，`todo.md` 只负责“做什么和先后顺序”，详细实现必须回到三份配套文档核对。

---

## 0.1 AI Agent 同步参看规则（必须）

1. 开工前必须同时阅读以下文档的对应章节：
- `docs/todo.md`：任务编号、执行顺序、完成状态。
- `docs/master-plan-v2.md`：目标边界、术语口径、阶段验收框架。
- `docs/implementation-roadmap-v2.md`：文件级改动点、接口与实现步骤。
- `docs/feasibility-assessment.md`：风险、前提条件、资源与回退约束。
2. 文档冲突时按以下优先级执行：
- 任务顺序与完成状态：以 `docs/todo.md` 为准。
- 具体文件路径与实施步骤：以 `docs/implementation-roadmap-v2.md` 为准。
- 业务边界与验收口径：以 `docs/master-plan-v2.md` 为准。
- 风险分级与实施前提：以 `docs/feasibility-assessment.md` 为准。
3. 若仍存在冲突或信息缺失，先在本文件新增“待澄清”任务，再进入代码实现。

---

## 0.2 AI Agent 单任务执行模板（建议严格遵循）

1. 选择当前阶段第一个未完成任务（如 `P6-S1-A`）。
2. 从 `master-plan-v2.md` 提取该任务的目标与验收边界。
3. 从 `implementation-roadmap-v2.md` 提取对应文件改动与实现步骤。
4. 从 `feasibility-assessment.md` 检查前提条件与主要风险。
5. 按步骤实现代码并补齐最小必要测试。
6. 执行验证命令并记录结果（通过/失败与原因）。
7. 回写 `docs/todo.md`：勾选任务、补“结果备注”和“遗留风险”。
8. 提交时在 commit message 中包含任务编号（示例：`feat: implement P6-S1-A pg vector store`）。

---

## 0.3 周期代码审查节奏（Lite）

1. 每次 `git push` 前自动执行轻量审查：`pnpm review:light`（由 `.githooks/pre-push` 触发）。
2. 每个阶段结束手动执行深度审查：`pnpm review:deep -- --stage=<phase>`。
3. 关键发布前手动执行全链路审查：`pnpm review:release`。
4. 审查结果归档：
- 深度审查：`docs/reviews/deep/`
- 发布审查：`docs/reviews/release/`

---

## 1. 当前进度快照

- [x] 阶段0：阻塞修复与一致性
- [x] 阶段1：每日新闻闭环（MVP+）
- [x] 阶段2：前端对接与体验
- [x] 阶段3：HKMA 自动化与数据标准化
- [x] 阶段4：任务编排与向量可插拔
- [x] 阶段5：能力扩展（真实行情 + 统一模型 + E2E + 可选 pgvector）
- [x] 阶段99：静态类型告警收口（并行低优先）
- [ ] 阶段6：Postgres + pgvector 索引优化与运维脚本
- [ ] 阶段7：Research 页面真实数据链路
- [ ] 阶段8：未上市公司情报引擎
- [ ] 阶段9：科技热度 + 关联分析 + 因果链路
- [ ] 阶段10：多模型切换 + 定时报告

---

## 2. 下一步执行顺序（从现在开始）

1. 阶段6：Postgres + pgvector
2. 阶段7：Research 真实化
3. 阶段8：未上市公司情报
4. 阶段9：热度与关联分析
5. 阶段10：多模型与定时报告

---

## 3. 阶段99：静态类型告警收口

### 3.1 任务清单

- [x] `P99-S1-A` 收敛 `apps/api/app/services/seed.py` 的 `Literal`/强类型告警（结果：`EventSourceType/EventType/Market/Sector` 推断收敛）
- [x] `P99-S1-B` 收敛 `apps/api/app/services/vector_store.py` 的向量参数类型告警（结果：Chroma 元数据/向量类型显式化，`psycopg` 可选依赖注释追踪）
- [x] `P99-S1-C` 收敛 `apps/api/app/sources/edgar.py`、`apps/api/app/sources/hkex.py` 事件类型告警（结果：事件与行业推断函数返回强类型）
- [x] `P99-S1-D` 收敛 `apps/api/app/sources/fred.py`、`apps/api/app/sources/rss.py` 文本解析与字段类型告警（结果：市场/事件/行业返回强类型）
- [x] `P99-S1-E` 收敛 `apps/api/tests/test_daily_news.py` 测试构造类型告警（结果：测试 helper 参数改为 `list[Market]`）
- [x] `P99-S1-F` 将类型检查纳入 CI（失败阻断）（结果：新增 `.github/workflows/typecheck.yml` + 基线门禁脚本）

### 3.2 验收

- [x] `uvx pyright --pythonpath apps/api/.venv/bin/python` 针对阶段99目标文件无告警
- [x] 现存告警均有注释或追踪文档（见 `docs/typecheck-baseline.md` 与 `tools/typecheck/pyright-baseline.json`）

---

## 4. 阶段6：Postgres + pgvector 索引优化与运维脚本

### 4.1 任务清单（P6-S1）

- [ ] `P6-S1-A` 新建 `apps/api/app/services/pg_vector_store.py`，实现 upsert/query/healthcheck
- [ ] `P6-S1-B` 修改 `apps/api/app/config.py`，新增 `ENABLE_PGVECTOR`、`PG_DSN`、`PGVECTOR_TABLE`
- [ ] `P6-S1-C` 修改 `apps/api/app/services/ingestion.py`，实现 Chroma/PG 双路由写入
- [ ] `P6-S1-D` 新建 `apps/api/tools/sql/001_pgvector_init.sql`（扩展、建表、索引）
- [ ] `P6-S1-E` 新建 `apps/api/tools/pg/healthcheck.py` 与 `apps/api/tools/pg/backfill_vectors.py`
- [ ] `P6-S1-F` 新建 `apps/api/tests/test_pg_vector_store.py`（开关行为与回退测试）

### 4.2 验收

- [ ] 开关关闭时保持现有行为
- [ ] 开关开启时写入/检索可用
- [ ] 工具脚本可独立运行并输出状态

---

## 5. 阶段7：Research 页面真实数据链路

### 5.1 任务清单（P7-S1）

- [ ] `P7-S1-A` 新建 `apps/api/app/sources/earnings.py`（财报获取 + 强类型模型）
- [ ] `P7-S1-B` 修改 `apps/api/app/api.py`，重构 `GET /research/company/{id}` 返回结构
- [ ] `P7-S1-C` 修改 `apps/api/app/services/analysis.py`，统一检索+分析链路并附引用
- [ ] `P7-S1-D` 修改 `apps/web/src/app/research/page.tsx`，去除演示态文案并展示来源/时间
- [ ] `P7-S1-E` 修改 `apps/web/src/lib/api.ts`，补齐 Research 类型定义
- [ ] `P7-S1-F` 新建 `apps/api/tests/test_research_api.py`（正常/缺失/回退路径）

### 5.2 验收

- [ ] 不再出现硬编码固定回答路径
- [ ] 页面可见 `source_type` 与 `updated_at`
- [ ] 回退场景文案准确且可用

---

## 6. 阶段8：未上市公司情报引擎

### 6.1 任务清单（P8-S1）

- [ ] `P8-S1-A` 修改 `apps/api/app/models.py` 新增未上市公司模型
- [ ] `P8-S1-B` 新建 `apps/api/app/services/unlisted_tracker.py`（画像/事件/时间线）
- [ ] `P8-S1-C` 修改 `apps/api/app/services/ingestion.py` 接入 `sync_from_events`
- [ ] `P8-S1-D` 修改 `apps/api/app/api.py` 增加 `/unlisted/companies` 系列端点
- [ ] `P8-S1-E` 新建 `apps/api/tests/test_unlisted_tracker.py`
- [ ] `P8-S1-F` 修改 `apps/web/src/app/research/page.tsx` 支持未上市公司展示
- [ ] `P8-S1-G` API 与前端显式区分 `source_type=seed/live`
- [ ] `P8-S1-H` 落地“修订后 14 家未上市种子列表”（见 6.3 执行基线）
- [ ] `P8-S1-I` 增加 `MiniMax` 预留关注条目（未上市，待后续上市后转入上市资产池）

### 6.2 验收

- [ ] 至少 14 家未上市公司可查询
- [ ] 关键事件可追溯来源
- [ ] Seed/实时数据无混淆

### 6.3 执行基线（修订后未上市种子）

| 公司 | 状态 | 核心产品 | 关联概念 |
|------|------|---------|---------|
| OpenAI | 未上市 | GPT 系列, Sora | MSFT |
| Anthropic | 未上市 | Claude 系列 | GOOGL |
| ByteDance | 未上市 | 豆包大模型, 云雀 | 省广集团等 |
| Moonshot AI | 未上市 | Kimi | 未上市 |
| Databricks | 未上市 | 数据 AI 平台 | 未上市 |
| Stripe | 未上市 | 支付基础设施 | 未上市 |
| SpaceX | 未上市 | 星链, 火箭 | 未上市 |
| Scale AI | 未上市 | 数据标注 | 未上市 |
| Anduril | 未上市 | 国防科技 | 未上市 |
| Figure AI | 未上市 | 人形机器人 | 未上市 |
| 01万物（零一万物） | 未上市 | 通用大模型 | 未上市 |
| 百川智能 | 未上市 | 通用大模型 | 未上市 |
| 阶跃星辰 | 未上市 | 多模态大模型 | 未上市 |
| DeepSeek | 未上市 | 推理大模型 | 未上市 |

---

## 7. 阶段9：科技热度 + 关联分析 + 因果链路

### 7.1 任务清单（P9-S1）

- [ ] `P9-S1-A` 新建 `apps/api/app/services/tech_heatmap.py`
- [ ] `P9-S1-B` 新建 `apps/api/app/services/correlation_engine.py`
- [ ] `P9-S1-C` 新建 `apps/api/app/services/causal_analyzer.py`
- [ ] `P9-S1-D` 修改 `apps/api/app/config.py`（预设组合与阈值）
- [ ] `P9-S1-E` 修改 `apps/api/app/api.py` 增加 `/tech/*`、`/correlation/*`
- [ ] `P9-S1-F` 新建 `apps/web/src/components/CorrelationMatrix.tsx`
- [ ] `P9-S1-G` 新建 `apps/web/src/app/correlation/page.tsx`
- [ ] `P9-S1-H` 新建 `apps/api/tests/test_correlation.py`
- [ ] `P9-S1-I` 实现前端“方案 A/B/C”页签切换（与后端预设一一对应）
- [ ] `P9-S1-J` 扩展科技关注资产池（美股 12 + 港股 8，见 7.3 执行基线）

### 7.2 验收

- [ ] 3 套预设矩阵可返回
- [ ] 因果链路结构化输出
- [ ] 前端可切换预设与窗口

### 7.3 执行基线（资产组合与关注池）

上市科技关注池（美股）：
`NVDA`, `MSFT`, `AAPL`, `AMZN`, `META`, `GOOGL`, `TSLA`, `AMD`, `AVGO`, `ARM`, `PLTR`, `CRM`

上市科技关注池（港股）：
`0700.HK`, `9988.HK`, `3690.HK`, `9618.HK`, `9866.HK`, `1810.HK`, `2015.HK`, `1024.HK`

未上市待转入关注池：
`MiniMax`（当前按未上市处理）

方案 A（宏观核心）：
`DXY + US10Y + US02Y + XAUUSD + NASDAQ + 0700.HK`

方案 B（AI 产业链）：
`NVDA + AMD + AVGO + MSFT + GOOGL + NASDAQ + DXY`

方案 C（中美科技联动）：
`NASDAQ + 0700.HK + DXY + US10Y + XAUUSD`

---

## 8. 阶段10：多模型切换 + 定时报告

### 8.1 任务清单（P10-S1）

- [ ] `P10-S1-A` 修改 `apps/api/app/config.py` 增加模型注册配置
- [ ] `P10-S1-B` 修改 `apps/api/app/services/analysis.py` 支持按模型路由
- [ ] `P10-S1-C` 新建 `apps/api/app/services/scheduled_tasks.py`
- [ ] `P10-S1-D` 修改 `apps/api/app/api.py` 增加模型查询/切换端点
- [ ] `P10-S1-E` 新建 `apps/web/src/components/ModelSelector.tsx`
- [ ] `P10-S1-F` 新建 `apps/web/src/components/ReportBadge.tsx`

### 8.2 验收

- [ ] 至少 2 个模型可切换
- [ ] 每日报告定时生成稳定
- [ ] Dashboard 显示最新报告状态

---

## 9. 里程碑与工时（v2.2）

| 阶段 | 预估工时 | 里程碑 |
|------|---------|------|
| 阶段99 | 2-4 小时（并行） | 类型告警受控 |
| 阶段6 | 8-12 小时 | PG 向量链路可开关 |
| 阶段7 | 10-14 小时 | Research 真实化完成 |
| 阶段8 | 8-12 小时 | 未上市情报可查询 |
| 阶段9 | 10-15 小时 | 相关/因果/热度联动 |
| 阶段10 | 5-8 小时 | 模型切换+定时报告 |
| 总计 | 43-65 小时 | v2.2 全量目标 |

---

## 10. 文档索引

- 总体方案：`docs/master-plan-v2.md`
- 详细步骤：`docs/implementation-roadmap-v2.md`
- 可行性评估：`docs/feasibility-assessment.md`
