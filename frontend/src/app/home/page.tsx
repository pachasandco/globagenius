"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFlightDeals, getPipelineStatus, getPreferences, clearSessionCookie, type FlightDeal, type FlightTripType, type PipelineStatus } from "@/lib/api";
import { initSession } from "@/lib/session";
import { FlightDealCard } from "@/components/FlightDealCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Article {
  slug: string;
  destination: string;
  country: string;
  title: string;
  subtitle: string;
  cover_photo: string;
  tags: string[];
}

export default function HomePage() {
  const [allDeals, setAllDeals] = useState<FlightDeal[]>([]);
  const [, setStatus] = useState<PipelineStatus | null>(null);
  const [, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  // null = unknown (Stripe check not back yet). Avoids flashing the premium
  // upsell banner to users who turn out to be premium.
  const [isPremium, setIsPremium] = useState<boolean | null>(null);
  const [showAllDeals, setShowAllDeals] = useState(false);
  const [destFilter, setDestFilter] = useState<string>("all");
  const [discoveryGuides, setDiscoveryGuides] = useState<Array<{ iata: string; destination: string; title: string; cover_photo: string }>>([]);
  const [flightTripTypes, setFlightTripTypes] = useState<FlightTripType[]>(["round_trip"]);
  const [onewayBannerDismissed, setOnewayBannerDismissed] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    if (!userId) {
      router.push("/login");
      return;
    }

    // Auto-logout after 15 min inactivity. Keep the cleanup so we can
    // return it from the useEffect at the END, after load() has started.
    const sessionCleanup = initSession();

    async function load() {
      // Check premium status
      try {
        const token = localStorage.getItem("gg_token");
        if (token) {
          const premStatus = await fetch(`${API_URL}/api/stripe/status`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const premData = await premStatus.json();
          setIsPremium(premData.is_premium || false);
        }
      } catch { /* ignore */ }

      // Single fetch — backend returns all deals (≥50%) with server-side
      // quota logic: free users get up to 3 unlocked, rest masked.
      try {
        const [dealsRes, statusRes] = await Promise.allSettled([
          getFlightDeals("free", 50, 40, 40),
          getPipelineStatus(),
        ]);
        if (dealsRes.status === "fulfilled") {
          setAllDeals(dealsRes.value.items || []);
        }
        if (statusRes.status === "fulfilled") {
          setStatus(statusRes.value as PipelineStatus);
        }
      } catch { /* ignore */ }

      // Load articles
      try {
        const res = await fetch(`${API_URL}/api/articles`);
        const data = await res.json();
        setArticles(data.articles || []);
      } catch { /* ignore */ }

      // Load destination guides for the "Découvrir vos futures destinations" collapsible
      try {
        const res = await fetch(`${API_URL}/api/destinations?limit=50`);
        const data = await res.json();
        setDiscoveryGuides(data.items || []);
      } catch { /* ignore */ }

      setLoading(false);
    }
    load();

    // Load user preferences once for the one-way banner — they don't change
    // every 60s, so keep them out of the polling loop.
    (async () => {
      try {
        const prefs = await getPreferences(userId!);
        const ftt = prefs.flight_trip_types && prefs.flight_trip_types.length > 0
          ? prefs.flight_trip_types
          : ["round_trip" as FlightTripType];
        setFlightTripTypes(ftt);
        const dismissed = typeof window !== "undefined"
          && localStorage.getItem("gg_oneway_banner_dismissed") === "1";
        setOnewayBannerDismissed(dismissed);
      } catch { /* ignore */ }
    })();

    const interval = setInterval(load, 60000);
    return () => {
      clearInterval(interval);
      if (sessionCleanup) sessionCleanup();
    };
  }, [router]);

  async function handleCheckout() {
    try {
      const token = localStorage.getItem("gg_token");
      if (!token) {
        alert("Session expirée. Veuillez vous reconnecter.");
        router.push("/login");
        return;
      }
      const res = await fetch(`${API_URL}/api/stripe/create-checkout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      });
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        alert(data.detail || "Erreur lors de la création du paiement. Réessayez.");
      }
    } catch {
      alert("Erreur de connexion au serveur. Réessayez.");
    }
  }

  function handleLogout() {
    localStorage.removeItem("gg_user_id");
    localStorage.removeItem("gg_email");
    localStorage.removeItem("gg_token");
    clearSessionCookie();
    router.push("/");
  }

  const unlockedDeals = allDeals.filter(d => !d.locked);
  const lockedDeals = allDeals.filter(d => d.locked);

  const filteredUnlocked = destFilter === "all" ? unlockedDeals : unlockedDeals.filter(d => d.destination === destFilter);
  const filteredLocked = destFilter === "all" ? lockedDeals : lockedDeals.filter(d => d.destination === destFilter);

  const INITIAL_DEALS_COUNT = 6;
  const visibleUnlocked = showAllDeals ? filteredUnlocked : filteredUnlocked.slice(0, INITIAL_DEALS_COUNT);
  const hasMoreDeals = filteredUnlocked.length > INITIAL_DEALS_COUNT;
  const availableDestinations = Array.from(new Set(allDeals.map(d => d.destination)));

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            <span className="text-[#1E90FF]">Globe</span><span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="text-sm text-gray-400 hidden md:block">{isPremium === true ? "🌟 Premium" : isPremium === false ? "Free" : ""}</span>
            <Link href="/planificateur" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">
              Planificateur
            </Link>
            <Link href="/profile" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">
              Profil
            </Link>
            <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-red-500 transition-colors">
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 md:px-5 py-6 md:py-8">
        {/* One-way migration banner — soft invitation for round-trip-only users */}
        {!onewayBannerDismissed && !flightTripTypes.includes("one_way") && (
          <div className="mb-6 bg-cyan-50 border border-cyan-200 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="text-sm text-[#0A1F3D]">
              <span className="font-semibold">🆕 Nouveaux deals « aller simple » disponibles.</span>{" "}
              Activez-les dans votre profil pour recevoir aussi les promos un sens et les combos malins « 2 billets » moins chers qu&apos;un A/R.
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Link
                href="/profile"
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                Activer →
              </Link>
              <button
                onClick={() => {
                  if (typeof window !== "undefined") {
                    localStorage.setItem("gg_oneway_banner_dismissed", "1");
                  }
                  setOnewayBannerDismissed(true);
                }}
                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
              >
                Plus tard
              </button>
            </div>
          </div>
        )}

        {/* Premium banner — only show once we know the user is NOT premium.
            isPremium === null means the Stripe check hasn't returned yet,
            and showing the banner during that window flashes it to premium users. */}
        {isPremium === false && (
          <div className="mb-6 bg-[#FFFEF9] border border-[#FF6B47] rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold bg-[#FF6B47] text-white px-2.5 py-0.5 rounded-full">🌸 Offre printemps -41%</span>
              </div>
              <h3 className="font-semibold mb-1">Un seul deal suffit à rembourser votre année</h3>
              <p className="text-sm text-[#0A1F3D]/70">
                Accès illimité à tous les deals ≥50%, sans quota hebdomadaire. Alertes Telegram instantanées.
                <span className="font-semibold"> 29€/an</span> <span className="line-through text-[#0A1F3D]/40">59€</span> — soit 2,42€/mois.
                <span className="block mt-1 text-xs text-[#16A34A]">✅ Satisfait ou remboursé 30 jours</span>
              </p>
            </div>
            <button
              onClick={handleCheckout}
              className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-6 py-3 rounded-xl text-sm shrink-0 transition-all"
            >
              Essayer Premium — 29€/an
            </button>
          </div>
        )}


        {/* Deals section */}
        <div className="mb-8">
          <div className="mb-4">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Vos deals</h2>
          </div>

          {loading && <div className="text-center py-12 text-gray-400">Chargement...</div>}

          {!loading && allDeals.length === 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
              <div className="text-4xl mb-3">🔍</div>
              <h3 className="font-semibold text-lg mb-2">Analyse en cours</h3>
              <p className="text-sm text-gray-400 max-w-md mx-auto mb-4">
                Notre pipeline scrape les prix 6 fois par jour depuis 8 aéroports français.
                Les deals apparaîtront dès qu'une anomalie de prix sera détectée.
              </p>
              <p className="text-xs text-gray-300">
                Vous serez alerté sur Telegram dès qu'un deal correspond à vos préférences.
              </p>
            </div>
          )}

          {!loading && allDeals.length > 0 && (<>
            {/* Destination filter pills */}
            {availableDestinations.length > 1 && (
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                <button
                  onClick={() => { setDestFilter("all"); setShowAllDeals(false); }}
                  className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-all border-2"
                  style={{
                    borderColor: destFilter === "all" ? "#FF6B47" : "#F0E6D8",
                    background: destFilter === "all" ? "#FF6B47" : "#FFFEF9",
                    color: destFilter === "all" ? "#fff" : "#0A1F3D",
                  }}
                >
                  Toutes
                </button>
                {availableDestinations.map((code) => (
                  <button
                    key={code}
                    onClick={() => { setDestFilter(code); setShowAllDeals(false); }}
                    className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-all border-2"
                    style={{
                      borderColor: destFilter === code ? "#FF6B47" : "#F0E6D8",
                      background: destFilter === code ? "#FF6B47" : "#FFFEF9",
                      color: destFilter === code ? "#fff" : "#0A1F3D",
                    }}
                  >
                    {code}
                  </button>
                ))}
              </div>
            )}

            {/* Unlocked deals */}
            {visibleUnlocked.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
                {visibleUnlocked.map((deal) => (
                  <FlightDealCard key={deal.id} deal={deal} />
                ))}
              </div>
            )}

            {/* Show more / less */}
            {!showAllDeals && hasMoreDeals && (
              <div className="text-center mt-8">
                <button
                  onClick={() => setShowAllDeals(true)}
                  className="px-8 py-3 rounded-full border-2 border-[#FF6B47] text-[#FF6B47] font-semibold text-sm hover:bg-[#FF6B47] hover:text-white transition-all"
                >
                  Voir plus de deals ({filteredUnlocked.length - INITIAL_DEALS_COUNT} restants)
                </button>
              </div>
            )}
            {showAllDeals && hasMoreDeals && (
              <div className="text-center mt-8">
                <button
                  onClick={() => setShowAllDeals(false)}
                  className="px-6 py-2 rounded-full text-sm text-[#0A1F3D]/50 hover:text-[#0A1F3D] transition-colors"
                >
                  Voir moins
                </button>
              </div>
            )}

            {/* Masked deals — quota atteinte ou >55% pour les free */}
            {isPremium === false && filteredLocked.length > 0 && (
              <div className="mt-10">
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">
                    {unlockedDeals.length === 0 ? "Deals de la semaine" : "Deals supplémentaires"}
                  </h3>
                  <span className="text-xs font-bold bg-[#FF6B47] text-white px-2.5 py-0.5 rounded-full">🔒 Premium</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
                  {filteredLocked.map((deal) => (
                    <div key={deal.id} className="relative">
                      <div className="blur-[3px] pointer-events-none select-none opacity-50">
                        <FlightDealCard deal={deal} />
                      </div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="bg-white/95 border border-[#FF6B47]/40 rounded-2xl px-5 py-4 text-center shadow-lg max-w-[200px]">
                          <div className="text-lg font-bold text-[#FF6B47] mb-0.5">-{Math.round(deal.discount_pct)}%</div>
                          <div className="text-xs text-[#0A1F3D]/70 mb-3 leading-snug">
                            {unlockedDeals.length === 0
                              ? "Limite hebdomadaire atteinte"
                              : "Réservé aux membres Premium"}
                          </div>
                          <button
                            onClick={handleCheckout}
                            className="bg-[#FF6B47] hover:bg-[#E55A38] text-white text-xs font-semibold px-4 py-2 rounded-full transition-all"
                          >
                            Débloquer — 29€/an
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>)}
        </div>

        {/* Découvrir vos futures destinations — collapsible */}
        {discoveryGuides.length > 0 && (
          <details className="mb-8 bg-white border border-gray-100 rounded-2xl">
            <summary className="cursor-pointer px-5 py-4 font-semibold text-[#0A1F3D] flex items-center justify-between">
              <span>🌍 Découvrir vos futures destinations</span>
              <span className="text-sm text-gray-400 font-normal">{discoveryGuides.length} destinations</span>
            </summary>
            <div className="px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {discoveryGuides.map((g) => (
                <Link key={g.iata} href={`/destination/${g.iata.toLowerCase()}`}
                      target="_blank" rel="noopener noreferrer"
                      className="group block overflow-hidden rounded-xl border border-gray-100 hover:border-[#FF6B47] transition-colors">
                  {g.cover_photo && (
                    <div className="relative aspect-video overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={g.cover_photo} alt={g.destination}
                           className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform" />
                    </div>
                  )}
                  <div className="p-3">
                    <div className="text-xs text-gray-400">{g.destination}</div>
                    <div className="font-semibold text-sm text-[#0A1F3D] line-clamp-2">{g.title}</div>
                  </div>
                </Link>
              ))}
            </div>
          </details>
        )}


        {/* CTA: Planificateur (full page lives at /planificateur). Visible to
            free + premium users; gating happens on the destination page. */}
        <div className="mb-8 bg-[#FFFEF9] border border-[#FF6B47]/30 rounded-2xl p-5 flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold text-[#0A1F3D] mb-1">🗺️ Planificateur de voyage</h3>
            <p className="text-sm text-[#0A1F3D]/70">
              Créez des itinéraires personnalisés avec l&apos;IA. {isPremium === false ? "Exclusif aux abonnés Premium." : ""}
            </p>
          </div>
          <Link
            href="/planificateur"
            className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-4 py-2 rounded-xl text-sm shrink-0 transition-all whitespace-nowrap"
          >
            Ouvrir →
          </Link>
        </div>


      </div>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 — Vols à prix cassés
        </div>
      </footer>
    </div>
  );
}
