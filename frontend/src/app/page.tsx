import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import RedirectIfLoggedIn from "./_components/RedirectIfLoggedIn";
import LandingAnimated, { HeroContent } from "./_components/LandingAnimated";

export const metadata: Metadata = {
  alternates: {
    canonical: "https://globegenius.app",
  },
};

const faqs = [
  { q: "Comment fonctionne Globe Genius ?", a: "On surveille en permanence les prix des vols au départ de 9 aéroports français. Dès qu’on détecte une baisse de prix significative, on vous envoie une alerte sur Telegram avec tous les détails pour réserver." },
  { q: "Quelle est la différence entre Gratuit et Premium ?", a: "En Gratuit, vous recevez jusqu’à 3 alertes complètes par semaine sur les deals à -40% et plus. En Premium, vous accédez à tous les deals sans limite (jusqu’à -70%+), y compris les erreurs de prix des compagnies, avec prix et liens de réservation débloqués." },
  { q: "Comment fonctionne la garantie 30 jours ?", a: "Si Premium ne vous convient pas, contactez-nous dans les 30 jours suivant votre achat et on vous rembourse intégralement, sans question." },
  { q: "Les prix incluent-ils les bagages ?", a: "Les prix affichés sont ceux des compagnies aériennes. Les bagages en soute sont parfois inclus selon la compagnie et le tarif. On le précise dans chaque alerte quand l’information est disponible." },
  { q: "Combien de temps entre la publication du prix et votre alerte ?", a: "Pour les vols Ryanair et Vueling au départ de Paris (CDG/ORY), on scrape les prix directement sur les APIs des compagnies toutes les 20 minutes. Dès qu’une anomalie est détectée, l’alerte Telegram part dans la foulée, généralement moins de 5 minutes après l’apparition du deal. Pour les autres aéroports et destinations, on utilise un agrégateur de vols interrogé toutes les 2 heures." },
  { q: "Pourquoi certains deals disparaissent avant que j’aie pu réserver ?", a: "Les tarifs érronés (« erreurs de prix ») sont des oublis de configuration des compagnies. Dès qu’elles s’en rendent compte, elles corrigent le tarif — parfois en quelques heures. C’est pourquoi les alertes temps réel sont déterminantes : réserver dans l’heure qui suit l’alerte maximise vos chances d’obtenir le prix affiché. Passez commande rapidement et contactez la compagnie si le tarif change avant l’émission." },
];

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map(f => ({
    "@type": "Question",
    name: f.q,
    acceptedAnswer: { "@type": "Answer", text: f.a },
  })),
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      <RedirectIfLoggedIn />

      {/* FAQ JSON-LD — server-rendered, crawler-visible */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />

      {/* ── NAVBAR ── */}
      <nav aria-label="Navigation principale" className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 py-4 bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-lg leading-none">
          Globe<span className="text-[var(--color-coral)]">Genius</span>
        </Link>
        <div className="flex items-center gap-6 text-sm">
          <a href="#comment-ca-marche" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">Comment ça marche</a>
          <a href="#tarifs" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">Tarifs</a>
          <a href="#faq" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">FAQ</a>
          <Link href="/login" className="text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors font-medium text-sm">
            Connexion
          </Link>
          <Link href="/signup" className="bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
            S&apos;inscrire
          </Link>
        </div>
      </nav>

      <main>
        {/* ── HERO ── */}
        <section className="relative min-h-[480px] flex items-center overflow-hidden">
          <Image
            src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=80"
            alt="Plage tropicale ensoleillée — voyagez moins cher avec Globe Genius"
            fill
            priority
            className="object-cover"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-ink)]/90 via-[var(--color-ink)]/70 to-[var(--color-ink)]/30" />
          <HeroContent />
        </section>

        {/* ── SOCIAL PROOF BAR ── */}
        <section className="flex flex-wrap justify-center gap-8 sm:gap-16 py-6 px-6 bg-white border-t border-[var(--color-sand)]">
          {[
            { value: "+2 400", label: "voyageurs inscrits" },
            { value: "-70%", label: "meilleur deal détecté" },
            { value: "30 j", label: "garantie satisfait ou remboursé" },
            { value: "9", label: "aéroports surveillés" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl font-extrabold text-[var(--color-coral)]">{s.value}</div>
              <div className="text-xs text-gray-400 mt-1">{s.label}</div>
            </div>
          ))}
        </section>

        {/* Deals passés, comment ça marche, FAQ */}
        <LandingAnimated />

        {/* ── PRICING ── */}
        <section id="tarifs" className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
            Choisissez votre formule
          </h2>
          <p className="text-center text-gray-400 text-sm mb-10">
            Un seul deal récupère jusqu&apos;à 10× le prix de l&apos;abonnement.
          </p>
          <div className="flex flex-col sm:flex-row gap-6 max-w-2xl mx-auto">
            {/* Premium first — anchoring effect */}
            <div className="flex-1 bg-[var(--color-ink)] rounded-2xl p-6 relative order-first sm:order-none ring-2 ring-[var(--color-coral)]">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--color-coral)] text-white text-xs font-bold px-3 py-1 rounded-full whitespace-nowrap">
                ⭐ RECOMMANDÉ
              </span>
              <div className="font-bold text-[var(--color-coral)] text-sm mb-1">Premium</div>
              <div className="mb-1">
                <span className="line-through text-gray-500 text-base">59€</span>{" "}
                <span className="text-3xl font-extrabold text-white">29€</span>
                <span className="text-gray-500 text-sm">/an</span>
              </div>
              <p className="text-[var(--color-coral)] text-xs font-semibold mb-4">Offre printemps — expire bientôt</p>
              <div className="text-sm text-gray-400 leading-loose mb-6">
                ✓ <span className="text-white">Tous les deals, jusqu&apos;à -70%</span><br />
                ✓ <span className="text-white">Erreurs de prix des compagnies</span><br />
                ✓ <span className="text-white">9 aéroports de départ</span><br />
                ✓ <span className="text-white">Alertes Telegram prioritaires</span><br />
                ✓ <span className="text-white font-semibold">Garantie satisfait 30 jours</span><br />
                <span className="text-[var(--color-forest)]">= 2,42€/mois · rentabilisé dès 1 vol</span>
              </div>
              <Link href="/signup" className="block text-center py-3 rounded-xl font-bold text-sm bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white transition-colors">
                Commencer Premium →
              </Link>
            </div>
            <div className="flex-1 bg-white border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="font-bold text-gray-400 text-sm mb-1">Gratuit</div>
              <div className="text-3xl font-extrabold text-[var(--color-ink)] mb-5">0€</div>
              <div className="text-sm text-gray-500 leading-loose mb-6">
                ✓ Deals à partir de -40%<br />
                ✓ 3 alertes complètes / semaine<br />
                ✓ 9 aéroports de départ<br />
                <span className="text-gray-300">✗ Deals au-delà de -50% (masqués)</span><br />
                <span className="text-gray-300">✗ Alertes illimitées</span><br />
                <span className="text-gray-300">✗ Erreurs de prix</span>
              </div>
              <Link href="/signup" className="block text-center py-3 rounded-xl font-bold text-sm border-2 border-[var(--color-sand)] text-gray-400 hover:border-[var(--color-ink)] hover:text-[var(--color-ink)] transition-colors">
                Essayer gratuitement
              </Link>
            </div>
          </div>
        </section>

        {/* ── CTA FINAL ── */}
        <section className="py-16 px-6 sm:px-12 bg-[var(--color-ink)] text-center">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-white mb-4">
            Chaque semaine sans alertes, c&apos;est un deal manqué.
          </h2>
          <p className="text-gray-400 mb-2">
            Les erreurs de prix disparaissent en quelques heures. Soyez prêt avant les autres.
          </p>
          <p className="text-gray-500 text-sm mb-8">Gratuit pour commencer — Premium en 30 secondes.</p>
          <Link href="/signup" className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors shadow-[0_8px_24px_rgba(232,57,42,0.4)]">
            Recevoir mes premières alertes →
          </Link>
          <p className="text-gray-600 text-xs mt-3">✓ Sans carte bancaire · ✓ Résiliable en 1 clic</p>
        </section>

        {/* ── TELEGRAM BANNER ── */}
        <section className="py-8 px-6 sm:px-12 bg-gradient-to-r from-[#0088cc]/10 to-[#0088cc]/5 border-t border-[#0088cc]/20">
          <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <svg className="w-12 h-12 text-[#0088cc] flex-shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
              </svg>
              <div>
                <h3 className="text-lg font-bold text-[#0088cc] mb-1">Reçois les alertes en temps réel</h3>
                <p className="text-gray-600 text-sm">Télécharge Telegram pour être notifié instantanément de chaque incroyable deal découvert</p>
              </div>
            </div>
            <a href="https://telegram.org/apps" target="_blank" rel="noopener noreferrer" className="px-6 py-3 bg-[#0088cc] hover:bg-[#006daa] text-white font-semibold rounded-xl transition-colors flex-shrink-0">
              Télécharger Telegram
            </a>
          </div>
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
