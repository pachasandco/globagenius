"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PlanDay {
  day: number;
  title: string;
  morning: { activity: string; description: string; duration: string; cost: string };
  lunch: { restaurant: string; cuisine: string; budget: string };
  afternoon: { activity: string; description: string; duration: string; cost: string };
  evening: { activity: string; description: string; budget: string };
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  data?: {
    type: string;
    message?: string;
    options?: string[];
    days?: PlanDay[];
    tips?: string[];
    estimated_budget?: string;
    destination?: string;
    duration?: string;
    style?: string;
  };
}

export default function PlannerPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id") || "anonymous";
    setUserId(id);
    // Welcome message
    setMessages([{
      role: "assistant",
      content: "Bonjour ! Je suis votre planificateur de voyage Globe Genius. Dites-moi votre destination et vos dates, et je vous prépare un programme sur mesure.",
      data: { type: "question", message: "Où souhaitez-vous partir ?", options: ["Lisbonne", "Barcelone", "Rome", "Marrakech", "Prague", "Autre destination"] }
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/planner/${userId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: data.message || "",
        data,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Désolé, une erreur est survenue. Réessayez.",
        data: { type: "error" },
      }]);
    } finally {
      setLoading(false);
    }
  }

  async function resetConversation() {
    await fetch(`${API_URL}/api/planner/${userId}/reset`, { method: "POST" });
    setMessages([{
      role: "assistant",
      content: "Conversation réinitialisée. Où souhaitez-vous partir ?",
      data: { type: "question", message: "Où souhaitez-vous partir ?" }
    }]);
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-8 h-8" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <span className="text-sm text-gray-400 hidden sm:block">Planificateur de voyage</span>
            <span className="bg-amber-100 text-amber-700 text-[10px] font-bold px-2 py-0.5 rounded-full">PREMIUM</span>
          </div>
        </div>
      </nav>

      {/* Chat area */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-4 md:px-5 py-4 md:py-6 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-100 shadow-sm"
              }`}>
                {/* Text message */}
                {msg.content && <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>}

                {/* Options */}
                {msg.data?.options && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {msg.data.options.map((opt) => (
                      <button
                        key={opt}
                        onClick={() => sendMessage(opt)}
                        disabled={loading}
                        className="text-xs bg-cyan-50 text-cyan-700 border border-cyan-100 px-3 py-1.5 rounded-full hover:bg-cyan-100 transition-colors disabled:opacity-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                )}

                {/* Planning */}
                {msg.data?.type === "planning" && msg.data.days && (
                  <div className="mt-4 space-y-4">
                    <div className="bg-cyan-50 rounded-xl p-3 text-center">
                      <div className="font-semibold text-cyan-900">{msg.data.destination} · {msg.data.duration}</div>
                      <div className="text-xs text-cyan-600">{msg.data.style} · Budget estimé : {msg.data.estimated_budget}</div>
                    </div>
                    {msg.data.days.map((day) => (
                      <div key={day.day} className="border border-gray-100 rounded-xl overflow-hidden">
                        <div className="bg-gray-50 px-4 py-2 font-semibold text-sm">
                          Jour {day.day} — {day.title}
                        </div>
                        <div className="p-4 space-y-3 text-sm">
                          <div>
                            <span className="text-amber-500 font-medium">🌅 Matin</span>
                            <p className="text-gray-700">{day.morning.activity}</p>
                            <p className="text-gray-400 text-xs">{day.morning.description} · {day.morning.duration} · {day.morning.cost}</p>
                          </div>
                          <div>
                            <span className="text-orange-500 font-medium">🍽 Déjeuner</span>
                            <p className="text-gray-700">{day.lunch.restaurant}</p>
                            <p className="text-gray-400 text-xs">{day.lunch.cuisine} · {day.lunch.budget}</p>
                          </div>
                          <div>
                            <span className="text-blue-500 font-medium">☀️ Après-midi</span>
                            <p className="text-gray-700">{day.afternoon.activity}</p>
                            <p className="text-gray-400 text-xs">{day.afternoon.description} · {day.afternoon.duration} · {day.afternoon.cost}</p>
                          </div>
                          <div>
                            <span className="text-purple-500 font-medium">🌙 Soirée</span>
                            <p className="text-gray-700">{day.evening.activity}</p>
                            <p className="text-gray-400 text-xs">{day.evening.description} · {day.evening.budget}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                    {msg.data.tips && (
                      <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
                        <div className="font-semibold text-sm text-amber-900 mb-2">💡 Conseils</div>
                        <ul className="space-y-1">
                          {msg.data.tips.map((tip, j) => (
                            <li key={j} className="text-xs text-amber-800">• {tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-2 h-2 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="sticky bottom-0 bg-white border-t border-gray-100 px-4 md:px-5 py-3 md:py-4">
        <div className="max-w-4xl mx-auto flex gap-2 md:gap-3">
          <button
            onClick={resetConversation}
            className="px-2.5 py-2.5 rounded-xl border border-gray-200 text-gray-400 text-sm hover:bg-gray-50 transition-colors shrink-0"
            title="Nouvelle conversation"
          >
            ↻
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && sendMessage(input)}
            placeholder="Ex: Je pars à Lisbonne 5 jours..."
            className="flex-1 px-3 py-2.5 md:px-4 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm min-w-0"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="bg-gray-900 text-white px-3 md:px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-black transition-colors disabled:opacity-50 shrink-0"
          >
            <span className="hidden sm:inline">Envoyer</span>
            <span className="sm:hidden">→</span>
          </button>
        </div>
      </div>
    </div>
  );
}
