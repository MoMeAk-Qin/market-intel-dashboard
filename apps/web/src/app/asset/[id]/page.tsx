'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import type { AssetMetric, AssetProfile } from '@market/shared';
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

const priceFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

const pctFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
  signDisplay: 'always',
});

const formatPrice = (value: number): string =>
  Math.abs(value) >= 1000 ? priceFormatter.format(value) : value.toFixed(2);

const formatMetricValue = (metric: AssetMetric): string => {
  if (metric.unit === 'pct') {
    if (metric.metric_id === 'spot_price') {
      return `${formatPrice(metric.value)} %`;
    }
    return `${pctFormatter.format(metric.value)} %`;
  }
  if (metric.unit === 'bps') {
    return `${pctFormatter.format(metric.value)} ${metric.unit}`;
  }
  if (metric.unit === 'index') {
    return `${formatPrice(metric.value)} idx`;
  }
  return `${formatPrice(metric.value)} ${metric.unit}`;
};

const formatSeriesLabel = (time: string, range: Range): string => {
  const parsed = new Date(time);
  if (Number.isNaN(parsed.getTime())) return time;
  if (range === '1D') {
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(parsed);
  }
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  }).format(parsed);
};

export default function AssetDetailPage() {
  const params = useParams<{ id: string }>();
  const assetId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [range, setRange] = useState<Range>('1M');

  const { data: profileData, isLoading: profileLoading, isError: profileError } = useQuery({
    queryKey: ['assetProfile', assetId, range],
    queryFn: () => apiGet<AssetProfile>(`/assets/${assetId}/profile`, { range }),
  });

  const chartPoints =
    profileData?.series.points.map((point) => ({
      label: formatSeriesLabel(point.time, range),
      value: point.value,
    })) ?? [];

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">Asset Detail</Badge>
          {profileData ? (
            <Badge variant={profileData.quote.is_fallback ? 'warning' : 'success'}>
              {profileData.quote.is_fallback ? '回退行情' : '实时行情'}
            </Badge>
          ) : null}
        </div>
        <h1 className="text-3xl font-semibold">{assetId}</h1>
        <p className="text-sm text-muted-foreground">Track price action and recent catalysts in one view.</p>
        {profileLoading ? (
          <Skeleton className="mt-2 h-6 w-56" />
        ) : profileError || !profileData ? (
          <p className="mt-2 text-sm text-muted-foreground">Unable to load quote snapshot.</p>
        ) : (
          <div className="mt-2 space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-2xl font-semibold text-foreground">{formatPrice(profileData.quote.price)}</p>
              <p
                className={
                  profileData.quote.change_pct && profileData.quote.change_pct < 0
                    ? 'text-sm text-rose-600'
                    : 'text-sm text-emerald-600'
                }
              >
                {pctFormatter.format(profileData.quote.change_pct ?? 0)}%
              </p>
              <p className="text-xs text-muted-foreground">{formatApiDateTime(profileData.quote.as_of)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {profileData.metrics.map((item) => (
                <Badge key={item.metric_id} variant="secondary">
                  {item.label}: {formatMetricValue(item)}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      <Card className="fade-up">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <CardTitle className="text-base">Price Trajectory</CardTitle>
            {profileData ? (
              <Badge variant={profileData.series.is_fallback ? 'warning' : 'success'}>
                {profileData.series.is_fallback ? '回退序列' : '实时序列'}
              </Badge>
            ) : null}
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
          {profileLoading ? (
            <Skeleton className="h-full" />
          ) : profileError || !profileData ? (
            <p className="text-sm text-muted-foreground">Unable to load chart.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartPoints} margin={{ left: 12, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis
                  tick={{ fontSize: 12 }}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(value) => formatPrice(Number(value))}
                />
                <Tooltip
                  formatter={(value) => formatPrice(Number(value))}
                  labelFormatter={(label) => String(label)}
                  contentStyle={{
                    borderColor: 'hsl(var(--border))',
                    borderRadius: '0.5rem',
                    background: 'hsl(var(--popover))',
                    color: 'hsl(var(--popover-foreground))',
                  }}
                />
                <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
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
          {profileLoading ? (
            Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-16" />)
          ) : profileError || !profileData ? (
            <p className="text-sm text-muted-foreground">Unable to load events.</p>
          ) : profileData.recent_events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent events for this asset.</p>
          ) : (
            profileData.recent_events.map((event) => (
              <div key={event.event_id} className="rounded-md border border-border bg-background/20 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{event.event_type}</Badge>
                  <Badge variant={event.stance === 'positive' ? 'default' : 'secondary'}>
                    {event.stance}
                  </Badge>
                </div>
                <p className="mt-2 text-sm font-semibold text-foreground">{event.headline}</p>
                <p className="text-xs text-muted-foreground">{event.publisher}</p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
