import Link from "next/link";
import type { Metadata } from "next";
import { EditorialShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Conditions d’utilisation et de vente — GlobeGenius",
  description: "Conditions de la formule Freemium GlobeGenius et de l’offre Premium à 39 € par an.",
  alternates: { canonical: "https://globegenius.app/conditions" },
  robots: { index: false, follow: false },
};

export default function Conditions() {
  return (
    <EditorialShell eyebrow="Cadre contractuel" title="Conditions d’utilisation et de vente" intro="Le fonctionnement du compte Freemium, de l’offre Premium et des alertes GlobeGenius, présenté sans ambiguïté.">
      <div className="gg-status-success rounded-2xl border p-5 text-sm leading-7">
        <strong>Avant l’ouverture commerciale :</strong> Premium est fixé à 39 € TTC par an. Tant que le bouton public de souscription n’est pas ouvert, la création et l’utilisation d’un compte Freemium n’entraînent aucun paiement, aucun renouvellement et aucune demande de carte bancaire.
      </div>

      <section><h2>1. Objet</h2><p>Les présentes conditions encadrent l’utilisation de GlobeGenius, accessible sur globegenius.app, ainsi que la souscription à l’offre Premium lorsqu’elle sera commercialement ouverte.</p></section>
      <section><h2>2. Description du service</h2><p>GlobeGenius détecte des tarifs aériens susceptibles d’être anormalement bas, les compare à un prix habituel observé, effectue des contrôles supplémentaires et envoie des alertes sur Telegram. GlobeGenius ne vend pas les billets et n’agit pas comme agence de voyage.</p></section>
      <section>
        <h2>3. Formule Freemium</h2>
        <p>La formule Freemium permet actuellement :</p>
        <ul className="mt-3 list-disc space-y-2 pl-6">
          <li>la surveillance d’un aéroport de départ principal ;</li>
          <li>jusqu’à deux alertes aller-retour complètes et instantanées par période glissante de sept jours ;</li>
          <li>une alerte aller-retour exceptionnelle complète par période glissante de trente jours ;</li>
          <li>un joker par période glissante de trente jours pour révéler le prix, les dates et le lien d’un deal Premium présenté dans l’espace utilisateur ;</li>
          <li>l’accès aux teasers des autres opportunités, aux préférences essentielles et aux guides destination.</li>
        </ul>
        <p>Les allers simples, les combinaisons de billets, les alertes sans quota, les réglages avancés et l’utilisation de plusieurs aéroports restent réservés aux comptes Premium. Les alertes gratuites ne sont pas retardées artificiellement : GlobeGenius limite leur nombre plutôt que d’envoyer un tarif potentiellement périmé.</p>
      </section>
      <section><h2>4. Fin de Premium Découverte</h2><p>La période Premium Découverte n’est plus proposée. Les comptes qui disposaient d’un essai automatique utilisent désormais la formule Freemium, sauf s’ils détiennent un badge OG, un abonnement Premium payant actif ou un droit Premium administratif distinct.</p></section>
      <section><h2>5. Badge OG</h2><p>Le maintien du Premium fondateur est réservé aux comptes auxquels GlobeGenius a effectivement attribué un <strong>badge OG</strong>. Ce badge matérialise une contribution reconnue à la phase fondatrice du produit.</p><p>Les anciens comptes de beta qui ne disposent pas de ce badge utilisent la formule Freemium. Les droits liés à un abonnement payant actif ou à une attribution administrative distincte ne sont pas concernés par cette règle.</p></section>
      <section><h2>6. Offre Premium</h2><p>L’offre Premium est fixée au tarif public de <strong>39 € TTC par an</strong>, payable en une fois et renouvelable annuellement. Elle est destinée à inclure toutes les alertes qualifiées sans quota Freemium, plusieurs aéroports, les deals exceptionnels, les allers simples, les combos malins et des options de personnalisation supplémentaires.</p><p>Les comparaisons de rentabilité présentées sur le site sont des illustrations. GlobeGenius ne garantit ni le montant d’une économie, ni la disponibilité d’un tarif, ni la réalisation d’une réservation.</p></section>
      <section><h2>7. Paiement et renouvellement</h2><p>Le paiement est traité par Stripe. Avant toute validation, l’utilisateur voit le prix, la durée, les conditions de renouvellement et le moyen d’annulation. Aucun prélèvement n’est effectué avant une action explicite de souscription.</p></section>
      <section><h2>8. Garantie commerciale prévue</h2><p>À l’ouverture commerciale de Premium, GlobeGenius prévoit une garantie satisfait ou remboursé de 30 jours à compter de la souscription. Les modalités opérationnelles seront rappelées au moment du paiement et pourront être exercées par email à <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>.</p></section>
      <section><h2>9. Prix et disponibilité des vols</h2><p>Les prix proviennent de partenaires et de systèmes tiers. Ils peuvent évoluer ou disparaître entre la détection, l’alerte et la réservation. Les frais de bagages, options, conditions de modification et conditions d’annulation relèvent du vendeur du billet.</p></section>
      <section><h2>10. Responsabilité</h2><p>GlobeGenius fournit un service d’information et de mise en relation. L’utilisateur reste seul responsable de la vérification du trajet, des dates, des formalités, des visas, des correspondances et des conditions du vendeur avant de réserver.</p></section>
      <section><h2>11. Données, évolution du service et suppression du compte</h2><p>Les modalités relatives aux données personnelles sont décrites dans la <Link href="/confidentialite">politique de confidentialité</Link>. La suppression du compte peut être demandée depuis l’espace utilisateur ou par email. Les limites du Freemium peuvent évoluer pour préserver la qualité, les coûts et l’équilibre du service ; toute modification substantielle sera présentée clairement aux utilisateurs.</p></section>
      <section><h2>12. Droit applicable et contact</h2><p>Les présentes conditions sont soumises au droit français. Toute question peut être adressée à <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>.</p></section>
      <p className="mt-10 border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 30 juillet 2026.</p>
    </EditorialShell>
  );
}
