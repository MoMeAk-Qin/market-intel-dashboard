'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

type ResearchResponse = {
  ticker: string;
  earnings_card: {
    headline: string;
    eps: { value: number; yoy: number };
    revenue: { value: number; yoy: number };
    guidance: string;
    sentiment: string;
  };
  reports: Array<{ title: string; publisher: string; date: string; summary: string; rating: string }>;
  fact_check: Array<{ statement: string; verdict: string; evidence: string }>;
};

export default function ResearchPage() {
  const [input, setInput] = useState('AAPL');
  const [ticker, setTicker] = useState('AAPL');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['research', ticker],
    queryFn: () => apiGet<ResearchResponse>(`/research/company/${ticker}`),
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Research Workspace</h1>
        <p className="text-sm text-slate-600">
          Track company fundamentals, analyst views, and fact checks in one consolidated view.
        </p>
        <Badge variant="warning">
          演示数据（非实时）
        </Badge>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Company Focus</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 md:flex-row md:items-center"
            onSubmit={(event) => {
              event.preventDefault();
              const next = input.trim().toUpperCase();
              if (next) setTicker(next);
            }}
          >
            <Input value={input} onChange={(event) => setInput(event.target.value)} />
            <Button type="submit">Load</Button>
          </form>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Earnings Card</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24" />
          ) : isError || !data ? (
            <div className="space-y-2">
              <p className="text-sm text-slate-500">Unable to load research data.</p>
              <Button variant="outline" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-lg font-semibold text-slate-900">{data.earnings_card.headline}</p>
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-md border border-slate-100 p-3">
                  <p className="text-xs text-slate-500">EPS</p>
                  <p className="text-base font-semibold">{data.earnings_card.eps.value}</p>
                  <p className="text-xs text-slate-500">YoY {data.earnings_card.eps.yoy}</p>
                </div>
                <div className="rounded-md border border-slate-100 p-3">
                  <p className="text-xs text-slate-500">Revenue</p>
                  <p className="text-base font-semibold">{data.earnings_card.revenue.value}B</p>
                  <p className="text-xs text-slate-500">YoY {data.earnings_card.revenue.yoy}</p>
                </div>
                <div className="rounded-md border border-slate-100 p-3">
                  <p className="text-xs text-slate-500">Sentiment</p>
                  <p className="text-base font-semibold">{data.earnings_card.sentiment}</p>
                  <p className="text-xs text-slate-500">{data.earnings_card.guidance}</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">Latest Reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <Skeleton className="h-24" />
            ) : data ? (
              data.reports.map((report) => (
                <div key={report.title} className="rounded-md border border-slate-100 p-3">
                  <p className="text-sm font-semibold text-slate-900">{report.title}</p>
                  <p className="text-xs text-slate-500">
                    {report.publisher} · {report.date}
                  </p>
                  <p className="text-xs text-slate-600">{report.summary}</p>
                  <p className="text-xs text-slate-500">Rating: {report.rating}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No reports available.</p>
            )}
          </CardContent>
        </Card>

        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">Fact Check</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading ? (
              <Skeleton className="h-24" />
            ) : data ? (
              data.fact_check.map((item) => (
                <div key={item.statement} className="rounded-md border border-slate-100 p-3">
                  <p className="text-sm font-semibold text-slate-900">{item.statement}</p>
                  <p className="text-xs text-slate-500">Verdict: {item.verdict}</p>
                  <p className="text-xs text-slate-600">{item.evidence}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No fact checks available.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
