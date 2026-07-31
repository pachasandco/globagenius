"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { Wordmark } from "../_components/Wordmark";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await login(email, password);
      localStorage.setItem("gg_user_id", res.user_id);
      localStorage.setItem("gg_email", res.email);
      localStorage.setItem("gg_token", res.token);
      router.push("/home");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="site-auth-page min-h-screen lg:grid lg:grid-cols-[0.92fr_1.08fr]">
      <section className="site-hero-soft hidden min-h-screen flex-col justify-between p-12 text-white lg:flex xl:p-16">
        <Link href="/" aria-label="Accueil GlobeGenius"><Wordmark variant="inverse" size="md" /></Link>
        <div className="max-w-xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#7DE0D6]">Votre radar personnel</p>
          <h1 className="mt-5 font-[family-name:var(--font-dm-serif)] text-5xl leading-[1.05] xl:text-6xl">
            Retrouvez les opportunités détectées depuis votre aéroport.
          </h1>
          <p className="mt-6 max-w-lg text-base leading-8 text-white/68">
            Vos préférences, vos deals et le statut de vos alertes Telegram restent réunis dans un espace simple et cohérent.
          </p>
        </div>
        <div className="flex flex-wrap gap-5 text-xs text-white/55">
          <span>Prix revérifiés</span>
          <span>Alertes Telegram</span>
          <span>10 aéroports français</span>
        </div>
      </section>

      <main className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="w-full max-w-md">
          <div className="mb-9 text-center lg:hidden">
            <Link href="/" aria-label="Accueil GlobeGenius"><Wordmark size="md" /></Link>
          </div>

          <div className="site-form-card rounded-[30px] border border-[#D9E2E3] p-6 sm:p-9">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Espace membre</p>
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl text-[#0B2A3F]">Connexion</h1>
            <p className="mt-3 text-sm leading-6 text-slate-500">Retrouvez vos deals, vos préférences et vos alertes.</p>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-[#0B2A3F]">Email</label>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="votre@email.com"
                  className="w-full rounded-xl border px-4 py-3.5 text-sm outline-none transition-colors"
                />
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="block text-sm font-semibold text-[#0B2A3F]">Mot de passe</label>
                  <Link href="/reset-password" className="text-xs font-semibold text-[#0E7490] transition-colors hover:text-[#0A6078]">Mot de passe oublié ?</Link>
                </div>
                <input
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Votre mot de passe"
                  className="w-full rounded-xl border px-4 py-3.5 text-sm outline-none transition-colors"
                />
              </div>

              {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

              <button type="submit" disabled={loading} className="site-cta-primary w-full rounded-xl py-3.5 font-bold disabled:cursor-not-allowed disabled:opacity-50">
                {loading ? "Connexion…" : "Se connecter"}
              </button>
            </form>

            <div className="mt-6 border-t border-[#D9E2E3] pt-6 text-center text-sm text-slate-500">
              Pas encore de compte ?{" "}
              <Link href="/signup" className="font-bold text-[#0E7490] hover:text-[#0A6078]">Activer mon radar gratuitement</Link>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-slate-400">
            <Link href="/conditions" className="hover:text-[#0E7490]">Conditions</Link>
            <span className="mx-2">·</span>
            <Link href="/confidentialite" className="hover:text-[#0E7490]">Confidentialité</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
