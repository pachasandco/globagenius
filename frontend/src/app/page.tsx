"use client";

import { motion } from "framer-motion";
import Link from "next/link";

/* ─── DATA ─── */
const deals = [
  { id: 1, emoji: "🇵🇹", from: "Paris", to: "Lisbonne", code: "CDG → LIS", dates: "10 – 17 mai", nights: 7, hotel: "Hotel Lisboa Plaza", stars: 4.3, price: 509, was: 978, off: 48, score: 84, img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=600&q=80" },
  { id: 2, emoji: "🇪🇸", from: "Lyon", to: "Barcelone", code: "LYS → BCN", dates: "15 – 20 mai", nights: 5, hotel: "Casa Bonay", stars: 4.5, price: 320, was: 668, off: 52, score: 78, img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=600&q=80" },
  { id: 3, emoji: "🇬🇷", from: "Marseille", to: "Athenes", code: "MRS → ATH", dates: "22 – 28 mai", nights: 6, hotel: "Electra Palace", stars: 4.6, price: 445, was: 812, off: 45, score: 75, img: "https://images.unsplash.com/photo-1555993539-1732b0258235?w=600&q=80" },
  { id: 4, emoji: "🇨🇿", from: "Nice", to: "Prague", code: "NCE → PRG", dates: "18 – 22 mai", nights: 4, hotel: "Mosaic House", stars: 4.4, price: 289, was: 525, off: 45, score: 72, img: "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=600&q=80" },
];

const airports = ["Paris CDG", "Paris ORY", "Lyon", "Marseille", "Nice", "Bordeaux", "Nantes", "Toulouse"];

/* ─── COMPONENTS ─── */
function DealCard({ deal, i }: { deal: (typeof deals)[0]; i: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: i * 0.08 }}
      className="group cursor-pointer"
    >
      {/* Image */}
      <div className="relative aspect-[4/3] rounded-2xl overflow-hidden mb-3">
        <img
          src={deal.img}
          alt={deal.to}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        {/* Discount badge */}
        <div className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm text-sm font-bold px-3 py-1 rounded-full shadow-sm"
          style={{ color: "#E11D48" }}
        >
          -{deal.off}%
        </div>
        {/* Score */}
        <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm text-white text-xs font-semibold px-2.5 py-1 rounded-full">
          ★ {deal.score}/100
        </div>
      </div>

      {/* Info */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <h3 className="font-semibold text-[15px]">{deal.from} → {deal.to}</h3>
          <span className="text-xs text-gray-400">{deal.code}</span>
        </div>
        <p className="text-sm text-gray-500 mb-1">
          {deal.dates} · {deal.nights} nuits · {deal.hotel} ★ {deal.stars}
        </p>
        <div className="flex items-baseline gap-2 mt-2">
          <span className="text-lg font-bold">{deal.price} €</span>
          <span className="text-sm text-gray-400 line-through">{deal.was} €</span>
          <span className="text-xs text-gray-400">/ pers. vol + hôtel</span>
        </div>
      </div>
    </motion.div>
  );
}

/* ─── PAGE ─── */
export default function Landing() {
  return (
    <div className="min-h-screen bg-white">

      {/* ── NAV ── */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white font-bold text-sm">G</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium px-3 py-2">
              Connexion
            </Link>
            <Link href="/signup" className="text-sm font-semibold bg-[#222] text-white px-5 py-2.5 rounded-full hover:bg-black transition-colors">
              S'inscrire
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="max-w-6xl mx-auto px-5 pt-16 pb-14 md:pt-24 md:pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-2xl"
        >
          <h1 className="font-[family-name:var(--font-dm-serif)] text-[40px] md:text-[56px] leading-[1.1] tracking-tight mb-5">
            Des packages voyage
            <br />
            <span className="text-gradient">a prix casses.</span>
          </h1>
          <p className="text-gray-500 text-lg leading-relaxed mb-8 max-w-lg">
            Notre IA analyse des milliers de vols et d'hôtels chaque jour pour
            vous trouver des packages <strong className="text-gray-900">à -40% minimum</strong> sur le prix du marché.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/signup"
              className="bg-[#222] text-white font-semibold px-7 py-3.5 rounded-full hover:bg-black transition-colors text-[15px]"
            >
              Voir les deals →
            </Link>
            <a
              href="#how"
              className="text-gray-500 font-medium px-5 py-3.5 rounded-full border border-gray-200 hover:border-gray-300 transition-colors text-[15px]"
            >
              Comment ça marche
            </a>
          </div>
        </motion.div>

        {/* Stats strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="flex flex-wrap gap-x-10 gap-y-2 mt-14 pt-8 border-t border-gray-100"
        >
          {[
            ["2 340+", "vols analysés / jour"],
            ["47", "deals actifs"],
            ["-48%", "meilleur deal actuel"],
            ["8", "aéroports couverts"],
          ].map(([val, label]) => (
            <div key={label} className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tracking-tight">{val}</span>
              <span className="text-sm text-gray-400">{label}</span>
            </div>
          ))}
        </motion.div>
      </section>

      {/* ── DEALS ── */}
      <section id="deals" className="bg-gray-50 py-14 md:py-20">
        <div className="max-w-6xl mx-auto px-5">
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[34px] mb-1">
                Deals du moment
              </h2>
              <p className="text-gray-400 text-sm">
                Mis à jour il y a 23 min · prix vérifiés
              </p>
            </div>
            <Link href="/signup" className="text-sm font-semibold text-cyan-600 hover:underline hidden sm:block">
              Tout voir →
            </Link>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {deals.map((d, i) => (
              <DealCard key={d.id} deal={d} i={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how" className="py-14 md:py-20">
        <div className="max-w-6xl mx-auto px-5">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[34px] text-center mb-12">
            Comment ça marche
          </h2>

          <div className="grid md:grid-cols-3 gap-10">
            {[
              { n: "1", icon: "🔍", t: "Scan permanent", d: "Notre pipeline analyse des milliers de vols et d'hôtels toutes les 2h depuis 8 aéroports français." },
              { n: "2", icon: "📊", t: "Détection d'anomalies", d: "Chaque prix est comparé à la moyenne des 30 derniers jours. On ne retient que les baisses de +40%." },
              { n: "3", icon: "🔔", t: "Alerte instantanée", d: "Dès qu'un package est qualifié, vous recevez une alerte Telegram avec le lien de réservation." },
            ].map((s, i) => (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="text-center"
              >
                <div className="text-4xl mb-4">{s.icon}</div>
                <div className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-xs font-bold text-gray-500 mb-3">{s.n}</div>
                <h3 className="font-semibold text-[17px] mb-2">{s.t}</h3>
                <p className="text-sm text-gray-400 leading-relaxed max-w-xs mx-auto">{s.d}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AIRPORTS ── */}
      <section className="border-t border-gray-100 py-12">
        <div className="max-w-6xl mx-auto px-5 text-center">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-[24px] mb-2">Départs couverts</h2>
          <p className="text-sm text-gray-400 mb-6">8 aéroports français surveillés en continu</p>
          <div className="flex flex-wrap justify-center gap-2">
            {airports.map((a) => (
              <span key={a} className="px-4 py-2 rounded-full bg-gray-50 border border-gray-100 text-sm text-gray-600">
                ✈️ {a}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="py-14 md:py-20">
        <div className="max-w-6xl mx-auto px-5">
          <div className="bg-[#222] rounded-3xl px-8 py-14 md:px-16 md:py-20 text-center">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-white text-[28px] md:text-[40px] mb-3">
              Prêt à voyager malin ?
            </h2>
            <p className="text-gray-400 text-sm mb-8 max-w-sm mx-auto">
              Inscrivez-vous gratuitement et recevez les meilleurs deals sur Telegram. Sans engagement.
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 bg-white text-[#222] font-semibold px-8 py-3.5 rounded-full hover:bg-gray-100 transition-colors text-[15px]"
            >
              Créer mon compte →
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-6xl mx-auto px-5 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white text-[8px] font-bold">G</div>
            <span>Globe Genius © 2026</span>
          </div>
          <div className="flex gap-5">
            <span className="hover:text-gray-600 cursor-pointer">Conditions</span>
            <span className="hover:text-gray-600 cursor-pointer">Confidentialité</span>
            <span className="hover:text-gray-600 cursor-pointer">Contact</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
