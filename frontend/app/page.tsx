import Link from "next/link";

const features = [
  "Multi-tenant ISP SaaS with Super-Admin and ISP Admin control",
  "Phone + OTP captive portal login with reconnect-aware sessions",
  "M-Pesa Paybill STK push with payment-to-session automation",
  "FreeRADIUS + MikroTik hotspot integration",
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <header className="card mb-8">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-cyan">LinkedWiFi Platform</p>
        <h1 className="font-display text-4xl font-bold md:text-6xl">Operate hotspot internet like a modern SaaS.</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-700">
          LINKEDWIFI unifies hotspot billing, session control, and router visibility for growing ISPs.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/login" className="rounded-xl bg-ink px-5 py-3 text-white">
            Launch Dashboard
          </Link>
          <a href="#pricing" className="rounded-xl border border-ink px-5 py-3">
            View Pricing
          </a>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {features.map((feature) => (
          <article key={feature} className="card">
            <p className="font-display text-xl font-semibold">{feature}</p>
          </article>
        ))}
      </section>

      <section id="pricing" className="mt-8 grid gap-4 md:grid-cols-3">
        <article className="card">
          <h3 className="font-display text-2xl font-semibold">Starter</h3>
          <p className="mt-2 text-slate-700">For single-location ISPs.</p>
          <p className="mt-4 text-3xl font-bold">KES 3,500/mo</p>
        </article>
        <article className="card border-cyan/50">
          <h3 className="font-display text-2xl font-semibold">Pro</h3>
          <p className="mt-2 text-slate-700">Multi-router growth setup.</p>
          <p className="mt-4 text-3xl font-bold">KES 8,900/mo</p>
        </article>
        <article className="card">
          <h3 className="font-display text-2xl font-semibold">Enterprise</h3>
          <p className="mt-2 text-slate-700">Custom tenancy and support.</p>
          <p className="mt-4 text-3xl font-bold">Custom</p>
        </article>
      </section>
    </main>
  );
}

