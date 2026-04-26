"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getPreferences, updatePreferences, changePassword, clearSessionCookie } from "@/lib/api";

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

const ALL_DESTINATIONS = [
  { code: "LIS", label: "Lisbonne" },
  { code: "BCN", label: "Barcelone" },
  { code: "FCO", label: "Rome" },
  { code: "ATH", label: "Athènes" },
  { code: "NAP", label: "Naples" },
  { code: "OPO", label: "Porto" },
  { code: "AMS", label: "Amsterdam" },
  { code: "BER", label: "Berlin" },
  { code: "PRG", label: "Prague" },
  { code: "BUD", label: "Budapest" },
  { code: "DUB", label: "Dublin" },
  { code: "EDI", label: "Édimbourg" },
  { code: "IST", label: "Istanbul" },
  { code: "MAD", label: "Madrid" },
  { code: "MXP", label: "Milan" },
  { code: "VCE", label: "Venise" },
  { code: "VIE", label: "Vienne" },
  { code: "WAW", label: "Varsovie" },
  { code: "ZAG", label: "Zagreb" },
  { code: "CPH", label: "Copenhague" },
  { code: "HEL", label: "Helsinki" },
  { code: "OSL", label: "Oslo" },
  { code: "ARN", label: "Stockholm" },
  { code: "AGP", label: "Malaga" },
  { code: "PMI", label: "Palma de Majorque" },
  { code: "TFS", label: "Ténérife" },
  { code: "HER", label: "Héraklion" },
  { code: "SPU", label: "Split" },
  { code: "DBV", label: "Dubrovnik" },
  { code: "ACE", label: "Lanzarote" },
  { code: "ALC", label: "Alicante" },
  { code: "BLQ", label: "Bologne" },
  { code: "BRI", label: "Bari" },
  { code: "BRU", label: "Bruxelles" },
  { code: "CAG", label: "Cagliari" },
  { code: "CFU", label: "Corfou" },
  { code: "CTA", label: "Catane" },
  { code: "FAO", label: "Faro" },
  { code: "FNC", label: "Madère" },
  { code: "FUE", label: "Fuerteventura" },
  { code: "IBZ", label: "Ibiza" },
  { code: "JMK", label: "Mykonos" },
  { code: "JTR", label: "Santorin" },
  { code: "KRK", label: "Cracovie" },
  { code: "LPA", label: "Las Palmas" },
  { code: "OLB", label: "Olbia" },
  { code: "PDL", label: "Ponta Delgada" },
  { code: "RHO", label: "Rhodes" },
  { code: "RIX", label: "Riga" },
  { code: "SAW", label: "Istanbul Sabiha" },
  { code: "SKG", label: "Thessalonique" },
  { code: "SOF", label: "Sofia" },
  { code: "SVQ", label: "Séville" },
  { code: "TIV", label: "Tivat" },
  { code: "TLL", label: "Tallinn" },
  { code: "VLC", label: "Valence" },
  { code: "VNO", label: "Vilnius" },
  { code: "ZRH", label: "Zurich" },
  { code: "LHR", label: "Londres Heathrow" },
  { code: "LGW", label: "Londres Gatwick" },
  { code: "STN", label: "Londres Stansted" },
  { code: "LTN", label: "Londres Luton" },
  { code: "MAN", label: "Manchester" },
  { code: "BHX", label: "Birmingham" },
  { code: "GLA", label: "Glasgow" },
  { code: "RAK", label: "Marrakech" },
  { code: "CMN", label: "Casablanca" },
  { code: "AGA", label: "Agadir" },
  { code: "FEZ", label: "Fès" },
  { code: "NDR", label: "Nador" },
  { code: "TNG", label: "Tanger" },
  { code: "ESU", label: "Essaouira" },
  { code: "TUN", label: "Tunis" },
  { code: "MIR", label: "Monastir" },
  { code: "DJE", label: "Djerba" },
  { code: "ALG", label: "Alger" },
  { code: "ORN", label: "Oran" },
  { code: "CZL", label: "Constantine" },
  { code: "TLM", label: "Tlemcen" },
  { code: "AAE", label: "Annaba" },
  { code: "BJA", label: "Béjaïa" },
  { code: "CAI", label: "Le Caire" },
  { code: "TLV", label: "Tel Aviv" },
  { code: "HRG", label: "Hurghada" },
  { code: "SSH", label: "Charm el-Cheikh" },
  { code: "DXB", label: "Dubaï" },
  { code: "CPT", label: "Le Cap" },
  { code: "JNB", label: "Johannesburg" },
  { code: "ZNZ", label: "Zanzibar" },
  { code: "JFK", label: "New York" },
  { code: "EWR", label: "New York Newark" },
  { code: "YUL", label: "Montréal" },
  { code: "MIA", label: "Miami" },
  { code: "LAX", label: "Los Angeles" },
  { code: "SFO", label: "San Francisco" },
  { code: "CUN", label: "Cancún" },
  { code: "PUJ", label: "Punta Cana" },
  { code: "BOG", label: "Bogotá" },
  { code: "GIG", label: "Rio de Janeiro" },
  { code: "EZE", label: "Buenos Aires" },
  { code: "LIM", label: "Lima" },
  { code: "SCL", label: "Santiago" },
  { code: "BKK", label: "Bangkok" },
  { code: "SIN", label: "Singapour" },
  { code: "KUL", label: "Kuala Lumpur" },
  { code: "NRT", label: "Tokyo Narita" },
  { code: "HND", label: "Tokyo Haneda" },
  { code: "ICN", label: "Séoul" },
  { code: "HKG", label: "Hong Kong" },
  { code: "BOM", label: "Mumbai" },
  { code: "DEL", label: "Delhi" },
  { code: "MLE", label: "Malé" },
  { code: "MRU", label: "Maurice" },
  { code: "RUN", label: "La Réunion" },
  { code: "PPT", label: "Papeete" },
  { code: "GVA", label: "Genève" },
  { code: "SYD", label: "Sydney" },
];

export default function ProfilePage() {
  const [airports, setAirports] = useState<string[]>([]);
  const [offerTypes, setOfferTypes] = useState<string[]>([]);
  const [dealTier, setDealTier] = useState<string>("regular");
  const [blockedDestinations, setBlockedDestinations] = useState<string[]>([]);
  const [destSearch, setDestSearch] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const destInputRef = useRef<HTMLInputElement>(null);
  const [isPremium, setIsPremium] = useState(false);
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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const router = useRouter();

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const filteredSuggestions = destSearch.trim().length > 0
    ? ALL_DESTINATIONS.filter((d) => {
        const q = destSearch.toLowerCase();
        return (
          !blockedDestinations.includes(d.code) &&
          (d.label.toLowerCase().includes(q) || d.code.toLowerCase().includes(q))
        );
      }).slice(0, 8)
    : [];

  useEffect(() => {
    const id = localStorage.getItem("gg_user_id");
    const userEmail = localStorage.getItem("gg_email");
    if (!id) {
      router.push("/signup");
      return;
    }
    setUserId(id);
    setEmail(userEmail || "");

    getPreferences(id)
      .then((prefs) => {
        if (prefs.airport_codes && prefs.airport_codes.length > 0) {
          setAirports(prefs.airport_codes);
        }
        if (prefs.offer_types && prefs.offer_types.length > 0) {
          setOfferTypes(prefs.offer_types);
        }
        if (prefs.deal_tier) {
          setDealTier(prefs.deal_tier);
        }
        if (prefs.blocked_destinations) {
          setBlockedDestinations(prefs.blocked_destinations);
        }
      })
      .catch(() => {
        setError("Erreur lors du chargement des préférences");
      })
      .finally(() => {
        setLoading(false);
      });

    const token = localStorage.getItem("gg_token");
    if (token) {
      fetch(`${API_URL}/api/stripe/status`, { headers: { Authorization: `Bearer ${token}` } })
        .then((r) => r.json())
        .then((d) => setIsPremium(d.is_premium || false))
        .catch(() => {});
    }
  }, [router, API_URL]);

  function blockDestination(code: string) {
    setBlockedDestinations((prev) => prev.includes(code) ? prev : [...prev, code]);
    setDestSearch("");
    setShowSuggestions(false);
  }

  function unblockDestination(code: string) {
    setBlockedDestinations((prev) => prev.filter((c) => c !== code));
  }

  function getDestLabel(code: string): string {
    const found = ALL_DESTINATIONS.find((d) => d.code === code);
    return found ? `${found.label} (${code})` : code;
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await updatePreferences(userId, {
        airport_codes: airports.length > 0 ? airports : ["CDG"],
        offer_types: offerTypes.length > 0 ? offerTypes : ["flight"],
        deal_tier: dealTier,
        blocked_destinations: blockedDestinations,
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

  async function handleDeleteAccount() {
    setDeleting(true);
    setError("");
    try {
      const token = localStorage.getItem("gg_token");
      const res = await fetch(`${API_URL}/api/users/${userId}/account`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erreur lors de la suppression");
      }
      localStorage.clear();
      clearSessionCookie();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression du compte");
      setDeleting(false);
      setShowDeleteConfirm(false);
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
                } catch {
                  /* portal redirect failed silently */
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

        {/* ── Destinations masquées ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Destinations masquées</h2>
          <p className="text-gray-400 text-sm mb-6">
            Masquez les destinations pour lesquelles vous ne souhaitez plus recevoir d&apos;alertes.
            Vous pouvez les réactiver à tout moment.
          </p>

          {/* Search input */}
          <div className="relative mb-4" ref={destInputRef as React.RefObject<HTMLDivElement>}>
            <input
              type="text"
              value={destSearch}
              onChange={(e) => {
                setDestSearch(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              placeholder="Rechercher une destination (ex: Lisbonne, BCN...)"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#FF6B47] text-sm"
            />
            {showSuggestions && filteredSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                {filteredSuggestions.map((d) => (
                  <button
                    key={d.code}
                    onMouseDown={() => blockDestination(d.code)}
                    className="w-full text-left px-4 py-2.5 hover:bg-gray-50 flex items-center justify-between text-sm"
                  >
                    <span>{d.label}</span>
                    <span className="text-gray-400 text-xs font-mono">{d.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Blocked pills */}
          {blockedDestinations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {blockedDestinations.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-full text-sm text-gray-700"
                >
                  {getDestLabel(code)}
                  <button
                    onClick={() => unblockDestination(code)}
                    className="ml-0.5 text-gray-400 hover:text-gray-700 transition-colors leading-none"
                    aria-label={`Retirer ${code}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">Aucune destination masquée.</p>
          )}
        </div>

        {/* Deal Tier — hidden until feature is re-enabled */}

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Enregistrement..." : "Enregistrer les modifications"}
        </button>

        {/* ── Danger zone ── */}
        <div className="mt-16 pt-8 border-t border-gray-200">
          <h2 className="text-base font-semibold text-gray-500 mb-1">Zone de danger</h2>
          <p className="text-gray-400 text-sm mb-4">
            La suppression de votre compte est irréversible. Toutes vos données seront effacées.
          </p>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-5 py-2.5 border border-red-200 text-red-500 text-sm font-semibold rounded-xl hover:bg-red-50 transition-colors"
            >
              Supprimer mon compte
            </button>
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-xl p-5 space-y-4">
              <p className="text-sm text-red-700 font-medium">
                Êtes-vous sûr ? Cette action supprimera définitivement votre compte, vos préférences et vos alertes.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-2.5 border border-gray-200 text-gray-600 text-sm font-semibold rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleting}
                  className="flex-1 py-2.5 bg-red-500 hover:bg-red-600 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {deleting ? "Suppression..." : "Oui, supprimer définitivement"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
