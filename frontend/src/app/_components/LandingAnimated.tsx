"use client";

import { motion } from "framer-motion";
import Link from "next/link";

const PAST_DEALS = [
  { origin: "CDG", destination: "JFK", city: "New York", flag: "🇺🇸", price: 198, usual: 580, discount: 66, img: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80" },
  { origin: "CDG", destination: "BKK", city: "Bangkok", flag: "🇹🇭", price: 312, usual: 750, discount: 58, img: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&q=80" },
  { origin: "ORY", destination: "RAK", city: "Marrakech", flag: "🇲🇦", price: 34, usual: 120, discount: 72, img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=800&q=80" },
  { origin: "LYS", destination: "LIS", city: "Lisbonne", flag: "🇵🇹", price: 48, usual: 180, discount: 73, img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=800&q=80" },
  { origin: "CDG", destination: "NRT", city: "Tokyo", flag: "🇯🇵", price: 389, usual: 900, discount: 57, img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80" },
  { origin: "MRS", destination: "BCN", city: "Barcelone", flag: "🇪🇸", price: 19, usual: 85, discount: 78, img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800&q=80" },
];

const STEPS = [
  { num: "1", title: "On surveille les vols depuis 9 aéroports français", desc: "CDG, Orly, Beauvais, Lyon, Marseille, Toulouse, Bordeaux, Nantes, Nice. Couverture actuelle : Europe, Méditerranée et Afrique du Nord. Long-courrier (Asie, Amériques) cet été 2026." },
  { num: "2", title: "On repère les anomalies de prix", desc: "Dès qu'un tarif chute sous le prix habituel (calculé à partir d'historiques de plusieurs semaines), on le marque comme un deal. Au départ de Paris, les prix sont rafraîchis toutes les 20 minutes. Sur les autres aéroports, toutes les 2 heures." },
  { num: "3", title: "On vérifie chaque deal avant de te l'envoyer", desc: "95% des deals sont re-vérifiés sur une seconde source pour éliminer les ghost fares (prix affiché qui n'existe pas vraiment). Tu reçois moins de bruit." },
  { num: "4", title: "Notification Telegram, 1 à 3 par jour max", desc: "Prix, dates, lien direct pour réserver. On plafonne à 3 alertes/jour étalées dans le temps — jamais 4 notifs entre 2h et 4h du matin. Les erreurs de prix disparaissent souvent en 1-4h, donc l'avance compte." },
];

const faqs = [
  { q: "C'est quoi GlobeGenius exactement ?", a: "On surveille en continu les prix des vols depuis 9 aéroports français vers l'Europe, la Méditerranée et l'Afrique du Nord. Quand un tarif chute significativement sous le prix habituel, on t'envoie une alerte Telegram avec dates, prix et lien direct pour réserver. On est en beta publique depuis mai 2026." },
  { q: "Pourquoi c'est gratuit pendant la beta ?", a: "Parce que ce n'est pas encore un produit fini. La couverture est limitée à l'Europe et la Méditerranée — le long-courrier (Asie, Amériques) arrive cet été 2026. Les 100 premiers inscrits gardent un statut « Membre fondateur » à vie : ils restent gratuits même quand on lancera officiellement à 4,99€/mois." },
  { q: "Combien d'alertes je reçois par jour ?", a: "Entre 1 et 3 alertes par jour selon ta config (aéroports + seuil de réduction minimum). On plafonne strictement à 5/24h, étalées dans le temps (jamais 4 notifs entre 2h et 4h du matin). Tu peux ajuster ton seuil à tout moment depuis ton profil." },
  { q: "Comment sont vérifiés les deals ?", a: "Chaque deal détecté est re-vérifié sur une seconde source avant envoi (95% de couverture). Ça élimine les « ghost fares » — les prix affichés mais qui n'existent pas vraiment au moment de réserver. Tu reçois moins de bruit que sur un comparateur classique." },
  { q: "Comment je gère mes préférences ?", a: "Depuis Telegram directement (commande /destinations pour bloquer une ville, /pause pour suspendre les alertes 7/30 jours, ou bouton « Masquer » sur chaque alerte) ou depuis la page Profil sur le site (aéroports, seuil de réduction minimum, destinations bloquées)." },
  { q: "Pourquoi certains deals disparaissent avant que j'aie pu réserver ?", a: "Les tarifs erronés (« erreurs de prix ») sont des oublis de configuration des compagnies. Dès qu'elles s'en rendent compte, elles corrigent — parfois en 1-4 heures. C'est pourquoi on t'envoie l'alerte dans les minutes qui suivent la détection. Réserver dans l'heure maximise les chances d'obtenir le prix." },
  { q: "Et le long-courrier (Tokyo, New York, Bangkok) ?", a: "Pas encore. La baseline statistique sur ces routes n'est pas mature, on enverrait trop de faux positifs. Couverture long-courrier prévue été 2026 — les fondateurs y auront accès en priorité." },
];

function FAQItem({ q, a, i }: { q: string; a: string; i: number }) {
  return (
    <motion.details
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: i * 0.05 }}
      className="group border-b border-[var(--color-sand)] last:border-0"
    >
      <summary className="flex items-center justify-between py-5 cursor-pointer list-none">
        <span className="font-medium text-[15px] text-[var(--color-ink)] pr-4">{q}</span>
        <span className="text-gray-300 group-open:rotate-45 transition-transform text-xl shrink-0">+</span>
      </summary>
      <p className="text-sm text-gray-500 leading-relaxed pb-5 pr-8">{a}</p>
    </motion.details>
  );
}

type HeroContentProps = {
  /** Number of users with Telegram linked — drives the "X / 100" badge. */
  foundersCount?: number;
  /** Hard cap from the backend. Defaults to 100 if not supplied. */
  maxFounders?: number;
};

export function HeroContent({ foundersCount = 0, maxFounders = 100 }: HeroContentProps) {
  const remaining = Math.max(maxFounders - foundersCount, 0);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative z-10 px-6 sm:px-12 py-16 max-w-2xl"
    >
      <Link
        href="/beta"
        className="inline-block bg-[var(--color-coral)]/20 border border-[var(--color-coral)]/40 text-[#FF9B82] px-4 py-1.5 rounded-full text-sm font-bold mb-6 backdrop-blur-sm hover:bg-[var(--color-coral)]/30 transition-colors"
      >
        🚧 Beta publique · {foundersCount}/{maxFounders} places fondateurs prises
      </Link>
      <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-white leading-tight mb-4">
        Alertes vols{" "}
        <em className="not-italic text-[var(--color-coral)]">vérifiées</em>{" "}
        depuis 9 aéroports français.
      </h1>
      <p className="text-white/75 text-lg leading-relaxed mb-8 max-w-lg">
        Couverture actuelle : Europe, Méditerranée, Afrique du Nord.
        <br />
        Une à trois notifications Telegram par jour, jamais plus.
        <br />
        Long-courrier (Asie, Amériques) cet été 2026.
      </p>
      <Link
        href="/signup"
        className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors shadow-[0_8px_24px_rgba(255,107,71,0.3)]"
      >
        Rejoindre les {maxFounders} fondateurs
      </Link>
      <p className="text-white/50 text-sm mt-3">
        Gratuit · Statut premium à vie · Plus que {remaining} places
      </p>
    </motion.div>
  );
}

export default function LandingAnimated() {
  return (
    <>
      {/* ── DEALS PASSÉS ── */}
      <section className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
          Ne cherchez plus, c&apos;est nous qui trouvons
        </h2>
        <p className="text-center text-gray-400 text-sm mb-10">
          Exemples de vrais deals détectés par Globe Genius ces dernières semaines.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-5xl mx-auto">
          {PAST_DEALS.map((deal, i) => (
            <motion.div
              key={deal.destination}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              className="bg-white rounded-2xl overflow-hidden border border-[var(--color-sand)]"
            >
              <div
                className="h-28 sm:h-36 bg-cover bg-center relative"
                style={{ backgroundImage: `url(${deal.img})` }}
              >
                <span className="absolute top-3 right-3 bg-[var(--color-coral)] text-white text-xs font-bold px-2.5 py-1 rounded-lg">
                  -{deal.discount}%
                </span>
              </div>
              <div className="p-3 sm:p-4">
                <div className="font-bold text-[var(--color-ink)] text-sm mb-1">
                  {deal.origin} → {deal.city} {deal.flag}
                </div>
                <div className="text-xs text-gray-400 mb-2">A/R</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-lg sm:text-xl font-extrabold text-[var(--color-coral)]">{deal.price}€</span>
                  <span className="text-sm text-gray-300 line-through">{deal.usual}€</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
        <div className="text-center mt-8">
          <Link href="/signup" className="text-[var(--color-coral)] font-bold text-sm hover:underline">
            S&apos;inscrire pour ne rien rater →
          </Link>
        </div>
      </section>

      {/* ── COMMENT ÇA MARCHE ── */}
      <section id="comment-ca-marche" className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-12">
          Comment ça marche ?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 max-w-5xl mx-auto">
          {STEPS.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.4 }}
              className="text-center"
            >
              <div className="w-12 h-12 bg-[#FFF1EC] text-[var(--color-coral)] rounded-full flex items-center justify-center font-extrabold text-lg mx-auto mb-4">
                {step.num}
              </div>
              <h3 className="font-bold text-[var(--color-ink)] text-base mb-2">{step.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-10">
          Questions fréquentes
        </h2>
        <div className="max-w-2xl mx-auto">
          {faqs.map((faq, i) => (
            <FAQItem key={i} q={faq.q} a={faq.a} i={i} />
          ))}
        </div>
      </section>
    </>
  );
}
