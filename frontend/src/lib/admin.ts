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
  return localStorage.getItem("gg_admin_key") || "";
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

// updateMinDiscount removed in v10 — admin override of user-controlled
// min_discount caused silent overrides of profile choices. The backend
// endpoint is gone too.

export const resetPrefs = (id: string) =>
  adminFetch(`/api/admin/users/${id}/reset_prefs`, { method: "POST" });

export const deleteUser = (id: string, confirmEmail: string) =>
  adminFetch<{ ok: boolean; deleted_id: string; deleted_email: string }>(
    `/api/admin/users/${id}`,
    {
      method: "DELETE",
      body: JSON.stringify({ confirm_email: confirmEmail }),
    }
  );

export interface FeedbackItem {
  user_email: string;
  user_id: string | null;
  destination: string | null;
  alert_type: string | null;
  price: number | null;
  discount_pct: number | null;
  feedback: "good" | "bad" | "too_late";
  feedback_at: string;
  message_id: string;
  sent_at: string;
}

export interface FeedbackResponse {
  items: FeedbackItem[];
  total_clicks: number;
  distinct_users: number;
  by_type: Record<string, number>;
  days_window: number;
}

export const listFeedback = (days = 30, limit = 200) =>
  adminFetch<FeedbackResponse>(`/api/admin/feedback?days=${days}&limit=${limit}`);

export interface BroadcastResult {
  ok: boolean;
  mode?: "test" | "send";
  recipients?: number;
  delivered?: number;
  failed?: number;
  // On a 409 confirmation-required response, the backend tells us the
  // real recipient count to echo back via confirm_count.
  needsConfirm?: boolean;
  detail?: string;
}

/**
 * Send a Telegram broadcast.
 * - mode "test": delivers only to the admin's own chat (preview).
 * - mode "send": real broadcast; the backend returns HTTP 409 with the
 *   live recipient count until confirm_count matches it (fat-finger guard).
 */
export async function broadcastMessage(
  message: string,
  mode: "test" | "send",
  confirmCount?: number
): Promise<BroadcastResult> {
  const res = await fetch(`${API_URL}/api/admin/broadcast`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey(), "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode, confirm_count: confirmCount ?? null }),
  });
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}));
    return { ok: false, needsConfirm: true, detail: body.detail || "Confirmation requise" };
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return { ok: false, detail: body.detail || `HTTP ${res.status}` };
  }
  return { ok: true, ...(await res.json()) };
}

export function setAdminKey(key: string) {
  localStorage.setItem("gg_admin_key", key);
}

export function hasAdminKey(): boolean {
  return !!adminKey();
}
