'use client';

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import type { DashboardSummary } from '@market/shared';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

const formatPct = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

export default function DashboardPage() {
  const date = new Date().toISOString().slice(0, 10);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', date],
    queryFn: () => apiGet<DashboardSummary>('/dashboard/summary', { date }),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-1/2" />
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Dashboard Unavailable</CardTitle>
          <CardDescription>Please check the API status or try again.</CardDescription>
        </CardHeader>
        <CardContent>
          <button
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white"
            onClick={() => refetch()}
          >
            Retry
          </button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <section className="fade-up space-y-3">
        <p className="text-sm font-medium text-slate-500">{data.date}</p>
        <h1 className="text-3xl font-semibold text-slate-900">Market Intelligence Overview</h1>
        <p className="max-w-2xl text-sm text-slate-600">
          Follow macro, industry, and company catalysts across key markets with a unified signal stack.
        </p>
      </section>

      <section className="fade-up grid gap-4 md:grid-cols-4">
        {Object.entries(data.kpis).map(([key, value]) => (
          <Card key={key} className="border-slate-100">
            <CardHeader>
              <CardDescription className="uppercase">{key}</CardDescription>
              <CardTitle className="text-2xl">{value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </section>

      <section className="fade-up grid gap-4 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Key Asset Pulse</CardTitle>
            <CardDescription>Frontier moves across FX, rates, metals, and equities.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              {data.key_assets.map((asset) => (
                <div key={asset.id} className="rounded-lg border border-slate-100 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{asset.name}</p>
                      <p className="text-xs text-slate-500">{asset.id}</p>
                    </div>
                    <Badge variant={asset.changePct >= 0 ? 'default' : 'secondary'}>
                      {formatPct(asset.changePct)}
                    </Badge>
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-slate-900">{asset.value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Hot Tags</CardTitle>
            <CardDescription>Trending narratives from the event stream.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {data.hot_tags.map((tag) => (
              <Badge key={tag} variant="outline">
                {tag}
              </Badge>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="fade-up space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Catalyst Timeline</h2>
          <p className="text-sm text-slate-500">Latest signals grouped by transmission lane.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {data.timeline.map((lane) => (
            <Card key={lane.lane}>
              <CardHeader>
                <CardTitle className="text-base uppercase">{lane.lane.replace('_', ' ')}</CardTitle>
                <CardDescription>{lane.events.length} active events</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {lane.events.length === 0 ? (
                  <p className="text-sm text-slate-500">No events in this lane.</p>
                ) : (
                  lane.events.map((event) => (
                    <div key={event.event_id} className="space-y-1 rounded-md border border-slate-100 p-3">
                      <p className="text-sm font-semibold text-slate-900">{event.headline}</p>
                      <p className="text-xs text-slate-500">{event.publisher}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
