import type { Metadata } from "next";
import Link from "next/link";
import RedirectIfLoggedIn from "./_components/RedirectIfLoggedIn";
import LandingAnimated, { HeroContent } from "./_components/LandingAnimated";
import { LandingNotificationHero } from "./_components/LandingNotificationHero";
import { Wordmark } from "./_components/Wordmark";

export const metadata: Metadata = {
  alternates: {
    canonical: "https://globegenius.app",
  },
};

/**
 * Fetches destination guides for the landing "Nos guides destination" section.
 * Now returns 3 random guides per visit (no caching) instead of the 6 most recent
 * — keeps the section fresh for repeat visitors.
 */
async function fetchRecentDestinationGuides(): Promise<Array<{ iata: string; destination: string; cover_photo: string; title: string }>> {
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${API_URL}/api/destinations?random=true&limit=3`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

const faqs = [
  { q: "Comment fonctionne Globe Genius ?", a: "On surveille en permanence les prix des vols au départ de 9 aéroports français. Dès qu’on détecte une baisse de prix significative, on vous envoie une alerte sur Telegram avec tous les détails pour réserver." },
  { q: "Quelle est la différence entre Gratuit et Premium ?", a: "En Gratuit, vous recevez 1 deal aller-retour entre -20% et -40% chaque jour, plus 1 grosse promo (≥-40%) une fois par semaine. En Premium, vous choisissez votre seuil (-40, -50 ou -60%), vous accédez en plus aux aller simple et aux combos malins (2 billets séparés moins chers qu'un A/R), et les long-courriers ne sont jamais plafonnés." },
  { q: "Combien d'alertes je reçois par jour ?", a: "On plafonne à 3 alertes par jour pour ne pas saturer votre Telegram. Les long-courriers (Asie, Amériques, océan Indien...) ne comptent pas dans ce plafond car ils sont rares et précieux. Vous pilotez le volume avec votre seuil de promo : -40% (~2-3/jour), -50% (~1-2/jour), -60% (0-1/jour, mais quand ça arrive c'est exceptionnel)." },
  { q: "Comment fonctionne la garantie 30 jours ?", a: "Si Premium ne vous convient pas, contactez-nous dans les 30 jours suivant votre achat et on vous rembourse intégralement, sans question." },
  { q: "Les prix incluent-ils les bagages ?", a: "Les prix affichés sont ceux des compagnies aériennes. Les bagages en soute sont parfois inclus selon la compagnie et le tarif. On le précise dans chaque alerte quand l’information est disponible." },
  { q: "Combien de temps entre la publication du prix et votre alerte ?", a: "Les prix sont mis à jour toutes les 20 minutes au départ de Paris (Beauvais, CDG et Orly), et toutes les 2 heures sur les autres aéroports français. Dès qu'une bonne affaire est repérée, l'alerte Telegram part dans la foulée, généralement moins de 5 minutes après l'apparition du deal." },
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

export default async function Landing() {
  const recentGuides = await fetchRecentDestinationGuides();
  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      <RedirectIfLoggedIn />

      {/* FAQ JSON-LD — server-rendered, crawler-visible */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />

      {/* ── NAVBAR ── */}
      <nav aria-label="Navigation principale" className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 h-[80px] bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-lg leading-none">
          <Wordmark />
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
        {/*
          The hero used to show a tropical beach photo, then a clumsy
          stylised world map. Replaced by a floating Telegram-style
          notification card that loops through the three V5 deal flavours
          (round-trip, one-way, split-ticket combo). Shows the product in
          action: the user receives an alert and reads the price drop.
        */}
        <section className="relative min-h-[520px] sm:min-h-[600px] flex items-center overflow-hidden">
          <LandingNotificationHero />
          <HeroContent />
        </section>

        {/* ── STATS BAR ── */}
        <section className="flex flex-wrap justify-center gap-8 sm:gap-12 py-6 px-6 bg-white border-t border-[var(--color-sand)]">
          {[
            { value: "<5s", label: "alerte sur Telegram" },
            { value: "-70%", label: "meilleur deal repéré" },
            { value: "24h/24", label: "surveillance des prix" },
            { value: "9", label: "aéroports français" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl font-extrabold text-[var(--color-ink)]">{s.value}</div>
              <div className="text-xs text-gray-400 mt-1">{s.label}</div>
            </div>
          ))}
        </section>

        {recentGuides.length > 0 && (
          <section className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
              Nos guides destination
            </h2>
            <p className="text-center text-gray-500 text-sm mb-10">
              Des guides écrits pour préparer chaque destination, mis à jour à chaque nouveau deal détecté.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {recentGuides.map((g) => (
                <Link key={g.iata} href={`/destination/${g.iata.toLowerCase()}`}
                      className="group block overflow-hidden rounded-2xl border border-[var(--color-sand)] bg-white hover:border-[var(--color-coral)] transition-colors">
                  <div className="relative aspect-video overflow-hidden">
                    {g.cover_photo ? (
                      // Using <img> here intentionally — <Image> with `fill` requires extra layout setup
                      // and these cards are below the fold.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={g.cover_photo} alt={g.destination}
                           className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform" />
                    ) : (
                      <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-coral-50)] to-[var(--color-cream)] flex items-center justify-center">
                        <span className="font-[family-name:var(--font-dm-serif)] text-3xl text-[var(--color-coral)]/40">
                          {g.iata}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-4">
                    <div className="text-xs text-gray-400">{g.destination}</div>
                    <div className="font-bold text-[var(--color-ink)]">{g.title}</div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* ── 3 TYPES DE DEALS ── */}
        <section className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
            On cherche partout pour vous
          </h2>
          <p className="text-center text-gray-500 text-sm max-w-xl mx-auto mb-10">
            La plupart des comparateurs ne regardent qu&apos;un seul type de billet&nbsp;: l&apos;aller-retour classique.
            Nous, on en surveille trois — c&apos;est comme ça qu&apos;on attrape des deals que les autres laissent passer.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">✈️</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">Aller-retour classique</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Le bon plan le plus courant&nbsp;: aller + retour, mêmes dates, prix total imbattable.
                Surveillé en continu sur les <strong>9 aéroports français</strong>.
              </p>
            </div>
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">🎫</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">Aller simple</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Tour du monde, expat, séjour long&nbsp;? On guette aussi les promos sur les sens uniques.
                Personne d&apos;autre ne le fait.
              </p>
            </div>
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">💡</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">
                Combo malin <span className="text-[var(--color-coral)]">— 2× aller simple</span>
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Parfois, deux billets aller simple sur deux compagnies différentes coûtent <strong>moins cher</strong> qu&apos;un A/R.
                On fait le calcul à votre place — économie typique <strong>-30%</strong>.
              </p>
            </div>
          </div>
          <p className="text-center text-xs text-gray-400 mt-6 max-w-xl mx-auto">
            💬 L&apos;aller simple et le combo malin sont réservés aux abonnés Premium et s&apos;activent dans votre profil.
          </p>
        </section>

        {/* Deals passés, comment ça marche, FAQ */}
        <LandingAnimated />

        {/* ── POURQUOI TELEGRAM ── */}
        <section className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
            Pourquoi Telegram, et pas un email&nbsp;?
          </h2>
          <p className="text-center text-gray-500 text-sm max-w-xl mx-auto mb-10">
            Parce qu&apos;un bon plan vol disparaît en 1 à 4 heures. L&apos;email arrive trop tard,
            une app à installer fait perdre 30 secondes décisives.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">⚡</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">5 secondes, pas 5 minutes</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Une notif Telegram s&apos;affiche sur ton écran de verrouillage en quelques secondes.
                Le temps qu&apos;un email arrive et soit lu, le tarif est déjà parti.
              </p>
            </div>
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">📱</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">Pas d&apos;app à installer</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Tu utilises déjà Telegram (ou tu l&apos;installes en 30 secondes — gratuit).
                Aucun compte à créer chez nous&nbsp;: tu autorises notre bot, c&apos;est tout.
              </p>
            </div>
            <div className="bg-[var(--color-cream-pure)] border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="text-2xl mb-3">🎚️</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-2">
                Tu pilotes tout depuis Telegram
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Bloque une destination en un tap, mets en pause 7 ou 30 jours,
                reprends quand tu veux — sans jamais ouvrir le site. C&apos;est toi qui pilotes.
              </p>
            </div>
          </div>
          <p className="text-center text-xs text-gray-400 mt-6 max-w-xl mx-auto">
            ✓ Compatible iPhone, Android, ordinateur · ✓ Tes alertes te suivent même hors connexion
          </p>
        </section>

        {/* ── PRICING ── */}
        <section id="tarifs" className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
            Choisissez votre formule
          </h2>
          <p className="text-center text-gray-400 text-sm mb-10">
            Un vol Premium rentabilise l&apos;abonnement dès le premier voyage.
          </p>
          <div className="flex flex-col sm:flex-row gap-6 max-w-2xl mx-auto">
            <div className="flex-1 bg-white border border-[var(--color-sand)] rounded-2xl p-6">
              <div className="font-bold text-[var(--color-ink)] text-sm mb-1">Gratuit</div>
              <div className="text-3xl font-extrabold text-[var(--color-ink)] mb-5">0€</div>
              <div className="text-sm text-gray-500 leading-loose mb-6">
                ✓ <span className="text-[var(--color-ink)] font-medium">1 deal -20% à -40%</span> par jour<br />
                ✓ <span className="text-[var(--color-ink)] font-medium">1 grosse promo ≥-40%</span> par semaine<br />
                ✓ Aller-retour, 9 aéroports de départ<br />
                <span className="text-gray-300">✗ Choisir le seuil de promo</span><br />
                <span className="text-gray-300">✗ Alertes illimitées</span><br />
                <span className="text-gray-300">✗ Aller simple &amp; combos malins</span>
              </div>
              <Link href="/signup" className="block text-center py-3 rounded-xl font-bold text-sm border-2 border-[var(--color-ink)] text-[var(--color-ink)] hover:bg-[var(--color-ink)] hover:text-white transition-colors">
                S&apos;inscrire gratuitement
              </Link>
            </div>
            <div className="flex-1 bg-[var(--color-ink)] rounded-2xl p-6 relative">
              <span className="absolute -top-3 right-4 bg-[var(--color-coral)] text-white text-xs font-bold px-3 py-1 rounded-full">
                POPULAIRE
              </span>
              <div className="font-bold text-[var(--color-coral)] text-sm mb-1">Premium</div>
              <div className="mb-5">
                <span className="line-through text-gray-500 text-base">59€</span>{" "}
                <span className="text-3xl font-extrabold text-white">29€</span>
                <span className="text-gray-500 text-sm">/an</span>
              </div>
              <div className="text-sm text-gray-400 leading-loose mb-6">
                ✓ <span className="text-white">Tous les deals jusqu&apos;à -70%+</span><br />
                ✓ <span className="text-white">Filtre personnalisé : -40, -50 ou -60%</span><br />
                ✓ <span className="text-white">Alertes illimitées, sans quota</span><br />
                ✓ <span className="text-white">Aller simple &amp; combos malins</span><br />
                ✓ <span className="text-white">9 aéroports de départ</span><br />
                ✓ <span className="text-white">Garantie satisfait 30 jours</span><br />
                <span className="text-[var(--color-forest)]">= 2,42€/mois</span>
              </div>
              <Link href="/signup" className="block text-center py-3 rounded-xl font-bold text-sm bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white transition-colors">
                Offre printemps -41%
              </Link>
            </div>
          </div>
        </section>

        {/* ── CTA FINAL — 2 cards : déjà Telegram / pas encore ── */}
        <section className="py-16 px-6 sm:px-12 bg-[var(--color-ink)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-white text-center mb-3">
            Prêt à recevoir ton premier deal&nbsp;?
          </h2>
          <p className="text-gray-400 text-center mb-10">
            Choisis la voie selon ton équipement. Activation en 30 secondes dans les deux cas.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-4xl mx-auto">
            {/* Already on Telegram */}
            <div className="bg-white rounded-2xl p-6 flex flex-col">
              <div className="text-sm font-semibold text-[var(--color-coral)] mb-2">
                ✓ Tu as déjà Telegram
              </div>
              <h3 className="font-[family-name:var(--font-dm-serif)] text-xl text-[var(--color-ink)] mb-3">
                Active tes alertes en 30 secondes
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-6 flex-1">
                Crée ton compte gratuit, choisis tes aéroports, lie ton Telegram en un clic.
                Le premier deal arrive dans les 24h en moyenne.
              </p>
              <Link
                href="/signup"
                className="block text-center bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-6 py-3 rounded-xl font-bold text-sm transition-colors shadow-[0_8px_24px_rgba(255,107,71,0.25)]"
              >
                Activer mes alertes Telegram
              </Link>
              <p className="text-xs text-gray-400 mt-2 text-center">Gratuit, sans carte bancaire</p>
            </div>

            {/* Doesn't have Telegram yet */}
            <div className="bg-[#0088cc]/10 border border-[#0088cc]/30 rounded-2xl p-6 flex flex-col">
              <div className="text-sm font-semibold text-[#4DA9DD] mb-2 flex items-center gap-2">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
                Pas encore Telegram&nbsp;?
              </div>
              <h3 className="font-[family-name:var(--font-dm-serif)] text-xl text-white mb-3">
                30 secondes, gratuit, depuis l&apos;App Store
              </h3>
              <p className="text-sm text-gray-300 leading-relaxed mb-6 flex-1">
                Telegram est utilisé par plus d&apos;un milliard de personnes dans le monde.
                Compatible iPhone, Android et ordinateur. Aucun spam, aucune pub, jamais.
              </p>
              <a
                href="https://telegram.org/apps"
                target="_blank"
                rel="noopener noreferrer"
                className="block text-center bg-[#0088cc] hover:bg-[#006daa] text-white px-6 py-3 rounded-xl font-bold text-sm transition-colors"
              >
                Télécharger Telegram
              </a>
              <p className="text-xs text-gray-400 mt-2 text-center">Puis reviens t&apos;inscrire ici</p>
            </div>
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
