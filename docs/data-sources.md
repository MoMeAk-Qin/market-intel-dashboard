# 免费数据源接口与字段映射

以下为测试期免费数据源的**具体接口**与字段映射，覆盖 EDGAR / HKEX / H.10 / Treasury / HKMA / FRED / RSS。所有请求均需配置 `User-Agent`，并遵守官方频率限制与使用条款。

## 1) SEC EDGAR（美股财报/公告）

**接口**
- 公司与 CIK 映射：
  - `https://www.sec.gov/files/company_tickers_exchange.json`
- 公司提交记录（核心）：
  - `https://data.sec.gov/submissions/CIK{CIK}.json`（CIK 需 10 位补零）
- 原始文件：
  - `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dash}/{primaryDocument}`

**字段映射**
- `company_tickers_exchange.json`
  - `cik_str` -> `company.cik`
  - `ticker` -> `company.ticker`
  - `title` -> `company.name`
  - `exchange` -> `company.exchange`
- `submissions CIK.json`（路径：`filings.recent`）
  - `form` -> `filing.form_type`
  - `filingDate` -> `filing.filing_date`
  - `reportDate` -> `filing.report_date`
  - `accessionNumber` -> `filing.accession_number`
  - `primaryDocument` -> `filing.primary_document`
  - `primaryDocDescription` -> `filing.title`
- `Event` 生成规则
  - `source_type = filing`
  - `event_type`：
    - `10-K/10-Q/20-F` => `earnings`
    - `8-K/6-K` => `regulation`（或 `risk`，由条目 `items` 判断）
  - `headline = "{ticker} {form} {primaryDocDescription}"`
  - `event_time = filingDate`
  - `evidence.source_url = 原始文件 URL`

## 2) HKEXnews（港股公告）

**接口**
- 公告检索页面（HTML 表格）：
  - `https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=en`

**字段映射**（解析页面表格）
- `Release Time` -> `filing.filing_date`（含时间）
- `Stock Code` -> `ticker`
- `Stock Short Name` -> `company.name`
- `Title` -> `filing.title` / `event.headline`
- `Document Link` -> `filing.source_url` / `event.evidence.source_url`

**事件规则**
- `source_type = filing`
- `event_type`：公告标题含 `results/earnings/profit warning` -> `earnings` / `risk`
- `markets = [HK]`

> 说明：HKEXnews 无官方公开 JSON，测试期使用 HTML 表格解析；生产可接授权接口或建立缓存。

## 3) 美联储 H.10（外汇）

**接口**
- 数据下载（官方 Data Download）：
  - `https://www.federalreserve.gov/datadownload/Download.aspx?rel=H10`

**字段映射（CSV）**
- `Series` -> `macro.series_id`
- `Time Period` -> `macro.date`
- `Value` -> `macro.value`

**示例 series**
- `H10/H10_NY_USD`（示意）
- `H10/H10_NY_JPY`
- `H10/H10_NY_EUR`

> 实际 series_id 以下载文件内 `Series` 列为准。

## 4) 美国财政部收益率曲线

**接口**
- Daily Treasury Yield Curve（CSV）：
  - `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/DailyTreasuryYieldCurveRateData.csv`

**字段映射**
- `Date` -> `macro.date`
- `1 Mo`/`2 Mo`/`3 Mo`/.../`30 Yr` -> `macro.value`
- `series_id` 规则：`UST_{TENOR}`，如 `UST_2Y` / `UST_10Y`

## 5) HKMA API（港元利率/资金面/外汇）

**发现入口（权威）**
- `https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/`

**实现方式**
- 不再手工维护 `{dataset}/{table}` 模板。
- 使用 `hkma-discovery` 自动递归发现 daily/monthly 数据表页面。
- 每页提取：
  - `API URL`
  - `Output Fields (JSON)`（含 `Unit Of Measure`）
  - 对应 API 的 OpenAPI JSON（提取 query 参数 + Record schema）

**自动化产物**
- `apps/api/app/sources/hkma_catalog.json`
- `apps/api/app/sources/hkma_endpoints.env`（`HKMA_ENDPOINTS=...`）
- `apps/api/app/sources/hkma_units.json`（`{api_url: {field: unit}}`）

**标准化（ingestion）**
- 按 catalog 拉取 records，拆分为 `MetricPoint`：
  - `provider=HKMA`
  - `series_id=HKMA.<API_SLUG>.<FIELD_NAME>`
  - `frequency=daily|monthly`
  - `date`、`value`
  - `unit_raw`（文档原始单位）/ `unit_norm`（归一化单位）

详细说明见 `docs/hkma-endpoints.md`。

## 6) FRED（宏观/利率/贵金属）

**接口**
- 观测值 API（需免费 API key）：
  - `https://api.stlouisfed.org/fred/series/observations?series_id={SERIES}&api_key={KEY}&file_type=json`

**字段映射**
- `observations[].date` -> `macro.date`
- `observations[].value` -> `macro.value`

**推荐 series_id（可扩展）**
- `DGS10` / `DGS2` / `DGS1MO`（美债收益率）
- `FEDFUNDS`（联邦基金目标利率）
- `CPIAUCSL`（CPI）
- `PCE`（PCE）
- `GOLDAMGBD228NLBM`（黄金伦敦早盘价）

## 7) 新闻 RSS（官方新闻稿 + 高质量媒体）

**接口（示例）**
- Fed Press：`https://www.federalreserve.gov/feeds/press_all.xml`
- US Treasury Press：`https://home.treasury.gov/news/press-releases/rss`
- HKMA Press：`https://www.hkma.gov.hk/eng/rss/press-release.xml`
- SEC Press：`https://www.sec.gov/rss/press-release.xml`

**字段映射**
- `entry.title` -> `event.headline`
- `entry.link` -> `event.evidence.source_url`
- `entry.published` -> `event.event_time`
- `feed.title` -> `event.publisher`
- `entry.summary` -> `event.summary` / `event.evidence.excerpt`

**事件主干规则（免费版）**
- 官方新闻稿 > 官方公告 > 高质量 RSS
- 同主题文章按标题相似度 + 时间窗去重合并
