import './globals.css';
import { Providers } from './providers';
import { SiteHeader } from '@/components/site-header';

export const metadata = {
  title: 'Cipher Wallet',
  description: 'Secure multi-chain crypto wallet with protected transaction preview.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-100 antialiased">
        <Providers>
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
