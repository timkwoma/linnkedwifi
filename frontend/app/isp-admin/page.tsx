"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  ApiError,
  apiGet,
  apiPatch,
  apiPost,
  clearStoredAuth,
  getStoredTenantId,
  getStoredToken,
} from "../../lib/api";

type Stats = {
  users: number;
  packages: number;
  payments_total: number;
  active_sessions: number;
  open_tickets: number;
};

type Device = {
  device_id: string;
  name: string;
  ip: string;
  status: string;
};

export default function ISPAdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState("");
  const [packageForm, setPackageForm] = useState({
    name: "",
    duration_minutes: 60,
    speed_limit_rx: 5000,
    speed_limit_tx: 2000,
    price: 20,
    category: "hotspot",
  });

  async function load() {
    const token = getStoredToken();
    const tenantId = getStoredTenantId();
    if (!tenantId) throw new Error("Missing tenant id. Login again.");
    const [s, d] = await Promise.all([
      apiGet<Stats>(`/ispadmin/stats?tenant_id=${tenantId}`, token),
      apiGet<Device[]>(`/devices?tenant_id=${tenantId}`, token),
    ]);
    setStats(s);
    setDevices(d);
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

  async function createPackage() {
    setError("");
    try {
      const tenantId = getStoredTenantId();
      if (!tenantId) throw new Error("Missing tenant id. Login again.");
      await apiPost(`/ispadmin/packages?tenant_id=${tenantId}`, packageForm, getStoredToken());
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function changeDeviceStatus(deviceId: string, status: string) {
    setError("");
    try {
      await apiPatch(`/devices/${deviceId}/status`, { status }, getStoredToken());
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const revenueData = [
    { name: "Mon", value: Math.round((stats?.payments_total ?? 0) * 0.12) },
    { name: "Tue", value: Math.round((stats?.payments_total ?? 0) * 0.14) },
    { name: "Wed", value: Math.round((stats?.payments_total ?? 0) * 0.18) },
    { name: "Thu", value: Math.round((stats?.payments_total ?? 0) * 0.2) },
    { name: "Fri", value: Math.round((stats?.payments_total ?? 0) * 0.16) },
    { name: "Sat", value: Math.round((stats?.payments_total ?? 0) * 0.1) },
    { name: "Sun", value: Math.round((stats?.payments_total ?? 0) * 0.1) },
  ];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="font-display text-4xl font-bold">ISP Admin Dashboard</h1>
      {error && <p className="mt-3 rounded-xl bg-red-100 p-3 text-red-700">{error}</p>}

      <section className="mt-6 grid gap-4 md:grid-cols-5">
        <article className="card"><p className="text-sm">Users</p><p className="text-3xl font-bold">{stats?.users ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Packages</p><p className="text-3xl font-bold">{stats?.packages ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Active Sessions</p><p className="text-3xl font-bold">{stats?.active_sessions ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Open Tickets</p><p className="text-3xl font-bold">{stats?.open_tickets ?? "-"}</p></article>
        <article className="card"><p className="text-sm">Revenue (KES)</p><p className="text-3xl font-bold">{stats?.payments_total ?? "-"}</p></article>
      </section>

      <section className="card mt-6 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={revenueData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Area type="monotone" dataKey="value" stroke="#f97316" fill="#fdba74" />
          </AreaChart>
        </ResponsiveContainer>
      </section>

      <section className="card mt-6">
        <h2 className="font-display text-2xl font-semibold">Create Package</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <input className="rounded-xl border border-slate-300 px-3 py-2" placeholder="Package Name" value={packageForm.name} onChange={(e) => setPackageForm({ ...packageForm, name: e.target.value })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" type="number" placeholder="Duration (minutes)" value={packageForm.duration_minutes} onChange={(e) => setPackageForm({ ...packageForm, duration_minutes: Number(e.target.value) })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" type="number" placeholder="Price" value={packageForm.price} onChange={(e) => setPackageForm({ ...packageForm, price: Number(e.target.value) })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" type="number" placeholder="RX Limit" value={packageForm.speed_limit_rx} onChange={(e) => setPackageForm({ ...packageForm, speed_limit_rx: Number(e.target.value) })} />
          <input className="rounded-xl border border-slate-300 px-3 py-2" type="number" placeholder="TX Limit" value={packageForm.speed_limit_tx} onChange={(e) => setPackageForm({ ...packageForm, speed_limit_tx: Number(e.target.value) })} />
          <select className="rounded-xl border border-slate-300 px-3 py-2" value={packageForm.category} onChange={(e) => setPackageForm({ ...packageForm, category: e.target.value })}>
            <option value="hotspot">hotspot</option>
            <option value="home">home</option>
          </select>
        </div>
        <button className="mt-3 rounded-xl bg-ink px-4 py-2 text-white" onClick={createPackage}>
          Create Package
        </button>
      </section>

      <section className="card mt-6">
        <h2 className="font-display text-2xl font-semibold">Routers / Devices</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">IP</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.device_id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{d.name}</td>
                  <td className="px-2 py-2">{d.ip}</td>
                  <td className="px-2 py-2">{d.status}</td>
                  <td className="px-2 py-2">
                    <select
                      className="rounded border border-slate-300 px-2 py-1"
                      value={d.status}
                      onChange={(e) => changeDeviceStatus(d.device_id, e.target.value)}
                    >
                      <option value="online">online</option>
                      <option value="offline">offline</option>
                      <option value="maintenance">maintenance</option>
                    </select>
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
