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

export function signup(email: string, password: string) {
  return fetchAPI<{ user_id: string; email: string; token: string }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return fetchAPI<{ user_id: string; email: string; token: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
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
}

export function getPreferences(userId: string) {
  return fetchAPI<UserPreferences>(`/api/users/${userId}/preferences`);
}

export function updatePreferences(userId: string, prefs: {
  airport_codes: string[];
  offer_types: string[];
  min_discount?: number;
  max_budget?: number | null;
  preferred_destinations?: string[] | null;
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
 * Enriched with raw_flights info server-side.
 */
export interface FlightDeal {
  id: string;
  tier: "free" | "premium";
  price: number;
  baseline_price: number;
  discount_pct: number;
  score: number;
  created_at: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string;
  airline: string | null;
  stops: number;
  source_url: string;
  trip_duration_days: number | null;
  duration_minutes: number | null;
}

/**
 * A vol+hotel package (legacy path, still used by GET /api/packages/{id}).
 * Not currently produced by the free/premium list endpoints — those return
 * FlightDeal only. Kept for backwards compatibility with the detail view.
 */
export interface Package {
  id: string;
  flight_id: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string;
  flight_price: number;
  accommodation_id: string;
  accommodation_price: number;
  total_price: number;
  baseline_total: number;
  discount_pct: number;
  score: number;
  status: string;
  created_at: string;
  expires_at: string;
  ai_description?: string;
  ai_reason?: string;
  ai_tip?: string;
  ai_tags?: string[];
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
  active_packages: number;
  active_baselines: number;
}

export function getFlightDeals(plan: "free" | "premium" = "free", limit = 20, minScore = 0) {
  return fetchAPI<{ items: FlightDeal[]; plan: string }>(
    `/api/packages?min_score=${minScore}&limit=${limit}&plan=${plan}`
  );
}

export function getPackage(id: string) {
  return fetchAPI<Package>(`/api/packages/${id}`);
}

export function getPipelineStatus() {
  return fetchAPI<PipelineStatus>("/api/status");
}
