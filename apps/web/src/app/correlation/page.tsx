'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type {
  CorrelationPreset,
  CorrelationWindowDays,
  HeatLevel,
} from '@market/shared';
import { analyzeCorrelation, getCorrelationMatrix, getTechHeatmap } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import { CorrelationMatrix, formatCorrAsPct } from '@/components/CorrelationMatrix';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

const presetLabel: Record<CorrelationPreset, string> = {
  A: '方案 A · 宏观核心',
  B: '方案 B · AI 产业链',
  C: '方案 C · 中美科技联动',
};

const levelVariant: Record<HeatLevel, 'warning' | 'success' | 'secondary'> = {
  high: 'warning',
  medium: 'success',
  low: 'secondary',
};

const priceFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

export default function CorrelationPage() {
  const [preset, setPreset] = useState<CorrelationPreset>('A');
  const [windowDays, setWindowDays] = useState<CorrelationWindowDays>(30);
  const [queryText, setQueryText] = useState('AI capex');
  const [submittedQuery, setSubmittedQuery] = useState('AI capex');

  const matrixQuery = useQuery({
    queryKey: ['correlation-matrix', preset, windowDays],
    queryFn: () => getCorrelationMatrix({ preset, window: windowDays }),
  });

  const heatmapQuery = useQuery({
    queryKey: ['tech-heatmap'],
    queryFn: () => getTechHeatmap({ limit: 20 }),
  });

  const causalQuery = useQuery({
    queryKey: ['correlation-analyze', submittedQuery],
    queryFn: () => analyzeCorrelation({ query: submittedQuery, max_depth: 4 }),
    enabled: submittedQuery.trim().length > 0,
  });

  return (
    <div className="space-y-6">
      <section className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Correlation Matrix Lab</h1>
        <p className="text-sm text-muted-foreground">
          同时查看科技热度、7/30/90 天相关矩阵和事件因果链。支持方案 A/B/C 快速切换。
        </p>
      </section>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">参数切换</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs value={preset} onValueChange={(value) => setPreset(value as CorrelationPreset)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="A">方案 A</TabsTrigger>
              <TabsTrigger value="B">方案 B</TabsTrigger>
              <TabsTrigger value="C">方案 C</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="grid gap-3 md:grid-cols-[1fr_220px]">
            <div className="rounded-md border border-border bg-background/25 p-3 text-xs text-muted-foreground">
              当前预设：<span className="font-semibold text-foreground">{presetLabel[preset]}</span>
            </div>
            <Select
              value={String(windowDays)}
              onValueChange={(value) => setWindowDays(Number(value) as CorrelationWindowDays)}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择窗口" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7 天</SelectItem>
                <SelectItem value="30">30 天</SelectItem>
                <SelectItem value="90">90 天</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader className="space-y-2">
          <CardTitle className="text-base">相关矩阵</CardTitle>
          {!matrixQuery.isLoading && matrixQuery.data ? (
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">preset: {matrixQuery.data.preset}</Badge>
              <Badge variant="outline">window: {matrixQuery.data.window_days}D</Badge>
              <Badge variant="outline">updated: {formatApiDateTime(matrixQuery.data.updated_at)}</Badge>
              {matrixQuery.data.fallback_assets.length > 0 ? (
                <Badge variant="warning">fallback: {matrixQuery.data.fallback_assets.join(', ')}</Badge>
              ) : (
                <Badge variant="success">source: live</Badge>
              )}
            </div>
          ) : null}
        </CardHeader>
        <CardContent className="space-y-3">
          {matrixQuery.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : matrixQuery.isError || !matrixQuery.data ? (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">无法加载相关矩阵。</p>
              <Button variant="outline" onClick={() => matrixQuery.refetch()}>
                Retry
              </Button>
            </div>
          ) : (
            <>
              <CorrelationMatrix assets={matrixQuery.data.assets} matrix={matrixQuery.data.matrix} />
              {matrixQuery.data.note ? (
                <p className="text-xs text-muted-foreground">说明：{matrixQuery.data.note}</p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">科技热度</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {heatmapQuery.isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : heatmapQuery.isError || !heatmapQuery.data ? (
              <p className="text-sm text-muted-foreground">热度数据加载失败。</p>
            ) : (
              heatmapQuery.data.items.slice(0, 10).map((item) => (
                <div key={item.asset_id} className="rounded-md border border-border bg-background/25 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{item.asset_id}</p>
                      <Badge variant="outline">{item.market}</Badge>
                      <Badge variant={levelVariant[item.level]}>{item.level}</Badge>
                      <Badge variant={item.source_type === 'live' ? 'success' : item.source_type === 'mixed' ? 'warning' : 'outline'}>
                        {item.source_type}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      heat: <span className="font-semibold text-foreground">{item.heat_score.toFixed(1)}</span>
                    </p>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    mentions(7d): {item.mentions_7d} · avg impact: {item.avg_impact.toFixed(1)} · change:{' '}
                    {item.change_pct === null || item.change_pct === undefined ? 'N/A' : formatCorrAsPct(item.change_pct / 100)}
                    {' '}· price:{' '}
                    {item.latest_price === null || item.latest_price === undefined
                      ? 'N/A'
                      : priceFormatter.format(item.latest_price)}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="fade-up">
          <CardHeader>
            <CardTitle className="text-base">因果链分析</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Input value={queryText} onChange={(event) => setQueryText(event.target.value)} placeholder="输入事件关键词，例如：AI capex / NVDA / DXY" />
              <Button
                onClick={() => setSubmittedQuery(queryText.trim())}
                disabled={!queryText.trim() || causalQuery.isFetching}
              >
                {causalQuery.isFetching ? '分析中...' : 'Analyze'}
              </Button>
            </div>

            {causalQuery.isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : causalQuery.isError || !causalQuery.data ? (
              <p className="text-sm text-muted-foreground">暂无因果链结果。</p>
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">event_id: {causalQuery.data.event_id ?? 'N/A'}</Badge>
                  <Badge variant={causalQuery.data.source_type === 'live' ? 'success' : causalQuery.data.source_type === 'mixed' ? 'warning' : 'outline'}>
                    source: {causalQuery.data.source_type}
                  </Badge>
                  <Badge variant="outline">generated: {formatApiDateTime(causalQuery.data.generated_at)}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{causalQuery.data.summary}</p>
                {causalQuery.data.nodes.map((node) => (
                  <div key={`${node.level}-${node.label}`} className="rounded-md border border-border bg-background/25 p-3">
                    <p className="text-sm font-semibold text-foreground">
                      L{node.level} · {node.label}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{node.detail}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Badge variant="outline">confidence: {node.confidence.toFixed(2)}</Badge>
                      {node.related_assets.map((asset) => (
                        <Badge key={`${node.level}-${asset}`} variant="secondary">
                          {asset}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
