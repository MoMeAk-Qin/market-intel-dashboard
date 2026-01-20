'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import type { AssetSeriesPoint, Event } from '@market/shared';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

const ranges = ['1D', '1W', '1M', '1Y'] as const;

type Range = (typeof ranges)[number];

export default function AssetDetailPage() {
  const params = useParams<{ id: string }>();
  const assetId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [range, setRange] = useState<Range>('1M');

  const { data: chartData, isLoading: chartLoading, isError: chartError } = useQuery({
    queryKey: ['assetChart', assetId, range],
    queryFn: () =>
      apiGet<{ assetId: string; range: string; series: AssetSeriesPoint[] }>(
        `/assets/${assetId}/chart`,
        { range },
      ),
  });

  const { data: eventsData, isLoading: eventsLoading, isError: eventsError } = useQuery({
    queryKey: ['assetEvents', assetId, range],
    queryFn: () => apiGet<{ assetId: string; items: Event[] }>(`/assets/${assetId}/events`, { range }),
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <Badge variant="secondary">Asset Detail</Badge>
        <h1 className="text-3xl font-semibold">{assetId}</h1>
        <p className="text-sm text-slate-600">Track price action and recent catalysts in one view.</p>
      </div>

      <Card className="fade-up">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-base">Price Trajectory</CardTitle>
          </div>
          <div className="flex gap-2">
            {ranges.map((item) => (
              <Button
                key={item}
                variant={item === range ? 'default' : 'outline'}
                size="sm"
                onClick={() => setRange(item)}
              >
                {item}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="h-72">
          {chartLoading ? (
            <Skeleton className="h-full" />
          ) : chartError || !chartData ? (
            <p className="text-sm text-slate-500">Unable to load chart.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData.series} margin={{ left: 12, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#0f172a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Related Events</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {eventsLoading ? (
            Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-16" />)
          ) : eventsError || !eventsData ? (
            <p className="text-sm text-slate-500">Unable to load events.</p>
          ) : eventsData.items.length === 0 ? (
            <p className="text-sm text-slate-500">No recent events for this asset.</p>
          ) : (
            eventsData.items.map((event) => (
              <div key={event.event_id} className="rounded-md border border-slate-100 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{event.event_type}</Badge>
                  <Badge variant={event.stance === 'positive' ? 'default' : 'secondary'}>
                    {event.stance}
                  </Badge>
                </div>
                <p className="mt-2 text-sm font-semibold text-slate-900">{event.headline}</p>
                <p className="text-xs text-slate-500">{event.publisher}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
