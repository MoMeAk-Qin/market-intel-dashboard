'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '@/lib/api';
import type { QAResponse } from '@market/shared';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';

export default function SearchPage() {
  const [question, setQuestion] = useState('What is the latest rate decision signal?');

  const { mutate, data, isPending, isError } = useMutation({
    mutationFn: (input: string) => apiPost<QAResponse>('/qa', { question: input }),
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Search & Q&A</h1>
        <p className="text-sm text-slate-600">
          Ask for a cross-asset narrative and get evidence-linked answers.
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
              if (next) mutate(next);
            }}
          >
            <Input value={question} onChange={(event) => setQuestion(event.target.value)} />
            <Button type="submit" disabled={isPending}>
              Ask
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Answer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPending ? (
            <Skeleton className="h-20" />
          ) : isError ? (
            <p className="text-sm text-slate-500">Unable to fetch an answer.</p>
          ) : data ? (
            <>
              <p className="text-sm text-slate-700">{data.answer}</p>
              <div>
                <p className="text-xs uppercase text-slate-500">Evidence</p>
                <div className="mt-2 space-y-2">
                  {data.evidence.map((item) => (
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
            <p className="text-sm text-slate-500">Submit a question to get started.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
