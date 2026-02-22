'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import {
  getAnalysisTask,
  listAnalysisTasks,
  submitAnalysisTask,
} from '@/lib/api';
import type { AnalysisTaskInfo, TaskStatus } from '@market/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

const searchQuestionSchema = z.object({
  question: z.string().trim().min(5, '问题至少 5 个字符').max(500, '问题请控制在 500 字以内'),
});

type SearchQuestionFormValues = z.input<typeof searchQuestionSchema>;

const defaultSearchValues: SearchQuestionFormValues = {
  question: 'What is the latest rate decision signal?',
};

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
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const questionForm = useForm<SearchQuestionFormValues>({
    resolver: zodResolver(searchQuestionSchema),
    defaultValues: defaultSearchValues,
  });

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

  const handleSubmit = questionForm.handleSubmit((values) => {
    submitTask.mutate(values.question.trim());
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Search & Q&A</h1>
        <p className="text-sm text-muted-foreground">
          提交分析任务后异步执行，可在任务列表里持续追踪状态。
        </p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Question</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...questionForm}>
            <form className="flex flex-col gap-3 md:flex-row md:items-start" onSubmit={handleSubmit}>
              <FormField
                control={questionForm.control}
                name="question"
                render={({ field }) => (
                  <FormItem className="w-full">
                    <FormLabel>分析问题</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={submitTask.isPending} className="md:mt-7">
                提交任务
              </Button>
            </form>
          </Form>
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
              <p className="text-xs text-muted-foreground">Task ID: {activeTask.task_id}</p>
              {activeTask.status === 'failed' ? (
                <p className="text-sm text-rose-600">{activeTask.error ?? '任务执行失败'}</p>
              ) : activeTask.result ? (
                <>
                  <p className="whitespace-pre-wrap text-sm text-foreground/90">{activeTask.result.answer}</p>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Evidence</p>
                    <div className="mt-2 space-y-2">
                      {activeTask.result.sources.map((item) => (
                        <div key={item.quote_id} className="rounded-md border border-border bg-background/20 p-3">
                          <p className="text-sm font-semibold text-foreground">{item.title}</p>
                          <p className="text-xs text-muted-foreground">{item.source_url}</p>
                          <p className="text-xs text-muted-foreground">{item.excerpt}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">任务已提交，等待分析完成。</p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">提交问题后，这里会显示任务状态与结果。</p>
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
            <p className="text-sm text-muted-foreground">任务列表加载失败。</p>
          ) : taskList.data.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无历史任务。</p>
          ) : (
            taskList.data.items.map((item) => (
              <button
                key={item.task_id}
                type="button"
                onClick={() => setActiveTaskId(item.task_id)}
                className="w-full cursor-pointer rounded-md border border-border bg-background/20 p-3 text-left transition-colors hover:bg-muted/35"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="line-clamp-1 text-sm font-medium text-foreground">{item.payload.question}</p>
                  <Badge variant={statusVariant[item.status]}>{statusLabel[item.status]}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{item.task_id}</p>
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
