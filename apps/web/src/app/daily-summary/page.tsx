'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useMutation } from '@tanstack/react-query';
import { getDailySummary } from '@/lib/api';
import type { DailySummaryRequest } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

const splitCsv = (value: string): string[] =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

export default function DailySummaryPage() {
  const [focus, setFocus] = useState('请按重点、影响、风险与关注点输出今日摘要。');
  const [markets, setMarkets] = useState('');
  const [tickers, setTickers] = useState('');
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState('20');

  const payload = useMemo<DailySummaryRequest>(
    () => ({
      focus: focus.trim() || undefined,
      markets: splitCsv(markets),
      tickers: splitCsv(tickers),
      query: query.trim() || undefined,
      limit: Number(limit),
      use_retrieval: true,
      top_k: 6,
    }),
    [focus, limit, markets, query, tickers],
  );

  const { mutate, data, isPending, isError, reset } = useMutation({
    mutationFn: (input: DailySummaryRequest) => getDailySummary(input),
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">日报摘要</h1>
        <p className="text-sm text-slate-600">基于今日新闻生成结构化摘要，并展示证据来源。</p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">摘要参数</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              mutate(payload);
            }}
          >
            <div className="md:col-span-2">
              <p className="mb-1 text-xs text-slate-500">摘要焦点</p>
              <Input value={focus} onChange={(event) => setFocus(event.target.value)} />
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">市场（逗号分隔）</p>
              <Input placeholder="US,HK" value={markets} onChange={(event) => setMarkets(event.target.value)} />
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">标的（逗号分隔）</p>
              <Input
                placeholder="AAPL,0700.HK"
                value={tickers}
                onChange={(event) => setTickers(event.target.value)}
              />
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">关键词</p>
              <Input placeholder="rate, inflation" value={query} onChange={(event) => setQuery(event.target.value)} />
            </div>
            <div>
              <p className="mb-1 text-xs text-slate-500">新闻上限</p>
              <Input type="number" min="1" max="50" value={limit} onChange={(event) => setLimit(event.target.value)} />
            </div>
            <div className="md:col-span-2 flex flex-wrap gap-3">
              <Button type="submit" disabled={isPending}>
                生成摘要
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  reset();
                  setFocus('请按重点、影响、风险与关注点输出今日摘要。');
                  setMarkets('');
                  setTickers('');
                  setQuery('');
                  setLimit('20');
                }}
              >
                重置
              </Button>
              <Link href="/news" className="inline-flex">
                <Button type="button" variant="ghost">
                  先看今日新闻
                </Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">摘要结果</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPending ? (
            <>
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
            </>
          ) : isError ? (
            <p className="text-sm text-slate-600">生成失败，请检查后端配置并重试。</p>
          ) : data ? (
            <>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <Badge variant="secondary">日期 {data.date}</Badge>
                <Badge variant="secondary">新闻数 {data.total_news}</Badge>
                <Badge variant="secondary">模型 {data.model}</Badge>
              </div>
              <div className="rounded-md border border-slate-100 p-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{data.answer}</p>
              </div>
              <div>
                <p className="mb-2 text-xs uppercase text-slate-500">证据</p>
                <div className="space-y-3">
                  {data.sources.map((source) => (
                    <article key={source.quote_id} className="rounded-md border border-slate-100 p-3">
                      <p className="text-sm font-semibold text-slate-900">{source.title}</p>
                      <a
                        className="text-xs text-blue-600 underline"
                        href={source.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.source_url}
                      </a>
                      <p className="mt-1 text-xs text-slate-600">{source.excerpt}</p>
                    </article>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-600">提交参数后生成日报摘要。</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
