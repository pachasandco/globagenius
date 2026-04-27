"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFlightDeals, getPipelineStatus, clearSessionCookie, type FlightDeal, type PipelineStatus } from "@/lib/api";
import { initSession } from "@/lib/session";
import { FlightDealCard } from "@/components/FlightDealCard";
import ReactMarkdown from "react-markdown";

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

const PLANNER_DESTINATIONS = [
  { label: "Tokyo", emoji: "🇯🇵" },
  { label: "Lisbonne", emoji: "🇵🇹" },
  { label: "Bali", emoji: "🇮🇩" },
  { label: "New York", emoji: "🇺🇸" },
  { label: "Marrakech", emoji: "🇲🇦" },
  { label: "Barcelone", emoji: "🇪🇸" },
];

const PLANNER_DURATIONS = ["Week-end", "1 semaine", "2 semaines", "3 semaines"];
const PLANNER_STYLES = ["Budget", "Food", "Aventure", "Romantique", "Premium"];

const PLANNER_TEMPLATES = [
  { label: "7 jours à Tokyo en avril", budget: "1 500 €" },
  { label: "Week-end pas cher en Europe depuis Paris", budget: "300 €" },
  { label: "10 jours au Japon en famille", budget: "3 500 €" },
];

function PlannerBlock({
  chatMessages,
  chatLoading,
  chatInput,
  setChatInput,
  sendChat,
  chatEndRef,
  showPlanner,
  setShowPlanner,
}: {
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  chatInput: string;
  setChatInput: (v: string) => void;
  sendChat: (t: string) => void;
  chatEndRef: React.RefObject<HTMLDivElement | null>;
  showPlanner: boolean;
  setShowPlanner: (v: boolean) => void;
}) {
  const [dest, setDest] = useState("");
  const [duration, setDuration] = useState("");
  const [style, setStyle] = useState("");
  const [expertMode, setExpertMode] = useState(false);

  function buildAndSend() {
    const parts: string[] = [];
    if (dest) parts.push(`destination : ${dest}`);
    if (duration) parts.push(duration);
    if (style) parts.push(`ambiance ${style.toLowerCase()}`);
    const prompt = parts.length > 0
      ? `Planifie-moi un voyage — ${parts.join(", ")}`
      : chatInput.trim();
    if (!prompt) return;
    sendChat(prompt);
    setDest("");
    setDuration("");
    setStyle("");
  }

  const canGenerate = !!(dest || duration || style);

  return (
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

          {chatMessages.length === 0 ? (
            /* ── Onboarding actif ── */
            <div className="p-5 md:p-6 space-y-6">
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Destination</p>
                <div className="flex flex-wrap gap-2 mb-3">
                  {PLANNER_DESTINATIONS.map((d) => (
                    <button
                      key={d.label}
                      onClick={() => setDest(dest === d.label ? "" : d.label)}
                      className="px-3 py-1.5 rounded-full text-sm border-2 font-medium transition-all"
                      style={{
                        borderColor: dest === d.label ? "#FF6B47" : "#e5e7eb",
                        background: dest === d.label ? "#FF6B47" : "white",
                        color: dest === d.label ? "white" : "#374151",
                      }}
                    >
                      {d.emoji} {d.label}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  value={dest && !PLANNER_DESTINATIONS.find(d => d.label === dest) ? dest : ""}
                  onChange={(e) => setDest(e.target.value)}
                  onFocus={() => {
                    if (PLANNER_DESTINATIONS.find(d => d.label === dest)) setDest("");
                  }}
                  placeholder="Autre destination..."
                  className="w-full text-sm bg-gray-50 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-[#FF6B47]/30 border border-gray-100"
                />
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Durée</p>
                <div className="flex flex-wrap gap-2">
                  {PLANNER_DURATIONS.map((d) => (
                    <button
                      key={d}
                      onClick={() => setDuration(duration === d ? "" : d)}
                      className="px-3 py-1.5 rounded-full text-sm border-2 font-medium transition-all"
                      style={{
                        borderColor: duration === d ? "#06b6d4" : "#e5e7eb",
                        background: duration === d ? "#ecfeff" : "white",
                        color: duration === d ? "#0e7490" : "#374151",
                      }}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Style</p>
                <div className="flex flex-wrap gap-2">
                  {PLANNER_STYLES.map((s) => (
                    <button
                      key={s}
                      onClick={() => setStyle(style === s ? "" : s)}
                      className="px-3 py-1.5 rounded-full text-sm border-2 font-medium transition-all"
                      style={{
                        borderColor: style === s ? "#8b5cf6" : "#e5e7eb",
                        background: style === s ? "#f5f3ff" : "white",
                        color: style === s ? "#6d28d9" : "#374151",
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preview de sortie */}
              <div className="bg-[#FFF8F0] border border-[#FF6B47]/20 rounded-xl px-4 py-3 text-xs text-[#0A1F3D]/60 flex flex-wrap gap-x-4 gap-y-1">
                <span>✈️ Vol optimal</span>
                <span>🏨 Quartiers recommandés</span>
                <span>📅 Itinéraire jour par jour</span>
                <span>💰 Budget détaillé</span>
              </div>

              <button
                onClick={buildAndSend}
                disabled={!canGenerate || chatLoading}
                className="w-full bg-[#FF6B47] hover:bg-[#E55A38] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all text-sm"
              >
                Créer mon itinéraire →
              </button>

              {/* Séparateur templates */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-100" /></div>
                <div className="relative flex justify-center"><span className="bg-white px-3 text-xs text-gray-400">ou essayez un exemple</span></div>
              </div>

              <div className="space-y-2">
                {PLANNER_TEMPLATES.map((t) => (
                  <button
                    key={t.label}
                    onClick={() => sendChat(t.label)}
                    disabled={chatLoading}
                    className="w-full text-left px-4 py-3 rounded-xl border border-gray-100 hover:border-[#FF6B47]/40 hover:bg-[#FFF8F0] transition-all group disabled:opacity-40"
                  >
                    <span className="text-sm text-gray-700 group-hover:text-[#FF6B47] transition-colors">{t.label}</span>
                    <span className="ml-2 text-xs text-gray-400">≈ {t.budget}</span>
                  </button>
                ))}
              </div>

              <button
                onClick={() => setExpertMode(true)}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors underline underline-offset-2 w-full text-center"
              >
                Mode libre — décrire moi-même
              </button>

              {expertMode && (
                <div className="flex gap-2 mt-1">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
                    placeholder="Ex: 7 jours à Kyoto, couple, budget 2000€, avril..."
                    className="flex-1 text-sm bg-gray-50 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-[#FF6B47]/30 border border-gray-100"
                    autoFocus
                  />
                  <button
                    onClick={() => sendChat(chatInput)}
                    disabled={chatLoading || !chatInput.trim()}
                    className="bg-[#FF6B47] hover:bg-[#E55A38] text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-40 transition-colors"
                  >
                    →
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* ── Conversation en cours ── */
            <>
              <div className="h-[300px] md:h-[380px] overflow-y-auto p-4 md:p-5 space-y-3">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                      msg.role === "user" ? "bg-gray-900 text-white" : "bg-gray-50 border border-gray-100"
                    }`}>
                      {msg.role === "assistant" ? (
                        <div className="prose prose-sm prose-gray max-w-none [&>p]:mb-2 [&>h1]:text-base [&>h2]:text-sm [&>h2]:font-semibold [&>h3]:text-sm [&>h3]:font-semibold [&>ul]:pl-4 [&>ul>li]:mb-0.5 [&>ol]:pl-4">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      )}
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
                            {msg.data.destination} · {msg.data.duration} · Budget : {msg.data.estimated_budget}
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
                <div ref={chatEndRef} />
              </div>
              <div className="border-t border-gray-100 p-3 flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
                  placeholder="Continuez la conversation..."
                  className="flex-1 text-sm bg-gray-50 rounded-xl px-4 py-2.5 outline-none focus:ring-2 focus:ring-[#FF6B47]/30 border border-gray-100"
                />
                <button
                  onClick={() => sendChat(chatInput)}
                  disabled={chatLoading || !chatInput.trim()}
                  className="bg-[#FF6B47] hover:bg-[#E55A38] text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-40 transition-colors"
                >
                  →
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
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
  const [showPlanner, setShowPlanner] = useState(true);
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
          <PlannerBlock
            chatMessages={chatMessages}
            chatLoading={chatLoading}
            chatInput={chatInput}
            setChatInput={setChatInput}
            sendChat={sendChat}
            chatEndRef={chatEndRef}
            showPlanner={showPlanner}
            setShowPlanner={setShowPlanner}
          />
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
