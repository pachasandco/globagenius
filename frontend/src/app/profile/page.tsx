"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getPreferences, updatePreferences, changePassword, clearSessionCookie, getTelegramStatus, generateTelegramLink, cancelSubscription, type FlightTripType, type CancellationReason } from "@/lib/api";
import { Wordmark } from "../_components/Wordmark";

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
  { code: "SAW", label: "Istanbul Sabiha" },
  { code: "MAD", label: "Madrid" },
  { code: "MXP", label: "Milan Malpensa" },
  { code: "LIN", label: "Milan Linate" },
  { code: "BGY", label: "Milan Bergame" },
  { code: "VCE", label: "Venise" },
  { code: "TSF", label: "Venise Trévise" },
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
  { code: "BSL", label: "Bâle-Mulhouse" },
  { code: "GVA", label: "Genève" },
  { code: "LUX", label: "Luxembourg" },
  { code: "BRU", label: "Bruxelles" },
  { code: "OTP", label: "Bucarest" },
  { code: "BEG", label: "Belgrade" },
  { code: "TIA", label: "Tirana" },
  { code: "SKP", label: "Skopje" },
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
  const [flightTripTypes, setFlightTripTypes] = useState<FlightTripType[]>(["round_trip"]);
  const [includeSplitTickets, setIncludeSplitTickets] = useState<boolean>(false);
  const [dealTier, setDealTier] = useState<string>("regular");
  // V9: premium-only discount floor. 40 = "voir tous les bons plans",
  // 50 = "seulement les très bonnes affaires", 60 = "uniquement les
  // perles rares". Free users have a fixed policy and never see this UI.
  const [minDiscount, setMinDiscount] = useState<40 | 50 | 60>(40);
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
  const [cancellingSubscription, setCancellingSubscription] = useState(false);
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
  // Cancellation survey: a single radio reason + an optional free-form
  // textarea. Both stay null/empty until the user actually picks
  // something so we can disable the Confirm button until then.
  const [cancelReason, setCancelReason] = useState<CancellationReason | null>(null);
  const [cancelFeedback, setCancelFeedback] = useState("");
  // Telegram connection state. null = not yet known (avoids flashing the
  // 'connect Telegram' card to users who are actually connected).
  const [telegramConnected, setTelegramConnected] = useState<boolean | null>(null);
  const [telegramLinking, setTelegramLinking] = useState(false);
  const [telegramLinkOpened, setTelegramLinkOpened] = useState(false);
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
        if (prefs.flight_trip_types && prefs.flight_trip_types.length > 0) {
          setFlightTripTypes(prefs.flight_trip_types);
        }
        if (typeof prefs.include_split_tickets === "boolean") {
          setIncludeSplitTickets(prefs.include_split_tickets);
        }
        // V9: load min_discount with strict whitelist. Anything outside
        // {40, 50, 60} (e.g. legacy 20/30 from V7) is coerced to 40 so the
        // UI doesn't show an undefined state.
        if (prefs.min_discount === 50 || prefs.min_discount === 60) {
          setMinDiscount(prefs.min_discount);
        } else {
          setMinDiscount(40);
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

    // Initial Telegram status
    getTelegramStatus(id)
      .then((d) => setTelegramConnected(!!d.connected))
      .catch(() => setTelegramConnected(false));
  }, [router, API_URL]);

  // While the user is in the middle of linking (link opened in another tab),
  // poll Telegram status every 4s so the UI flips to "connected" automatically
  // when /start <token> hits the bot. Stop polling once connected or after the
  // user has opened the link but hasn't completed within ~5 minutes.
  useEffect(() => {
    if (!telegramLinkOpened || telegramConnected || !userId) return;
    let cancelled = false;
    let pollCount = 0;
    const interval = setInterval(async () => {
      pollCount += 1;
      if (pollCount > 75) {
        clearInterval(interval); // give up after ~5 min
        return;
      }
      try {
        const d = await getTelegramStatus(userId);
        if (!cancelled && d.connected) {
          setTelegramConnected(true);
          clearInterval(interval);
        }
      } catch { /* ignore */ }
    }, 4000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [telegramLinkOpened, telegramConnected, userId]);

  async function handleConnectTelegram() {
    if (!userId) return;
    setTelegramLinking(true);
    setError("");
    try {
      const { link } = await generateTelegramLink(userId);
      // Open Telegram in a new tab/app. Once the user clicks Start there,
      // our polling loop will detect telegram_connected=true within ~4s.
      window.open(link, "_blank", "noopener,noreferrer");
      setTelegramLinkOpened(true);
    } catch {
      setError("Impossible de générer le lien Telegram. Réessaie dans un instant.");
    } finally {
      setTelegramLinking(false);
    }
  }

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
        flight_trip_types: flightTripTypes.length > 0 ? flightTripTypes : ["round_trip"],
        // Combos require A/R tracking — silently disable if user dropped round_trip.
        include_split_tickets: includeSplitTickets && flightTripTypes.includes("round_trip"),
        // V9: only premium users get the min_discount filter. Sending
        // null for free users keeps the backend from quietly persisting
        // a value that has no effect.
        min_discount: isPremium ? minDiscount : null,
      });
      setSuccess("Préférences mises à jour avec succès !");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError("Erreur lors de la sauvegarde des préférences");
    } finally {
      setSaving(false);
    }
  }

  async function handleCancelSubscription() {
    if (!cancelReason) return;  // UI disables the button, but be defensive
    setCancellingSubscription(true);
    setError("");
    try {
      const r = await cancelSubscription({
        reason: cancelReason,
        feedback: cancelFeedback.trim() || undefined,
      });
      if (r.had_subscription) {
        setSuccess("Abonnement annulé. Vous gardez Premium jusqu'à la fin de la période en cours.");
      } else {
        setSuccess("Aucun abonnement actif à annuler.");
      }
      setCancelConfirmOpen(false);
      setCancelReason(null);
      setCancelFeedback("");
      setTimeout(() => setSuccess(""), 6000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur d'annulation");
    } finally {
      setCancellingSubscription(false);
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
            <Wordmark />
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/home" className="text-gray-400 text-sm hover:text-gray-600">
              Accueil
            </Link>
            <Link href="/planificateur" className="text-gray-400 text-sm hover:text-gray-600">
              Planificateur
            </Link>
          </div>
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

        {/* ── Telegram connection (visible only when NOT connected) ── */}
        {/*
          Stays hidden while telegramConnected === null (initial fetch in
          flight) so connected users never see a flash of this card.
          Once telegramLinkOpened is true and the user finishes /start in
          Telegram, our polling effect flips telegramConnected to true and
          this block disappears.
        */}
        {telegramConnected === false && (
          <div className="mb-10 p-5 bg-[#0088cc]/5 border-2 border-[#0088cc]/30 rounded-2xl">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#0088cc] text-white flex items-center justify-center text-xl shrink-0">
                ✈️
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-[#082B78] mb-1">
                  Connectez Telegram pour recevoir vos alertes
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                  {telegramLinkOpened
                    ? "Telegram s'est ouvert dans un nouvel onglet. Cliquez sur \"Start\" dans la conversation avec @Globegenius_bot pour finaliser. Cette page se mettra à jour automatiquement."
                    : "Vos préférences sont prêtes mais aucune alerte ne vous est envoyée tant que Telegram n'est pas relié à votre compte."}
                </p>
                {!telegramLinkOpened ? (
                  <button
                    onClick={handleConnectTelegram}
                    disabled={telegramLinking}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0088cc] hover:bg-[#006daa] text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
                  >
                    {telegramLinking ? "Génération du lien…" : "🔗 Connecter Telegram"}
                  </button>
                ) : (
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="inline-flex items-center gap-2 text-sm text-gray-500">
                      <span className="inline-block w-2 h-2 rounded-full bg-[#0088cc] animate-pulse" />
                      En attente de la confirmation Telegram…
                    </span>
                    <button
                      onClick={handleConnectTelegram}
                      disabled={telegramLinking}
                      className="text-xs text-gray-500 underline hover:text-[#0088cc] transition-colors"
                    >
                      Renvoyer le lien
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Telegram connected confirmation (transient, shows once after linking) ── */}
        {telegramConnected === true && telegramLinkOpened && (
          <div className="mb-10 p-4 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
            ✅ Telegram connecté avec succès. Vous recevrez vos alertes au prochain cycle.
          </div>
        )}

        {/* ── Email ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Adresse email</h2>
          <p className="text-gray-400 text-sm mb-4">Votre email de connexion</p>

          {!showEmailForm ? (
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
              <span className="text-[var(--color-ink)]">{email}</span>
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

        {/* ── Types de vols ── */}
        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-1">Types de vols</h2>
          <p className="text-gray-400 text-sm mb-6">
            Choisissez les types d&apos;alertes que vous souhaitez recevoir sur Telegram.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { id: "round_trip" as FlightTripType, label: "Aller-retour", desc: "Vols A/R en promo (par défaut)", icon: "🔄" },
              { id: "one_way" as FlightTripType, label: "Aller simple", desc: "Aller seul ou retour seul en promo", icon: "➡️" },
            ].map((tt) => {
              const selected = flightTripTypes.includes(tt.id);
              return (
                <button
                  key={tt.id}
                  type="button"
                  onClick={() =>
                    setFlightTripTypes((prev) =>
                      selected
                        ? (prev.length > 1 ? prev.filter((t) => t !== tt.id) : prev)
                        : [...prev, tt.id]
                    )
                  }
                  className="text-left p-4 rounded-xl border-2 transition-all relative"
                  style={{
                    borderColor: selected ? "#06b6d4" : "#e5e7eb",
                    background: selected ? "#ecfeff" : "white",
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span>{tt.icon}</span>
                    <span className="font-semibold text-sm">{tt.label}</span>
                  </div>
                  <div className="text-xs text-gray-500">{tt.desc}</div>
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

          {/* Sub-option of 'Aller-retour' — combos malins (2x one-way) */}
          {flightTripTypes.includes("round_trip") && (
            <div className="mt-3 ml-4 pl-4 border-l-2 border-cyan-100">
              <label className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={includeSplitTickets}
                  onChange={(e) => setIncludeSplitTickets(e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-cyan-500 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-[#082B78] group-hover:text-cyan-700 transition-colors">
                    💡 Inclure les combos malins (2 billets)
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Recevez aussi les A/R reconstitués avec 2 aller simples séparés quand c&apos;est moins cher.
                    <span className="block mt-0.5 text-gray-400">
                      ⚠️ Bagages et annulation gérés séparément pour chaque billet.
                    </span>
                  </div>
                </div>
              </label>
            </div>
          )}

          <p className="text-xs text-gray-400 mt-2">
            Au moins un type doit rester sélectionné.
          </p>
        </div>

        {/* ── V9 Niveau de promo (Premium only) ── */}
        {isPremium && (
          <div className="mb-12">
            <h2 className="text-xl font-semibold mb-1">Niveau de promo</h2>
            <p className="text-gray-400 text-sm mb-6">
              À partir de quel niveau de réduction souhaitez-vous être alerté&nbsp;? Plus vous montez, moins vous recevez d&apos;alertes — mais celles que vous recevez sont exceptionnelles. Dans tous les cas, on plafonne à 3 alertes par jour pour ne pas saturer votre Telegram (les long-courriers ne comptent pas dans ce plafond).
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { value: 40 as const, label: "À partir de -40%", desc: "~2-3 alertes/jour. Tous les bons plans détectés.", icon: "📊" },
                { value: 50 as const, label: "À partir de -50%", desc: "~1-2 alertes/jour. Sélectif, on garde les très bonnes affaires.", icon: "🔥" },
                { value: 60 as const, label: "À partir de -60%", desc: "0-1 alerte/jour. Que les vraies pépites (erreurs de prix).", icon: "💎" },
              ].map((opt) => {
                const selected = minDiscount === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMinDiscount(opt.value)}
                    className="text-left p-4 rounded-xl border-2 transition-all relative"
                    style={{
                      borderColor: selected ? "#06b6d4" : "#e5e7eb",
                      background: selected ? "#ecfeff" : "white",
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span>{opt.icon}</span>
                      <span className="font-semibold text-sm">{opt.label}</span>
                    </div>
                    <div className="text-xs text-gray-500">{opt.desc}</div>
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
        )}

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

          {isPremium && (
            <div className="mb-8 p-4 border border-[var(--color-sand)] rounded-xl bg-white">
              <h3 className="font-semibold text-[var(--color-ink)] mb-1">Abonnement Premium</h3>
              <p className="text-sm text-gray-500 mb-3">
                Vous pouvez annuler à tout moment. Vous gardez l&apos;accès Premium jusqu&apos;à la fin de la
                période payée. Aucun nouveau prélèvement.
              </p>
              {!cancelConfirmOpen ? (
                <button
                  type="button"
                  onClick={() => setCancelConfirmOpen(true)}
                  className="text-sm text-[var(--color-coral)] hover:underline"
                >
                  Annuler mon abonnement
                </button>
              ) : (
                // Mini-survey before confirmation. We ask one mandatory
                // reason + an optional free-form note. The actual
                // cancellation only fires once a reason is selected, but
                // "Préfère ne pas répondre" is one of the valid answers
                // so users in a hurry can still leave quickly.
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-semibold text-[var(--color-ink)] mb-1">
                      Avant de partir — pourquoi annulez-vous&nbsp;?
                    </p>
                    <p className="text-xs text-gray-500 mb-3">
                      Vos réponses nous aident à améliorer le produit. C&apos;est anonyme.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {([
                        { v: "too_expensive", label: "💸 Trop cher" },
                        { v: "too_few_alerts", label: "🔇 Pas assez d'alertes pertinentes" },
                        { v: "too_many_alerts", label: "🔊 Trop d'alertes" },
                        { v: "travelling_less", label: "🛏️ Je voyage moins ces temps-ci" },
                        { v: "found_better", label: "🔁 J'ai trouvé un meilleur outil" },
                        { v: "bugs", label: "🐞 L'app ou le bot a des bugs" },
                        { v: "other", label: "✏️ Autre raison" },
                        { v: "no_answer", label: "🙊 Je préfère ne pas répondre" },
                      ] as { v: CancellationReason; label: string }[]).map((opt) => {
                        const selected = cancelReason === opt.v;
                        return (
                          <button
                            key={opt.v}
                            type="button"
                            onClick={() => setCancelReason(opt.v)}
                            className={
                              "text-left text-sm px-3 py-2 rounded-lg border-2 transition-all " +
                              (selected
                                ? "border-[var(--color-coral)] bg-[var(--color-coral-50)] text-[var(--color-ink)] font-medium"
                                : "border-gray-200 bg-white text-gray-700 hover:border-[var(--color-coral)]/40")
                            }
                          >
                            {opt.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="cancel-feedback"
                      className="block text-sm font-medium text-[var(--color-ink)] mb-1"
                    >
                      Une chose qui aurait pu vous faire rester&nbsp;?
                      <span className="text-gray-400 font-normal"> (optionnel)</span>
                    </label>
                    <textarea
                      id="cancel-feedback"
                      value={cancelFeedback}
                      onChange={(e) => setCancelFeedback(e.target.value.slice(0, 500))}
                      maxLength={500}
                      rows={3}
                      placeholder="Ex : un seuil -45%, des départs depuis Lyon, prix mensuel…"
                      className="w-full text-sm bg-gray-50 rounded-lg px-3 py-2 border border-gray-200 focus:border-[var(--color-coral)] focus:ring-2 focus:ring-[var(--color-coral)]/20 outline-none resize-none"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      {cancelFeedback.length}/500
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-2 sm:items-center pt-2 border-t border-gray-100">
                    <button
                      type="button"
                      onClick={handleCancelSubscription}
                      disabled={cancellingSubscription || !cancelReason}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition-colors"
                    >
                      {cancellingSubscription ? "Annulation…" : "Confirmer l'annulation"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setCancelConfirmOpen(false);
                        setCancelReason(null);
                        setCancelFeedback("");
                      }}
                      className="px-4 py-2 text-sm text-gray-600 hover:text-[var(--color-ink)] font-medium"
                    >
                      Garder l&apos;abonnement
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {isPremium ? (
            // Premium users: nudge them to cancel their subscription first
            // so they can keep using the app until end-of-period before
            // deleting. The delete button itself stays available below as
            // a safety net (it also cancels Stripe), but the friendlier
            // path is "annule l'abonnement" → wait → delete when free.
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 text-sm text-amber-900">
              <strong>Pour supprimer votre compte&nbsp;:</strong> annulez d'abord votre abonnement
              ci-dessus. Vous gardez l'accès Premium jusqu'à la fin de la période payée, puis vous
              passerez en gratuit et pourrez supprimer votre compte.
              <br />
              <span className="text-xs text-amber-700 mt-1 block">
                Si vous supprimez votre compte maintenant, l'abonnement Stripe sera également annulé
                automatiquement (pas de remboursement — pour un remboursement, contactez-nous par email).
              </span>
            </div>
          ) : null}

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
                {isPremium && (
                  <span className="block mt-2 text-red-800 font-semibold">
                    ⚠️ Votre abonnement Stripe sera également annulé. Aucun remboursement automatique.
                  </span>
                )}
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
