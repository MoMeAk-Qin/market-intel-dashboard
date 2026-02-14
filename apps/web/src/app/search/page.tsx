'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  getAnalysisTask,
  listAnalysisTasks,
  submitAnalysisTask,
} from '@/lib/api';
import type { AnalysisTaskInfo, TaskStatus } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

const statusLabel: Record<TaskStatus, string> = {
  pending: '排队中',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
};

const statusVariant: Record<TaskStatus, 'secondary' | 'warning' | 'success' | 'outline'> = {
  pending: 'secondary',
  running: 'warning',
  completed: 'success',
  failed: 'outline',
};

export default function SearchPage() {
  const [question, setQuestion] = useState('What is the latest rate decision signal?');
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const submitTask = useMutation({
    mutationFn: (input: string) => submitAnalysisTask({ question: input }),
    onSuccess: (task) => setActiveTaskId(task.task_id),
  });

  const taskDetail = useQuery({
    queryKey: ['analysis-task', activeTaskId],
    queryFn: () => getAnalysisTask(activeTaskId ?? ''),
    enabled: Boolean(activeTaskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') {
        return false;
      }
      return 1000;
    },
  });

  const taskList = useQuery({
    queryKey: ['analysis-task-list'],
    queryFn: () => listAnalysisTasks(8),
    refetchInterval: 3000,
  });

  const activeTask = useMemo<AnalysisTaskInfo | null>(() => {
    if (taskDetail.data) {
      return taskDetail.data;
    }
    if (activeTaskId && taskList.data) {
      return taskList.data.items.find((item) => item.task_id === activeTaskId) ?? null;
    }
    return null;
  }, [activeTaskId, taskDetail.data, taskList.data]);

  const isSubmitting = submitTask.isPending || taskDetail.isFetching;

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Search & Q&A</h1>
        <p className="text-sm text-slate-600">
          提交分析任务后异步执行，可在任务列表里持续追踪状态。
        </p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Question</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 md:flex-row md:items-center"
            onSubmit={(event) => {
              event.preventDefault();
              const next = question.trim();
              if (next) {
                submitTask.mutate(next);
              }
            }}
          >
            <Input value={question} onChange={(event) => setQuestion(event.target.value)} />
            <Button type="submit" disabled={submitTask.isPending}>
              提交任务
            </Button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link href="/news">
              <Button type="button" size="sm" variant="outline">
                今日新闻
              </Button>
            </Link>
            <Link href="/daily-summary">
              <Button type="button" size="sm" variant="outline">
                日报摘要
              </Button>
            </Link>
          </div>
          {submitTask.isError ? (
            <p className="mt-3 text-sm text-rose-600">
              提交失败：{submitTask.error instanceof Error ? submitTask.error.message : 'unknown error'}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Task Status</CardTitle>
          {activeTask ? <Badge variant={statusVariant[activeTask.status]}>{statusLabel[activeTask.status]}</Badge> : null}
        </CardHeader>
        <CardContent className="space-y-4">
          {isSubmitting ? (
            <Skeleton className="h-16" />
          ) : activeTask ? (
            <>
              <p className="text-xs text-slate-500">Task ID: {activeTask.task_id}</p>
              {activeTask.status === 'failed' ? (
                <p className="text-sm text-rose-600">{activeTask.error ?? '任务执行失败'}</p>
              ) : activeTask.result ? (
                <>
                  <p className="whitespace-pre-wrap text-sm text-slate-700">{activeTask.result.answer}</p>
                  <div>
                    <p className="text-xs uppercase text-slate-500">Evidence</p>
                    <div className="mt-2 space-y-2">
                      {activeTask.result.sources.map((item) => (
                        <div key={item.quote_id} className="rounded-md border border-slate-100 p-3">
                          <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                          <p className="text-xs text-slate-500">{item.source_url}</p>
                          <p className="text-xs text-slate-600">{item.excerpt}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-600">任务已提交，等待分析完成。</p>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-500">提交问题后，这里会显示任务状态与结果。</p>
          )}
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Recent Tasks</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {taskList.isLoading ? (
            <Skeleton className="h-20" />
          ) : taskList.isError || !taskList.data ? (
            <p className="text-sm text-slate-500">任务列表加载失败。</p>
          ) : taskList.data.items.length === 0 ? (
            <p className="text-sm text-slate-500">暂无历史任务。</p>
          ) : (
            taskList.data.items.map((item) => (
              <button
                key={item.task_id}
                type="button"
                onClick={() => setActiveTaskId(item.task_id)}
                className="w-full cursor-pointer rounded-md border border-slate-100 p-3 text-left transition-colors hover:bg-slate-50"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="line-clamp-1 text-sm font-medium text-slate-900">{item.payload.question}</p>
                  <Badge variant={statusVariant[item.status]}>{statusLabel[item.status]}</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-500">{item.task_id}</p>
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
