"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getPackages, getPipelineStatus, type Package, type PipelineStatus } from "@/lib/api";

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

function DealCard({ pkg }: { pkg: Package }) {
  const nights = Math.round(
    (new Date(pkg.return_date).getTime() - new Date(pkg.departure_date).getTime()) / 86400000
  );
  const dep = new Date(pkg.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const ret = new Date(pkg.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const isPremium = pkg.discount_pct >= 40;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className={`px-4 py-3 flex items-center justify-between ${isPremium ? "bg-gray-900" : "bg-gray-700"}`}>
        <div>
          <div className="text-white text-sm font-semibold">{pkg.origin} → {pkg.destination}</div>
          <div className="text-gray-400 text-xs">{dep} – {ret} · {nights} nuits</div>
        </div>
        <div className="flex items-center gap-2">
          {isPremium && <span className="bg-amber-400 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-full">PREMIUM</span>}
          <div className={`text-white text-xs font-bold px-2.5 py-1 rounded-full ${isPremium ? "bg-red-500" : "bg-orange-500"}`}>
            -{Math.round(pkg.discount_pct)}%
          </div>
        </div>
      </div>
      <div className="p-4">
        {pkg.ai_description && <p className="text-sm text-gray-500 italic mb-3 leading-relaxed">{pkg.ai_description}</p>}
        <div className="flex items-end justify-between mb-2">
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
        {pkg.ai_tip && (
          <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 text-xs text-amber-800">💡 {pkg.ai_tip}</div>
        )}
        {pkg.ai_tags && pkg.ai_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {pkg.ai_tags.map((tag: string) => (
              <span key={tag} className="text-[11px] text-cyan-600 bg-cyan-50 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [premiumDeals, setPremiumDeals] = useState<Package[]>([]);
  const [freeDeals, setFreeDeals] = useState<Package[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"premium" | "free">("premium");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const userEmail = localStorage.getItem("gg_email");
    if (!userId) {
      router.push("/login");
      return;
    }
    setEmail(userEmail || "");

    async function load() {
      try {
        const [premRes, freeRes, statusRes] = await Promise.allSettled([
          getPackages(0, 50, "premium"),
          getPackages(0, 50, "free"),
          getPipelineStatus(),
        ]);
        if (premRes.status === "fulfilled") {
          const d = premRes.value as { packages?: Package[]; items?: Package[] };
          setPremiumDeals(d?.packages || d?.items || []);
        }
        if (freeRes.status === "fulfilled") {
          const d = freeRes.value as { packages?: Package[]; items?: Package[] };
          setFreeDeals(d?.packages || d?.items || []);
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
    return () => clearInterval(interval);
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

  // Get unique destinations from deals for planner suggestions
  const detectedDestinations = [...new Set([
    ...premiumDeals.map(d => d.destination),
    ...freeDeals.map(d => d.destination),
  ])].slice(0, 6);

  function handleLogout() {
    localStorage.removeItem("gg_user_id");
    localStorage.removeItem("gg_email");
    localStorage.removeItem("gg_token");
    router.push("/");
  }

  const deals = activeTab === "premium" ? premiumDeals : freeDeals;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white font-bold text-sm">G</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="text-gray-900 font-medium">Deals</Link>
            <Link href="/articles" className="hover:text-gray-900 transition-colors">Articles</Link>
            <Link href="/planner" className="hover:text-gray-900 transition-colors">Planificateur</Link>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="text-sm text-gray-400 hidden md:block">{email}</span>
            <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-red-500 transition-colors">
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 md:px-5 py-6 md:py-8">
        {/* Status bar */}
        {status && (
          <div className="grid grid-cols-2 md:flex md:flex-wrap gap-4 md:gap-6 mb-6 p-4 md:p-5 bg-white rounded-2xl border border-gray-100">
            <div>
              <div className="text-2xl font-bold">{premiumDeals.length + freeDeals.length}</div>
              <div className="text-xs text-gray-400">Deals actifs</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{status.active_baselines}</div>
              <div className="text-xs text-gray-400">Routes surveillées</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{(status.recent_scrapes || []).length}</div>
              <div className="text-xs text-gray-400">Scrapes récents</div>
            </div>
            <div className="md:ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400">Pipeline actif · 6x/jour</span>
            </div>
          </div>
        )}

        {/* Deals section */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Vos deals</h2>
            <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1 self-start sm:self-auto">
              <button
                onClick={() => setActiveTab("premium")}
                className={`px-3 py-2 rounded-lg text-xs md:text-sm font-semibold transition-all ${activeTab === "premium" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
              >
                ⭐ Premium -{">"}40%
                {premiumDeals.length > 0 && <span className="ml-1 bg-amber-100 text-amber-700 text-[10px] md:text-xs px-1.5 py-0.5 rounded-full">{premiumDeals.length}</span>}
              </button>
              <button
                onClick={() => setActiveTab("free")}
                className={`px-3 py-2 rounded-lg text-xs md:text-sm font-semibold transition-all ${activeTab === "free" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
              >
                🆓 Gratuit -20 à -39%
                {freeDeals.length > 0 && <span className="ml-1 bg-gray-200 text-gray-600 text-[10px] md:text-xs px-1.5 py-0.5 rounded-full">{freeDeals.length}</span>}
              </button>
            </div>
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

          {!loading && deals.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
              {deals.map((pkg) => (
                <DealCard key={pkg.id} pkg={pkg} />
              ))}
            </div>
          )}
        </div>

        {/* Articles section */}
        {articles.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Guides de voyage</h2>
              <Link href="/articles" className="text-sm font-semibold text-cyan-600 hover:underline">
                Tout voir →
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {articles.slice(0, 4).map((article) => (
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

        {/* Planificateur de voyage integre */}
        <div className="mb-8">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-4">🗺️ Planificateur de voyage</h2>
          <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
            {/* Chat messages */}
            <div className="h-[300px] md:h-[350px] overflow-y-auto p-4 md:p-5 space-y-3">
              {chatMessages.length === 0 && (
                <div className="text-center py-8">
                  <div className="text-3xl mb-3">✈️</div>
                  <p className="text-sm text-gray-500 mb-4">
                    Dites-moi votre destination et vos dates, je vous prépare un programme sur mesure.
                  </p>
                  {/* Destination suggestions from detected deals */}
                  <div className="flex flex-wrap justify-center gap-2">
                    {detectedDestinations.length > 0 ? (
                      detectedDestinations.map(dest => (
                        <button key={dest} onClick={() => sendChat(`Je pars à ${dest} 7 jours`)}
                          className="text-xs bg-cyan-50 text-cyan-700 border border-cyan-100 px-3 py-1.5 rounded-full hover:bg-cyan-100 transition-colors">
                          {dest}
                        </button>
                      ))
                    ) : (
                      ["Lisbonne", "Barcelone", "Rome", "Marrakech", "Prague", "Athènes"].map(dest => (
                        <button key={dest} onClick={() => sendChat(`Je pars à ${dest} 7 jours en mai`)}
                          className="text-xs bg-cyan-50 text-cyan-700 border border-cyan-100 px-3 py-1.5 rounded-full hover:bg-cyan-100 transition-colors">
                          {dest}
                        </button>
                      ))
                    )}
                  </div>
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
              <div ref={chatEndRef} />
            </div>
            {/* Input */}
            <div className="border-t border-gray-100 p-3 flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
                placeholder="Ex: Je pars à Lisbonne 5 jours en mai..."
                className="flex-1 px-3 py-2 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm"
                disabled={chatLoading}
              />
              <button onClick={() => sendChat(chatInput)} disabled={chatLoading || !chatInput.trim()}
                className="bg-gray-900 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-black disabled:opacity-50 shrink-0">
                Envoyer
              </button>
            </div>
          </div>
        </div>

        {/* Quick links */}
        <div className="grid sm:grid-cols-2 gap-4">
          <Link href="/articles" className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md transition-shadow group">
            <div className="text-xl mb-1">✍️</div>
            <h3 className="font-semibold text-sm group-hover:text-cyan-600 transition-colors">Guides de destinations</h3>
            <p className="text-xs text-gray-400">Articles complets rédigés par IA.</p>
          </Link>
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
          Globe Genius © 2026 — Packages voyage à prix cassés détectés par IA
        </div>
      </footer>
    </div>
  );
}
