import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de confidentialité — Globe Genius",
  description: "Politique de confidentialité et protection des données personnelles de Globe Genius.",
  alternates: { canonical: "https://globegenius.app/confidentialite" },
  robots: { index: false, follow: false },
};

export default function Confidentialite() {
  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 md:px-5 h-[64px] flex items-center">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 md:px-5 py-12">
        <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl mb-8 text-[#0A1F3D]">Politique de confidentialité</h1>

        <div className="prose prose-gray max-w-none text-[#0A1F3D]/80 space-y-8">
          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Données collectées</h2>
            <p>Lors de votre utilisation de Globe Genius, nous collectons :</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>À l&apos;inscription :</strong> adresse email, mot de passe (hashé, jamais stocké en clair)</li>
              <li><strong>Préférences de voyage :</strong> aéroports de départ, types d&apos;offres, destinations préférées, seuil minimum de réduction</li>
              <li><strong>Connexion Telegram :</strong> identifiant de chat Telegram (si vous connectez votre compte)</li>
              <li><strong>Paiement :</strong> les données de paiement sont traitées directement par Stripe. Globe Genius ne stocke jamais vos numéros de carte bancaire.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Utilisation des données</h2>
            <p>Vos données sont utilisées exclusivement pour :</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Vous envoyer des alertes personnalisées sur les vols à prix cassés correspondant à vos préférences</li>
              <li>Gérer votre compte et votre abonnement</li>
              <li>Améliorer le service (statistiques anonymes d&apos;utilisation)</li>
            </ul>
            <p className="font-semibold">Vos données ne sont jamais vendues ni partagées avec des tiers à des fins publicitaires.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Stockage et sécurité</h2>
            <p>
              Les données sont stockées sur des serveurs sécurisés :<br />
              Base de données : Supabase (infrastructure AWS, chiffrement au repos et en transit)<br />
              Application : Railway (infrastructure Google Cloud, Europe)
            </p>
            <p>Les mots de passe sont hashés avec bcrypt. Les communications sont chiffrées via HTTPS (TLS 1.3).</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Durée de conservation</h2>
            <p>
              Vos données sont conservées tant que votre compte est actif. En cas de suppression de votre compte, vos données personnelles sont supprimées sous 30 jours. Les données anonymisées à des fins statistiques peuvent être conservées plus longtemps.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Vos droits (RGPD)</h2>
            <p>Conformément au Règlement Général sur la Protection des Données (RGPD), vous disposez des droits suivants :</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Droit d&apos;accès :</strong> obtenir une copie de vos données personnelles</li>
              <li><strong>Droit de rectification :</strong> corriger vos données inexactes</li>
              <li><strong>Droit à l&apos;effacement :</strong> demander la suppression de vos données</li>
              <li><strong>Droit à la portabilité :</strong> recevoir vos données dans un format structuré</li>
              <li><strong>Droit d&apos;opposition :</strong> vous opposer au traitement de vos données</li>
            </ul>
            <p>
              Pour exercer ces droits, contactez-nous à <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a>. Nous répondons sous 30 jours.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Cookies</h2>
            <p>
              Globe Genius utilise uniquement des cookies techniques nécessaires au fonctionnement du service (authentification, session utilisateur). Aucun cookie publicitaire, de tracking ou d&apos;analyse tiers n&apos;est utilisé.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Services tiers</h2>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Stripe :</strong> traitement des paiements (soumis à la <a href="https://stripe.com/privacy" className="text-[#FF6B47] hover:underline" target="_blank" rel="noopener noreferrer">politique de confidentialité Stripe</a>)</li>
              <li><strong>Telegram :</strong> envoi des alertes (soumis à la <a href="https://telegram.org/privacy" className="text-[#FF6B47] hover:underline" target="_blank" rel="noopener noreferrer">politique de confidentialité Telegram</a>)</li>
              <li><strong>Travelpayouts/Aviasales :</strong> données de prix des vols et liens affiliés</li>
            </ul>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Contact</h2>
            <p>
              Pour toute question relative à la protection de vos données :<br />
              Email : <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a>
            </p>
          </section>

          <p className="text-sm text-[#0A1F3D]/40 pt-4">Dernière mise à jour : avril 2026</p>
        </div>
      </div>

      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-4xl mx-auto px-4 md:px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 · <Link href="/mentions-legales" className="hover:text-gray-500">Mentions légales</Link> · <Link href="/conditions" className="hover:text-gray-500">CGV</Link>
        </div>
      </footer>
    </div>
  );
}
