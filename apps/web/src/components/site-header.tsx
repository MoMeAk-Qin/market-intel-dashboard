import Link from 'next/link';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Dashboard' },
  { href: '/events', label: 'Event Hub' },
  { href: '/research', label: 'Research' },
  { href: '/search', label: 'Search & Q&A' },
];

export const SiteHeader = () => (
  <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur">
    <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
      <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-slate-900">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-slate-900 text-sm font-semibold text-white">
          MI
        </span>
        Market Intel
      </Link>
      <nav className="flex items-center gap-4 text-sm font-medium text-slate-600">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn('transition-colors hover:text-slate-900')}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </div>
  </header>
);
