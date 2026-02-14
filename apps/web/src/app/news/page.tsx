'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getNewsToday } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';

const markets = ['all', 'US', 'HK', 'FX', 'RATES', 'METALS'];
const sortOptions = ['time', 'impact'] as const;

export default function NewsPage() {
  const [market, setMarket] = useState('all');
  const [tickers, setTickers] = useState('');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<(typeof sortOptions)[number]>('time');
  const [limit, setLimit] = useState('30');

  const requestParams = useMemo(
    () => ({
      market: market === 'all' ? undefined : market,
      tickers: tickers.trim() || undefined,
      q: query.trim() || undefined,
      sort,
      limit: Number(limit),
    }),
    [limit, market, query, sort, tickers],
  );

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['news-today', requestParams],
    queryFn: () => getNewsToday(requestParams),
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">今日新闻</h1>
        <p className="text-sm text-slate-600">按市场、标的与关键词过滤当日新闻，支持按时间或影响排序。</p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">过滤条件</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-5">
          <div>
            <p className="mb-1 text-xs text-slate-500">市场</p>
            <Select value={market} onValueChange={setMarket}>
              <SelectTrigger>
                <SelectValue placeholder="市场" />
              </SelectTrigger>
              <SelectContent>
                {markets.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item === 'all' ? '全部' : item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
            <Input
              placeholder="inflation, gold"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div>
            <p className="mb-1 text-xs text-slate-500">排序</p>
            <Select value={sort} onValueChange={(value) => setSort(value as (typeof sortOptions)[number])}>
              <SelectTrigger>
                <SelectValue placeholder="排序" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="time">时间</SelectItem>
                <SelectItem value="impact">影响</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <p className="mb-1 text-xs text-slate-500">条数上限</p>
            <Select value={limit} onValueChange={setLimit}>
              <SelectTrigger>
                <SelectValue placeholder="条数" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="30">30</SelectItem>
                <SelectItem value="40">40</SelectItem>
                <SelectItem value="50">50</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <CardTitle className="text-base">新闻列表</CardTitle>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>日期：{data?.date ?? '--'}</span>
            <span>总数：{data?.total ?? 0}</span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-28" />)
          ) : isError || !data ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">加载新闻失败，请重试。</p>
              <Button onClick={() => refetch()}>重试</Button>
            </div>
          ) : data.items.length === 0 ? (
            <p className="text-sm text-slate-600">暂无符合条件的新闻。</p>
          ) : (
            data.items.map((item) => (
              <article key={item.event_id} className="rounded-md border border-slate-100 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{item.event_type}</Badge>
                  <Badge variant={item.stance === 'positive' ? 'default' : 'secondary'}>{item.stance}</Badge>
                  {item.data_origin === 'seed' ? (
                    <Badge variant="warning">Seed（模拟数据）</Badge>
                  ) : (
                    <Badge variant="success">Live</Badge>
                  )}
                </div>
                <h2 className="mt-2 text-base font-semibold text-slate-900">{item.headline}</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {item.publisher} · {formatApiDateTime(item.event_time)}
                </p>
                <p className="mt-2 text-sm text-slate-700">{item.summary}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {item.markets.map((tag) => (
                    <Badge key={`${item.event_id}-${tag}`} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                  {item.tickers.map((ticker) => (
                    <Badge key={`${item.event_id}-${ticker}`} variant="outline">
                      {ticker}
                    </Badge>
                  ))}
                </div>
              </article>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
