"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { suggestEmailCorrection } from "@/lib/email-suggestion";
import { Wordmark } from "../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const emailSuggestion = useMemo(() => suggestEmailCorrection(email), [email]);

  async function createAccount() {
    const response = await fetch(`${API_URL}/api/auth/signup-public`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || "Erreur lors de l’inscription.");
    }
    document.cookie = "gg_session=1; path=/; SameSite=Lax; max-age=2592000";
    return body as { user_id: string; email: string; token: string };
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    if (password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    setLoading(true);
    try {
      const response = await createAccount();
      localStorage.setItem("gg_user_id", response.user_id);
      localStorage.setItem("gg_email", response.email);
      localStorage.setItem("gg_token", response.token);
      router.push("/onboarding");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur lors de l’inscription.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F3EA] px-4 py-8 sm:flex sm:items-center sm:justify-center sm:py-12">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-9 block text-center font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>

        <div className="rounded-[28px] border border-[#D9E2E3] bg-white p-6 shadow-[0_22px_60px_rgba(11,42,63,.07)] sm:p-8">
          <div className="text-center">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Compte gratuit</p>
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-3xl text-[#0B2A3F]">Configurez vos alertes vols</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">Choisissez vos aéroports, puis connectez Telegram pour recevoir les baisses de prix vérifiées.</p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-[#0B2A3F]">Email</label>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="votre@email.com"
                className="w-full rounded-xl border border-[#D9E2E3] px-4 py-3 text-sm outline-none transition-colors focus:border-[#0E7490] focus:ring-1 focus:ring-[#0E7490]"
              />
              {emailSuggestion && (
                <p className="mt-1.5 text-xs text-slate-500">
                  Vouliez-vous dire{" "}
                  <button type="button" onClick={() => setEmail(emailSuggestion)} className="font-semibold text-[#0E7490] hover:underline">{emailSuggestion}</button> ?
                </p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-[#0B2A3F]">Mot de passe</label>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="6 caractères minimum"
                className="w-full rounded-xl border border-[#D9E2E3] px-4 py-3 text-sm outline-none transition-colors focus:border-[#0E7490] focus:ring-1 focus:ring-[#0E7490]"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-[#0B2A3F]">Confirmer le mot de passe</label>
              <input
                type="password"
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Retapez votre mot de passe"
                className="w-full rounded-xl border border-[#D9E2E3] px-4 py-3 text-sm outline-none transition-colors focus:border-[#0E7490] focus:ring-1 focus:ring-[#0E7490]"
              />
            </div>

            {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>}

            <button type="submit" disabled={loading} className="w-full rounded-xl bg-[#0E7490] py-3.5 font-bold text-white transition-colors hover:bg-[#0A6078] disabled:cursor-not-allowed disabled:opacity-50">
              {loading ? "Création du compte…" : "Créer mon compte gratuit"}
            </button>
          </form>

          <div className="mt-5 rounded-2xl bg-[#E9F5F7] p-4 text-sm leading-6 text-slate-600">
            <strong className="text-[#0B2A3F]">Premium sera proposé à 49 € par an.</strong> Le paiement ouvrira plus tard : aucune carte bancaire et aucun prélèvement ne sont demandés lors de l’inscription.
          </div>

          <p className="mt-5 text-center text-xs leading-5 text-slate-400">
            En créant un compte, vous acceptez les <Link href="/conditions" className="underline hover:text-[#0E7490]">conditions d’utilisation</Link> et la <Link href="/confidentialite" className="underline hover:text-[#0E7490]">politique de confidentialité</Link>.
          </p>
        </div>

        <p className="mt-6 text-center text-sm text-slate-400">Déjà un compte ? <Link href="/login" className="font-medium text-[#0E7490] hover:underline">Se connecter</Link></p>
      </div>
    </div>
  );
}
