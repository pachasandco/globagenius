"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getPreferences, updatePreferences, changePassword } from "@/lib/api";

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
  const [email, setEmail] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id");
    const userEmail = localStorage.getItem("gg_email");
    if (!id) {
      router.push("/signup");
      return;
    }
    setUserId(id);
    setEmail(userEmail || "");

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

  async function handleChangeEmail() {
    if (!newEmail.trim()) {
      setError("Veuillez entrer une adresse email");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const token = localStorage.getItem("gg_token");
      const res = await fetch(`${API_URL}/api/users/${userId}/email`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ email: newEmail }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erreur lors de la modification de l'email");
      }

      localStorage.setItem("gg_email", newEmail);
      setEmail(newEmail);
      setNewEmail("");
      setShowEmailForm(false);
      setSuccess("Email modifié avec succès !");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la modification de l'email");
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword() {
    if (!currentPassword || !newPassword) {
      setError("Veuillez remplir tous les champs");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await changePassword(userId, currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setShowPasswordForm(false);
      setSuccess("Mot de passe modifié avec succès !");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la modification du mot de passe");
    } finally {
      setSaving(false);
    }
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
        <p className="text-gray-400 mb-8">Mettez à jour vos préférences et votre compte</p>

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

        {/* ── Email ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Adresse email</h2>
          <p className="text-gray-400 text-sm mb-4">Votre email de connexion</p>

          {!showEmailForm ? (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
              <span className="text-gray-900">{email}</span>
              <button
                onClick={() => setShowEmailForm(true)}
                className="text-sm text-[#FF6B47] hover:text-[#E55A38] font-semibold transition-colors"
              >
                Modifier
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="Nouvelle adresse email"
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#FF6B47]"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowEmailForm(false);
                    setNewEmail("");
                  }}
                  className="flex-1 py-2 rounded-xl border border-gray-200 text-gray-500 font-medium hover:bg-gray-50 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleChangeEmail}
                  disabled={saving || !newEmail.trim()}
                  className="flex-1 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-2 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? "Modification..." : "Confirmer"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Password ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Mot de passe</h2>
          <p className="text-gray-400 text-sm mb-6">
            Sécurisez votre compte en changeant votre mot de passe.
          </p>

          {!showPasswordForm ? (
            <div className="bg-gray-50 rounded-xl p-4 flex items-center justify-between">
              <div>
                <div className="text-gray-600 font-medium">••••••••</div>
              </div>
              <button
                onClick={() => setShowPasswordForm(true)}
                className="px-4 py-2 bg-[#FF6B47] hover:bg-[#E55A38] text-white text-sm font-semibold rounded-lg transition-colors"
              >
                Modifier
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <input
                type="password"
                placeholder="Mot de passe actuel"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm transition-colors"
              />
              <input
                type="password"
                placeholder="Nouveau mot de passe (min. 6 caractères)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm transition-colors"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowPasswordForm(false);
                    setCurrentPassword("");
                    setNewPassword("");
                    setError("");
                  }}
                  className="flex-1 px-4 py-2 border border-gray-200 text-gray-600 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleChangePassword}
                  disabled={saving || !currentPassword || !newPassword}
                  className="flex-1 px-4 py-2 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? "Modification..." : "Confirmer"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Abonnement ── */}
        {isPremium && (
          <div className="mb-12">
            <h2 className="text-xl font-semibold mb-1">Abonnement</h2>
            <div className="mb-4 inline-block px-3 py-1 bg-green-50 border border-green-200 rounded-full text-sm text-green-700 font-semibold">
              ✅ Abonnement Premium actif
            </div>
            <p className="text-gray-400 text-sm mb-6">
              Gérez votre abonnement Premium.
            </p>
            <button
              onClick={async () => {
                try {
                  const token = localStorage.getItem("gg_token");
                  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stripe/portal`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
                  });
                  const data = await res.json();
                  if (data.portal_url) window.location.href = data.portal_url;
                } catch (err) {
                  console.error("Erreur:", err);
                }
              }}
              className="px-6 py-3 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold rounded-lg transition-colors"
            >
              Gérer mon abonnement →
            </button>
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
