"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearSessionCookie, getTelegramStatus } from "@/lib/api";
import { initSession } from "@/lib/session";
import { slugFor } from "@/lib/destinations";
import { Wordmark } from "../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TELEGRAM_BOT_URL = "https://t.me/Globegenius_bot";

type Guide = {
  iata: string;
  destination: string;
  title: string;
  cover_photo: string;
};

type PlanInfo = {
  plan: "og" | "premium" | "freemium";
  label: string;
  is_premium: boolean;
  is_og: boolean;
  badge_number: number | null;
  freemium: {
    primary_airports: number;
    regular_alerts_per_week: number;
    exceptional_alerts_per_month: number;
    monthly_unlocks: number;
    unlock_available: boolean;
    unlock_available_at: string;
  };
};

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [guides, setGuides] = useState<Guide[]>([]);
  const [telegramConnected, setTelegramConnected] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const token = localStorage.getItem("gg_token");
    if (!userId || !token) {
      router.push("/login");
      return;
    }

    const cleanup = initSession();
    const headers = { Authorization: `Bearer ${token}` };

    Promise.allSettled([
      fetch(`${API_URL}/api/account/plan`, { headers }).then((response) => response.json()),
      fetch(`${API_URL}/api/destinations?limit=50`).then((response) => response.json()),
      getTelegramStatus(userId),
    ]).then(([planResult, guidesResult, telegramResult]) => {
      if (planResult.status === "fulfilled" && planResult.value?.plan) {
        setPlan(planResult.value);
      }
      if (guidesResult.status === "fulfilled") {
        setGuides(guidesResult.value?.items || []);
      }
      if (telegramResult.status === "fulfilled") {
        setTelegramConnected(Boolean(telegramResult.value?.connected));
      } else {
        setTelegramConnected(false);
      }
      setLoading(false);
    });

    return () => {
      if (cleanup) cleanup();
    };
  }, [router]);

  // Deep-link des emails freemium (?upgrade=1) : ouvre le checkout Stripe
  // directement — un clic de moins entre l'email et le paiement. Stripe
  // est live côté backend même si la nouvelle UI n'affiche pas encore de
  // bouton d'achat ; le lien email reste donc fonctionnel. Session
  // expirée → redirection /login gérée par handleCheckout.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("upgrade") === "1") {
      handleCheckout();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCheckout() {
    try {
      const token = localStorage.getItem("gg_token");
      if (!token) {
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
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="sticky top-0 z-50 border-b border-[#D9E2E3] bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-4 md:px-5">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none"><Wordmark /></Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-slate-400 md:block">{plan?.label || ""}</span>
            <Link href="/deals" className="text-sm text-slate-500 transition-colors hover:text-[#0E7490]">Mes deals</Link>
            <Link href="/profile" className="text-sm text-slate-500 transition-colors hover:text-[#0E7490]">Profil</Link>
            <button onClick={handleLogout} className="text-sm text-slate-500 transition-colors hover:text-red-500">Déconnexion</button>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-4 py-8 md:px-5 md:py-10">
        <div className="mb-8">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Votre espace GlobeGenius</p>
          <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl">Vos alertes vivent sur Telegram.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">
            Configurez vos préférences ici, consultez les opportunités détectées et recevez les alertes actionnables directement dans le chat.
          </p>
        </div>

        {!loading && (
          telegramConnected ? (
            <section className="mb-6 rounded-3xl border border-[#0E7490]/20 bg-[#E9F5F7] p-6 md:flex md:items-center md:justify-between md:gap-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#229ED9] font-bold text-white">G</div>
                <div>
                  <h2 className="font-bold text-[#0B2A3F]">Vos alertes Telegram sont actives</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Tapez <code className="font-mono text-[#0E7490]">/destinations</code> pour masquer une ville ou <code className="font-mono text-[#0E7490]">/pause</code> pour suspendre les alertes.
                  </p>
                </div>
              </div>
              <a href={TELEGRAM_BOT_URL} target="_blank" rel="noopener noreferrer" className="mt-5 inline-flex w-full justify-center rounded-xl bg-[#229ED9] px-5 py-3 text-sm font-bold text-white hover:bg-[#1B86B8] md:mt-0 md:w-auto">
                Ouvrir le chat
              </a>
            </section>
          ) : (
            <section className="mb-6 rounded-3xl border border-[#FF7A59]/30 bg-[#FFF0EA] p-6 md:flex md:items-center md:justify-between md:gap-6">
              <div>
                <h2 className="font-bold text-[#0B2A3F]">Connectez Telegram pour recevoir vos alertes Freemium</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Votre compte est déjà actif. La connexion Telegram permet de recevoir 2 alertes complètes par semaine et 1 pépite exceptionnelle par mois.
                </p>
              </div>
              <Link href="/onboarding" className="mt-5 inline-flex w-full justify-center rounded-xl bg-[#FF7A59] px-5 py-3 text-sm font-bold text-white hover:bg-[#E96543] md:mt-0 md:w-auto">
                Activer Telegram
              </Link>
            </section>
          )
        )}

        {plan?.plan === "og" && (
          <section className="mb-8 rounded-[32px] bg-[#0B2A3F] p-7 text-white md:flex md:items-center md:justify-between md:gap-8 md:p-9">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#F4B942]">Badge OG{plan.badge_number ? ` #${plan.badge_number}` : ""}</div>
              <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Votre Premium est maintenu.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/65">Votre contribution fondatrice vous donne accès aux alertes Premium sans limite de durée.</p>
            </div>
            <Link href="/deals" className="mt-6 inline-flex rounded-xl bg-[#F4B942] px-6 py-3 text-sm font-bold text-[#0B2A3F] md:mt-0">Voir les deals</Link>
          </section>
        )}

        {plan?.plan === "premium" && (
          <section className="mb-8 rounded-[32px] bg-[#0B2A3F] p-7 text-white md:flex md:items-center md:justify-between md:gap-8 md:p-9">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#52C9BE]">Premium actif</div>
              <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Toutes les alertes sont ouvertes.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/65">Plusieurs aéroports, allers simples, combos malins et alertes sans quota.</p>
            </div>
            <Link href="/deals" className="mt-6 inline-flex rounded-xl bg-[#52C9BE] px-6 py-3 text-sm font-bold text-[#0B2A3F] md:mt-0">Voir les deals</Link>
          </section>
        )}

        {plan?.plan === "freemium" && (
          <>
            <section className="mb-6 rounded-[32px] border border-[#D9E2E3] bg-white p-7 md:p-9">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Votre formule Freemium</div>
                  <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Des alertes gratuites, sélectionnées avec exigence.</h2>
                </div>
                <Link href="/deals" className="rounded-xl bg-[#0E7490] px-5 py-3 text-sm font-bold text-white hover:bg-[#0A6078]">Utiliser mon joker</Link>
              </div>
              <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl bg-[#E9F5F7] p-5"><div className="text-2xl font-bold">1</div><div className="mt-1 text-sm text-slate-600">aéroport de départ</div></div>
                <div className="rounded-2xl bg-[#E9F5F7] p-5"><div className="text-2xl font-bold">2</div><div className="mt-1 text-sm text-slate-600">alertes complètes par semaine</div></div>
                <div className="rounded-2xl bg-[#FFF0EA] p-5"><div className="text-2xl font-bold">1</div><div className="mt-1 text-sm text-slate-600">pépite complète par mois</div></div>
                <div className="rounded-2xl bg-[#FFF0EA] p-5"><div className="text-2xl font-bold">1</div><div className="mt-1 text-sm text-slate-600">joker Premium par mois</div></div>
              </div>
            </section>

            <section className="mb-8 grid gap-6 rounded-[32px] bg-[#0B2A3F] p-7 text-white md:grid-cols-[1fr_auto] md:items-center md:p-9">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#52C9BE]">Premium · ouverture prochaine</div>
                <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">49 € par an, soit 4,08 € par mois.</h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-white/65">
                  Une seule réservation peut amortir l’abonnement plusieurs fois : 100 € économisés représentent plus de deux années, et 150 € plus de trois. L’économie réelle dépend du billet réservé.
                </p>
                <p className="mt-3 text-xs text-white/45">Stripe sera configuré ultérieurement. Aucun paiement et aucune carte bancaire ne sont demandés aujourd’hui.</p>
              </div>
              <div className="rounded-2xl border border-white/15 bg-white/10 px-6 py-5 text-center">
                <div className="font-[family-name:var(--font-dm-serif)] text-4xl">49 €</div>
                <div className="text-xs text-white/55">par an</div>
                <button disabled className="mt-4 cursor-not-allowed rounded-xl bg-white/15 px-5 py-2.5 text-sm font-semibold text-white/70">Paiement bientôt disponible</button>
              </div>
            </section>
          </>
        )}

        <section>
          <div className="mb-5 flex items-baseline justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#FF7A59]">Inspiration</p>
              <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-2xl">Guides destination</h2>
            </div>
            {guides.length > 0 && <span className="text-sm text-slate-400">{guides.length} disponible{guides.length > 1 ? "s" : ""}</span>}
          </div>

          {loading && <div className="rounded-2xl bg-white p-10 text-center text-slate-400">Chargement…</div>}
          {!loading && guides.length === 0 && (
            <div className="rounded-2xl border border-[#D9E2E3] bg-white p-10 text-center">
              <div className="text-4xl">📚</div>
              <h3 className="mt-3 font-bold">Les guides arrivent</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">Un guide est publié progressivement pour les destinations surveillées.</p>
            </div>
          )}
          {!loading && guides.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 md:gap-4">
              {guides.map((guide) => (
                <Link key={guide.iata} href={`/destination/${slugFor(guide.iata)}`} className="group block overflow-hidden rounded-2xl border border-[#D9E2E3] bg-white transition-all hover:border-[#0E7490] hover:shadow-[0_8px_24px_rgba(11,42,63,.08)]">
                  <div className="relative aspect-[4/3] overflow-hidden bg-[#E9F5F7]">
                    {guide.cover_photo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={guide.cover_photo} alt={guide.destination} className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center font-[family-name:var(--font-dm-serif)] text-3xl text-[#0E7490]/40">{guide.iata}</div>
                    )}
                  </div>
                  <div className="p-3">
                    <div className="text-[11px] uppercase tracking-wider text-slate-400">{guide.destination}</div>
                    <div className="mt-1 line-clamp-2 text-sm font-semibold leading-snug text-[#0B2A3F]">{guide.title}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="mt-8 border-t border-[#D9E2E3] py-6">
        <div className="mx-auto max-w-6xl px-5 text-center text-xs text-slate-300">Globe Genius © 2026 — Alertes vols vérifiées</div>
      </footer>
    </div>
  );
}
