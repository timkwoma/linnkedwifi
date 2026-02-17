const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function buildHeaders(token?: string, hasJsonBody = false): HeadersInit {
  const headers: Record<string, string> = {};
  if (hasJsonBody) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function parseErrorMessage(res: Response): Promise<string> {
  const text = await res.text();
  return text || `Request failed (${res.status})`;
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: buildHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorMessage(res));
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: buildHeaders(token, true),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorMessage(res));
  return (await res.json()) as T;
}

export async function apiPatch<T>(path: string, body: unknown, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: buildHeaders(token, true),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorMessage(res));
  return (await res.json()) as T;
}

export async function apiDelete<T>(path: string, token?: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  if (!res.ok) throw new ApiError(res.status, await parseErrorMessage(res));
  return (await res.json()) as T;
}

export function getStoredToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("linkedwifi_token") ?? "";
}

export function getStoredTenantId(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("linkedwifi_tenant_id") ?? "";
}

export function clearStoredAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("linkedwifi_token");
  localStorage.removeItem("linkedwifi_tenant_id");
}
