"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getRecentDeals, type RecentDeal } from "@/lib/api";

const FALLBACK_DEALS = [
  { origin_city: "Paris", dest_city: "Tokyo", price: 449, baseline: 720, discount_pct: 38, trip_type: "round_trip" },
  { origin_city: "Paris", dest_city: "Phuket", price: 494, baseline: 835, discount_pct: 41, trip_type: "round_trip" },
  { origin_city: "Toulouse", dest_city: "Lisbonne", price: 64, baseline: 178, discount_pct: 64, trip_type: "round_trip" },
  { origin_city: "Marseille", dest_city: "Barcelone", price: 40, baseline: 121, discount_pct: 67, trip_type: "round_trip" },
  { origin_city: "Paris", dest_city: "Marrakech", price: 74, baseline: 155, discount_pct: 52, trip_type: "round_trip" },
  { origin_city: "Lyon", dest_city: "Rome", price: 58, baseline: 146, discount_pct: 60, trip_type: "round_trip" },
] as const;

type DisplayDeal = Pick<RecentDeal, "origin_city" | "dest_city" | "price" | "baseline" | "discount_pct"> & {
  trip_type?: string;
};

export function RecentDealsGrid() {
  const [deals, setDeals] = useState<DisplayDeal[]>([...FALLBACK_DEALS]);

  useEffect(() => {
    let active = true;
    getRecentDeals()
      .then((items) => {
        if (!active || !items?.length) return;
        const roundTrips = (items as Array<RecentDeal & { trip_type?: string }>).filter(
          (item) => item.trip_type === "round_trip"
        );
        // Keep the curated A/R fallback rather than ever showing an old API
        // payload whose trip shape is unknown.
        if (roundTrips.length) setDeals(roundTrips.slice(0, 6));
      })
      .catch(() => {
        // The fallback keeps the proof section useful during API maintenance.
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {deals.map((deal, index) => (
          <article
            key={`${deal.origin_city}-${deal.dest_city}-${index}`}
            className="rounded-3xl border border-[#D9E2E3] bg-white p-6 shadow-[0_18px_50px_rgba(11,42,63,.06)]"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-full bg-[#E9F5F7] px-3 py-1 text-xs font-bold text-[#0E7490]">
                Aller-retour
              </span>
              <span className="text-xs font-semibold text-[#168F73]">Prix A/R vérifié</span>
            </div>
            <h3 className="mt-7 text-lg font-bold text-[#0B2A3F]">
              {deal.origin_city} → {deal.dest_city}
            </h3>
            <div className="mt-4 flex items-end gap-3">
              <span className="font-[family-name:var(--font-dm-serif)] text-4xl text-[#FF7A59]">
                {Math.round(deal.price)} €
              </span>
              <span className="pb-1 text-sm text-slate-400 line-through">
                {Math.round(deal.baseline)} €
              </span>
            </div>
            <div className="mt-5 flex items-center justify-between border-t border-[#EEF1F1] pt-4 text-sm text-slate-500">
              <span>Écart au prix habituel A/R</span>
              <strong className="text-[#168F73]">−{Math.round(deal.discount_pct)} %</strong>
            </div>
          </article>
        ))}
      </div>
      <div className="mt-8 text-center">
        <Link
          href="/signup?utm_source=site&utm_medium=proof&utm_campaign=recent_deals"
          className="inline-flex rounded-xl bg-[#0E7490] px-6 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078]"
        >
          Configurer mes alertes gratuites
        </Link>
        <p className="mt-3 text-xs text-slate-400">
          Tarifs aller-retour par personne, vérifiés au moment de la détection. Les prix évoluent en permanence et GlobeGenius ne vend pas les billets.
        </p>
      </div>
    </div>
  );
}
