"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  ArrowRight,
  ChevronRight,
  Compass,
  MapPin,
  Send,
  Sparkles,
  Sunrise,
  Sun,
  Moon,
  Wallet,
  Plane,
} from "lucide-react";

import { clearSessionCookie } from "@/lib/api";
import { initSession } from "@/lib/session";
import { Wordmark } from "../_components/Wordmark";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

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

// ─── Pill: a small toggleable choice. Used for destination / duration /
// style. Tinted by colour token so the three rows are visually distinct
// without leaving the design system.
function ChoicePill({
  active,
  onClick,
  tone,
  children,
}: {
  active: boolean;
  onClick: () => void;
  tone: "coral" | "cyan" | "violet";
  children: React.ReactNode;
}) {
  const palette = {
    coral: {
      activeBg: "bg-[var(--color-coral)] text-white border-[var(--color-coral)] shadow-[0_4px_12px_rgba(255,107,71,0.25)]",
      idleHover: "hover:border-[var(--color-coral)]/60 hover:text-[var(--color-coral)]",
    },
    cyan: {
      activeBg: "bg-cyan-500 text-white border-cyan-500 shadow-[0_4px_12px_rgba(6,182,212,0.25)]",
      idleHover: "hover:border-cyan-500/60 hover:text-cyan-700",
    },
    violet: {
      activeBg: "bg-violet-500 text-white border-violet-500 shadow-[0_4px_12px_rgba(139,92,246,0.25)]",
      idleHover: "hover:border-violet-500/60 hover:text-violet-700",
    },
  }[tone];

  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "px-3.5 py-1.5 rounded-full text-sm font-medium border transition-all " +
        (active
          ? palette.activeBg
          : `bg-white border-gray-200 text-gray-700 ${palette.idleHover}`)
      }
    >
      {children}
    </button>
  );
}

// ─── Onboarding form: shown until the user sends a first message. Picks
// up the three core inputs (destination / duration / style) plus a free
// expert prompt and three click-to-try templates.
function OnboardingForm({
  chatInput,
  setChatInput,
  sendChat,
  chatLoading,
}: {
  chatInput: string;
  setChatInput: (v: string) => void;
  sendChat: (t: string) => void;
  chatLoading: boolean;
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
    <Card className="border-gray-100 shadow-[0_4px_24px_rgba(10,31,61,0.05)]">
      <CardContent className="p-6 md:p-8 space-y-7">
        {/* Destination */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <MapPin className="size-4 text-[var(--color-coral)]" />
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-[0.08em]">Destination</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {PLANNER_DESTINATIONS.map((d) => (
              <ChoicePill
                key={d.label}
                tone="coral"
                active={dest === d.label}
                onClick={() => setDest(dest === d.label ? "" : d.label)}
              >
                {d.emoji} {d.label}
              </ChoicePill>
            ))}
          </div>
          <Input
            type="text"
            value={dest && !PLANNER_DESTINATIONS.find(d => d.label === dest) ? dest : ""}
            onChange={(e) => setDest(e.target.value)}
            onFocus={() => {
              if (PLANNER_DESTINATIONS.find(d => d.label === dest)) setDest("");
            }}
            placeholder="Autre destination…"
            className="h-10"
          />
        </div>

        {/* Duration */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Compass className="size-4 text-cyan-600" />
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-[0.08em]">Durée</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {PLANNER_DURATIONS.map((d) => (
              <ChoicePill
                key={d}
                tone="cyan"
                active={duration === d}
                onClick={() => setDuration(duration === d ? "" : d)}
              >
                {d}
              </ChoicePill>
            ))}
          </div>
        </div>

        {/* Style */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-violet-600" />
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-[0.08em]">Style</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {PLANNER_STYLES.map((s) => (
              <ChoicePill
                key={s}
                tone="violet"
                active={style === s}
                onClick={() => setStyle(style === s ? "" : s)}
              >
                {s}
              </ChoicePill>
            ))}
          </div>
        </div>

        {/* Output preview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 rounded-xl bg-gradient-to-br from-[var(--color-cream)] to-[var(--color-coral-50)] border border-[var(--color-coral)]/15 px-4 py-3">
          {[
            { icon: <Plane className="size-3.5" />, label: "Vol optimal" },
            { icon: <MapPin className="size-3.5" />, label: "Quartiers" },
            { icon: <Compass className="size-3.5" />, label: "Itinéraire" },
            { icon: <Wallet className="size-3.5" />, label: "Budget" },
          ].map(({ icon, label }) => (
            <div key={label} className="flex items-center gap-1.5 text-xs text-[var(--color-ink)]/70">
              <span className="text-[var(--color-coral)]">{icon}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>

        <Button
          size="lg"
          onClick={buildAndSend}
          disabled={!canGenerate || chatLoading}
          className="w-full h-11 bg-[var(--color-coral)] text-white hover:bg-[var(--color-coral-hover)] shadow-[0_8px_24px_rgba(255,107,71,0.25)] text-sm font-semibold"
        >
          Créer mon itinéraire
          <ArrowRight className="size-4" />
        </Button>

        <div className="relative">
          <Separator />
          <span className="absolute left-1/2 -translate-x-1/2 -top-2.5 bg-card px-3 text-xs text-gray-400">
            ou essayez un exemple
          </span>
        </div>

        <div className="space-y-2">
          {PLANNER_TEMPLATES.map((t) => (
            <button
              key={t.label}
              type="button"
              onClick={() => sendChat(t.label)}
              disabled={chatLoading}
              className="w-full text-left px-4 py-3 rounded-xl border border-gray-100 hover:border-[var(--color-coral)]/40 hover:bg-[var(--color-coral-50)] transition-all flex items-center justify-between group disabled:opacity-40"
            >
              <span className="text-sm text-gray-700 group-hover:text-[var(--color-coral)] transition-colors">
                {t.label}
              </span>
              <span className="flex items-center gap-2">
                <Badge variant="secondary" className="bg-gray-50 text-gray-500 border border-gray-200">
                  ≈ {t.budget}
                </Badge>
                <ChevronRight className="size-4 text-gray-300 group-hover:text-[var(--color-coral)] transition-colors" />
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setExpertMode(true)}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors underline underline-offset-4 w-full text-center"
        >
          Mode libre — décris toi-même
        </button>

        {expertMode && (
          <div className="flex gap-2">
            <Input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
              placeholder="Ex: 7 jours à Kyoto, couple, budget 2000€, avril…"
              autoFocus
              className="h-10"
            />
            <Button
              size="lg"
              onClick={() => sendChat(chatInput)}
              disabled={chatLoading || !chatInput.trim()}
              className="h-10 bg-[var(--color-coral)] text-white hover:bg-[var(--color-coral-hover)]"
            >
              <Send className="size-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Itinerary card: rendered inside an assistant message when the
// backend returns a "planning" payload with day-by-day data.
function ItineraryCard({ data }: { data: ChatData }) {
  if (!data.days) return null;
  return (
    <div className="mt-3 space-y-2">
      <div className="rounded-lg border border-cyan-100 bg-cyan-50 px-3 py-2 flex items-center justify-between">
        <div className="text-xs font-semibold text-cyan-900">
          {data.destination} · {data.duration}
        </div>
        {data.estimated_budget && (
          <Badge className="bg-white text-cyan-800 border border-cyan-200">
            <Wallet className="size-3" />
            {data.estimated_budget}
          </Badge>
        )}
      </div>
      <div className="space-y-1.5">
        {data.days.map((day) => (
          <Card key={day.day} className="border-gray-100 py-0">
            <CardContent className="p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="font-semibold text-sm text-[var(--color-ink)]">
                  Jour {day.day}
                </div>
                <div className="text-xs text-gray-500">{day.title}</div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5 text-xs">
                {day.morning?.activity && (
                  <div className="flex items-start gap-1.5 text-gray-600">
                    <Sunrise className="size-3.5 text-amber-500 mt-0.5 shrink-0" />
                    <span>{day.morning.activity}</span>
                  </div>
                )}
                {day.afternoon?.activity && (
                  <div className="flex items-start gap-1.5 text-gray-600">
                    <Sun className="size-3.5 text-yellow-500 mt-0.5 shrink-0" />
                    <span>{day.afternoon.activity}</span>
                  </div>
                )}
                {day.evening?.activity && (
                  <div className="flex items-start gap-1.5 text-gray-600">
                    <Moon className="size-3.5 text-indigo-500 mt-0.5 shrink-0" />
                    <span>{day.evening.activity}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── A single chat bubble. Differentiates user vs. assistant with
// avatar, side, background and rich rendering on the assistant side.
function ChatBubble({
  msg,
  onOptionClick,
  loading,
}: {
  msg: ChatMessage;
  onOptionClick: (text: string) => void;
  loading: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-2.5 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="size-8 rounded-full bg-gradient-to-br from-[var(--color-coral)] to-[var(--color-cherry)] flex items-center justify-center shrink-0 shadow-[0_4px_12px_rgba(255,107,71,0.25)]">
          <Sparkles className="size-4 text-white" />
        </div>
      )}
      <div
        className={
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm " +
          (isUser
            ? "bg-[var(--color-ink)] text-white"
            : "bg-white border border-gray-100")
        }
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <div className="prose prose-sm prose-gray max-w-none [&>p]:mb-2 [&>p:last-child]:mb-0 [&>h1]:text-base [&>h2]:text-sm [&>h2]:font-semibold [&>h3]:text-sm [&>h3]:font-semibold [&>ul]:pl-4 [&>ul>li]:mb-0.5 [&>ol]:pl-4">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
        {msg.data?.options && msg.data.options.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2.5">
            {msg.data.options.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => onOptionClick(opt)}
                disabled={loading}
                className="text-[11px] bg-cyan-50 text-cyan-700 border border-cyan-100 px-2.5 py-1 rounded-full hover:bg-cyan-100 disabled:opacity-50 transition-colors"
              >
                {opt}
              </button>
            ))}
          </div>
        )}
        {msg.data?.type === "planning" && <ItineraryCard data={msg.data} />}
      </div>
    </div>
  );
}

// ─── Chat panel: shown after the first user message. Scrollable
// conversation + sticky input. Replaces the onboarding card.
function ChatPanel({
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
  return (
    <Card className="border-gray-100 shadow-[0_4px_24px_rgba(10,31,61,0.05)] overflow-hidden py-0 gap-0">
      <ScrollArea className="h-[520px] md:h-[620px]">
        <div className="p-4 md:p-5 space-y-3">
          {chatMessages.map((msg, i) => (
            <ChatBubble
              key={i}
              msg={msg}
              onOptionClick={sendChat}
              loading={chatLoading}
            />
          ))}
          {chatLoading && (
            <div className="flex gap-2.5 justify-start">
              <div className="size-8 rounded-full bg-gradient-to-br from-[var(--color-coral)] to-[var(--color-cherry)] flex items-center justify-center shrink-0">
                <Sparkles className="size-4 text-white" />
              </div>
              <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3 flex items-center gap-1">
                <span className="size-2 rounded-full bg-gray-300 animate-bounce" />
                <span className="size-2 rounded-full bg-gray-300 animate-bounce [animation-delay:150ms]" />
                <span className="size-2 rounded-full bg-gray-300 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
      </ScrollArea>
      <div className="border-t border-gray-100 p-3 flex gap-2 bg-white">
        <Input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !chatLoading && sendChat(chatInput)}
          placeholder="Continuez la conversation…"
          className="h-10 flex-1"
        />
        <Button
          size="lg"
          onClick={() => sendChat(chatInput)}
          disabled={chatLoading || !chatInput.trim()}
          className="h-10 bg-[var(--color-coral)] text-white hover:bg-[var(--color-coral-hover)]"
        >
          <Send className="size-4" />
        </Button>
      </div>
    </Card>
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
    <div className="min-h-screen bg-[var(--color-cream)]">
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[80px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            <Wordmark />
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="text-sm text-gray-400 hidden md:block">
              {isPremium === true ? "🌟 Premium" : isPremium === false ? "Free" : ""}
            </span>
            <Link href="/home" className="text-sm text-gray-500 hover:text-[var(--color-ink)] transition-colors">
              Accueil
            </Link>
            <Link href="/profile" className="text-sm text-gray-500 hover:text-[var(--color-ink)] transition-colors">
              Profil
            </Link>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-red-500 transition-colors"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-4 md:px-5 py-8 md:py-12">
        {isPremium === false ? (
          <Card className="border-[var(--color-coral)]/30 bg-gradient-to-br from-[var(--color-cream-pure)] to-[var(--color-coral-50)]">
            <CardContent className="p-6 md:p-8">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
                <div className="max-w-xl">
                  <Badge className="bg-[var(--color-coral)] text-white mb-3">
                    🗺️ Premium
                  </Badge>
                  <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl md:text-3xl text-[var(--color-ink)] mb-2">
                    Planificateur de voyage
                  </h1>
                  <p className="text-sm md:text-base text-[var(--color-ink)]/70">
                    Créez des itinéraires personnalisés avec l&apos;IA — destination, durée, ambiance,
                    jour par jour. Exclusif aux abonnés Premium.
                  </p>
                </div>
                <Button
                  size="lg"
                  onClick={handleCheckout}
                  className="h-11 bg-[var(--color-coral)] text-white hover:bg-[var(--color-coral-hover)] shadow-[0_8px_24px_rgba(255,107,71,0.25)] text-sm font-semibold shrink-0"
                >
                  Débloquer — 29€/an
                  <ArrowRight className="size-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : isPremium === true ? (
          <>
            <header className="mb-7 md:mb-9">
              <Badge className="bg-[var(--color-coral)]/10 text-[var(--color-coral)] border-[var(--color-coral)]/30 mb-3">
                <Sparkles className="size-3" />
                Planificateur IA
              </Badge>
              <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl text-[var(--color-ink)] mb-2">
                Construis ton prochain voyage
              </h1>
              <p className="text-sm md:text-base text-[var(--color-ink)]/65 max-w-xl">
                Choisis une destination, une durée et une ambiance. L&apos;assistant te prépare
                un itinéraire jour par jour avec budget, transports et bonnes adresses.
              </p>
            </header>
            {chatMessages.length === 0 ? (
              <OnboardingForm
                chatInput={chatInput}
                setChatInput={setChatInput}
                sendChat={sendChat}
                chatLoading={chatLoading}
              />
            ) : (
              <ChatPanel
                chatMessages={chatMessages}
                chatLoading={chatLoading}
                chatInput={chatInput}
                setChatInput={setChatInput}
                sendChat={sendChat}
                chatEndRef={chatEndRef}
              />
            )}
          </>
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
