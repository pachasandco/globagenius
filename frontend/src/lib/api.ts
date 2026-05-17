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

export function forgotPassword(email: string) {
  return fetchAPI<{ ok: boolean }>("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, newPassword: string) {
  return fetchAPI<{ ok: boolean }>("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

// ─── Preferences ───

export type FlightTripType = "round_trip" | "one_way";

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
  flight_trip_types: FlightTripType[];
  include_split_tickets: boolean;
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
  flight_trip_types?: FlightTripType[];
  include_split_tickets?: boolean;
  // V9: premium-only discount floor (40/50/60). Null or omitted = no
  // change. Free users always pass null — the field has no effect for them.
  min_discount?: number | null;
}) {
  return fetchAPI<UserPreferences>(`/api/users/${userId}/preferences`, {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

export type CancellationReason =
  | "too_expensive"
  | "too_few_alerts"
  | "too_many_alerts"
  | "travelling_less"
  | "found_better"
  | "bugs"
  | "other"
  | "no_answer";

export async function cancelSubscription(
  survey?: { reason: CancellationReason; feedback?: string }
): Promise<{
  ok: boolean;
  had_subscription: boolean;
  cancelled: boolean;
}> {
  const token = typeof window !== "undefined" ? localStorage.getItem("gg_token") : "";
  const res = await fetch(`${API_URL}/api/users/me/cancel-subscription`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: survey ? JSON.stringify(survey) : undefined,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`);
  }
  return res.json();
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
  return_date: string | null;
  airline: string | null;
  stops: number;
  trip_duration_days: number | null;
  duration_minutes: number | null;
  trip_type: FlightTripType;
  direction: "outbound" | "inbound" | null;
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

// ─── Destination guides ───

export interface DestinationGuide {
  article: {
    id: string;
    iata: string;
    destination: string;
    slug: string;
    title: string;
    h1: string;
    meta_description: string;
    lead: string;
    nut_graf: string;
    top_picks: Array<{
      name: string;
      angle: string;
      description: string;
      practical: string;
    }>;
    // Legacy 3-day program — dropped in 2026-05, kept optional until
    // every article has been regenerated to the new format. Render
    // `neighborhoods` instead.
    itinerary?: Array<{
      day: number;
      title: string;
      morning: string;
      lunch: string;
      afternoon: string;
      evening: string;
      lodging: string;
      rain_plan: string;
      budget_option: string;
      premium_option: string;
    }> | null;
    neighborhoods?: Array<{
      name: string;
      character: string;
      description: string;
      highlights: string;
    }>;
    infos_pratiques: Record<string, string>;
    faq: Array<{ q: string; a: string }>;
    sources: string[];
    tags: string[];
    word_count: number;
    generated_at: string;
  };
  photo: {
    url: string;
    photographer_name: string;
    photographer_url: string;
  };
  deals: Array<{
    origin: string;
    destination: string;
    departure_date: string;
    return_date: string | null;
    price: number;
    baseline_price: number;
    discount_pct: number;
    airline: string | null;
    source_url: string | null;
    trip_type: string;
  }>;
}

export async function getDestinationGuide(iata: string): Promise<DestinationGuide | null> {
  const res = await fetch(`${API_URL}/api/destinations/${iata.toUpperCase()}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


// ─── Beta cohort counter ───

export interface BetaCount {
  founders_count: number;
  max_founders: number;
}

/**
 * Fetch the current beta-founder count. Used by the hero badge and
 * the /beta page to render "X / 100 places fondateurs prises".
 * Falls back to {0, 100} on network error so the page never crashes.
 */
export async function getBetaCount(): Promise<BetaCount> {
  try {
    const res = await fetch(`${API_URL}/api/stats/beta-count`, {
      cache: "no-store",
    });
    if (!res.ok) return { founders_count: 0, max_founders: 100 };
    return res.json();
  } catch {
    return { founders_count: 0, max_founders: 100 };
  }
}
