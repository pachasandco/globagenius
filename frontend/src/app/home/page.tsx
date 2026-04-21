"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFlightDeals, getPipelineStatus, type FlightDeal, type PipelineStatus } from "@/lib/api";
import { initSession } from "@/lib/session";

interface PlanDay {
  day: number;
  title: string;
  morning?: { activity: string };
  afternoon?: { activity: string };
  evening?: { activity: string };
}

interface ChatData {
  type?: string;
  message?: string;
  options?: string[];
  days?: PlanDay[];
  destination?: string;
  duration?: string;
  estimated_budget?: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: ChatData;
}

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

function FlightDealCard({ deal }: { deal: FlightDeal }) {
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
      {/* Savings sticker coral */}
      <div
        className="absolute -top-3 -right-3 w-14 h-14 rounded-full bg-[#FF6B47] text-white flex items-center justify-center font-bold text-sm shadow-[0_8px_20px_rgba(255,107,71,0.35)] z-10"
        style={{ transform: "rotate(-8deg)" }}
      >
        -{discount}%
      </div>

      {/* Premium badge if applicable */}
      {isPremium && (
        <span className="inline-block bg-[#FFC940] text-[#0A1F3D] text-[10px] font-bold px-2 py-0.5 rounded-full mb-2">
          PREMIUM
        </span>
      )}

      {/* Route in DM Serif */}
      <div className="font-[family-name:var(--font-dm-serif)] text-xl md:text-2xl text-[#0A1F3D] mb-1 pr-12">
        {deal.origin} → {deal.destination}
      </div>

      {/* Dates + days */}
      <div className="text-sm text-[#0A1F3D]/60 mb-3">
        {dep} – {ret} · {days} jour{days > 1 ? "s" : ""}
      </div>

      {/* Chips row : airline + stops */}
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        {deal.airline && (
          <span className="bg-[#F0E6D8]/60 text-[#0A1F3D] text-xs px-2.5 py-1 rounded-full">
            ✈️ {deal.airline}
          </span>
        )}
        <span className="bg-[#F0E6D8]/60 text-[#0A1F3D] text-xs px-2.5 py-1 rounded-full">
          {stopsLabel}
        </span>
        <span className="bg-[#ECF4FF] text-[#0088cc] text-xs px-2.5 py-1 rounded-full font-medium">
          👥 {Math.floor(Math.random() * 12) + 3} réservent
        </span>
      </div>

      {/* Price hierarchy */}
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

      {/* CTA footer */}
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

export default function HomePage() {
  const [myDeals, setMyDeals] = useState<FlightDeal[]>([]);
  const [lockedDeals, setLockedDeals] = useState<FlightDeal[]>([]);
  const [, setStatus] = useState<PipelineStatus | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPremium, setIsPremium] = useState(false);
  const [showAllDeals, setShowAllDeals] = useState(false);
  const [destFilter, setDestFilter] = useState<string>("all");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [showPlanner, setShowPlanner] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
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
      // Load user preferences
      try {
        const userId = localStorage.getItem("gg_user_id");
        if (userId) {
          const { getPreferences } = await import("@/lib/api");
          const prefs = await getPreferences(userId);
          console.log("Preferences loaded:", prefs);
        }
      } catch (err) {
        console.error("Failed to load preferences:", err);
      }

      // Check premium status first so we know which deals to fetch
      let isPremiumRef = false;
      try {
        const token = localStorage.getItem("gg_token");
        if (token) {
          const premStatus = await fetch(`${API_URL}/api/stripe/status`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const premData = await premStatus.json();
          isPremiumRef = premData.is_premium || false;
          setIsPremium(isPremiumRef);
        }
      } catch { /* ignore */ }

      // Fetch deals based on premium status
      const plan = isPremiumRef ? "premium" : "free";
      try {
        const [dealsRes, statusRes] = await Promise.allSettled([
          getFlightDeals(plan, 50),
          getPipelineStatus(),
        ]);
        if (dealsRes.status === "fulfilled") {
          setMyDeals(dealsRes.value.items || []);
        }
        if (statusRes.status === "fulfilled") {
          setStatus(statusRes.value as PipelineStatus);
        }
      } catch { /* ignore */ }

      // If free user, also fetch 3 locked premium deals for teaser
      if (!isPremiumRef) {
        try {
          const lockedRes = await getFlightDeals("premium", 3);
          setLockedDeals(lockedRes.items || []);
        } catch { /* ignore */ }
      }

      // Load articles
      try {
        const res = await fetch(`${API_URL}/api/articles`);
        const data = await res.json();
        setArticles(data.articles || []);
      } catch { /* ignore */ }

      setLoading(false);
    }
    load();
    const interval = setInterval(load, 60000);
    return () => {
      clearInterval(interval);
      if (sessionCleanup) sessionCleanup();
    };
  }, [router]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  async function sendChat(text: string) {
    if (!text.trim()) return;
    const userId = localStorage.getItem("gg_user_id") || "anonymous";
    setChatMessages(prev => [...prev, { role: "user", content: text }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/planner/${userId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: "assistant", content: data.message || "", data }]);
    } catch {
      setChatMessages(prev => [...prev, { role: "assistant", content: "Erreur. Réessayez." }]);
    } finally {
      setChatLoading(false);
    }
  }

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
        console.error("Stripe checkout error:", data);
        alert(data.detail || "Erreur lors de la création du paiement. Réessayez.");
      }
    } catch (e) {
      console.error("Checkout failed:", e);
      alert("Erreur de connexion au serveur. Réessayez.");
    }
  }

  function handleLogout() {
    localStorage.removeItem("gg_user_id");
    localStorage.removeItem("gg_email");
    localStorage.removeItem("gg_token");
    router.push("/");
  }

  const filteredByDest = destFilter === "all" ? myDeals : myDeals.filter(d => d.destination === destFilter);
  const INITIAL_DEALS_COUNT = 6;
  const deals = showAllDeals ? filteredByDest : filteredByDest.slice(0, INITIAL_DEALS_COUNT);
  const hasMoreDeals = filteredByDest.length > INITIAL_DEALS_COUNT;
  const availableDestinations = Array.from(new Set(myDeals.map(d => d.destination)));

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="text-gray-900 font-medium">Deals</Link>
            <a href="#guides" className="hover:text-gray-900 transition-colors">Guides</a>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="text-sm text-gray-400 hidden md:block">{isPremium ? "🌟 Premium" : "Free"}</span>
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
        {/* Premium banner */}
        {!isPremium && (
          <div className="mb-6 bg-[#FFFEF9] border border-[#FF6B47] rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold bg-[#FF6B47] text-white px-2.5 py-0.5 rounded-full">🌸 Offre printemps -41%</span>
              </div>
              <h3 className="font-semibold mb-1">Un seul deal suffit à rembourser votre année</h3>
              <p className="text-sm text-[#0A1F3D]/70">
                Tous les deals -30% et plus, erreurs de prix incluses. Alertes Telegram instantanées.
                <span className="font-semibold"> 29€/an</span> <span className="line-through text-[#0A1F3D]/40">59€</span> — soit 2,42€/mois.
                <span className="block mt-1 text-xs text-[#16A34A]">✅ Satisfait ou remboursé 14 jours</span>
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

          {!loading && deals.length === 0 && (
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

          {!loading && deals.length > 0 && (<>
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

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
              {deals.map((deal) => (
                <FlightDealCard key={deal.id} deal={deal} />
              ))}
            </div>

            {/* Show more button */}
            {!showAllDeals && hasMoreDeals && (
              <div className="text-center mt-8">
                <button
                  onClick={() => setShowAllDeals(true)}
                  className="px-8 py-3 rounded-full border-2 border-[#FF6B47] text-[#FF6B47] font-semibold text-sm hover:bg-[#FF6B47] hover:text-white transition-all"
                >
                  Voir plus de deals ({filteredByDest.length - INITIAL_DEALS_COUNT} restants)
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

            {/* Locked premium deals teaser */}
            {!isPremium && lockedDeals.length > 0 && (
              <div className="mt-10">
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Deals Premium</h3>
                  <span className="text-xs font-bold bg-[#FF6B47] text-white px-2.5 py-0.5 rounded-full">🔒 Réservé</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
                  {lockedDeals.map((deal) => (
                    <div key={deal.id} className="relative">
                      <div className="blur-[6px] pointer-events-none opacity-60">
                        <FlightDealCard deal={deal} />
                      </div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="bg-[#FFFEF9] border border-[#FF6B47] rounded-2xl px-6 py-4 text-center shadow-xl">
                          <div className="text-sm font-semibold text-[#0A1F3D] mb-1">-{Math.round(deal.discount_pct)}% détecté</div>
                          <div className="text-xs text-[#0A1F3D]/60 mb-3">Débloquez avec Premium</div>
                          <button
                            onClick={handleCheckout}
                            className="bg-[#FF6B47] hover:bg-[#E55A38] text-white text-xs font-semibold px-4 py-2 rounded-full transition-all"
                          >
                            29€/an →
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

        {/* Guides section */}
        {articles.length > 0 && (
          <div id="guides" className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Guides de voyage</h2>
              <span className="text-sm text-[#0A1F3D]/40">
                {articles.length} guide{articles.length > 1 ? "s" : ""}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {articles.map((article) => (
                <Link key={article.slug} href={`/articles/${article.slug}`} className="group">
                  <div className="relative aspect-[4/3] rounded-xl overflow-hidden mb-2">
                    <img src={article.cover_photo} alt={article.destination} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <div className="absolute bottom-2 left-2">
                      <div className="text-white font-semibold text-sm drop-shadow">{article.destination}</div>
                      <div className="text-white/70 text-[11px]">{article.country}</div>
                    </div>
                  </div>
                  <h3 className="text-sm font-medium group-hover:text-cyan-600 transition-colors line-clamp-1">{article.title}</h3>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Planificateur de voyage integre — Premium only */}
        {!isPremium ? (
          <div className="mb-8 bg-[#FFFEF9] border border-[#FF6B47] rounded-2xl p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-[#0A1F3D] mb-1">🗺️ Planificateur de voyage</h3>
                <p className="text-sm text-[#0A1F3D]/70">Créez des itinéraires sur mesure avec l'IA. Exclusive aux abonnés Premium.</p>
              </div>
              <button
                onClick={handleCheckout}
                className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-4 py-2 rounded-xl text-sm shrink-0 transition-all"
              >
                Débloquer →
              </button>
            </div>
          </div>
        ) : (
          <div className="mb-8">
            <button
              onClick={() => setShowPlanner(!showPlanner)}
              className="w-full flex items-center justify-between mb-4 hover:opacity-75 transition-opacity"
            >
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">🗺️ Planificateur de voyage</h2>
              <span className="text-2xl font-light text-gray-400">{showPlanner ? "−" : "+"}</span>
            </button>
            {showPlanner && (
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden p-6">
                <div className="text-center space-y-6">
                  {/* Calendar */}
                  <div>
                    <h3 className="text-sm font-semibold text-[#0A1F3D] mb-4">Sélectionnez vos dates</h3>
                    <div className="grid grid-cols-7 gap-2 max-w-xs mx-auto mb-4">
                      {/* Days of week headers */}
                      {["L", "M", "M", "J", "V", "S", "D"].map((day) => (
                        <div key={day} className="text-xs font-semibold text-gray-400 py-2">
                          {day}
                        </div>
                      ))}
                      {/* Calendar days */}
                      {Array.from({ length: 35 }).map((_, i) => {
                        const day = i - 3;
                        const isCurrentMonth = day > 0 && day <= 30;
                        return (
                          <button
                            key={i}
                            className={`aspect-square rounded-lg text-sm font-medium transition-all ${
                              isCurrentMonth
                                ? "bg-gray-50 text-[#0A1F3D] hover:bg-[#FF6B47] hover:text-white cursor-pointer"
                                : "text-gray-200"
                            }`}
                          >
                            {isCurrentMonth ? day : ""}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Hint text */}
                  <div className="border-t pt-4">
                    <p className="text-xs text-gray-400">
                      👆 Cliquez sur le titre pour accéder au planificateur complet avec l'IA
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Quick links */}
        <div className="grid sm:grid-cols-2 gap-4">
          <a href="#guides" className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md transition-shadow group">
            <div className="text-xl mb-1">✍️</div>
            <h3 className="font-semibold text-sm group-hover:text-cyan-600 transition-colors">Guides de destinations</h3>
            <p className="text-xs text-gray-400">Guides complets pour préparer votre voyage.</p>
          </a>
          <Link href="/onboarding" className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md transition-shadow group">
            <div className="text-xl mb-1">⚙️</div>
            <h3 className="font-semibold text-sm group-hover:text-cyan-600 transition-colors">Mes préférences</h3>
            <p className="text-xs text-gray-400">Aéroports, destinations, alertes Telegram.</p>
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
