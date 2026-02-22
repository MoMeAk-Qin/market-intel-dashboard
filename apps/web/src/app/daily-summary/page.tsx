'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { getDailySummary } from '@/lib/api';
import type { DailySummaryRequest } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

const splitCsv = (value: string): string[] =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const tickerTokenRegex = /^[A-Za-z0-9.-]+$/;

const dailySummaryFormSchema = z.object({
  focus: z.string().trim().min(1, '摘要焦点不能为空').max(400, '摘要焦点请控制在 400 字以内'),
  markets: z.string().default(''),
  tickers: z
    .string()
    .default('')
    .refine((value) => {
      if (!value.trim()) {
        return true;
      }
      return splitCsv(value).every((token) => tickerTokenRegex.test(token));
    }, '标的格式无效，请使用逗号分隔，如 AAPL,0700.HK'),
  query: z.string().default(''),
  limit: z
    .string()
    .default('20')
    .refine((value) => {
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 1 && parsed <= 50;
    }, '新闻上限必须是 1 到 50 的整数'),
});

type DailySummaryFormValues = z.input<typeof dailySummaryFormSchema>;

const defaultFormValues: DailySummaryFormValues = {
  focus: '请按重点、影响、风险与关注点输出今日摘要。',
  markets: '',
  tickers: '',
  query: '',
  limit: '20',
};

const toPayload = (values: DailySummaryFormValues): DailySummaryRequest => ({
  focus: values.focus?.trim() || undefined,
  markets: splitCsv(values.markets ?? ''),
  tickers: splitCsv(values.tickers ?? ''),
  query: values.query?.trim() || undefined,
  limit: Number(values.limit ?? '20'),
  use_retrieval: true,
  top_k: 6,
});

export default function DailySummaryPage() {
  const form = useForm<DailySummaryFormValues>({
    resolver: zodResolver(dailySummaryFormSchema),
    defaultValues: defaultFormValues,
  });

  const { mutate, data, isPending, isError, reset } = useMutation({
    mutationFn: (input: DailySummaryRequest) => getDailySummary(input),
  });

  const handleSubmit = form.handleSubmit((values) => {
    mutate(toPayload(values));
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">日报摘要</h1>
        <p className="text-sm text-muted-foreground">基于今日新闻生成结构化摘要，并展示证据来源。</p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">摘要参数</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="grid gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
              <FormField
                control={form.control}
                name="focus"
                render={({ field }) => (
                  <FormItem className="md:col-span-2">
                    <FormLabel>摘要焦点</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="markets"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>市场（逗号分隔）</FormLabel>
                    <FormControl>
                      <Input placeholder="US,HK" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="tickers"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>标的（逗号分隔）</FormLabel>
                    <FormControl>
                      <Input placeholder="AAPL,0700.HK" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="query"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>关键词</FormLabel>
                    <FormControl>
                      <Input placeholder="rate, inflation" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="limit"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>新闻上限</FormLabel>
                    <FormControl>
                      <Input type="number" min="1" max="50" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="md:col-span-2 flex flex-wrap gap-3">
                <Button type="submit" disabled={isPending}>
                  生成摘要
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    reset();
                    form.reset(defaultFormValues);
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
          </Form>
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
            <p className="text-sm text-muted-foreground">生成失败，请检查后端配置并重试。</p>
          ) : data ? (
            <>
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="secondary">日期 {data.date}</Badge>
                <Badge variant="secondary">新闻数 {data.total_news}</Badge>
                <Badge variant="secondary">模型 {data.model}</Badge>
              </div>
              <div className="rounded-md border border-border bg-background/20 p-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">{data.answer}</p>
              </div>
              <div>
                <p className="mb-2 text-xs uppercase text-muted-foreground">证据</p>
                <div className="space-y-3">
                  {data.sources.map((source) => (
                    <article key={source.quote_id} className="rounded-md border border-border bg-background/20 p-3">
                      <p className="text-sm font-semibold text-foreground">{source.title}</p>
                      <a
                        className="text-xs text-primary underline"
                        href={source.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {source.source_url}
                      </a>
                      <p className="mt-1 text-xs text-muted-foreground">{source.excerpt}</p>
                    </article>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">提交参数后生成日报摘要。</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
