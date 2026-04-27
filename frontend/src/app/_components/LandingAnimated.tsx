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
  { num: "1", title: "On surveille tous les vols au départ de la France", desc: "Depuis 9 aéroports français, vers le monde entier. En continu, 24h/24." },
  { num: "2", title: "L'algorithme détecte l'anomalie de prix", desc: "Dès qu'un tarif chute sous le prix habituel, notre système le signale. Pour Ryanair et Vueling au départ de Paris, la vérification a lieu toutes les 20 minutes." },
  { num: "3", title: "Vous recevez l'alerte sur Telegram", desc: "Prix, dates, lien direct pour réserver. L'alerte arrive dans les minutes qui suivent la détection — pas le lendemain." },
  { num: "4", title: "Vous réservez avant que ça remonte", desc: "Les erreurs de prix disparaissent souvent en quelques heures. L'avance qu'on vous donne, c'est ça qui fait la différence." },
];

const faqs = [
  { q: "Comment fonctionne Globe Genius ?", a: "On surveille en permanence les prix des vols au départ de 9 aéroports français. Dès qu'on détecte une baisse de prix significative, on vous envoie une alerte sur Telegram avec tous les détails pour réserver." },
  { q: "Quelle est la différence entre Gratuit et Premium ?", a: "En Gratuit, vous recevez jusqu'à 3 alertes complètes par semaine sur les deals à -40% et plus. En Premium, vous accédez à tous les deals sans limite (jusqu'à -70%+), y compris les erreurs de prix des compagnies, avec prix et liens de réservation débloqués." },
  { q: "Comment fonctionne la garantie 30 jours ?", a: "Si Premium ne vous convient pas, contactez-nous dans les 30 jours suivant votre achat et on vous rembourse intégralement, sans question." },
  { q: "Les prix incluent-ils les bagages ?", a: "Les prix affichés sont ceux des compagnies aériennes. Les bagages en soute sont parfois inclus selon la compagnie et le tarif. On le précise dans chaque alerte quand l'information est disponible." },
  { q: "Combien de temps entre la publication du prix et votre alerte ?", a: "Pour les vols Ryanair et Vueling au départ de Paris (CDG/ORY), on scrape les prix directement sur les APIs des compagnies toutes les 20 minutes. Dès qu'une anomalie est détectée, l'alerte Telegram part dans la foulée, généralement moins de 5 minutes après l'apparition du deal. Pour les autres aéroports et destinations, on utilise un agrégateur de vols interrogé toutes les 2 heures." },
  { q: "Pourquoi certains deals disparaissent avant que j'aie pu réserver ?", a: "Les tarifs érronés (« erreurs de prix ») sont des oublis de configuration des compagnies. Dès qu'elles s'en rendent compte, elles corrigent le tarif — parfois en quelques heures. C'est pourquoi les alertes temps réel sont déterminantes : réserver dans l'heure qui suit l'alerte maximise vos chances d'obtenir le prix affiché. Passez commande rapidement et contactez la compagnie si le tarif change avant l'émission." },
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

export function HeroContent() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative z-10 px-6 sm:px-12 py-16 max-w-2xl"
    >
      <span className="inline-flex items-center gap-2 bg-[var(--color-coral)] text-white px-4 py-1.5 rounded-full text-sm font-bold mb-6">
        🔥 Offre printemps — 29€/an · <span className="line-through opacity-70">59€</span> · Expire bientôt
      </span>
      <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-white leading-tight mb-4">
        Les vols à -70% partent{" "}
        <br className="hidden sm:block" />
        <em className="not-italic text-[var(--color-coral)]">en quelques heures.</em>
      </h1>
      <p className="text-white/80 text-lg leading-relaxed mb-3 max-w-lg">
        Globe Genius surveille les prix 24h/24 et vous alerte sur Telegram dès qu&apos;une erreur de prix apparaît — avant qu&apos;elle disparaisse.
      </p>
      <p className="text-white/50 text-sm mb-8 flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
        +2 400 voyageurs ont déjà économisé cette année
      </p>
      <Link
        href="/signup"
        className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-all shadow-[0_8px_32px_rgba(232,57,42,0.45)] hover:shadow-[0_12px_40px_rgba(232,57,42,0.55)] hover:-translate-y-0.5"
      >
        Recevoir mes premières alertes gratuitement →
      </Link>
      <p className="text-white/40 text-sm mt-3">✓ Gratuit · ✓ Sans carte · ✓ Résiliable en 1 clic</p>
    </motion.div>
  );
}

export default function LandingAnimated() {
  return (
    <>
      {/* ── DEALS PASSÉS ── */}
      <section className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
          Ne cherchez plus vos voyages. On vous alerte quand le prix est vraiment bon.
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
