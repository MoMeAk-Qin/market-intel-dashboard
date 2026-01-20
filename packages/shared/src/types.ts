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
};

export type AssetSeriesPoint = {
  date: string;
  value: number;
};

export type QAResponse = {
  answer: string;
  evidence: EventEvidence[];
};

export type DashboardSummary = {
  date: string;
  kpis: { major: number; macro: number; company: number; risk: number };
  key_assets: Array<{ id: string; name: string; value: number; changePct: number }>;
  timeline: Array<{ lane: 'macro' | 'industry' | 'company' | 'policy_risk'; events: Event[] }>;
  hot_tags: string[];
};
