你是一个资深全栈工程师与 DevOps 工程师。请在本地生成一个可直接运行的 monorepo（pnpm workspace），并在 GitHub 上创建一个新的仓库并把代码推送上去。你必须执行必要的 shell 命令完成创建与推送。

===== 运行环境与前置假设（请先检查）=====
- 运行环境：macOS
- 必须具备：node >= 18、pnpm、git
- 使用GitHub mcp

===== 项目目标 =====
生成并推送一个「方案2：港股/美股/外汇/贵金属/债市分析系统」MVP 代码仓库：
- monorepo（pnpm workspace）：
  - apps/web  (Next.js 14+ App Router, TypeScript)
  - apps/api  (Node.js + Fastify 或 Express, TypeScript)
  - packages/shared (共享类型与 schema)
- 一键启动：
  - web: http://localhost:3000
  - api: http://localhost:4000
- 前端通过 NEXT_PUBLIC_API_BASE_URL 调用后端
- React Query、Recharts、TanStack Table、Tailwind + shadcn/ui（统一用这一套）
- 事件详情 Drawer/Modal
- 列表筛选/排序/分页
- mock 数据驱动（不使用数据库）

===== 必须实现的页面 =====
1) Dashboard (/)
2) Event Hub (/events)
3) Asset Detail (/asset/[id])
4) Research (/research)
5) Search & Q&A (/search)

===== 数据契约（必须严格使用 TypeScript 类型）=====
在 packages/shared/src/types.ts 定义并导出：
Event、AssetSeriesPoint、QAResponse、DashboardSummary
（字段详见下方“数据结构”）

Event:
- event_id: string (uuid)
- event_time: string (ISO)
- ingest_time: string (ISO)
- source_type: "news" | "filing" | "earnings" | "research" | "macro_data"
- publisher: string
- headline: string
- summary: string
- event_type: "earnings" | "guidance" | "mna" | "buyback" | "rate_decision" | "macro_release" | "regulation" | "risk"
- markets: Array<"US" | "HK" | "FX" | "RATES" | "METALS">
- tickers: string[]
- instruments: string[]
- sectors: Array<"Tech" | "Industrials">
- numbers: Array<{ name: string; value: number; unit?: string; period?: string; yoy?: number; qoq?: number; source_quote_id?: string }>
- stance: "positive" | "negative" | "neutral"
- impact: number (0-100)
- confidence: number (0-1)
- impact_chain: string[]
- evidence: Array<{ quote_id: string; source_url: string; title: string; published_at: string; excerpt: string }>
- related_event_ids?: string[]

AssetSeriesPoint:
- date: string (YYYY-MM-DD)
- value: number

QAResponse:
- answer: string
- evidence: Event["evidence"]

DashboardSummary:
- date: string
- kpis: { major: number; macro: number; company: number; risk: number }
- key_assets: Array<{ id: string; name: string; value: number; changePct: number }>
- timeline: Array<{ lane: "macro" | "industry" | "company" | "policy_risk"; events: Event[] }>
- hot_tags: string[]

===== 后端 API（apps/api）必须实现 =====
- GET /health -> { ok: true }
- GET /dashboard/summary?date=YYYY-MM-DD -> DashboardSummary
- GET /events 支持 query:
  from,to,market,sector,type,stance,minImpact,minConfidence,q,page,pageSize
  返回: { items: Event[]; page: number; pageSize: number; total: number }
- GET /events/:id -> Event
- GET /assets/:assetId/chart?range=1D|1W|1M|1Y -> { assetId, range, series: AssetSeriesPoint[] }
- GET /assets/:assetId/events?range=1D|1W|1M|1Y -> { assetId, items: Event[] }
- GET /research/company/:ticker -> { ticker; earnings_card; reports; fact_check }
- POST /qa body { question: string } -> QAResponse（evidence >= 1，按关键词返回不同答案）

mock 数据：
- apps/api/src/mock/data.ts 生成 80 条 Event
- 每条至少 1 evidence、impact_chain 3-5 条、impact/confidence 合理分布
- evidence.source_url 使用示例链接（不要抓取真实网页）

===== 前端要求（apps/web）=====
- TanStack React Query 管理请求
- apps/web/src/lib/api.ts 封装 fetcher（错误处理、query string）
- 每页 loading / error / empty
- Events：Filters -> query params -> refetch；点击后再 GET /events/:id 拉详情
- Asset Detail：id 支持 DXY/XAUUSD/US10Y/NASDAQ/AAPL/0700.HK 等
- 简洁产品化 UI（不要花哨）

===== 工程要求 =====
- TypeScript strict
- ESLint + Prettier（最少即可）
- README：安装、启动、API 列表、未来接 Postgres/pgvector TODO
- .env.example（web/api 各一份）

===== GitHub 仓库创建与推送（必须完成）=====
1) 生成代码仓库目录名：market-intel-dashboard
2) `git init`，提交 initial commit
3) 创建 GitHub 新仓库（public），仓库名：market-intel-dashboard
   - 优先使用：`gh repo create market-intel-dashboard --public --source=. --remote=origin --push`
   - 如果没有 gh：
     - 若存在 GITHUB_TOKEN 且能调用 GitHub API，则用 curl 创建 repo（需要用户名）并 git push
     - 否则输出清晰指令提示用户安装 gh 或登录：`gh auth login`
4) 推送成功后，在终端输出仓库 URL

===== 输出要求 =====
- 你必须实际写文件到磁盘并执行命令（mkdir、cat/heredoc、pnpm install 等）
- 创建完成后，运行一次：
  - pnpm i
  - pnpm dev（可以后台启动后立刻停止，确认能跑起来即可）
- 最后输出：
  - 本地路径
  - 如何启动
  - GitHub 仓库 URL

现在开始执行：先自检依赖与登录状态，然后生成项目文件，再创建仓库并推送。
