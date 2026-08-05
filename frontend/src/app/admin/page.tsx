"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  tier: string;
  stripe_customer_id: string | null;
  telegram_connected: boolean;
  has_grant: boolean;
  badge: boolean;
}

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

interface StatusData {
  active_baselines: number;
  recent_scrapes: ScrapeLog[];
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

const SOURCE_LABELS: Record<string, { label: string; className: string }> = {
  ryanair: { label: "Ryanair", className: "bg-blue-50 text-blue-700" },
  transavia: { label: "Transavia", className: "bg-emerald-50 text-emerald-700" },
  vueling: { label: "Vueling", className: "bg-amber-50 text-amber-700" },
  travelpayouts: { label: "Agrégateur", className: "bg-violet-50 text-violet-700" },
};

const IATA_CITY: Record<string, string> = {
  RAK: "Marrakech", CMN: "Casablanca", AGA: "Agadir", FEZ: "Fès", TNG: "Tanger",
  LIS: "Lisbonne", OPO: "Porto", FAO: "Faro", BCN: "Barcelone", MAD: "Madrid",
  SVQ: "Séville", VLC: "Valence", AGP: "Malaga", IBZ: "Ibiza", PMI: "Palma",
  ALC: "Alicante", FCO: "Rome", CIA: "Rome Ciampino", BGY: "Milan Bergame",
  NAP: "Naples", BRI: "Bari", PMO: "Palerme", ATH: "Athènes", HER: "Héraklion",
  RHO: "Rhodes", SKG: "Thessalonique", TFS: "Ténérife", LPA: "Gran Canaria",
  ACE: "Lanzarote", FUE: "Fuerteventura", TUN: "Tunis", MIR: "Monastir",
  ALG: "Alger", DUB: "Dublin", STN: "Londres Stansted", KRK: "Cracovie",
  WRO: "Wrocław", BUD: "Budapest", JFK: "New York", YUL: "Montréal",
  CUN: "Cancún", PUJ: "Punta Cana", BKK: "Bangkok", NRT: "Tokyo", DXB: "Dubaï",
  MLE: "Maldives", MRU: "Maurice", RUN: "La Réunion", PPT: "Papeete", GIG: "Rio",
  MIA: "Miami", LAX: "Los Angeles", HKG: "Hong Kong", IST: "Istanbul",
  TLV: "Tel Aviv", CAI: "Le Caire", AMS: "Amsterdam", BER: "Berlin", PRG: "Prague",
  VIE: "Vienne", WAW: "Varsovie", CPH: "Copenhague", ZRH: "Zurich", BRU: "Bruxelles",
  BIO: "Bilbao",
};

function number(value: number): string {
  return new Intl.NumberFormat("fr-FR").format(value || 0);
}

function percent(value: number): string {
  return `${Math.round(value || 0)} %`;
}

function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers.map(csvEscape).join(","), ...rows.map((row) => row.map(csvEscape).join(","))].join("\n");
}

function downloadCsv(filename: string, content: string): void {
  const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function isPremiumUser(user: AdminUser): boolean {
  return Boolean(
    user.badge ||
      user.has_grant ||
      user.stripe_customer_id ||
      (user.tier && user.tier !== "free")
  );
}

function KpiCard({
  label,
  value,
  note,
  accent,
}: {
  label: string;
  value: string;
  note: string;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-[#D9E2E3] bg-white p-5 shadow-[0_12px_30px_rgba(11,42,63,.04)]">
      <div className={`mb-4 h-1.5 w-12 rounded-full ${accent}`} />
      <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">{label}</div>
      <div className="mt-2 font-[family-name:var(--font-dm-serif)] text-4xl text-[#0B2A3F]">{value}</div>
      <div className="mt-2 text-xs leading-5 text-slate-500">{note}</div>
    </div>
  );
}

function FunnelRow({ label, value, total, detail }: { label: string; value: number; total: number; detail: string }) {
  const width = total > 0 ? Math.max(3, Math.min(100, (value / total) * 100)) : 0;
  return (
    <div>
      <div className="mb-2 flex items-end justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-[#0B2A3F]">{label}</div>
          <div className="text-xs text-slate-400">{detail}</div>
        </div>
        <div className="text-lg font-bold text-[#0B2A3F]">{number(value)}</div>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-[#0E7490]" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [status, setStatus] = useState<StatusData | null>(null);
  const [routes, setRoutes] = useState<RouteRow[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [ctr, setCtr] = useState<CtrData | null>(null);
  const [routeFilter, setRouteFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [triggerResult, setTriggerResult] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("gg_admin_key");
    if (!saved) return;
    setAdminKey(saved);
    setAuthenticated(true);
    void loadData(saved);
  }, []);

  async function json<T>(response: Response): Promise<T> {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = (body as { detail?: string }).detail;
      throw new Error(detail || `Erreur HTTP ${response.status}`);
    }
    return body as T;
  }

  async function loadData(key: string) {
    setLoading(true);
    setError("");
    try {
      const headers = { "X-Admin-Key": key };
      const [statusData, routesData, ctrData, usersData] = await Promise.all([
        fetch(`${API_URL}/api/status`).then((response) => json<StatusData>(response)),
        fetch(`${API_URL}/api/admin/routes`, { headers }).then((response) =>
          json<{ routes: RouteRow[] }>(response)
        ),
        fetch(`${API_URL}/api/admin/ctr?days=30`, { headers }).then((response) =>
          json<CtrData>(response)
        ),
        fetch(`${API_URL}/api/admin/users`, { headers }).then((response) =>
          json<{ items: AdminUser[] }>(response)
        ),
      ]);

      setStatus(statusData);
      setRoutes(routesData.routes || []);
      setCtr(ctrData);
      setUsers(usersData.items || []);
      setLastUpdated(new Date());
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Chargement impossible";
      setError(message);
      if (/401|403|admin|key|unauthorized|forbidden/i.test(message)) {
        localStorage.removeItem("gg_admin_key");
        setAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    const key = adminKey.trim();
    if (!key) return;
    localStorage.setItem("gg_admin_key", key);
    setAuthenticated(true);
    await loadData(key);
  }

  function logout() {
    localStorage.removeItem("gg_admin_key");
    setAuthenticated(false);
    setUsers([]);
    setRoutes([]);
    setCtr(null);
    setStatus(null);
  }

  async function triggerJob(job: string) {
    setTriggerResult(`Lancement de ${job}…`);
    try {
      const response = await fetch(`${API_URL}/api/trigger/${job}`, {
        method: "POST",
        headers: { "X-Admin-Key": adminKey },
      });
      const data = await json<{ detail?: string; status?: string }>(response);
      setTriggerResult(data.detail || `${job} lancé`);
    } catch (caught) {
      setTriggerResult(caught instanceof Error ? caught.message : "Erreur inconnue");
    }
  }

  function exportAll() {
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const blocks: string[] = [];

    if (routes.length) {
      blocks.push(
        "## Routes surveillées\n" +
          toCsv(
            ["origine", "destination", "ville", "source", "baseline", "prix_moyen", "echantillons", "mise_a_jour"],
            routes.map((route) => [
              route.origin,
              route.destination,
              IATA_CITY[route.destination] || "",
              route.sources.join(" / "),
              route.has_baseline ? "oui" : "non",
              route.baseline_avg ?? "",
              route.baseline_samples ?? 0,
              route.baseline_updated_at ?? "",
            ])
          )
      );
    }

    if (ctr?.top_destinations?.length) {
      blocks.push(
        "## Clics par destination — 30 jours\n" +
          toCsv(
            ["destination", "liens_generes", "liens_cliques", "clics", "ctr_pct"],
            ctr.top_destinations.map((item) => [item.destination, item.tokens, item.clicked, item.clicks, item.ctr])
          )
      );
    }

    if (status?.recent_scrapes?.length) {
      blocks.push(
        "## Collectes récentes\n" +
          toCsv(
            ["date", "source", "type", "elements", "erreurs", "statut", "duree_ms"],
            status.recent_scrapes.map((item) => [
              item.started_at,
              item.source,
              item.type,
              item.items_count,
              item.errors_count,
              item.status,
              item.duration_ms,
            ])
          )
      );
    }

    if (!blocks.length) {
      alert("Aucune donnée disponible à exporter.");
      return;
    }
    downloadCsv(`globegenius-pilotage-${stamp}.csv`, blocks.join("\n\n"));
  }

  const metrics = useMemo(() => {
    const totalUsers = users.length;
    const premiumUsers = users.filter(isPremiumUser).length;
    const freemiumUsers = Math.max(0, totalUsers - premiumUsers);
    const ogUsers = users.filter((user) => user.badge).length;
    const telegramUsers = users.filter((user) => user.telegram_connected).length;
    const freemiumConnected = users.filter(
      (user) => !isPremiumUser(user) && user.telegram_connected
    ).length;
    const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    const newUsers7d = users.filter((user) => {
      const created = new Date(user.created_at).getTime();
      return Number.isFinite(created) && created >= sevenDaysAgo;
    }).length;
    const activationRate = totalUsers ? (telegramUsers / totalUsers) * 100 : 0;
    const premiumRate = totalUsers ? (premiumUsers / totalUsers) * 100 : 0;
    const baselineCoverage = routes.length
      ? (routes.filter((route) => route.has_baseline).length / routes.length) * 100
      : 0;
    const scrapes = status?.recent_scrapes || [];
    const successfulScrapes = scrapes.filter((item) => item.status === "success").length;
    const scrapeSuccessRate = scrapes.length ? (successfulScrapes / scrapes.length) * 100 : 0;
    const scrapeErrors = scrapes.reduce((sum, item) => sum + (item.errors_count || 0), 0);

    return {
      totalUsers,
      premiumUsers,
      freemiumUsers,
      ogUsers,
      telegramUsers,
      freemiumConnected,
      newUsers7d,
      activationRate,
      premiumRate,
      baselineCoverage,
      scrapeSuccessRate,
      scrapeErrors,
    };
  }, [users, routes, status]);

  const filteredRoutes = routes.filter(
    (route) =>
      !routeFilter ||
      route.origin.includes(routeFilter.toUpperCase()) ||
      route.destination.includes(routeFilter.toUpperCase()) ||
      (IATA_CITY[route.destination] || "").toUpperCase().includes(routeFilter.toUpperCase())
  );

  if (!authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F7F3EA] px-4">
        <div className="w-full max-w-sm rounded-[28px] border border-[#D9E2E3] bg-white p-8 shadow-[0_25px_70px_rgba(11,42,63,.08)]">
          <div className="text-center">
            <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Pilotage interne</div>
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">GlobeGenius Admin</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">Accès aux indicateurs produit et aux opérations.</p>
          </div>
          <input
            type="password"
            value={adminKey}
            onChange={(event) => setAdminKey(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && void handleLogin()}
            placeholder="Clé administrateur"
            className="mt-7 w-full rounded-xl border border-[#D9E2E3] px-4 py-3 text-sm outline-none focus:border-[#0E7490] focus:ring-1 focus:ring-[#0E7490]"
          />
          <button
            onClick={() => void handleLogin()}
            className="mt-4 w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078]"
          >
            Ouvrir le tableau de bord
          </button>
          {error && <p className="mt-4 text-center text-xs text-red-500">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="sticky top-0 z-50 border-b border-[#D9E2E3] bg-white/95 backdrop-blur">
        <div className="mx-auto flex min-h-20 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div>
            <div className="font-[family-name:var(--font-dm-serif)] text-xl">GlobeGenius</div>
            <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#0E7490]">Pilotage</div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2 text-sm">
            <Link href="/admin/users" className="rounded-xl bg-[#0B2A3F] px-4 py-2.5 font-semibold text-white hover:bg-[#123B54]">
              Gestion des accès
            </Link>
            <Link href="/home" className="rounded-xl border border-[#D9E2E3] bg-white px-3.5 py-2.5 text-slate-600 hover:border-[#0E7490] hover:text-[#0E7490]">
              Voir le site
            </Link>
            <button onClick={exportAll} className="rounded-xl border border-[#D9E2E3] bg-white px-3.5 py-2.5 text-slate-600 hover:border-[#0E7490] hover:text-[#0E7490]">
              Export CSV
            </button>
            <button onClick={() => void loadData(adminKey)} disabled={loading} className="rounded-xl bg-[#0E7490] px-3.5 py-2.5 font-semibold text-white hover:bg-[#0A6078] disabled:opacity-50">
              {loading ? "Actualisation…" : "Actualiser"}
            </button>
            <button onClick={logout} className="px-2 py-2 text-xs text-slate-400 hover:text-red-500">Déconnexion</button>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <header className="mb-8 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#FF7A59]">Vue dirigeant</p>
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl md:text-5xl">Tableau de bord produit</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-500">
              Acquisition, activation Telegram, potentiel de conversion Freemium et santé du moteur de détection.
            </p>
          </div>
          <div className="text-xs text-slate-400">
            {lastUpdated ? `Données actualisées le ${lastUpdated.toLocaleString("fr-FR")}` : "Chargement des données…"}
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <section>
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0E7490]">Utilisateurs et revenus futurs</p>
              <h2 className="mt-1 font-[family-name:var(--font-dm-serif)] text-2xl">Les KPI qui pilotent la croissance</h2>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <KpiCard label="Comptes" value={number(metrics.totalUsers)} note="Utilisateurs enregistrés" accent="bg-[#0B2A3F]" />
            <KpiCard label="Freemium" value={number(metrics.freemiumUsers)} note="Audience à convertir vers 39 € / an" accent="bg-[#FF7A59]" />
            <KpiCard label="Premium" value={number(metrics.premiumUsers)} note={`${percent(metrics.premiumRate)} de la base`} accent="bg-[#2AB7A9]" />
            <KpiCard label="Membres OG" value={number(metrics.ogUsers)} note="Accès Premium conservé" accent="bg-amber-400" />
            <KpiCard label="Telegram actif" value={percent(metrics.activationRate)} note={`${number(metrics.telegramUsers)} comptes connectés`} accent="bg-[#0E7490]" />
            <KpiCard label="Inscriptions 7 j" value={number(metrics.newUsers7d)} note="Nouveaux comptes sur 7 jours" accent="bg-violet-500" />
          </div>
        </section>

        <section className="mt-8 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
          <div className="rounded-[28px] border border-[#D9E2E3] bg-white p-6 md:p-7">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0E7490]">Funnel d’activation</p>
                <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-2xl">Du compte gratuit à l’accès Premium</h2>
              </div>
              <span className="rounded-full bg-[#E9F5F7] px-3 py-1 text-xs font-bold text-[#0E7490]">Données réelles</span>
            </div>
            <div className="mt-7 space-y-6">
              <FunnelRow label="Comptes créés" value={metrics.totalUsers} total={metrics.totalUsers} detail="Base totale" />
              <FunnelRow label="Telegram connecté" value={metrics.telegramUsers} total={metrics.totalUsers} detail="Peut recevoir les alertes" />
              <FunnelRow label="Freemium activés" value={metrics.freemiumConnected} total={metrics.totalUsers} detail="Audience de conversion prioritaire" />
              <FunnelRow label="Accès Premium" value={metrics.premiumUsers} total={metrics.totalUsers} detail="OG, grants et abonnements" />
            </div>
          </div>

          <div className="rounded-[28px] bg-[#0B2A3F] p-6 text-white md:p-7">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#52C9BE]">Lecture business</p>
            <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-2xl">Leviers prioritaires</h2>
            <div className="mt-6 space-y-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-2xl font-bold">{number(Math.max(0, metrics.totalUsers - metrics.telegramUsers))}</div>
                <div className="mt-1 text-sm leading-6 text-white/60">comptes à réactiver pour connecter Telegram</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-2xl font-bold">{number(metrics.freemiumConnected)}</div>
                <div className="mt-1 text-sm leading-6 text-white/60">Freemium actifs pouvant recevoir les relances Brevo</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <div className="text-2xl font-bold">39 € / an</div>
                <div className="mt-1 text-sm leading-6 text-white/60">offre Premium à convertir lorsque Stripe sera ouvert</div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-10">
          <div className="mb-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#FF7A59]">Valeur produit</p>
            <h2 className="mt-1 font-[family-name:var(--font-dm-serif)] text-2xl">Usage et performance des alertes</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard label="Alertes 30 j" value={number(ctr?.total_sent || 0)} note="Alertes contenant un lien mesurable" accent="bg-[#0E7490]" />
            <KpiCard label="CTR réservation" value={percent(ctr?.ctr_pct || 0)} note={`${number(ctr?.total_links_clicked || 0)} liens distincts ouverts`} accent="bg-[#FF7A59]" />
            <KpiCard label="Routes suivies" value={number(routes.length)} note={`${routes.filter((route) => route.tier === "tier1").length} temps réel · ${routes.filter((route) => route.tier === "tier2").length} agrégateur`} accent="bg-violet-500" />
            <KpiCard label="Couverture baseline" value={percent(metrics.baselineCoverage)} note={`${number(status?.active_baselines || 0)} baselines actives`} accent="bg-emerald-500" />
          </div>

          {ctr && ctr.top_destinations.length > 0 && (
            <div className="mt-5 rounded-[28px] border border-[#D9E2E3] bg-white p-6 md:p-7">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0E7490]">Intention de réservation</p>
                  <h3 className="mt-2 font-[family-name:var(--font-dm-serif)] text-2xl">Destinations qui génèrent le plus de clics</h3>
                </div>
                <div className="text-xs text-slate-400">Fenêtre : {ctr.period_days} jours</div>
              </div>
              <div className="mt-6 grid gap-3 md:grid-cols-2">
                {ctr.top_destinations.slice(0, 8).map((destination) => (
                  <div key={destination.destination} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-bold text-[#0B2A3F]">{IATA_CITY[destination.destination] || destination.destination}</div>
                        <div className="text-xs text-slate-400">{destination.destination} · {destination.clicked}/{destination.tokens} liens ouverts</div>
                      </div>
                      <div className="text-lg font-bold text-[#0E7490]">{percent(destination.ctr)}</div>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
                      <div className="h-full rounded-full bg-[#FF7A59]" style={{ width: `${Math.min(destination.ctr, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="mt-10">
          <div className="mb-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0E7490]">Santé opérationnelle</p>
            <h2 className="mt-1 font-[family-name:var(--font-dm-serif)] text-2xl">Moteur de collecte et de qualification</h2>
          </div>

          <div className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
            <div className="rounded-[28px] border border-[#D9E2E3] bg-white p-6">
              <div className="flex items-center gap-3">
                <span className={`h-3 w-3 rounded-full ${metrics.scrapeSuccessRate >= 90 ? "bg-emerald-500" : metrics.scrapeSuccessRate >= 70 ? "bg-amber-400" : "bg-red-500"}`} />
                <h3 className="font-bold">État du pipeline</h3>
              </div>
              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-2xl font-bold text-[#0B2A3F]">{percent(metrics.scrapeSuccessRate)}</div>
                  <div className="mt-1 text-xs text-slate-400">collectes réussies</div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-2xl font-bold text-[#0B2A3F]">{number(metrics.scrapeErrors)}</div>
                  <div className="mt-1 text-xs text-slate-400">erreurs remontées</div>
                </div>
              </div>
              <div className="mt-5 border-t border-slate-100 pt-5">
                <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">Actions manuelles</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => void triggerJob("scrape_flights")} className="rounded-xl bg-[#0E7490] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0A6078]">Collecter les vols</button>
                  <button onClick={() => void triggerJob("recalculate_baselines")} className="rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-600">Recalculer les baselines</button>
                  <button onClick={() => void triggerJob("expire_stale_data")} className="rounded-xl bg-slate-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Nettoyer les données</button>
                </div>
                {triggerResult && <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">{triggerResult}</div>}
              </div>
            </div>

            <div className="rounded-[28px] border border-[#D9E2E3] bg-white p-6">
              <div className="flex items-end justify-between gap-3">
                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">Dernières collectes</div>
                  <h3 className="mt-1 font-[family-name:var(--font-dm-serif)] text-2xl">Journaux du moteur</h3>
                </div>
                <div className="text-xs text-slate-400">{status?.recent_scrapes?.length || 0} exécutions</div>
              </div>
              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[620px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                      <th className="pb-3 pr-4">Date</th>
                      <th className="pb-3 pr-4">Source</th>
                      <th className="pb-3 pr-4">Éléments</th>
                      <th className="pb-3 pr-4">Erreurs</th>
                      <th className="pb-3 pr-4">Durée</th>
                      <th className="pb-3">Statut</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(status?.recent_scrapes || []).slice(0, 12).map((scrape) => (
                      <tr key={scrape.id} className="border-b border-slate-50">
                        <td className="py-3 pr-4 text-xs whitespace-nowrap">{dateTime(scrape.started_at)}</td>
                        <td className="py-3 pr-4 text-xs font-semibold">{scrape.source}</td>
                        <td className="py-3 pr-4 font-bold">{number(scrape.items_count)}</td>
                        <td className="py-3 pr-4">{scrape.errors_count ? <span className="font-bold text-red-500">{scrape.errors_count}</span> : <span className="text-slate-300">0</span>}</td>
                        <td className="py-3 pr-4 text-xs text-slate-400">{scrape.duration_ms ? `${Math.round(scrape.duration_ms / 1000)} s` : "—"}</td>
                        <td className="py-3">
                          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${scrape.status === "success" ? "bg-emerald-50 text-emerald-700" : scrape.status === "partial" ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>
                            {scrape.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-10 rounded-[28px] border border-[#D9E2E3] bg-white p-6 md:p-7">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0E7490]">Couverture</p>
              <h2 className="mt-1 font-[family-name:var(--font-dm-serif)] text-2xl">Routes et maturité des baselines</h2>
              <p className="mt-2 text-sm text-slate-500">{routes.filter((route) => route.tier === "tier1").length} routes temps réel · {routes.filter((route) => route.tier === "tier2").length} routes agrégateur</p>
            </div>
            <input
              value={routeFilter}
              onChange={(event) => setRouteFilter(event.target.value)}
              placeholder="Filtrer : CDG, Tokyo…"
              className="w-full rounded-xl border border-[#D9E2E3] px-4 py-2.5 text-sm outline-none focus:border-[#0E7490] sm:w-64"
            />
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="pb-3 pr-4">Route</th>
                  <th className="pb-3 pr-4">Destination</th>
                  <th className="pb-3 pr-4">Sources</th>
                  <th className="pb-3 pr-4">Baseline</th>
                  <th className="pb-3 pr-4">Prix moyen</th>
                  <th className="pb-3 pr-4">Échantillons</th>
                  <th className="pb-3">Mise à jour</th>
                </tr>
              </thead>
              <tbody>
                {filteredRoutes.map((route) => (
                  <tr key={`${route.origin}-${route.destination}-${route.tier}`} className="border-b border-slate-50 hover:bg-slate-50/70">
                    <td className="py-3 pr-4 font-mono text-xs font-bold">{route.origin} → {route.destination}</td>
                    <td className="py-3 pr-4 text-sm">{IATA_CITY[route.destination] || route.destination}</td>
                    <td className="py-3 pr-4">
                      <div className="flex flex-wrap gap-1">
                        {route.sources.map((source) => (
                          <span key={source} className={`rounded-full px-2 py-1 text-[10px] font-bold ${SOURCE_LABELS[source]?.className || "bg-slate-100 text-slate-600"}`}>
                            {SOURCE_LABELS[source]?.label || source}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3 pr-4">{route.has_baseline ? <span className="font-semibold text-emerald-600">Active</span> : <span className="text-slate-300">Absente</span>}</td>
                    <td className="py-3 pr-4">{route.baseline_avg != null ? `${route.baseline_avg} €` : "—"}</td>
                    <td className="py-3 pr-4 text-slate-500">{route.baseline_samples ?? "—"}</td>
                    <td className="py-3 text-xs text-slate-400">{dateTime(route.baseline_updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!filteredRoutes.length && <div className="py-10 text-center text-sm text-slate-400">Aucune route ne correspond au filtre.</div>}
        </section>
      </main>
    </div>
  );
}
