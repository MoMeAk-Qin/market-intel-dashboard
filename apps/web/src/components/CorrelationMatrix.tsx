import type { CSSProperties } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';

type CorrelationMatrixProps = {
  assets: string[];
  matrix: number[][];
  className?: string;
};

const pctFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 1,
  signDisplay: 'always',
});

const corrFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
  signDisplay: 'always',
});

function cellStyle(value: number): CSSProperties {
  const alpha = Math.min(Math.abs(value), 1) * 0.5 + 0.08;
  const background = value >= 0 ? `rgba(16,185,129,${alpha})` : `rgba(244,63,94,${alpha})`;
  return { backgroundColor: background };
}

export function CorrelationMatrix({ assets, matrix, className }: CorrelationMatrixProps) {
  if (assets.length === 0 || matrix.length === 0) {
    return <p className={cn('text-sm text-muted-foreground', className)}>暂无矩阵数据。</p>;
  }

  return (
    <Table className={cn(className)}>
      <TableHeader>
        <TableRow>
          <TableHead className="sticky left-0 z-10 bg-background/90">Asset</TableHead>
          {assets.map((asset) => (
            <TableHead key={asset} className="text-center">
              {asset}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {assets.map((rowAsset, rowIdx) => (
          <TableRow key={rowAsset}>
            <TableCell className="sticky left-0 z-10 bg-background/90">
              <div className="font-semibold text-foreground">{rowAsset}</div>
            </TableCell>
            {assets.map((colAsset, colIdx) => {
              const corr = matrix[rowIdx]?.[colIdx] ?? 0;
              return (
                <TableCell key={`${rowAsset}-${colAsset}`} className="text-center text-xs">
                  <span
                    className="inline-flex min-w-16 justify-center rounded-md px-2 py-1 font-medium text-foreground"
                    style={cellStyle(corr)}
                  >
                    {corrFormatter.format(corr)}
                  </span>
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
      <caption className="mt-3 text-left text-xs text-muted-foreground">
        相关系数范围 [-1, +1]；颜色越深表示绝对值越高。绿色为正相关，红色为负相关。
      </caption>
    </Table>
  );
}

export function formatCorrAsPct(value: number): string {
  return `${pctFormatter.format(value * 100)}%`;
}
