import './globals.css';
import { Providers } from './providers';
import { SiteHeader } from '@/components/site-header';

export const metadata = {
  title: 'Market Intel Dashboard',
  description: '跨市场事件、今日新闻、问答分析与日报摘要工作台。',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen text-slate-100 antialiased">
        <Providers>
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
