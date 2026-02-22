'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getModelRegistry, selectModel } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';

type ModelSelectorProps = {
  className?: string;
};

export function ModelSelector({ className }: ModelSelectorProps) {
  const queryClient = useQueryClient();
  const [draftModel, setDraftModel] = useState<string>('');
  const modelQuery = useQuery({
    queryKey: ['model-registry'],
    queryFn: getModelRegistry,
  });

  useEffect(() => {
    if (!modelQuery.data) {
      return;
    }
    if (!draftModel) {
      setDraftModel(modelQuery.data.active_model);
    }
  }, [draftModel, modelQuery.data]);

  const switchMutation = useMutation({
    mutationFn: (model: string) => selectModel({ model }),
    onSuccess: (payload) => {
      setDraftModel(payload.active_model);
      void queryClient.invalidateQueries({ queryKey: ['model-registry'] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard-report'] });
    },
  });

  if (modelQuery.isLoading) {
    return <Skeleton className={cn('h-12 w-full', className)} />;
  }
  if (modelQuery.isError || !modelQuery.data) {
    return (
      <div className={cn('rounded-md border border-border bg-background/25 px-3 py-2 text-xs text-muted-foreground', className)}>
        模型配置读取失败
      </div>
    );
  }

  const changed = draftModel !== modelQuery.data.active_model;
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant="outline">active: {modelQuery.data.active_model}</Badge>
        <Badge variant="outline">default: {modelQuery.data.default_model}</Badge>
      </div>
      <div className="flex gap-2">
        <Select value={draftModel} onValueChange={setDraftModel}>
          <SelectTrigger className="min-w-[180px]">
            <SelectValue placeholder="选择模型" />
          </SelectTrigger>
          <SelectContent>
            {modelQuery.data.available_models.map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant={changed ? 'default' : 'outline'}
          disabled={!changed || switchMutation.isPending}
          onClick={() => switchMutation.mutate(draftModel)}
        >
          {switchMutation.isPending ? '切换中...' : '切换模型'}
        </Button>
      </div>
    </div>
  );
}
