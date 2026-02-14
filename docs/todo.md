# TODO 清单（结合代码核对结果，更新于 2026-02-09）

实施清单入口：`docs/implementation-checklist.md`  
后续开发执行以 `docs/implementation-checklist.md` 为主；`docs/todo.md` 用于阶段目标与 KPI 复盘。

## 阶段 0：阻塞修复与一致性（必须先做）

- [x] 修复 `/events` 时间过滤与排序在混合时区输入下的运行时问题（后端）
- [x] 补齐并统一共享类型：`DailyNewsResponse` / `DailySummaryResponse` / `AnalysisRequest` / `AnalysisResponse`（`packages/shared`）
- [x] 统一前后端日期/时区使用方式（避免今日新闻跨日误差）

## 阶段 1：每日新闻闭环（MVP+，优先级最高）

- [x] 关注清单与过滤逻辑（用户关注市场/标的/关键词；默认应用到 `/news/today`、`/daily/summary`）
- [x] `/analysis` 输出模板固化（结论/影响/风险/关注点 + [n] 证据引用），并做结构化校验
- [x] 分析结果缓存（按问题+来源 hash，带 TTL），`/analysis` 与 `/daily/summary` 复用
- [x] `/qa` 由规则回答升级为“检索 + Qwen”或“向量检索 + Qwen”链路

验收标准 / 里程碑（含 KPI）：
- P95 响应时延：无缓存 ≤ 6s；命中缓存 ≤ 1.5s（本地环境）
- 检索召回：TopK 中至少 1 条有效证据命中率 ≥ 85%（20 条测试问题）
- 缓存命中率：同问题 24h 内重复请求命中率 ≥ 70%
测试方法 / 采样口径 / 统计周期：
- 延时：本地连续请求 30 次计算 P95；工作日/周末各测 1 次
- 召回：人工构造 20 条问题+对应证据（含 3 个市场、2 个时间窗），TopK=6；月度复测
- 缓存命中：选 10 条高频问题，24h 内重复请求 3 次；周度复测

## 阶段 2：前端对接与体验

- 新增“今日新闻”页面（默认当日 + 关注清单过滤）
- 日报摘要卡（答案 + 证据卡 + [n] 引用联动）
- 过滤与排序 UX（市场/标的/关键词/时间范围）
- 导航补入口，完善 `/analysis` 与 `/daily/summary` 的前端接入

验收标准 / 里程碑（含 KPI）：
- 主要页面首屏渲染 ≤ 2.5s（本地环境）
- 过滤交互响应 ≤ 300ms（本地环境）
- 前端错误率（5xx/网络错误）≤ 1%
测试方法 / 采样口径 / 统计周期：
- 首屏时间：本地冷启动 10 次取 P95；月度复测
- 交互响应：事件页切换 10 次过滤条件取均值；双周复测
- 错误率：按前端日志统计 7 天窗口；周度复盘

## 阶段 3：LLM 治理与可解释性

- 统一 LLM 调用封装（超时/重试/日志/耗时/Token 统计），只使用 Qwen（DashScope）
- LLM 输入规范与脱敏策略（仅传必要字段，避免长文本与敏感信息）
- 结构化输出合规性校验（模板字段齐全、证据编号存在）

验收标准 / 里程碑（含 KPI）：
- LLM 调用失败率 ≤ 2%（日级别）
- 结构化输出合规率 ≥ 90%（抽样评估）
- 平均 token 消耗较基线下降 ≥ 20%（启用缓存/截断后）
测试方法 / 采样口径 / 统计周期：
- 失败率：按“调用次数 × 错误类型”统计；周度复盘
- 合规率：抽样 50 条回答检查结构字段覆盖；月度复盘
- token：对比启用缓存/截断前后 50 条问题均值；双周复盘

## 阶段 4：数据源与质量（让“今日新闻更准更稳”）

- 确认 HKMA dataset/table 并完善字段映射（`docs/hkma-endpoints.md`）
- RSS 白名单梳理、增删与来源评级（官方 > 高质量媒体）
- 来源节流与重试策略统一（User-Agent、频控、退避）
- 事件去重与主干合并（标题相似度 + 时间窗 + 主干优先级）
- 数据质量与异常监控（缺失率、重复率、延迟统计）

验收标准 / 里程碑（含 KPI）：
- RSS 拉取成功率 ≥ 98%（日级别）
- 去重后重复率 ≤ 5%（按日事件集合）
- 数据延迟：源发布后 6 小时内入库比例 ≥ 90%
测试方法 / 采样口径 / 统计周期：
- RSS 成功率：按“源 × 天”统计；周度复盘
- 重复率：同日事件集合按标题+来源去重；周度复盘
- 数据延迟：抽样 30 条事件比对发布时间与入库时间；月度复盘

## 阶段 5：能力扩展（可选）

- 接入真实行情与财务数据源（替换免费测试源）
- 资产级视图与指标口径统一（行情/宏观/财报统一 schema）
- 可选接入 Postgres + pgvector（非 PC 端或高级用法）

验收标准 / 里程碑（含 KPI）：
- 行情更新成功率 ≥ 99%（日级别）
- 关键指标口径一致性测试通过率 = 100%
测试方法 / 采样口径 / 统计周期：
- 行情成功率：按“源 × 天”统计；月度复盘
- 口径一致性：抽样 20 个指标与前端展示比对；季度复盘

## 阶段 99：静态类型告警（最低优先级）

- `apps/api/app/services/http_client.py`：`request_with_retry` 透传参数类型过宽导致 httpx 参数类型告警
- `apps/api/app/services/ingestion.py`：`asyncio.gather` 返回异常/非列表的静态类型告警
- `apps/api/app/services/seed.py`：事件构造使用 `Literal` 类型的告警（`EventType` / `Market` / `Sector`）
- `apps/api/app/services/vector_store.py`：`chromadb` `upsert` 参数类型告警
- `apps/api/app/sources/edgar.py` / `apps/api/app/sources/hkex.py`：事件字段 `Literal` 类型告警
- `apps/api/app/sources/fred.py` / `apps/api/app/sources/rss.py`：`markets/sectors` 及文本解析相关类型告警
- `apps/api/tests/test_daily_news.py`：`Event` 构造参数 `Literal` 类型告警
