"use client";

import { useEffect, useState } from "react";
import type { FlightDeal } from "@/lib/api";

function useCountdown(expiresAt: string | null): string | null {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!expiresAt) return;
    function update() {
      const diff = new Date(expiresAt!).getTime() - Date.now();
      if (diff <= 0) { setLabel(null); return; }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      if (h > 48) { setLabel(null); return; }
      if (h >= 1) setLabel(`Expire dans ${h}h${m > 0 ? m + "m" : ""}`);
      else setLabel(`Expire dans ${m}min`);
    }
    update();
    const id = setInterval(update, 30000);
    return () => clearInterval(id);
  }, [expiresAt]);

  return label;
}

interface Props {
  deal: FlightDeal;
  onUpgrade?: () => void;
}

export function FlightDealCard({ deal, onUpgrade }: Props) {
  const days = deal.trip_duration_days ?? Math.round(
    (new Date(deal.return_date).getTime() - new Date(deal.departure_date).getTime()) / 86400000
  );
  const dep = new Date(deal.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const ret = new Date(deal.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const isPremium = deal.tier === "premium";
  const discount = Math.round(deal.discount_pct);
  const stopsLabel = deal.stops === 0 ? "Direct" : `${deal.stops} escale${deal.stops > 1 ? "s" : ""}`;
  const locked = deal.locked || deal.price === null || deal.baseline_price === null;
  const saving = !locked && deal.baseline_price !== null && deal.price !== null
    ? Math.round(deal.baseline_price - deal.price)
    : null;
  const countdown = useCountdown(deal.expires_at ?? null);

  return (
    <div className="relative bg-[#FFFEF9] rounded-2xl border border-[#F0E6D8] hover:border-[#FF6B47] shadow-[0_4px_16px_rgba(10,31,61,0.04)] hover:shadow-[0_12px_32px_rgba(255,107,71,0.12)] transition-all duration-300 overflow-visible p-5 pt-7">
      {/* Discount sticker */}
      <div
        className="absolute -top-3 -right-3 w-14 h-14 rounded-full bg-[#FF6B47] text-white flex items-center justify-center font-bold text-sm shadow-[0_8px_20px_rgba(255,107,71,0.35)] z-10"
        style={{ transform: "rotate(-8deg)" }}
      >
        -{discount}%
      </div>

      {isPremium && (
        <span className="inline-block bg-[#FFC940] text-[#0A1F3D] text-[10px] font-bold px-2 py-0.5 rounded-full mb-2">
          PREMIUM
        </span>
      )}

      <div className="font-[family-name:var(--font-dm-serif)] text-xl md:text-2xl text-[#0A1F3D] mb-1 pr-12">
        {deal.origin} → {deal.destination}
      </div>

      <div className="text-sm text-[#0A1F3D]/60 mb-3">
        {dep} – {ret} · {days} jour{days > 1 ? "s" : ""}
      </div>

      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        {deal.airline && (
          <span className="bg-[#F0E6D8]/60 text-[#0A1F3D] text-xs px-2.5 py-1 rounded-full">
            ✈️ {deal.airline}
          </span>
        )}
        <span className="bg-[#F0E6D8]/60 text-[#0A1F3D] text-xs px-2.5 py-1 rounded-full">
          {stopsLabel}
        </span>
        {countdown && (
          <span className="bg-[#FFF1EC] text-[#E55A38] text-xs font-semibold px-2.5 py-1 rounded-full animate-pulse">
            ⏳ {countdown}
          </span>
        )}
      </div>

      {locked ? (
        <div className="flex items-baseline gap-2 select-none mb-3">
          <span className="text-3xl font-bold blur-sm text-[#0A1F3D]/30">••• €</span>
          <span className="text-sm text-[#0A1F3D]/30 line-through blur-sm">••• €</span>
        </div>
      ) : (
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-3xl font-bold text-[#0A1F3D]">{Math.round(deal.price as number)} €</span>
          <span className="text-sm text-[#0A1F3D]/40 line-through">{Math.round(deal.baseline_price as number)} €</span>
        </div>
      )}

      {saving !== null && (
        <div className="text-xs text-[#16A34A] font-semibold mb-3">
          ✨ Économie de {saving} €
        </div>
      )}

      {locked ? (
        <button
          onClick={onUpgrade}
          className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white text-sm font-semibold py-3 rounded-full transition-all shadow-[0_4px_12px_rgba(255,107,71,0.2)] hover:shadow-[0_8px_20px_rgba(255,107,71,0.3)]"
        >
          Débloquer — 29€/an →
        </button>
      ) : deal.source_url ? (
        <a
          href={deal.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block w-full text-center bg-[#FF6B47] hover:bg-[#E55A38] text-white text-sm font-semibold py-3 rounded-full transition-all shadow-[0_4px_12px_rgba(255,107,71,0.2)] hover:shadow-[0_8px_20px_rgba(255,107,71,0.3)]"
        >
          Voir l&apos;offre →
        </a>
      ) : null}
    </div>
  );
}
