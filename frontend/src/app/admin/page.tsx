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
  baselines_sample: Array<{ route_key: string; avg_price: number; std_dev: number; sample_count: number }>;
  price_diagnosis: Array<{ route: string; price: number; baseline_avg: number; discount_pct: number; z_score: number; would_qualify: boolean }>;
}

interface RouteRow {
  origin: string;
  destination: string;
  sources: string[];
  tier: "tier1" | "tier2";
  has_baseline: boolean;
  baseline_avg: number | null;
  baseline_samples: number;
  baseline_updated_at: string | null;
}

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  ryanair:      { label: "Ryanair",   color: "bg-blue-100 text-blue-800" },
  transavia:    { label: "Transavia", color: "bg-green-100 text-green-800" },
  vueling:      { label: "Vueling",   color: "bg-yellow-100 text-yellow-800" },
  travelpayouts:{ label: "Agrégateur",color: "bg-purple-100 text-purple-800" },
};

// ── Coverage recap (static — mirrors tier1_routes.py) ──────────────────────
const TIER1_ROUTES_ADMIN: [string, string][] = [
  ["CDG","RAK"],["CDG","CMN"],["CDG","AGA"],["CDG","FEZ"],["CDG","TNG"],
  ["ORY","RAK"],["ORY","CMN"],["ORY","AGA"],
  ["CDG","LIS"],["CDG","OPO"],["CDG","FAO"],
  ["ORY","LIS"],["ORY","OPO"],
  ["CDG","BCN"],["CDG","MAD"],["CDG","SVQ"],["CDG","VLC"],["CDG","AGP"],
  ["CDG","IBZ"],["CDG","PMI"],["CDG","ALC"],
  ["ORY","BCN"],["ORY","MAD"],["ORY","AGP"],["ORY","PMI"],["ORY","IBZ"],["ORY","ALC"],
  ["CDG","FCO"],["CDG","CIA"],["CDG","BGY"],["CDG","NAP"],["CDG","BRI"],["CDG","PMO"],
  ["ORY","FCO"],["ORY","NAP"],
  ["CDG","ATH"],["CDG","HER"],["CDG","RHO"],["CDG","SKG"],
  ["ORY","ATH"],["ORY","HER"],
  ["CDG","TFS"],["CDG","LPA"],["CDG","ACE"],["CDG","FUE"],
  ["ORY","TFS"],["ORY","LPA"],
  ["CDG","TUN"],["CDG","MIR"],["ORY","TUN"],["ORY","ALG"],
  ["CDG","DUB"],["CDG","STN"],
  ["CDG","KRK"],["CDG","WRO"],["CDG","BUD"],
];
const TIER1_SET_ADMIN = new Set(TIER1_ROUTES_ADMIN.map(([o, d]) => `${o}:${d}`));
const IATA_CITY: Record<string, string> = {
  RAK:"Marrakech",CMN:"Casablanca",AGA:"Agadir",FEZ:"Fès",TNG:"Tanger",
  LIS:"Lisbonne",OPO:"Porto",FAO:"Faro",
  BCN:"Barcelone",MAD:"Madrid",SVQ:"Séville",VLC:"Valence",AGP:"Malaga",
  IBZ:"Ibiza",PMI:"Palma",ALC:"Alicante",
  FCO:"Rome",CIA:"Rome Ciampino",BGY:"Milan Bergame",NAP:"Naples",BRI:"Bari",PMO:"Palerme",
  ATH:"Athènes",HER:"Héraklion",RHO:"Rhodes",SKG:"Thessalonique",
  TFS:"Ténérife",LPA:"Gran Canaria",ACE:"Lanzarote",FUE:"Fuerteventura",
  TUN:"Tunis",MIR:"Monastir",ALG:"Alger",DUB:"Dublin",STN:"Londres Stansted",
  KRK:"Cracovie",WRO:"Wrocław",BUD:"Budapest",
  JFK:"New York",YUL:"Montréal",CUN:"Cancún",PUJ:"Punta Cana",
  BKK:"Bangkok",NRT:"Tokyo",DXB:"Dubaï",MLE:"Maldives",
  MRU:"Maurice",RUN:"La Réunion",PPT:"Papeete",GIG:"Rio",MIA:"Miami",LAX:"Los Angeles",HKG:"Hong Kong",
  IST:"Istanbul",TLV:"Tel Aviv",CAI:"Le Caire",
  AMS:"Amsterdam",BER:"Berlin",PRG:"Prague",VIE:"Vienne",WAW:"Varsovie",CPH:"Copenhague",ZRH:"Zurich",BRU:"Bruxelles",
};
const TP_DESTS_ADMIN = [
  "RAK","CMN","AGA","LIS","OPO","BCN","MAD","AGP","FCO","NAP","ATH","HER",
  "TFS","LPA","TUN","DUB","BUD","KRK","IST","TLV","CAI",
  "IBZ","PMI","ALC",
  "JFK","YUL","CUN","PUJ","BKK","NRT","DXB","MLE","MRU","RUN","GIG","MIA","LAX","HKG",
  "AMS","BER","PRG","VIE","WAW","CPH","ZRH","BRU",
];
const MVP_AIRPORTS = ["CDG","ORY","LYS","MRS","NCE","BOD","NTE","TLS","BVA"];

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [status, setStatus] = useState<{ active_baselines: number; recent_scrapes: ScrapeLog[] } | null>(null);
  const [debug, setDebug] = useState<DebugData | null>(null);
  const [routes, setRoutes] = useState<RouteRow[] | null>(null);
  const [routeFilter, setRouteFilter] = useState("");
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
      const [statusRes, debugRes, routesRes] = await Promise.all([
        fetch(`${API_URL}/api/status`).then(r => r.json()),
        fetch(`${API_URL}/api/debug/data`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/routes`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
      ]);
      setStatus(statusRes);
      if (!debugRes.detail) setDebug(debugRes);
      if (routesRes.routes) setRoutes(routesRes.routes);
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
      <div className="min-h-screen bg-[#FFF8F0] flex items-center justify-center px-4">
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
          <button onClick={handleLogin} className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all">
            Acceder
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 h-[64px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500 flex items-center justify-center text-white font-bold text-sm">A</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Admin</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/admin/users" className="text-sm text-cyan-600 hover:text-cyan-700 font-medium">👥 Users</Link>
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

        {/* Routes actives */}
        {routes && (
          <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <h2 className="font-semibold">
                Routes actives
                <span className="ml-2 text-xs font-normal text-gray-400">
                  {routes.filter(r => r.tier === "tier1").length} temps réel · {routes.filter(r => r.tier === "tier2").length} agrégateur
                </span>
              </h2>
              <input
                value={routeFilter}
                onChange={e => setRouteFilter(e.target.value.toUpperCase())}
                placeholder="Filtrer (ex: CDG, BKK…)"
                className="text-xs px-3 py-1.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-400 w-44"
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                    <th className="pb-2 pr-4">Route</th>
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2 pr-4">Baseline</th>
                    <th className="pb-2 pr-4">Prix moy.</th>
                    <th className="pb-2 pr-4">Échantillons</th>
                    <th className="pb-2">Mis à jour</th>
                  </tr>
                </thead>
                <tbody>
                  {routes
                    .filter(r => !routeFilter || r.origin.includes(routeFilter) || r.destination.includes(routeFilter))
                    .map((r, i) => (
                      <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 pr-4 font-mono font-semibold text-xs">
                          {r.origin} → {r.destination}
                        </td>
                        <td className="py-2 pr-4">
                          <div className="flex flex-wrap gap-1">
                            {r.sources.map(s => (
                              <span key={s} className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${SOURCE_LABELS[s]?.color ?? "bg-gray-100 text-gray-600"}`}>
                                {SOURCE_LABELS[s]?.label ?? s}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-2 pr-4">
                          {r.has_baseline
                            ? <span className="text-green-600 font-semibold text-xs">✓ Active</span>
                            : <span className="text-gray-300 text-xs">—</span>}
                        </td>
                        <td className="py-2 pr-4 text-xs">
                          {r.baseline_avg != null ? `${r.baseline_avg} €` : "—"}
                        </td>
                        <td className="py-2 pr-4 text-xs text-gray-500">
                          {r.baseline_samples ?? "—"}
                        </td>
                        <td className="py-2 text-xs text-gray-400">
                          {r.baseline_updated_at
                            ? new Date(r.baseline_updated_at).toLocaleDateString("fr-FR")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Destinations surveillées par aéroport */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
          <h2 className="font-semibold mb-4">Destinations surveillées par aéroport</h2>
          <div className="space-y-3">
            {MVP_AIRPORTS.map((ap) => {
              const realtime = TIER1_ROUTES_ADMIN.filter(([o]) => o === ap).map(([, d]) => d);
              const tpOnly = TP_DESTS_ADMIN.filter((d) => !TIER1_SET_ADMIN.has(`${ap}:${d}`));
              return (
                <div key={ap} className="border border-gray-100 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 bg-gray-50 flex items-center gap-2">
                    <span className="font-bold text-sm">{ap}</span>
                    <span className="text-xs text-gray-400">
                      {realtime.length > 0 && <span className="text-green-600 font-medium">{realtime.length} temps réel</span>}
                      {realtime.length > 0 && " · "}
                      {tpOnly.length} agrégateur
                    </span>
                  </div>
                  <div className="px-4 py-3 flex flex-wrap gap-1.5">
                    {realtime.map((d) => (
                      <span key={`rt-${d}`} className="px-2 py-0.5 bg-green-50 border border-green-100 rounded-full text-[10px] font-medium text-green-800">
                        ⚡ {d} {IATA_CITY[d] ? `· ${IATA_CITY[d]}` : ""}
                      </span>
                    ))}
                    {tpOnly.map((d) => (
                      <span key={`tp-${d}`} className="px-2 py-0.5 bg-gray-50 border border-gray-200 rounded-full text-[10px] text-gray-600">
                        {d} {IATA_CITY[d] ? `· ${IATA_CITY[d]}` : ""}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

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
          </>
        )}

        {loading && <div className="text-center py-12 text-gray-400">Chargement...</div>}
      </div>
    </div>
  );
}
