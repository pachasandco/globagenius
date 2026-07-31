import type { Metadata } from "next";
import { EditorialShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Notre méthodologie — GlobeGenius",
  description: "Comment GlobeGenius détecte, compare, vérifie et présente les opportunités de vols.",
  alternates: { canonical: "https://globegenius.app/methodologie" },
  openGraph: {
    title: "Notre méthodologie · GlobeGenius",
    description: "La méthode utilisée pour détecter et vérifier les alertes vols.",
    url: "https://globegenius.app/methodologie",
    type: "article",
  },
};

export default function MethodologiePage() {
  return (
    <EditorialShell eyebrow="Transparence méthodologique" title="Comment GlobeGenius distingue un vrai deal d’une promotion ordinaire" intro="Le moteur automatise la surveillance, mais une alerte n’est envoyée qu’après plusieurs contrôles de cohérence et de fraîcheur.">
      <nav aria-label="Sommaire" className="rounded-2xl border border-[#D9E2E3] bg-[#E9F5F7] p-5 text-sm">
        <p className="font-bold text-[#0B2A3F]">Sur cette page</p>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-slate-600">
          <li><a href="#collecte">Collecte des prix</a></li>
          <li><a href="#reference">Construction du prix de référence</a></li>
          <li><a href="#qualification">Qualification d’un deal</a></li>
          <li><a href="#verification">Vérification avant envoi</a></li>
          <li><a href="#presentation">Présentation de l’économie</a></li>
          <li><a href="#limites">Limites assumées</a></li>
        </ol>
      </nav>

      <section id="collecte">
        <h2>1. Collecte des prix</h2>
        <p>GlobeGenius surveille les routes configurées depuis les aéroports couverts. Les observations servent à suivre l’évolution d’un prix selon la route, la période de départ, la durée du séjour et le type de trajet.</p>
        <p>Le service ne cherche pas à reproduire un comparateur généraliste. Il concentre ses ressources sur un catalogue de départs et de destinations qui peut être vérifié et enrichi progressivement.</p>
      </section>

      <section id="reference">
        <h2>2. Construction du prix de référence</h2>
        <p>Un prix bas n’est intéressant que par rapport à un niveau habituel crédible. GlobeGenius construit donc une référence à partir des observations disponibles pour un contexte comparable, plutôt qu’à partir d’un prix maximum ou d’un tarif barré fourni par un vendeur.</p>
        <p>Lorsque les données sont insuffisantes, incohérentes ou trop anciennes, le moteur peut refuser de qualifier l’offre. Cette prudence réduit le nombre d’alertes, mais protège la qualité du signal.</p>
      </section>

      <section id="qualification">
        <h2>3. Qualification d’un deal</h2>
        <p>Le tarif observé est comparé à sa référence. Le moteur prend également en compte la fraîcheur, la cohérence du trajet, les dates, le type de vol et les règles de diffusion applicables au compte.</p>
        <p>Les allers-retours et les allers simples sont traités séparément. Un prix d’aller simple n’est pas présenté comme le prix d’un aller-retour. La vitrine publique met prioritairement en avant des allers-retours disposant d’une vraie date de retour.</p>
      </section>

      <section id="verification">
        <h2>4. Vérification avant envoi</h2>
        <p>Avant la diffusion, GlobeGenius contrôle à nouveau les informations disponibles : prix, dates, route, forme du trajet et lien de réservation. Une offre trop ancienne ou devenue incohérente est écartée.</p>
        <p>La mention « prix confirmé » signifie que le tarif a été revérifié au moment du contrôle. Elle ne garantit pas qu’il restera disponible après l’envoi : les compagnies et distributeurs peuvent modifier un prix à tout instant.</p>
      </section>

      <section id="presentation">
        <h2>5. Présentation de l’économie</h2>
        <p>Le pourcentage affiché correspond à l’écart entre le prix détecté et le prix de référence retenu. Lorsque les deux montants ne sont pas cohérents, l’offre ne doit pas être utilisée dans une communication commerciale.</p>
        <div className="gg-status-warning mt-5 rounded-2xl border p-5 text-sm leading-7">GlobeGenius ne promet ni une économie fixe, ni un nombre déterminé d’alertes. La fréquence dépend des prix réellement observés depuis chaque aéroport.</div>
      </section>

      <section id="limites">
        <h2>6. Limites assumées</h2>
        <ul className="mt-3 list-disc space-y-2 pl-6">
          <li>un tarif peut disparaître entre la vérification et le clic ;</li>
          <li>les bagages, sièges et autres options peuvent modifier le coût final ;</li>
          <li>les aéroports régionaux peuvent produire moins d’opportunités que Paris ;</li>
          <li>une route récente peut rester silencieuse tant que sa référence n’est pas assez solide ;</li>
          <li>GlobeGenius ne remplace pas la vérification des conditions du vendeur avant le paiement.</li>
        </ul>
      </section>

      <section>
        <h2>Modèle économique</h2>
        <p>GlobeGenius propose un compte Freemium et une formule Premium annuelle à 39 €. Certains liens de réservation peuvent également être affiliés. Cette rémunération ne doit pas modifier le classement ou la qualification technique d’un deal.</p>
      </section>

      <section>
        <h2>Amélioration continue</h2>
        <p>Les retours transmis après une alerte, les ouvertures de liens et les contrôles opérationnels servent à identifier les routes, sources ou formats qui méritent un ajustement. Les règles peuvent évoluer, mais la séparation entre faits observés, estimation et promesse commerciale doit rester explicite.</p>
      </section>

      <p className="mt-10 border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 31 juillet 2026.</p>
    </EditorialShell>
  );
}
