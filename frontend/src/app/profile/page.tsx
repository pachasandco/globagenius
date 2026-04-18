"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getPreferences, updatePreferences } from "@/lib/api";

const AIRPORTS = [
  { code: "CDG", label: "Paris Charles de Gaulle" },
  { code: "ORY", label: "Paris Orly" },
  { code: "LYS", label: "Lyon Saint-Exupery" },
  { code: "MRS", label: "Marseille Provence" },
  { code: "NCE", label: "Nice Cote d'Azur" },
  { code: "BOD", label: "Bordeaux Merignac" },
  { code: "NTE", label: "Nantes Atlantique" },
  { code: "TLS", label: "Toulouse Blagnac" },
  { code: "BVA", label: "Paris Beauvais" },
];

const OFFER_TYPES = [
  { id: "flight", label: "Vols à prix cassés", desc: "Billets d'avion aller-retour en promo", icon: "✈️" },
];

export default function ProfilePage() {
  const [airports, setAirports] = useState<string[]>([]);
  const [offerTypes, setOfferTypes] = useState<string[]>([]);
  const [minDiscount, setMinDiscount] = useState<number>(20);
  const [isPremium, setIsPremium] = useState(false);
  const [showUpsellBanner, setShowUpsellBanner] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id");
    if (!id) {
      router.push("/signup");
      return;
    }
    setUserId(id);

    // Load existing preferences
    getPreferences(id)
      .then((prefs) => {
        if (prefs.airport_codes && prefs.airport_codes.length > 0) {
          setAirports(prefs.airport_codes);
        }
        if (prefs.offer_types && prefs.offer_types.length > 0) {
          setOfferTypes(prefs.offer_types);
        }
        if (prefs.min_discount) {
          setMinDiscount(prefs.min_discount);
        }
      })
      .catch((err) => {
        setError("Erreur lors du chargement des préférences");
      })
      .finally(() => {
        setLoading(false);
      });

    // Check premium status
    const token = localStorage.getItem("gg_token");
    if (token) {
      fetch(`${API_URL}/api/stripe/status`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => r.json())
        .then((d) => setIsPremium(d.is_premium || false))
        .catch(() => {});
    }
  }, [router, API_URL]);

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await updatePreferences(userId, {
        airport_codes: airports.length > 0 ? airports : ["CDG"],
        offer_types: offerTypes.length > 0 ? offerTypes : ["flight"],
        min_discount: minDiscount,
      });
      setSuccess("Préférences mises à jour avec succès !");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError("Erreur lors de la sauvegarde des préférences");
    } finally {
      setSaving(false);
    }
  }

  function toggleOfferType(id: string) {
    setOfferTypes((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFF8F0] flex items-center justify-center">
        <div className="text-gray-500">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-2xl mx-auto px-4 md:px-5 py-4 flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <Link href="/home" className="text-gray-400 text-sm hover:text-gray-600">
            Accueil
          </Link>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 md:px-5 py-12">
        <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl mb-1">Mon profil</h1>
        <p className="text-gray-400 mb-8">Mettez à jour vos préférences de voyage</p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
            ✅ {success}
          </div>
        )}

        {/* ── Airports ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Aéroports de départ</h2>
          <p className="text-gray-400 text-sm mb-6">
            Sélectionnez un ou plusieurs aéroports. Nous surveillerons les vols au départ de chacun.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
        </div>

        {/* ── Offer Types ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Types d'offres</h2>
          <p className="text-gray-400 text-sm mb-6">Quels types de deals souhaitez-vous recevoir ?</p>

          <div className="space-y-3">
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
        </div>

        {/* ── Min Discount ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Seuil minimum de réduction</h2>
          <p className="text-gray-400 text-sm mb-6">
            Vous ne recevrez des alertes qu&apos;à partir de ce pourcentage.
          </p>

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
            <div className="mt-4 bg-[#FFF1EC] border border-[#FF6B47] rounded-xl p-4 text-sm text-[#0A1F3D]/70">
              💎 Les deals -30% et plus sont réservés Premium. 29€/an, remboursé dès le 1er voyage.{" "}
              <a href="/home" className="underline font-semibold">Débloquer Premium →</a>
            </div>
          )}
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Enregistrement..." : "Enregistrer les modifications"}
        </button>
      </div>
    </div>
  );
}
