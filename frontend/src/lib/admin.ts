const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  tier: "free" | "premium";
  min_discount: number;
  stripe_customer_id: string | null;
  telegram_connected: boolean;
  has_grant: boolean;
  grant_expires_at: string | null;
  is_admin: boolean;
}

function adminKey(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("gg_admin_key") || "";
}

async function adminFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const key = adminKey();
  const res = await fetch(`${API_URL}${path}`, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      "X-Admin-Key": key,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const listUsers = () =>
  adminFetch<{ items: AdminUser[]; count: number }>("/api/admin/users");

export const getUser = (id: string) =>
  adminFetch<{ user: unknown; preferences: unknown; grants: unknown[]; tier: string }>(
    `/api/admin/users/${id}`
  );

export const grantPremium = (
  id: string,
  expires_at?: string | null,
  reason?: string | null
) =>
  adminFetch(`/api/admin/users/${id}/premium`, {
    method: "PUT",
    body: JSON.stringify({
      expires_at: expires_at || null,
      reason: reason || null,
    }),
  });

export const revokePremium = (id: string) =>
  adminFetch(`/api/admin/users/${id}/premium`, { method: "DELETE" });

export const updateMinDiscount = (id: string, value: number) =>
  adminFetch(`/api/admin/users/${id}/min_discount`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });

export const resetPrefs = (id: string) =>
  adminFetch(`/api/admin/users/${id}/reset_prefs`, { method: "POST" });

export function setAdminKey(key: string) {
  sessionStorage.setItem("gg_admin_key", key);
}

export function hasAdminKey(): boolean {
  return !!adminKey();
}
