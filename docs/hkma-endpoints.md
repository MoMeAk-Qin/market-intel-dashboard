# HKMA API 接入清单（自动发现 + 自动单位映射）

## 背景与结论

- 不再使用 `{dataset}/{table}` URL 模板，也不再人工确认 dataset/table。
- 以 HKMA 官方文档页（apidocs）中展示的 **API URL** 为唯一权威。
- 每个接口的字段与单位来自文档页 **Output Fields (JSON)** 表格（含 Unit Of Measure）。
- 接口的 query 参数、Record 字段类型来自对应 API URL 返回的 **OpenAPI JSON**。

最终目标：通过程序自动生成 `hkma_catalog.json`，并据此生成 `HKMA_ENDPOINTS`、字段/单位映射、以及 ingestion 所需的标准化规则。

---

## 文档入口（自动发现的根目录）

- Market Data and Statistics 根目录：
  https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/

该根目录下至少包含两类：
- Monthly Statistical Bulletin（按月）
- Daily Monetary Statistics（按日）

程序应递归抓取上述两类目录下的所有“具体数据表页面”。

---

## 自动化产物（作为开发交付物）

### 1) hkma_catalog.json（核心产物）
每个条目包含：
- frequency: daily | monthly
- doc_url: apidocs 页面
- api_url: 文档页的 API URL（真实 endpoint）
- openapi_summary:
  - base_url
  - endpoints (method/url)
  - query_params
  - record_fields（字段类型/format）
- fields_meta（来自 Output Fields 表格）：
  - name / type / unit_of_measure / description

### 2) hkma_endpoints.env（可选）
自动从 hkma_catalog.json 生成：
- HKMA_ENDPOINTS= <api_url1>,<api_url2>,...

### 3) hkma_units.json（可选）
按 api_url 分组输出：
- { api_url: { field_name: unit_of_measure } }

---

## MVP 优先接入（按日 + 按月都要）

### A. 日频（Daily Monetary Statistics）
用途：每日监控/分析（资金面、短端利率、联系汇率压力）
- Daily Figures of Interbank Liquidity
  - 关键字段（示例）：closing_balance、hibor_overnight、disc_win_base_rate、cu_weakside/cu_strongside、twi
  - 单位从 Output Fields 表自动获取

（后续可扩展：Daily Figures of Monetary Base 等）

### B. 月频（Monthly Statistical Bulletin）
用途：基准/同比环比（上月末、去年同期）
- Monetary Statistics（Monthly）
  - 关键字段（示例）：m1_total/m2_total/m3_total、monetary_base_total、aggr_balance、exrate_hkd_usd 等
  - 单位从 Output Fields 表自动获取

---

## ingestion 设计要求（给 Codex 的实现约束）

### 1) 采集分两步
1) Discover：
- 从 apidocs 根目录递归抓取所有具体数据表页面
- 每个页面抽取：
  - API URL
  - Output Fields (JSON) 表（字段/单位/描述）
- 再请求 API URL 返回 OpenAPI JSON，抽取参数/Record schema

2) Fetch data（后续 ingestion）：
- 使用 api_url + query（from/to/pagesize/offset 等）拉 records
- 解析返回：header/result/records

### 2) 指标标准化（建议的内部 schema）
把 HKMA “宽表 record” 拆成多条 MetricPoint（供前端画图/供分析）：
- provider="HKMA"
- series_id：建议规则 `HKMA.<API_SLUG>.<FIELD_NAME>`
- frequency: daily|monthly
- date: end_of_date / end_of_month
- value: number
- unit_raw: Unit Of Measure（原文）
- unit_norm: 归一化单位（可选，如 HK$ million -> HKD_mn）
- description: 文档描述

### 3) Daily vs Monthly 的使用规则
- Daily：每日分析输入（今日值 + 近14天滚动回看增量拉取）
- Monthly：基准对照（上月末、去年同期）用于 YoY/MoM
- 不混用同一条 series（daily/monthly 分开）

---

## 待办事项（新版）

1) 实现 hkma 文档自动发现（递归抓取）
2) 实现 Output Fields 表格解析（Name/Type/Unit Of Measure/Description）
3) 实现 OpenAPI JSON 摘要抽取（endpoints/params/record schema）
4) 生成 hkma_catalog.json（并纳入仓库版本控制）
5) 基于 hkma_catalog.json 自动生成：
   - HKMA_ENDPOINTS
   - units 映射表（可选）
6) 实现数据拉取与标准化（record -> MetricPoint）
7) 在 Dashboard/Asset 页面接入（先展示关键字段）