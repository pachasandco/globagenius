import type { Metadata } from "next";
import { EditorialShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Politique de confidentialité — GlobeGenius",
  description: "Politique de confidentialité et protection des données personnelles de GlobeGenius.",
  alternates: { canonical: "https://globegenius.app/confidentialite" },
  robots: { index: false, follow: false },
};

export default function Confidentialite() {
  return (
    <EditorialShell eyebrow="Protection des données" title="Politique de confidentialité" intro="Les données utilisées par GlobeGenius, leur finalité et les moyens dont vous disposez pour garder le contrôle.">
      <section>
        <h2>Données collectées</h2>
        <p>Lors de votre utilisation de GlobeGenius, nous pouvons collecter :</p>
        <ul className="mt-3 list-disc space-y-2 pl-6">
          <li><strong>À l’inscription :</strong> adresse email et mot de passe hashé, jamais stocké en clair ;</li>
          <li><strong>Préférences de voyage :</strong> aéroports de départ, types d’offres et réglages d’alertes ;</li>
          <li><strong>Connexion Telegram :</strong> identifiant de chat lorsque vous associez le bot à votre compte ;</li>
          <li><strong>Paiement :</strong> les données bancaires sont traitées par Stripe et ne sont pas stockées par GlobeGenius ;</li>
          <li><strong>Utilisation des alertes :</strong> ouverture des liens courts GlobeGenius et feedback volontaire sur la pertinence d’une alerte.</li>
        </ul>
      </section>

      <section>
        <h2>Utilisation des données</h2>
        <p>Les données servent à personnaliser les alertes, gérer le compte et l’abonnement, sécuriser le service, mesurer la qualité des alertes et améliorer le produit.</p>
        <p><strong>Les données personnelles ne sont pas vendues à des annonceurs.</strong></p>
      </section>

      <section>
        <h2>Prestataires techniques</h2>
        <p>GlobeGenius utilise des prestataires nécessaires au fonctionnement du service, notamment Supabase pour la base de données, Railway pour l’hébergement applicatif, Stripe pour les paiements, Telegram pour l’envoi des alertes et Brevo pour certains emails transactionnels ou marketing lorsque le consentement requis a été donné.</p>
        <p>Les données transmises à chaque prestataire sont limitées à ce qui est nécessaire à sa fonction.</p>
      </section>

      <section>
        <h2>Durée de conservation</h2>
        <p>Les données du compte sont conservées pendant la durée d’utilisation du service. Lorsqu’un compte est supprimé, les données personnelles associées sont effacées ou anonymisées dans les délais nécessaires au traitement de la demande et aux obligations légales applicables.</p>
      </section>

      <section>
        <h2>Vos droits</h2>
        <p>Conformément au RGPD, vous disposez notamment d’un droit d’accès, de rectification, d’effacement, de limitation, de portabilité et d’opposition lorsque les conditions légales sont réunies.</p>
        <p>Pour exercer un droit ou poser une question, écrivez à <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>. Une réponse est apportée dans le délai légal applicable.</p>
      </section>

      <section>
        <h2>Cookies et mesure de campagne</h2>
        <p>GlobeGenius utilise les éléments techniques nécessaires à l’authentification et à la continuité de session. Les paramètres de campagne présents dans une URL peuvent également être mémorisés afin d’attribuer une inscription à sa source marketing. Aucun cookie publicitaire tiers n’est requis pour utiliser le service.</p>
      </section>

      <section>
        <h2>Liens de redirection</h2>
        <p>Les liens d’alerte peuvent passer par une URL courte GlobeGenius avant de rediriger vers le vendeur du billet. Ce mécanisme permet d’enregistrer le fait qu’un lien a été ouvert, son heure et la destination concernée afin d’évaluer la qualité des alertes.</p>
      </section>

      <section>
        <h2>Contact et réclamation</h2>
        <p>Contact : <a href="mailto:contact@globegenius.app">contact@globegenius.app</a>. Vous pouvez également introduire une réclamation auprès de l’autorité de contrôle compétente si vous estimez que vos droits ne sont pas respectés.</p>
      </section>

      <p className="mt-10 border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 31 juillet 2026.</p>
    </EditorialShell>
  );
}
