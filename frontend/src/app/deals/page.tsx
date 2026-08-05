"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Wordmark } from "../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const AIRPORT_LABELS: Record<string, string> = {
  CDG: "Paris-CDG",
  ORY: "Paris-Orly",
  BVA: "Paris-Beauvais",
  LYS: "Lyon",
  MRS: "Marseille",
  NCE: "Nice",
  BOD: "Bordeaux",
  NTE: "Nantes",
  TLS: "Toulouse",
  BSL: "Bâle-Mulhouse",
};

const DESTINATION_LABELS: Record<string, string> = {
  BCN: "Barcelone", LIS: "Lisbonne", FCO: "Rome", ATH: "Athènes",
  NAP: "Naples", OPO: "Porto", AMS: "Amsterdam", BER: "Berlin",
  PRG: "Prague", BUD: "Budapest", DUB: "Dublin", IST: "Istanbul",
  MAD: "Madrid", MXP: "Milan", VCE: "Venise", VIE: "Vienne",
  AGP: "Malaga", PMI: "Palma", HER: "Héraklion", RAK: "Marrakech",
  TUN: "Tunis", ALG: "Alger", DXB: "Dubaï", JFK: "New York",
  YUL: "Montréal", MIA: "Miami", LAX: "Los Angeles", BKK: "Bangkok",
  NRT: "Tokyo", HND: "Tokyo", ICN: "Séoul", SIN: "Singapour",
  MRU: "Maurice", RUN: "La Réunion", PPT: "Papeete", SYD: "Sydney",
};

type PlanInfo = {
  plan: "og" | "premium_trial" | "premium" | "freemium";
  label: string;
  is_premium: boolean;
  trial_expires_at: string | null;
  freemium: {
    unlock_available: boolean;
    unlock_available_at: string;
    regular_alerts_per_week: number;
    exceptional_alerts_per_month: number;
    monthly_unlocks: number;
  };
};

type Teaser = {
  id: string;
  origin: string;
  destination: string;
  discount_pct: number;
  estimated_savings_eur: number | null;
  locked: boolean;
};

type FullDeal = {
  id: string;
  origin: string;
  destination: string;
  departure_date: string;
  return_date: string | null;
  airline: string | null;
  stops: number | null;
  price: number;
  baseline_price: number | null;
  discount_pct: number;
  source_url: string | null;
};

function labelFor(code: string, dictionary: Record<string, string>) {
  return dictionary[code] || code;
}

function formatDate(value: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function formatPrice(value: number | null | undefined) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

export default function DealsPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [teasers, setTeasers] = useState<Teaser[]>([]);
  const [loading, setLoading] = useState(true);
  const [unlockingId, setUnlockingId] = useState<string | null>(null);
  const [unlocked, setUnlocked] = useState<FullDeal | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("gg_token");
    if (!token) {
      router.push("/login");
      return;
    }
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API_URL}/api/account/plan`, { headers }).then((response) => {
        if (!response.ok) throw new Error("Impossible de charger votre formule.");
        return response.json();
      }),
      fetch(`${API_URL}/api/freemium/teasers?limit=12`, { headers }).then((response) => {
        if (!response.ok) throw new Error("Impossible de charger les opportunités.");
        return response.json();
      }),
    ])
      .then(([planBody, teaserBody]) => {
        setPlan(planBody);
        setTeasers(teaserBody.items || []);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Erreur de chargement."))
      .finally(() => setLoading(false));
  }, [router]);

  const unlockDate = useMemo(() => {
    if (!plan || plan.freemium.unlock_available) return null;
    return formatDate(plan.freemium.unlock_available_at);
  }, [plan]);

  async function unlockDeal(dealId: string) {
    const token = localStorage.getItem("gg_token");
    if (!token) return router.push("/login");
    setUnlockingId(dealId);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/freemium/unlock/${dealId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail;
        throw new Error(typeof detail === "string" ? detail : detail?.message || "Ce deal ne peut pas être déverrouillé.");
      }
      setUnlocked(body.deal);
      if (body.consumed_joker) {
        setPlan((current) => current ? {
          ...current,
          freemium: { ...current.freemium, unlock_available: false },
        } : current);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur lors du déverrouillage.");
    } finally {
      setUnlockingId(null);
    }
  }

  const isUnlimited = Boolean(plan?.is_premium);

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="border-b border-[#D9E2E3] bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-4 md:px-5">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px]"><Wordmark /></Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/home" className="text-slate-500 hover:text-[#0E7490]">Accueil</Link>
            <Link href="/profile" className="text-slate-500 hover:text-[#0E7490]">Profil</Link>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-4 py-10 md:px-5">
        <div className="grid gap-8 lg:grid-cols-[1fr_320px] lg:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Opportunités détectées</p>
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl md:text-5xl">Les deals qui méritent votre attention.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500">
              Nous montrons la route et l’économie potentielle. Le prix exact, les dates et le lien sont révélés aux membres Premium ou avec le joker mensuel Freemium.
            </p>
          </div>

          <aside className="rounded-3xl border border-[#D9E2E3] bg-white p-6">
            <div className="text-xs font-bold uppercase tracking-[0.14em] text-[#FF7A59]">{plan?.label || "Votre formule"}</div>
            {isUnlimited ? (
              <p className="mt-3 text-sm leading-6 text-slate-600">Tous les deals peuvent être ouverts sans consommer de joker.</p>
            ) : (
              <>
                <p className="mt-3 text-sm leading-6 text-slate-600">Vous disposez d’un joker pour révéler un deal Premium chaque mois.</p>
                <div className={`mt-4 rounded-2xl p-4 text-sm font-semibold ${plan?.freemium.unlock_available ? "bg-[#E9F5F7] text-[#0E7490]" : "bg-slate-100 text-slate-500"}`}>
                  {plan?.freemium.unlock_available ? "Joker disponible" : `Prochain joker : ${unlockDate || "dans 30 jours"}`}
                </div>
              </>
            )}
          </aside>
        </div>

        {error && <div className="mt-7 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div>}

        {unlocked && (
          <section className="mt-8 rounded-[32px] border border-[#2AB7A9]/30 bg-white p-6 shadow-[0_20px_60px_rgba(11,42,63,.08)] md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#168F73]">Deal déverrouillé</p>
                <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-3xl">
                  {labelFor(unlocked.origin, AIRPORT_LABELS)} → {labelFor(unlocked.destination, DESTINATION_LABELS)}
                </h2>
              </div>
              <div className="rounded-full bg-[#FFF0EA] px-4 py-2 font-bold text-[#E96543]">−{Math.round(unlocked.discount_pct)} %</div>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div><div className="text-xs text-slate-400">Prix détecté</div><div className="mt-1 text-xl font-bold">{formatPrice(unlocked.price)}</div></div>
              <div><div className="text-xs text-slate-400">Prix habituel</div><div className="mt-1 text-xl font-bold">{formatPrice(unlocked.baseline_price)}</div></div>
              <div><div className="text-xs text-slate-400">Départ</div><div className="mt-1 font-semibold">{formatDate(unlocked.departure_date)}</div></div>
              <div><div className="text-xs text-slate-400">Retour</div><div className="mt-1 font-semibold">{formatDate(unlocked.return_date)}</div></div>
            </div>
            {unlocked.source_url && (
              <a href={unlocked.source_url} target="_blank" rel="noopener noreferrer" className="mt-7 inline-flex rounded-xl bg-[#0E7490] px-6 py-3 text-sm font-bold text-white hover:bg-[#0A6078]">
                Vérifier et réserver
              </a>
            )}
            <p className="mt-4 text-xs leading-5 text-slate-400">Les tarifs aériens évoluent rapidement. GlobeGenius ne vend pas le billet et ne garantit pas que le prix restera disponible.</p>
          </section>
        )}

        <section className="mt-10">
          {loading ? (
            <div className="rounded-3xl bg-white p-12 text-center text-slate-400">Recherche des meilleurs deals…</div>
          ) : teasers.length === 0 ? (
            <div className="rounded-3xl border border-[#D9E2E3] bg-white p-12 text-center">
              <div className="text-4xl">🧭</div>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-2xl">Aucune pépite active pour le moment</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">Le moteur continue de surveiller les prix. Les nouvelles opportunités apparaîtront ici après vérification.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teasers.map((deal) => {
                const canOpen = isUnlimited || Boolean(plan?.freemium.unlock_available);
                return (
                  <article key={deal.id} className="rounded-3xl border border-[#D9E2E3] bg-white p-6 transition-transform hover:-translate-y-1 hover:shadow-[0_18px_40px_rgba(11,42,63,.08)]">
                    <div className="flex items-center justify-between gap-3">
                      <span className="rounded-full bg-[#E9F5F7] px-3 py-1 text-xs font-bold text-[#0E7490]">Deal vérifié</span>
                      <span className="text-lg font-bold text-[#E96543]">−{deal.discount_pct} %</span>
                    </div>
                    <h2 className="mt-5 font-[family-name:var(--font-dm-serif)] text-2xl">
                      {labelFor(deal.origin, AIRPORT_LABELS)} → {labelFor(deal.destination, DESTINATION_LABELS)}
                    </h2>
                    <p className="mt-3 text-sm leading-6 text-slate-500">
                      {deal.estimated_savings_eur ? `Économie potentielle d’environ ${formatPrice(deal.estimated_savings_eur)} par billet.` : "Le prix est nettement inférieur à son niveau habituel."}
                    </p>
                    <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-slate-400 blur-[2px] select-none">Prix exact · dates · compagnie · lien</div>
                    <button
                      type="button"
                      onClick={() => unlockDeal(deal.id)}
                      disabled={!canOpen || unlockingId === deal.id}
                      className="mt-5 w-full rounded-xl bg-[#0E7490] px-4 py-3 text-sm font-bold text-white hover:bg-[#0A6078] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
                    >
                      {unlockingId === deal.id ? "Déverrouillage…" : isUnlimited ? "Voir le deal complet" : canOpen ? "Utiliser mon joker" : "Joker déjà utilisé"}
                    </button>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {!isUnlimited && (
          <section className="mt-10 rounded-[32px] bg-[#0B2A3F] p-7 text-white md:flex md:items-center md:justify-between md:gap-8 md:p-9">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#52C9BE]">Premium · 39 € par an</p>
              <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Une seule réservation peut amortir l’abonnement plusieurs fois.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/65">Toutes les alertes, plusieurs aéroports, les prix, les dates et les liens immédiatement. Le paiement public ouvrira lors du lancement commercial.</p>
            </div>
            <button disabled className="mt-6 rounded-xl bg-white/15 px-6 py-3 text-sm font-bold text-white/70 md:mt-0">Ouverture prochaine</button>
          </section>
        )}
      </main>
    </div>
  );
}
