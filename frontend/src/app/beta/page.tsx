import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../_components/Wordmark";
import { getBetaCount } from "@/lib/api";

export const metadata: Metadata = {
  title: "Programme Beta Fondateur — GlobeGenius",
  description:
    "100 places fondateurs disponibles. Statut premium gratuit à vie pendant la beta publique. Couverture Europe + Méditerranée + Afrique du Nord, long-courrier été 2026.",
  alternates: { canonical: "https://globegenius.app/beta" },
  openGraph: {
    title: "Programme Beta Fondateur · GlobeGenius",
    description:
      "100 places fondateurs disponibles. Statut premium gratuit à vie.",
    url: "https://globegenius.app/beta",
    type: "website",
  },
};

export default async function BetaPage() {
  const { founders_count, max_founders } = await getBetaCount();
  const remaining = Math.max(max_founders - founders_count, 0);
  const filledPct = Math.min(100, Math.round((founders_count / max_founders) * 100));

  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      {/* ── NAVBAR ── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 h-[80px] bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-lg leading-none">
          <Wordmark />
        </Link>
        <div className="flex items-center gap-6 text-sm">
          <Link href="/" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">
            Accueil
          </Link>
          <Link href="/login" className="text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors font-medium text-sm">
            Connexion
          </Link>
          <Link href="/signup" className="bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
            Rejoindre la beta
          </Link>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-6 sm:px-12 py-12">
        {/* ── HERO ── */}
        <header className="text-center mb-12">
          <span className="inline-block bg-[var(--color-coral)]/15 border border-[var(--color-coral)]/30 text-[var(--color-coral)] px-3 py-1 rounded-full text-xs font-bold mb-6">
            🚧 Beta publique · Lancement officiel été 2026
          </span>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-[var(--color-ink)] leading-tight mb-4">
            Programme Beta Fondateur
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            GlobeGenius est en beta publique depuis mai 2026. Les {max_founders}{" "}
            premiers inscrits gardent un statut premium gratuit à vie en
            échange d&apos;un feedback honnête sur la qualité des alertes.
          </p>
        </header>

        {/* ── COMPTEUR ── */}
        <section className="bg-[var(--color-ink)] rounded-2xl p-8 text-center mb-12">
          <div className="font-[family-name:var(--font-dm-serif)] text-6xl text-white mb-2">
            {founders_count}{" "}
            <span className="text-gray-500 text-3xl font-normal">/ {max_founders}</span>
          </div>
          <div className="text-gray-400 text-sm mb-6">places fondateurs prises</div>
          <div className="bg-white/10 rounded-full h-2 max-w-md mx-auto mb-6 overflow-hidden">
            <div
              className="bg-[var(--color-coral)] h-full rounded-full transition-all"
              style={{ width: `${filledPct}%` }}
              aria-hidden="true"
            />
          </div>
          <Link
            href="/signup"
            className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-3 rounded-xl font-bold text-base transition-colors"
          >
            Rejoindre les {remaining} places restantes
          </Link>
        </section>

        {/* ── CE QUE TU RECOIS ── */}
        <section className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl font-bold text-[var(--color-ink)] mb-6">
            Ce que tu reçois
          </h2>
          <ul className="space-y-3 text-[var(--color-ink)]/85">
            <li>
              ✓ <strong>Alertes premium</strong> (jusqu&apos;à 5 par jour, étalées dans le temps — jamais de réveil avec 4 notifs d&apos;un coup)
            </li>
            <li>
              ✓ <strong>Accès aux destinations long-courrier</strong> dès leur déploiement (été 2026)
            </li>
            <li>
              ✓ <strong>Détection stopover</strong> (visite gratuite d&apos;une 2e ville pendant ton vol) dès qu&apos;elle est livrée
            </li>
            <li>
              ✓ <strong>Préférences personnalisées</strong> : aéroports, seuil de réduction, destinations bloquées
            </li>
            <li>
              ✓ <strong>Statut « Premium à vie »</strong> — même quand on lancera officiellement à 4,99€/mois
            </li>
          </ul>
        </section>

        {/* ── CE QU'ON ATTEND ── */}
        <section className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl font-bold text-[var(--color-ink)] mb-6">
            Ce qu&apos;on attend de toi
          </h2>
          <p className="text-[var(--color-ink)]/85 mb-4">
            C&apos;est une beta, pas un produit fini. On attend :
          </p>
          <ul className="space-y-3 text-[var(--color-ink)]/85">
            <li>
              — Que tu cliques sur <strong>👍 / 👎</strong> sur les alertes que tu reçois (ça nous aide à affiner les seuils)
            </li>
            <li>
              — Que tu nous signales les faux deals via le bouton <strong>⏱️ « Trop tard »</strong>
            </li>
            <li>
              — Que tu sois patient pendant qu&apos;on étend la couverture sur l&apos;Asie et les Amériques (été 2026)
            </li>
          </ul>
          <p className="text-sm text-gray-500 mt-6">
            Aucune obligation financière. Aucun engagement de durée. Désinscription en un clic depuis Telegram.
          </p>
        </section>

        {/* ── ROADMAP ── */}
        <section className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl font-bold text-[var(--color-ink)] mb-6">
            La roadmap
          </h2>
          <div className="space-y-6">
            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">Mai 2026 (actuel)</div>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>✓ 162 destinations Europe &amp; Méditerranée matures</li>
                <li>✓ Reverification 95% avant envoi</li>
                <li>✓ Pool 5 alertes/jour, étalées dans le temps</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">Été 2026</div>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>○ Couverture long-courrier (Asie, Amériques, Afrique sub-saharienne)</li>
                <li>○ Détection stopover (visite 24-72h d&apos;une 2e ville)</li>
                <li>○ Lancement officiel à 4,99€/mois (les fondateurs restent gratuits à vie)</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">Automne 2026</div>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>○ Extension Belgique francophone, Suisse romande, Luxembourg</li>
                <li>○ App PWA installable</li>
              </ul>
            </div>
          </div>
        </section>

        {/* ── FOUNDER NOTE ── */}
        <section className="mb-12 bg-white rounded-2xl p-8 border border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl font-bold text-[var(--color-ink)] mb-4">
            Mot du fondateur
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Salut, je suis Moussa, dev solo basé en région parisienne.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            J&apos;ai construit GlobeGenius parce qu&apos;aucun service d&apos;alertes
            vols ne couvre vraiment la France hors-Paris. Les concurrents
            anglo-saxons (Going, Jack&apos;s Flight Club) ignorent Lyon,
            Marseille, Toulouse, Bordeaux, Nantes.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed">
            Aujourd&apos;hui en beta, {founders_count} utilisateurs reçoivent
            quotidiennement des alertes pour des vols à -40% à -80% sur
            l&apos;Europe et la Méditerranée. Si tu veux faire partie des{" "}
            {max_founders} premiers fondateurs, c&apos;est ici :
          </p>
          <Link
            href="/signup"
            className="inline-block mt-6 bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-6 py-3 rounded-xl font-bold text-sm transition-colors"
          >
            Rejoindre la beta — gratuit à vie
          </Link>
        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="py-6 px-6 sm:px-12 bg-[#050e1a] flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-gray-500">
        <span>© 2026 Globe Genius</span>
        <div className="flex gap-4">
          <Link href="/conditions" className="hover:text-gray-300 transition-colors">Conditions</Link>
          <Link href="/confidentialite" className="hover:text-gray-300 transition-colors">Confidentialité</Link>
          <Link href="/mentions-legales" className="hover:text-gray-300 transition-colors">Mentions légales</Link>
          <a href="mailto:contact@globegenius.app" className="hover:text-gray-300 transition-colors">Contact</a>
        </div>
      </footer>
    </div>
  );
}
