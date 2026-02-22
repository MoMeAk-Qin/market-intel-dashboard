'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import type { DashboardSummary } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ModelSelector } from '@/components/ModelSelector';
import { ReportBadge } from '@/components/ReportBadge';
import { Skeleton } from '@/components/ui/skeleton';

const laneLabel: Record<string, string> = {
  macro: '宏观',
  industry: '行业',
  company: '公司',
  policy_risk: '政策与风险',
};

const moneyFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

const pctFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
  signDisplay: 'always',
});

function formatAssetValue(value: number): string {
  if (Math.abs(value) >= 1000) {
    return moneyFormatter.format(value);
  }
  return value.toFixed(2);
}

export default function HomePage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiGet<DashboardSummary>('/dashboard/summary'),
  });

  return (
    <div className="space-y-6">
      <section className="fade-up rounded-3xl border border-cyan-300/25 bg-[linear-gradient(135deg,rgba(15,23,42,0.86)_0%,rgba(15,23,42,0.58)_100%)] p-6 md:p-8">
        <div className="flex flex-wrap items-center gap-3">
          <Badge className="border border-cyan-300/40 bg-cyan-300/10 text-cyan-100" variant="outline">
            Market Intel
          </Badge>
          <Badge className="border border-emerald-300/40 bg-emerald-300/10 text-emerald-100" variant="outline">
            Phase 1 开发中
          </Badge>
        </div>
        <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">跨市场情报总览</h1>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
          聚合事件流、今日新闻、问答分析与日报摘要。当前重点是先打通可观测与前端闭环。
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/news">
            <Button>查看今日新闻</Button>
          </Link>
          <Link href="/daily-summary">
            <Button variant="outline">生成日报摘要</Button>
          </Link>
          <Link href="/search">
            <Button variant="ghost" className="text-foreground hover:bg-muted/55 hover:text-foreground">
              打开问答分析
            </Button>
          </Link>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-border/70 bg-background/35 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">模型配置</p>
            <ModelSelector />
          </div>
          <div className="rounded-xl border border-border/70 bg-background/35 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">每日报告状态</p>
            <ReportBadge />
          </div>
        </div>
      </section>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
      ) : isError || !data ? (
        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">总览加载失败</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">无法获取 `/dashboard/summary`，请确认 API 服务可用后重试。</p>
            <Button onClick={() => refetch()}>重试</Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            <Card className="fade-up">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">高影响事件</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-foreground">{data.kpis.major}</p>
              </CardContent>
            </Card>
            <Card className="fade-up">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">宏观事件</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-foreground">{data.kpis.macro}</p>
              </CardContent>
            </Card>
            <Card className="fade-up">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">公司事件</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-foreground">{data.kpis.company}</p>
              </CardContent>
            </Card>
            <Card className="fade-up">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">风险事件</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold text-foreground">{data.kpis.risk}</p>
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
            <Card className="fade-up">
              <CardHeader>
                <CardTitle className="text-base">关键资产</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.key_assets.map((asset) => (
                  <div key={asset.id} className="flex items-center justify-between rounded-md border border-border bg-background/20 p-3">
                    <div>
                      <p className="text-sm font-semibold text-foreground">{asset.name}</p>
                      <p className="text-xs text-muted-foreground">{asset.id}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-foreground">{formatAssetValue(asset.value)}</p>
                      <p className={asset.changePct >= 0 ? 'text-xs text-emerald-600' : 'text-xs text-rose-600'}>
                        {pctFormatter.format(asset.changePct)}%
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="fade-up">
              <CardHeader>
                <CardTitle className="text-base">热点标签</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {data.hot_tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            {data.timeline.map((lane) => (
              <Card key={lane.lane} className="fade-up">
                <CardHeader>
                  <CardTitle className="text-base">{laneLabel[lane.lane] ?? lane.lane}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {lane.events.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无事件</p>
                  ) : (
                    lane.events.map((event) => (
                      <div key={event.event_id} className="rounded-md border border-border bg-background/20 p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary">{event.event_type}</Badge>
                          <Badge variant={event.stance === 'positive' ? 'default' : 'secondary'}>{event.stance}</Badge>
                        </div>
                        <p className="mt-2 text-sm font-semibold text-foreground">{event.headline}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{formatApiDateTime(event.event_time)}</p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
