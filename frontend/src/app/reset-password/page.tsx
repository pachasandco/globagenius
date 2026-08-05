"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/api";
import { Wordmark } from "../_components/Wordmark";

export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (submitting || !email.trim()) return;
    setSubmitting(true);
    try {
      await forgotPassword(email.trim());
    } catch {
      // Anti-enumeration: always show the same confirmation state.
    }
    setSubmitted(true);
    setSubmitting(false);
  }

  return (
    <div className="site-auth-page flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
      <div className="w-full max-w-md">
        <div className="mb-9 text-center"><Link href="/" aria-label="Accueil GlobeGenius"><Wordmark size="md" /></Link></div>
        <div className="site-form-card rounded-[30px] border border-[#D9E2E3] p-6 sm:p-9">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Sécurité du compte</p>
          <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl text-[#0B2A3F]">Mot de passe oublié</h1>

          {!submitted ? (
            <>
              <p className="mt-4 text-sm leading-7 text-slate-500">
                Entrez votre adresse email. Lorsqu’elle correspond à un compte GlobeGenius, un lien valable une heure est envoyé.
              </p>
              <form onSubmit={handleSubmit} className="mt-7 space-y-5">
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-[#0B2A3F]">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="votre@email.com" required autoFocus className="w-full rounded-xl border px-4 py-3.5 text-sm outline-none" />
                </div>
                <button type="submit" disabled={submitting || !email.trim()} className="site-cta-primary w-full rounded-xl py-3.5 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-50">
                  {submitting ? "Envoi en cours…" : "Envoyer le lien"}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="gg-status-success mt-6 rounded-2xl border p-4 text-sm leading-6">
                Si un compte existe avec <strong>{email}</strong>, le lien arrivera dans quelques minutes. Pensez à vérifier vos spams.
              </div>
              <Link href="/login" className="site-cta-primary mt-6 block w-full rounded-xl py-3.5 text-center text-sm font-bold">Retour à la connexion</Link>
            </>
          )}

          {!submitted && <div className="mt-6 border-t border-[#D9E2E3] pt-6 text-center"><Link href="/login" className="text-sm font-semibold text-[#0E7490] hover:text-[#0A6078]">← Retour à la connexion</Link></div>}
        </div>
      </div>
    </div>
  );
}
