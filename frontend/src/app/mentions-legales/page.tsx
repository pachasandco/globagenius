import type { Metadata } from "next";
import { EditorialShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Mentions légales — GlobeGenius",
  description: "Mentions légales du service GlobeGenius.",
  alternates: { canonical: "https://globegenius.app/mentions-legales" },
  robots: { index: false, follow: false },
};

export default function MentionsLegales() {
  return (
    <EditorialShell eyebrow="Informations légales" title="Mentions légales" intro="Les informations relatives à l’édition, à l’hébergement et au fonctionnement du site GlobeGenius.">
      <section><h2>Éditeur du site</h2><p>Le site <strong>globegenius.app</strong> est édité par GlobeGenius. Contact : <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>.</p></section>
      <section><h2>Hébergement</h2><p>Le service applicatif est hébergé par Railway Corporation. Les composants techniques peuvent également s’appuyer sur des prestataires spécialisés nécessaires au fonctionnement de GlobeGenius.</p></section>
      <section><h2>Propriété intellectuelle</h2><p>Les textes, éléments graphiques, interfaces, logos et composants originaux du site sont protégés. Leur reproduction ou adaptation substantielle nécessite une autorisation préalable, sauf exception prévue par la loi.</p></section>
      <section><h2>Données personnelles</h2><p>Les modalités de traitement des données et l’exercice des droits sont détaillés dans la <a href="/confidentialite">politique de confidentialité</a>.</p></section>
      <section><h2>Cookies et session</h2><p>Le site utilise les mécanismes techniques nécessaires à l’authentification, à la continuité de session et à l’attribution de campagne. Aucun cookie publicitaire tiers n’est requis pour accéder au service.</p></section>
      <section><h2>Liens affiliés</h2><p>Certains liens de réservation peuvent contenir un identifiant affilié. GlobeGenius peut percevoir une commission lorsqu’une réservation éligible est réalisée, sans modification du prix facturé à l’utilisateur. Les liens d’alerte peuvent passer par une URL courte GlobeGenius afin d’enregistrer l’ouverture avant la redirection.</p></section>
      <section><h2>Limitation de responsabilité</h2><p>Les tarifs sont fournis par des services tiers et peuvent évoluer rapidement. GlobeGenius ne vend pas le billet, ne garantit pas la disponibilité finale du prix et invite l’utilisateur à vérifier toutes les informations auprès du vendeur avant de réserver.</p></section>
      <section><h2>Contact</h2><p>Pour toute question : <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>.</p></section>
      <p className="mt-10 border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 31 juillet 2026.</p>
    </EditorialShell>
  );
}
