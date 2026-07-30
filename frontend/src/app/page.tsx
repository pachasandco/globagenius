import type { Metadata } from "next";
import Link from "next/link";
import RedirectIfLoggedIn from "./_components/RedirectIfLoggedIn";
import { LandingNotificationHero, LandingNotificationStackMobile } from "./_components/LandingNotificationHero";
import { RecentDealsGrid } from "./_components/RecentDealsGrid";
import { Wordmark } from "./_components/Wordmark";

export const metadata: Metadata = {
  title: "GlobeGenius — Le radar français des bons plans vols",
  description:
    "Créé en France pour les voyageurs qui partent de France. GlobeGenius surveille les prix depuis Paris et plusieurs grands aéroports régionaux, puis envoie les baisses vérifiées sur Telegram.",
  alternates: { canonical: "https://globegenius.app" },
  openGraph: {
    title: "GlobeGenius — Les bons plans vols ne partent pas uniquement de Paris",
    description:
      "Activez gratuitement le radar de votre aéroport et recevez sur Telegram les baisses de prix réellement intéressantes.",
    url: "https://globegenius.app",
    type: "website",
  },
};

const AIRPORTS = [
  ["Paris", "paris"],
  ["Lyon", "lyon"],
  ["Marseille", "marseille"],
  ["Toulouse", "toulouse"],
  ["Bordeaux", "bordeaux"],
  ["Nantes", "nantes"],
  ["Nice", "nice"],
  ["Bâle-Mulhouse", "bale-mulhouse"],
] as const;

const FAQS = [
  {
    q: "Que comprend le compte Freemium ?",
    a: "Un aéroport principal, deux alertes complètes par semaine, une pépite exceptionnelle complète et un joker de déverrouillage par mois. Les autres opportunités peuvent être présentées sous forme de teasers.",
  },
  {
    q: "GlobeGenius est-il un service français ?",
    a: "Oui. GlobeGenius a été créé en France pour répondre aux habitudes des voyageurs qui partent de France : prix en euros, aéroports régionaux, destinations appréciées du marché français et alertes en français.",
  },
  {
    q: "Le service fonctionne-t-il hors de Paris ?",
    a: "Oui, GlobeGenius surveille aussi Lyon, Marseille, Nice, Bordeaux, Toulouse, Nantes et Bâle-Mulhouse. Le volume varie selon l’aéroport : Paris produit généralement davantage de long-courriers, tandis que les régions offrent surtout des opportunités Europe, Méditerranée et ponctuellement du long-courrier.",
  },
  {
    q: "Combien d’alertes vais-je recevoir depuis mon aéroport ?",
    a: "GlobeGenius ne garantit pas un nombre fixe d’alertes. La fréquence dépend des prix réellement observés. Nous préférons ne rien envoyer plutôt que présenter une promotion ordinaire comme un bon plan. La couverture est ouverte et renforcée progressivement, aéroport par aéroport.",
  },
  {
    q: "GlobeGenius vend-il les billets ?",
    a: "Non. GlobeGenius détecte et vérifie les opportunités, puis vous redirige vers le site de réservation. Vous restez libre de réserver ou non.",
  },
  {
    q: "Pourquoi les alertes passent-elles par Telegram ?",
    a: "Parce que certains tarifs ne restent disponibles que quelques heures. Telegram permet de recevoir rapidement le prix, les dates et le lien de réservation.",
  },
  {
    q: "Combien coûtera Premium ?",
    a: "Premium est proposé à 39 € par an, soit 3,25 € par mois. La création du compte Freemium ne déclenche aucun prélèvement.",
  },
];

function SectionTitle({ eyebrow, title, copy }: { eyebrow: string; title: string; copy?: string }) {
  return (
    <div className="mx-auto mb-10 max-w-3xl text-center">
      <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-[#FF7A59]">{eyebrow}</p>
      <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl leading-tight text-[#0B2A3F] sm:text-5xl">{title}</h2>
      {copy && <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-500 sm:text-base">{copy}</p>}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <RedirectIfLoggedIn />

      <nav className="sticky top-0 z-50 border-b border-[#D9E2E3] bg-[#FFFCF7]/95 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>
          <div className="hidden items-center gap-7 text-sm text-slate-600 lg:flex">
            <a href="#deals" className="hover:text-[#0E7490]">Deals récents</a>
            <a href="#difference" className="hover:text-[#0E7490]">Pourquoi nous</a>
            <a href="#formules" className="hover:text-[#0E7490]">Formules</a>
            <a href="#couverture" className="hover:text-[#0E7490]">Aéroports</a>
            <Link href="/methodologie" className="hover:text-[#0E7490]">Méthodologie</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden text-sm font-medium text-slate-600 sm:inline">Connexion</Link>
            <Link
              href="/signup?utm_source=site&utm_medium=header&utm_campaign=freemium_activation"
              className="rounded-xl bg-[#0E7490] px-4 py-2.5 text-sm font-bold text-white shadow-[0_8px_24px_rgba(14,116,144,.20)] hover:bg-[#0A6078]"
            >
              Activer mon radar
            </Link>
          </div>
        </div>
      </nav>

      <main>
        <section className="relative overflow-hidden bg-[#0B2A3F]">
          <LandingNotificationHero />
          <div className="relative z-10 mx-auto grid min-h-[680px] max-w-7xl items-center px-5 py-20 sm:px-8 lg:grid-cols-[1.08fr_.92fr]">
            <div className="max-w-2xl">
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold text-white/85 backdrop-blur">
                <span className="h-2 w-2 rounded-full bg-[#52C9BE]" />
                Créé en France · couverture ouverte aéroport par aéroport
              </div>
              <h1 className="font-[family-name:var(--font-dm-serif)] text-5xl leading-[1.02] text-white sm:text-6xl lg:text-7xl">
                Les bons plans vols ne partent pas uniquement de Paris.
                <span className="mt-2 block text-[#FF9478]">Activez le radar de votre aéroport.</span>
              </h1>
              <p className="mt-7 max-w-xl text-lg leading-8 text-white/72">
                GlobeGenius est un service français qui surveille les prix depuis Paris et plusieurs grands aéroports régionaux, vérifie les baisses réellement intéressantes et vous prévient sur Telegram.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/signup?utm_source=site&utm_medium=hero&utm_campaign=freemium_activation"
                  className="rounded-xl bg-[#FF7A59] px-7 py-4 text-center text-base font-bold text-white shadow-[0_12px_32px_rgba(255,122,89,.30)] hover:bg-[#E96543]"
                >
                  Activer gratuitement mon radar
                </Link>
                <a href="#deals" className="rounded-xl border border-white/20 bg-white/8 px-7 py-4 text-center text-base font-semibold text-white hover:bg-white/12">
                  Voir les deals détectés
                </a>
              </div>
              <div className="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
                <span>✓ Sans carte bancaire</span>
                <span>✓ Prix re-vérifiés</span>
                <span>✓ Aucune fausse promesse de volume</span>
              </div>
            </div>
          </div>
        </section>
        <LandingNotificationStackMobile />

        <section className="border-b border-[#D9E2E3] bg-white">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-[#D9E2E3] md:grid-cols-4">
            {[
              ["10", "aéroports de départ surveillés"],
              ["France", "produit pensé pour ce marché"],
              ["24/7", "surveillance automatisée"],
              ["Telegram", "alertes actionnables"],
            ].map(([value, label]) => (
              <div key={label} className="bg-white px-5 py-7 text-center">
                <div className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#0E7490]">{value}</div>
                <div className="mt-1 text-xs uppercase tracking-wide text-slate-400">{label}</div>
              </div>
            ))}
          </div>
        </section>

        <section id="deals" className="px-5 py-20 sm:px-8">
          <SectionTitle
            eyebrow="Preuves, pas promesses"
            title="Des prix réellement détectés"
            copy="Chaque alerte compare le tarif observé à son prix habituel, puis le contrôle à nouveau avant l’envoi. Les économies présentées reposent sur les données du deal, jamais sur un montant inventé."
          />
          <div className="mx-auto max-w-6xl"><RecentDealsGrid /></div>
        </section>

        <section id="difference" className="bg-white px-5 py-20 sm:px-8">
          <SectionTitle
            eyebrow="Créé en France. Pensé pour partir d’ici."
            title="Un radar construit autour des voyageurs français"
            copy="Pas une newsletter mondiale traduite en français : un produit conçu pour les aéroports, les prix et les habitudes de départ du marché français."
          />
          <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
            {[
              ["Votre vrai aéroport", "Choisissez l’aéroport que vous pouvez réellement rejoindre, sans transformer un tarif parisien en faux bon plan après le TGV, le parking ou une nuit d’hôtel."],
              ["Une lecture locale", "Prix en euros, interface en français et surveillance de destinations pertinentes pour les voyageurs qui partent de France."],
              ["Moins, mais mieux", "Nous ne promettons pas un nombre fixe d’alertes. Si aucun tarif ne mérite votre attention, GlobeGenius préfère rester silencieux."],
            ].map(([title, copy]) => (
              <div key={title} className="rounded-3xl border border-[#D9E2E3] bg-[#F7F3EA] p-7">
                <h3 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">{title}</h3>
                <p className="mt-4 text-sm leading-7 text-slate-500">{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="fonctionnement" className="px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Le produit" title="Vous ne cherchez plus. GlobeGenius surveille." />
          <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-3">
            {[
              ["01", "Choisissez votre départ", "Sélectionnez l’aéroport principal que GlobeGenius doit surveiller pour votre compte Freemium."],
              ["02", "Les prix sont analysés", "Chaque tarif est comparé à son historique réel selon la route, la période et la durée du séjour."],
              ["03", "Recevez l’alerte", "Le prix est contrôlé une dernière fois puis envoyé sur Telegram avec les dates et le lien direct."],
            ].map(([num, title, copy]) => (
              <div key={num} className="rounded-3xl border border-[#D9E2E3] bg-white p-7">
                <div className="font-[family-name:var(--font-dm-serif)] text-5xl text-[#2AB7A9]/35">{num}</div>
                <h3 className="mt-7 text-xl font-bold text-[#0B2A3F]">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-500">{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="formules" className="bg-white px-5 py-20 sm:px-8">
          <SectionTitle
            eyebrow="Deux formules simples"
            title="Commencez gratuitement. Passez à Premium lorsque la valeur est visible."
            copy="Le Freemium limite le nombre d’alertes, jamais leur fraîcheur. Premium débloquera toutes les opportunités qualifiées, mais ne créera pas artificiellement des deals lorsqu’un aéroport est calme."
          />
          <div className="mx-auto grid max-w-4xl gap-5 md:grid-cols-2">
            <div className="rounded-[32px] border-2 border-[#2AB7A9] bg-white p-7 shadow-[0_20px_55px_rgba(42,183,169,.12)]">
              <span className="rounded-full bg-[#E9F5F7] px-3 py-1 text-xs font-bold text-[#0E7490]">Disponible maintenant</span>
              <h3 className="mt-6 font-[family-name:var(--font-dm-serif)] text-3xl">Freemium</h3>
              <div className="mt-3 text-2xl font-bold text-[#168F73]">0 €</div>
              <ul className="mt-6 space-y-3 text-sm leading-6 text-slate-600">
                <li>✓ 1 aéroport principal</li>
                <li>✓ 2 alertes complètes par semaine</li>
                <li>✓ 1 pépite complète par mois</li>
                <li>✓ 1 joker Premium par mois</li>
              </ul>
              <Link href="/signup?utm_source=site&utm_medium=pricing&utm_campaign=freemium_activation" className="mt-8 block w-full rounded-xl bg-[#0E7490] px-6 py-3.5 text-center text-sm font-bold text-white hover:bg-[#0A6078]">
                Tester mon aéroport gratuitement
              </Link>
            </div>

            <div className="rounded-[32px] bg-[#0B2A3F] p-7 text-white">
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-[#52C9BE]">Ouverture prochaine</span>
              <h3 className="mt-6 font-[family-name:var(--font-dm-serif)] text-3xl">Premium</h3>
              <div className="mt-3 text-2xl font-bold">39 € / an</div>
              <ul className="mt-6 space-y-3 text-sm leading-6 text-white/70">
                <li>✓ Alertes complètes sans quota</li>
                <li>✓ Plusieurs aéroports</li>
                <li>✓ Allers simples et combos malins</li>
                <li>✓ Réglages avancés</li>
              </ul>
              <div className="mt-8 rounded-xl border border-white/15 bg-white/10 px-6 py-3.5 text-center text-sm font-bold text-white/70">
                Paiement bientôt disponible
              </div>
            </div>
          </div>
          <div className="mx-auto mt-8 max-w-3xl rounded-2xl bg-[#FFF0EA] px-6 py-5 text-center text-sm leading-7 text-slate-600">
            <strong className="text-[#0B2A3F]">Une seule réservation peut amortir l’abonnement plusieurs fois.</strong> Le montant réellement économisé dépend du billet réservé, de sa disponibilité et de votre décision de réservation.
          </div>
        </section>

        <section id="couverture" className="px-5 py-20 sm:px-8">
          <SectionTitle
            eyebrow="Couverture transparente"
            title="Paris pour le volume. Les régions pour de vraies opportunités locales."
            copy="La France ne se résume pas à Paris, mais le marché aérien n’offre pas le même volume partout. GlobeGenius ouvre et renforce chaque aéroport progressivement, selon la qualité des données et la fréquence des prix réellement intéressants."
          />
          <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-3">
            {[
              ["Paris · volume élevé", "Davantage de fréquences et de long-courriers vers Tokyo, Bangkok, New York, Montréal, Miami et d’autres destinations mondiales.", "Couverture la plus régulière"],
              ["Grandes régions · actif", "Lyon, Marseille, Toulouse, Bordeaux, Nantes, Nice et Bâle-Mulhouse sont surveillés avec une fréquence qui dépend des opportunités du marché.", "Couverture différenciante"],
              ["Déploiement progressif", "Aucun aéroport n’est présenté comme équivalent à Paris. Les volumes sont observés avant d’intensifier la commercialisation locale.", "Promesse maîtrisée"],
            ].map(([title, copy, badge]) => (
              <div key={title} className="rounded-3xl bg-[#0B2A3F] p-7 text-white">
                <span className="text-xs font-bold uppercase tracking-[0.16em] text-[#52C9BE]">{badge}</span>
                <h3 className="mt-5 font-[family-name:var(--font-dm-serif)] text-2xl">{title}</h3>
                <p className="mt-4 text-sm leading-7 text-white/65">{copy}</p>
              </div>
            ))}
          </div>
          <div className="mx-auto mt-8 flex max-w-5xl flex-wrap justify-center gap-2">
            {AIRPORTS.map(([label, slug]) => (
              <Link key={slug} href={`/depart/${slug}`} className="rounded-full border border-[#D9E2E3] bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:border-[#0E7490] hover:text-[#0E7490]">
                {label}
              </Link>
            ))}
          </div>
          <p className="mx-auto mt-6 max-w-3xl text-center text-sm leading-7 text-slate-500">
            La présence d’un aéroport signifie que sa surveillance est active. Elle ne constitue pas une garantie de volume. GlobeGenius préfère une alerte rare et crédible à une succession de promotions ordinaires.
          </p>
        </section>

        <section id="premium" className="bg-[#E9F5F7] px-5 py-20 sm:px-8">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[1fr_.9fr]">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#0E7490]">Premium · ouverture prochaine</p>
              <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-4xl leading-tight text-[#0B2A3F] sm:text-5xl">
                39 € par an pour recevoir toutes les opportunités qualifiées de vos aéroports.
              </h2>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600">
                Plusieurs aéroports, tous les types de billets et aucune limite Freemium. La fréquence reste liée aux vrais prix disponibles : Premium débloque les résultats, il ne fabrique pas de fausses affaires.
              </p>
              <div className="mt-7 flex flex-wrap gap-3 text-sm text-[#0B2A3F]">
                <span className="rounded-full bg-white px-4 py-2 font-semibold">3,25 € / mois</span>
                <span className="rounded-full bg-white px-4 py-2 font-semibold">Alertes sans quota</span>
                <span className="rounded-full bg-white px-4 py-2 font-semibold">Plusieurs départs</span>
              </div>
              <p className="mt-6 text-sm text-slate-500">
                La création du compte Freemium n’entraîne aucun paiement. Le prix affiché sera confirmé avant toute souscription.
              </p>
            </div>
            <div className="rounded-[32px] border border-white/80 bg-white p-8 shadow-[0_25px_70px_rgba(11,42,63,.10)]">
              <div className="flex items-baseline justify-between">
                <div>
                  <div className="text-sm font-bold text-[#0E7490]">GlobeGenius Premium</div>
                  <div className="mt-2 font-[family-name:var(--font-dm-serif)] text-5xl text-[#0B2A3F]">39 €</div>
                  <div className="text-sm text-slate-400">par an</div>
                </div>
                <span className="rounded-full bg-[#FFF0EA] px-3 py-1 text-xs font-bold text-[#E96543]">Bientôt</span>
              </div>
              <ul className="mt-7 space-y-3 text-sm text-slate-600">
                <li>✓ Toutes les alertes qualifiées sans quota</li>
                <li>✓ Deals exceptionnels, aller simple et combos malins</li>
                <li>✓ Choix étendu des aéroports et seuils personnalisés</li>
                <li>✓ Garantie satisfait ou remboursé 30 jours à l’ouverture</li>
              </ul>
              <Link href="/signup?utm_source=site&utm_medium=pricing&utm_campaign=freemium_activation" className="mt-8 block w-full rounded-xl bg-[#0E7490] px-6 py-3.5 text-center text-sm font-bold text-white hover:bg-[#0A6078]">
                Tester gratuitement mon aéroport
              </Link>
              <p className="mt-3 text-center text-xs text-slate-400">Aucune carte bancaire demandée aujourd’hui</p>
            </div>
          </div>
        </section>

        <section className="bg-[#0B2A3F] px-5 py-20 text-white sm:px-8">
          <div className="mx-auto max-w-4xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#52C9BE]">Créé en France. Pensé pour partir d’ici.</p>
            <h2 className="mt-4 font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl">Découvrez d’abord ce que votre aéroport peut réellement vous apporter.</h2>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-white/65">
              Créez votre compte Freemium, choisissez votre départ et connectez Telegram. Vous verrez la valeur réelle du radar avant de décider de passer à Premium.
            </p>
            <Link href="/signup?utm_source=site&utm_medium=final_cta&utm_campaign=freemium_activation" className="mt-8 inline-flex rounded-xl bg-[#FF7A59] px-7 py-4 font-bold text-white hover:bg-[#E96543]">
              Activer gratuitement mon radar
            </Link>
          </div>
        </section>

        <section id="faq" className="bg-white px-5 py-20 sm:px-8">
          <SectionTitle eyebrow="Questions fréquentes" title="Une promesse claire avant de commencer" />
          <div className="mx-auto max-w-3xl divide-y divide-[#D9E2E3] border-y border-[#D9E2E3]">
            {FAQS.map((faq) => (
              <details key={faq.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold text-[#0B2A3F]">
                  {faq.q}<span className="text-2xl font-light text-[#FF7A59] transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 pr-8 text-sm leading-7 text-slate-500">{faq.a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-[#D9E2E3] bg-[#FFFCF7] px-5 py-8 text-sm text-slate-400">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div>Globe Genius © 2026 · Créé en France</div>
          <div className="flex flex-wrap justify-center gap-5">
            <Link href="/methodologie" className="hover:text-[#0E7490]">Méthodologie</Link>
            <Link href="/conditions" className="hover:text-[#0E7490]">Conditions</Link>
            <Link href="/confidentialite" className="hover:text-[#0E7490]">Confidentialité</Link>
            <Link href="/mentions-legales" className="hover:text-[#0E7490]">Mentions légales</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
