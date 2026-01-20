import Fastify from 'fastify';
import cors from '@fastify/cors';
import type { AssetSeriesPoint, DashboardSummary, Event, QAResponse } from '@market/shared';
import { ASSET_CATALOG, ASSET_MARKET_MAP, DASHBOARD_TAGS, EVENTS } from './mock/data';

const server = Fastify({ logger: false });

const PORT = Number(process.env.PORT ?? 4000);
const CORS_ORIGIN = process.env.CORS_ORIGIN ?? '*';

await server.register(cors, { origin: CORS_ORIGIN });

server.get('/health', async () => ({ ok: true }));

server.get('/dashboard/summary', async (request) => {
  const { date } = request.query as { date?: string };
  const targetDate = date ?? new Date().toISOString().slice(0, 10);
  return buildDashboardSummary(targetDate);
});

server.get('/events', async (request) => {
  const {
    from,
    to,
    market,
    sector,
    type,
    stance,
    minImpact,
    minConfidence,
    q,
    page,
    pageSize,
  } = request.query as Record<string, string | undefined>;

  const filtered = filterEvents({
    from,
    to,
    market,
    sector,
    type,
    stance,
    minImpact,
    minConfidence,
    q,
  });

  const currentPage = Math.max(1, Number(page ?? 1));
  const size = Math.max(5, Math.min(50, Number(pageSize ?? 20)));
  const start = (currentPage - 1) * size;
  const items = filtered.slice(start, start + size);

  return {
    items,
    page: currentPage,
    pageSize: size,
    total: filtered.length,
  };
});

server.get('/events/:id', async (request, reply) => {
  const { id } = request.params as { id: string };
  const event = EVENTS.find((item) => item.event_id === id);
  if (!event) {
    reply.code(404);
    return { message: 'Event not found' };
  }
  return event;
});

server.get('/assets/:assetId/chart', async (request, reply) => {
  const { assetId } = request.params as { assetId: string };
  const { range } = request.query as { range?: string };
  const selectedRange = normalizeRange(range);

  const asset = ASSET_CATALOG.find((item) => item.id === assetId);
  if (!asset) {
    reply.code(404);
    return { message: 'Asset not found' };
  }

  return {
    assetId,
    range: selectedRange,
    series: buildAssetSeries(asset.base, selectedRange),
  };
});

server.get('/assets/:assetId/events', async (request, reply) => {
  const { assetId } = request.params as { assetId: string };
  const { range } = request.query as { range?: string };
  const selectedRange = normalizeRange(range);
  const market = ASSET_MARKET_MAP[assetId];

  if (!market) {
    reply.code(404);
    return { message: 'Asset not found' };
  }

  const days = rangeToDays(selectedRange);
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  const items = EVENTS.filter((event) => {
    const time = new Date(event.event_time).getTime();
    return time >= cutoff && event.markets.includes(market);
  }).slice(0, 12);

  return { assetId, items };
});

server.get('/research/company/:ticker', async (request) => {
  const { ticker } = request.params as { ticker: string };
  const normalized = ticker.toUpperCase();
  return {
    ticker: normalized,
    earnings_card: {
      headline: `${normalized} maintains steady demand with margin discipline`,
      eps: { value: 2.18, yoy: 0.12 },
      revenue: { value: 32.4, yoy: 0.08 },
      guidance: 'FY outlook held, with upside skew into 2H.',
      sentiment: 'Stable with a constructive tilt',
    },
    reports: [
      {
        title: `${normalized} tactical update`,
        publisher: 'Crown Research',
        date: new Date().toISOString().slice(0, 10),
        summary: 'Channel momentum remains steady, with valuation slightly below the historical midpoint.',
        rating: 'Overweight',
      },
      {
        title: `${normalized} supply chain check`,
        publisher: 'Atlas Insight',
        date: new Date(Date.now() - 86400000).toISOString().slice(0, 10),
        summary: 'Order visibility improves, while cost pressure remains a key watch item.',
        rating: 'Neutral',
      },
    ],
    fact_check: [
      {
        statement: 'Overseas demand is recovering and supports pricing power.',
        verdict: 'Partially supported',
        evidence: 'Recent channel data shows modest improvement, though trends vary by region.',
      },
    ],
  };
});

server.post('/qa', async (request) => {
  const body = request.body as { question?: string };
  const question = body?.question?.toLowerCase() ?? '';

  let picked = EVENTS.find((event) => event.event_type === 'rate_decision');
  let answer =
    'Policy pacing still hinges on inflation and growth, with near-term focus on the next policy update.';

  if (question.includes('gold') || question.includes('xau')) {
    picked = EVENTS.find((event) => event.markets.includes('METALS')) ?? picked;
    answer =
      'Precious metals remain driven by real yields and risk hedging demand, with near-term moves tied to policy expectations.';
  } else if (question.includes('earnings') || question.includes('aapl')) {
    picked = EVENTS.find((event) => event.event_type === 'earnings') ?? picked;
    answer =
      'Earnings momentum is still led by product and services mix, with market focus on margin durability.';
  } else if (question.includes('fx') || question.includes('dxy')) {
    picked = EVENTS.find((event) => event.markets.includes('FX')) ?? picked;
    answer =
      'The dollar index is tugged by policy divergence and risk demand, with the short-term path leaning on macro confirmation.';
  } else if (question.includes('risk') || question.includes('regulation')) {
    picked = EVENTS.find((event) => event.event_type === 'risk') ?? picked;
    answer =
      'Policy and regulatory events meaningfully affect risk appetite; track how quickly the impact chain spreads.';
  }

  const evidence = picked?.evidence ?? EVENTS[0].evidence;
  const payload: QAResponse = { answer, evidence };
  return payload;
});

const buildDashboardSummary = (date: string): DashboardSummary => {
  const major = EVENTS.filter((event) => event.impact >= 80).length;
  const macro = EVENTS.filter((event) =>
    ['macro_release', 'rate_decision'].includes(event.event_type),
  ).length;
  const company = EVENTS.filter((event) =>
    ['earnings', 'guidance', 'buyback', 'mna'].includes(event.event_type),
  ).length;
  const risk = EVENTS.filter((event) => event.event_type === 'risk' || event.stance === 'negative')
    .length;

  const key_assets = ASSET_CATALOG.map((asset, index) => {
    const swing = (Math.sin(index + 1) * 0.8 + 0.2) * 0.6;
    const changePct = Number((swing * 2 - 0.6).toFixed(2));
    return {
      id: asset.id,
      name: asset.name,
      value: Number((asset.base * (1 + changePct / 100)).toFixed(2)),
      changePct,
    };
  });

  const laneOrder = ['macro', 'industry', 'company', 'policy_risk'] as const;
  const laneEvents = laneOrder.map((lane) => ({
    lane,
    events: EVENTS.filter((event) => mapLane(event) === lane).slice(0, 5),
  }));

  return {
    date,
    kpis: { major, macro, company, risk },
    key_assets,
    timeline: laneEvents,
    hot_tags: DASHBOARD_TAGS,
  };
};

const mapLane = (event: Event) => {
  if (event.event_type === 'macro_release' || event.event_type === 'rate_decision') {
    return 'macro' as const;
  }
  if (event.event_type === 'regulation' || event.event_type === 'risk') {
    return 'policy_risk' as const;
  }
  if (['earnings', 'guidance', 'buyback', 'mna'].includes(event.event_type)) {
    return 'company' as const;
  }
  return 'industry' as const;
};

const filterEvents = (query: {
  from?: string;
  to?: string;
  market?: string;
  sector?: string;
  type?: string;
  stance?: string;
  minImpact?: string;
  minConfidence?: string;
  q?: string;
}) => {
  const fromTime = query.from ? new Date(query.from).getTime() : undefined;
  const toTime = query.to ? new Date(query.to).getTime() : undefined;
  const minImpact = query.minImpact ? Number(query.minImpact) : undefined;
  const minConfidence = query.minConfidence ? Number(query.minConfidence) : undefined;
  const keyword = query.q?.toLowerCase().trim();

  return EVENTS.filter((event) => {
    const time = new Date(event.event_time).getTime();
    if (fromTime && time < fromTime) return false;
    if (toTime && time > toTime) return false;
    if (query.market && !event.markets.includes(query.market as Event['markets'][number])) {
      return false;
    }
    if (query.sector && !event.sectors.includes(query.sector as Event['sectors'][number])) {
      return false;
    }
    if (query.type && event.event_type !== query.type) return false;
    if (query.stance && event.stance !== query.stance) return false;
    if (minImpact && event.impact < minImpact) return false;
    if (minConfidence && event.confidence < minConfidence) return false;
    if (keyword) {
      const haystack = [
        event.headline,
        event.summary,
        event.publisher,
        event.tickers.join(' '),
        event.instruments.join(' '),
      ]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(keyword)) return false;
    }
    return true;
  }).sort((a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime());
};

const normalizeRange = (range?: string) => {
  if (range === '1D' || range === '1W' || range === '1M' || range === '1Y') {
    return range;
  }
  return '1M';
};

const rangeToDays = (range: string) => {
  if (range === '1D') return 1;
  if (range === '1W') return 7;
  if (range === '1M') return 30;
  return 365;
};

const buildAssetSeries = (base: number, range: string): AssetSeriesPoint[] => {
  const points = range === '1D' ? 24 : range === '1W' ? 7 : range === '1M' ? 30 : 12;
  const step = range === '1Y' ? 30 : 1;
  return Array.from({ length: points }).map((_, index) => {
    const shift = Math.sin(index / 2) * 0.6 + Math.cos(index / 3) * 0.4;
    const value = base * (1 + shift * 0.002 + index * 0.0008);
    const date = new Date(Date.now() - (points - index - 1) * step * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    return { date, value: Number(value.toFixed(2)) };
  });
};

const start = async () => {
  try {
    await server.listen({ port: PORT, host: '0.0.0.0' });
    console.log(`API running at http://localhost:${PORT}`);
  } catch (error) {
    console.error(error);
    process.exit(1);
  }
};

start();
