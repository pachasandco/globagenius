"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface CtrData {
  period_days: number;
  total_sent: number;
  total_links_generated: number;
  total_links_clicked: number;
  total_clicks: number;
  ctr_pct: number;
  top_destinations: Array<{
    destination: string;
    tokens: number;
    clicked: number;
    clicks: number;
    ctr: number;
  }>;
}

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
  passive?: boolean;
  has_baseline: boolean;
  baseline_avg: number | null;
  baseline_samples: number;
  baseline_updated_at: string | null;
}

// ── CSV export helpers ──────────────────────────────────────────────
// Pure client-side: builds CSV strings from data already loaded on the
// page and triggers a download via a Blob URL. No server round-trip.

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  // Quote if the value contains a comma, quote, or newline.
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function toCsv(headers: string[], rows: (unknown[])[]): string {
  const lines = [headers.map(csvEscape).join(",")];
  for (const row of rows) {
    lines.push(row.map(csvEscape).join(","));
  }
  return lines.join("\n");
}

function downloadCsv(filename: string, content: string): void {
  // Prepend a UTF-8 BOM so Excel opens accented French labels correctly.
  const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const SOURCE_LABELS: Record<string, { label: string; color: string }> = {
  ryanair:      { label: "Ryanair",   color: "bg-blue-100 text-blue-800" },
  transavia:    { label: "Transavia", color: "bg-green-100 text-green-800" },
  vueling:      { label: "Vueling",   color: "bg-yellow-100 text-yellow-800" },
  travelpayouts:{ label: "Agrégateur",color: "bg-purple-100 text-purple-800" },
};

// IATA → ville. Sert au rendu lisible des codes IATA dans le panneau
// 'Destinations surveillées par aéroport'. Liste indicative, complétée
// au fur et à mesure — un code absent affiche juste son IATA brut.
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
  BIO:"Bilbao",
};

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [status, setStatus] = useState<{ active_baselines: number; recent_scrapes: ScrapeLog[] } | null>(null);
  const [debug, setDebug] = useState<DebugData | null>(null);
  const [routes, setRoutes] = useState<RouteRow[] | null>(null);
  const [routeFilter, setRouteFilter] = useState("");
  const [ctr, setCtr] = useState<CtrData | null>(null);
  const [loading, setLoading] = useState(false);
  const [triggerResult, setTriggerResult] = useState("");
  // Telegram broadcast composer
  const [bcMessage, setBcMessage] = useState("");
  const [bcStatus, setBcStatus] = useState("");
  const [bcPendingCount, setBcPendingCount] = useState<number | null>(null);
  const [bcSending, setBcSending] = useState(false);
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
      const [statusRes, debugRes, routesRes, ctrRes] = await Promise.all([
        fetch(`${API_URL}/api/status`).then(r => r.json()),
        fetch(`${API_URL}/api/debug/data`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/routes`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
        fetch(`${API_URL}/api/admin/ctr?days=30`, { headers: { "X-Admin-Key": key } }).then(r => r.json()),
      ]);
      setStatus(statusRes);
      if (!debugRes.detail) setDebug(debugRes);
      if (routesRes.routes) setRoutes(routesRes.routes);
      if (!ctrRes.detail) setCtr(ctrRes);
    } catch { /* ignore */ }
    setLoading(false);
  }

  function handleLogin() {
    localStorage.setItem("gg_admin_key", adminKey);
    setAuthenticated(true);
    loadData(adminKey);
  }

  // Export every table currently loaded on the page into a single CSV.
  // Each section is delimited by a "## <section>" marker so one file
  // holds routes + CTR + scrape logs + baselines without needing a zip.
  function exportAll() {
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const blocks: string[] = [];

    if (routes && routes.length) {
      const rows = routes.map((r) => [
        r.origin,
        r.destination,
        IATA_CITY[r.destination] || "",
        r.tier === "tier1" ? "temps réel" : "agrégateur",
        r.passive ? "oui" : "non",
        r.sources.join(" / "),
        r.has_baseline ? "oui" : "non",
        r.baseline_avg ?? "",
        r.baseline_samples ?? 0,
        r.baseline_updated_at ?? "",
      ]);
      blocks.push(
        "## Destinations surveillées\n" +
          toCsv(
            ["origine", "destination", "ville", "tier", "passive", "sources", "baseline", "prix_moyen", "samples", "maj"],
            rows
          )
      );
    }

    if (ctr?.top_destinations?.length) {
      const rows = ctr.top_destinations.map((d) => [
        d.destination,
        d.tokens,
        d.clicked,
        d.clicks,
        d.ctr,
      ]);
      blocks.push(
        "## Top destinations CTR (30j)\n" +
          toCsv(["destination", "liens_generes", "liens_cliques", "clics_totaux", "ctr_pct"], rows)
      );
    }

    if (status?.recent_scrapes?.length) {
      const rows = status.recent_scrapes.map((s) => [
        s.started_at,
        s.source,
        s.type,
        s.items_count,
        s.errors_count,
        s.status,
        s.duration_ms,
      ]);
      blocks.push(
        "## Scrape logs\n" +
          toCsv(["started_at", "source", "type", "items", "errors", "status", "duration_ms"], rows)
      );
    }

    if (debug?.baselines_sample?.length) {
      const rows = debug.baselines_sample.map((b) => [
        b.route_key,
        b.avg_price,
        b.std_dev,
        b.sample_count,
      ]);
      blocks.push(
        "## Baselines (échantillon)\n" +
          toCsv(["route_key", "prix_moyen", "ecart_type", "samples"], rows)
      );
    }

    if (!blocks.length) {
      alert("Aucune donnée chargée à exporter — clique sur Refresh d'abord.");
      return;
    }

    downloadCsv(`globegenius-admin-${stamp}.csv`, blocks.join("\n\n"));
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

  async function broadcast(mode: "test" | "send", confirmCount?: number) {
    const message = bcMessage.trim();
    if (!message) { setBcStatus("Message vide."); return; }
    setBcSending(true);
    setBcStatus(mode === "test" ? "Envoi du test à toi…" : "Envoi en cours…");
    try {
      const res = await fetch(`${API_URL}/api/admin/broadcast`, {
        method: "POST",
        headers: { "X-Admin-Key": adminKey, "Content-Type": "application/json" },
        body: JSON.stringify({ message, mode, confirm_count: confirmCount ?? null }),
      });
      if (res.status === 409) {
        const body = await res.json().catch(() => ({}));
        // Extract the recipient count from the detail message.
        const m = /(\d+)\s+destinataires/.exec(body.detail || "");
        const n = m ? parseInt(m[1], 10) : null;
        setBcPendingCount(n);
        setBcStatus(`⚠️ Confirme l'envoi à ${n ?? "?"} fondateurs (clique "Confirmer l'envoi").`);
        setBcSending(false);
        return;
      }
      const data = await res.json();
      if (!res.ok) {
        setBcStatus(`Erreur : ${data.detail || res.status}`);
      } else if (mode === "test") {
        setBcStatus(`✅ Test envoyé à ton compte (${data.delivered}/1). Vérifie Telegram, puis "Envoyer à tous".`);
      } else {
        setBcStatus(`✅ Diffusé : ${data.delivered}/${data.recipients} (${data.failed} échecs).`);
        setBcPendingCount(null);
        setBcMessage("");
      }
    } catch (e) {
      setBcStatus(`Erreur : ${e}`);
    } finally {
      setBcSending(false);
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
        <div className="max-w-6xl mx-auto px-4 h-[80px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-red-500 flex items-center justify-center text-white font-bold text-sm">A</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Admin</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/admin/users" className="text-sm text-cyan-600 hover:text-cyan-700 font-medium">👥 Users</Link>
            <Link href="/admin/feedback" className="text-sm text-cyan-600 hover:text-cyan-700 font-medium">💬 Feedback</Link>
            <Link href="/home" className="text-sm text-gray-500 hover:text-gray-900">Home</Link>
            <button onClick={exportAll} className="text-sm text-emerald-600 hover:text-emerald-700 font-medium">⬇ CSV</button>
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

        {/* CTR block */}
        {ctr && (
          <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold">Taux de clic — 30 derniers jours</h2>
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${ctr.ctr_pct >= 25 ? "bg-green-100 text-green-700" : ctr.ctr_pct >= 10 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                {ctr.ctr_pct}% CTR
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xl font-bold">{ctr.total_sent}</div>
                <div className="text-xs text-gray-400">alertes envoyées</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xl font-bold">{ctr.total_links_generated}</div>
                <div className="text-xs text-gray-400">liens générés</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xl font-bold">{ctr.total_links_clicked}</div>
                <div className="text-xs text-gray-400">liens cliqués</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xl font-bold">{ctr.total_clicks}</div>
                <div className="text-xs text-gray-400">clics totaux</div>
              </div>
            </div>
            {ctr.top_destinations.length > 0 && (
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase mb-2">Top destinations par CTR</div>
                <div className="space-y-1">
                  {ctr.top_destinations.map(d => (
                    <div key={d.destination} className="flex items-center gap-2 text-sm">
                      <span className="w-10 font-mono font-medium">{d.destination}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div
                          className="h-2 rounded-full bg-[#FF6B47]"
                          style={{ width: `${Math.min(d.ctr, 100)}%` }}
                        />
                      </div>
                      <span className="w-14 text-right text-xs text-gray-500">{d.ctr}% ({d.clicked}/{d.tokens})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
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

        {/* Telegram broadcast */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
          <h2 className="font-semibold mb-1">📣 Message Telegram aux fondateurs</h2>
          <p className="text-xs text-gray-400 mb-3">
            Envoi ponctuel (update beta, annonce). Teste d&apos;abord sur ton compte,
            puis diffuse. Les utilisateurs en pause sont exclus automatiquement.
          </p>
          <textarea
            value={bcMessage}
            onChange={(e) => { setBcMessage(e.target.value); setBcPendingCount(null); setBcStatus(""); }}
            rows={5}
            maxLength={3500}
            placeholder={"Mise à jour J+5 : 52 fondateurs en une semaine 🙏\n\nIl reste 48 places gratuites à vie.\n96% des alertes validées 👍\n\n→ globegenius.app"}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono resize-y mb-1"
          />
          <div className="text-[11px] text-gray-400 mb-3">{bcMessage.length}/3500 · texte brut (pas de Markdown)</div>
          <div className="flex flex-wrap gap-2 items-center">
            <button
              onClick={() => broadcast("test")}
              disabled={bcSending || !bcMessage.trim()}
              className="bg-gray-700 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-800 disabled:opacity-40"
            >
              📩 M&apos;envoyer le test
            </button>
            {bcPendingCount === null ? (
              <button
                onClick={() => broadcast("send")}
                disabled={bcSending || !bcMessage.trim()}
                className="bg-[#FF6B47] text-white text-sm px-4 py-2 rounded-lg hover:bg-[#E55A38] disabled:opacity-40"
              >
                📣 Préparer l&apos;envoi à tous
              </button>
            ) : (
              <button
                onClick={() => broadcast("send", bcPendingCount)}
                disabled={bcSending}
                className="bg-red-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-40"
              >
                ✅ Confirmer l&apos;envoi à {bcPendingCount} fondateurs
              </button>
            )}
          </div>
          {bcStatus && <div className="mt-2 text-xs text-gray-600">{bcStatus}</div>}
        </div>

        {/* Scrape logs */}
        {status?.recent_scrapes && (
          <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
            <h2 className="font-semibold mb-3">Scrape Logs</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-xs text-gray-400">
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2 pr-4">Vols</th>
                    <th className="pb-2 pr-4">Erreurs</th>
                    <th className="pb-2 pr-4">Durée</th>
                    <th className="pb-2">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {status.recent_scrapes.map(s => (
                    <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2 pr-4 text-xs whitespace-nowrap">
                        {new Date(s.started_at).toLocaleString("fr-FR", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" })}
                      </td>
                      <td className="py-2 pr-4 text-xs font-medium">{s.source}</td>
                      <td className="py-2 pr-4 font-bold">{s.items_count}</td>
                      <td className="py-2 pr-4">{s.errors_count > 0 ? <span className="text-red-500 font-semibold">{s.errors_count}</span> : <span className="text-gray-300">0</span>}</td>
                      <td className="py-2 pr-4 text-xs text-gray-400">{s.duration_ms ? `${Math.round(s.duration_ms / 1000)}s` : "—"}</td>
                      <td className="py-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${s.status === "success" ? "bg-green-50 text-green-700" : s.status === "partial" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>
                          {s.status}
                        </span>
                      </td>
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

        {/* Destinations surveillées par aéroport — dérivé du endpoint
            live /api/admin/routes pour ne jamais drifter vs le backend. */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-6">
          <h2 className="font-semibold mb-1">Destinations surveillées par aéroport</h2>
          <p className="text-xs text-gray-400 mb-4">
            Source : <code>tier1_routes.py</code> + <code>raw_flights</code> live.
            ⚡ = scraping direct (~20 min) · sinon = agrégateur Travelpayouts (~2 h).
          </p>
          {routes === null ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : (
            (() => {
              const airports = Array.from(new Set(routes.map((r) => r.origin))).sort();
              return (
                <div className="space-y-3">
                  {airports.map((ap) => {
                    const apRoutes = routes.filter((r) => r.origin === ap);
                    const realtime = apRoutes.filter((r) => r.tier === "tier1");
                    const tpOnly = apRoutes.filter((r) => r.tier === "tier2");
                    return (
                      <div key={ap} className="border border-gray-100 rounded-xl overflow-hidden">
                        <div className="px-4 py-2 bg-gray-50 flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-sm">{ap}</span>
                          <span className="text-xs text-gray-400">
                            {realtime.length > 0 && (
                              <span className="text-green-600 font-medium">
                                {realtime.length} temps réel
                              </span>
                            )}
                            {realtime.length > 0 && tpOnly.length > 0 && " · "}
                            {tpOnly.length > 0 && `${tpOnly.length} agrégateur`}
                          </span>
                        </div>
                        <div className="px-4 py-3 flex flex-wrap gap-1.5">
                          {realtime.map((r) => (
                            <span
                              key={`rt-${r.destination}`}
                              className="px-2 py-0.5 bg-green-50 border border-green-100 rounded-full text-[10px] font-medium text-green-800"
                              title={r.sources.join(", ")}
                            >
                              ⚡ {r.destination}
                              {IATA_CITY[r.destination] ? ` · ${IATA_CITY[r.destination]}` : ""}
                            </span>
                          ))}
                          {tpOnly.map((r) => (
                            <span
                              key={`tp-${r.destination}`}
                              className="px-2 py-0.5 bg-gray-50 border border-gray-200 rounded-full text-[10px] text-gray-600"
                            >
                              {r.destination}
                              {IATA_CITY[r.destination] ? ` · ${IATA_CITY[r.destination]}` : ""}
                            </span>
                          ))}
                          {apRoutes.length === 0 && (
                            <span className="text-xs text-gray-300 italic">aucune route surveillée</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()
          )}
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
