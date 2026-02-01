# 后端架构方案（免费数据源测试版）

## 目标

构建一个面向港股、美股、外汇、贵金属、债市的分析系统后端，支持财报/公告、研报视图、宏观与新闻事件聚合，优先覆盖科技与工业行业，采用每日早/晚两次更新。

> 推荐 Python 3.12（ChromaDB 在 3.12 环境下兼容性更佳）

## 数据源（免费）

- **财报/公告**
  - HK：HKEXnews（公告、年报/中报、盈警）
  - US：SEC EDGAR（10-K/10-Q/8-K）
- **宏观/利率/外汇**
  - 美联储 H.10（外汇）
  - 美国财政部收益率曲线（Daily Treasury Yield）
  - HKMA API（利率/流动性/外汇数据）
  - FRED（宏观与利率序列）
- **新闻**
  - 官方新闻稿：Fed / Treasury / HKMA / SEC / HKEX
  - 高质量 RSS：FT / WSJ / CNBC / MarketWatch / Nikkei（少量）
- **行情/基本面（免费测试）**
  - Yahoo Finance 非官方接口（港美股快照）
  - Stooq（历史行情补充）
  - FRED（利率/黄金/宏观时序补齐）

详细接口与字段映射见 `docs/data-sources.md`。

> 备注：Reuters/同级媒体需授权，测试期以官方新闻稿 + 高质量 RSS 作为事件主干来源。

## 核心流程

1. **采集**：按源类型拉取原始数据，保留 source_id/URL/发布时间
2. **规范化**：统一时间（UTC 存储、Asia/Hong_Kong 展示）、货币与实体标识
3. **去重聚合**：标题+时间窗+关键词相似度去重
4. **事件主干绑定**：官方新闻稿 > 官方公告/财报 > 高质量 RSS
5. **打标评分**：市场/行业、事件类型、影响度与置信度
6. **服务输出**：统一 API 给前端与后续检索系统

## 数据模型（核心）

- `Event`：统一事件（主干 + 证据链）
- `Filing`：财报/公告（EDGAR/HKEX）
- `NewsArticle`：新闻原文 + 摘要
- `MacroSeries`：宏观时序（H.10/FRED/Treasury/HKMA）
- `MarketSnapshot`：行情/估值/财务快照（日频）

## 更新策略

- **时区**：Asia/Hong_Kong
- **频率**：每日早/晚两次（默认 08:30 / 18:30）
- **实现**：APScheduler + CronTrigger
- **幂等性**：按 source_id/发布时间/标题 hash 去重

## 可观测性与重试

- 统一日志输出到 `apps/api/data/api.log`
- HTTP 请求带指数退避重试（可配置）

## API 设计（与前端对齐）

- `GET /health`
- `GET /dashboard/summary?date=YYYY-MM-DD`
- `GET /events`（筛选/排序/分页）
- `GET /events/:id`
- `GET /assets/:assetId/chart?range=1D|1W|1M|1Y`
- `GET /assets/:assetId/events?range=1D|1W|1M|1Y`
- `GET /research/company/:ticker`
- `POST /qa`
- `POST /analysis`（信源检索增强分析）

## 后续扩展

- PC 端默认使用 Chroma 作为嵌入式向量库（本地落盘），用于信源语义检索与 `/analysis` 检索增强；生产可切换到 Postgres + pgvector
- 引入 Postgres + pgvector 作为持久化与语义检索
- 接入授权新闻与研报源（Reuters/FactSet/Refinitiv 等）
- 增加多语言摘要、主题跟踪与信号强度回测
