import Link from 'next/link';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: '总览' },
  { href: '/events', label: '事件中心' },
  { href: '/news', label: '今日新闻' },
  { href: '/daily-summary', label: '日报摘要' },
  { href: '/search', label: '问答分析' },
  { href: '/research', label: '研究工作台' },
];

export const SiteHeader = () => (
  <header className="sticky top-3 z-40 px-4">
    <div className="mx-auto flex max-w-6xl items-center justify-between rounded-2xl border border-white/10 bg-slate-950/70 px-6 py-4 backdrop-blur-xl">
      <Link
        href="/"
        className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 flex items-center gap-3 text-base font-semibold text-slate-100"
      >
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/40 bg-cyan-300/15 text-sm font-semibold text-cyan-100">
          MI
        </span>
        <span className="leading-tight">
          Market Intel
          <span className="block text-[11px] font-medium uppercase tracking-[0.2em] text-slate-400">
            Dashboard
          </span>
        </span>
      </Link>
      <nav className="hidden items-center gap-2 text-sm font-medium text-slate-300 lg:flex">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'cursor-pointer rounded-full border border-transparent px-3 py-1.5 transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950',
              'hover:border-cyan-300/40 hover:bg-cyan-300/10 hover:text-cyan-100',
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <Link
        href="/events"
        className="cursor-pointer rounded-full border border-emerald-300/40 bg-emerald-300/20 px-4 py-2 text-sm font-semibold text-emerald-100 transition duration-200 hover:bg-emerald-300/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
      >
        打开事件流
      </Link>
    </div>
    <nav className="mx-auto mt-3 flex max-w-6xl items-center gap-2 overflow-x-auto px-1 pb-1 text-sm font-medium text-slate-300 lg:hidden">
      {navItems.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            'cursor-pointer whitespace-nowrap rounded-full border border-transparent px-3 py-1.5 transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950',
            'hover:border-cyan-300/40 hover:bg-cyan-300/10 hover:text-cyan-100',
          )}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  </header>
);
