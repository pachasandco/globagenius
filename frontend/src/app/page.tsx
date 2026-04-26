"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";

/* ─── DESTINATION IMAGES ───
   Mapped by IATA code so that live deals fetched from /api/packages can
   pick a relevant cover photo without depending on the backend. */
const DESTINATION_IMAGES: Record<string, { img: string; flag: string; name: string }> = {
  // Portugal
  LIS: { img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=800&q=80", flag: "🇵🇹", name: "Lisbonne" },
  OPO: { img: "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800&q=80", flag: "🇵🇹", name: "Porto" },
  FAO: { img: "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80", flag: "🇵🇹", name: "Faro" },
  FNC: { img: "https://images.unsplash.com/photo-1590077428593-a55bb07c4665?w=800&q=80", flag: "🇵🇹", name: "Madère" },
  PDL: { img: "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=800&q=80", flag: "🇵🇹", name: "Açores" },
  // Espagne
  BCN: { img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800&q=80", flag: "🇪🇸", name: "Barcelone" },
  MAD: { img: "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=800&q=80", flag: "🇪🇸", name: "Madrid" },
  AGP: { img: "https://images.unsplash.com/photo-1509840841025-9088ba78a826?w=800&q=80", flag: "🇪🇸", name: "Malaga" },
  PMI: { img: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80", flag: "🇪🇸", name: "Majorque" },
  IBZ: { img: "https://images.unsplash.com/photo-1534258936925-c58bed479fcb?w=800&q=80", flag: "🇪🇸", name: "Ibiza" },
  VLC: { img: "https://images.unsplash.com/photo-1544531586-fde5298cdd40?w=800&q=80", flag: "🇪🇸", name: "Valence" },
  SVQ: { img: "https://images.unsplash.com/photo-1515443961218-a51367888e4b?w=800&q=80", flag: "🇪🇸", name: "Séville" },
  ALC: { img: "https://images.unsplash.com/photo-1509840841025-9088ba78a826?w=800&q=80", flag: "🇪🇸", name: "Alicante" },
  // Italie
  FCO: { img: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800&q=80", flag: "🇮🇹", name: "Rome" },
  NAP: { img: "https://images.unsplash.com/photo-1547595628-c61a29f496f0?w=800&q=80", flag: "🇮🇹", name: "Naples" },
  VCE: { img: "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?w=800&q=80", flag: "🇮🇹", name: "Venise" },
  MXP: { img: "https://images.unsplash.com/photo-1520440229-6469a149ac59?w=800&q=80", flag: "🇮🇹", name: "Milan" },
  BLQ: { img: "https://images.unsplash.com/photo-1598135753163-6167c1a1ad65?w=800&q=80", flag: "🇮🇹", name: "Bologne" },
  CTA: { img: "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800&q=80", flag: "🇮🇹", name: "Catane" },
  CAG: { img: "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800&q=80", flag: "🇮🇹", name: "Cagliari" },
  OLB: { img: "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800&q=80", flag: "🇮🇹", name: "Olbia" },
  BRI: { img: "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800&q=80", flag: "🇮🇹", name: "Bari" },
  // Grèce
  ATH: { img: "https://images.unsplash.com/photo-1555993539-1732b0258235?w=800&q=80", flag: "🇬🇷", name: "Athènes" },
  HER: { img: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&q=80", flag: "🇬🇷", name: "Crète" },
  JTR: { img: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&q=80", flag: "🇬🇷", name: "Santorin" },
  JMK: { img: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&q=80", flag: "🇬🇷", name: "Mykonos" },
  RHO: { img: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&q=80", flag: "🇬🇷", name: "Rhodes" },
  CFU: { img: "https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=800&q=80", flag: "🇬🇷", name: "Corfou" },
  SKG: { img: "https://images.unsplash.com/photo-1555993539-1732b0258235?w=800&q=80", flag: "🇬🇷", name: "Thessalonique" },
  // Europe centrale
  PRG: { img: "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=800&q=80", flag: "🇨🇿", name: "Prague" },
  BUD: { img: "https://images.unsplash.com/photo-1551867633-194f125bddfa?w=800&q=80", flag: "🇭🇺", name: "Budapest" },
  VIE: { img: "https://images.unsplash.com/photo-1516550893923-42d28e5677af?w=800&q=80", flag: "🇦🇹", name: "Vienne" },
  KRK: { img: "https://images.unsplash.com/photo-1519197924294-4ba991a11128?w=800&q=80", flag: "🇵🇱", name: "Cracovie" },
  WAW: { img: "https://images.unsplash.com/photo-1519197924294-4ba991a11128?w=800&q=80", flag: "🇵🇱", name: "Varsovie" },
  SOF: { img: "https://images.unsplash.com/photo-1520939817895-060bdaf4fe1b?w=800&q=80", flag: "🇧🇬", name: "Sofia" },
  ZAG: { img: "https://images.unsplash.com/photo-1555990793-da11153b2473?w=800&q=80", flag: "🇭🇷", name: "Zagreb" },
  // Europe du Nord & Ouest
  AMS: { img: "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=800&q=80", flag: "🇳🇱", name: "Amsterdam" },
  BER: { img: "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800&q=80", flag: "🇩🇪", name: "Berlin" },
  EDI: { img: "https://images.unsplash.com/photo-1506377585622-bedcbb027afc?w=800&q=80", flag: "🇬🇧", name: "Édimbourg" },
  DUB: { img: "https://images.unsplash.com/photo-1518005020951-eccb494ad742?w=800&q=80", flag: "🇮🇪", name: "Dublin" },
  CPH: { img: "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=800&q=80", flag: "🇩🇰", name: "Copenhague" },
  HEL: { img: "https://images.unsplash.com/photo-1538332576228-eb5b4c4de6f5?w=800&q=80", flag: "🇫🇮", name: "Helsinki" },
  OSL: { img: "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=800&q=80", flag: "🇳🇴", name: "Oslo" },
  ARN: { img: "https://images.unsplash.com/photo-1509356843151-3e7d96241e11?w=800&q=80", flag: "🇸🇪", name: "Stockholm" },
  BRU: { img: "https://images.unsplash.com/photo-1559113202-c916b8e44373?w=800&q=80", flag: "🇧🇪", name: "Bruxelles" },
  GVA: { img: "https://images.unsplash.com/photo-1504194921103-f8b80cadd5e4?w=800&q=80", flag: "🇨🇭", name: "Genève" },
  ZRH: { img: "https://images.unsplash.com/photo-1504194921103-f8b80cadd5e4?w=800&q=80", flag: "🇨🇭", name: "Zurich" },
  // Baltes
  TLL: { img: "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800&q=80", flag: "🇪🇪", name: "Tallinn" },
  RIX: { img: "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800&q=80", flag: "🇱🇻", name: "Riga" },
  VNO: { img: "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800&q=80", flag: "🇱🇹", name: "Vilnius" },
  // Turquie & Balkans
  IST: { img: "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800&q=80", flag: "🇹🇷", name: "Istanbul" },
  SAW: { img: "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800&q=80", flag: "🇹🇷", name: "Istanbul" },
  DBV: { img: "https://images.unsplash.com/photo-1555990793-da11153b2473?w=800&q=80", flag: "🇭🇷", name: "Dubrovnik" },
  SPU: { img: "https://images.unsplash.com/photo-1555990793-da11153b2473?w=800&q=80", flag: "🇭🇷", name: "Split" },
  TIV: { img: "https://images.unsplash.com/photo-1555990793-da11153b2473?w=800&q=80", flag: "🇲🇪", name: "Tivat" },
  // Maghreb & Moyen-Orient
  RAK: { img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=800&q=80", flag: "🇲🇦", name: "Marrakech" },
  CMN: { img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=800&q=80", flag: "🇲🇦", name: "Casablanca" },
  TUN: { img: "https://images.unsplash.com/photo-1605000797499-95a51c5269ae?w=800&q=80", flag: "🇹🇳", name: "Tunis" },
  CAI: { img: "https://images.unsplash.com/photo-1572252009286-268acec5ca0a?w=800&q=80", flag: "🇪🇬", name: "Le Caire" },
  SSH: { img: "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=800&q=80", flag: "🇪🇬", name: "Charm el-Cheikh" },
  HRG: { img: "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=800&q=80", flag: "🇪🇬", name: "Hurghada" },
  TLV: { img: "https://images.unsplash.com/photo-1544967082-d9d25d867d66?w=800&q=80", flag: "🇮🇱", name: "Tel Aviv" },
  DXB: { img: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800&q=80", flag: "🇦🇪", name: "Dubaï" },
  // Canaries
  TFS: { img: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80", flag: "🇪🇸", name: "Tenerife" },
  LPA: { img: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80", flag: "🇪🇸", name: "Las Palmas" },
  FUE: { img: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80", flag: "🇪🇸", name: "Fuerteventura" },
  ACE: { img: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80", flag: "🇪🇸", name: "Lanzarote" },
  // Long-courrier
  JFK: { img: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80", flag: "🇺🇸", name: "New York" },
  MIA: { img: "https://images.unsplash.com/photo-1506966953602-c20cc11f75e3?w=800&q=80", flag: "🇺🇸", name: "Miami" },
  LAX: { img: "https://images.unsplash.com/photo-1534190760961-74e8c1c5c3da?w=800&q=80", flag: "🇺🇸", name: "Los Angeles" },
  YUL: { img: "https://images.unsplash.com/photo-1519178614-68673b201f36?w=800&q=80", flag: "🇨🇦", name: "Montréal" },
  BKK: { img: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&q=80", flag: "🇹🇭", name: "Bangkok" },
  NRT: { img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80", flag: "🇯🇵", name: "Tokyo" },
  HND: { img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80", flag: "🇯🇵", name: "Tokyo" },
  ICN: { img: "https://images.unsplash.com/photo-1517154421773-0529f29ea451?w=800&q=80", flag: "🇰🇷", name: "Séoul" },
  HKG: { img: "https://images.unsplash.com/photo-1536599018102-9f803c140fc1?w=800&q=80", flag: "🇭🇰", name: "Hong Kong" },
  SIN: { img: "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=800&q=80", flag: "🇸🇬", name: "Singapour" },
  KUL: { img: "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80", flag: "🇲🇾", name: "Kuala Lumpur" },
  DEL: { img: "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800&q=80", flag: "🇮🇳", name: "Delhi" },
  BOM: { img: "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=800&q=80", flag: "🇮🇳", name: "Mumbai" },
  SYD: { img: "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=800&q=80", flag: "🇦🇺", name: "Sydney" },
  GIG: { img: "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?w=800&q=80", flag: "🇧🇷", name: "Rio" },
  EZE: { img: "https://images.unsplash.com/photo-1589909202802-8f4aadce1849?w=800&q=80", flag: "🇦🇷", name: "Buenos Aires" },
  BOG: { img: "https://images.unsplash.com/photo-1518638150340-f706e86654de?w=800&q=80", flag: "🇨🇴", name: "Bogota" },
  LIM: { img: "https://images.unsplash.com/photo-1526392060635-9d6019884377?w=800&q=80", flag: "🇵🇪", name: "Lima" },
  CUN: { img: "https://images.unsplash.com/photo-1510097467424-192d713fd8b2?w=800&q=80", flag: "🇲🇽", name: "Cancun" },
  PUJ: { img: "https://images.unsplash.com/photo-1510097467424-192d713fd8b2?w=800&q=80", flag: "🇩🇴", name: "Punta Cana" },
  CPT: { img: "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=800&q=80", flag: "🇿🇦", name: "Le Cap" },
  JNB: { img: "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=800&q=80", flag: "🇿🇦", name: "Johannesburg" },
  ZNZ: { img: "https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=800&q=80", flag: "🇹🇿", name: "Zanzibar" },
  MLE: { img: "https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=800&q=80", flag: "🇲🇻", name: "Maldives" },
  MRU: { img: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80", flag: "🇲🇺", name: "Maurice" },
  RUN: { img: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80", flag: "🇷🇪", name: "La Réunion" },
};

const DEFAULT_DESTINATION_IMAGE = "https://images.unsplash.com/photo-1500835556837-99ac94a94552?w=800&q=80";

function destinationMeta(code: string) {
  return DESTINATION_IMAGES[code] || { img: DEFAULT_DESTINATION_IMAGE, flag: "✈️", name: code };
}

/* Past deals — hardcoded examples that show the value of the service */
const PAST_DEALS = [
  { origin: "CDG", destination: "JFK", city: "New York", flag: "🇺🇸", price: 198, usual: 580, discount: 66, img: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80" },
  { origin: "CDG", destination: "BKK", city: "Bangkok", flag: "🇹🇭", price: 312, usual: 750, discount: 58, img: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=800&q=80" },
  { origin: "ORY", destination: "RAK", city: "Marrakech", flag: "🇲🇦", price: 34, usual: 120, discount: 72, img: "https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=800&q=80" },
  { origin: "LYS", destination: "LIS", city: "Lisbonne", flag: "🇵🇹", price: 48, usual: 180, discount: 73, img: "https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=800&q=80" },
  { origin: "CDG", destination: "NRT", city: "Tokyo", flag: "🇯🇵", price: 389, usual: 900, discount: 57, img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80" },
  { origin: "MRS", destination: "BCN", city: "Barcelone", flag: "🇪🇸", price: 19, usual: 85, discount: 78, img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800&q=80" },
];

const faqs = [
  { q: "Comment fonctionne Globe Genius ?", a: "On surveille en permanence les prix des vols au départ de 9 aéroports français. Dès qu\u2019on détecte une baisse de prix significative, on vous envoie une alerte sur Telegram avec tous les détails pour réserver." },
  { q: "Quelle est la différence entre Gratuit et Premium ?", a: "En Gratuit, vous recevez jusqu\u2019à 3 alertes complètes par semaine sur les deals à -40% et plus. En Premium, vous accédez à tous les deals sans limite (jusqu\u2019à -70%+), y compris les erreurs de prix des compagnies, avec prix et liens de réservation débloqués." },
  { q: "Comment fonctionne la garantie 30 jours ?", a: "Si Premium ne vous convient pas, contactez-nous dans les 30 jours suivant votre achat et on vous rembourse intégralement, sans question." },
  { q: "Les prix incluent-ils les bagages ?", a: "Les prix affichés sont ceux des compagnies aériennes. Les bagages en soute sont parfois inclus selon la compagnie et le tarif. On le précise dans chaque alerte quand l\u2019information est disponible." },
  { q: "Combien de temps entre la publication du prix et votre alerte ?", a: "Pour les vols Ryanair et Vueling au départ de Paris (CDG/ORY), on scrape les prix directement sur les APIs des compagnies toutes les 20 minutes. Dès qu\u2019une anomalie est détectée, l\u2019alerte Telegram part dans la foulée, généralement moins de 5 minutes après l\u2019apparition du deal. Pour les autres aéroports et destinations, on utilise un agrégateur de vols interrogé toutes les 2 heures." },
  { q: "Pourquoi certains deals disparaissent avant que j\u2019aie pu réserver ?", a: "Les tarifs érronés (\u00ab\u00a0erreurs de prix\u00a0\u00bb) sont des oublis de configuration des compagnies. Dès qu\u2019elles s\u2019en rendent compte, elles corrigent le tarif \u2014 parfois en quelques heures. C\u2019est pourquoi les alertes temps réel sont déterminantes : réserver dans l\u2019heure qui suit l\u2019alerte maximise vos chances d\u2019obtenir le prix affiché. Passez commande rapidement et contactez la compagnie si le tarif change avant l\u2019émission." },
];

/* ─── COMPONENTS ─── */

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

/* ─── FAQ STRUCTURED DATA (page-specific — Organization/WebSite/SoftwareApplication are in layout.tsx) ─── */
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
    <div className="min-h-screen bg-[var(--color-cream)]">

      {/* ── FAQ JSON-LD (page-specific, complements layout.tsx schemas) ── */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />

      {/* ── NAVBAR ── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 py-4 bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
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

      {/* ── HERO ── */}
      <section className="relative min-h-[480px] flex items-center overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=80"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-ink)]/90 via-[var(--color-ink)]/70 to-[var(--color-ink)]/30" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 px-6 sm:px-12 py-16 max-w-2xl"
        >
          <span className="inline-block bg-[var(--color-coral)]/20 border border-[var(--color-coral)]/40 text-[#FF9B82] px-4 py-1.5 rounded-full text-sm font-bold mb-6 backdrop-blur-sm">
            🔥 Offre printemps — Premium à 29€/an au lieu de 59€
          </span>

          <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-white leading-tight mb-4">
            Des vols à prix cassés,{" "}
            <br className="hidden sm:block" />
            détectés{" "}
            <em className="not-italic text-[var(--color-coral)]">avant tout le monde</em>.
          </h1>

          <p className="text-white/75 text-lg leading-relaxed mb-8 max-w-lg">
            On surveille tous les vols au départ de la France et on vous envoie les meilleures offres sur Telegram. Jusqu&apos;à -70% sur vos billets.
          </p>

          <Link
            href="/signup"
            className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors shadow-[0_8px_24px_rgba(255,107,71,0.3)]"
          >
            Essayer gratuitement
          </Link>
          <p className="text-white/50 text-sm mt-3">Gratuit, sans carte bancaire</p>
        </motion.div>
      </section>

      {/* ── STATS BAR ── */}
      <section className="flex flex-wrap justify-center gap-8 sm:gap-12 py-6 px-6 bg-white border-t border-[var(--color-sand)]">
        {[
          { value: "≥50%", label: "réduction minimum" },
          { value: "-70%", label: "meilleur deal détecté" },
          { value: "6×/jour", label: "scraping des prix" },
          { value: "9", label: "aéroports de départ" },
        ].map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-2xl font-extrabold text-[var(--color-ink)]">{s.value}</div>
            <div className="text-xs text-gray-400 mt-1">{s.label}</div>
          </div>
        ))}
      </section>

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
          {[
            {
              num: "1",
              title: "On surveille tous les vols au départ de la France",
              desc: "Depuis 9 aéroports français, vers le monde entier. En continu, 24h/24.",
            },
            {
              num: "2",
              title: "L\u2019algorithme détecte l\u2019anomalie de prix",
              desc: "Dès qu\u2019un tarif chute sous le prix habituel, notre système le signale. Pour Ryanair et Vueling au départ de Paris, la vérification a lieu toutes les 20 minutes.",
            },
            {
              num: "3",
              title: "Vous recevez l\u2019alerte sur Telegram",
              desc: "Prix, dates, lien direct pour réserver. L\u2019alerte arrive dans les minutes qui suivent la détection \u2014 pas le lendemain.",
            },
            {
              num: "4",
              title: "Vous réservez avant que ça remonte",
              desc: "Les erreurs de prix disparaissent souvent en quelques heures. L\u2019avance qu\u2019on vous donne, c\u2019est ça qui fait la différence.",
            },
          ].map((step, i) => (
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

      {/* ── PRICING ── */}
      <section id="tarifs" className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
          Choisissez votre formule
        </h2>
        <p className="text-center text-gray-400 text-sm mb-10">
          Un vol Premium rentabilise l&apos;abonnement dès le premier voyage.
        </p>

        <div className="flex flex-col sm:flex-row gap-6 max-w-2xl mx-auto">
          {/* Free */}
          <div className="flex-1 bg-white border border-[var(--color-sand)] rounded-2xl p-6">
            <div className="font-bold text-[var(--color-ink)] text-sm mb-1">Gratuit</div>
            <div className="text-3xl font-extrabold text-[var(--color-ink)] mb-5">0€</div>
            <div className="text-sm text-gray-500 leading-loose mb-6">
              ✓ Deals à partir de -40%<br />
              ✓ 3 alertes complètes / semaine<br />
              ✓ 9 aéroports de départ<br />
              <span className="text-gray-300">✗ Deals au-delà de -50% (masqués)</span><br />
              <span className="text-gray-300">✗ Alertes illimitées</span><br />
              <span className="text-gray-300">✗ Erreurs de prix</span>
            </div>
            <Link
              href="/signup"
              className="block text-center py-3 rounded-xl font-bold text-sm border-2 border-[var(--color-ink)] text-[var(--color-ink)] hover:bg-[var(--color-ink)] hover:text-white transition-colors"
            >
              S&apos;inscrire gratuitement
            </Link>
          </div>

          {/* Premium */}
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
              ✓ <span className="text-white">Tous les deals, jusqu&apos;à -70%</span><br />
              ✓ <span className="text-white">Erreurs de prix des compagnies</span><br />
              ✓ <span className="text-white">9 aéroports de départ</span><br />
              ✓ <span className="text-white">Alertes Telegram prioritaires</span><br />
              ✓ <span className="text-white">Garantie satisfait 30 jours</span><br />
              <span className="text-[var(--color-forest)]">= 2,42€/mois</span>
            </div>
            <Link
              href="/signup"
              className="block text-center py-3 rounded-xl font-bold text-sm bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white transition-colors"
            >
              Offre printemps -41%
            </Link>
          </div>
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

      {/* ── CTA FINAL ── */}
      <section className="py-16 px-6 sm:px-12 bg-[var(--color-ink)] text-center">
        <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-white mb-4">
          Prêt à voyager moins cher ?
        </h2>
        <p className="text-gray-400 mb-8">
          Rejoignez les voyageurs qui économisent sur chaque vol.
        </p>
        <Link
          href="/signup"
          className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors shadow-[0_8px_24px_rgba(255,107,71,0.3)]"
        >
          Commencer gratuitement
        </Link>
      </section>

      {/* ── TELEGRAM REMINDER BANNER ── */}
      <section className="py-8 px-6 sm:px-12 bg-gradient-to-r from-[#0088cc]/10 to-[#0088cc]/5 border-t border-[#0088cc]/20">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <svg className="w-12 h-12 text-[#0088cc] flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
            </svg>
            <div>
              <h3 className="text-lg font-bold text-[#0088cc] mb-1">Reçois les alertes en temps réel</h3>
              <p className="text-gray-600 text-sm">Télécharge Telegram pour être notifié instantanément de chaque incroyable deal découvert</p>
            </div>
          </div>
          <a
            href="https://telegram.org/apps"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-[#0088cc] hover:bg-[#006daa] text-white font-semibold rounded-xl transition-colors flex-shrink-0"
          >
            Télécharger Telegram
          </a>
        </div>
      </section>

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
