'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { generateDailyReport, getLatestReport } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

type ReportBadgeProps = {
  className?: string;
};

function statusVariant(status: string, sourceType: string): 'outline' | 'warning' | 'success' | 'secondary' {
  if (status === 'running') {
    return 'warning';
  }
  if (status === 'completed' && sourceType === 'live') {
    return 'success';
  }
  if (status === 'completed' && sourceType === 'fallback') {
    return 'outline';
  }
  if (status === 'failed') {
    return 'warning';
  }
  return 'secondary';
}

export function ReportBadge({ className }: ReportBadgeProps) {
  const queryClient = useQueryClient();
  const reportQuery = useQuery({
    queryKey: ['dashboard-report'],
    queryFn: getLatestReport,
    refetchInterval: 60_000,
  });
  const generateMutation = useMutation({
    mutationFn: () => generateDailyReport(true),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['dashboard-report'] });
    },
  });

  if (reportQuery.isLoading) {
    return <Skeleton className={cn('h-14 w-full', className)} />;
  }
  if (reportQuery.isError || !reportQuery.data) {
    return (
      <div className={cn('rounded-md border border-border bg-background/25 px-3 py-2 text-xs text-muted-foreground', className)}>
        报告状态读取失败
      </div>
    );
  }

  const report = reportQuery.data;
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={statusVariant(report.status, report.source_type)}>
          report: {report.status}
        </Badge>
        <Badge variant="outline">model: {report.model}</Badge>
        <Badge variant="outline">source: {report.source_type}</Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        target: {report.target_date} · generated:{' '}
        {report.generated_at ? formatApiDateTime(report.generated_at) : 'N/A'} · events: {report.total_events}
      </p>
      {report.summary ? (
        <p className="line-clamp-2 text-xs text-muted-foreground">{report.summary}</p>
      ) : null}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? '生成中...' : '重新生成'}
        </Button>
      </div>
    </div>
  );
}
