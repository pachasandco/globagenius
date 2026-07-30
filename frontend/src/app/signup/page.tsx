"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signup, getBetaCount } from "@/lib/api";
import { suggestEmailCorrection } from "@/lib/email-suggestion";
import { Wordmark } from "../_components/Wordmark";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  // CNIL : case décochée par défaut, consentement explicite uniquement.
  const [marketingConsent, setMarketingConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  // Beta cohort cap: when 100 founders are reached, the signup form is
  // replaced by a "closed" message. We fetch the live count once on mount;
  // null = loading, true/false = decision. A failed fetch defaults to open
  // so a transient API hiccup doesn't lock genuine signups out.
  const [cohortFull, setCohortFull] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    getBetaCount()
      .then((c) => setCohortFull(c.founders_count >= c.max_founders))
      .catch(() => setCohortFull(false));
  }, []);

  const emailSuggestion = useMemo(() => suggestEmailCorrection(email), [email]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caracteres");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas");
      return;
    }

    setLoading(true);
    try {
      const res = await signup(email, password, marketingConsent);
      localStorage.setItem("gg_user_id", res.user_id);
      localStorage.setItem("gg_email", res.email);
      localStorage.setItem("gg_token", res.token);
      router.push("/onboarding");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur lors de l'inscription";
      // Backend returns 403 once the 100-founder cap is reached. The
      // initial mount check might have raced, so flip to the closed
      // state on the spot rather than just showing a red error.
      if (/inscriptions/i.test(msg) && /fermées|fermees|100 places/i.test(msg)) {
        setCohortFull(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-start sm:items-center justify-center px-4 md:px-5 py-8 sm:py-0">
      <div className="w-full max-w-sm">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl leading-none block text-center mb-10">
          <Wordmark />
        </Link>

        {cohortFull === true ? (
          <div className="text-center">
            <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-3">
              Inscriptions fermées
            </h1>
            <p className="text-gray-500 text-sm leading-relaxed mb-6">
              Les <strong>100 places fondateurs</strong> de l&apos;Active Beta sont
              prises. Merci à toutes et tous pour l&apos;engouement 🙏
            </p>
            <p className="text-gray-500 text-sm leading-relaxed mb-8">
              Le lancement public arrive bientôt. En attendant, tu peux suivre
              les coulisses sur la <Link href="/" className="text-[#FF6B47] hover:underline">page d&apos;accueil</Link>{" "}
              ou nous écrire à{" "}
              <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">
                contact@globegenius.app
              </a>.
            </p>
            <Link
              href="/"
              className="inline-block bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-6 py-3 rounded-xl transition-colors"
            >
              ← Retour à l&apos;accueil
            </Link>
            <p className="text-center text-sm text-gray-400 mt-8">
              Déjà membre ?{" "}
              <Link href="/login" className="text-cyan-600 font-medium hover:underline">
                Se connecter
              </Link>
            </p>
          </div>
        ) : (
        <>
        <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl text-center mb-2">
          Creer un compte
        </h1>
        <p className="text-gray-400 text-sm text-center mb-8">
          Recevez les meilleurs deals voyage directement sur Telegram.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="votre@email.com"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm transition-colors"
            />
            {emailSuggestion && (
              <p className="text-xs text-gray-500 mt-1.5">
                Vouliez-vous dire{" "}
                <button
                  type="button"
                  onClick={() => setEmail(emailSuggestion)}
                  className="text-[#FF6B47] font-semibold hover:underline"
                >
                  {emailSuggestion}
                </button>
                {" "}?
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="6 caracteres minimum"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirmer le mot de passe</label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Retapez votre mot de passe"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none text-sm transition-colors"
            />
          </div>

          <label className="flex items-start gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={marketingConsent}
              onChange={(e) => setMarketingConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[#FF6B47] focus:ring-[#FF6B47]"
            />
            <span className="text-xs text-gray-500 leading-relaxed">
              J&apos;accepte de recevoir par email les récapitulatifs de deals,
              les nouveautés et les offres de GlobeGenius. (facultatif —
              modifiable à tout moment depuis mon profil)
            </span>
          </label>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creation..." : "S'inscrire"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-6">
          Deja un compte ?{" "}
          <Link href="/login" className="text-cyan-600 font-medium hover:underline">
            Se connecter
          </Link>
        </p>
        </>
        )}
      </div>
    </div>
  );
}
