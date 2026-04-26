"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFlightDeals, getPipelineStatus, clearSessionCookie, type FlightDeal, type PipelineStatus } from "@/lib/api";
import { initSession } from "@/lib/session";
import { FlightDealCard } from "@/components/FlightDealCard";

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

export default function HomePage() {
  const [allDeals, setAllDeals] = useState<FlightDeal[]>([]);
  const [, setStatus] = useState<PipelineStatus | null>(null);
  const [, setArticles] = useState<Article[]>([]);
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
          getFlightDeals("free", 50),
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
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="text-gray-900 font-medium">Deals</Link>
            <Link href="/articles" className="hover:text-gray-900 transition-colors">Destinations</Link>
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
                  <FlightDealCard key={deal.id} deal={deal} onUpgrade={handleCheckout} />
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

            {/* Locked deals — CTA upgrade directement dans la card */}
            {!isPremium && filteredLocked.length > 0 && (
              <div className="mt-10">
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">
                    {unlockedDeals.length === 0 ? "Deals de la semaine" : "Deals supplémentaires"}
                  </h3>
                  <span className="text-xs font-bold bg-[#FF6B47] text-white px-2.5 py-0.5 rounded-full">🔒 Premium</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
                  {filteredLocked.map((deal) => (
                    <FlightDealCard key={deal.id} deal={deal} onUpgrade={handleCheckout} />
                  ))}
                </div>
              </div>
            )}
          </>)}
        </div>


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
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">📅 Planificateur de voyage</h2>
              <span className="text-2xl font-light text-gray-400">{showPlanner ? "−" : "+"}</span>
            </button>
            {showPlanner && (
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                {/* Chat messages */}
                <div className="h-[300px] md:h-[350px] overflow-y-auto p-4 md:p-5 space-y-3">
                  {chatMessages.length === 0 && (
                    <div className="text-center py-8">
                      <div className="text-3xl mb-3">✈️</div>
                      <p className="text-sm text-gray-500">
                        Dites-moi votre destination et vos dates, je vous prépare un programme sur mesure.
                      </p>
                    </div>
                  )}
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                        msg.role === "user" ? "bg-gray-900 text-white" : "bg-gray-50 border border-gray-100"
                      }`}>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        {msg.data?.options && msg.data.options.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {msg.data.options.map(opt => (
                              <button key={opt} onClick={() => sendChat(opt)} disabled={chatLoading}
                                className="text-[11px] bg-cyan-50 text-cyan-700 border border-cyan-100 px-2 py-1 rounded-full hover:bg-cyan-100 disabled:opacity-50">
                                {opt}
                              </button>
                            ))}
                          </div>
                        )}
                        {msg.data?.type === "planning" && msg.data?.days && (
                          <div className="mt-3 space-y-2">
                            <div className="bg-cyan-50 rounded-lg p-2 text-center text-xs font-semibold text-cyan-900">
                              {msg.data.destination} · {msg.data.duration} · Budget: {msg.data.estimated_budget}
                            </div>
                            {msg.data.days.map(day => (
                              <div key={day.day} className="border border-gray-100 rounded-lg p-2 text-xs">
                                <div className="font-semibold mb-1">Jour {day.day} — {day.title}</div>
                                <div className="text-gray-500">🌅 {day.morning?.activity} · ☀️ {day.afternoon?.activity} · 🌙 {day.evening?.activity}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-2.5">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" />
                          <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: "150ms" }} />
                          <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                {/* Input */}
                <div className="border-t border-gray-100 p-3 flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
                    placeholder="Ex: Je pars à Tokyo 7 jours en avril..."
                    className="flex-1 text-sm bg-gray-50 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-cyan-100"
                  />
                  <button
                    onClick={() => sendChat(chatInput)}
                    disabled={chatLoading || !chatInput.trim()}
                    className="bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm font-medium disabled:opacity-40 hover:bg-gray-700 transition-colors"
                  >
                    →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

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
