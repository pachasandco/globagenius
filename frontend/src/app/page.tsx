import type { Metadata } from "next";
import Link from "next/link";
import RedirectIfLoggedIn from "./_components/RedirectIfLoggedIn";
import { LandingNotificationHero, LandingNotificationStackMobile } from "./_components/LandingNotificationHero";
import { Wordmark } from "./_components/Wordmark";
import { getBetaCount } from "@/lib/api";

export const metadata: Metadata = {
  title: "GlobeGenius — Les bons plans vols vérifiés avant qu’ils disparaissent",
  description:
    "Long-courriers depuis Paris, vols européens depuis 10 aéroports français. GlobeGenius détecte les baisses anormales, vérifie les prix et vous alerte sur Telegram.",
  alternates: { canonical: "https://globegenius.app" },
  openGraph: {
    title: "GlobeGenius — Alertes vols vérifiées",
    description:
      "Les meilleurs prix vols détectés, vérifiés et envoyés sur Telegram avant qu’ils disparaissent.",
    url: "https://globegenius.app",
    type: "website",
  },
};

const AIRPORTS = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Nantes", "Nice", "Beauvais", "Bâle-Mulhouse"];

const EXAMPLE_DEALS = [
  { route: "Paris → Tokyo", price: "449 €", baseline: "720 €", discount: "−38%", tag: "Long-courrier" },
  { route: "Paris → Phuket", price: "494 €", baseline: "835 €", discount: "−41%", tag: "Long-courrier" },
  { route: "Toulouse → Lisbonne", price: "64 €", baseline: "178 €", discount: "−64%", tag: "Europe" },
];

const FAQS = [
  {
    q: "GlobeGenius vend-il les billets ?",
    a: "Non. GlobeGenius détecte et vérifie les opportunités, puis vous redirige vers le site de réservation. Vous restez libre de réserver ou non.",
  },
  {
    q: "Pourquoi Telegram ?",
    a: "Parce que certains tarifs ne restent disponibles que quelques heures. Telegram permet de recevoir l’alerte immédiatement, avec le prix, les dates et le lien de réservation.",
  },
  {
    q: "Le service fonctionne-t-il hors de Paris ?",
    a: "Oui. GlobeGenius surveille 10 aéroports français. Paris fournit davantage de long-courriers, tandis que les aéroports régionaux offrent surtout des opportunités Europe, Méditerranée et quelques pépites long-courrier.",
  },
  {
    q: "Comment un deal est-il vérifié ?",
    a: "Le tarif détecté est comparé à son prix habituel, puis contrôlé à nouveau avant l’envoi. Les offres qui ne sont plus disponibles sont écartées.",
  },
];

function SectionTitle({ eyebrow, title, copy }: { eyebrow: string; title: string; copy?: string }) {
  return (
    <div className="mx-auto mb-10 max-w-2xl text-center">
      <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-[var(--color-coral)]">{eyebrow}</p>
      <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl leading-tight text-[var(--color-ink)] sm:text-4xl">{title}</h2>
      {copy && <p className="mt-4 text-sm leading-7 text-slate-500 sm:text-base">{copy}</p>}
    </div>
  );
}

export default async function Landing() {
  const betaCount = await getBetaCount().catch(() => ({ founders_count: 0, max_founders: 100 }));
  const remaining = Math.max(betaCount.max_founders - betaCount.founders_count, 0);

  return (
    <div className="min-h-screen bg-[#FFF9F2] text-[var(--color-ink)]">
      <RedirectIfLoggedIn />

      <nav className="sticky top-0 z-50 border-b border-[#EADFD2] bg-[#FFF9F2]/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>
          <div className="hidden items-center gap-7 text-sm text-slate-600 md:flex">
            <a href="#preuve" className="hover:text-[var(--color-coral)]">Deals récents</a>
            <a href="#fonctionnement" className="hover:text-[var(--color-coral)]">Fonctionnement</a>
            <a href="#couverture" className="hover:text-[var(--color-coral)]">Aéroports</a>
            <a href="#faq" className="hover:text-[var(--color-coral)]">FAQ</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden text-sm font-medium text-slate-600 sm:inline">Connexion</Link>
            <Link href="/signup" className="rounded-xl bg-[var(--color-coral)] px-4 py-2.5 text-sm font-bold text-white shadow-[0_8px_24px_rgba(255,107,71,0.22)] hover:bg-[var(--color-coral-hover)]">
              Activer mes alertes
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <section className="relative overflow-hidden bg-[#082B78]">
          <LandingNotificationHero />
          <div className="relative z-10 mx-auto grid min-h-[650px] max-w-7xl items-center px-5 py-20 sm:px-8 lg:grid-cols-[1.08fr_.92fr]">
            <div className="max-w-2xl">
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold text-white/85 backdrop-blur">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Surveillance active depuis 10 aéroports français
              </div>
              <h1 className="font-[family-name:var(--font-dm-serif)] text-5xl leading-[1.03] text-white sm:text-6xl lg:text-7xl">
                Les bons plans vols,
                <span className="block text-[#FF8265]">avant qu’ils disparaissent.</span>
              </h1>
              <p className="mt-7 max-w-xl text-lg leading-8 text-white/72">
                Long-courriers depuis Paris, vols européens depuis les principaux aéroports français. GlobeGenius détecte les baisses anormales, vérifie les prix et vous alerte immédiatement sur Telegram.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link href="/signup" className="rounded-xl bg-[#FF6B47] px-7 py-4 text-center text-base font-bold text-white shadow-[0_12px_32px_rgba(255,107,71,.35)] hover:bg-[#E95D39]">
                  Recevoir les prochains deals
                </Link>
                <a href="#fonctionnement" className="rounded-xl border border-white/20 bg-white/8 px-7 py-4 text-center text-base font-semibold text-white hover:bg-white/12">
                  Voir comment ça marche
                </a>
              </div>
              <div className="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
                <span>✓ Aucune recherche manuelle</span>
                <span>✓ Prix re-vérifiés</span>
                <span>✓ Alertes personnalisées</span>
              </div>
            </div>
          </div>
        </section>
        <LandingNotificationStackMobile />

        <section className="border-b border-[#EADFD2] bg-white">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-[#EADFD2] md:grid-cols-4">
            {[
              ["10", "aéroports couverts"],
              ["20 min", "mise à jour sur Paris"],
              ["< 5 min", "entre détection et alerte"],
              ["24/7", "surveillance automatisée"],
            ].map(([value, label]) => (
              <div key={label} className="bg-white px-5 py-7 text-center">
                <div className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#082B78]">{value}</div>
                <div className="mt-1 text-xs uppercase tracking-wide text-slate-400">{label}</div>
              </div>
            ))}
          </div>
        </section>

        <section id="preuve" className="px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Preuves, pas promesses" title="Des deals réellement détectés" copy="Chaque alerte présente le prix observé, le prix habituel estimé, les dates et le lien de réservation. Les exemples ci-dessous illustrent les types d’opportunités recherchées par GlobeGenius." />
          <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
            {EXAMPLE_DEALS.map((deal) => (
              <article key={deal.route} className="rounded-3xl border border-[#EADFD2] bg-white p-6 shadow-[0_18px_50px_rgba(8,43,120,.06)]">
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-[#EEF3FF] px-3 py-1 text-xs font-bold text-[#082B78]">{deal.tag}</span>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">Vérifié</span>
                </div>
                <h3 className="mt-8 text-xl font-bold text-[#082B78]">{deal.route}</h3>
                <div className="mt-5 flex items-end gap-3">
                  <span className="font-[family-name:var(--font-dm-serif)] text-4xl text-[var(--color-coral)]">{deal.price}</span>
                  <span className="pb-1 text-sm text-slate-300 line-through">{deal.baseline}</span>
                </div>
                <div className="mt-5 border-t border-[#F0E7DD] pt-4 text-sm text-slate-500">
                  Écart au prix habituel <strong className="float-right text-emerald-700">{deal.discount}</strong>
                </div>
              </article>
            ))}
          </div>
          <p className="mx-auto mt-6 max-w-2xl text-center text-xs leading-5 text-slate-400">Les tarifs évoluent en permanence et peuvent expirer rapidement. GlobeGenius ne vend pas les billets et ne garantit pas leur disponibilité au moment de la réservation.</p>
        </section>

        <section id="fonctionnement" className="bg-white px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Le produit" title="Vous ne cherchez plus. GlobeGenius surveille." />
          <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
            {[
              ["01", "Choisissez vos départs", "Sélectionnez Paris, votre aéroport régional ou plusieurs aéroports selon votre mobilité."],
              ["02", "Les prix sont analysés", "Chaque tarif est comparé à son historique réel selon la route, la période et la durée du séjour."],
              ["03", "Recevez l’alerte", "Le prix est contrôlé une dernière fois puis envoyé sur Telegram avec les dates et le lien direct."],
            ].map(([num, title, copy]) => (
              <div key={num} className="rounded-3xl border border-[#EADFD2] bg-[#FFF9F2] p-7">
                <div className="font-[family-name:var(--font-dm-serif)] text-5xl text-[#FF6B47]/25">{num}</div>
                <h3 className="mt-7 text-xl font-bold text-[#082B78]">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-500">{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="couverture" className="px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Couverture équilibrée" title="Paris pour le volume. La province pour les opportunités." copy="Le service ne promet pas le même nombre de deals partout. Paris concentre davantage de long-courriers. Les aéroports régionaux apportent surtout des vols européens, méditerranéens et quelques offres exceptionnelles." />
          <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-3">
            {[
              ["Paris · Long-courrier", "Tokyo, Bangkok, New York, Montréal, Miami, Phuket et autres destinations mondiales.", "Moteur de désir"],
              ["Paris · Europe", "Une fréquence plus régulière pour Lisbonne, Rome, Athènes, Marrakech, Istanbul et les capitales européennes.", "Moteur de régularité"],
              ["Aéroports régionaux", "Lyon, Marseille, Toulouse, Bordeaux, Nantes, Nice, Beauvais et Bâle-Mulhouse.", "Avantage de couverture"],
            ].map(([title, copy, badge]) => (
              <div key={title} className="rounded-3xl bg-[#082B78] p-7 text-white">
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-[#FF9A82]">{badge}</span>
                <h3 className="mt-5 font-[family-name:var(--font-dm-serif)] text-2xl">{title}</h3>
                <p className="mt-4 text-sm leading-7 text-white/65">{copy}</p>
              </div>
            ))}
          </div>
          <div className="mx-auto mt-8 flex max-w-5xl flex-wrap justify-center gap-2">
            {AIRPORTS.map((airport) => <span key={airport} className="rounded-full border border-[#E1D5C7] bg-white px-4 py-2 text-sm font-medium text-slate-600">{airport}</span>)}
          </div>
        </section>

        <section className="bg-[#FFF1EC] px-5 py-20 sm:px-8">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[var(--color-coral)]">Pourquoi Telegram</p>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-4xl leading-tight text-[#082B78]">Une bonne affaire peut disparaître avant votre prochain email.</h2>
              <p className="mt-5 max-w-xl text-base leading-8 text-slate-600">L’alerte apparaît immédiatement sur votre téléphone. Vous pouvez ouvrir le deal, masquer une destination ou suspendre les notifications sans revenir sur le site.</p>
            </div>
            <div className="rounded-[28px] border border-[#D7E7F2] bg-white p-6 shadow-[0_24px_70px_rgba(8,43,120,.10)]">
              <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#229ED9] font-bold text-white">G</div>
                <div><div className="font-bold text-[#082B78]">GlobeGenius</div><div className="text-xs text-slate-400">alerte reçue maintenant</div></div>
              </div>
              <div className="pt-5">
                <div className="text-xs font-bold uppercase tracking-wide text-emerald-700">Deal exceptionnel · Vérifié</div>
                <div className="mt-3 text-xl font-bold text-[#082B78]">Paris → Tokyo</div>
                <div className="mt-4 text-4xl font-bold text-[#FF6B47]">449 € A/R</div>
                <div className="mt-1 text-sm text-slate-400">Prix habituel médian : 720 €</div>
                <button className="mt-6 w-full rounded-xl bg-[#229ED9] py-3 text-sm font-bold text-white">Voir le vol</button>
              </div>
            </div>
          </div>
        </section>

        <section id="faq" className="bg-white px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Questions fréquentes" title="Ce qu’il faut savoir avant de commencer" />
          <div className="mx-auto max-w-3xl divide-y divide-[#EADFD2] border-y border-[#EADFD2]">
            {FAQS.map((faq) => (
              <details key={faq.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold text-[#082B78]">
                  {faq.q}<span className="text-2xl font-light text-[#FF6B47] transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="max-w-2xl pt-4 text-sm leading-7 text-slate-500">{faq.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="bg-[#082B78] px-5 py-20 text-center text-white sm:px-8">
          <div className="mx-auto max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#FF9A82]">Accès fondateur</p>
            <h2 className="mt-5 font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl">Le prochain bon plan ne prévient pas deux fois.</h2>
            <p className="mx-auto mt-5 max-w-xl text-base leading-8 text-white/65">Configurez vos aéroports une fois. GlobeGenius surveille les prix et vous prévient quand une vraie opportunité apparaît.</p>
            <Link href="/signup" className="mt-8 inline-block rounded-xl bg-[#FF6B47] px-8 py-4 text-base font-bold text-white shadow-[0_12px_32px_rgba(255,107,71,.30)] hover:bg-[#E95D39]">
              Activer mes alertes Telegram
            </Link>
            <p className="mt-4 text-xs text-white/40">{remaining > 0 ? `${remaining} places fondateurs encore disponibles` : "Accès fondateur complet — lancement public prochainement"}</p>
          </div>
        </section>
      </main>

      <footer className="border-t border-[#EADFD2] bg-[#FFF9F2] px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-xs text-slate-400 sm:flex-row">
          <div>GlobeGenius © 2026 — Alertes vols vérifiées</div>
          <div className="flex gap-5"><Link href="/mentions-legales">Mentions légales</Link><Link href="/confidentialite">Confidentialité</Link><Link href="/conditions">Conditions</Link></div>
        </div>
      </footer>
    </div>
  );
}
