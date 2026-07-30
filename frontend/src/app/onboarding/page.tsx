"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { generateTelegramLink, getPreferences, updatePreferences } from "@/lib/api";
import { Wordmark } from "../_components/Wordmark";

const AIRPORTS = [
  { code: "CDG", label: "Paris Charles de Gaulle" },
  { code: "ORY", label: "Paris Orly" },
  { code: "BVA", label: "Paris Beauvais" },
  { code: "LYS", label: "Lyon Saint-Exupéry" },
  { code: "MRS", label: "Marseille Provence" },
  { code: "NCE", label: "Nice Côte d’Azur" },
  { code: "BOD", label: "Bordeaux Mérignac" },
  { code: "NTE", label: "Nantes Atlantique" },
  { code: "TLS", label: "Toulouse Blagnac" },
  { code: "BSL", label: "Bâle-Mulhouse" },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [airport, setAirport] = useState("CDG");
  const [acceptLonghaulStopover, setAcceptLonghaulStopover] = useState(true);
  const [telegramLink, setTelegramLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [userId, setUserId] = useState("");
  const router = useRouter();

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id");
    if (!id) {
      router.push("/signup");
      return;
    }
    setUserId(id);

    getPreferences(id)
      .then((preferences) => {
        if (preferences.airport_codes?.length) setAirport(preferences.airport_codes[0]);
        if (typeof preferences.accept_longhaul_stopover === "boolean") {
          setAcceptLonghaulStopover(preferences.accept_longhaul_stopover);
        }
      })
      .catch(() => {
        // First-time users keep safe defaults.
      });
  }, [router]);

  async function savePreferences() {
    setLoading(true);
    setError("");
    try {
      await updatePreferences(userId, {
        airport_codes: [airport],
        offer_types: ["flight"],
        deal_tier: "regular",
        flight_trip_types: ["round_trip"],
        include_split_tickets: false,
        accept_longhaul_stopover: acceptLonghaulStopover,
      });
      setStep(3);
    } catch {
      setError("Impossible d’enregistrer vos préférences. Vérifiez votre connexion puis réessayez.");
    } finally {
      setLoading(false);
    }
  }

  async function connectTelegram() {
    setLoading(true);
    setError("");
    try {
      const response = await generateTelegramLink(userId);
      setTelegramLink(response.link);
    } catch {
      setTelegramLink("https://t.me/Globegenius_bot");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F3EA] px-4 py-8 md:flex md:items-center md:justify-center md:py-12">
      <div className="w-full max-w-2xl">
        <Link href="/" className="mb-8 block text-center font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>

        <div className="mb-8 flex gap-2 px-8">
          {[1, 2, 3].map((item) => (
            <div key={item} className={`h-1 flex-1 rounded-full ${item <= step ? "bg-[#0E7490]" : "bg-[#D9E2E3]"}`} />
          ))}
        </div>

        <div className="rounded-[30px] border border-[#D9E2E3] bg-white p-6 shadow-[0_22px_60px_rgba(11,42,63,.07)] md:p-9">
          {step === 1 && (
            <div>
              <p className="text-center text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Étape 1 sur 3</p>
              <h1 className="mt-3 text-center font-[family-name:var(--font-dm-serif)] text-3xl">Votre véritable aéroport de départ</h1>
              <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-500">
                Le compte Freemium surveille un aéroport. Choisissez celui que vous pouvez réellement utiliser, sans devoir ajouter un trajet coûteux vers Paris.
              </p>

              <div className="mt-7 grid grid-cols-2 gap-3 md:grid-cols-3">
                {AIRPORTS.map((item) => {
                  const selected = airport === item.code;
                  return (
                    <button
                      key={item.code}
                      type="button"
                      onClick={() => setAirport(item.code)}
                      className={`relative rounded-2xl border-2 p-4 text-left transition-all ${selected ? "border-[#0E7490] bg-[#E9F5F7]" : "border-[#D9E2E3] bg-white hover:border-[#2AB7A9]"}`}
                    >
                      <div className="font-bold text-[#0B2A3F]">{item.code}</div>
                      <div className="mt-1 text-xs leading-5 text-slate-500">{item.label}</div>
                      {selected && <span className="absolute right-2 top-2 rounded-full bg-[#0E7490] px-2 py-1 text-[10px] font-bold text-white">Principal</span>}
                    </button>
                  );
                })}
              </div>

              <div className="mt-5 rounded-2xl border border-[#D9E2E3] bg-[#F7F3EA] p-4 text-xs leading-6 text-slate-500">
                <strong className="text-[#0B2A3F]">À savoir :</strong> la fréquence des alertes varie selon l’aéroport et la période. Paris offre généralement plus de volume ; les régions peuvent être plus irrégulières. GlobeGenius ne garantit pas un nombre fixe de deals et préfère rester silencieux plutôt que signaler une promotion ordinaire.
              </div>

              <button type="button" onClick={() => setStep(2)} className="mt-8 w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078]">
                Continuer
              </button>
            </div>
          )}

          {step === 2 && (
            <div>
              <p className="text-center text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Étape 2 sur 3</p>
              <h1 className="mt-3 text-center font-[family-name:var(--font-dm-serif)] text-3xl">Votre formule Freemium</h1>
              <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-500">
                Vous recevrez les meilleurs allers-retours vérifiés depuis {airport}, dans la limite du quota gratuit et uniquement lorsqu’un prix mérite réellement votre attention.
              </p>

              <div className="mt-7 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-[#E9F5F7] p-4 text-center">
                  <div className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#0E7490]">2</div>
                  <div className="mt-1 text-xs leading-5 text-slate-600">alertes complètes par semaine</div>
                </div>
                <div className="rounded-2xl bg-[#FFF0EA] p-4 text-center">
                  <div className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#E96543]">1</div>
                  <div className="mt-1 text-xs leading-5 text-slate-600">pépite exceptionnelle par mois</div>
                </div>
                <div className="rounded-2xl bg-[#F7F3EA] p-4 text-center">
                  <div className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">1</div>
                  <div className="mt-1 text-xs leading-5 text-slate-600">joker de déverrouillage par mois</div>
                </div>
              </div>

              <div className="mt-6 rounded-2xl border border-[#D9E2E3] p-4">
                <label className="flex cursor-pointer items-start gap-3">
                  <input type="checkbox" checked={acceptLonghaulStopover} onChange={(event) => setAcceptLonghaulStopover(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0E7490]" />
                  <span>
                    <span className="block text-sm font-bold text-[#0B2A3F]">Accepter une escale en long-courrier</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">Les vols européens restent directs. Cette option augmente les opportunités vers les destinations lointaines.</span>
                  </span>
                </label>
              </div>

              <div className="mt-5 rounded-2xl border border-[#FF7A59]/25 bg-[#FFF0EA] p-4 text-sm leading-6 text-slate-600">
                Les allers simples, les combos malins, plusieurs aéroports et les alertes sans quota sont réservés au Premium à 39 € par an. Premium débloque toutes les opportunités qualifiées, mais ne crée pas artificiellement des deals lorsqu’un aéroport est calme.
              </div>

              {error && <div className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

              <div className="mt-8 flex gap-3">
                <button type="button" onClick={() => setStep(1)} className="flex-1 rounded-xl border border-[#D9E2E3] py-3.5 font-semibold text-slate-500 hover:bg-slate-50">Retour</button>
                <button type="button" onClick={savePreferences} disabled={loading} className="flex-1 rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078] disabled:opacity-50">
                  {loading ? "Enregistrement…" : "Enregistrer"}
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="text-center">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Étape essentielle</p>
              <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Connectez Telegram</h1>
              <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-500">
                Les alertes sont envoyées dans le bot dès qu’un prix intéressant est confirmé. Sans connexion Telegram, aucune alerte ne peut être reçue.
              </p>

              <div className="mx-auto mt-7 max-w-md rounded-3xl bg-[#E9F5F7] p-6">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#229ED9] text-xl font-bold text-white">G</div>
                <p className="mt-4 text-sm leading-6 text-slate-600">Ouvrez le bot GlobeGenius puis appuyez sur <strong>Start</strong> pour associer votre compte Freemium.</p>
              </div>

              {!telegramLink ? (
                <button type="button" onClick={connectTelegram} disabled={loading} className="mt-7 w-full rounded-xl bg-[#229ED9] py-3.5 font-bold text-white hover:bg-[#1B86B8] disabled:opacity-50">
                  {loading ? "Création du lien…" : "Connecter Telegram"}
                </button>
              ) : (
                <div className="mt-7 space-y-3">
                  <a href={telegramLink} target="_blank" rel="noopener noreferrer" className="block w-full rounded-xl bg-[#229ED9] py-3.5 font-bold text-white hover:bg-[#1B86B8]">Ouvrir Telegram</a>
                  <button type="button" onClick={() => router.push("/home")} className="w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078]">J’ai lancé le bot — accéder à mon espace</button>
                </div>
              )}

              <button type="button" onClick={() => router.push("/home")} className="mt-5 text-xs leading-5 text-slate-400 underline underline-offset-4 hover:text-slate-600">
                Continuer sans Telegram — je comprends qu’aucune alerte ne sera envoyée
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
