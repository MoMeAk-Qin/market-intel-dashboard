'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import { getNewsToday } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';

const markets = ['all', 'US', 'HK', 'FX', 'RATES', 'METALS'] as const;
const sortOptions = ['time', 'impact'] as const;

const tickerTokenRegex = /^[A-Za-z0-9.-]+$/;

const newsFilterSchema = z.object({
  market: z.enum(markets).default('all'),
  tickers: z
    .string()
    .default('')
    .refine((value) => {
      if (!value.trim()) {
        return true;
      }
      return value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
        .every((token) => tickerTokenRegex.test(token));
    }, '标的格式无效，请使用逗号分隔，如 AAPL,0700.HK'),
  q: z.string().default(''),
  sort: z.enum(sortOptions).default('time'),
  limit: z
    .string()
    .default('30')
    .refine((value) => {
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 1 && parsed <= 50;
    }, '条数上限必须是 1 到 50 的整数'),
});

type NewsFilterValues = z.input<typeof newsFilterSchema>;

const defaultNewsFilters: NewsFilterValues = {
  market: 'all',
  tickers: '',
  q: '',
  sort: 'time',
  limit: '30',
};

export default function NewsPage() {
  const [submittedFilters, setSubmittedFilters] = useState<NewsFilterValues>(defaultNewsFilters);
  const filterForm = useForm<NewsFilterValues>({
    resolver: zodResolver(newsFilterSchema),
    defaultValues: defaultNewsFilters,
  });

  const requestParams = useMemo(
    () => ({
      market:
        submittedFilters.market === 'all'
          ? undefined
          : (submittedFilters.market ?? undefined),
      tickers: submittedFilters.tickers?.trim() || undefined,
      q: submittedFilters.q?.trim() || undefined,
      sort: submittedFilters.sort ?? 'time',
      limit: Number(submittedFilters.limit ?? '30'),
    }),
    [submittedFilters],
  );

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['news-today', requestParams],
    queryFn: () => getNewsToday(requestParams),
  });

  const handleSubmit = filterForm.handleSubmit((values) => {
    setSubmittedFilters(values);
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">今日新闻</h1>
        <p className="text-sm text-muted-foreground">按市场、标的与关键词过滤当日新闻，支持按时间或影响排序。</p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">过滤条件</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...filterForm}>
            <form className="grid gap-4 md:grid-cols-6" onSubmit={handleSubmit}>
              <FormField
                control={filterForm.control}
                name="market"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>市场</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="市场" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {markets.map((item) => (
                          <SelectItem key={item} value={item}>
                            {item === 'all' ? '全部' : item}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="tickers"
                render={({ field }) => (
                  <FormItem className="md:col-span-2">
                    <FormLabel>标的（逗号分隔）</FormLabel>
                    <FormControl>
                      <Input placeholder="AAPL,0700.HK" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="q"
                render={({ field }) => (
                  <FormItem className="md:col-span-2">
                    <FormLabel>关键词</FormLabel>
                    <FormControl>
                      <Input placeholder="inflation, gold" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="sort"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>排序</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="排序" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="time">时间</SelectItem>
                        <SelectItem value="impact">影响</SelectItem>
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="limit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>条数上限</FormLabel>
                    <FormControl>
                      <Input type="number" min="1" max="50" placeholder="1 - 50" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex items-end gap-2 md:col-span-2">
                <Button type="submit">应用过滤</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    filterForm.reset(defaultNewsFilters);
                    setSubmittedFilters(defaultNewsFilters);
                  }}
                >
                  重置
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <CardTitle className="text-base">新闻列表</CardTitle>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>日期：{data?.date ?? '--'}</span>
            <span>总数：{data?.total ?? 0}</span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-28" />)
          ) : isError || !data ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">加载新闻失败，请重试。</p>
              <Button onClick={() => refetch()}>重试</Button>
            </div>
          ) : data.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无符合条件的新闻。</p>
          ) : (
            data.items.map((item) => (
              <article key={item.event_id} className="rounded-md border border-border bg-background/20 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{item.event_type}</Badge>
                  <Badge variant={item.stance === 'positive' ? 'default' : 'secondary'}>{item.stance}</Badge>
                  {item.data_origin === 'seed' ? (
                    <Badge variant="warning">Seed（模拟数据）</Badge>
                  ) : (
                    <Badge variant="success">Live</Badge>
                  )}
                </div>
                <h2 className="mt-2 text-base font-semibold text-foreground">{item.headline}</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.publisher} · {formatApiDateTime(item.event_time)}
                </p>
                <p className="mt-2 text-sm text-foreground/90">{item.summary}</p>
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
