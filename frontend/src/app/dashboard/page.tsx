"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPackages, getPipelineStatus, type Package, type PipelineStatus } from "@/lib/api";

function DealCard({ pkg }: { pkg: Package }) {
  const nights = Math.round(
    (new Date(pkg.return_date).getTime() - new Date(pkg.departure_date).getTime()) / 86400000
  );
  const depDate = new Date(pkg.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const retDate = new Date(pkg.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="bg-gray-900 px-4 py-3 flex items-center justify-between">
        <div>
          <div className="text-white text-sm font-semibold">
            {pkg.origin} → {pkg.destination}
          </div>
          <div className="text-gray-400 text-xs">
            {depDate} – {retDate} · {nights} nuits
          </div>
        </div>
        <div className="bg-rose-500 text-white text-xs font-bold px-2.5 py-1 rounded-full">
          -{Math.round(pkg.discount_pct)}%
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-end justify-between mb-3">
          <div>
            <div className="text-xs text-gray-400 mb-0.5">Vol + Hôtel</div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold">{Math.round(pkg.total_price)} €</span>
              <span className="text-sm text-gray-300 line-through">{Math.round(pkg.baseline_total)} €</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 bg-cyan-50 rounded-lg px-2.5 py-1">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
            <span className="text-xs font-semibold text-cyan-700">Score {pkg.score}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>Vol : {Math.round(pkg.flight_price)} €</span>
          <span>·</span>
          <span>Hôtel : {Math.round(pkg.accommodation_price)} €</span>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [pkgRes, statusRes] = await Promise.all([
          getPackages(0, 50),
          getPipelineStatus(),
        ]);
        setPackages(pkgRes.packages);
        setStatus(statusRes);
      } catch (e) {
        setError("Impossible de se connecter au pipeline. Vérifiez que le backend tourne sur le port 8000.");
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white font-bold text-sm">G</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-400">Dashboard</span>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-5 py-8">
        {/* Status bar */}
        {status && (
          <div className="flex flex-wrap gap-6 mb-8 p-5 bg-white rounded-2xl border border-gray-100">
            <div>
              <div className="text-2xl font-bold">{status.active_packages}</div>
              <div className="text-xs text-gray-400">Packages actifs</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{status.active_baselines}</div>
              <div className="text-xs text-gray-400">Baselines</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{status.recent_scrapes.length}</div>
              <div className="text-xs text-gray-400">Scrapes recents</div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400">Pipeline actif</span>
            </div>
          </div>
        )}

        {/* Title */}
        <div className="flex items-end justify-between mb-6">
          <div>
            <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl md:text-3xl mb-1">
              Deals disponibles
            </h1>
            <p className="text-sm text-gray-400">
              {packages.length} package{packages.length !== 1 ? "s" : ""} actif{packages.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        {/* Content */}
        {loading && (
          <div className="text-center py-20 text-gray-400">
            Chargement des deals...
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 rounded-xl p-5 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && packages.length === 0 && (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold mb-2">Aucun deal pour le moment</h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              Le pipeline est en cours d'analyse. Les premiers deals apparaîtront
              dès que les baselines de prix seront calculées (24h après le premier scraping).
            </p>
          </div>
        )}

        {!loading && !error && packages.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {packages.map((pkg) => (
              <DealCard key={pkg.id} pkg={pkg} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
