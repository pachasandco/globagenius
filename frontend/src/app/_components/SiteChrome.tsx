import Link from "next/link";
import type { ReactNode } from "react";
import { Wordmark } from "./Wordmark";

export function PublicHeader({ compact = false }: { compact?: boolean }) {
  return (
    <nav className="site-header sticky top-0 z-50 border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
      <div className={`mx-auto flex items-center justify-between px-5 sm:px-8 ${compact ? "h-16 max-w-6xl" : "h-20 max-w-7xl"}`}>
        <Link href="/" aria-label="Accueil GlobeGenius"><Wordmark size={compact ? "sm" : "md"} /></Link>
        <div className="flex items-center gap-3">
          <Link href="/login" className="hidden text-sm font-medium text-slate-600 transition-colors hover:text-[#0E7490] sm:inline">Connexion</Link>
          <Link href="/signup" className="site-cta-primary rounded-xl px-4 py-2.5 text-sm font-bold">Activer mon radar</Link>
        </div>
      </div>
    </nav>
  );
}

export function SimpleHeader({ backHref = "/", backLabel = "Retour à l’accueil" }: { backHref?: string; backLabel?: string }) {
  return (
    <nav className="site-header border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link href="/" aria-label="Accueil GlobeGenius"><Wordmark size="sm" /></Link>
        <Link href={backHref} className="text-sm font-semibold text-[#0E7490] transition-colors hover:text-[#0A6078]">{backLabel}</Link>
      </div>
    </nav>
  );
}

export function AppHeader() {
  return (
    <header className="site-header sticky top-0 z-50 border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:h-20 sm:px-8">
        <Link href="/home" aria-label="Accueil de votre espace GlobeGenius"><Wordmark size="sm" /></Link>
        <nav aria-label="Navigation de l’espace utilisateur" className="flex items-center gap-1 rounded-xl border border-[#D9E2E3] bg-white p-1 text-xs font-semibold sm:gap-2 sm:text-sm">
          <Link href="/home" className="rounded-lg px-2.5 py-2 text-slate-600 transition-colors hover:bg-[#E9F5F7] hover:text-[#0E7490] sm:px-4">Accueil</Link>
          <Link href="/deals" className="rounded-lg px-2.5 py-2 text-slate-600 transition-colors hover:bg-[#E9F5F7] hover:text-[#0E7490] sm:px-4">Deals</Link>
          <Link href="/profile" className="rounded-lg px-2.5 py-2 text-slate-600 transition-colors hover:bg-[#E9F5F7] hover:text-[#0E7490] sm:px-4">Profil</Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-[#D9E2E3] bg-[#FFFCF7] py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 text-center text-xs text-slate-500 sm:flex-row sm:text-left">
        <span>GlobeGenius © 2026 — Alertes vols vérifiées</span>
        <div className="flex flex-wrap justify-center gap-4">
          <Link href="/methodologie" className="hover:text-[#0E7490]">Méthodologie</Link>
          <Link href="/conditions" className="hover:text-[#0E7490]">Conditions</Link>
          <Link href="/confidentialite" className="hover:text-[#0E7490]">Confidentialité</Link>
          <Link href="/mentions-legales" className="hover:text-[#0E7490]">Mentions légales</Link>
        </div>
      </div>
    </footer>
  );
}

export function AppRouteShell({ route, children }: { route: "deals" | "profile"; children: ReactNode }) {
  return (
    <div className={`app-route-shell app-route-${route} min-h-screen bg-[#F7F3EA] text-[#0B2A3F]`}>
      <AppHeader />
      {children}
      <SiteFooter />
    </div>
  );
}

export function EditorialShell({ eyebrow, title, intro, children }: { eyebrow?: string; title: string; intro?: string; children: ReactNode }) {
  return (
    <div className="site-page min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <SimpleHeader />
      <main>
        <section className="site-hero-soft border-b border-white/10 px-5 py-14 text-white sm:px-8 sm:py-20">
          <div className="mx-auto max-w-4xl">
            {eyebrow && <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#7DE0D6]">{eyebrow}</p>}
            <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl leading-tight sm:text-6xl">{title}</h1>
            {intro && <p className="mt-5 max-w-3xl text-base leading-8 text-white/70 sm:text-lg">{intro}</p>}
          </div>
        </section>
        <div className="mx-auto max-w-4xl px-5 py-12 sm:px-8 sm:py-16">
          <article className="site-editorial-card rounded-[32px] border border-[#D9E2E3] bg-white p-6 shadow-[0_18px_55px_rgba(11,42,63,.07)] sm:p-10">{children}</article>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
