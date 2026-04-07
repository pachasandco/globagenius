const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ─── Auth ───

export function signup(email: string) {
  return fetchAPI<{ user_id: string; email: string }>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function login(email: string) {
  return fetchAPI<{ user_id: string; email: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

// ─── Preferences ───

export interface UserPreferences {
  id: string;
  user_id: string;
  airport_code: string;
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
  airport_code: string;
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

// ─── Packages ───

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
}

export interface QualifiedItem {
  id: string;
  type: "flight" | "accommodation";
  item_id: string;
  price: number;
  baseline_price: number;
  discount_pct: number;
  score: number;
  status: string;
  created_at: string;
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

export function getPackages(minScore = 0, limit = 20) {
  return fetchAPI<{ packages: Package[] }>(`/api/packages?min_score=${minScore}&limit=${limit}`);
}

export function getPackage(id: string) {
  return fetchAPI<Package>(`/api/packages/${id}`);
}

export function getQualifiedItems(type = "", limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (type) params.set("type_filter", type);
  return fetchAPI<{ items: QualifiedItem[] }>(`/api/qualified-items?${params}`);
}

export function getPipelineStatus() {
  return fetchAPI<PipelineStatus>("/api/status");
}
