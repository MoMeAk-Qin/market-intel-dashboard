import './globals.css';
import { Space_Grotesk, Source_Serif_4 } from 'next/font/google';
import { Providers } from './providers';
import { SiteHeader } from '@/components/site-header';
import { cn } from '@/lib/utils';

const space = Space_Grotesk({ subsets: ['latin'], variable: '--font-sans' });
const serif = Source_Serif_4({ subsets: ['latin'], variable: '--font-serif' });

export const metadata = {
  title: 'Market Intel Dashboard',
  description: 'HK, US, FX, metals, and rates market analysis system.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={cn('min-h-screen text-slate-900 antialiased', space.variable, serif.variable)}>
        <Providers>
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
