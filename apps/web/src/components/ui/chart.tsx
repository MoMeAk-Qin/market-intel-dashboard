'use client';

import * as React from 'react';
import * as RechartsPrimitive from 'recharts';
import { cn } from '@/lib/utils';

export type ChartConfig = Record<
  string,
  {
    label?: React.ReactNode;
    icon?: React.ComponentType<{ className?: string }>;
    color?: string;
  }
>;

type ChartContextProps = {
  config: ChartConfig;
};

const ChartContext = React.createContext<ChartContextProps | null>(null);

const useChart = () => {
  const context = React.useContext(ChartContext);
  if (!context) {
    throw new Error('useChart must be used within <ChartContainer>');
  }
  return context;
};

const ChartStyle = ({ id, config }: { id: string; config: ChartConfig }) => {
  const colorEntries = Object.entries(config).filter(([, value]) => value.color);
  if (colorEntries.length === 0) {
    return null;
  }

  const cssVariables = colorEntries
    .map(([key, value]) => `  --color-${key}: ${value.color};`)
    .join('\n');

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: `[data-chart="${id}"] {\n${cssVariables}\n}`,
      }}
    />
  );
};

type ChartContainerProps = React.HTMLAttributes<HTMLDivElement> & {
  config: ChartConfig;
  children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>['children'];
};

const ChartContainer = React.forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ id, className, children, config, ...props }, ref) => {
    const uniqueId = React.useId().replace(/:/g, '');
    const chartId = `chart-${id ?? uniqueId}`;

    return (
      <div
        ref={ref}
        data-chart={chartId}
        className={cn(
          'flex aspect-video justify-center text-xs [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-legend-item-text]:text-foreground [&_.recharts-cartesian-grid_line[stroke="#ccc"]]:stroke-border',
          className,
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <ChartContext.Provider value={{ config }}>
          <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
        </ChartContext.Provider>
      </div>
    );
  },
);
ChartContainer.displayName = 'ChartContainer';

const ChartTooltip = RechartsPrimitive.Tooltip;
const ChartLegend = RechartsPrimitive.Legend;

type TooltipPayloadItem = {
  dataKey?: string | number;
  name?: string;
  value?: string | number;
  color?: string;
  payload?: Record<string, unknown>;
};

type ChartTooltipContentProps = React.HTMLAttributes<HTMLDivElement> & {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
  hideLabel?: boolean;
  formatter?: (
    value: string | number,
    name: string,
    item: TooltipPayloadItem,
    index: number,
    payload: TooltipPayloadItem[],
  ) => React.ReactNode;
  labelFormatter?: (label: string | number, payload: TooltipPayloadItem[]) => React.ReactNode;
};

const ChartTooltipContent = React.forwardRef<HTMLDivElement, ChartTooltipContentProps>(
  (
    {
      active,
      payload = [],
      label,
      hideLabel = false,
      formatter,
      labelFormatter,
      className,
      ...props
    },
    ref,
  ) => {
    const { config } = useChart();

    if (!active || payload.length === 0) {
      return null;
    }

    const labelNode =
      hideLabel || label === undefined
        ? null
        : labelFormatter
          ? labelFormatter(label, payload)
          : <p className="font-medium text-foreground">{label}</p>;

    return (
      <div
        ref={ref}
        className={cn(
          'min-w-[10rem] rounded-md border border-border bg-popover/95 px-3 py-2 text-popover-foreground shadow-panel backdrop-blur-md',
          className,
        )}
        {...props}
      >
        {labelNode}
        <div className="mt-2 space-y-1">
          {payload.map((item, index) => {
            const key = String(item.dataKey ?? item.name ?? index);
            const itemConfig = config[String(item.dataKey ?? '')];
            const itemLabel = itemConfig?.label ?? item.name ?? item.dataKey ?? key;
            const markerColor = item.color ?? itemConfig?.color ?? 'hsl(var(--muted-foreground))';

            return (
              <div key={key} className="flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: markerColor }}
                    aria-hidden
                  />
                  <span className="text-muted-foreground">{itemLabel}</span>
                </div>
                {formatter ? (
                  formatter(
                    item.value ?? '',
                    String(item.name ?? item.dataKey ?? ''),
                    item,
                    index,
                    payload,
                  )
                ) : (
                  <span className="font-semibold text-foreground">{item.value ?? '-'}</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  },
);
ChartTooltipContent.displayName = 'ChartTooltipContent';

type LegendPayloadItem = {
  dataKey?: string | number;
  value?: string;
  color?: string;
};

type ChartLegendContentProps = React.HTMLAttributes<HTMLDivElement> & {
  payload?: LegendPayloadItem[];
};

const ChartLegendContent = React.forwardRef<HTMLDivElement, ChartLegendContentProps>(
  ({ className, payload = [], ...props }, ref) => {
    const { config } = useChart();

    if (payload.length === 0) {
      return null;
    }

    return (
      <div ref={ref} className={cn('mt-2 flex flex-wrap items-center justify-center gap-4', className)} {...props}>
        {payload.map((item) => {
          const key = String(item.dataKey ?? item.value ?? '');
          const itemConfig = config[String(item.dataKey ?? '')];
          const color = item.color ?? itemConfig?.color ?? 'hsl(var(--muted-foreground))';
          return (
            <div key={key} className="flex items-center gap-2 text-xs">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} aria-hidden />
              <span className="text-muted-foreground">{itemConfig?.label ?? item.value ?? key}</span>
            </div>
          );
        })}
      </div>
    );
  },
);
ChartLegendContent.displayName = 'ChartLegendContent';

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  useChart,
};
