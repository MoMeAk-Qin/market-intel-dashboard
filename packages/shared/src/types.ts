export type EventSourceType =
  | 'news'
  | 'filing'
  | 'earnings'
  | 'research'
  | 'macro_data';

export type EventType =
  | 'earnings'
  | 'guidance'
  | 'mna'
  | 'buyback'
  | 'rate_decision'
  | 'macro_release'
  | 'regulation'
  | 'risk';

export type Market = 'US' | 'HK' | 'FX' | 'RATES' | 'METALS';

export type Sector = 'Tech' | 'Industrials';
export type DataOrigin = 'live' | 'seed';

export type EventNumber = {
  name: string;
  value: number;
  unit?: string;
  period?: string;
  yoy?: number;
  qoq?: number;
  source_quote_id?: string;
};

export type EventEvidence = {
  quote_id: string;
  source_url: string;
  title: string;
  published_at: string;
  excerpt: string;
};

export type Event = {
  event_id: string;
  event_time: string;
  ingest_time: string;
  source_type: EventSourceType;
  publisher: string;
  headline: string;
  summary: string;
  event_type: EventType;
  markets: Market[];
  tickers: string[];
  instruments: string[];
  sectors: Sector[];
  numbers: EventNumber[];
  stance: 'positive' | 'negative' | 'neutral';
  impact: number;
  confidence: number;
  impact_chain: string[];
  evidence: EventEvidence[];
  related_event_ids?: string[];
  data_origin: DataOrigin;
};

export type AssetSeriesPoint = {
  date: string;
  value: number;
};

export type QuotePoint = {
  time: string;
  value: number;
};

export type QuoteSnapshot = {
  asset_id: string;
  price: number;
  change?: number | null;
  change_pct?: number | null;
  currency?: string | null;
  as_of: string;
  source: string;
  is_fallback: boolean;
};

export type QuoteSeries = {
  asset_id: string;
  range: '1D' | '1W' | '1M' | '1Y';
  source: string;
  is_fallback: boolean;
  points: QuotePoint[];
};

export type MetricDomain = 'quote' | 'macro' | 'fundamental';

export type AssetMetric = {
  metric_id: string;
  domain: MetricDomain;
  label: string;
  value: number;
  unit: string;
  as_of: string;
  source: string;
  is_fallback: boolean;
};

export type AssetProfile = {
  asset_id: string;
  name: string;
  market: Market;
  range: '1D' | '1W' | '1M' | '1Y';
  schema_version: string;
  quote: QuoteSnapshot;
  series: QuoteSeries;
  metrics: AssetMetric[];
  recent_events: Event[];
};

export type QAResponse = {
  answer: string;
  evidence: EventEvidence[];
};

export type AnalysisRequest = {
  question: string;
  context?: string;
  sources?: string[];
  use_retrieval?: boolean;
  top_k?: number;
};

export type AnalysisUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

export type AnalysisResponse = {
  answer: string;
  model: string;
  usage?: AnalysisUsage | null;
  sources: EventEvidence[];
};

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export type AnalysisTaskInfo = {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  payload: AnalysisRequest;
  result?: AnalysisResponse | null;
  error?: string | null;
};

export type AnalysisTaskList = {
  items: AnalysisTaskInfo[];
  total: number;
};

export type DailyNewsResponse = {
  date: string;
  items: Event[];
  total: number;
};

export type DailySummaryRequest = {
  focus?: string;
  markets?: string[];
  tickers?: string[];
  query?: string;
  limit?: number;
  use_retrieval?: boolean;
  top_k?: number;
};

export type DailySummaryResponse = {
  date: string;
  answer: string;
  model: string;
  total_news: number;
  usage?: AnalysisUsage | null;
  sources: EventEvidence[];
};

export type ResearchSourceType = 'live' | 'fallback';
export type ResearchCompanyType = 'listed' | 'unlisted';

export type ResearchNewsItem = {
  event_id: string;
  headline: string;
  summary: string;
  publisher: string;
  event_time: string;
  event_type: EventType;
  impact: number;
  confidence: number;
  source_type: EventSourceType;
  source_url: string;
  quote_id?: string | null;
};

export type ResearchAnalysisBlock = {
  answer: string;
  model: string;
  is_fallback: boolean;
  sources: EventEvidence[];
};

export type ResearchCompanyResponse = {
  ticker: string;
  company_type: ResearchCompanyType;
  source_type: ResearchSourceType;
  updated_at: string;
  quote?: QuoteSnapshot | null;
  earnings_card?: {
    headline: string;
    eps: { value: number; yoy?: number | null };
    revenue: { value: number; yoy?: number | null };
    guidance: string;
    sentiment: string;
  } | null;
  news: ResearchNewsItem[];
  analysis: ResearchAnalysisBlock;
  note?: string | null;
};

export type UnlistedSourceType = 'seed' | 'live';
export type UnlistedCompanyStatus = 'unlisted';

export type UnlistedCompany = {
  company_id: string;
  name: string;
  status: UnlistedCompanyStatus;
  core_products: string[];
  related_concepts: string[];
  description: string;
  source_type: UnlistedSourceType;
  updated_at: string;
};

export type UnlistedEvent = {
  company_id: string;
  event_id: string;
  event_time: string;
  headline: string;
  summary: string;
  publisher: string;
  event_type: EventType;
  impact: number;
  confidence: number;
  source_type: UnlistedSourceType;
  source_url: string;
  quote_id?: string | null;
};

export type UnlistedCompanyResponse = {
  company: UnlistedCompany;
  timeline: UnlistedEvent[];
  total_events: number;
  updated_at: string;
  note?: string | null;
};

export type HealthResponse = {
  ok: boolean;
  store_events: number;
  updated_at: string | null;
  vector_store_enabled: boolean;
  vector_store_ready: boolean;
};

export type PaginatedEvents = {
  items: Event[];
  page: number;
  pageSize: number;
  total: number;
};

export type DashboardSummary = {
  date: string;
  kpis: { major: number; macro: number; company: number; risk: number };
  key_assets: Array<{ id: string; name: string; value: number; changePct: number }>;
  timeline: Array<{ lane: 'macro' | 'industry' | 'company' | 'policy_risk'; events: Event[] }>;
  hot_tags: string[];
};

export type CorrelationPreset = 'A' | 'B' | 'C';
export type CorrelationWindowDays = 7 | 30 | 90;
export type HeatLevel = 'low' | 'medium' | 'high';
export type HeatSourceType = 'live' | 'seed' | 'mixed';

export type TechHeatItem = {
  asset_id: string;
  market: string;
  latest_price?: number | null;
  change_pct?: number | null;
  mentions_7d: number;
  avg_impact: number;
  heat_score: number;
  level: HeatLevel;
  source_type: HeatSourceType;
};

export type TechHeatmapResponse = {
  generated_at: string;
  threshold: number;
  items: TechHeatItem[];
};

export type CorrelationMatrixResponse = {
  preset: CorrelationPreset;
  window_days: CorrelationWindowDays;
  assets: string[];
  matrix: number[][];
  fallback_assets: string[];
  updated_at: string;
  note?: string | null;
};

export type CausalAnalyzeRequest = {
  event_id?: string;
  query?: string;
  max_depth?: number;
};

export type CausalNode = {
  level: number;
  label: string;
  detail: string;
  related_assets: string[];
  confidence: number;
  evidence: EventEvidence[];
};

export type CausalAnalyzeResponse = {
  event_id?: string | null;
  source_type: HeatSourceType;
  summary: string;
  nodes: CausalNode[];
  generated_at: string;
};

export type ModelRegistryResponse = {
  active_model: string;
  default_model: string;
  available_models: string[];
};

export type ModelSwitchRequest = {
  model: string;
};

export type ReportStatus = 'idle' | 'running' | 'completed' | 'failed';
export type ReportSourceType = 'live' | 'fallback';

export type DailyReportSnapshot = {
  report_id: string;
  target_date: string;
  generated_at?: string | null;
  status: ReportStatus;
  model: string;
  source_type: ReportSourceType;
  summary?: string | null;
  total_events: number;
  error?: string | null;
};
