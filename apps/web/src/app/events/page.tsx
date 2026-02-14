'use client';

import { Suspense, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiGet } from '@/lib/api';
import { formatApiDateTime } from '@/lib/datetime';
import type { Event, PaginatedEvents } from '@market/shared';
import {
  ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';

const marketOptions = ['US', 'HK', 'FX', 'RATES', 'METALS'];
const sectorOptions = ['Tech', 'Industrials'];
const typeOptions = [
  'earnings',
  'guidance',
  'mna',
  'buyback',
  'rate_decision',
  'macro_release',
  'regulation',
  'risk',
];
const stanceOptions = ['positive', 'neutral', 'negative'];
const originOptions = ['all', 'live', 'seed'] as const;

const formatTime = (value: string) => formatApiDateTime(value);

function EventsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const queryParams = useMemo(() => {
    const params = Object.fromEntries(searchParams.entries());
    return {
      from: params.from,
      to: params.to,
      market: params.market,
      sector: params.sector,
      type: params.type,
      origin: params.origin,
      stance: params.stance,
      minImpact: params.minImpact,
      minConfidence: params.minConfidence,
      q: params.q,
      page: params.page ?? '1',
      pageSize: params.pageSize ?? '20',
    };
  }, [searchParams]);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['events', queryParams],
    queryFn: () => apiGet<PaginatedEvents>('/events', queryParams),
  });

  const { data: detailData, isFetching: detailLoading } = useQuery({
    queryKey: ['event', selectedId],
    queryFn: () => apiGet<Event>(`/events/${selectedId}`),
    enabled: Boolean(selectedId),
  });

  const columns = useMemo<ColumnDef<Event>[]>(
    () => [
      {
        accessorKey: 'headline',
        header: 'Event',
        cell: ({ row }) => (
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-900">{row.original.headline}</p>
            <p className="text-xs text-slate-500">{row.original.publisher}</p>
          </div>
        ),
      },
      {
        accessorKey: 'markets',
        header: 'Markets',
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            {row.original.markets.map((market) => (
              <Badge key={market} variant="secondary">
                {market}
              </Badge>
            ))}
          </div>
        ),
      },
      {
        accessorKey: 'event_type',
        header: 'Type',
        cell: ({ row }) => <span className="text-xs uppercase text-slate-600">{row.original.event_type}</span>,
      },
      {
        accessorKey: 'data_origin',
        header: 'Origin',
        cell: ({ row }) => (
          <Badge variant={row.original.data_origin === 'live' ? 'default' : 'secondary'}>
            {row.original.data_origin === 'live' ? 'Live' : 'Seed'}
          </Badge>
        ),
      },
      {
        accessorKey: 'impact',
        header: 'Impact',
        cell: ({ row }) => <span className="text-sm font-semibold">{row.original.impact}</span>,
      },
      {
        accessorKey: 'stance',
        header: 'Stance',
        cell: ({ row }) => (
          <Badge variant={row.original.stance === 'positive' ? 'default' : 'secondary'}>
            {row.original.stance}
          </Badge>
        ),
      },
      {
        accessorKey: 'event_time',
        header: 'Time',
        cell: ({ row }) => <span className="text-xs text-slate-500">{formatTime(row.original.event_time)}</span>,
      },
    ],
    [],
  );

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 1;

  const updateParams = (next: Record<string, string | undefined>) => {
    const nextParams = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (!value) {
        nextParams.delete(key);
      } else {
        nextParams.set(key, value);
      }
    });
    router.push(`/events?${nextParams.toString()}`);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    updateParams({
      q: (formData.get('q') as string) || undefined,
      market: (formData.get('market') as string) || undefined,
      sector: (formData.get('sector') as string) || undefined,
      type: (formData.get('type') as string) || undefined,
      origin: (formData.get('origin') as string) || undefined,
      stance: (formData.get('stance') as string) || undefined,
      minImpact: (formData.get('minImpact') as string) || undefined,
      minConfidence: (formData.get('minConfidence') as string) || undefined,
      page: '1',
    });
  };

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Event Hub</h1>
        <p className="text-sm text-slate-600">
          Filter, rank, and deep dive into cross-asset catalysts with evidence-backed context.
        </p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit}>
            <Input name="q" placeholder="Search headline, ticker, or keyword" defaultValue={queryParams.q} />
            <Select name="market" defaultValue={queryParams.market ?? ''}>
              <SelectTrigger>
                <SelectValue placeholder="Market" />
              </SelectTrigger>
              <SelectContent>
                {marketOptions.map((market) => (
                  <SelectItem key={market} value={market}>
                    {market}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select name="sector" defaultValue={queryParams.sector ?? ''}>
              <SelectTrigger>
                <SelectValue placeholder="Sector" />
              </SelectTrigger>
              <SelectContent>
                {sectorOptions.map((sector) => (
                  <SelectItem key={sector} value={sector}>
                    {sector}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select name="type" defaultValue={queryParams.type ?? ''}>
              <SelectTrigger>
                <SelectValue placeholder="Event type" />
              </SelectTrigger>
              <SelectContent>
                {typeOptions.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select name="stance" defaultValue={queryParams.stance ?? ''}>
              <SelectTrigger>
                <SelectValue placeholder="Stance" />
              </SelectTrigger>
              <SelectContent>
                {stanceOptions.map((stance) => (
                  <SelectItem key={stance} value={stance}>
                    {stance}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select name="origin" defaultValue={queryParams.origin ?? ''}>
              <SelectTrigger>
                <SelectValue placeholder="Origin" />
              </SelectTrigger>
              <SelectContent>
                {originOptions.map((origin) => (
                  <SelectItem key={origin} value={origin}>
                    {origin}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input name="minImpact" type="number" min="0" max="100" placeholder="Min impact" defaultValue={queryParams.minImpact} />
            <Input
              name="minConfidence"
              type="number"
              min="0"
              max="1"
              step="0.01"
              placeholder="Min confidence"
              defaultValue={queryParams.minConfidence}
            />
            <div className="flex items-center gap-2">
              <Button type="submit">Apply</Button>
              <Button type="button" variant="outline" onClick={() => router.push('/events')}>
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Event Feed</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-14" />
              ))}
            </div>
          ) : isError || !data ? (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">Unable to load events.</p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          ) : data.items.length === 0 ? (
            <p className="text-sm text-slate-600">No events match your filters.</p>
          ) : (
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead
                        key={header.id}
                        onClick={header.column.getToggleSortingHandler()}
                        className="cursor-pointer select-none"
                      >
                        {header.isPlaceholder ? null : header.column.columnDef.header?.toString()}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {table.getRowModel().rows.map((row) => (
                  <TableRow key={row.id} onClick={() => setSelectedId(row.original.event_id)}>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>{cell.renderValue() as React.ReactNode}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {data ? (
            <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
              <span>
                Page {data.page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() => updateParams({ page: String(data.page - 1) })}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= totalPages}
                  onClick={() => updateParams({ page: String(data.page + 1) })}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Drawer open={Boolean(selectedId)} onOpenChange={(open) => !open && setSelectedId(null)}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Event Details</DrawerTitle>
          </DrawerHeader>
          {detailLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-24" />
            </div>
          ) : detailData ? (
            <div className="space-y-6 text-sm">
              <div>
                <p className="text-lg font-semibold text-slate-900">{detailData.headline}</p>
                <p className="text-xs text-slate-500">{detailData.publisher}</p>
              </div>
              <p className="text-slate-700">{detailData.summary}</p>
              <div className="grid gap-3">
                <div>
                  <p className="text-xs uppercase text-slate-500">Impact Chain</p>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-slate-700">
                    {detailData.impact_chain.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500">Key Numbers</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    {detailData.numbers.map((number) => (
                      <div key={number.name} className="rounded-md border border-slate-100 p-3">
                        <p className="text-xs text-slate-500">{number.name}</p>
                        <p className="text-base font-semibold">
                          {number.value} {number.unit ?? ''}
                        </p>
                        <p className="text-xs text-slate-500">{number.period ?? ''}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase text-slate-500">Evidence</p>
                  <div className="mt-2 space-y-2">
                    {detailData.evidence.map((item) => (
                      <div key={item.quote_id} className="rounded-md border border-slate-100 p-3">
                        <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                        <p className="text-xs text-slate-500">{item.source_url}</p>
                        <p className="text-xs text-slate-600">{item.excerpt}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Select an event to view details.</p>
          )}
        </DrawerContent>
      </Drawer>
    </div>
  );
}

function EventsPageFallback() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Event Hub</h1>
        <p className="text-sm text-slate-600">Loading event filters and feed...</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {Array.from({ length: 9 }).map((_, index) => (
              <Skeleton key={index} className="h-10" />
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Event Feed</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-14" />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default function EventsPage() {
  return (
    <Suspense fallback={<EventsPageFallback />}>
      <EventsPageContent />
    </Suspense>
  );
}
