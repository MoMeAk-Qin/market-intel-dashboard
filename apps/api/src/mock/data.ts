import { randomUUID } from 'crypto';
import type { Event, EventNumber, EventSourceType, EventType, Market, Sector } from '@market/shared';

const publishers = [
  'Bloomberg Wire',
  'Market Pulse',
  'Rates Desk',
  'Alpha Ledger',
  'Pacific Markets',
  'Crown Research',
  'Summit Macro',
  'Atlas Insight',
  'Harbor Analytics',
  'Northbridge Daily',
];

const headlineTemplates = [
  'Policy signals reshape {market} positioning',
  '{ticker} posts resilient demand in core segments',
  '{ticker} guides {direction} on margin outlook',
  '{market} volatility rises as liquidity thins',
  'Deal chatter lifts {sector} breadth',
  'Macro print surprises on {macro}',
  'Central bank delivers {stance} tone',
  '{ticker} announces capital return update',
  '{sector} supply chain normalizes faster than expected',
  'Risk sentiment softens after {macro} shock',
];

const summaryTemplates = [
  'Traders recalibrated exposure after the latest release, with follow-through expected across the next two sessions.',
  'The update shifts consensus ranges, lifting dispersion across peer names and reinforcing a more selective stance.',
  'Early price action suggests positioning was light, leaving room for a follow-on move if confirmation data arrives.',
  'Liquidity pockets remain thin, and intraday swings are likely to persist into the next macro catalyst.',
  'Analysts flagged a better mix shift, but highlighted cost discipline as the main determinant of earnings power.',
  'The announcement underscores a cautious tone in guidance while keeping optionality for upside revisions.',
];

const macroTags = ['inflation', 'jobs', 'growth', 'liquidity', 'policy'];

const eventTypes: EventType[] = [
  'earnings',
  'guidance',
  'mna',
  'buyback',
  'rate_decision',
  'macro_release',
  'regulation',
  'risk',
];

const sourceTypes: EventSourceType[] = [
  'news',
  'filing',
  'earnings',
  'research',
  'macro_data',
];

const markets: Market[] = ['US', 'HK', 'FX', 'RATES', 'METALS'];

const sectors: Sector[] = ['Tech', 'Industrials'];

const tickers = ['AAPL', 'MSFT', 'NVDA', '0700.HK', '9988.HK', 'TSLA', 'AMZN', 'META'];

const instruments = ['NASDAQ', 'SPX', 'DXY', 'US10Y', 'XAUUSD', 'USDJPY'];

const assetCatalog = [
  { id: 'DXY', name: 'US Dollar Index', base: 104.2 },
  { id: 'XAUUSD', name: 'Gold Spot', base: 2352 },
  { id: 'US10Y', name: 'US 10Y Yield', base: 4.12 },
  { id: 'NASDAQ', name: 'Nasdaq 100', base: 18240 },
  { id: 'AAPL', name: 'Apple Inc.', base: 196.3 },
  { id: '0700.HK', name: 'Tencent Holdings', base: 328.4 },
];

const assetMarketMap: Record<string, Market> = {
  DXY: 'FX',
  XAUUSD: 'METALS',
  US10Y: 'RATES',
  NASDAQ: 'US',
  AAPL: 'US',
  '0700.HK': 'HK',
};

const numberTemplates: Array<Omit<EventNumber, 'value'> & { valueRange: [number, number] }> = [
  { name: 'EPS', unit: 'USD', period: 'Q', valueRange: [1.2, 2.4], yoy: 0.12 },
  { name: 'Revenue', unit: 'B USD', period: 'Q', valueRange: [12, 38], yoy: 0.08 },
  { name: 'CPI', unit: '%', period: 'M', valueRange: [2.4, 3.6], yoy: 0.3 },
  { name: 'Payrolls', unit: 'K', period: 'M', valueRange: [120, 260], yoy: 0.05 },
  { name: 'PMI', unit: 'pts', period: 'M', valueRange: [47, 54], yoy: -0.02 },
];

const impactChains = [
  'Policy tone shifts rate path expectations',
  'Rates repricing tightens financial conditions',
  'Equity multiples compress across cyclicals',
  'FX volatility spikes in high-beta pairs',
  'Commodities demand recalibrates on growth fears',
  'Credit spreads widen on risk repricing',
];

const evidenceTitles = [
  'Morning Briefing Note',
  'Macro Snapshot',
  'Earnings Call Highlights',
  'Regulatory Update Memo',
  'Rates Strategy Recap',
];

const hotTags = ['AI capex', 'rate cut odds', 'USD strength', 'China demand', 'carry unwind', 'buyback cadence'];

const seeded = (seed: number) => {
  const value = Math.sin(seed + 1) * 10000;
  return value - Math.floor(value);
};

const pick = <T,>(items: T[], seed: number) => items[Math.floor(seeded(seed) * items.length)];

const pickMany = <T,>(items: T[], seed: number, min = 1, max = 3) => {
  const count = Math.max(min, Math.floor(seeded(seed + 1) * (max - min + 1)) + min);
  const selected: T[] = [];
  for (let i = 0; i < count; i += 1) {
    selected.push(items[Math.floor(seeded(seed + i + 2) * items.length)]);
  }
  return Array.from(new Set(selected));
};

const formatIso = (date: Date) => date.toISOString();

const makeNumbers = (seed: number): EventNumber[] => {
  const entries = pickMany(numberTemplates, seed, 1, 2);
  return entries.map((entry, index) => {
    const range = entry.valueRange;
    const value = range[0] + seeded(seed + index + 4) * (range[1] - range[0]);
    return {
      name: entry.name,
      value: Number(value.toFixed(2)),
      unit: entry.unit,
      period: entry.period,
      yoy: entry.yoy,
      qoq: entry.qoq,
      source_quote_id: `Q${seed}-${index}`,
    };
  });
};

const makeEvidence = (seed: number) => {
  const count = Math.max(1, Math.floor(seeded(seed + 9) * 2) + 1);
  const items = [] as Event['evidence'];
  for (let i = 0; i < count; i += 1) {
    items.push({
      quote_id: `E-${seed}-${i}`,
      source_url: `https://example.com/source/${seed}/${i}`,
      title: pick(evidenceTitles, seed + i + 3),
      published_at: new Date(Date.now() - seed * 36e5).toISOString(),
      excerpt:
        'Key takeaway: the data and guidance reinforce near-term expectations, keeping volatility elevated.',
    });
  }
  return items;
};

const makeHeadline = (seed: number) => {
  const template = pick(headlineTemplates, seed);
  return template
    .replace('{market}', pick(markets, seed + 2))
    .replace('{ticker}', pick(tickers, seed + 3))
    .replace('{direction}', seeded(seed + 4) > 0.5 ? '上修' : '下修')
    .replace('{sector}', pick(sectors, seed + 5))
    .replace('{macro}', pick(macroTags, seed + 6))
    .replace('{stance}', seeded(seed + 7) > 0.6 ? '偏鹰' : '偏鸽');
};

export const EVENTS: Event[] = Array.from({ length: 80 }).map((_, index) => {
  const baseTime = Date.now() - index * 6 * 60 * 60 * 1000;
  const eventType = pick(eventTypes, index + 1);
  const sourceType = pick(sourceTypes, index + 3);
  const marketList = pickMany(markets, index + 5, 1, 3);
  const tickerList = pickMany(tickers, index + 7, 1, 2);
  const instrumentList = pickMany(instruments, index + 9, 1, 2);
  const impact = Math.round(35 + seeded(index + 11) * 60);
  const confidence = Number((0.45 + seeded(index + 13) * 0.5).toFixed(2));

  return {
    event_id: randomUUID(),
    event_time: formatIso(new Date(baseTime)),
    ingest_time: formatIso(new Date(baseTime + 20 * 60 * 1000)),
    source_type: sourceType,
    publisher: pick(publishers, index + 12),
    headline: makeHeadline(index + 10),
    summary: pick(summaryTemplates, index + 14),
    event_type: eventType,
    markets: marketList,
    tickers: tickerList,
    instruments: instrumentList,
    sectors: pickMany(sectors, index + 15, 1, 2),
    numbers: makeNumbers(index + 16),
    stance: seeded(index + 17) > 0.64 ? 'positive' : seeded(index + 18) > 0.5 ? 'neutral' : 'negative',
    impact,
    confidence,
    impact_chain: pickMany(impactChains, index + 19, 3, 5),
    evidence: makeEvidence(index + 20),
    related_event_ids: seeded(index + 21) > 0.7 ? [] : undefined,
  };
});

export const ASSET_CATALOG = assetCatalog;
export const ASSET_MARKET_MAP = assetMarketMap;
export const DASHBOARD_TAGS = hotTags;
