const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function _getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("gg_token");
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = _getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ─── Auth ───

function _setSessionCookie() {
  if (typeof document !== "undefined") {
    document.cookie = "gg_session=1; path=/; SameSite=Lax; max-age=2592000";
  }
}

export function clearSessionCookie() {
  if (typeof document !== "undefined") {
    document.cookie = "gg_session=; path=/; max-age=0";
  }
}

export async function signup(email: string, password: string) {
  const res = await fetchAPI<{ user_id: string; email: string; token: string }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  _setSessionCookie();
  return res;
}

export async function login(email: string, password: string) {
  const res = await fetchAPI<{ user_id: string; email: string; token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  _setSessionCookie();
  return res;
}

export function changePassword(userId: string, currentPassword: string, newPassword: string) {
  return fetchAPI<{ message: string }>(`/api/users/${userId}/password`, {
    method: "PUT",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

// ─── Preferences ───

export interface UserPreferences {
  id: string;
  user_id: string;
  airport_codes: string[];
  offer_types: string[];
  min_discount: number;
  max_budget: number | null;
  preferred_destinations: string[] | null;
  telegram_connected: boolean;
  telegram_chat_id: number | null;
  notifications_enabled: boolean;
  deal_tier: string;
  blocked_destinations: string[];
}

export function getPreferences(userId: string) {
  return fetchAPI<UserPreferences>(`/api/users/${userId}/preferences`);
}

export function updatePreferences(userId: string, prefs: {
  airport_codes: string[];
  offer_types: string[];
  max_budget?: number | null;
  preferred_destinations?: string[] | null;
  deal_tier?: string;
  blocked_destinations?: string[];
}) {
  return fetchAPI<UserPreferences>(`/api/users/${userId}/preferences`, {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

// ─── Telegram ───

export function generateTelegramLink(userId: string) {
  return fetchAPI<{ link: string; token: string }>(`/api/users/${userId}/telegram/generate-link`, {
    method: "POST",
  });
}

export function getTelegramStatus(userId: string) {
  return fetchAPI<{ connected: boolean; chat_id: number | null }>(`/api/users/${userId}/telegram/status`);
}

// ─── Deals ───

/**
 * A flight-only deal as returned by GET /api/packages?plan=free|premium.
 * Enriched with raw_flights info server-side. Sensitive fields
 * (price, baseline_price, source_url) are nullified when the caller
 * doesn't have access — see `locked`.
 *
 * Locking rules (server-side, NOT bypass-able from the frontend):
 * - Anonymous (no JWT): all deals locked
 * - Authenticated free user: free-tier deals unlocked, premium-tier locked
 * - Authenticated premium user: all deals unlocked
 */
export interface FlightDeal {
  id: string;
  tier: "free" | "premium";
  discount_pct: number;
  score: number;
  created_at: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string;
  airline: string | null;
  stops: number;
  trip_duration_days: number | null;
  duration_minutes: number | null;
  // Nullable when locked
  price: number | null;
  baseline_price: number | null;
  source_url: string | null;
  locked: boolean;
}

export interface PipelineStatus {
  status: string;
  recent_scrapes: Array<{
    id: string;
    source: string;
    type: string;
    items_count: number;
    errors_count: number;
    status: string;
    started_at: string;
  }>;
  active_baselines: number;
}

export function getFlightDeals(
  plan: "free" | "premium" = "free",
  limit = 20,
  minScore = 0,
  minDiscount = 0
) {
  return fetchAPI<{ items: FlightDeal[]; plan: string }>(
    `/api/packages?min_score=${minScore}&limit=${limit}&plan=${plan}&min_discount=${minDiscount}`
  );
}

export function getPipelineStatus() {
  return fetchAPI<PipelineStatus>("/api/status");
}
