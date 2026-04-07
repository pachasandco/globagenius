const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

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
  return fetchAPI<{ packages: Package[] }>(
    `/api/packages?min_score=${minScore}&limit=${limit}`
  );
}

export function getPackage(id: string) {
  return fetchAPI<Package>(`/api/packages/${id}`);
}

export function getQualifiedItems(type = "", limit = 20) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (type) params.set("type_filter", type);
  return fetchAPI<{ items: QualifiedItem[] }>(
    `/api/qualified-items?${params}`
  );
}

export function getPipelineStatus() {
  return fetchAPI<PipelineStatus>("/api/status");
}

export function getHealth() {
  return fetchAPI<{ status: string; timestamp: string }>("/health");
}
