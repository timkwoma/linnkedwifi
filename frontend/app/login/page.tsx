"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiPost } from "../../lib/api";

type Role = "super_admin" | "isp_admin" | "user";

export default function LoginPage() {
  const router = useRouter();
  const [role, setRole] = useState<Role>("isp_admin");
  const [tenantId, setTenantId] = useState("");
  const [phone, setPhone] = useState("+254700000002");
  const [code, setCode] = useState("");
  const [otpRequested, setOtpRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function requestOtp(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiPost<{ message: string; dev_otp: string }>("/auth/request-otp", {
          phone,
          role,
          tenant_id: role === "super_admin" ? null : tenantId || null,
      });
      setOtpRequested(true);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await apiPost<{ access_token: string; tenant_id: string | null }>(
        "/auth/verify-otp",
        {
          phone,
          role,
          tenant_id: role === "super_admin" ? null : tenantId || null,
          code,
        },
      );
      localStorage.setItem("linkedwifi_token", data.access_token);
      localStorage.setItem("linkedwifi_tenant_id", data.tenant_id ?? "");
      if (role === "super_admin") router.push("/super-admin");
      else router.push("/isp-admin");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-6 py-12">
      <section className="card">
        <h1 className="font-display text-3xl font-bold">Multi-tenant Login</h1>
        <p className="mt-2 text-slate-700">Phone + OTP authentication for Super-Admin, ISP Admin, and users.</p>

        <form onSubmit={otpRequested ? verifyOtp : requestOtp} className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-medium">Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
            >
              <option value="super_admin">Super-Admin</option>
              <option value="isp_admin">ISP Admin</option>
              <option value="user">User</option>
            </select>
          </label>

          {role !== "super_admin" && (
            <label className="block">
              <span className="text-sm font-medium">Tenant ID</span>
              <input
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                placeholder="UUID of tenant"
                required
              />
            </label>
          )}

          <label className="block">
            <span className="text-sm font-medium">Phone</span>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
              required
            />
          </label>

          {otpRequested && (
            <label className="block">
              <span className="text-sm font-medium">OTP Code</span>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2"
                required
              />
            </label>
          )}

          {error && <p className="rounded-xl bg-red-100 p-3 text-sm text-red-700">{error}</p>}

          <button
            disabled={loading}
            className="w-full rounded-xl bg-ink px-4 py-3 text-white disabled:opacity-60"
          >
            {loading ? "Please wait..." : otpRequested ? "Verify OTP" : "Request OTP"}
          </button>
        </form>
      </section>
    </main>
  );
}
