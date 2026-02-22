'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { zodResolver } from '@hookform/resolvers/zod';
import { Info } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import { z } from 'zod';
import { getResearchCompany, getUnlistedCompanies, getUnlistedCompany } from '@/lib/api';
import type { ResearchCompanyResponse, UnlistedCompany, UnlistedCompanyResponse } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const tickerSchema = z.object({
  ticker: z
    .string()
    .trim()
    .min(1, 'Ticker 不能为空')
    .max(12, 'Ticker 不能超过 12 个字符')
    .regex(/^[A-Za-z0-9.-]+$/, '仅支持字母、数字、点与短横线'),
});

type TickerFormValues = z.infer<typeof tickerSchema>;

const quickTickers = [
  'AAPL',
  'MSFT',
  'NVDA',
  'AMZN',
  'GOOGL',
  'META',
  'TSLA',
  '0700.HK',
  '9988.HK',
  'OPENAI',
  'ANTHROPIC',
  'DEEPSEEK',
  'MINIMAX',
];

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

const pctFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
  signDisplay: 'always',
});

const chartConfig = {
  current: {
    label: '当前值',
    color: 'hsl(var(--chart-1))',
  },
  yoy: {
    label: '同比(%)',
    color: 'hsl(var(--chart-2))',
  },
} satisfies ChartConfig;

const formatMetricValue = (value: number): string => numberFormatter.format(value);
const formatPctValue = (value: number | null | undefined): string =>
  value === null || value === undefined ? 'N/A' : `${pctFormatter.format(value)}%`;

const formatDateTime = (value: string): string => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString('zh-CN', { hour12: false });
};

const normalizeCompanyId = (value: string): string => value.trim().toLowerCase().replace(/[^a-z0-9-]/g, '');

const resolveUnlistedCompanyId = (input: string, companies: UnlistedCompany[]): string | null => {
  const normalized = normalizeCompanyId(input);
  if (!normalized) {
    return null;
  }
  const compact = normalized.replace(/-/g, '');
  const aliasMap: Record<string, string> = {
    openai: 'openai',
    anthropic: 'anthropic',
    bytedance: 'bytedance',
    moonshot: 'moonshot-ai',
    moonshotai: 'moonshot-ai',
    kimi: 'moonshot-ai',
    databricks: 'databricks',
    stripe: 'stripe',
    spacex: 'spacex',
    scaleai: 'scale-ai',
    anduril: 'anduril',
    figureai: 'figure-ai',
    '01ai': '01ai',
    lingyi: '01ai',
    baichuan: 'baichuan',
    stepfun: 'stepfun',
    deepseek: 'deepseek',
    minimax: 'minimax',
  };
  const fromAlias = aliasMap[normalized] ?? aliasMap[compact];
  if (fromAlias) {
    return fromAlias;
  }
  const byId = companies.find((item) => normalizeCompanyId(item.company_id) === normalized);
  if (byId) {
    return byId.company_id;
  }
  const byName = companies.find((item) => normalizeCompanyId(item.name) === normalized);
  return byName?.company_id ?? normalized;
};

export default function ResearchPage() {
  const [ticker, setTicker] = useState('AAPL');
  const form = useForm<TickerFormValues>({
    resolver: zodResolver(tickerSchema),
    defaultValues: { ticker: 'AAPL' },
  });

  const tickerInput = form.watch('ticker');

  const { data, isLoading, isError, refetch, error, isFetching } = useQuery<ResearchCompanyResponse>({
    queryKey: ['research', ticker],
    queryFn: () => getResearchCompany(ticker),
  });

  const { data: unlistedCompanies = [] } = useQuery<UnlistedCompany[]>({
    queryKey: ['unlisted', 'companies'],
    queryFn: getUnlistedCompanies,
  });

  const unlistedCompanyId = useMemo(() => {
    if (data?.company_type !== 'unlisted') {
      return null;
    }
    return resolveUnlistedCompanyId(ticker, unlistedCompanies);
  }, [data?.company_type, ticker, unlistedCompanies]);

  const { data: unlistedDetail, isFetching: isUnlistedDetailFetching } = useQuery<UnlistedCompanyResponse>({
    queryKey: ['unlisted', 'companies', unlistedCompanyId],
    queryFn: () => getUnlistedCompany(unlistedCompanyId ?? ''),
    enabled: Boolean(unlistedCompanyId),
  });

  useEffect(() => {
    if (!isError) {
      return;
    }
    const message = error instanceof Error ? error.message : '未知错误';
    toast.error(`Research 数据加载失败：${message}`);
  }, [error, isError]);

  const commandCandidates = useMemo(() => {
    const fromUnlisted = unlistedCompanies.map((item) => item.company_id.toUpperCase());
    return Array.from(new Set([...quickTickers, ...fromUnlisted]));
  }, [unlistedCompanies]);

  const filteredTickers = useMemo(() => {
    const keyword = tickerInput.trim().toUpperCase();
    if (!keyword) {
      return commandCandidates;
    }
    return commandCandidates.filter((item) => item.includes(keyword)).slice(0, 8);
  }, [commandCandidates, tickerInput]);

  const chartData = useMemo(() => {
    if (!data?.earnings_card) {
      return [];
    }
    return [
      {
        metric: 'EPS',
        current: data.earnings_card.eps.value,
        yoy: data.earnings_card.eps.yoy ?? 0,
      },
      {
        metric: 'Revenue',
        current: data.earnings_card.revenue.value,
        yoy: data.earnings_card.revenue.yoy ?? 0,
      },
    ];
  }, [data]);

  const applyTicker = (nextTicker: string) => {
    const normalized = nextTicker.trim().toUpperCase();
    form.setValue('ticker', normalized, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    });
    setTicker(normalized);
  };

  const resetTicker = () => {
    form.reset({ ticker: 'AAPL' });
    setTicker('AAPL');
  };

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Research Workspace</h1>
        <p className="text-sm text-muted-foreground">
          展示实时财报、相关新闻和统一分析结论，支持 fallback 降级并明确来源。
        </p>
        {data ? (
          <div className="flex flex-wrap gap-2">
            <Badge variant={data.source_type === 'live' ? 'success' : 'warning'}>
              source_type: {data.source_type}
            </Badge>
            <Badge variant="outline">company_type: {data.company_type}</Badge>
            <Badge variant="outline">updated_at: {formatDateTime(data.updated_at)}</Badge>
            {data.company_type === 'unlisted' && unlistedDetail ? (
              <Badge variant={unlistedDetail.company.source_type === 'live' ? 'success' : 'outline'}>
                unlisted_source: {unlistedDetail.company.source_type}
              </Badge>
            ) : null}
          </div>
        ) : null}
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Company Focus</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Form {...form}>
            <form
              className="flex flex-col gap-3 md:flex-row md:items-end"
              onSubmit={form.handleSubmit((values) => {
                setTicker(values.ticker.trim().toUpperCase());
              })}
            >
              <FormField
                control={form.control}
                name="ticker"
                render={({ field }) => (
                  <FormItem className="w-full">
                    <FormLabel>Ticker</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="AAPL / NVDA / 0700.HK / OPENAI / MINIMAX"
                        {...field}
                        onChange={(event) => field.onChange(event.target.value.toUpperCase())}
                      />
                    </FormControl>
                    <FormDescription>
                      支持上市 ticker 与未上市公司 ID（如 OPENAI、MINIMAX），提交后自动请求研究接口。
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex gap-2">
                <Button type="submit" disabled={isFetching}>
                  {isFetching ? '加载中...' : 'Load'}
                </Button>
                <Button type="button" variant="outline" onClick={resetTicker}>
                  Reset
                </Button>
              </div>
            </form>
          </Form>

          <Command className="bg-background/20">
            <CommandInput placeholder="快速筛选并回车选择 ticker / 未上市公司..." />
            <CommandList>
              <CommandEmpty>没有匹配的 ticker。</CommandEmpty>
              <CommandGroup heading="Watchlist">
                {filteredTickers.map((item) => (
                  <CommandItem key={item} value={item} onSelect={applyTicker}>
                    {item}
                    <CommandShortcut>↵</CommandShortcut>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </CardContent>
      </Card>

      {isLoading ? (
        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">Research Loading</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      ) : isError || !data ? (
        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">Research 加载失败</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">无法获取研究数据，请确认 API 可用后重试。</p>
            <Button variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue="earnings" className="fade-up space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="earnings">Earnings</TabsTrigger>
            <TabsTrigger value="news">News</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
          </TabsList>

          <TabsContent value="earnings">
            <Card>
              <CardHeader className="flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-base">
                    {data.company_type === 'unlisted'
                      ? `${data.ticker} 未上市公司画像`
                      : data.earnings_card?.headline ?? `${data.ticker} 财报数据暂不可用`}
                  </CardTitle>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {data.company_type === 'unlisted'
                      ? '未上市公司默认展示 seed 画像，命中事件后自动切换为 live。'
                      : data.earnings_card?.guidance ?? '当前仅返回新闻与规则分析，请稍后重试。'}
                  </p>
                </div>
                {data.company_type === 'listed' ? (
                  <TooltipProvider delayDuration={150}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border bg-muted/45 text-muted-foreground transition-colors hover:text-foreground"
                          aria-label="图表说明"
                        >
                          <Info className="h-4 w-4" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>图表对比 EPS/Revenue 当前值与同比变化。</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ) : null}
              </CardHeader>
              <CardContent className="space-y-4">
                {data.company_type === 'unlisted' ? (
                  isUnlistedDetailFetching ? (
                    <div className="space-y-2">
                      <Skeleton className="h-20 w-full" />
                      <Skeleton className="h-28 w-full" />
                    </div>
                  ) : !unlistedDetail ? (
                    <p className="text-sm text-muted-foreground">未上市公司画像暂不可用，请稍后重试。</p>
                  ) : (
                    <div className="space-y-4">
                      <div className="rounded-md border border-border bg-background/35 p-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline">{unlistedDetail.company.name}</Badge>
                          <Badge variant="outline">status: {unlistedDetail.company.status}</Badge>
                          <Badge variant={unlistedDetail.company.source_type === 'live' ? 'success' : 'outline'}>
                            source_type: {unlistedDetail.company.source_type}
                          </Badge>
                          <Badge variant="outline">
                            updated_at: {formatDateTime(unlistedDetail.company.updated_at)}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{unlistedDetail.company.description}</p>
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-md border border-border bg-background/35 p-3">
                          <p className="text-xs text-muted-foreground">Core Products</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {unlistedDetail.company.core_products.map((product) => (
                              <Badge key={product} variant="secondary">
                                {product}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-md border border-border bg-background/35 p-3">
                          <p className="text-xs text-muted-foreground">Related Concepts</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {unlistedDetail.company.related_concepts.map((concept) => (
                              <Badge key={concept} variant="outline">
                                {concept}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="space-y-2 rounded-md border border-border bg-background/35 p-3">
                        <p className="text-xs text-muted-foreground">
                          Timeline ({unlistedDetail.total_events}) · {unlistedDetail.note ?? '按事件时间倒序展示'}
                        </p>
                        {unlistedDetail.timeline.length === 0 ? (
                          <p className="text-sm text-muted-foreground">尚未命中实时事件，当前展示种子画像。</p>
                        ) : (
                          unlistedDetail.timeline.slice(0, 6).map((item) => (
                            <div key={item.event_id} className="rounded-md border border-border bg-background/45 p-2">
                              <p className="text-sm font-semibold text-foreground">{item.headline}</p>
                              <p className="text-xs text-muted-foreground">
                                {item.publisher} · {formatDateTime(item.event_time)} · impact {item.impact}
                              </p>
                              <div className="mt-1 flex flex-wrap gap-2">
                                <Badge variant="outline">{item.event_type}</Badge>
                                <Badge variant={item.source_type === 'live' ? 'success' : 'outline'}>
                                  {item.source_type}
                                </Badge>
                                {item.source_url ? (
                                  <a
                                    href={item.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-xs text-primary underline-offset-4 hover:underline"
                                  >
                                    来源
                                  </a>
                                ) : null}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )
                ) : !data.earnings_card ? (
                  <p className="text-sm text-muted-foreground">未获取到实时财报字段，已触发回退策略。</p>
                ) : (
                  <>
                    <div className="grid gap-3 md:grid-cols-4">
                      <div className="rounded-md border border-border bg-background/35 p-3">
                        <p className="text-xs text-muted-foreground">EPS</p>
                        <p className="text-lg font-semibold text-foreground">
                          {formatMetricValue(data.earnings_card.eps.value)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          YoY {formatPctValue(data.earnings_card.eps.yoy)}
                        </p>
                      </div>
                      <div className="rounded-md border border-border bg-background/35 p-3">
                        <p className="text-xs text-muted-foreground">Revenue (B)</p>
                        <p className="text-lg font-semibold text-foreground">
                          {formatMetricValue(data.earnings_card.revenue.value)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          YoY {formatPctValue(data.earnings_card.revenue.yoy)}
                        </p>
                      </div>
                      <div className="rounded-md border border-border bg-background/35 p-3">
                        <p className="text-xs text-muted-foreground">Sentiment</p>
                        <p className="text-lg font-semibold text-foreground">{data.earnings_card.sentiment}</p>
                        <p className="text-xs text-muted-foreground">Ticker: {data.ticker}</p>
                      </div>
                      <div className="rounded-md border border-border bg-background/35 p-3">
                        <p className="text-xs text-muted-foreground">Quote</p>
                        <p className="text-lg font-semibold text-foreground">
                          {data.quote ? formatMetricValue(data.quote.price) : 'N/A'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {data.quote?.currency ?? '--'} · {data.quote ? formatDateTime(data.quote.as_of) : '--'}
                        </p>
                      </div>
                    </div>

                    <ChartContainer config={chartConfig} className="h-64 w-full">
                      <BarChart data={chartData}>
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis dataKey="metric" tickLine={false} axisLine={false} />
                        <YAxis yAxisId="left" tickLine={false} axisLine={false} width={60} />
                        <YAxis
                          yAxisId="right"
                          orientation="right"
                          tickLine={false}
                          axisLine={false}
                          width={60}
                          tickFormatter={(value: number) => `${value}%`}
                        />
                        <ChartTooltip
                          content={
                            <ChartTooltipContent
                              formatter={(value, name) => (
                                <span className="font-semibold text-foreground">
                                  {name === 'yoy' ? formatPctValue(Number(value)) : formatMetricValue(Number(value))}
                                </span>
                              )}
                            />
                          }
                        />
                        <ChartLegend content={<ChartLegendContent />} />
                        <Bar yAxisId="left" dataKey="current" fill="var(--color-current)" radius={[6, 6, 0, 0]} />
                        <Bar yAxisId="right" dataKey="yoy" fill="var(--color-yoy)" radius={[6, 6, 0, 0]} />
                      </BarChart>
                    </ChartContainer>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="news">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent News</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.news.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无相关新闻。</p>
                ) : (
                  data.news.map((item) => (
                    <div key={item.event_id} className="rounded-md border border-border bg-background/30 p-3">
                      <p className="text-sm font-semibold text-foreground">{item.headline}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.publisher} · {formatDateTime(item.event_time)} · impact {item.impact}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">{item.summary}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge variant="outline">{item.event_type}</Badge>
                        <Badge variant={item.source_type === 'news' ? 'success' : 'outline'}>
                          {item.source_type}
                        </Badge>
                        {item.source_url ? (
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs text-primary underline-offset-4 hover:underline"
                          >
                            查看来源
                          </a>
                        ) : null}
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Unified Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">model: {data.analysis.model}</Badge>
                  <Badge variant={data.analysis.is_fallback ? 'warning' : 'success'}>
                    {data.analysis.is_fallback ? 'fallback' : 'live'}
                  </Badge>
                </div>
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">{data.analysis.answer}</p>
                {data.analysis.sources.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-foreground">Sources</p>
                    {data.analysis.sources.map((source) => (
                      <div
                        key={source.quote_id}
                        className="rounded-md border border-border bg-background/30 p-2 text-xs text-muted-foreground"
                      >
                        <p className="font-medium text-foreground">{source.title}</p>
                        <p>{source.excerpt}</p>
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary underline-offset-4 hover:underline"
                        >
                          {source.source_url}
                        </a>
                      </div>
                    ))}
                  </div>
                ) : null}
                {data.note ? <p className="text-xs text-muted-foreground">备注：{data.note}</p> : null}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
