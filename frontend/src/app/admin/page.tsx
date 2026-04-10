"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ScrapeLog {
  id: string;
  type: string;
  source: string;
  items_count: number;
  errors_count: number;
  status: string;
  started_at: string;
  duration_ms: number;
}

interface DebugData {
  flights_sample: Array<{ origin: string; destination: string; departure_date: string; price: number }>;
  accommodations_sample: Array<{ city: string; name: string; total_price: number; check_in: string }>;
  baselines_sample: Array<{ route_key: string; avg_price: number; std_dev: number; sample_count: number }>;
  price_diagnosis: Array<{ route: string; price: number; baseline_avg: number; discount_pct: number; z_score: number; would_qualify: boolean }>;
  flight_date_keys: string[];
  accommodation_date_keys: string[];
}

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [status, setStatus] = useState<{ active_baselines: number; active_packages: number; recent_scrapes: ScrapeLog[] } | null>(null);
  const [debug, setDebug] = useState<DebugData | null>(null);
  const [loading, setLoading] = useState(false);
  const [triggerResult, setTriggerResult] = useState("");
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem("gg_admin_key");
    if (saved) {
      setAdminKey(saved);
      setAuthenticated(true);
      loadData(saved);
    }
  }, []);

  async function loadData(key: string) {
    setLoading(true);
    try {
      const [statusRes, debugRes] = await Promise.all([
        fetch(`${API_URL}/api/status`).then(r => r.json()),
        fetch(`${API_URL}/api/debug/data`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
      ]);
      setStatus(statusRes);
      if (!debugRes.detail) setDebug(debugRes);
    } catch { /* ignore */ }
    setLoading(false);
  }

  function handleLogin() {
    localStorage.setItem("gg_admin_key", adminKey);
    setAuthenticated(true);
    loadData(adminKey);
  }

  async function triggerJob(job: string) {
    setTriggerResult(`Triggering ${job}...`);
    try {
      const res = await fetch(`${API_URL}/api/trigger/${job}`, {
        method: "POST",
        headers: { "X-Admin-Key": adminKey },
      });
      const data = await res.json();
      setTriggerResult(data.detail || `${job} triggered`);
    } catch (e) {
      setTriggerResult(`Error: ${e}`);
    }
  }

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-white rounded-2xl border border-gray-100 p-8">
          <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl text-center mb-6">Admin Globe Genius</h1>
          <input
            type="password"
            value={adminKey}
            onChange={e => setAdminKey(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            placeholder="Admin API Key"
            className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 outline-none text-sm mb-4"
          />
          <button onClick={handleLogin} className="w-full bg-gray-900 text-white font-semibold py-3 rounded-xl">
            Acceder
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 h-[64px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500 flex items-center justify-center text-white font-bold text-sm">A</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Admin</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/home" className="text-sm text-gray-500 hover:text-gray-900">Home</Link>
            <button onClick={() => loadData(adminKey)} className="text-sm text-cyan-600 font-medium">Refresh</button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Pipeline Status */}
        {status && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="text-3xl font-bold">{status.active_packages}</div>
              <div className="text-xs text-gray-400">Packages actifs</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="text-3xl font-bold">{status.active_baselines}</div>
              <div className="text-xs text-gray-400">Baselines</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="text-3xl font-bold">{(status.recent_scrapes || []).length}</div>
              <div className="text-xs text-gray-400">Scrapes recents</div>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-4 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
              <span className="text-sm font-medium">Pipeline actif</span>
            </div>
          </div>
        )}

        {/* Trigger buttons */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
          <h2 className="font-semibold mb-3">Trigger manuels</h2>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => triggerJob("scrape_flights")} className="bg-cyan-500 text-white text-sm px-4 py-2 rounded-lg hover:bg-cyan-600">Scrape Vols</button>
            <button onClick={() => triggerJob("scrape_accommodations")} className="bg-cyan-500 text-white text-sm px-4 py-2 rounded-lg hover:bg-cyan-600">Scrape Hotels</button>
            <button onClick={() => triggerJob("recalculate_baselines")} className="bg-amber-500 text-white text-sm px-4 py-2 rounded-lg hover:bg-amber-600">Recalc Baselines</button>
            <button onClick={() => triggerJob("expire_stale_data")} className="bg-gray-500 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-600">Expire Data</button>
          </div>
          {triggerResult && <div className="mt-2 text-xs text-gray-500">{triggerResult}</div>}
        </div>

        {/* Scrape logs */}
        {status?.recent_scrapes && (
          <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
            <h2 className="font-semibold mb-3">Scrape Logs</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                    <th className="pb-2">Date</th>
                    <th className="pb-2">Type</th>
                    <th className="pb-2">Items</th>
                    <th className="pb-2">Erreurs</th>
                    <th className="pb-2">Duree</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {status.recent_scrapes.map(s => (
                    <tr key={s.id} className="border-b border-gray-50">
                      <td className="py-2 text-xs">{new Date(s.started_at).toLocaleString("fr-FR")}</td>
                      <td className="py-2">{s.type}</td>
                      <td className="py-2 font-bold">{s.items_count}</td>
                      <td className="py-2">{s.errors_count > 0 ? <span className="text-red-500">{s.errors_count}</span> : "0"}</td>
                      <td className="py-2 text-xs">{s.duration_ms ? `${Math.round(s.duration_ms / 1000)}s` : "-"}</td>
                      <td className="py-2"><span className={`text-xs px-2 py-0.5 rounded-full ${s.status === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>{s.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Debug data */}
        {debug && (
          <>
            {/* Price diagnosis */}
            <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
              <h2 className="font-semibold mb-3">Diagnostic prix</h2>
              {debug.price_diagnosis.length === 0 ? (
                <p className="text-sm text-gray-400">Aucun diagnostic disponible</p>
              ) : (
                <div className="space-y-1">
                  {debug.price_diagnosis.map((p, i) => (
                    <div key={i} className={`flex items-center gap-3 text-sm py-1 ${p.would_qualify ? "text-green-700" : "text-gray-500"}`}>
                      <span className="text-lg">{p.would_qualify ? "✅" : "❌"}</span>
                      <span className="font-medium w-24">{p.route}</span>
                      <span>{p.price}€</span>
                      <span className="text-gray-300">vs</span>
                      <span>{p.baseline_avg}€</span>
                      <span className={p.discount_pct > 0 ? "text-green-600 font-bold" : "text-red-400"}>
                        {p.discount_pct > 0 ? "-" : "+"}{Math.abs(p.discount_pct)}%
                      </span>
                      <span className="text-xs text-gray-300">z={p.z_score}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Baselines */}
            <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
              <h2 className="font-semibold mb-3">Baselines ({debug.baselines_sample.length})</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {debug.baselines_sample.map(b => (
                  <div key={b.route_key} className="bg-gray-50 rounded-lg p-2 text-sm">
                    <div className="font-medium">{b.route_key}</div>
                    <div className="text-xs text-gray-400">avg={b.avg_price}€ · std={b.std_dev}€ · n={b.sample_count}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Date matching */}
            <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
              <h2 className="font-semibold mb-3">Matching dates</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs font-bold text-gray-400 mb-1">Vols</div>
                  {debug.flight_date_keys.map(k => <div key={k} className="text-sm text-gray-600">{k}</div>)}
                </div>
                <div>
                  <div className="text-xs font-bold text-gray-400 mb-1">Hotels</div>
                  {debug.accommodation_date_keys.map(k => <div key={k} className="text-sm text-gray-600">{k}</div>)}
                </div>
              </div>
            </div>
          </>
        )}

        {loading && <div className="text-center py-12 text-gray-400">Chargement...</div>}
      </div>
    </div>
  );
}
