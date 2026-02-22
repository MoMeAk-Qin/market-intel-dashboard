'use client';

import { Toaster as Sonner, type ToasterProps } from 'sonner';

const Toaster = ({ ...props }: ToasterProps) => (
  <Sonner
    theme="dark"
    closeButton
    richColors
    toastOptions={{
      className: 'border border-border bg-popover text-popover-foreground',
    }}
    {...props}
  />
);

export { Toaster };
