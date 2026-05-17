import type { Metadata } from "next";
import Link from "next/link";
import RedirectIfLoggedIn from "./_components/RedirectIfLoggedIn";
import LandingAnimated, { HeroContent } from "./_components/LandingAnimated";
import { LandingNotificationHero } from "./_components/LandingNotificationHero";
import { Wordmark } from "./_components/Wordmark";
import { getBetaCount } from "@/lib/api";

export const metadata: Metadata = {
  title: "GlobeGenius — Alertes vols vérifiées 9 aéroports français · Beta",
  description:
    "Une à trois alertes Telegram par jour sur les vols à -40% / -80% depuis 9 aéroports français. Couverture Europe + Méditerranée + Afrique du Nord. Beta publique, gratuit pour les 100 premiers fondateurs.",
  alternates: {
    canonical: "https://globegenius.app",
  },
  openGraph: {
    title: "GlobeGenius · Beta publique · 9 aéroports français",
    description:
      "Alertes vols vérifiées (95%) sur 162 destinations Europe/Med matures. Gratuit pour les 100 premiers fondateurs.",
    url: "https://globegenius.app",
    type: "website",
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
  { q: "C'est quoi GlobeGenius exactement ?", a: "On surveille en continu les prix des vols depuis 9 aéroports français vers l'Europe, la Méditerranée et l'Afrique du Nord. Quand un tarif chute significativement sous le prix habituel, on t'envoie une alerte Telegram avec dates, prix et lien direct pour réserver. On est en beta publique depuis mai 2026." },
  { q: "Pourquoi c'est gratuit pendant la beta ?", a: "Parce que ce n'est pas encore un produit fini. La couverture est limitée à l'Europe et la Méditerranée — le long-courrier (Asie, Amériques) arrive cet été 2026. Les 100 premiers inscrits gardent un statut « Membre fondateur » à vie : ils restent gratuits même quand on lancera officiellement à 4,99€/mois." },
  { q: "Combien d'alertes je reçois par jour ?", a: "Entre 1 et 3 alertes par jour selon ta config. On plafonne strictement à 5/24h, étalées dans le temps (jamais 4 notifs entre 2h et 4h du matin). Tu peux ajuster ton seuil à tout moment depuis ton profil." },
  { q: "Comment sont vérifiés les deals ?", a: "Chaque deal détecté est re-vérifié sur une seconde source avant envoi (95% de couverture). Ça élimine les ghost fares — prix affichés mais qui n'existent pas vraiment au moment de réserver." },
  { q: "Comment je gère mes préférences ?", a: "Depuis Telegram directement (commandes /destinations, /pause, ou bouton Masquer sur chaque alerte) ou depuis la page Profil sur le site." },
  { q: "Et le long-courrier (Tokyo, New York, Bangkok) ?", a: "Pas encore. La baseline statistique sur ces routes n'est pas mature, on enverrait trop de faux positifs. Couverture long-courrier prévue été 2026 — les fondateurs y auront accès en priorité." },
  { q: "Pourquoi certains deals disparaissent avant que j'aie pu réserver ?", a: "Les tarifs erronés (erreurs de prix) sont des oublis des compagnies. Elles corrigent en 1-4 heures dès qu'elles s'en rendent compte. C'est pourquoi on t'envoie l'alerte dans les minutes qui suivent la détection. Réserver dans l'heure maximise les chances." },
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
  const [recentGuides, betaCount] = await Promise.all([
    fetchRecentDestinationGuides(),
    getBetaCount(),
  ]);
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
          <Link href="/beta" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">Beta</Link>
          <a href="#faq" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">FAQ</a>
          <Link href="/login" className="text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors font-medium text-sm">
            Connexion
          </Link>
          <Link href="/signup" className="bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
            Rejoindre la beta
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
          <HeroContent
            foundersCount={betaCount.founders_count}
            maxFounders={betaCount.max_founders}
          />
        </section>

        {/* ── 3 PILIERS DE POSITIONNEMENT ──
            Replaces the 4-numbers stats bar with the three differentiators
            that anchor the whole brand (see POSITIONNEMENT.md for the
            long form). Each pillar is intentionally short: a pictogramme,
            a 3-4 word headline, a one-line proof. The reader should be
            able to read all three in under 5 seconds and remember them.
              1. Géographie    — 9 aéroports français, pas Paris-only
              2. Identité      — par un Français, pas une équipe US
              3. Honnêteté     — prix de référence = médiane statistique
                                  réelle, pas un max gonflé
        */}
        <section className="py-12 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            <div className="text-center md:text-left">
              <div className="text-3xl mb-2">🇫🇷</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-1">9 aéroports français</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Pas seulement Paris. Lyon, Marseille, Toulouse, Bordeaux, Nantes, Nice et 3 autres.
              </p>
            </div>
            <div className="text-center md:text-left">
              <div className="text-3xl mb-2">🤝</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-1">Pensé en France</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Un service d&apos;alertes vols pensé en France, pour les voyageurs qui partent de France.
              </p>
            </div>
            <div className="text-center md:text-left">
              <div className="text-3xl mb-2">💯</div>
              <h3 className="font-bold text-[var(--color-ink)] mb-1">Sans prix gonflés</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Référence = médiane statistique sur 6 mois. Pas un prix max théorique pour faire briller le deal.
              </p>
            </div>
          </div>
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
            💬 L&apos;aller simple et le combo malin s&apos;activent dans ton profil. Pendant la beta, tous les membres fondateurs y ont accès gratuitement.
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

        {/* ── BETA INVITE ──
            Replaces the Free vs Premium pricing block during the public
            beta. Stripe is still wired in the backend, but we don't
            display a paid plan until the long-haul coverage lands
            (target: summer 2026). The "founders for life" framing
            converts curiosity into commitment without asking for a
            payment that the product doesn't justify yet.
        */}
        <section id="tarifs" className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
            Pendant la beta publique
          </h2>
          <p className="text-center text-gray-400 text-sm mb-10">
            Tout est gratuit pour les {betaCount.max_founders} premiers inscrits.
            Statut « Membre fondateur » à vie quand on lancera officiellement.
          </p>
          <div className="max-w-2xl mx-auto bg-[var(--color-ink)] rounded-2xl p-8 text-center">
            <div className="text-[var(--color-coral)] text-sm font-bold mb-2">
              🚧 Beta publique · Lancement officiel été 2026
            </div>
            <div className="font-[family-name:var(--font-dm-serif)] text-4xl text-white mb-2">
              {betaCount.founders_count} / {betaCount.max_founders}
            </div>
            <div className="text-gray-400 text-sm mb-6">places fondateurs prises</div>
            <div className="text-sm text-gray-300 leading-loose mb-8 text-left max-w-md mx-auto">
              ✓ <span className="text-white">Alertes premium gratuites à vie</span><br />
              ✓ <span className="text-white">Accès au long-courrier dès l&apos;été 2026</span><br />
              ✓ <span className="text-white">Détection stopover dès qu&apos;elle sera livrée</span><br />
              ✓ <span className="text-white">Tes préférences personnalisées</span><br />
              ✓ <span className="text-white">Aucun engagement, désinscription en 1 clic</span>
            </div>
            <Link
              href="/signup"
              className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-base transition-colors shadow-[0_8px_24px_rgba(255,107,71,0.25)]"
            >
              Rejoindre la beta — gratuit à vie
            </Link>
            <p className="text-xs text-gray-500 mt-4">
              <Link href="/beta" className="underline hover:text-gray-300">En savoir plus sur le programme fondateur →</Link>
            </p>
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
