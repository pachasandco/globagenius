"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFlightDeals, type FlightDeal } from "@/lib/api";

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
  AGP: { img: "https://images.unsplash.com/photo-1592820685916-2c1a50e5cf28?w=800&q=80", flag: "🇪🇸", name: "Malaga" },
  PMI: { img: "https://images.unsplash.com/photo-1575375082828-8d1e2c5d7b06?w=800&q=80", flag: "🇪🇸", name: "Majorque" },
  IBZ: { img: "https://images.unsplash.com/photo-1534258936925-c58bed479fcb?w=800&q=80", flag: "🇪🇸", name: "Ibiza" },
  VLC: { img: "https://images.unsplash.com/photo-1599486761929-c5cd9f9b3a9f?w=800&q=80", flag: "🇪🇸", name: "Valence" },
  SVQ: { img: "https://images.unsplash.com/photo-1515443961218-a51367888e4b?w=800&q=80", flag: "🇪🇸", name: "Séville" },
  ALC: { img: "https://images.unsplash.com/photo-1592820685916-2c1a50e5cf28?w=800&q=80", flag: "🇪🇸", name: "Alicante" },
  // Italie
  FCO: { img: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800&q=80", flag: "🇮🇹", name: "Rome" },
  NAP: { img: "https://images.unsplash.com/photo-1547595628-c61a29f496f0?w=800&q=80", flag: "🇮🇹", name: "Naples" },
  VCE: { img: "https://images.unsplash.com/photo-1534113416831-ed75ddca41c0?w=800&q=80", flag: "🇮🇹", name: "Venise" },
  MXP: { img: "https://images.unsplash.com/photo-1520440229-6469a149ac59?w=800&q=80", flag: "🇮🇹", name: "Milan" },
  BLQ: { img: "https://images.unsplash.com/photo-1564420228450-d5b02e590fb8?w=800&q=80", flag: "🇮🇹", name: "Bologne" },
  CTA: { img: "https://images.unsplash.com/photo-1523531294919-4bcd7c65ef41?w=800&q=80", flag: "🇮🇹", name: "Catane" },
  CAG: { img: "https://images.unsplash.com/photo-1523531294919-4bcd7c65ef41?w=800&q=80", flag: "🇮🇹", name: "Cagliari" },
  OLB: { img: "https://images.unsplash.com/photo-1523531294919-4bcd7c65ef41?w=800&q=80", flag: "🇮🇹", name: "Olbia" },
  BRI: { img: "https://images.unsplash.com/photo-1523531294919-4bcd7c65ef41?w=800&q=80", flag: "🇮🇹", name: "Bari" },
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
  BER: { img: "https://images.unsplash.com/photo-1587330979470-3016b6702d89?w=800&q=80", flag: "🇩🇪", name: "Berlin" },
  EDI: { img: "https://images.unsplash.com/photo-1506377585622-bedcbb027afc?w=800&q=80", flag: "🇬🇧", name: "Édimbourg" },
  DUB: { img: "https://images.unsplash.com/photo-1518005020951-eccb494ad742?w=800&q=80", flag: "🇮🇪", name: "Dublin" },
  CPH: { img: "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=800&q=80", flag: "🇩🇰", name: "Copenhague" },
  HEL: { img: "https://images.unsplash.com/photo-1538332576228-eb5b4c4de6f5?w=800&q=80", flag: "🇫🇮", name: "Helsinki" },
  OSL: { img: "https://images.unsplash.com/photo-1502781252888-9143f38c5269?w=800&q=80", flag: "🇳🇴", name: "Oslo" },
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
  SSH: { img: "https://images.unsplash.com/photo-1539768942893-daf53e736b68?w=800&q=80", flag: "🇪🇬", name: "Charm el-Cheikh" },
  HRG: { img: "https://images.unsplash.com/photo-1539768942893-daf53e736b68?w=800&q=80", flag: "🇪🇬", name: "Hurghada" },
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
  BOG: { img: "https://images.unsplash.com/photo-1568635773674-08e1e25f3e86?w=800&q=80", flag: "🇨🇴", name: "Bogota" },
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

// Fallback = generic aerial travel photo (not champagne!)
const DEFAULT_DESTINATION_IMAGE = "https://images.unsplash.com/photo-1436491865332-7a61a109db05?w=800&q=80";

function destinationMeta(code: string) {
  return DESTINATION_IMAGES[code] || { img: DEFAULT_DESTINATION_IMAGE, flag: "✈️", name: code };
}

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
  { q: "Comment sont détectés les deals ?", a: "Notre pipeline scanne les prix des vols aller-retour toutes les 2 heures sur les 8 aéroports français couverts. Chaque prix est comparé à la médiane des 30 derniers jours sur la même route et la même durée de séjour (weekend, semaine, vacances longues). Seuls les vols avec une remise statistiquement anormale (minimum -20%) et confirmés en temps réel sont retenus." },
  { q: "Est-ce que les prix affichés sont fiables ?", a: "Oui. Juste avant chaque alerte, le prix est revérifié en direct contre l'API Aviasales/Travelpayouts. Si le vol a disparu ou que le prix a augmenté de plus de 5%, l'alerte est annulée. Les liens pointent directement vers les pages de réservation Aviasales." },
  { q: "Quelle est la différence entre Gratuit et Premium ?", a: "Gratuit : alertes pour les vols avec -20% à -39% de remise, visibles sur le site. Premium : accès aux deals les plus puissants (-40% et plus, incluant les erreurs de prix), alertes Telegram temps réel, packages vol+hôtel quand disponibles." },
  { q: "Comment recevoir les alertes ?", a: "Après inscription, connectez votre compte Telegram via l'onboarding. Vous recevrez les alertes dès qu'un deal correspond à votre aéroport de départ, envoyées au maximum 2 heures après la détection d'une nouvelle anomalie de prix." },
  { q: "Combien ça coûte ?", a: "La formule Gratuite permet de voir tous les deals -20% à -39% sur le site, sans limite. La formule Premium (2,99€/mois) donne accès aux deals -40% et plus et aux alertes Telegram prioritaires. Pas de période d'essai : la formule gratuite sert à découvrir le produit." },
  { q: "Quels aéroports sont couverts ?", a: "8 aéroports français : Paris CDG, Paris Orly, Lyon, Marseille, Nice, Bordeaux, Nantes et Toulouse. Les long-courriers sont scrapés uniquement depuis CDG. D'autres aéroports seront ajoutés selon la demande." },
  { q: "Quelle durée de séjour ?", a: "De 1 à 12 jours — du weekend prolongé aux vacances de deux semaines. Les séjours très longs sont exclus car ils suivent une autre logique tarifaire." },
];

/* ─── COMPONENTS ─── */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffMin = Math.round((now - then) / 60000);
  if (diffMin < 60) return `il y a ${diffMin} min`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `il y a ${diffH} h`;
  const diffD = Math.round(diffH / 24);
  return `il y a ${diffD} j`;
}

function LandingDealCard({ deal, i }: { deal: FlightDeal; i: number }) {
  const meta = destinationMeta(deal.destination);
  const days = deal.trip_duration_days ?? Math.round(
    (new Date(deal.return_date).getTime() - new Date(deal.departure_date).getTime()) / 86400000
  );
  const dep = new Date(deal.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const ret = new Date(deal.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const stopsLabel = deal.stops === 0 ? "Direct" : `${deal.stops} escale${deal.stops > 1 ? "s" : ""}`;
  const discount = Math.round(deal.discount_pct);
  const isPremium = deal.tier === "premium";
  const locked = deal.locked || deal.price === null || deal.baseline_price === null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: i * 0.06 }}
      className="group cursor-pointer"
    >
      <div className="relative bg-[#FFFEF9] rounded-2xl border border-[#F0E6D8] group-hover:border-[#FF6B47] shadow-[0_4px_16px_rgba(10,31,61,0.04)] group-hover:shadow-[0_12px_32px_rgba(255,107,71,0.12)] transition-all duration-300 overflow-hidden">
        {/* Image header with photo overlay (preserved black gradient for image legibility) */}
        <div className="relative aspect-[4/3] overflow-hidden">
          <img
            src={meta.img}
            alt={meta.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

          {/* Savings sticker coral, top-right, rotated */}
          <div
            className="absolute top-3 right-3 w-12 h-12 rounded-full bg-[#FF6B47] text-white flex items-center justify-center font-bold text-xs shadow-[0_6px_16px_rgba(255,107,71,0.4)]"
            style={{ transform: "rotate(-8deg)" }}
          >
            -{discount}%
          </div>

          {/* Premium badge top-left */}
          {isPremium && (
            <div className="absolute top-3 left-3 bg-[#FFC940] text-[#0A1F3D] text-[10px] font-bold px-2 py-0.5 rounded-full">
              PREMIUM
            </div>
          )}

          {/* Relative time bottom-right (on the image) */}
          <div className="absolute bottom-3 right-3 bg-[#FFFEF9]/90 backdrop-blur-sm text-[10px] font-semibold px-2 py-1 rounded-full text-[#0A1F3D]/70">
            {relativeTime(deal.created_at)}
          </div>

          {/* Route label bottom-left (on the image) */}
          <div className="absolute bottom-3 left-3 right-16">
            <div className="text-white font-semibold text-base drop-shadow-lg">
              {meta.flag} {deal.origin} → {deal.destination}
            </div>
            <div className="text-white/80 text-xs">
              {dep} – {ret} · {days} jour{days > 1 ? "s" : ""}
            </div>
          </div>
        </div>

        {/* Body under image */}
        <div className="p-4">
          <div className="flex items-center gap-2 text-xs text-[#0A1F3D]/60 mb-2">
            <span>✈️ {deal.airline || "Compagnie"}</span>
            <span>·</span>
            <span>{stopsLabel}</span>
          </div>
          {locked ? (
            <div className="flex items-baseline gap-2 select-none">
              <span className="text-xl font-bold blur-sm text-[#0A1F3D]/30">••• €</span>
              <span className="text-xs text-[#0A1F3D]/40 ml-auto">Connectez-vous</span>
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-[#0A1F3D]">{Math.round(deal.price as number)} €</span>
              <span className="text-sm text-[#0A1F3D]/40 line-through">{Math.round(deal.baseline_price as number)} €</span>
              <span className="text-[10px] text-[#0A1F3D]/40 ml-auto">aller-retour</span>
            </div>
          )}
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

/* ─── TELEGRAM HERO MOCKUP ─── */
const FALLBACK_DEALS_HERO = [
  { origin: "CDG", destination: "LIS", destCity: "LISBONNE", departure_date: "2026-09-01", return_date: "2026-09-10", price: 89, baseline_price: 210, discount_pct: 58 },
  { origin: "CDG", destination: "BCN", destCity: "BARCELONE", departure_date: "2026-10-15", return_date: "2026-10-22", price: 95, baseline_price: 180, discount_pct: 47 },
  { origin: "CDG", destination: "RAK", destCity: "MARRAKECH", departure_date: "2026-11-05", return_date: "2026-11-12", price: 98, baseline_price: 240, discount_pct: 59 },
];

function formatShortDateFr(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function computeHeroDays(dep: string, ret: string): number {
  return Math.round((new Date(ret).getTime() - new Date(dep).getTime()) / 86400000);
}

function TelegramHeroMockup({ deals }: { deals: FlightDeal[] }) {
  const items = deals && deals.length >= 3
    ? deals.slice(0, 3).map(d => ({
        origin: d.origin,
        destination: d.destination,
        destCity: (destinationMeta(d.destination).name || d.destination).toUpperCase(),
        departure_date: d.departure_date,
        return_date: d.return_date,
        price: d.price ?? 0,
        baseline_price: d.baseline_price ?? 0,
        discount_pct: d.discount_pct,
      }))
    : FALLBACK_DEALS_HERO;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="relative"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 1.8, type: "spring", stiffness: 200 }}
        className="absolute -top-3 -right-3 bg-[#FFC940] text-[#0A1F3D] text-xs font-bold px-3 py-1.5 rounded-full shadow-[0_8px_20px_rgba(255,201,64,0.4)] z-10"
      >
        ⚡ Temps réel
      </motion.div>

      <div className="bg-[#FFFEF9] rounded-3xl border border-[#F0E6D8] shadow-[0_24px_48px_rgba(10,31,61,0.08)] overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#F0E6D8] bg-[#FFF8F0]">
          <div className="w-10 h-10 rounded-full bg-[#FF6B47] flex items-center justify-center">
            <img src="/globe1.png" alt="" className="w-6 h-6 object-contain" />
          </div>
          <div className="flex-1">
            <div className="font-semibold text-[14px] text-[#0A1F3D] leading-none mb-1">Globe Genius Bot</div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16A34A]" />
              <span className="text-[11px] text-[#16A34A]">en ligne</span>
            </div>
          </div>
        </div>

        <div className="p-4 space-y-3 max-h-[460px] overflow-hidden">
          {items.map((deal, i) => {
            const badge = deal.discount_pct >= 60 ? "🔴" : deal.discount_pct >= 30 ? "🟠" : "🟡";
            return (
              <motion.div
                key={`hero-${deal.destination}-${i}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.6 + i * 0.6 }}
                className="bg-[#FFF8F0] rounded-2xl p-3 border border-[#F0E6D8] max-w-[94%]"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-sm">{badge}</span>
                  <span className="font-bold text-[13px] text-[#0A1F3D] uppercase tracking-tight">{deal.destCity}</span>
                </div>
                <div className="text-[11px] text-[#0A1F3D]/60 mb-1">✈️ {deal.origin} → {deal.destination}</div>
                <div className="text-[11px] text-[#0A1F3D]/60 mb-2">
                  📅 {formatShortDateFr(deal.departure_date)} - {formatShortDateFr(deal.return_date)} · {computeHeroDays(deal.departure_date, deal.return_date)}j
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-base font-bold text-[#FF6B47]">{deal.price ? `${Math.round(deal.price)}€` : "•••€"}</span>
                  {deal.baseline_price > 0 && (
                    <span className="text-[11px] text-[#0A1F3D]/40 line-through">{Math.round(deal.baseline_price)}€</span>
                  )}
                  <span className="ml-auto text-[11px] font-bold text-[#FF6B47] bg-[#FFF1EC] px-2 py-0.5 rounded-full">
                    -{Math.round(deal.discount_pct)}%
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
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
    "Globe Genius détecte les vols aller-retour à prix anormalement bas sur les 8 aéroports français. Alertes Telegram dès qu'une anomalie est confirmée.",
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
    "Deals vols à prix cassés. Vols aller-retour avec anomalies de prix confirmées, alertes Telegram.",
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
  const [recentDeals, setRecentDeals] = useState<FlightDeal[]>([]);
  const [destFilter, setDestFilter] = useState<string>("all");

  const availableDests = Array.from(new Set(recentDeals.map(d => d.destination)));
  const filteredDeals = destFilter === "all" ? recentDeals : recentDeals.filter(d => d.destination === destFilter);
  const [dealsUpdatedAt, setDealsUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const token = localStorage.getItem("gg_token");
    if (userId && token) {
      router.replace("/home");
    }
  }, [router]);

  useEffect(() => {
    // Fetch live deals as social proof. Anonymous call → backend returns
    // route/dates/airline/discount but locks price/baseline/source_url.
    let cancelled = false;
    async function load() {
      try {
        const [freeRes, premiumRes] = await Promise.allSettled([
          getFlightDeals("free", 6),
          getFlightDeals("premium", 6),
        ]);
        const all: FlightDeal[] = [];
        if (freeRes.status === "fulfilled") all.push(...(freeRes.value.items || []));
        if (premiumRes.status === "fulfilled") all.push(...(premiumRes.value.items || []));
        // Sort by created_at desc, take 6 most recent across both tiers
        all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        if (!cancelled && all.length > 0) {
          setRecentDeals(all.slice(0, 6));
          setDealsUpdatedAt(all[0].created_at);
        }
      } catch { /* keep empty, section will hide */ }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="min-h-screen bg-[#FFF8F0]">

      {/* ── JSON-LD STRUCTURED DATA ── */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />

      {/* ── NAV ── */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-end gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-10 h-10 shrink-0 object-contain" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">Globe Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-500">
            <a href="#deals" className="hover:text-gray-900 transition-colors">Deals</a>
            <a href="#how" className="hover:text-gray-900 transition-colors">Comment ça marche</a>
            <Link href="/articles" className="hover:text-gray-900 transition-colors">Guides</Link>
            <a href="#destinations" className="hover:text-gray-900 transition-colors">Destinations</a>
            <a href="#faq" className="hover:text-gray-900 transition-colors">FAQ</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium px-2.5 py-2 md:px-3">
              Connexion
            </Link>
            <Link href="/signup" className="text-sm font-semibold bg-[#FF6B47] hover:bg-[#E55A38] text-white px-4 py-2 md:px-5 md:py-2.5 rounded-full transition-all">
              S'inscrire
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="bg-[#FFF8F0]">
        <div className="max-w-6xl mx-auto px-4 md:px-5 py-16 md:py-24 lg:py-28">
          <div className="grid md:grid-cols-[1.3fr_1fr] gap-10 md:gap-12 lg:gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-2 bg-[#FFFEF9] border border-[#F0E6D8] rounded-full px-3.5 py-1.5 mb-6">
                <span className="w-2 h-2 rounded-full bg-[#16A34A] animate-pulse" />
                <span className="text-xs font-semibold text-[#0A1F3D]">
                  Pipeline actif · 2 340+ vols analysés aujourd&apos;hui
                </span>
              </div>

              <h1 className="font-[family-name:var(--font-dm-serif)] text-[40px] md:text-[56px] lg:text-[72px] leading-[1.02] tracking-tight mb-5 text-[#0A1F3D]">
                Des vols<br />à prix cassés.
              </h1>

              <p className="text-[#0A1F3D]/70 text-base md:text-lg leading-relaxed mb-8 max-w-lg">
                Lisbonne à <span className="bg-[#FFF1EC] text-[#FF6B47] font-semibold px-1.5 rounded">89€</span>,
                Marrakech à <span className="bg-[#FFF1EC] text-[#FF6B47] font-semibold px-1.5 rounded">98€</span>,
                Athènes à <span className="bg-[#FFF1EC] text-[#FF6B47] font-semibold px-1.5 rounded">156€</span>.
                Des <strong className="text-[#0A1F3D]">prix anormalement bas</strong>, vérifiés,
                qui apparaissent parfois quelques heures avant de disparaître.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <Link
                  href="/signup"
                  className="bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-8 py-4 rounded-full transition-all text-[15px] shadow-[0_8px_24px_rgba(255,107,71,0.25)] hover:shadow-[0_12px_32px_rgba(255,107,71,0.35)] text-center"
                >
                  Découvrir les deals →
                </Link>
                <a
                  href="#how"
                  className="text-[#0A1F3D] font-medium px-6 py-4 rounded-full border-2 border-[#0A1F3D]/10 hover:border-[#0A1F3D]/20 hover:bg-[#FFFEF9] transition-all text-[15px] text-center"
                >
                  Comment ça marche
                </a>
              </div>
            </motion.div>

            <TelegramHeroMockup deals={recentDeals} />
          </div>
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

      {/* ── TELEGRAM PREVIEW ── */}
      <section className="py-12 md:py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4 md:px-5 grid md:grid-cols-2 gap-10 md:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <div className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2">
              Notification Telegram
            </div>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[36px] mb-4">
              Une alerte. Vous partez.
            </h2>
            <p className="text-gray-600 text-base leading-relaxed mb-6">
              Pas d&apos;email perdu dans un dossier promo, pas de notif push qui s&apos;empile.
              Un message Telegram simple, lisible en 5 secondes, avec le prix, la baseline,
              et le lien direct vers la réservation. Vous décidez en moins d&apos;une minute.
            </p>
            <ul className="space-y-3 text-sm text-gray-600">
              <li className="flex items-start gap-3">
                <span className="text-emerald-500 mt-0.5">✓</span>
                <span>Prix vérifié en direct juste avant l&apos;envoi</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-emerald-500 mt-0.5">✓</span>
                <span>Comparaison à la médiane historique sur la même route</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-emerald-500 mt-0.5">✓</span>
                <span>Lien de réservation direct, vous quittez Telegram et c&apos;est réglé</span>
              </li>
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="flex justify-center"
          >
            {/* Telegram message mockup */}
            <div className="w-full max-w-sm bg-[#212d3b] rounded-2xl shadow-2xl shadow-black/20 overflow-hidden border border-gray-800">
              {/* Bot identity */}
              <div className="px-5 pt-5 pb-4 border-b border-gray-700/50">
                <div className="text-white font-semibold text-[15px]">Globe Genius</div>
                <div className="text-gray-400 text-xs">bot</div>
              </div>

              {/* Message bubble */}
              <div className="p-5">
                <div className="bg-[#2b3a4d] rounded-2xl rounded-tl-sm p-4 text-[13px] leading-relaxed">
                  <div className="text-orange-400 font-bold mb-3">🟠 PROMO FLASH</div>
                  <div className="text-gray-100 space-y-1.5">
                    <div>🌍 <span className="text-white">Paris → Lisbonne</span></div>
                    <div>📅 12 mai – 19 mai</div>
                    <div>🗓 7 jours sur place</div>
                    <div>✈️ TAP Portugal</div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-white/10">
                    <div className="text-white font-semibold">
                      💰 89€ <span className="text-gray-400 font-normal">au lieu de ~181€</span>
                      <span className="text-orange-400 ml-2">· 🔥 -51%</span>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-white/10">
                    <div className="text-cyan-400 underline">👉 Réserver sur Aviasales</div>
                  </div>
                  <div className="text-right text-gray-500 text-[11px] mt-2">14:23</div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── DEALS ── */}
      {recentDeals.length > 0 && (
        <section id="deals" className="py-12 md:py-24">
          <div className="max-w-6xl mx-auto px-4 md:px-5">
            <div className="flex items-end justify-between mb-6">
              <div>
                <motion.div
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2"
                >
                  {dealsUpdatedAt ? `Dernier deal détecté ${relativeTime(dealsUpdatedAt)}` : "Mis à jour en continu"}
                </motion.div>
                <h2 className="font-[family-name:var(--font-dm-serif)] text-[28px] md:text-[36px]">
                  Deals récents
                </h2>
                <p className="text-gray-500 text-sm mt-2 max-w-lg">
                  Vrais deals détectés ces derniers jours. Créez un compte pour voir le prix exact et accéder au lien de réservation.
                </p>
              </div>
              <Link href="/signup" className="text-sm font-semibold text-cyan-600 hover:underline hidden sm:block">
                Créer un compte →
              </Link>
            </div>

            {/* Destination filter pills */}
            <div className="flex gap-2 mb-8 overflow-x-auto pb-2 scrollbar-hide">
              <button
                onClick={() => setDestFilter("all")}
                className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-all border-2"
                style={{
                  borderColor: destFilter === "all" ? "#FF6B47" : "#F0E6D8",
                  background: destFilter === "all" ? "#FF6B47" : "#FFFEF9",
                  color: destFilter === "all" ? "#fff" : "#0A1F3D",
                }}
              >
                Toutes
              </button>
              {availableDests.map((code) => {
                const meta = destinationMeta(code);
                return (
                  <button
                    key={code}
                    onClick={() => setDestFilter(code)}
                    className="shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition-all border-2"
                    style={{
                      borderColor: destFilter === code ? "#FF6B47" : "#F0E6D8",
                      background: destFilter === code ? "#FF6B47" : "#FFFEF9",
                      color: destFilter === code ? "#fff" : "#0A1F3D",
                    }}
                  >
                    {meta.flag} {meta.name}
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-7">
              {filteredDeals.map((d, i) => (
                <LandingDealCard key={d.id} deal={d} i={i} />
              ))}
            </div>
          </div>
        </section>
      )}

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
                d: "Notre pipeline analyse les prix des vols aller-retour toutes les 2h depuis les 8 aéroports français couverts.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A8.966 8.966 0 013 12c0-1.777.515-3.435 1.404-4.832" />
                  </svg>
                ),
                color: "#06B6D4",
              },
              {
                n: "2",
                t: "Détection d'anomalies",
                d: "Chaque prix est comparé à la médiane des 30 derniers jours sur la même route et la même durée de séjour. Seules les anomalies statistiquement significatives (minimum -20%) sont qualifiées.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
                  </svg>
                ),
                color: "#FF6B47",
              },
              {
                n: "3",
                t: "Alerte Telegram",
                d: "Avant chaque envoi, le prix est revérifié en direct. Dès qu'un deal est confirmé, vous recevez une alerte avec le prix, la baseline et le lien de réservation.",
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                ),
                color: "#FFC940",
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
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center text-white mb-5 shadow-lg"
                  style={{ background: s.color }}
                >
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
              src="https://images.unsplash.com/photo-1488085061387-422e29b40080?w=1920&q=80"
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
              <div className="flex items-end gap-2 mb-2">
                <img src="/globe1.png" alt="Globe Genius" className="w-9 h-9 shrink-0 object-contain" />
                <span className="font-[family-name:var(--font-dm-serif)] text-[15px] leading-none">Globe Genius</span>
              </div>
              <p className="text-xs text-gray-400 max-w-xs">
                Vols à prix cassés. Anomalies de prix détectées, alertes Telegram temps réel.
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
