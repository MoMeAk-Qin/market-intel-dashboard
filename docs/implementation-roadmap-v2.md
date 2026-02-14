# 详细实施计划（Implementation Roadmap）

> 版本：v2.2（路径与阶段对齐可执行版）
> 更新日期：2026-02-14
> 说明：执行状态勾选与优先级只在 `docs/todo.md` 维护；本文档提供落地步骤。

---

## 0. 执行约定

1. 后端路径统一为 `apps/api/app/...`，前端路径统一为 `apps/web/src/...`。
2. 新能力默认“开关关闭”，不破坏现有可运行链路。
3. 每阶段交付至少包含：代码、测试、文档更新（`docs/todo.md` 状态回写）。
4. 阶段执行顺序：阶段99（并行）→ 阶段6 → 阶段7 → 阶段8 → 阶段9 → 阶段10。

---

## 阶段99：静态类型告警收口（并行低优先）

### 文件范围

| 类型 | 文件 |
|------|------|
| 修改 | `apps/api/app/services/seed.py` |
| 修改 | `apps/api/app/services/vector_store.py` |
| 修改 | `apps/api/app/sources/edgar.py` |
| 修改 | `apps/api/app/sources/hkex.py` |
| 修改 | `apps/api/app/sources/fred.py` |
| 修改 | `apps/api/app/sources/rss.py` |
| 修改 | `apps/api/tests/test_daily_news.py` |

### 可执行步骤

1. 收敛 `Literal` 类型告警，补齐强类型别名与显式转换。
2. 收敛向量写入参数类型，避免 `Any` 扩散。
3. 在 CI 中增加静态检查步骤（失败即阻断合并）。

### 验收

- [ ] `uv run pyright` 无新增告警
- [ ] 已知告警有注释和 issue 追踪

---

## 阶段6：Postgres + pgvector 索引优化与运维脚本

### 目标

在保留默认 InMemory/Chroma 行为的前提下，提供可选 PG 向量后端，支持初始化、健康检查、回填和回滚。

### 文件变更

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新建 | `apps/api/app/services/pg_vector_store.py` | PG 向量存储实现 |
| 修改 | `apps/api/app/services/ingestion.py` | 向量写入路由（chroma/pg） |
| 修改 | `apps/api/app/config.py` | PG 开关与连接配置 |
| 新建 | `apps/api/tools/sql/001_pgvector_init.sql` | 建表与索引脚本 |
| 新建 | `apps/api/tools/pg/healthcheck.py` | 健康检查脚本 |
| 新建 | `apps/api/tools/pg/backfill_vectors.py` | 回填脚本 |
| 新建 | `apps/api/tests/test_pg_vector_store.py` | 单元测试 |

### 可执行步骤

1. 在 `config.py` 新增配置：
   - `ENABLE_PGVECTOR: bool = False`
   - `PG_DSN: str | None`
   - `PGVECTOR_TABLE: str = "event_vectors"`
2. 实现 `pg_vector_store.py`：
   - `upsert_events(...)`
   - `query_similar(...)`
   - `healthcheck()`
3. 在 `ingestion.py` 按开关路由向量写入：
   - `ENABLE_PGVECTOR=False` 走现有 Chroma
   - `ENABLE_PGVECTOR=True` 走 PG
4. 增加 SQL 初始化脚本：启用 `vector` 扩展、建表、建索引。
5. 增加工具脚本：
   - 健康检查
   - 事件向量回填
6. 增加测试：
   - 开关行为
   - 写入成功/失败回退
   - 查询结果结构校验

### 验收

- [ ] 开关关闭时行为与当前一致
- [ ] 开关打开时可完成写入和检索
- [ ] 脚本可独立运行并输出明确状态

---

## 阶段7：Research 页面真实数据链路

### 目标

将 Research 从演示态升级为真实链路，确保返回结果可追溯来源并支持前端展示。

### 文件变更

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新建 | `apps/api/app/sources/earnings.py` | 财报数据获取 |
| 修改 | `apps/api/app/api.py` | `research` 端点真实化 |
| 修改 | `apps/api/app/services/analysis.py` | 研究分析拼装与引用 |
| 修改 | `apps/web/src/app/research/page.tsx` | 移除演示文案，显示来源/时间 |
| 修改 | `apps/web/src/lib/api.ts` | 研究接口类型与字段 |
| 新建 | `apps/api/tests/test_research_api.py` | 后端研究接口测试 |

### 可执行步骤

1. 新增财报抓取 `fetch_earnings(ticker)`，定义强类型返回模型。
2. 重构 `GET /research/company/{id}`：
   - 上市公司：行情 + 财报 + 相关新闻 + 分析
   - 未上市公司（若命中）：返回占位结构并附来源说明
3. 删除硬编码演示回答路径，统一走检索+分析链路。
4. 前端研究页：
   - 展示 `source_type`、`updated_at`
   - 当数据回退时明确标注“回退数据”而非“演示行情”
5. 增加 API 测试：正常路径、数据缺失路径、回退路径。

### 验收

- [ ] 研究接口不再返回固定模板答案
- [ ] 页面可见来源与时间戳
- [ ] 失败场景回退可用且文案准确

---

## 阶段8：未上市公司情报引擎

### 目标

建立未上市公司画像、关键事件与时间线能力，并与现有事件流对齐。

### 修订后种子基线（必须落地）

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

### 文件变更

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `apps/api/app/models.py` | 新增未上市公司相关模型 |
| 新建 | `apps/api/app/services/unlisted_tracker.py` | 情报追踪服务 |
| 修改 | `apps/api/app/services/ingestion.py` | 事件同步到未上市引擎 |
| 修改 | `apps/api/app/api.py` | 未上市公司查询端点 |
| 新建 | `apps/api/tests/test_unlisted_tracker.py` | 测试 |
| 修改 | `apps/web/src/app/research/page.tsx` | 支持未上市公司展示 |

### 可执行步骤

1. 在 `models.py` 增加：`UnlistedCompany`、`UnlistedEvent`、`UnlistedCompanyResponse`。
   - `UnlistedCompany` 至少包含：`company_id`, `name`, `status`, `core_products`, `related_concepts`, `description`。
2. 在 `unlisted_tracker.py` 实现：
   - 公司种子加载
   - 事件匹配（实体 + 事件类型）
   - 查询接口
   - 按“修订后种子基线”内置 14 家初始公司，支持后续增量维护。
3. 在 `ingestion.py` 每轮处理后调用 `sync_from_events(...)`。
4. 在 `api.py` 增加：
   - `GET /unlisted/companies`
   - `GET /unlisted/companies/{company_id}`
5. 增加来源类型字段：`source_type=seed/live`，避免混淆。

### 验收

- [ ] 至少 14 家未上市公司可查询
- [ ] 事件时间线可回溯到来源
- [ ] Seed 与实时数据在 API/前端均可区分

---

## 阶段9：科技热度 + 关联分析 + 因果链路

### 目标

在 Dashboard 提供可操作的“热点 + 相关性 + 因果”组合视图。

### 文件变更

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 新建 | `apps/api/app/services/tech_heatmap.py` | 热度评分与异动检测 |
| 新建 | `apps/api/app/services/correlation_engine.py` | 相关性计算 |
| 新建 | `apps/api/app/services/causal_analyzer.py` | 因果链分析 |
| 修改 | `apps/api/app/config.py` | 预设组合与阈值配置 |
| 修改 | `apps/api/app/api.py` | 热度/相关/因果端点 |
| 新建 | `apps/web/src/components/CorrelationMatrix.tsx` | 相关矩阵组件 |
| 新建 | `apps/web/src/app/correlation/page.tsx` | 关联分析页面 |
| 新建 | `apps/api/tests/test_correlation.py` | 后端测试 |

### 可执行步骤

1. 在 `config.py` 定义预设组合（与前端页签一一对应）：
   - 方案 A（宏观核心）`MACRO_CORE = [DXY, US10Y, US02Y, XAUUSD, NASDAQ, 0700.HK]`
   - 方案 B（AI 产业链）`AI_SUPPLY_CHAIN = [NVDA, AMD, AVGO, MSFT, GOOGL, NASDAQ, DXY]`
   - 方案 C（中美科技联动）`CROSS_BORDER_TECH = [NASDAQ, 0700.HK, DXY, US10Y, XAUUSD]`
   - 若 `US02Y` 暂无实时行情，必须提供降级策略（回退/跳过并给出前端提示）。
2. 实现热度服务：价格异动、新闻热度、综合评分。
3. 实现相关性服务：7/30/90 天矩阵与两两相关查询。
4. 实现因果服务：输入事件，输出分层传导链与证据引用。
5. 新增端点：
   - `GET /tech/heatmap`
   - `GET /correlation/matrix`
   - `POST /correlation/analyze`
6. 前端新增矩阵页，支持“方案 A/B/C”页签切换与窗口切换。

### 验收

- [ ] 3 套预设均可返回矩阵
- [ ] 因果分析返回结构化链路结果
- [ ] 前端可展示并交互切换

---

## 阶段10：多模型切换 + 定时报告

### 目标

支持按任务选择模型并自动生成日度报告。

### 文件变更

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 修改 | `apps/api/app/config.py` | 多模型配置 |
| 修改 | `apps/api/app/services/analysis.py` | 按模型路由调用 |
| 新建 | `apps/api/app/services/scheduled_tasks.py` | 定时任务编排 |
| 修改 | `apps/api/app/api.py` | 模型配置端点 |
| 新建 | `apps/web/src/components/ModelSelector.tsx` | 模型切换组件 |
| 新建 | `apps/web/src/components/ReportBadge.tsx` | 报告提醒组件 |

### 可执行步骤

1. 在 `config.py` 增加模型注册结构与默认模型配置。
2. 在 `analysis.py` 增加 `get_client(model_name)` 路由能力。
3. 在 `api.py` 提供模型查询/切换接口。
4. 新增 `scheduled_tasks.py`，设置每日报告任务（默认 17:00）。
5. 前端增加模型选择与新报告提示。

### 验收

- [ ] 模型切换可生效并可回滚
- [ ] 每日报告按计划写入并可下载
- [ ] 前端可见当前模型与新报告状态

---

## 依赖关系（执行图）

```text
阶段99（并行）
  ↓
阶段6（基础增强）
  ↓
阶段7（Research真实化）
  ↓
阶段8（未上市情报）
  ↓
阶段9（热度+关联+因果）
  ↓
阶段10（多模型+定时报告）
```

---

## 工时估算（v2.2）

| 阶段 | 预估工时 |
|------|---------|
| 阶段99 | 2-4 小时（并行） |
| 阶段6 | 8-12 小时 |
| 阶段7 | 10-14 小时 |
| 阶段8 | 8-12 小时 |
| 阶段9 | 10-15 小时 |
| 阶段10 | 5-8 小时 |
| **总计** | **43-65 小时** |

---

*文档版本：v2.2 - 路径与阶段对齐可执行版*
