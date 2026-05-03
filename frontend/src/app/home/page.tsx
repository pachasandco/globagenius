"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getPreferences, getTelegramStatus, clearSessionCookie, type FlightTripType } from "@/lib/api";
import { initSession } from "@/lib/session";
import { Wordmark } from "../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TELEGRAM_BOT_URL = "https://t.me/Globegenius_bot";

type Guide = {
  iata: string;
  destination: string;
  title: string;
  cover_photo: string;
};

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  // null = unknown (Stripe check not back yet). Avoids flashing the premium
  // upsell banner to users who turn out to be premium.
  const [isPremium, setIsPremium] = useState<boolean | null>(null);
  const [guides, setGuides] = useState<Guide[]>([]);
  const [telegramConnected, setTelegramConnected] = useState<boolean | null>(null);
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
      // Premium status, Telegram link state and the destination guides are
      // the only data the home page needs now that "Vos deals" is gone.
      // Real-time deals live in Telegram — no point polling them here.
      const token = localStorage.getItem("gg_token");

      const [premiumRes, guidesRes, tgRes] = await Promise.allSettled([
        token
          ? fetch(`${API_URL}/api/stripe/status`, {
              headers: { Authorization: `Bearer ${token}` },
            }).then(r => r.json())
          : Promise.resolve({ is_premium: false }),
        // Pull a generous slice (server caps at 50). All published guides
        // show up here, ordered by recency.
        fetch(`${API_URL}/api/destinations?limit=50`).then(r => r.json()),
        getTelegramStatus(userId!),
      ]);

      if (premiumRes.status === "fulfilled") {
        setIsPremium(premiumRes.value?.is_premium || false);
      }
      if (guidesRes.status === "fulfilled") {
        setGuides(guidesRes.value?.items || []);
      }
      if (tgRes.status === "fulfilled") {
        setTelegramConnected(Boolean(tgRes.value?.connected));
      }

      setLoading(false);
    }
    load();

    // Load user preferences once for the one-way banner — they don't change
    // often, so keep them out of any polling loop.
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

    return () => {
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

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[80px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            <Wordmark />
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
            <div className="text-sm text-[#082B78]">
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
              <p className="text-sm text-[#082B78]/70">
                Accès illimité à tous les deals ≥50%, sans quota hebdomadaire. Alertes Telegram instantanées.
                <span className="font-semibold"> 29€/an</span> <span className="line-through text-[#082B78]/40">59€</span> — soit 2,42€/mois.
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


        {/* Telegram status banner — the chat is where the product lives. */}
        {!loading && (
          telegramConnected ? (
            <div className="mb-6 bg-[#0088cc]/5 border border-[#0088cc]/20 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <svg className="w-10 h-10 text-[#0088cc] shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
                <div>
                  <div className="font-semibold text-[#082B78] mb-0.5">Tes alertes sont actives sur Telegram</div>
                  <p className="text-sm text-[#082B78]/70">
                    Les nouveaux deals arrivent dans le chat. Tape <code className="text-[#0088cc] font-mono">/destinations</code> pour bloquer une ville,{" "}
                    <code className="text-[#0088cc] font-mono">/pause</code> pour mettre tes alertes en pause.
                  </p>
                </div>
              </div>
              <a
                href={TELEGRAM_BOT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-[#0088cc] hover:bg-[#006daa] text-white font-semibold px-5 py-2.5 rounded-xl text-sm shrink-0 transition-colors whitespace-nowrap"
              >
                Ouvrir le chat →
              </a>
            </div>
          ) : (
            <div className="mb-6 bg-amber-50 border border-amber-200 rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="font-semibold text-[#082B78] mb-0.5">⚠️ Connecte ton Telegram pour recevoir les alertes</div>
                <p className="text-sm text-[#082B78]/70">
                  Sans Telegram, tu ne reçois aucune notification de deal. La connexion prend 30 secondes.
                </p>
              </div>
              <Link
                href="/profile"
                className="bg-amber-500 hover:bg-amber-600 text-white font-semibold px-5 py-2.5 rounded-xl text-sm shrink-0 transition-colors whitespace-nowrap"
              >
                Connecter Telegram →
              </Link>
            </div>
          )
        )}

        {/* Planificateur — promoted as a hero card now that the deals
            section is gone. Free users see the same card; access gating
            is handled inside the planner. */}
        <div className="mb-8 bg-gradient-to-br from-[#FFFEF9] to-[#FFF1EC] border border-[#FF6B47]/30 rounded-2xl p-6 md:p-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
            <div className="max-w-xl">
              <div className="text-xs font-bold text-[#FF6B47] mb-2 tracking-wide">🗺️ PLANIFICATEUR DE VOYAGE</div>
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl md:text-3xl text-[#082B78] mb-2">
                Construis ton prochain voyage avec l&apos;IA
              </h2>
              <p className="text-sm md:text-base text-[#082B78]/70">
                Itinéraire jour par jour, restaurants, activités, budget — l&apos;assistant prépare tout en quelques secondes.
                {isPremium === false && (
                  <span className="block mt-1 text-xs text-[#FF6B47] font-semibold">Exclusif aux abonnés Premium.</span>
                )}
              </p>
            </div>
            <Link
              href="/planificateur"
              className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-bold px-6 py-3 rounded-xl text-sm shrink-0 transition-all shadow-[0_8px_24px_rgba(255,107,71,0.25)]"
            >
              Ouvrir le planificateur →
            </Link>
          </div>
        </div>

        {/* Destination guides — every published guide, no collapsible. The
            home page is now a "browse + plan + chat" hub, not a deal feed. */}
        <div className="mb-8">
          <div className="flex items-baseline justify-between mb-5">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#082B78]">
              Vos guides destination
            </h2>
            {guides.length > 0 && (
              <span className="text-sm text-gray-400">{guides.length} disponible{guides.length > 1 ? "s" : ""}</span>
            )}
          </div>

          {loading && (
            <div className="text-center py-12 text-gray-400">Chargement…</div>
          )}

          {!loading && guides.length === 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
              <div className="text-4xl mb-3">📚</div>
              <h3 className="font-semibold text-lg mb-2">Les guides arrivent</h3>
              <p className="text-sm text-gray-400 max-w-md mx-auto">
                On rédige un guide à chaque nouvelle destination détectée. Reviens dans quelques jours pour les premiers.
              </p>
            </div>
          )}

          {!loading && guides.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 md:gap-4">
              {guides.map((g) => (
                <Link
                  key={g.iata}
                  href={`/destination/${g.iata.toLowerCase()}`}
                  className="group block overflow-hidden rounded-2xl border border-gray-100 bg-white hover:border-[#FF6B47] hover:shadow-[0_8px_24px_rgba(10,31,61,0.08)] transition-all"
                >
                  {g.cover_photo && (
                    <div className="relative aspect-[4/3] overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={g.cover_photo}
                        alt={g.destination}
                        className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    </div>
                  )}
                  <div className="p-3">
                    <div className="text-[11px] text-gray-400 uppercase tracking-wider mb-0.5">{g.destination}</div>
                    <div className="font-semibold text-sm text-[#082B78] line-clamp-2 leading-snug">{g.title}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
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
