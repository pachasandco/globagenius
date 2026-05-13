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

    if (password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }
    if (password !== confirm) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }
    if (!token) {
      setError("Lien invalide. Demandez un nouveau lien depuis la page de connexion.");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
      // Auto-redirect after a short pause so the user reads the confirmation
      setTimeout(() => router.push("/login"), 2200);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      setError(
        msg.toLowerCase().includes("invalide") || msg.toLowerCase().includes("expir")
          ? "Lien invalide ou expiré. Demandez un nouveau lien."
          : "Erreur lors de la réinitialisation. Réessayez dans un instant."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-start sm:items-center justify-center px-4 py-8 sm:py-0">
      <div className="w-full max-w-sm text-center">
        <Link
          href="/"
          className="font-[family-name:var(--font-dm-serif)] text-xl leading-none block text-center mb-10"
        >
          <Wordmark />
        </Link>

        <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm text-left">
          <div className="text-3xl mb-4 text-center">🔒</div>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-3 text-center">
            Nouveau mot de passe
          </h1>

          {success ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <p className="text-sm text-green-700">
                ✅ Mot de passe modifié avec succès. Redirection vers la page
                de connexion…
              </p>
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed text-center">
                Choisissez un nouveau mot de passe pour votre compte. Au moins
                6 caractères.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Nouveau mot de passe"
                  required
                  minLength={6}
                  autoFocus
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#FF6B47] text-sm"
                />
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Confirmez le mot de passe"
                  required
                  minLength={6}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#FF6B47] text-sm"
                />

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {submitting ? "Modification…" : "Réinitialiser"}
                </button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  href="/reset-password"
                  className="text-sm text-gray-500 hover:text-[#FF6B47] transition-colors"
                >
                  Demander un nouveau lien →
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
