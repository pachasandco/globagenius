import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Wordmark } from "../../_components/Wordmark";

const AIRPORT_PAGES = {
  paris: {
    city: "Paris",
    codes: "CDG · ORY · BVA",
    promise: "Long-courriers, Europe et Méditerranée",
    copy: "Paris concentre le plus grand volume de bons plans GlobeGenius, notamment vers l’Asie, l’Amérique du Nord, l’océan Indien et les grandes villes européennes.",
    examples: ["Tokyo", "Bangkok", "New York", "Montréal", "Phuket", "Lisbonne"],
  },
  lyon: {
    city: "Lyon",
    codes: "LYS",
    promise: "Europe régulière et opportunités long-courrier",
    copy: "GlobeGenius surveille Lyon pour les baisses de prix vers l’Europe, la Méditerranée et les rares opportunités long-courrier qui méritent une alerte.",
    examples: ["Rome", "Lisbonne", "Athènes", "Marrakech", "Istanbul", "Montréal"],
  },
  marseille: {
    city: "Marseille",
    codes: "MRS",
    promise: "Europe, Méditerranée et Afrique du Nord",
    copy: "Depuis Marseille, le moteur privilégie les routes où les variations de prix sont réellement significatives plutôt que d’envoyer une longue liste de promotions ordinaires.",
    examples: ["Barcelone", "Rome", "Athènes", "Marrakech", "Tunis", "Istanbul"],
  },
  toulouse: {
    city: "Toulouse",
    codes: "TLS",
    promise: "Bons plans européens vérifiés",
    copy: "Les alertes depuis Toulouse couvrent principalement l’Europe et la Méditerranée, avec un contrôle du prix habituel propre à chaque route.",
    examples: ["Lisbonne", "Madrid", "Rome", "Athènes", "Marrakech", "Dublin"],
  },
  bordeaux: {
    city: "Bordeaux",
    codes: "BOD",
    promise: "Europe et escapades méditerranéennes",
    copy: "GlobeGenius compare les tarifs observés depuis Bordeaux à leur historique réel avant de déclencher une alerte Telegram.",
    examples: ["Lisbonne", "Porto", "Rome", "Barcelone", "Marrakech", "Athènes"],
  },
  nantes: {
    city: "Nantes",
    codes: "NTE",
    promise: "Vols européens et opportunités saisonnières",
    copy: "Depuis Nantes, le service cherche les écarts de prix réellement inhabituels, y compris sur les routes saisonnières.",
    examples: ["Lisbonne", "Rome", "Dublin", "Athènes", "Marrakech", "Barcelone"],
  },
  nice: {
    city: "Nice",
    codes: "NCE",
    promise: "Europe, Méditerranée et quelques long-courriers",
    copy: "Nice bénéficie d’une bonne couverture européenne et de certaines liaisons long-courrier que GlobeGenius surveille séparément.",
    examples: ["Rome", "Athènes", "Istanbul", "Lisbonne", "New York", "Montréal"],
  },
  "bale-mulhouse": {
    city: "Bâle-Mulhouse",
    codes: "BSL",
    promise: "Une couverture transfrontalière utile",
    copy: "Bâle-Mulhouse complète la couverture française avec de nombreuses routes européennes et des niveaux de prix parfois très différents des aéroports voisins.",
    examples: ["Lisbonne", "Rome", "Budapest", "Athènes", "Marrakech", "Istanbul"],
  },
} as const;

type AirportSlug = keyof typeof AIRPORT_PAGES;

export function generateStaticParams() {
  return Object.keys(AIRPORT_PAGES).map((airport) => ({ airport }));
}

export async function generateMetadata({ params }: { params: Promise<{ airport: string }> }): Promise<Metadata> {
  const { airport } = await params;
  const data = AIRPORT_PAGES[airport as AirportSlug];
  if (!data) return {};
  return {
    title: `Alertes vols pas chers depuis ${data.city} — GlobeGenius`,
    description: `Recevez sur Telegram les baisses de prix vérifiées depuis ${data.city}. ${data.promise}.`,
    alternates: { canonical: `https://globegenius.app/depart/${airport}` },
  };
}

export default async function AirportPage({ params }: { params: Promise<{ airport: string }> }) {
  const { airport } = await params;
  const data = AIRPORT_PAGES[airport as AirportSlug];
  if (!data) notFound();

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-5">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>
          <Link href={`/signup?utm_source=airport_page&utm_medium=seo&utm_campaign=${airport}`} className="rounded-xl bg-[#0E7490] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#0A6078]">
            Activer mes alertes
          </Link>
        </div>
      </nav>

      <main>
        <section className="bg-[#0B2A3F] px-5 py-20 text-white">
          <div className="mx-auto max-w-4xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#52C9BE]">Départ {data.codes}</p>
            <h1 className="mt-5 font-[family-name:var(--font-dm-serif)] text-4xl leading-tight sm:text-6xl">
              Les bons plans vols depuis {data.city}, vérifiés avant l’alerte.
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-white/70">{data.copy}</p>
            <Link href={`/signup?utm_source=airport_page&utm_medium=seo&utm_campaign=${airport}&utm_content=hero`} className="mt-9 inline-flex rounded-xl bg-[#FF7A59] px-7 py-4 font-bold text-white hover:bg-[#E96543]">
              Surveiller les vols depuis {data.city}
            </Link>
            <p className="mt-4 text-xs text-white/45">Compte gratuit · Telegram requis pour recevoir les alertes</p>
          </div>
        </section>

        <section className="px-5 py-16">
          <div className="mx-auto max-w-5xl">
            <div className="grid gap-5 md:grid-cols-3">
              {[
                ["Prix habituel", "Chaque tarif est comparé à l’historique de la route au départ de cet aéroport."],
                ["Vérification", "Le prix est contrôlé une nouvelle fois avant l’envoi de l’alerte."],
                ["Telegram", "Les opportunités sont envoyées rapidement avec les dates et le lien de réservation."],
              ].map(([title, copy]) => (
                <div key={title} className="rounded-3xl border border-[#D9E2E3] bg-white p-6">
                  <h2 className="font-bold text-[#0E7490]">{title}</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-500">{copy}</p>
                </div>
              ))}
            </div>

            <div className="mt-14 rounded-[32px] bg-white p-7 shadow-[0_18px_60px_rgba(11,42,63,.06)] sm:p-10">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#FF7A59]">Destinations surveillées</p>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-3xl">Quelques routes typiques depuis {data.city}</h2>
              <div className="mt-7 flex flex-wrap gap-3">
                {data.examples.map((destination) => (
                  <span key={destination} className="rounded-full border border-[#D9E2E3] bg-[#E9F5F7] px-4 py-2 text-sm font-semibold text-[#0B2A3F]">
                    {data.city} → {destination}
                  </span>
                ))}
              </div>
              <p className="mt-7 text-sm leading-7 text-slate-500">
                Le volume varie selon les compagnies, les saisons et les routes. GlobeGenius préfère ne rien envoyer plutôt que de présenter une promotion ordinaire comme une affaire exceptionnelle.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
