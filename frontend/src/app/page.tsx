"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";

/* ─── DATA ─── */
const deals = [
  { id: 1, from: "Paris", to: "Lisbonne", code: "CDG → LIS", dates: "10 – 17 mai", nights: 7, hotel: "Hotel Lisboa Plaza", stars: 4.3, price: 509, was: 978, off: 48, score: 84, img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=800&q=80", flag: "🇵🇹" },
  { id: 2, from: "Lyon", to: "Barcelone", code: "LYS → BCN", dates: "15 – 20 mai", nights: 5, hotel: "Casa Bonay", stars: 4.5, price: 320, was: 668, off: 52, score: 78, img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800&q=80", flag: "🇪🇸" },
  { id: 3, from: "Marseille", to: "Athènes", code: "MRS → ATH", dates: "22 – 28 mai", nights: 6, hotel: "Electra Palace", stars: 4.6, price: 445, was: 812, off: 45, score: 75, img: "https://images.unsplash.com/photo-1555993539-1732b0258235?w=800&q=80", flag: "🇬🇷" },
  { id: 4, from: "Nice", to: "Prague", code: "NCE → PRG", dates: "18 – 22 mai", nights: 4, hotel: "Mosaic House", stars: 4.4, price: 289, was: 525, off: 45, score: 72, img: "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=800&q=80", flag: "🇨🇿" },
  { id: 5, from: "Bordeaux", to: "Marrakech", code: "BOD → RAK", dates: "25 – 31 mai", nights: 6, hotel: "Riad Yasmine", stars: 4.7, price: 395, was: 740, off: 47, score: 81, img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=800&q=80", flag: "🇲🇦" },
  { id: 6, from: "Toulouse", to: "Amsterdam", code: "TLS → AMS", dates: "12 – 16 mai", nights: 4, hotel: "The Hoxton", stars: 4.4, price: 310, was: 580, off: 47, score: 76, img: "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=800&q=80", flag: "🇳🇱" },
];

const destinations = [
  { name: "Lisbonne", img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=400&q=80", deals: 12 },
  { name: "Barcelone", img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=400&q=80", deals: 9 },
  { name: "Marrakech", img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=400&q=80", deals: 7 },
  { name: "Rome", img: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=400&q=80", deals: 11 },
  { name: "Prague", img: "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=400&q=80", deals: 6 },
  { name: "Athènes", img: "https://images.unsplash.com/photo-1555993539-1732b0258235?w=400&q=80", deals: 8 },
];

const airports = ["Paris CDG", "Paris ORY", "Lyon", "Marseille", "Nice", "Bordeaux", "Nantes", "Toulouse"];

const faqs = [
  { q: "Comment sont détectés les deals ?", a: "Notre pipeline analyse les prix de milliers de vols et d'hôtels toutes les 2 heures. On compare chaque prix à la moyenne des 30 derniers jours. Seuls les packages avec une remise réelle de 40% ou plus sont retenus." },
  { q: "Est-ce que les prix affichés sont fiables ?", a: "Oui. Chaque prix est vérifié au moment du scraping et les données expirent après 2 heures. Les liens pointent directement vers les sites de réservation (Google Flights, Booking.com)." },
  { q: "Comment recevoir les alertes ?", a: "Après inscription, connectez votre compte Telegram via l'onboarding. Vous recevrez les alertes instantanément pour les deals avec un score supérieur à 70, et un digest quotidien à 8h." },
  { q: "Combien ça coûte ?", a: "L'accès est gratuit pendant la période de lancement. Un abonnement à 2,99€/mois sera mis en place prochainement avec un essai gratuit de 7 jours." },
  { q: "Quels aéroports sont couverts ?", a: "8 aéroports français : Paris CDG, Paris Orly, Lyon, Marseille, Nice, Bordeaux, Nantes et Toulouse. D'autres aéroports seront ajoutés selon la demande." },
];

/* ─── COMPONENTS ─── */
function DealCard({ deal, i }: { deal: (typeof deals)[0]; i: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: i * 0.06 }}
      className="group cursor-pointer"
    >
      <div className="relative aspect-[4/3] rounded-2xl overflow-hidden mb-3">
        <img src={deal.img} alt={deal.to} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
        <div className="absolute top-3 left-3 bg-red-500 text-white text-xs font-bold px-2.5 py-1 rounded-full">
          -{deal.off}%
        </div>
        <div className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm text-xs font-semibold px-2.5 py-1 rounded-full text-gray-800">
          ★ {deal.score}
        </div>
        <div className="absolute bottom-3 left-3 right-3">
          <div className="text-white font-semibold text-lg drop-shadow-lg">{deal.flag} {deal.from} → {deal.to}</div>
          <div className="text-white/80 text-xs">{deal.dates} · {deal.nights} nuits</div>
        </div>
      </div>
      <div className="px-1">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
          <span>🏨 {deal.hotel}</span>
          <span>·</span>
          <span>★ {deal.stars}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-bold">{deal.price} €</span>
          <span className="text-sm text-gray-400 line-through">{deal.was} €</span>
          <span className="text-xs text-gray-400 ml-auto">vol + hôtel / pers.</span>
        </div>
      </div>
    </motion.div>
  );
}

function FAQItem({ q, a, i }: { q: string; a: string; i: number }) {
  return (
    <motion.details
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: i * 0.05 }}
      className="group border-b border-gray-100 last:border-0"
    >
      <summary className="flex items-center justify-between py-5 cursor-pointer list-none">
        <span className="font-medium text-[15px] pr-4">{q}</span>
        <span className="text-gray-300 group-open:rotate-45 transition-transform text-xl shrink-0">+</span>
      </summary>
      <p className="text-sm text-gray-500 leading-relaxed pb-5 pr-8">{a}</p>
    </motion.details>
  );
}

/* ─── STRUCTURED DATA (static constants, no user input — safe for JSON-LD) ─── */
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://www.globegenius.app/#organization",
  name: "Globe Genius",
  url: "https://www.globegenius.app",
  logo: {
    "@type": "ImageObject",
    url: "https://www.globegenius.app/globe1.png",
    width: 512,
    height: 512,
  },
  description:
    "Globe Genius trouve les packages voyage (vol + hôtel) à -40% minimum sur le prix du marché.",
  sameAs: ["https://t.me/Globegenius_bot"],
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer support",
    availableLanguage: "French",
  },
};

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://www.globegenius.app/#website",
  name: "Globe Genius",
  url: "https://www.globegenius.app",
  description:
    "Packages voyage à prix cassés. Vols + hôtels à -40% minimum.",
  inLanguage: "fr-FR",
  publisher: { "@id": "https://www.globegenius.app/#organization" },
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map(f => ({
    "@type": "Question",
    name: f.q,
    acceptedAnswer: { "@type": "Answer", text: f.a },
  })),
};

/* ─── PAGE ─── */
export default function Landing() {
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const token = localStorage.getItem("gg_token");
    if (userId && token) {
      router.replace("/home");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-white">

      {/* ── JSON-LD STRUCTURED DATA ── */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />

      {/* ── NAV ── */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-8 h-8 shrink-0 object-contain" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-500">
            <a href="#deals" className="hover:text-gray-900 transition-colors">Deals</a>
            <a href="#how" className="hover:text-gray-900 transition-colors">Comment ça marche</a>
            <a href="#destinations" className="hover:text-gray-900 transition-colors">Destinations</a>
            <a href="#faq" className="hover:text-gray-900 transition-colors">FAQ</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium px-2.5 py-2 md:px-3">
              Connexion
            </Link>
            <Link href="/signup" className="text-sm font-semibold bg-[#222] text-white px-4 py-2 md:px-5 md:py-2.5 rounded-full hover:bg-black transition-colors">
              S'inscrire
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="relative overflow-hidden">
        {/* Background image */}
        <div className="absolute inset-0">
          <img
            src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1920&q=80"
            alt="Travel"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-white via-white/95 to-white/40" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 md:px-5 py-12 md:py-32 lg:py-40">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-xl"
          >
            <div className="inline-flex items-center gap-2 bg-cyan-50 border border-cyan-100 rounded-full px-3.5 py-1.5 mb-6">
              <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
              <span className="text-xs font-semibold text-cyan-700">Pipeline actif · 2 340+ vols analysés aujourd'hui</span>
            </div>

            <h1 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[48px] lg:text-[64px] leading-[1.08] tracking-tight mb-4 md:mb-5">
              Des packages voyage
              <br />
              <span className="text-gradient">à prix cassés.</span>
            </h1>
            <p className="text-gray-600 text-base md:text-lg leading-relaxed mb-6 md:mb-8">
              Nous analysons des milliers de vols et d'hôtels pour vous trouver des packages
              <strong className="text-gray-900"> à -40% minimum</strong> sur le prix du marché.
              Recevez les alertes sur Telegram.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                href="/signup"
                className="bg-[#222] text-white font-semibold px-6 py-3.5 md:px-8 md:py-4 rounded-full hover:bg-black transition-colors text-[15px] shadow-lg shadow-black/10 text-center"
              >
                Découvrir les deals →
              </Link>
              <a
                href="#how"
                className="text-gray-600 font-medium px-5 py-3.5 md:px-6 md:py-4 rounded-full border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all text-[15px] text-center"
              >
                Comment ça marche
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── SOCIAL PROOF ── */}
      <section className="border-y border-gray-100 bg-gray-50/50">
        <div className="max-w-6xl mx-auto px-4 md:px-5 py-6 md:py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { val: "2 340+", label: "Vols analysés / jour", icon: "✈️" },
              { val: "47", label: "Deals actifs", icon: "🔥" },
              { val: "-48%", label: "Meilleur deal actuel", icon: "💰" },
              { val: "8", label: "Aéroports couverts", icon: "🌍" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl mb-1">{s.icon}</div>
                <div className="text-2xl md:text-3xl font-bold tracking-tight">{s.val}</div>
                <div className="text-xs text-gray-400 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DEALS ── */}
      <section id="deals" className="py-12 md:py-24">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="flex items-end justify-between mb-10">
            <div>
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2"
              >
                Mis à jour il y a 23 min
              </motion.div>
              <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[36px]">
                Deals du moment
              </h2>
            </div>
            <Link href="/signup" className="text-sm font-semibold text-cyan-600 hover:underline hidden sm:block">
              Voir tous les deals →
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-7">
            {deals.map((d, i) => (
              <DealCard key={d.id} deal={d} i={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how" className="py-12 md:py-24 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="text-center mb-14">
            <div className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2">Simple & automatique</div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[36px] mb-3">
              Comment ça marche
            </h2>
            <p className="text-gray-400 max-w-lg mx-auto text-[15px]">
              Un système qui tourne 24h/24 pour vous trouver les meilleures opportunités.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-8">
            {[
              {
                n: "1",
                t: "Scan permanent",
                d: "Notre pipeline analyse des milliers de vols et d'hôtels toutes les 2h depuis 8 aéroports français.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A8.966 8.966 0 013 12c0-1.777.515-3.435 1.404-4.832" />
                  </svg>
                ),
                color: "from-cyan-500 to-blue-500",
              },
              {
                n: "2",
                t: "Détection d'anomalies",
                d: "Chaque prix est comparé à la moyenne 30 jours. Seules les baisses de +40% sont retenues et scorées.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
                  </svg>
                ),
                color: "from-amber-400 to-orange-500",
              },
              {
                n: "3",
                t: "Alerte Telegram",
                d: "Dès qu'un deal est qualifié, vous recevez une alerte détaillée avec description et lien de réservation.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                ),
                color: "from-emerald-400 to-cyan-500",
              },
            ].map((s, i) => (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="bg-white rounded-2xl p-8 border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${s.color} flex items-center justify-center text-white mb-5 shadow-lg`}>
                  {s.icon}
                </div>
                <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-[11px] font-bold text-gray-400 mb-3">{s.n}</div>
                <h3 className="font-semibold text-[17px] mb-2">{s.t}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{s.d}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DESTINATIONS ── */}
      <section id="destinations" className="py-12 md:py-24">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="text-center mb-12">
            <div className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2">Europe, Maghreb & plus</div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[36px] mb-3">
              Destinations populaires
            </h2>
            <p className="text-gray-400 max-w-md mx-auto text-[15px]">
              Explorez les destinations les plus recherchées avec les meilleurs deals du moment.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {destinations.map((d, i) => (
              <motion.div
                key={d.name}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="group relative aspect-[3/2] rounded-2xl overflow-hidden cursor-pointer"
              >
                <img src={d.img} alt={d.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <h3 className="text-white font-semibold text-lg drop-shadow-lg">{d.name}</h3>
                  <p className="text-white/70 text-sm">{d.deals} deals disponibles</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AIRPORTS ── */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 md:px-5 text-center">
          <h3 className="font-[family-name:var(--font-dm-serif)] text-[22px] mb-4">Départs couverts</h3>
          <div className="flex flex-wrap justify-center gap-2">
            {airports.map((a) => (
              <span key={a} className="px-4 py-2 rounded-full bg-white border border-gray-100 text-sm text-gray-600 shadow-sm">
                ✈️ {a}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── TELEGRAM PREVIEW ── */}
      <section className="py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
            <div>
              <div className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2">Alertes intelligentes</div>
              <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[34px] mb-4">
                Des deals détaillés, directement sur Telegram
              </h2>
              <p className="text-gray-500 leading-relaxed mb-6">
                Chaque deal est analysé et accompagné d'une description attractive,
                explique pourquoi c'est une bonne affaire et vous donne un conseil de réservation.
              </p>
              <ul className="space-y-3 text-sm text-gray-600">
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-cyan-100 text-cyan-600 flex items-center justify-center shrink-0 mt-0.5 text-xs">✓</span>
                  Alertes instantanées pour les meilleurs deals (score ≥ 70)
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-cyan-100 text-cyan-600 flex items-center justify-center shrink-0 mt-0.5 text-xs">✓</span>
                  Digest quotidien des top 5 deals à 8h du matin
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-cyan-100 text-cyan-600 flex items-center justify-center shrink-0 mt-0.5 text-xs">✓</span>
                  Descriptions détaillées avec contexte et conseils
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-cyan-100 text-cyan-600 flex items-center justify-center shrink-0 mt-0.5 text-xs">✓</span>
                  Liens directs vers les sites de réservation
                </li>
              </ul>
            </div>

            {/* Mock Telegram message */}
            <div className="bg-[#0E1621] rounded-2xl p-6 shadow-2xl">
              <div className="flex items-center gap-3 mb-4 pb-3 border-b border-white/10">
                <img src="/globe1.png" alt="Globe Genius" className="w-10 h-10 rounded-full shrink-0 object-contain" />
                <div>
                  <div className="text-white text-sm font-semibold">Globe Genius</div>
                  <div className="text-gray-500 text-xs">bot</div>
                </div>
              </div>
              <div className="bg-[#182533] rounded-xl p-4 text-[13px] leading-relaxed">
                <p className="text-white">✈️ <strong>GLOBE GENIUS DEAL ALERT</strong></p>
                <p className="text-white mt-2">🌍 Paris → Lisbonne</p>
                <p className="text-gray-400">📅 10 – 17 mai · 7 nuits</p>
                <p className="text-gray-300 mt-3 italic">
                  Lisbonne en mai, le combo parfait : ruelles pavées d'Alfama,
                  pastéis de nata face au Tage. Le Lisboa Plaza 4⭐ est
                  idéalement placé dans le quartier de Liberdade.
                </p>
                <p className="text-white mt-3">💰 <strong>509€</strong> au lieu de 978€ · <span className="text-red-400 font-bold">-48%</span></p>
                <p className="text-gray-400 mt-1">📊 48% en dessous du prix moyen. Mai est la haute saison — ce tarif est une anomalie rare.</p>
                <p className="text-cyan-400 mt-2">💡 Réservez dans les 24h : les vols à ce prix disparaissent vite.</p>
                <p className="text-gray-500 mt-3">🎯 Score : 84/100<br />#Lisbonne #4étoiles #Mai #CoupDeCoeur</p>
                <div className="flex gap-2 mt-3">
                  <span className="text-cyan-400 text-xs underline">👉 Vol</span>
                  <span className="text-cyan-400 text-xs underline">👉 Hôtel</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-12 md:py-24 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 md:px-5">
          <div className="text-center mb-10">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[34px] mb-3">
              Questions fréquentes
            </h2>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 px-6 shadow-sm">
            {faqs.map((f, i) => (
              <FAQItem key={i} q={f.q} a={f.a} i={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-12 md:py-24">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="relative rounded-3xl overflow-hidden">
            <img
              src="https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1920&q=80"
              alt="Travel"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/60" />
            <div className="relative px-5 py-12 md:px-16 md:py-24 text-center">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-white text-[24px] md:text-[42px] mb-3 md:mb-4">
                Prêt à voyager malin ?
              </h2>
              <p className="text-white/60 mb-6 md:mb-8 max-w-md mx-auto text-sm md:text-base">
                Inscrivez-vous gratuitement et recevez les meilleurs deals directement sur Telegram.
              </p>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 bg-white text-gray-900 font-semibold px-6 py-3.5 md:px-8 md:py-4 rounded-full hover:bg-gray-100 transition-colors text-[14px] md:text-[15px] shadow-lg"
              >
                Créer mon compte gratuitement →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-gray-100 py-10">
        <div className="max-w-6xl mx-auto px-4 md:px-5">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <img src="/globe1.png" alt="Globe Genius" className="w-7 h-7 shrink-0 object-contain" />
                <span className="font-[family-name:var(--font-dm-serif)] text-[15px]">Globe Genius</span>
              </div>
              <p className="text-xs text-gray-400 max-w-xs">
                Packages voyage à prix cassés. Vols + hôtels à -40% minimum.
              </p>
            </div>
            <div className="flex gap-8 text-sm text-gray-400">
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Produit</span>
                <a href="#deals" className="hover:text-gray-600">Deals</a>
                <a href="#how" className="hover:text-gray-600">Comment ça marche</a>
                <a href="#faq" className="hover:text-gray-600">FAQ</a>
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Légal</span>
                <span className="hover:text-gray-600 cursor-pointer">Conditions</span>
                <span className="hover:text-gray-600 cursor-pointer">Confidentialité</span>
                <span className="hover:text-gray-600 cursor-pointer">Contact</span>
              </div>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-gray-100 text-xs text-gray-300 text-center">
            © 2026 Globe Genius. Tous droits réservés.
          </div>
        </div>
      </footer>

    </div>
  );
}
