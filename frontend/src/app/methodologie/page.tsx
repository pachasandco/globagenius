import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../_components/Wordmark";

export const metadata: Metadata = {
  title: "Notre méthodologie — GlobeGenius",
  description:
    "Comment GlobeGenius détecte, vérifie et envoie ses alertes vols — en toute transparence. Calcul du prix habituel, élimination des ghost fares, faux positifs, feedback et limites assumées.",
  alternates: { canonical: "https://globegenius.app/methodologie" },
  openGraph: {
    title: "Notre méthodologie · GlobeGenius",
    description:
      "Le détail complet de comment on détecte, vérifie et envoie les alertes vols.",
    url: "https://globegenius.app/methodologie",
    type: "article",
  },
};

export default function MethodologiePage() {
  return (
    <div className="min-h-screen bg-[var(--color-cream)]">
      {/* ── NAVBAR ── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 h-[80px] bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-lg leading-none">
          <Wordmark />
        </Link>
        <div className="flex items-center gap-6 text-sm">
          <Link href="/" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">
            Accueil
          </Link>
          <Link href="/beta" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">
            Beta
          </Link>
          <Link href="/signup" className="bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
            Rejoindre la beta
          </Link>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-6 sm:px-12 py-12">
        {/* ── HERO ── */}
        <header className="text-center mb-12">
          <span className="inline-block bg-[var(--color-coral)]/15 border border-[var(--color-coral)]/30 text-[var(--color-coral)] px-3 py-1 rounded-full text-xs font-bold mb-6">
            📐 Transparence méthodologique
          </span>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-[var(--color-ink)] leading-tight mb-4">
            Notre méthodologie
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            Comment GlobeGenius détecte, vérifie et envoie ses alertes vols — en toute transparence.
          </p>
        </header>

        {/* ── SOMMAIRE ── */}
        <nav aria-label="Sommaire" className="bg-white rounded-2xl p-6 border border-[var(--color-sand)] mb-12">
          <div className="text-sm font-semibold text-[var(--color-ink)] mb-3">Sur cette page</div>
          <ol className="space-y-1.5 text-sm text-[var(--color-ink)]/85 list-decimal list-inside">
            <li><a href="#pourquoi" className="hover:text-[var(--color-coral)]">Pourquoi cette page existe</a></li>
            <li><a href="#prix-habituel" className="hover:text-[var(--color-coral)]">Comment on calcule le « prix habituel »</a></li>
            <li><a href="#ghost-fares" className="hover:text-[var(--color-coral)]">Comment on élimine les ghost fares</a></li>
            <li><a href="#faux-positifs" className="hover:text-[var(--color-coral)]">Comment on évite les faux positifs</a></li>
            <li><a href="#feedback" className="hover:text-[var(--color-coral)]">Comment ton feedback améliore le système</a></li>
            <li><a href="#limites" className="hover:text-[var(--color-coral)]">Nos limites et ce qu&apos;on ne fait pas (encore)</a></li>
            <li><a href="#modele" className="hover:text-[var(--color-coral)]">Comment GlobeGenius gagne de l&apos;argent</a></li>
            <li><a href="#qui" className="hover:text-[var(--color-coral)]">Qui est derrière</a></li>
            <li><a href="#engagement" className="hover:text-[var(--color-coral)]">Notre engagement de transparence</a></li>
            <li><a href="#faq" className="hover:text-[var(--color-coral)]">Questions fréquentes</a></li>
          </ol>
        </nav>

        {/* ── POURQUOI ── */}
        <section id="pourquoi" className="mb-12">
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            La plupart des services d&apos;alertes vols ne disent jamais comment ils fonctionnent. Combien de deals sont vérifiés ? Comment les prix de référence sont calculés ? Quels biais sont corrigés ? <strong>C&apos;est l&apos;opacité totale.</strong>
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Chez GlobeGenius, on fait le pari inverse. <strong>Si tu nous confies ton attention plusieurs fois par jour, tu mérites de savoir comment on travaille.</strong> Voici donc le détail de notre méthodologie.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed">
            Pas tout, évidemment. Certaines optimisations restent privées — c&apos;est notre avantage opérationnel. Mais tout ce qui détermine la qualité de tes alertes est sur cette page.
          </p>
        </section>

        {/* ── 1. PRIX HABITUEL ── */}
        <section id="prix-habituel" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            1. Comment on calcule le « prix habituel »
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            C&apos;est le cœur de notre engagement : <strong>ne jamais gonfler les prix de référence pour faire briller un deal.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Notre approche</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Notre prix habituel est une <strong>médiane statistique sur 6 mois</strong> des prix réellement observés sur la route, depuis l&apos;aéroport de départ concerné. Pas un prix maximum théorique. Pas un tarif « officiel » que personne ne paie jamais.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Concrètement, pour la route Paris → Marrakech, on a observé entre novembre 2025 et mai 2026 des prix allant de 89€ à 412€ aller-retour. La médiane statistique est de <strong>155€</strong>. Quand on envoie une alerte « Paris → Marrakech à 74€ », l&apos;économie affichée (-52%) est calculée vs ces 155€ — pas vs le pic à 412€ qu&apos;un voyageur a peut-être payé une seule fois en plein pic vacances.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Pourquoi on fait ça</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Calculer une économie depuis un prix maximum théorique permet d&apos;afficher des « -80% » ou « -90% » qui font rêver. C&apos;est légal. C&apos;est partout dans le secteur. <strong>C&apos;est aussi trompeur.</strong>
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Le vrai bénéfice pour un voyageur, c&apos;est combien il économise vs ce qu&apos;il aurait payé en moyenne. Pas vs un pic exceptionnel qu&apos;il n&apos;aurait jamais payé de toute façon.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Ajustements saisonniers</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Notre médiane est ajustée par la saisonnalité française : vacances scolaires (zones A, B, C), ponts, été, hiver. Un aller-retour Paris-Marrakech en février n&apos;a pas le même prix médian qu&apos;en août. Notre baseline le sait.
          </p>

          <div className="bg-[var(--color-cream)] border-l-4 border-[var(--color-coral)] rounded-r p-4 mt-6">
            <div className="text-sm font-semibold text-[var(--color-ink)] mb-1">Limite assumée</div>
            <p className="text-sm text-[var(--color-ink)]/85">
              Pour les routes nouvelles ou rarement empruntées (moins de 5 observations sur 6 mois), notre baseline n&apos;est pas encore statistiquement fiable. <strong>Sur ces routes, on ne génère pas d&apos;alertes pour l&apos;instant.</strong> On préfère rater un deal plutôt qu&apos;envoyer un faux deal.
            </p>
          </div>
        </section>

        {/* ── 2. GHOST FARES ── */}
        <section id="ghost-fares" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            2. Comment on élimine les « ghost fares »
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Un « ghost fare » est un prix affiché par un système de réservation qui n&apos;est plus disponible à l&apos;achat réel. Le voyageur clique, arrive sur la page de paiement, et découvre que le prix réel est différent. <strong>C&apos;est la frustration numéro 1 du secteur.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Notre système de vérification croisée</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Avant d&apos;envoyer une alerte, on fait passer chaque deal candidat par un système de vérification à deux niveaux.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Niveau 1 — Détection initiale.</strong> Notre moteur surveille en continu les prix des vols au départ des 9 aéroports français. Quand un prix tombe significativement sous notre baseline, on le marque comme « candidat deal ».
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Niveau 2 — Re-vérification croisée.</strong> Avant l&apos;envoi, on interroge une deuxième source pour confirmer la disponibilité réelle du tarif. Si l&apos;écart entre les deux sources dépasse un seuil de tolérance, le deal est rejeté ou mis en quarantaine pour observation.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Résultat</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>95% des deals envoyés sont vérifiés sur deux sources.</strong> Le 5% restant correspond à des deals tellement temporaires (erreurs tarifaires de quelques minutes) que la double vérification n&apos;a pas le temps de s&apos;exécuter. Ces deals sont signalés explicitement « Promo flash » dans nos alertes.
          </p>

          <div className="bg-[var(--color-cream)] border-l-4 border-[var(--color-coral)] rounded-r p-4 mt-6">
            <div className="text-sm font-semibold text-[var(--color-ink)] mb-1">Limite assumée</div>
            <p className="text-sm text-[var(--color-ink)]/85">
              Aucun système n&apos;est parfait. Sur les LCC (Ryanair, Wizz, Easyjet), les prix peuvent évoluer en quelques minutes après notre vérification. <strong>Si tu reçois une alerte et qu&apos;au moment de réserver le prix a changé, c&apos;est rare mais possible.</strong> Notre objectif est de garder ce taux sous 5%.
            </p>
          </div>
        </section>

        {/* ── 3. FAUX POSITIFS ── */}
        <section id="faux-positifs" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            3. Comment on évite les faux positifs
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Un faux positif, c&apos;est une alerte envoyée pour un prix qui n&apos;est pas réellement exceptionnel. Pour les éviter, on a construit plusieurs filtres systématiques.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Exclusions compagnies</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Certaines compagnies ont une volatilité tarifaire tellement élevée que notre baseline statistique génère trop de faux positifs sur certaines routes. On les exclut explicitement le temps d&apos;accumuler suffisamment de données pour les calibrer correctement.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Aujourd&apos;hui</strong> : Vueling est exclue de plusieurs routes Paris-Espagne. Cette exclusion sera revue quand on aura assez de données stables sur ces routes.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Cooldown par destination</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Si on a envoyé une alerte vers Marrakech il y a 5 jours, on n&apos;enverra <strong>pas</strong> d&apos;autre alerte vers Marrakech avant 7 jours. Même si un nouveau prix bas est détecté.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Pourquoi ? Parce qu&apos;on préfère une qualité d&apos;alerte irréprochable plutôt qu&apos;un flux constant. <strong>Une alerte sur 4 jours = une vraie aubaine. Trois alertes sur Marrakech en une semaine = du spam.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Caps par destination</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Certaines destinations à très forte volatilité (Bali, Bangkok, Marrakech) ont un nombre maximum d&apos;alertes par mois. Au-delà, on bloque même si les prix continuent à descendre. <strong>C&apos;est un choix éditorial pour préserver la qualité moyenne perçue.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Filtre durée de séjour</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed">
            On exclut les « fake deals » type aller-retour 1h ou voyage de 14h avec 12h d&apos;escale dans un aéroport. Notre algorithme privilégie les durées de séjour cohérentes avec les usages réels (3 jours minimum pour la plupart des destinations).
          </p>
        </section>

        {/* ── 4. FEEDBACK ── */}
        <section id="feedback" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            4. Comment ton feedback améliore le système
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Chaque alerte Telegram envoyée par GlobeGenius inclut <strong>trois boutons de feedback</strong> :
          </p>
          <ul className="space-y-2 text-[var(--color-ink)]/85 mb-6">
            <li>👍 <strong>Bon deal</strong> : le deal est réel et pertinent</li>
            <li>👎 <strong>Faux deal</strong> : le prix n&apos;est pas réellement exceptionnel</li>
            <li>⏱️ <strong>Trop tard</strong> : le deal était bon mais déjà épuisé</li>
          </ul>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Pourquoi ce système</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Aucun algorithme automatique ne détecte tout. Les voyageurs réels voient des choses qu&apos;on rate : prix qui montent au checkout, frais cachés sur l&apos;OTA de destination, dates incompatibles avec leurs besoins, deal « techniquement bon » mais « humainement décevant ».
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Vos clics nous apprennent à ajuster nos seuils, à identifier les patterns d&apos;erreur, et à améliorer la baseline chaque semaine.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Engagement de transparence</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            On publiera régulièrement sur cette page un <strong>rapport de précision</strong> avec les chiffres réels :
          </p>
          <ul className="space-y-1 text-[var(--color-ink)]/85 list-disc list-inside">
            <li>Nombre de deals envoyés sur la période</li>
            <li>Taux de « 👍 Bon » / « 👎 Faux » / « ⏱️ Trop tard »</li>
            <li>Patterns d&apos;erreur identifiés grâce aux feedbacks</li>
            <li>Corrections apportées</li>
            <li>Évolution de notre taux de précision global</li>
          </ul>
        </section>

        {/* ── 5. LIMITES ── */}
        <section id="limites" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            5. Nos limites et ce qu&apos;on ne fait pas (encore)
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Soyons honnêtes : GlobeGenius n&apos;est pas parfait. Voici ce qu&apos;on ne fait pas (encore), et pourquoi.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Couverture géographique</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Aujourd&apos;hui, on couvre l&apos;Europe, la Méditerranée et l&apos;Afrique du Nord.</strong> Le long-courrier (Asie, Amériques, Pacifique) arrivera prochainement en beta, quand notre baseline statistique sera mature sur ces zones.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            On ne lance pas le long-courrier avant d&apos;être sûr de la qualité. <strong>C&apos;est plus important pour nous d&apos;attendre que de livrer une feature à moitié.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Volume d&apos;alertes</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            On envoie <strong>jusqu&apos;à 5 alertes par jour maximum, étalées dans le temps</strong>. Volontairement.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Si tu es un voyageur « deal hunter » intensif qui veut voir tous les bons plans possibles, on n&apos;est probablement pas suffisant pour toi seul. <strong>Combine GlobeGenius avec Google Flights et Skyscanner.</strong> On est un service de « vraies aubaines vérifiées », pas un agrégateur exhaustif.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Types de billets</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Aujourd&apos;hui, on surveille principalement les <strong>aller-retour classiques</strong>. Les alertes <strong>aller simple</strong> (intéressantes pour les expatriés, les Erasmus, les digital nomads) sont en cours de déploiement.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Le <strong>stopover</strong> (escale longue volontaire de 24-72h pour visiter deux villes pour le prix d&apos;une) arrivera prochainement en beta. <strong>Personne d&apos;autre ne le fait en français.</strong>
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Niches non couvertes</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-2">GlobeGenius ne couvre <strong>pas</strong> :</p>
          <ul className="space-y-1 text-[var(--color-ink)]/85 list-disc list-inside">
            <li>Les vols intérieurs France (TGV souvent plus pertinent)</li>
            <li>Les vols private jet ou business class luxe (autre marché)</li>
            <li>Les billets de groupe (&gt; 9 passagers)</li>
            <li>Les vols cargo, sanitaires, militaires</li>
          </ul>
        </section>

        {/* ── 6. MODELE ── */}
        <section id="modele" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            6. Comment GlobeGenius gagne de l&apos;argent
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Transparence totale sur notre modèle économique.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Pendant la beta publique</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>100% gratuit pour les 100 premiers inscrits.</strong> Ces 100 fondateurs gardent leur statut Premium gratuit à vie quand on lancera officiellement.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            Pendant cette phase, GlobeGenius ne génère aucun revenu. Le projet est financé sur fonds personnels du fondateur.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">À partir du lancement officiel</h3>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Deux sources de revenus :</strong>
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-2">
            <strong>Abonnement Premium à 4,99€/mois.</strong> Donne accès :
          </p>
          <ul className="space-y-1 text-[var(--color-ink)]/85 list-disc list-inside mb-4">
            <li>Toutes les alertes en temps réel (vs J+24h pour le tier gratuit)</li>
            <li>Stopover et aller simple</li>
            <li>Choix illimité d&apos;aéroports de départ</li>
            <li>Support direct par Telegram</li>
          </ul>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Commission d&apos;affiliation.</strong> Quand tu cliques sur un lien deal et que tu réserves, la plateforme de réservation (Aviasales/Travelpayouts ou autre) nous verse une commission. <strong>Cette commission n&apos;influence jamais quels deals on détecte ou priorise.</strong> On envoie le meilleur deal disponible, pas celui qui rapporte le plus.
          </p>

          <h3 className="font-semibold text-[var(--color-ink)] text-lg mb-2 mt-6">Ce qu&apos;on ne fera jamais</h3>
          <ul className="space-y-2 text-[var(--color-ink)]/85">
            <li>— <strong>Vendre tes données.</strong> Ton email, ton téléphone, tes préférences restent chez nous. Point.</li>
            <li>— <strong>Publicité dans tes alertes.</strong> Tu paies pour ne pas avoir de pub. On respecte ça.</li>
            <li>— <strong>Sponsorisation cachée de compagnies.</strong> Si une compagnie nous payait pour mettre en avant ses vols, on cesserait d&apos;être un service d&apos;alertes objectif. Donc on ne le fera jamais.</li>
            <li>— <strong>Marketing trompeur « -90% ».</strong> Notre engagement principal. Pas négociable.</li>
          </ul>
        </section>

        {/* ── 7. QUI ── */}
        <section id="qui" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            7. Qui est derrière
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            GlobeGenius est un projet français, indépendant, lancé en 2026.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Fondateur</strong> : Arthur, basé en région parisienne.
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">
            <strong>Pas d&apos;investisseurs externes.</strong> Pas de pression de croissance forcée par un VC. <strong>Le rythme est celui de la qualité, pas du burn rate.</strong>
          </p>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-2">Tu peux nous contacter directement :</p>
          <ul className="space-y-1 text-[var(--color-ink)]/85 list-disc list-inside">
            <li>Par email : <a href="mailto:arthur@globegenius.app" className="text-[var(--color-coral)] hover:underline">arthur@globegenius.app</a></li>
            <li>Via le bot Telegram (réponse directe au support)</li>
          </ul>
        </section>

        {/* ── 8. ENGAGEMENT ── */}
        <section id="engagement" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            8. Notre engagement de transparence
          </h2>
          <p className="text-[var(--color-ink)]/85 leading-relaxed mb-4">On s&apos;engage publiquement à :</p>
          <ol className="space-y-3 text-[var(--color-ink)]/85 list-decimal list-inside">
            <li><strong>Publier un rapport de précision régulier</strong> avec nos vrais chiffres et nos corrections.</li>
            <li><strong>Maintenir cette page à jour</strong> à chaque évolution méthodologique. Toutes les modifications seront archivées dans un historique public.</li>
            <li><strong>Annoncer publiquement toute évolution du modèle économique</strong> au minimum 30 jours avant son application.</li>
            <li><strong>Communiquer honnêtement nos échecs.</strong> Si on rate massivement un deal majeur, ou qu&apos;on envoie un faux deal à grande échelle, on le dira ouvertement dans une notification dédiée.</li>
            <li>
              <strong>Garder le contrôle aux utilisateurs.</strong> Tu peux à tout moment :
              <ul className="space-y-1 mt-2 ml-6 list-disc list-inside text-[var(--color-ink)]/85">
                <li>Mettre tes alertes en pause (<code className="text-xs bg-[var(--color-sand)]/40 px-1 rounded">/pause</code> sur Telegram ou globegenius.app/profile)</li>
                <li>Te désabonner sans question (<code className="text-xs bg-[var(--color-sand)]/40 px-1 rounded">/stop</code>)</li>
                <li>Supprimer définitivement tes données (<code className="text-xs bg-[var(--color-sand)]/40 px-1 rounded">/delete</code> ou demande email)</li>
              </ul>
            </li>
          </ol>
        </section>

        {/* ── FAQ ── */}
        <section id="faq" className="mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl font-bold text-[var(--color-ink)] mb-6">
            Questions fréquentes
          </h2>

          <div className="space-y-6">
            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">« Vous publiez vraiment vos vrais chiffres ? »</div>
              <p className="text-[var(--color-ink)]/85 leading-relaxed">
                Oui. Si on hésite à publier un chiffre, c&apos;est qu&apos;il y a un problème — donc on le publiera quand même, avec les corrections en cours.
              </p>
            </div>

            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">« Vos concurrents ne vont-ils pas copier votre méthodologie ? »</div>
              <p className="text-[var(--color-ink)]/85 leading-relaxed">
                Possible. Mais notre vrai fossé compétitif est notre <strong>engagement public dans la durée</strong>, pas la méthodologie en elle-même. Un concurrent qui annonce demain « nous aussi on calcule sur médiane » devra le prouver pendant 18 mois pour avoir la même crédibilité. <strong>On a déjà commencé.</strong>
              </p>
            </div>

            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">« Comment vérifier que vous tenez vraiment vos engagements ? »</div>
              <p className="text-[var(--color-ink)]/85 leading-relaxed mb-2">Quatre moyens :</p>
              <ol className="space-y-1 text-[var(--color-ink)]/85 list-decimal list-inside">
                <li>Lire nos rapports de précision</li>
                <li>Cliquer sur les boutons feedback de chaque alerte et vérifier vous-mêmes</li>
                <li>Comparer un échantillon de nos alertes avec Google Flights / Skyscanner</li>
                <li>Nous interpeller publiquement sur Twitter, LinkedIn, ou directement par email</li>
              </ol>
            </div>

            <div>
              <div className="font-semibold text-[var(--color-ink)] mb-2">« Pourquoi ne pas tout publier en open source ? »</div>
              <p className="text-[var(--color-ink)]/85 leading-relaxed">
                Notre logique générale est publique, oui. Mais les paramètres exacts (seuils, formules pondérées, optimisations) restent privés. C&apos;est notre savoir-faire opérationnel. <strong>Si on publiait tout, on disparaîtrait dans 18 mois face à des copycats sans valeur ajoutée.</strong> Garder 20% privé nous permet de continuer à investir dans la qualité.
              </p>
            </div>
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="bg-[var(--color-ink)] rounded-2xl p-8 text-center mb-12">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl font-bold text-white mb-3">
            Tu veux tester en conditions réelles ?
          </h2>
          <p className="text-gray-400 text-sm mb-6 max-w-md mx-auto">
            Il reste des places fondateurs avec statut Premium gratuit à vie.
          </p>
          <Link
            href="/beta"
            className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-3 rounded-xl font-bold text-base transition-colors"
          >
            Voir le programme beta
          </Link>
        </section>

        {/* ── PAGE EVOLUE ── */}
        <section className="text-center text-sm text-gray-500 mb-12">
          <p className="mb-2">Cette méthodologie n&apos;est pas figée. Elle s&apos;améliore en continu grâce aux feedbacks, aux nouvelles données et aux retours utilisateurs.</p>
          <p>
            Une question ou une suggestion ?{" "}
            <a href="mailto:arthur@globegenius.app" className="text-[var(--color-coral)] hover:underline">arthur@globegenius.app</a>
          </p>
        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="py-6 px-6 sm:px-12 bg-[#050e1a] flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-gray-500">
        <span>© 2026 Globe Genius</span>
        <div className="flex gap-4 flex-wrap justify-center">
          <Link href="/methodologie" className="hover:text-gray-300 transition-colors">Méthodologie</Link>
          <Link href="/conditions" className="hover:text-gray-300 transition-colors">Conditions</Link>
          <Link href="/confidentialite" className="hover:text-gray-300 transition-colors">Confidentialité</Link>
          <Link href="/mentions-legales" className="hover:text-gray-300 transition-colors">Mentions légales</Link>
          <a href="mailto:contact@globegenius.app" className="hover:text-gray-300 transition-colors">Contact</a>
        </div>
      </footer>
    </div>
  );
}
