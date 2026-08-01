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

function MetricCard({
  value,
  label,
  tone = "ocean",
}: {
  value: number | string;
  label: string;
  tone?: "ocean" | "coral";
}) {
  const toneClasses =
    tone === "coral"
      ? "bg-[#FFF0EA] text-[#FF7A59]"
      : "bg-[#E9F5F7] text-[#0E7490]";

  return (
    <div className="rounded-2xl border border-[#D9E2E3] bg-white p-5 shadow-[0_12px_34px_rgba(11,42,63,.05)]">
      <div className={`inline-flex min-w-12 items-center justify-center rounded-xl px-3 py-2 text-2xl font-bold ${toneClasses}`}>
        {value}
      </div>
      <div className="mt-4 text-sm leading-6 text-slate-600">{label}</div>
    </div>
  );
}

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

  const planLabel = loading ? "Chargement…" : plan?.label || "Compte GlobeGenius";
  const radarActive = telegramConnected === true;

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="sticky top-0 z-50 border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-8">
          <Link href="/" aria-label="Accueil GlobeGenius">
            <Wordmark />
          </Link>
          <div className="flex items-center gap-3 sm:gap-5">
            <span className="hidden rounded-full bg-[#E9F5F7] px-3 py-1.5 text-xs font-bold text-[#0E7490] md:inline-flex">
              {planLabel}
            </span>
            <Link href="/deals" className="text-sm font-medium text-slate-600 transition-colors hover:text-[#0E7490]">
              Mes deals
            </Link>
            <Link href="/profile" className="text-sm font-medium text-slate-600 transition-colors hover:text-[#0E7490]">
              Profil
            </Link>
            <button onClick={handleLogout} className="hidden text-sm font-medium text-slate-500 transition-colors hover:text-[#C93F3F] sm:inline">
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <header
        className="relative overflow-hidden bg-[#0B2A3F] text-white"
        style={{
          backgroundImage:
            "radial-gradient(circle at 80% 18%, rgba(42,183,169,.30), transparent 30%), radial-gradient(circle at 18% 0%, rgba(14,116,144,.48), transparent 40%), linear-gradient(135deg, #061824 0%, #0B2A3F 50%, #0A6078 100%)",
        }}
      >
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full border border-white/10" />
        <div className="absolute -bottom-36 right-[18%] h-80 w-80 rounded-full border border-white/10" />

        <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-8 sm:py-16 lg:grid-cols-[1.12fr_.88fr] lg:items-center">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold text-white/85 backdrop-blur">
              <span className={`h-2 w-2 rounded-full ${radarActive ? "bg-[#52C9BE]" : "bg-[#FF9478]"}`} />
              {radarActive ? "Radar actif · alertes Telegram connectées" : "Radar à finaliser · Telegram non connecté"}
            </div>
            <p className="mt-7 text-xs font-bold uppercase tracking-[0.2em] text-[#52C9BE]">Votre espace GlobeGenius</p>
            <h1 className="mt-3 max-w-3xl font-[family-name:var(--font-dm-serif)] text-4xl leading-[1.05] text-white sm:text-5xl lg:text-6xl">
              Votre radar surveille.
              <span className="mt-1 block text-[#FF9478]">Vous partez quand le prix devient intéressant.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-white/70">
              Retrouvez vos opportunités qualifiées, ajustez vos aéroports et pilotez les alertes reçues directement sur Telegram.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/deals"
                className="rounded-xl bg-white px-6 py-3.5 text-center text-sm font-bold text-[#0B2A3F] shadow-[0_12px_30px_rgba(0,0,0,.18)] transition-colors hover:bg-[#E9F5F7]"
              >
                Voir mes deals
              </Link>
              <Link
                href="/profile"
                className="rounded-xl border border-white/20 bg-white/8 px-6 py-3.5 text-center text-sm font-semibold text-white transition-colors hover:bg-white/12"
              >
                Modifier mes alertes
              </Link>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/15 bg-white/10 p-6 shadow-[0_28px_80px_rgba(0,0,0,.22)] backdrop-blur-md sm:p-7">
            <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/50">Votre formule</p>
                <p className="mt-2 text-xl font-bold text-white">{planLabel}</p>
              </div>
              <span className={`rounded-full px-3 py-1.5 text-xs font-bold ${radarActive ? "bg-[#52C9BE]/20 text-[#8FE2DA]" : "bg-[#FF7A59]/18 text-[#FFB09C]"}`}>
                {radarActive ? "Actif" : "À connecter"}
              </span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-2xl bg-white/8 p-4">
                <div className="text-white/45">Canal</div>
                <div className="mt-2 font-bold text-white">Telegram</div>
              </div>
              <div className="rounded-2xl bg-white/8 p-4">
                <div className="text-white/45">Prix</div>
                <div className="mt-2 font-bold text-white">Revérifiés</div>
              </div>
            </div>
            <p className="mt-5 text-sm leading-6 text-white/60">
              GlobeGenius préfère rester silencieux plutôt que vous envoyer une promotion ordinaire présentée comme un bon plan.
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-8 md:py-12">
        {!loading && (
          radarActive ? (
            <section className="mb-7 rounded-[28px] border border-[#D9E2E3] bg-white p-6 shadow-[0_18px_55px_rgba(11,42,63,.06)] md:flex md:items-center md:justify-between md:gap-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#0E7490] font-bold text-white shadow-[0_10px_24px_rgba(14,116,144,.22)]">G</div>
                <div>
                  <div className="inline-flex rounded-full bg-[#EAF8F5] px-3 py-1 text-xs font-bold text-[#168F73]">Connexion confirmée</div>
                  <h2 className="mt-3 text-lg font-bold text-[#0B2A3F]">Vos alertes Telegram sont actives</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Tapez <code className="font-mono text-[#0E7490]">/destinations</code> pour masquer une ville ou <code className="font-mono text-[#0E7490]">/pause</code> pour suspendre les alertes.
                  </p>
                </div>
              </div>
              <a
                href={TELEGRAM_BOT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex w-full justify-center rounded-xl bg-[#0E7490] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078] md:mt-0 md:w-auto"
              >
                Ouvrir le chat
              </a>
            </section>
          ) : (
            <section className="mb-7 rounded-[28px] border border-[#D9E2E3] bg-white p-6 shadow-[0_18px_55px_rgba(11,42,63,.06)] md:flex md:items-center md:justify-between md:gap-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#FFF0EA] text-xl font-bold text-[#FF7A59]">!</div>
                <div>
                  <div className="inline-flex rounded-full bg-[#FFF0EA] px-3 py-1 text-xs font-bold text-[#FF7A59]">Dernière étape</div>
                  <h2 className="mt-3 text-lg font-bold text-[#0B2A3F]">Connectez Telegram pour recevoir vos alertes</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    Votre compte est actif. La connexion Telegram ouvre la réception des alertes complètes et des pépites mensuelles.
                  </p>
                </div>
              </div>
              <Link
                href="/onboarding"
                className="mt-5 inline-flex w-full justify-center rounded-xl bg-[#0E7490] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078] md:mt-0 md:w-auto"
              >
                Connecter Telegram
              </Link>
            </section>
          )
        )}

        {plan?.plan === "og" && (
          <section className="mb-8 rounded-[32px] border border-[#E8DDCF] bg-[#FFFCF7] p-7 shadow-[0_18px_55px_rgba(11,42,63,.05)] md:flex md:items-center md:justify-between md:gap-8 md:p-9">
            <div>
              <div className="inline-flex rounded-full bg-[#FFF5D8] px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-[#8A6513]">
                Badge OG{plan.badge_number ? ` #${plan.badge_number}` : ""}
              </div>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">Votre Premium fondateur est maintenu.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">Votre contribution fondatrice vous donne accès aux alertes Premium sans limite de durée.</p>
            </div>
            <Link href="/deals" className="mt-6 inline-flex rounded-xl bg-[#0E7490] px-6 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078] md:mt-0">
              Voir les deals
            </Link>
          </section>
        )}

        {plan?.plan === "premium" && (
          <section className="mb-8 rounded-[32px] border border-[#D9E2E3] bg-white p-7 shadow-[0_18px_55px_rgba(11,42,63,.05)] md:flex md:items-center md:justify-between md:gap-8 md:p-9">
            <div>
              <div className="inline-flex rounded-full bg-[#EAF8F5] px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-[#168F73]">Premium actif</div>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">Toutes les alertes sont ouvertes.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">Plusieurs aéroports, allers simples, combos malins et alertes sans quota.</p>
            </div>
            <Link href="/deals" className="mt-6 inline-flex rounded-xl bg-[#0E7490] px-6 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078] md:mt-0">
              Voir les deals
            </Link>
          </section>
        )}

        {plan?.plan === "freemium" && (
          <>
            <section className="mb-7 rounded-[32px] border border-[#D9E2E3] bg-[#FFFCF7] p-7 shadow-[0_18px_55px_rgba(11,42,63,.05)] md:p-9">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Votre formule Freemium</div>
                  <h2 className="mt-3 max-w-3xl font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">Des alertes gratuites, sélectionnées avec exigence.</h2>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">La même qualité de détection que Premium, avec un volume encadré et un joker mensuel.</p>
                </div>
                <Link href="/deals" className="rounded-xl bg-[#0E7490] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#0A6078]">
                  Utiliser mon joker
                </Link>
              </div>
              <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard value={plan.freemium?.primary_airports ?? 1} label="aéroport principal surveillé" />
                <MetricCard value={plan.freemium?.regular_alerts_per_week ?? 2} label="alertes complètes par semaine" />
                <MetricCard value={plan.freemium?.exceptional_alerts_per_month ?? 1} label="pépite complète par mois" tone="coral" />
                <MetricCard value={plan.freemium?.monthly_unlocks ?? 1} label="joker Premium par mois" tone="coral" />
              </div>
            </section>

            <section
              className="mb-9 grid gap-7 overflow-hidden rounded-[32px] bg-[#0B2A3F] p-7 text-white shadow-[0_24px_70px_rgba(11,42,63,.20)] md:grid-cols-[1fr_auto] md:items-center md:p-9"
              style={{
                backgroundImage:
                  "radial-gradient(circle at 88% 15%, rgba(42,183,169,.26), transparent 32%), linear-gradient(135deg, #0B2A3F 0%, #0A6078 100%)",
              }}
            >
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.18em] text-[#8FE2DA]">Premium · ouverture prochaine</div>
                <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">39 € par an, soit 3,25 € par mois.</h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-white/70">
                  Une seule réservation peut amortir l’abonnement plusieurs fois. L’économie réelle dépend du billet réservé et de sa disponibilité.
                </p>
                <p className="mt-3 text-xs leading-5 text-white/45">Le paiement sera ouvert officiellement lors du lancement commercial. Aucune carte bancaire n’est demandée aujourd’hui.</p>
              </div>
              <div className="rounded-2xl border border-white/15 bg-white/10 px-7 py-6 text-center backdrop-blur">
                <div className="font-[family-name:var(--font-dm-serif)] text-4xl">39 €</div>
                <div className="mt-1 text-xs text-white/55">par an</div>
                <button disabled className="mt-4 cursor-not-allowed rounded-xl bg-white/15 px-5 py-2.5 text-sm font-semibold text-white/70">
                  Paiement bientôt disponible
                </button>
              </div>
            </section>
          </>
        )}

        <section>
          <div className="mb-6 flex items-end justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#FF7A59]">Inspiration</p>
              <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">Guides destination</h2>
              <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">Préparez votre voyage lorsque votre radar détecte enfin le bon prix.</p>
            </div>
            {guides.length > 0 && <span className="hidden text-sm text-slate-400 sm:block">{guides.length} disponible{guides.length > 1 ? "s" : ""}</span>}
          </div>

          {loading && <div className="rounded-2xl border border-[#D9E2E3] bg-white p-10 text-center text-slate-400">Chargement…</div>}
          {!loading && guides.length === 0 && (
            <div className="rounded-[28px] border border-[#D9E2E3] bg-white p-10 text-center shadow-[0_14px_40px_rgba(11,42,63,.04)]">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E9F5F7] text-2xl">📚</div>
              <h3 className="mt-4 font-bold text-[#0B2A3F]">Les guides arrivent</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">Un guide est publié progressivement pour les destinations surveillées.</p>
            </div>
          )}
          {!loading && guides.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:gap-4 lg:grid-cols-4 xl:grid-cols-5">
              {guides.map((guide) => (
                <Link
                  key={guide.iata}
                  href={`/destination/${slugFor(guide.iata)}`}
                  className="group block overflow-hidden rounded-2xl border border-[#D9E2E3] bg-white shadow-[0_12px_32px_rgba(11,42,63,.04)] transition-all hover:-translate-y-0.5 hover:border-[#0E7490] hover:shadow-[0_18px_44px_rgba(11,42,63,.10)]"
                >
                  <div className="relative aspect-[4/3] overflow-hidden bg-[#E9F5F7]">
                    {guide.cover_photo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={guide.cover_photo} alt={guide.destination} className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center font-[family-name:var(--font-dm-serif)] text-3xl text-[#0E7490]/40">{guide.iata}</div>
                    )}
                  </div>
                  <div className="p-4">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-[#0E7490]">{guide.destination}</div>
                    <div className="mt-1 line-clamp-2 text-sm font-semibold leading-snug text-[#0B2A3F]">{guide.title}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="mt-10 border-t border-[#D9E2E3] bg-[#FFFCF7] py-7">
        <div className="mx-auto max-w-7xl px-5 text-center text-xs text-slate-400">GlobeGenius © 2026 — Alertes vols vérifiées</div>
      </footer>
    </div>
  );
}
