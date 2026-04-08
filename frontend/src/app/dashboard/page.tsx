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
  const isPremium = pkg.discount_pct >= 40;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className={`px-4 py-3 flex items-center justify-between ${isPremium ? "bg-gray-900" : "bg-gray-700"}`}>
        <div>
          <div className="text-white text-sm font-semibold">
            {pkg.origin} → {pkg.destination}
          </div>
          <div className="text-gray-400 text-xs">
            {depDate} – {retDate} · {nights} nuits
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isPremium && (
            <span className="bg-amber-400 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-full">PREMIUM</span>
          )}
          <div className={`text-white text-xs font-bold px-2.5 py-1 rounded-full ${isPremium ? "bg-red-500" : "bg-orange-500"}`}>
            -{Math.round(pkg.discount_pct)}%
          </div>
        </div>
      </div>
      <div className="p-4">
        {/* AI description if available */}
        {pkg.ai_description && (
          <p className="text-sm text-gray-600 italic mb-3 leading-relaxed">{pkg.ai_description}</p>
        )}

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

        {/* AI tip */}
        {pkg.ai_tip && (
          <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 text-xs text-amber-800 mb-3">
            💡 {pkg.ai_tip}
          </div>
        )}

        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>Vol : {Math.round(pkg.flight_price)} €</span>
          <span>·</span>
          <span>Hôtel : {Math.round(pkg.accommodation_price)} €</span>
        </div>

        {/* AI tags */}
        {pkg.ai_tags && pkg.ai_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {pkg.ai_tags.map((tag: string) => (
              <span key={tag} className="text-[11px] text-cyan-600 bg-cyan-50 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [freePackages, setFreePackages] = useState<Package[]>([]);
  const [premiumPackages, setPremiumPackages] = useState<Package[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"free" | "premium">("free");

  useEffect(() => {
    async function load() {
      try {
        const [freeRes, premiumRes, statusRes] = await Promise.allSettled([
          getPackages(0, 50, "free"),
          getPackages(0, 50, "premium"),
          getPipelineStatus(),
        ]);
        if (freeRes.status === "fulfilled") {
          const data = freeRes.value as { packages?: Package[]; items?: Package[] };
          setFreePackages(data?.packages || data?.items || []);
        }
        if (premiumRes.status === "fulfilled") {
          const data = premiumRes.value as { packages?: Package[]; items?: Package[] };
          setPremiumPackages(data?.packages || data?.items || []);
        }
        if (statusRes.status === "fulfilled") {
          setStatus(statusRes.value as PipelineStatus);
        }
      } catch {
        setError("Impossible de se connecter au pipeline.");
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  const packages = activeTab === "free" ? freePackages : premiumPackages;

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
              <div className="text-2xl font-bold">{freePackages.length + premiumPackages.length}</div>
              <div className="text-xs text-gray-400">Packages actifs</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{status.active_baselines}</div>
              <div className="text-xs text-gray-400">Baselines</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{(status.recent_scrapes || []).length}</div>
              <div className="text-xs text-gray-400">Scrapes récents</div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400">Pipeline actif</span>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit">
          <button
            onClick={() => setActiveTab("free")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === "free"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            🆓 Gratuit
            <span className="ml-2 text-xs text-gray-400">-20 à -39%</span>
            {freePackages.length > 0 && (
              <span className="ml-2 bg-gray-200 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">{freePackages.length}</span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("premium")}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === "premium"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            ⭐ Premium
            <span className="ml-2 text-xs text-gray-400">-40% et plus</span>
            {premiumPackages.length > 0 && (
              <span className="ml-2 bg-amber-100 text-amber-700 text-xs px-1.5 py-0.5 rounded-full">{premiumPackages.length}</span>
            )}
          </button>
        </div>

        {/* Plan info */}
        {activeTab === "premium" && (
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-100 rounded-xl p-4 mb-6 flex items-center justify-between">
            <div>
              <div className="font-semibold text-sm text-amber-900">Deals Premium — remise de 40% et plus</div>
              <div className="text-xs text-amber-700 mt-0.5">Les meilleures anomalies de prix détectées par notre IA. Abonnement à 9,90€/mois (bientôt).</div>
            </div>
            <span className="bg-amber-400 text-amber-900 text-xs font-bold px-3 py-1.5 rounded-full shrink-0">PREMIUM</span>
          </div>
        )}

        {activeTab === "free" && (
          <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-4 mb-6">
            <div className="font-semibold text-sm text-cyan-900">Deals Gratuits — remise de 20 à 39%</div>
            <div className="text-xs text-cyan-700 mt-0.5">De bonnes affaires accessibles à tous. Passez en Premium pour accéder aux deals à -40% et plus.</div>
          </div>
        )}

        {/* Content */}
        {loading && (
          <div className="text-center py-20 text-gray-400">Chargement des deals...</div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 rounded-xl p-5 text-sm">{error}</div>
        )}

        {!loading && !error && packages.length === 0 && (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold mb-2">Aucun deal {activeTab === "free" ? "gratuit" : "premium"} pour le moment</h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              Le pipeline analyse les prix en continu. Les deals apparaîtront dès que des anomalies seront détectées.
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
