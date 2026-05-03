"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearSessionCookie } from "@/lib/api";
import { initSession } from "@/lib/session";
import ReactMarkdown from "react-markdown";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

function PlannerInline({
  chatMessages,
  chatLoading,
  chatInput,
  setChatInput,
  sendChat,
  chatEndRef,
}: {
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  chatInput: string;
  setChatInput: (v: string) => void;
  sendChat: (t: string) => void;
  chatEndRef: React.RefObject<HTMLDivElement | null>;
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
    <div>
      <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl mb-2">📅 Planificateur de voyage</h1>
      <p className="text-sm text-gray-500 mb-6">
        Créez votre itinéraire sur mesure avec l&apos;IA — destination, durée, ambiance.
      </p>

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
            <div className="h-[420px] md:h-[560px] overflow-y-auto p-4 md:p-5 space-y-3">
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
    </div>
  );
}

export default function PlanificateurPage() {
  const router = useRouter();
  const [isPremium, setIsPremium] = useState<boolean | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    if (!userId) {
      router.push("/login");
      return;
    }

    const sessionCleanup = initSession();

    (async () => {
      try {
        const token = localStorage.getItem("gg_token");
        if (token) {
          const premStatus = await fetch(`${API_URL}/api/stripe/status`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const premData = await premStatus.json();
          setIsPremium(premData.is_premium || false);
        } else {
          setIsPremium(false);
        }
      } catch {
        setIsPremium(false);
      }
    })();

    return () => {
      if (sessionCleanup) sessionCleanup();
    };
  }, [router]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  async function sendChat(text: string) {
    if (!text.trim()) return;
    const userId = localStorage.getItem("gg_user_id") || "anonymous";
    const token = localStorage.getItem("gg_token");
    setChatMessages(prev => [...prev, { role: "user", content: text }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/planner/${userId}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        },
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
            <Link href="/home" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">
              Accueil
            </Link>
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

      <main className="max-w-6xl mx-auto px-4 md:px-5 py-6 md:py-8">
        {isPremium === false ? (
          <div className="mb-8 bg-[#FFFEF9] border border-[#FF6B47] rounded-2xl p-6 md:p-8">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl md:text-3xl mb-2">🗺️ Planificateur de voyage</h1>
                <p className="text-sm md:text-base text-[#0A1F3D]/70 max-w-xl">
                  Créez des itinéraires personnalisés avec l&apos;IA — destination, durée, ambiance, jour par jour.
                  Exclusif aux abonnés Premium.
                </p>
              </div>
              <button
                onClick={handleCheckout}
                className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-6 py-3 rounded-xl text-sm shrink-0 transition-all"
              >
                Débloquer — 29€/an
              </button>
            </div>
          </div>
        ) : isPremium === true ? (
          <PlannerInline
            chatMessages={chatMessages}
            chatLoading={chatLoading}
            chatInput={chatInput}
            setChatInput={setChatInput}
            sendChat={sendChat}
            chatEndRef={chatEndRef}
          />
        ) : null}
      </main>

      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 — Vols à prix cassés
        </div>
      </footer>
    </div>
  );
}
