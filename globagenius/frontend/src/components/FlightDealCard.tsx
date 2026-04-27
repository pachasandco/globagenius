import type { FlightDeal } from "@/lib/api";

export function FlightDealCard({ deal }: { deal: FlightDeal }) {
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

  return (
    <div className="relative bg-[#FFFEF9] rounded-2xl border border-[#F0E6D8] hover:border-[#FF6B47] shadow-[0_4px_16px_rgba(10,31,61,0.04)] hover:shadow-[0_12px_32px_rgba(255,107,71,0.12)] transition-all duration-300 overflow-visible p-5 pt-7">
      {/* Savings sticker */}
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
        <div className="bg-[#FFF1EC] border border-[#FF6B47]/30 rounded-xl px-3 py-2.5 text-xs text-[#E55A38] font-medium text-center">
          💎 {isPremium ? "Réservé aux abonnés Premium" : "Connectez-vous pour débloquer ce deal"}
        </div>
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
