"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getPreferences, updatePreferences, generateTelegramLink } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const AIRPORTS = [
  { code: "CDG", label: "Paris Charles de Gaulle" },
  { code: "ORY", label: "Paris Orly" },
  { code: "LYS", label: "Lyon Saint-Exupery" },
  { code: "MRS", label: "Marseille Provence" },
  { code: "NCE", label: "Nice Cote d'Azur" },
  { code: "BOD", label: "Bordeaux Merignac" },
  { code: "NTE", label: "Nantes Atlantique" },
  { code: "TLS", label: "Toulouse Blagnac" },
];

const OFFER_TYPES = [
  { id: "package", label: "Packages vol + hotel", desc: "Les meilleures offres combinees", icon: "✈️🏨" },
  { id: "flight", label: "Vols seuls", desc: "Billets d'avion a prix casses", icon: "✈️" },
  { id: "accommodation", label: "Hebergements seuls", desc: "Hotels et logements en promo", icon: "🏨" },
];

const DESTINATIONS_EUROPE = [
  { code: "LIS", label: "Lisbonne", emoji: "🇵🇹" },
  { code: "BCN", label: "Barcelone", emoji: "🇪🇸" },
  { code: "FCO", label: "Rome", emoji: "🇮🇹" },
  { code: "ATH", label: "Athenes", emoji: "🇬🇷" },
  { code: "AMS", label: "Amsterdam", emoji: "🇳🇱" },
  { code: "PRG", label: "Prague", emoji: "🇨🇿" },
  { code: "BUD", label: "Budapest", emoji: "🇭🇺" },
  { code: "RAK", label: "Marrakech", emoji: "🇲🇦" },
  { code: "IST", label: "Istanbul", emoji: "🇹🇷" },
  { code: "MAD", label: "Madrid", emoji: "🇪🇸" },
  { code: "BER", label: "Berlin", emoji: "🇩🇪" },
  { code: "DUB", label: "Dublin", emoji: "🇮🇪" },
];

const DESTINATIONS_LONG_COURRIER = [
  { code: "JFK", label: "New York", emoji: "🇺🇸" },
  { code: "YUL", label: "Montreal", emoji: "🇨🇦" },
  { code: "CUN", label: "Cancun", emoji: "🇲🇽" },
  { code: "PUJ", label: "Punta Cana", emoji: "🇩🇴" },
  { code: "BKK", label: "Bangkok", emoji: "🇹🇭" },
  { code: "NRT", label: "Tokyo", emoji: "🇯🇵" },
  { code: "DXB", label: "Dubai", emoji: "🇦🇪" },
  { code: "MLE", label: "Maldives", emoji: "🇲🇻" },
  { code: "MRU", label: "Maurice", emoji: "🇲🇺" },
  { code: "RUN", label: "La Reunion", emoji: "🇫🇷" },
  { code: "PPT", label: "Tahiti", emoji: "🇵🇫" },
  { code: "GIG", label: "Rio de Janeiro", emoji: "🇧🇷" },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [airports, setAirports] = useState<string[]>(["CDG"]);
  const [offerTypes, setOfferTypes] = useState<string[]>(["package", "flight", "accommodation"]);
  const [destinations, setDestinations] = useState<string[]>([]);
  const [minDiscount, setMinDiscount] = useState<number>(20);
  const [isPremium, setIsPremium] = useState(false);
  const [showUpsellBanner, setShowUpsellBanner] = useState(false);
  const [telegramLink, setTelegramLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState("");
  const router = useRouter();

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id");
    if (!id) {
      router.push("/signup");
      return;
    }
    setUserId(id);

    // Preload existing preferences so returning users see their current selection
    getPreferences(id)
      .then((prefs) => {
        if (prefs.airport_codes && prefs.airport_codes.length > 0) {
          setAirports(prefs.airport_codes);
        }
        if (prefs.offer_types && prefs.offer_types.length > 0) {
          setOfferTypes(prefs.offer_types);
        }
        if (prefs.preferred_destinations && prefs.preferred_destinations.length > 0) {
          setDestinations(prefs.preferred_destinations);
        }
        if (prefs.min_discount) {
          setMinDiscount(prefs.min_discount);
        }
      })
      .catch(() => {
        // First-time user or API error — keep defaults
      });

    // Check premium status for upsell gating on high thresholds
    const token = localStorage.getItem("gg_token");
    if (token) {
      fetch(`${API_URL}/api/stripe/status`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => r.json())
        .then((d) => setIsPremium(d.is_premium || false))
        .catch(() => {});
    }
  }, [router]);

  function toggleOfferType(id: string) {
    setOfferTypes((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  function toggleDestination(code: string) {
    setDestinations((prev) =>
      prev.includes(code) ? prev.filter((d) => d !== code) : [...prev, code]
    );
  }

  async function handleSavePreferences() {
    setLoading(true);
    try {
      await updatePreferences(userId, {
        airport_codes: airports.length > 0 ? airports : ["CDG"],
        offer_types: offerTypes.length > 0 ? offerTypes : ["package"],
        preferred_destinations: destinations.length > 0 ? destinations : null,
        min_discount: minDiscount,
      });
      setStep(4);
    } catch {
      // Continue anyway
      setStep(4);
    } finally {
      setLoading(false);
    }
  }

  async function handleConnectTelegram() {
    setLoading(true);
    try {
      const res = await generateTelegramLink(userId);
      setTelegramLink(res.link);
    } catch {
      setTelegramLink("https://t.me/GlobeGeniusBot");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-start md:items-center justify-center px-4 md:px-5 py-8 md:py-0">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 justify-center mb-8">
          <img src="/globe1.png" alt="Globe Genius" className="w-9 h-9 shrink-0 object-contain" />
          <span className="font-[family-name:var(--font-dm-serif)] text-xl leading-none">Globe Genius</span>
        </Link>

        {/* Progress */}
        <div className="flex gap-2 mb-8 max-w-xs mx-auto">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className="h-1 flex-1 rounded-full transition-colors"
              style={{ background: s <= step ? "#FF6B47" : "#F0E6D8" }}
            />
          ))}
        </div>

        {/* ── STEP 1: Airport ── */}
        {step === 1 && (
          <div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-center mb-2">
              Vos aeroports de depart
            </h2>
            <p className="text-gray-400 text-sm text-center mb-6">
              Selectionnez un ou plusieurs aeroports. On surveillera les vols au depart de chacun.
            </p>

            <div className="grid grid-cols-2 gap-3 mb-8">
              {AIRPORTS.map((ap) => {
                const selected = airports.includes(ap.code);
                return (
                  <button
                    key={ap.code}
                    onClick={() =>
                      setAirports((prev) =>
                        selected ? prev.filter((c) => c !== ap.code) : [...prev, ap.code]
                      )
                    }
                    className="text-left p-3 rounded-xl border-2 transition-all relative"
                    style={{
                      borderColor: selected ? "#06b6d4" : "#e5e7eb",
                      background: selected ? "#ecfeff" : "white",
                    }}
                  >
                    <div className="font-semibold text-sm">{ap.code}</div>
                    <div className="text-xs text-gray-400">{ap.label}</div>
                    {selected && (
                      <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-cyan-500 flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => setStep(2)}
              disabled={airports.length === 0}
              className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continuer ({airports.length} aeroport{airports.length !== 1 ? "s" : ""})
            </button>
          </div>
        )}

        {/* ── STEP 2: Offer types ── */}
        {step === 2 && (
          <div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-center mb-2">
              Types d'offres
            </h2>
            <p className="text-gray-400 text-sm text-center mb-6">
              Quels types de deals souhaitez-vous recevoir ?
            </p>

            <div className="space-y-3 mb-8">
              {OFFER_TYPES.map((ot) => (
                <button
                  key={ot.id}
                  onClick={() => toggleOfferType(ot.id)}
                  className="w-full text-left p-4 rounded-xl border-2 flex items-center gap-3 transition-all"
                  style={{
                    borderColor: offerTypes.includes(ot.id) ? "#06b6d4" : "#e5e7eb",
                    background: offerTypes.includes(ot.id) ? "#ecfeff" : "white",
                  }}
                >
                  <span className="text-xl">{ot.icon}</span>
                  <div>
                    <div className="font-semibold text-sm">{ot.label}</div>
                    <div className="text-xs text-gray-400">{ot.desc}</div>
                  </div>
                  <div className="ml-auto">
                    {offerTypes.includes(ot.id) && (
                      <div className="w-5 h-5 rounded-full bg-cyan-500 flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex-1 py-3 rounded-xl border border-gray-200 text-gray-500 font-medium hover:bg-gray-50 transition-colors">
                Retour
              </button>
              <button onClick={() => setStep(3)} className="flex-1 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all">
                Continuer
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: Destinations ── */}
        {step === 3 && (
          <div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-center mb-2">
              Destinations preferees
            </h2>
            <p className="text-gray-400 text-sm text-center mb-6">
              Optionnel — selectionnez vos destinations favorites ou laissez vide pour tout recevoir.
            </p>

            <div className="mb-3">
              <div className="text-xs font-bold text-gray-400 tracking-wider uppercase mb-2">Europe & Maghreb</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {DESTINATIONS_EUROPE.map((d) => (
                  <button
                    key={d.code}
                    onClick={() => toggleDestination(d.code)}
                    className="p-2.5 rounded-xl border-2 text-center transition-all"
                    style={{
                      borderColor: destinations.includes(d.code) ? "#06b6d4" : "#e5e7eb",
                      background: destinations.includes(d.code) ? "#ecfeff" : "white",
                    }}
                  >
                    <div className="text-base mb-0.5">{d.emoji}</div>
                    <div className="text-[11px] font-medium">{d.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-6">
              <div className="text-xs font-bold text-gray-400 tracking-wider uppercase mb-2">Long-courrier</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {DESTINATIONS_LONG_COURRIER.map((d) => (
                  <button
                    key={d.code}
                    onClick={() => toggleDestination(d.code)}
                    className="p-2.5 rounded-xl border-2 text-center transition-all"
                    style={{
                      borderColor: destinations.includes(d.code) ? "#06b6d4" : "#e5e7eb",
                      background: destinations.includes(d.code) ? "#ecfeff" : "white",
                    }}
                  >
                    <div className="text-base mb-0.5">{d.emoji}</div>
                    <div className="text-[11px] font-medium">{d.label}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <h3 className="font-semibold text-[15px] mb-1">Seuil minimum de réduction</h3>
              <p className="text-sm text-gray-400 mb-4">Vous ne recevrez des alertes qu&apos;à partir de ce pourcentage.</p>
              <div className="flex flex-wrap gap-2">
                {[20, 30, 40, 50, 60].map((val) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => {
                      if (!isPremium && val >= 40) {
                        setShowUpsellBanner(true);
                        return;
                      }
                      setShowUpsellBanner(false);
                      setMinDiscount(val);
                    }}
                    className="px-4 py-2 rounded-xl border-2 font-semibold text-sm transition-all"
                    style={{
                      borderColor: minDiscount === val ? "#FF6B47" : "#F0E6D8",
                      background: minDiscount === val ? "#FFF1EC" : "#FFFEF9",
                      color: minDiscount === val ? "#E55A38" : "#6b7280",
                    }}
                  >
                    -{val}%
                  </button>
                ))}
              </div>
              {showUpsellBanner && !isPremium && (
                <div className="mt-3 bg-[#FFF1EC] border border-[#FF6B47] rounded-xl p-3 text-sm text-[#0A1F3D]/70">
                  💎 Les seuils 40% et plus sont réservés aux abonnés Premium.{" "}
                  <a href="/home" className="underline font-semibold">Passer en Premium</a>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 py-3 rounded-xl border border-gray-200 text-gray-500 font-medium hover:bg-gray-50 transition-colors">
                Retour
              </button>
              <button
                onClick={handleSavePreferences}
                disabled={loading}
                className="flex-1 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50"
              >
                {loading ? "Enregistrement..." : "Continuer"}
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 4: Telegram ── */}
        {step === 4 && (
          <div className="text-center">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-2">
              Connecter Telegram
            </h2>
            <p className="text-gray-400 text-sm mb-8">
              Recevez vos alertes de deals directement sur Telegram.
            </p>

            {!telegramLink ? (
              <button
                onClick={handleConnectTelegram}
                disabled={loading}
                className="w-full bg-[#0088cc] text-white font-semibold py-3.5 rounded-xl hover:bg-[#006daa] transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mb-4"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
                {loading ? "Generation du lien..." : "Connecter Telegram"}
              </button>
            ) : (
              <div className="mb-6">
                <a
                  href={telegramLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full bg-[#0088cc] text-white font-semibold py-3.5 rounded-xl hover:bg-[#006daa] transition-colors mb-3"
                >
                  Ouvrir Telegram →
                </a>
                <p className="text-xs text-gray-400">
                  Cliquez sur "Start" dans Telegram pour activer les alertes.
                </p>
              </div>
            )}

            <button
              onClick={() => router.push("/home")}
              className="w-full py-3 rounded-xl border border-gray-200 text-gray-500 font-medium hover:bg-gray-50 transition-colors"
            >
              {telegramLink ? "Acceder au dashboard" : "Passer cette etape"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
