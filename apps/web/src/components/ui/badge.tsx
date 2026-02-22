import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border border-transparent px-2.5 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-primary/35 bg-primary/20 text-primary',
        secondary: 'border-border bg-muted/50 text-muted-foreground',
        outline: 'border-border bg-transparent text-foreground',
        warning: 'border-amber-300/40 bg-amber-300/15 text-amber-100',
        success: 'border-emerald-300/40 bg-emerald-300/15 text-emerald-100',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = ({ className, variant, ...props }: BadgeProps) => (
  <div className={cn(badgeVariants({ variant }), className)} {...props} />
);

export { Badge, badgeVariants };
