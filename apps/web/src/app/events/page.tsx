'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Suspense, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
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
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
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

const eventsFilterSchema = z.object({
  q: z.string().default(''),
  market: z.string().default(''),
  sector: z.string().default(''),
  type: z.string().default(''),
  origin: z.enum(['all', 'live', 'seed']).default('all'),
  stance: z.string().default(''),
  minImpact: z
    .string()
    .default('')
    .refine((value) => {
      if (!value.trim()) {
        return true;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100;
    }, 'Min impact 必须在 0 到 100 之间'),
  minConfidence: z
    .string()
    .default('')
    .refine((value) => {
      if (!value.trim()) {
        return true;
      }
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed >= 0 && parsed <= 1;
    }, 'Min confidence 必须在 0 到 1 之间'),
});

type EventsFilterValues = z.input<typeof eventsFilterSchema>;

const defaultFilterValues: EventsFilterValues = {
  q: '',
  market: '',
  sector: '',
  type: '',
  origin: 'all',
  stance: '',
  minImpact: '',
  minConfidence: '',
};

const normalizeOriginValue = (value?: string): EventsFilterValues['origin'] =>
  value === 'live' || value === 'seed' || value === 'all' ? value : 'all';

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

  const initialFilterValues = useMemo<EventsFilterValues>(
    () => ({
      q: queryParams.q ?? '',
      market: queryParams.market ?? '',
      sector: queryParams.sector ?? '',
      type: queryParams.type ?? '',
      origin: normalizeOriginValue(queryParams.origin),
      stance: queryParams.stance ?? '',
      minImpact: queryParams.minImpact ?? '',
      minConfidence: queryParams.minConfidence ?? '',
    }),
    [
      queryParams.minConfidence,
      queryParams.minImpact,
      queryParams.market,
      queryParams.origin,
      queryParams.q,
      queryParams.sector,
      queryParams.stance,
      queryParams.type,
    ],
  );

  const filterForm = useForm<EventsFilterValues>({
    resolver: zodResolver(eventsFilterSchema),
    defaultValues: initialFilterValues,
  });

  useEffect(() => {
    filterForm.reset(initialFilterValues);
  }, [filterForm, initialFilterValues]);

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
            <p className="text-sm font-semibold text-foreground">{row.original.headline}</p>
            <p className="text-xs text-muted-foreground">{row.original.publisher}</p>
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
        cell: ({ row }) => <span className="text-xs uppercase text-muted-foreground">{row.original.event_type}</span>,
      },
      {
        accessorKey: 'data_origin',
        header: 'Origin',
        cell: ({ row }) => (
          <Badge variant={row.original.data_origin === 'live' ? 'success' : 'warning'}>
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
        cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatTime(row.original.event_time)}</span>,
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

  const handleSubmit = filterForm.handleSubmit((values) => {
    updateParams({
      q: values.q?.trim() || undefined,
      market: values.market || undefined,
      sector: values.sector || undefined,
      type: values.type || undefined,
      origin: values.origin === 'all' ? undefined : values.origin,
      stance: values.stance || undefined,
      minImpact: values.minImpact?.trim() || undefined,
      minConfidence: values.minConfidence?.trim() || undefined,
      page: '1',
    });
  });

  return (
    <div className="space-y-6">
      <div className="fade-up space-y-2">
        <h1 className="text-3xl font-semibold">Event Hub</h1>
        <p className="text-sm text-muted-foreground">
          Filter, rank, and deep dive into cross-asset catalysts with evidence-backed context.
        </p>
      </div>

      <Card className="fade-up">
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...filterForm}>
            <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit}>
              <FormField
                control={filterForm.control}
                name="q"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>关键词</FormLabel>
                    <FormControl>
                      <Input placeholder="Search headline, ticker, or keyword" {...field} />
                    </FormControl>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="market"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Market</FormLabel>
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Market" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {marketOptions.map((market) => (
                          <SelectItem key={market} value={market}>
                            {market}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="sector"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sector</FormLabel>
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Sector" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {sectorOptions.map((sector) => (
                          <SelectItem key={sector} value={sector}>
                            {sector}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Event type</FormLabel>
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Event type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {typeOptions.map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="stance"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Stance</FormLabel>
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Stance" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {stanceOptions.map((stance) => (
                          <SelectItem key={stance} value={stance}>
                            {stance}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="origin"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Origin</FormLabel>
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Origin" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {originOptions.map((origin) => (
                          <SelectItem key={origin} value={origin}>
                            {origin}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="minImpact"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min impact</FormLabel>
                    <FormControl>
                      <Input type="number" min="0" max="100" placeholder="0 - 100" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={filterForm.control}
                name="minConfidence"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Min confidence</FormLabel>
                    <FormControl>
                      <Input type="number" min="0" max="1" step="0.01" placeholder="0 - 1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="flex items-center gap-2 pt-7">
                <Button type="submit">Apply</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    filterForm.reset(defaultFilterValues);
                    router.push('/events');
                  }}
                >
                  Reset
                </Button>
              </div>
            </form>
          </Form>
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
              <p className="text-sm text-muted-foreground">Unable to load events.</p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          ) : data.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events match your filters.</p>
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
            <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
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
                <p className="text-lg font-semibold text-foreground">{detailData.headline}</p>
                <p className="text-xs text-muted-foreground">{detailData.publisher}</p>
              </div>
              <p className="text-foreground/90">{detailData.summary}</p>
              <div className="grid gap-3">
                <div>
                  <p className="text-xs uppercase text-muted-foreground">Impact Chain</p>
                  <ul className="mt-2 list-disc space-y-1 pl-4 text-foreground/90">
                    {detailData.impact_chain.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase text-muted-foreground">Key Numbers</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    {detailData.numbers.map((number) => (
                      <div key={number.name} className="rounded-md border border-border bg-background/20 p-3">
                        <p className="text-xs text-muted-foreground">{number.name}</p>
                        <p className="text-base font-semibold">
                          {number.value} {number.unit ?? ''}
                        </p>
                        <p className="text-xs text-muted-foreground">{number.period ?? ''}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs uppercase text-muted-foreground">Evidence</p>
                  <div className="mt-2 space-y-2">
                    {detailData.evidence.map((item) => (
                      <div key={item.quote_id} className="rounded-md border border-border bg-background/20 p-3">
                        <p className="text-sm font-semibold text-foreground">{item.title}</p>
                        <p className="text-xs text-muted-foreground">{item.source_url}</p>
                        <p className="text-xs text-muted-foreground">{item.excerpt}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select an event to view details.</p>
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
        <p className="text-sm text-muted-foreground">Loading event filters and feed...</p>
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
