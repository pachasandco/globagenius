"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getFlightDeals, getPipelineStatus, type FlightDeal, type PipelineStatus } from "@/lib/api";

function FlightDealCard({ deal }: { deal: FlightDeal }) {
  const days = deal.trip_duration_days ?? Math.round(
    (new Date(deal.return_date).getTime() - new Date(deal.departure_date).getTime()) / 86400000
  );
  const depDate = new Date(deal.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const retDate = new Date(deal.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const isPremium = deal.tier === "premium";
  const discount = Math.round(deal.discount_pct);
  const stopsLabel = deal.stops === 0 ? "Direct" : `${deal.stops} escale${deal.stops > 1 ? "s" : ""}`;
  const locked = deal.locked || deal.price === null || deal.baseline_price === null;
  const saving = !locked && deal.baseline_price !== null && deal.price !== null
    ? Math.round(deal.baseline_price - deal.price)
    : null;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className={`px-4 py-3 flex items-center justify-between ${isPremium ? "bg-gray-900" : "bg-gray-700"}`}>
        <div>
          <div className="text-white text-sm font-semibold">
            {deal.origin} → {deal.destination}
          </div>
          <div className="text-gray-400 text-xs">
            {depDate} – {retDate} · {days} jour{days > 1 ? "s" : ""} · {stopsLabel}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isPremium && (
            <span className="bg-amber-400 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-full">PREMIUM</span>
          )}
          <div className={`text-white text-xs font-bold px-2.5 py-1 rounded-full ${isPremium ? "bg-red-500" : "bg-orange-500"}`}>
            -{discount}%
          </div>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-end justify-between mb-3">
          <div>
            <div className="text-xs text-gray-400 mb-0.5">
              Vol aller-retour{deal.airline ? ` · ${deal.airline}` : ""}
            </div>
            {locked ? (
              <div className="flex items-baseline gap-2 select-none">
                <span className="text-2xl font-bold blur-sm text-gray-400">••• €</span>
                <span className="text-sm text-gray-300 line-through blur-sm">••• €</span>
              </div>
            ) : (
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold">{Math.round(deal.price as number)} €</span>
                <span className="text-sm text-gray-300 line-through">{Math.round(deal.baseline_price as number)} €</span>
              </div>
            )}
            {saving !== null && (
              <div className="text-xs text-emerald-600 mt-0.5">Économie de {saving} €</div>
            )}
            {locked && (
              <div className="text-xs text-gray-400 mt-0.5">Tarif réservé aux abonnés</div>
            )}
          </div>
          <div className="flex items-center gap-1.5 bg-cyan-50 rounded-lg px-2.5 py-1">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
            <span className="text-xs font-semibold text-cyan-700">Score {deal.score}</span>
          </div>
        </div>
        {locked ? (
          <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 text-xs text-amber-800">
            💎 {isPremium ? "Réservé aux abonnés Premium" : "Connectez-vous pour voir le prix"}
          </div>
        ) : deal.source_url ? (
          <a
            href={deal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center bg-[#FF6B47] hover:bg-[#E55A38] text-white text-sm font-semibold py-2.5 rounded-xl transition-all"
          >
            Voir l&apos;offre
          </a>
        ) : null}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [freeDeals, setFreeDeals] = useState<FlightDeal[]>([]);
  const [premiumDeals, setPremiumDeals] = useState<FlightDeal[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"free" | "premium">("free");

  useEffect(() => {
    async function load() {
      try {
        const [freeRes, premiumRes, statusRes] = await Promise.allSettled([
          getFlightDeals("free", 50),
          getFlightDeals("premium", 50),
          getPipelineStatus(),
        ]);
        if (freeRes.status === "fulfilled") {
          setFreeDeals(freeRes.value.items || []);
        }
        if (premiumRes.status === "fulfilled") {
          setPremiumDeals(premiumRes.value.items || []);
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

  const deals = activeTab === "free" ? freeDeals : premiumDeals;

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-end gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-10 h-10 shrink-0 object-contain" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">Globe Genius</span>
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
              <div className="text-2xl font-bold">{freeDeals.length + premiumDeals.length}</div>
              <div className="text-xs text-gray-400">Deals actifs</div>
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
            {freeDeals.length > 0 && (
              <span className="ml-2 bg-gray-200 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">{freeDeals.length}</span>
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
            {premiumDeals.length > 0 && (
              <span className="ml-2 bg-amber-100 text-amber-700 text-xs px-1.5 py-0.5 rounded-full">{premiumDeals.length}</span>
            )}
          </button>
        </div>

        {/* Plan info */}
        {activeTab === "premium" && (
          <div className="bg-[#FFFEF9] border border-[#FF6B47] rounded-xl p-4 mb-6 flex items-center justify-between">
            <div>
              <div className="font-semibold text-sm text-[#0A1F3D]">Deals Premium — vols à -40% et plus</div>
              <div className="text-xs text-[#0A1F3D]/70 mt-0.5">Les plus grosses anomalies de prix détectées. Réservation directe. Abonnement à 2,99€/mois.</div>
            </div>
            <span className="bg-amber-400 text-amber-900 text-xs font-bold px-3 py-1.5 rounded-full shrink-0">PREMIUM</span>
          </div>
        )}

        {activeTab === "free" && (
          <div className="bg-cyan-50 border border-cyan-100 rounded-xl p-4 mb-6">
            <div className="font-semibold text-sm text-cyan-900">Deals Gratuits — vols à -20% à -39%</div>
            <div className="text-xs text-cyan-700 mt-0.5">De bonnes affaires visibles ici sans engagement. Passez en Premium pour débloquer les -40% et plus et les alertes Telegram.</div>
          </div>
        )}

        {/* Content */}
        {loading && (
          <div className="text-center py-20 text-gray-400">Chargement des deals...</div>
        )}

        {error && (
          <div className="bg-red-50 text-red-600 rounded-xl p-5 text-sm">{error}</div>
        )}

        {!loading && !error && deals.length === 0 && (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold mb-2">Aucun deal {activeTab === "free" ? "gratuit" : "premium"} pour le moment</h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              Le pipeline analyse les prix en continu. Les deals apparaîtront dès que des anomalies seront détectées.
            </p>
          </div>
        )}

        {!loading && !error && deals.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {deals.map((deal) => (
              <FlightDealCard key={deal.id} deal={deal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
