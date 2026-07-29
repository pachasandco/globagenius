"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { generateTelegramLink, getPreferences, updatePreferences, type FlightTripType } from "@/lib/api";
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
  const [airports, setAirports] = useState<string[]>(["CDG"]);
  const [flightTripTypes, setFlightTripTypes] = useState<FlightTripType[]>(["round_trip"]);
  const [includeSplitTickets, setIncludeSplitTickets] = useState(false);
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
        if (preferences.airport_codes?.length) setAirports(preferences.airport_codes);
        if (preferences.flight_trip_types?.length) setFlightTripTypes(preferences.flight_trip_types);
        if (typeof preferences.include_split_tickets === "boolean") setIncludeSplitTickets(preferences.include_split_tickets);
        if (typeof preferences.accept_longhaul_stopover === "boolean") setAcceptLonghaulStopover(preferences.accept_longhaul_stopover);
      })
      .catch(() => {
        // First-time users keep safe defaults.
      });
  }, [router]);

  function toggleAirport(code: string) {
    setAirports((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]);
  }

  function toggleTripType(type: FlightTripType) {
    setFlightTripTypes((current) => {
      if (current.includes(type)) return current.length > 1 ? current.filter((item) => item !== type) : current;
      return [...current, type];
    });
  }

  async function savePreferences() {
    setLoading(true);
    setError("");
    try {
      await updatePreferences(userId, {
        airport_codes: airports.length ? airports : ["CDG"],
        offer_types: ["flight"],
        deal_tier: "regular",
        flight_trip_types: flightTripTypes.length ? flightTripTypes : ["round_trip"],
        include_split_tickets: includeSplitTickets && flightTripTypes.includes("round_trip"),
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
              <h1 className="mt-3 text-center font-[family-name:var(--font-dm-serif)] text-3xl">Vos aéroports de départ</h1>
              <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-500">
                Pendant Premium Découverte, tous les aéroports sélectionnés sont surveillés. Ensuite, le Freemium conserve le premier aéroport de la sélection comme départ principal.
              </p>

              <div className="mt-5 rounded-2xl bg-[#E9F5F7] px-4 py-3 text-sm leading-6 text-slate-600">
                <strong className="text-[#0B2A3F]">Conseil :</strong> sélectionnez d’abord l’aéroport que vous utilisez le plus souvent.
              </div>

              <div className="mt-7 grid grid-cols-2 gap-3 md:grid-cols-3">
                {AIRPORTS.map((airport) => {
                  const selected = airports.includes(airport.code);
                  const primary = selected && airports[0] === airport.code;
                  return (
                    <button
                      key={airport.code}
                      type="button"
                      onClick={() => toggleAirport(airport.code)}
                      className={`relative rounded-2xl border-2 p-4 text-left transition-all ${selected ? "border-[#0E7490] bg-[#E9F5F7]" : "border-[#D9E2E3] bg-white hover:border-[#2AB7A9]"}`}
                    >
                      <div className="font-bold text-[#0B2A3F]">{airport.code}</div>
                      <div className="mt-1 text-xs leading-5 text-slate-500">{airport.label}</div>
                      {primary ? (
                        <span className="absolute right-2 top-2 rounded-full bg-[#0E7490] px-2 py-1 text-[10px] font-bold text-white">Principal</span>
                      ) : selected ? (
                        <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-[#0E7490] text-xs text-white">✓</span>
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <button type="button" onClick={() => setStep(2)} disabled={!airports.length} className="mt-8 w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078] disabled:opacity-50">
                Continuer avec {airports.length} aéroport{airports.length > 1 ? "s" : ""}
              </button>
            </div>
          )}

          {step === 2 && (
            <div>
              <p className="text-center text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Étape 2 sur 3</p>
              <h1 className="mt-3 text-center font-[family-name:var(--font-dm-serif)] text-3xl">Les vols qui vous intéressent</h1>
              <p className="mx-auto mt-3 max-w-lg text-center text-sm leading-6 text-slate-500">Ces préférences seront pleinement actives pendant vos 7 jours Premium et restent enregistrées pour une future souscription.</p>

              <div className="mt-6 rounded-2xl border border-[#FF7A59]/25 bg-[#FFF0EA] p-4 text-sm leading-6 text-slate-600">
                Après l’essai, le Freemium envoie les alertes complètes uniquement pour les allers-retours classiques. Les allers simples et les combos restent visibles sous forme d’opportunités Premium.
              </div>

              <div className="mt-8 grid grid-cols-2 gap-3">
                {[
                  ["round_trip", "Aller-retour", "La majorité des alertes GlobeGenius"],
                  ["one_way", "Aller simple", "Disponible en Premium Découverte et Premium"],
                ].map(([id, label, copy]) => {
                  const type = id as FlightTripType;
                  const selected = flightTripTypes.includes(type);
                  return (
                    <button key={id} type="button" onClick={() => toggleTripType(type)} className={`rounded-2xl border-2 p-5 text-left ${selected ? "border-[#0E7490] bg-[#E9F5F7]" : "border-[#D9E2E3]"}`}>
                      <div className="font-bold text-[#0B2A3F]">{label}</div>
                      <div className="mt-2 text-xs leading-5 text-slate-500">{copy}</div>
                    </button>
                  );
                })}
              </div>

              <div className="mt-5 space-y-3">
                <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-[#D9E2E3] p-4">
                  <input type="checkbox" checked={includeSplitTickets} disabled={!flightTripTypes.includes("round_trip")} onChange={(event) => setIncludeSplitTickets(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0E7490]" />
                  <span>
                    <span className="block text-sm font-bold text-[#0B2A3F]">Inclure les combos malins</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">Deux billets aller simple séparés lorsqu’ils sont moins chers qu’un aller-retour classique. Premium uniquement après l’essai.</span>
                  </span>
                </label>
                <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-[#D9E2E3] p-4">
                  <input type="checkbox" checked={acceptLonghaulStopover} onChange={(event) => setAcceptLonghaulStopover(event.target.checked)} className="mt-1 h-4 w-4 accent-[#0E7490]" />
                  <span>
                    <span className="block text-sm font-bold text-[#0B2A3F]">Accepter une escale en long-courrier</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">Les vols européens restent directs. Cette option augmente les opportunités vers les destinations lointaines.</span>
                  </span>
                </label>
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
              <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl">Connectez Telegram et démarrez vos 7 jours Premium</h1>
              <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-500">
                La période Premium Découverte commence lorsque vous appuyez sur <strong>Start</strong> dans le bot. Sans connexion Telegram, le compteur ne démarre pas et aucune alerte n’est envoyée.
              </p>

              <div className="mx-auto mt-7 max-w-md rounded-3xl bg-[#E9F5F7] p-6">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#229ED9] text-xl font-bold text-white">G</div>
                <p className="mt-4 text-sm leading-6 text-slate-600">Ouvrez le bot GlobeGenius puis appuyez sur <strong>Start</strong> pour associer votre compte et activer l’essai sans carte bancaire.</p>
              </div>

              {!telegramLink ? (
                <button type="button" onClick={connectTelegram} disabled={loading} className="mt-7 w-full rounded-xl bg-[#229ED9] py-3.5 font-bold text-white hover:bg-[#1B86B8] disabled:opacity-50">
                  {loading ? "Création du lien…" : "Connecter Telegram et démarrer l’essai"}
                </button>
              ) : (
                <div className="mt-7 space-y-3">
                  <a href={telegramLink} target="_blank" rel="noopener noreferrer" className="block w-full rounded-xl bg-[#229ED9] py-3.5 font-bold text-white hover:bg-[#1B86B8]">Ouvrir Telegram</a>
                  <button type="button" onClick={() => router.push("/home")} className="w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white hover:bg-[#0A6078]">J’ai lancé le bot — accéder à mon espace</button>
                </div>
              )}

              <button type="button" onClick={() => router.push("/home")} className="mt-5 text-xs leading-5 text-slate-400 underline underline-offset-4 hover:text-slate-600">
                Continuer sans Telegram — l’essai ne démarrera pas et aucune alerte ne sera envoyée
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
