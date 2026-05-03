"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";

import { forgotPassword } from "@/lib/api";

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
      // Anti-enumeration: even on error we show the success state.
      // The server already returns 200 in every realistic case.
    }
    setSubmitted(true);
    setSubmitting(false);
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-start sm:items-center justify-center px-4 py-8 sm:py-0">
      <div className="w-full max-w-sm text-center">
        <Link
          href="/"
          className="font-[family-name:var(--font-dm-serif)] text-xl leading-none block text-center mb-10"
        >
          <span className="text-[#1E90FF]">Globe</span><span className="text-[#FF6B47]">Genius</span>
        </Link>

        <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm text-left">
          <div className="text-3xl mb-4 text-center">🔑</div>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-3 text-center">
            Mot de passe oublié
          </h1>

          {!submitted ? (
            <>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed text-center">
                Entrez votre adresse email. Si elle correspond à un compte
                Globe Genius, vous recevrez un lien pour définir un nouveau
                mot de passe (valable 1 heure).
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="votre@email.com"
                  required
                  autoFocus
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#FF6B47] text-sm"
                />
                <button
                  type="submit"
                  disabled={submitting || !email.trim()}
                  className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {submitting ? "Envoi en cours…" : "Envoyer le lien"}
                </button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  href="/login"
                  className="text-sm text-gray-500 hover:text-[#FF6B47] transition-colors"
                >
                  ← Retour à la connexion
                </Link>
              </div>
            </>
          ) : (
            <>
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
                <p className="text-sm text-green-700">
                  ✅ Si un compte existe avec <strong>{email}</strong>, vous
                  recevrez un email avec un lien de réinitialisation dans
                  quelques minutes. Pensez à vérifier vos spams.
                </p>
              </div>
              <Link
                href="/login"
                className="block w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all text-sm text-center"
              >
                Retour à la connexion
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
