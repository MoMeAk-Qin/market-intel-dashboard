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
