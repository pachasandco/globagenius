"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { resetPassword } from "@/lib/api";
import { Wordmark } from "../../_components/Wordmark";

export default function ResetPasswordTokenPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const token = params?.token ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 6) return setError("Le mot de passe doit contenir au moins 6 caractères.");
    if (password !== confirm) return setError("Les deux mots de passe ne correspondent pas.");
    if (!token) return setError("Lien invalide. Demandez un nouveau lien depuis la page de connexion.");

    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2200);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      setError(msg.toLowerCase().includes("invalide") || msg.toLowerCase().includes("expir") ? "Lien invalide ou expiré. Demandez un nouveau lien." : "Erreur lors de la réinitialisation. Réessayez dans un instant.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="site-auth-page flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
      <div className="w-full max-w-md">
        <div className="mb-9 text-center"><Link href="/" aria-label="Accueil GlobeGenius"><Wordmark size="md" /></Link></div>
        <div className="site-form-card rounded-[30px] border border-[#D9E2E3] p-6 sm:p-9">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Sécurité du compte</p>
          <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl text-[#0B2A3F]">Nouveau mot de passe</h1>

          {success ? (
            <div className="gg-status-success mt-6 rounded-2xl border p-4 text-sm leading-6">Mot de passe modifié avec succès. Redirection vers la connexion…</div>
          ) : (
            <>
              <p className="mt-4 text-sm leading-7 text-slate-500">Choisissez un nouveau mot de passe d’au moins 6 caractères.</p>
              <form onSubmit={handleSubmit} className="mt-7 space-y-5">
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-[#0B2A3F]">Nouveau mot de passe</label>
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="6 caractères minimum" required minLength={6} autoFocus className="w-full rounded-xl border px-4 py-3.5 text-sm outline-none" />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-[#0B2A3F]">Confirmation</label>
                  <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Retapez le mot de passe" required minLength={6} className="w-full rounded-xl border px-4 py-3.5 text-sm outline-none" />
                </div>
                {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
                <button type="submit" disabled={submitting} className="site-cta-primary w-full rounded-xl py-3.5 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-50">{submitting ? "Modification…" : "Réinitialiser"}</button>
              </form>
              <div className="mt-6 border-t border-[#D9E2E3] pt-6 text-center"><Link href="/reset-password" className="text-sm font-semibold text-[#0E7490] hover:text-[#0A6078]">Demander un nouveau lien</Link></div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
