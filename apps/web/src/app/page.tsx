import Link from 'next/link';

type ChainInfo = {
  symbol: string;
  name: string;
  settlement: string;
  avgFee: string;
  bridge: string;
  status: string;
};

type SecurityFeature = {
  icon: 'vault' | 'radar' | 'recover';
  tag: string;
  title: string;
  description: string;
  points: string[];
};

type Snapshot = {
  title: string;
  subtitle: string;
  metric: string;
};

type Review = {
  name: string;
  role: string;
  quote: string;
  rating: string;
};

const chainCards: ChainInfo[] = [
  {
    symbol: 'ETH',
    name: 'Ethereum',
    settlement: '6.2s finality',
    avgFee: '$1.20',
    bridge: 'RouteGuard',
    status: 'Live',
  },
  {
    symbol: 'BTC',
    name: 'Bitcoin',
    settlement: '8.5m average',
    avgFee: '$2.05',
    bridge: 'Wrapped Channel',
    status: 'Live',
  },
  {
    symbol: 'SOL',
    name: 'Solana',
    settlement: '2.4s finality',
    avgFee: '$0.03',
    bridge: 'Native Rail',
    status: 'Live',
  },
  {
    symbol: 'ARB',
    name: 'Arbitrum',
    settlement: '4.1s finality',
    avgFee: '$0.12',
    bridge: 'Fast Exit',
    status: 'Live',
  },
];

const securityFeatures: SecurityFeature[] = [
  {
    icon: 'vault',
    tag: 'Hardware-grade Signing',
    title: 'MPC + passkey auth',
    description:
      'Private key shards are isolated across devices and secure enclaves, so no single point can expose full signing authority.',
    points: ['Biometric re-check for high-risk moves', 'Sharded keys never leave encrypted memory'],
  },
  {
    icon: 'radar',
    tag: 'Threat Intelligence',
    title: 'Real-time scam blocking',
    description:
      'Wallet screens contract bytecode, domain reputation, and token metadata in milliseconds before final confirmation.',
    points: ['Known drainer signature detection', 'Suspicious allowance and approval alerts'],
  },
  {
    icon: 'recover',
    tag: 'Recovery Control',
    title: 'Social + device recovery',
    description:
      'Recover access via trusted contacts and backup devices with configurable time-lock, geography rules, and emergency freeze.',
    points: ['Time-locked withdrawals for vault accounts', 'Optional travel mode and region locks'],
  },
];

const transactionPath = [
  {
    step: '01',
    title: 'Intent validation',
    detail: 'Simulates slippage, gas spikes, and route failures before any signature request.',
  },
  {
    step: '02',
    title: 'Route optimization',
    detail: 'Picks the fastest and cheapest bridge/swap path across trusted liquidity venues.',
  },
  {
    step: '03',
    title: 'Protected execution',
    detail: 'Submits through private relay to reduce sandwich attacks and mempool leakage.',
  },
];

const snapshots: Snapshot[] = [
  { title: 'Vault Home', subtitle: 'Portfolio + account isolation', metric: '$2.8M secured' },
  { title: 'Bridge Route', subtitle: 'MEV-shielded cross-chain swap', metric: '3.2s settlement' },
  { title: 'Risk Console', subtitle: 'Allowance and contract alerts', metric: '0 active threats' },
];

const reviews: Review[] = [
  {
    name: 'A. Chen',
    role: 'Treasury Lead, BlockRiver',
    quote: 'The preview engine catches risky approvals before anyone signs.',
    rating: '4.9',
  },
  {
    name: 'M. Patel',
    role: 'DeFi Ops, NorthGrid',
    quote: 'Cross-chain routing is faster than our previous custody flow.',
    rating: '4.8',
  },
  {
    name: 'R. Diaz',
    role: 'Founder, Delta Labs',
    quote: 'Recovery controls made governance-grade wallet policies practical.',
    rating: '4.9',
  },
];

const interactiveClass =
  'cursor-pointer transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950';

function SecurityIcon({ icon }: { icon: SecurityFeature['icon'] }) {
  if (icon === 'vault') {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-cyan-200" aria-hidden="true">
        <path
          d="M12 2 4 5v6c0 5.7 3.6 9.9 8 11 4.4-1.1 8-5.3 8-11V5l-8-3Zm0 5.5a2.5 2.5 0 0 1 2.5 2.5V12H9.5V10A2.5 2.5 0 0 1 12 7.5Zm-3.2 6h6.4v4.2H8.8v-4.2Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (icon === 'radar') {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-cyan-200" aria-hidden="true">
        <path
          d="M12 3a9 9 0 1 0 9 9h-2.2A6.8 6.8 0 1 1 12 5.2V3Zm0 4.2a4.8 4.8 0 1 0 4.8 4.8h-2.1a2.7 2.7 0 1 1-2.7-2.7V7.2Zm0 3.1a1.7 1.7 0 1 0 1.7 1.7A1.7 1.7 0 0 0 12 10.3Z"
          fill="currentColor"
        />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 text-cyan-200" aria-hidden="true">
      <path
        d="M12 2a7 7 0 0 0-7 7v2H3v3h2v2h2v4h10v-4h2v-2h2v-3h-2V9a7 7 0 0 0-7-7Zm-5 9V9a5 5 0 1 1 10 0v2H7Zm5 7.5a2.5 2.5 0 0 1-2.5-2.5h1.8a.7.7 0 0 0 1.4 0h1.8a2.5 2.5 0 0 1-2.5 2.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function WalletLandingPage() {
  return (
    <div className="relative space-y-8 pb-10 md:space-y-12 md:pb-14">
      <section className="fade-up relative overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(140deg,rgba(19,29,50,0.95)_0%,rgba(9,13,25,0.88)_50%,rgba(5,9,19,0.82)_100%)] p-6 shadow-[0_30px_110px_-38px_rgba(16,185,129,0.55)] md:p-10">
        <div className="pointer-events-none absolute -top-16 right-8 h-60 w-60 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-8 h-64 w-64 rounded-full bg-emerald-400/20 blur-3xl" />
        <div className="relative grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-center">
          <div className="space-y-6">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-4 py-1.5 text-xs font-medium uppercase tracking-[0.2em] text-emerald-200">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,1)]" />
              Trusted by 1.8M+ holders
            </span>
            <div className="space-y-4">
              <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-slate-50 md:text-5xl">
                The secure multi-chain wallet built for high-value moves.
              </h1>
              <p className="max-w-xl text-base leading-relaxed text-slate-300/90">
                Cipher Wallet combines dark-glass controls, transaction simulation, and adaptive defense to keep every transfer auditable and protected.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/#download"
                className={`${interactiveClass} rounded-full border border-emerald-300/40 bg-emerald-300/20 px-5 py-2.5 text-sm font-semibold text-emerald-100 hover:bg-emerald-300/30`}
              >
                Download Wallet
              </Link>
              <Link
                href="/#security"
                className={`${interactiveClass} rounded-full border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-semibold text-slate-100 hover:border-cyan-300/60 hover:bg-cyan-400/10`}
              >
                View Security Model
              </Link>
            </div>
            <div className="grid gap-3 text-sm text-slate-200/90 sm:grid-cols-3">
              <div className="glass-panel rounded-2xl px-4 py-3">
                <p className="text-xl font-semibold text-white">128+</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-300">Chains & L2s</p>
              </div>
              <div className="glass-panel rounded-2xl px-4 py-3">
                <p className="text-xl font-semibold text-white">$14.2B</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-300">Monthly Volume</p>
              </div>
              <div className="glass-panel rounded-2xl px-4 py-3">
                <p className="text-xl font-semibold text-white">24/7</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-300">Risk Monitoring</p>
              </div>
            </div>
            <div className="glass-panel rounded-2xl px-4 py-3 text-sm text-slate-200/90">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-100">App score</p>
                <p className="text-sm font-semibold text-amber-300">4.9 / 5.0</p>
              </div>
              <p className="mt-1 text-xs text-slate-300">Based on 18,420 verified reviews from high-frequency and retail wallet users.</p>
            </div>
          </div>

          <aside className="glass-panel fade-up-delayed rounded-3xl border border-cyan-300/20 p-5 md:p-6">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-cyan-200/90">
              <span>Transaction Preview</span>
              <span className="rounded-full border border-cyan-300/40 bg-cyan-300/10 px-2 py-1">Secure Route</span>
            </div>
            <div className="mt-5 space-y-3 text-sm text-slate-200/90">
              <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">From</p>
                <p className="mt-1 font-medium text-slate-100">0x8a4c...2f74 (Main Vault)</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-400">To</p>
                <p className="mt-1 font-medium text-slate-100">SOL Treasury / Bridge Channel 03</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Network Fee</p>
                  <p className="mt-1 font-medium text-slate-100">$0.41</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-slate-950/55 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">MEV Shield</p>
                  <p className="mt-1 font-medium text-emerald-200">Enabled</p>
                </div>
              </div>
            </div>
            <div className="mt-5 rounded-2xl border border-emerald-300/25 bg-emerald-300/10 p-4">
              <p className="text-xs uppercase tracking-wide text-emerald-200/90">Expected receive</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-100">12.487 SOL</p>
              <p className="mt-1 text-xs text-emerald-100/80">Estimated settlement in 3.2 seconds after signature.</p>
            </div>
            <button
              type="button"
              className={`${interactiveClass} mt-5 w-full rounded-xl border border-emerald-300/35 bg-emerald-300/20 px-4 py-3 text-sm font-semibold text-emerald-100 hover:bg-emerald-300/30`}
            >
              Confirm with Face ID
            </button>
          </aside>
        </div>
      </section>

      <section id="chains" className="fade-up space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Multi-chain support</p>
          <h2 className="text-2xl font-semibold text-slate-100 md:text-3xl">One wallet, optimized routes across major ecosystems.</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {chainCards.map((chain) => (
            <article key={chain.symbol} className="glass-panel rounded-3xl p-4">
              <div className="flex items-start justify-between">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/35 bg-cyan-300/10 text-sm font-semibold text-cyan-100">
                  {chain.symbol}
                </span>
                <span className="rounded-full border border-emerald-300/35 bg-emerald-300/10 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-emerald-200">
                  {chain.status}
                </span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-slate-100">{chain.name}</h3>
              <p className="mt-1 text-sm text-slate-300">Settlement {chain.settlement}</p>
              <p className="mt-1 text-sm text-slate-300">Average fee {chain.avgFee}</p>
              <p className="mt-1 text-sm text-slate-300">Bridge {chain.bridge}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="security" className="fade-up space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Security features</p>
          <h2 className="text-2xl font-semibold text-slate-100 md:text-3xl">Defense-in-depth designed for crypto-native threat models.</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {securityFeatures.map((feature) => (
            <article key={feature.title} className="glass-panel rounded-3xl p-5">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/40 bg-cyan-300/10">
                <SecurityIcon icon={feature.icon} />
              </div>
              <p className="text-xs uppercase tracking-[0.15em] text-cyan-200/80">{feature.tag}</p>
              <h3 className="mt-3 text-xl font-semibold text-slate-100">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-300/95">{feature.description}</p>
              <ul className="mt-4 space-y-2 text-sm text-slate-200/90">
                {feature.points.map((point) => (
                  <li key={point} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-emerald-300" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section id="preview" className="fade-up grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Execution flow</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-100">Protected transaction path</h2>
          <div className="mt-5 space-y-3">
            {transactionPath.map((item) => (
              <div key={item.step} className="rounded-2xl border border-white/10 bg-slate-950/45 p-4">
                <div className="flex items-center gap-3">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/45 text-xs font-semibold text-cyan-100">
                    {item.step}
                  </span>
                  <h3 className="text-base font-semibold text-slate-100">{item.title}</h3>
                </div>
                <p className="mt-2 text-sm text-slate-300/90">{item.detail}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Live risk score</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-100">Preview before signing</h2>
          <div className="mt-4 space-y-3 text-sm">
            <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-3 text-slate-200">
              Route confidence: <span className="font-semibold text-emerald-200">98.7%</span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-3 text-slate-200">
              Slippage tolerance: <span className="font-semibold text-slate-100">0.18%</span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-3 text-slate-200">
              Contract risk grade: <span className="font-semibold text-emerald-200">A</span>
            </div>
            <div className="rounded-2xl border border-white/10 bg-slate-950/45 p-3 text-slate-200">
              Sandbox simulation: <span className="font-semibold text-emerald-200">Pass</span>
            </div>
          </div>
          <button
            type="button"
            className={`${interactiveClass} mt-5 w-full rounded-xl border border-cyan-300/35 bg-cyan-300/15 px-4 py-3 text-sm font-semibold text-cyan-100 hover:bg-cyan-300/25`}
          >
            Start Secure Transfer
          </button>
        </article>
      </section>

      <section id="proof" className="fade-up space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Product snapshots</p>
          <h2 className="text-2xl font-semibold text-slate-100 md:text-3xl">Real UI states before you install.</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {snapshots.map((snapshot) => (
            <article key={snapshot.title} className="glass-panel rounded-3xl p-4">
              <div className="mb-4 h-36 rounded-2xl border border-white/10 bg-[linear-gradient(140deg,rgba(8,47,73,0.35),rgba(15,23,42,0.7),rgba(6,95,70,0.3))] p-3">
                <div className="rounded-xl border border-white/10 bg-slate-900/55 px-3 py-2 text-xs text-slate-300">
                  {snapshot.subtitle}
                </div>
                <div className="mt-3 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-3 py-2 text-sm font-semibold text-cyan-100">
                  {snapshot.metric}
                </div>
              </div>
              <h3 className="text-base font-semibold text-slate-100">{snapshot.title}</h3>
              <p className="mt-1 text-sm text-slate-300">{snapshot.subtitle}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="fade-up space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/80">Social proof</p>
          <h2 className="text-2xl font-semibold text-slate-100 md:text-3xl">Teams trust Cipher Wallet in production.</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {reviews.map((review) => (
            <article key={review.name} className="glass-panel rounded-3xl p-5">
              <p className="text-sm text-slate-200/95">&ldquo;{review.quote}&rdquo;</p>
              <p className="mt-4 text-sm font-semibold text-slate-100">{review.name}</p>
              <p className="mt-1 text-xs text-slate-400">{review.role}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.2em] text-amber-300">Rating {review.rating}</p>
            </article>
          ))}
        </div>
      </section>

      <section
        id="download"
        className="fade-up relative overflow-hidden rounded-[1.75rem] border border-emerald-300/25 bg-[linear-gradient(135deg,rgba(6,95,70,0.32),rgba(15,23,42,0.78),rgba(8,47,73,0.36))] px-6 py-8 text-center md:px-10"
      >
        <div className="pointer-events-none absolute left-1/2 top-0 h-36 w-36 -translate-x-1/2 rounded-full bg-emerald-300/20 blur-3xl" />
        <div className="relative mx-auto max-w-2xl space-y-3">
          <p className="text-xs uppercase tracking-[0.2em] text-emerald-100/80">Download now</p>
          <h2 className="text-2xl font-semibold text-slate-50 md:text-3xl">Take Cipher Wallet on every device.</h2>
          <p className="text-sm text-slate-200/90">
            Sync your vaults across mobile and desktop with encrypted cloud state and device-bound authentication.
          </p>
          <div className="mx-auto mt-2 flex h-24 w-24 items-center justify-center rounded-2xl border border-white/20 bg-white/10 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-200">
            QR Install
          </div>
          <div className="flex flex-wrap justify-center gap-3 pt-2">
            <Link
              href="#"
              className={`${interactiveClass} rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-semibold text-slate-100 hover:border-emerald-300/60 hover:bg-emerald-300/20`}
            >
              iOS Download
            </Link>
            <Link
              href="#"
              className={`${interactiveClass} rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-semibold text-slate-100 hover:border-emerald-300/60 hover:bg-emerald-300/20`}
            >
              Android Download
            </Link>
            <Link
              href="#"
              className={`${interactiveClass} rounded-full border border-white/20 bg-white/10 px-5 py-2.5 text-sm font-semibold text-slate-100 hover:border-emerald-300/60 hover:bg-emerald-300/20`}
            >
              Desktop App
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
