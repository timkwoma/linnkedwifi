"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { ApiError, apiDelete, apiGet, apiPost, clearStoredAuth, getStoredToken } from "../../lib/api";

type Stats = {
  tenants: number;
  accounts: number;
  payments_success: number;
  active_sessions: number;
};

type Tenant = {
  tenant_id: string;
  name: string;
  email: string;
  plan: string;
  active: boolean;
};

export default function SuperAdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    plan: "starter",
    admin_name: "",
    admin_phone: "",
    admin_email: "",
  });

  async function load() {
    const token = getStoredToken();
    const [s, t] = await Promise.all([
      apiGet<Stats>("/superadmin/stats", token),
      apiGet<Tenant[]>("/superadmin/tenants", token),
    ]);
    setStats(s);
    setTenants(t);
  }

  useEffect(() => {
    load()
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          clearStoredAuth();
          router.push("/login");
          return;
        }
        setError((e as Error).message);
      });
  }, [router]);

  async function createTenant() {
    setSaving(true);
    setError("");
    try {
      await apiPost(
        "/superadmin/tenants",
        { ...form, admin_email: form.admin_email || null },
        getStoredToken(),
      );
      setForm({
        name: "",
        email: "",
        plan: "starter",
        admin_name: "",
        admin_phone: "",
        admin_email: "",
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function deactivateTenant(tenantId: string) {
    setError("");
    try {
      await apiDelete(`/superadmin/tenants/${tenantId}`, getStoredToken());
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const chartData = [
    { name: "Tenants", value: stats?.tenants ?? 0 },
    { name: "Accounts", value: stats?.accounts ?? 0 },
    { name: "Sessions", value: stats?.active_sessions ?? 0 },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="font-display text-4xl font-bold">Super-Admin Dashboard</h1>
      {error && <p className="mt-3 rounded-xl bg-red-100 p-3 text-red-700">{error}</p>}

      <section className="mt-6 grid gap-4 md:grid-cols-4">
        <article className="card"><p className="text-sm">Tenants</p><p className="text-3xl font-bold">{stats?.tenants ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Accounts</p><p className="text-3xl font-bold">{stats?.accounts ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Payment Success</p><p className="text-3xl font-bold">{stats?.payments_success ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Active Sessions</p><p className="text-3xl font-bold">{stats?.active_sessions ?? "-"}</p></article>
      </section>

      <section className="card mt-6 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Bar dataKey="value" fill="#0891b2" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="card mt-6">
        <h2 className="font-display text-2xl font-semibold">Create Tenant</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Tenant Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Tenant Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Plan (starter/pro)" value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Admin Name" value={form.admin_name} onChange={(e) => setForm({ ...form, admin_name: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Admin Phone" value={form.admin_phone} onChange={(e) => setForm({ ...form, admin_phone: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Admin Email (optional)" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} />
        </div>
        <button className="mt-3 rounded-xl bg-ink px-4 py-2 text-white disabled:opacity-60" disabled={saving} onClick={createTenant}>
          {saving ? "Saving..." : "Create Tenant"}
        </button>
      </section>

      <section className="card mt-6">
        <h2 className="font-display text-2xl font-semibold">Tenants</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Email</th>
                <th className="px-2 py-2">Plan</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.tenant_id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{t.name}</td>
                  <td className="px-2 py-2">{t.email}</td>
                  <td className="px-2 py-2">{t.plan}</td>
                  <td className="px-2 py-2">{t.active ? "Active" : "Disabled"}</td>
                  <td className="px-2 py-2">
                    {t.active ? (
                      <button className="rounded-lg border border-slate-300 px-2 py-1 text-xs" onClick={() => deactivateTenant(t.tenant_id)}>
                        Deactivate
                      </button>
                    ) : (
                      <span className="text-xs text-slate-500">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
