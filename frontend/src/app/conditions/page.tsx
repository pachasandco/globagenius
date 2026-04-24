import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Conditions Générales de Vente — Globe Genius",
  description: "Conditions générales de vente et d'utilisation du service Globe Genius Premium.",
  alternates: { canonical: "https://globegenius.app/conditions" },
  robots: { index: false, follow: false },
};

export default function Conditions() {
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
        <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl mb-8 text-[#0A1F3D]">Conditions Générales de Vente</h1>

        <div className="prose prose-gray max-w-none text-[#0A1F3D]/80 space-y-8">
          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 1 — Objet</h2>
            <p>
              Les présentes Conditions Générales de Vente (CGV) régissent l&apos;utilisation du service Globe Genius, accessible à l&apos;adresse <strong>globegenius.app</strong>, et la souscription à l&apos;abonnement Premium.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 2 — Description du service</h2>
            <p>Globe Genius est un service de détection automatique de vols à prix anormalement bas au départ de 8 aéroports français. Le service comprend :</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Formule Gratuite :</strong> accès aux deals avec une réduction de 20 à 29% par rapport au prix moyen du marché, consultables sur le site.</li>
              <li><strong>Formule Premium (29€/an) :</strong> accès à tous les deals (réduction de 30% et plus, incluant les erreurs de prix et les promos flash), alertes Telegram instantanées avec liens de réservation directs vers Aviasales et Booking.com.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 3 — Prix et paiement</h2>
            <p>
              L&apos;abonnement Premium est proposé au tarif de <strong>29€ par an</strong>, payable en une seule fois. Le paiement est effectué par carte bancaire via la plateforme sécurisée Stripe. Le prix est indiqué en euros, toutes taxes comprises.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 4 — Droit de rétractation et garantie satisfait ou remboursé</h2>
            <p>
              Conformément à l&apos;article L221-28 du Code de la consommation, le droit de rétractation ne s&apos;applique pas aux services pleinement exécutés avant la fin du délai de rétractation.
            </p>
            <p>
              Toutefois, Globe Genius offre une <strong>garantie satisfait ou remboursé de 30 jours</strong> à compter de la date de souscription. Si vous n&apos;êtes pas satisfait du service, envoyez un email à <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a> dans les 30 jours suivant l&apos;achat pour obtenir un remboursement intégral, sans condition.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 5 — Durée et renouvellement</h2>
            <p>
              L&apos;abonnement Premium est souscrit pour une durée d&apos;un an. Il est renouvelé automatiquement à chaque échéance annuelle, sauf résiliation par l&apos;utilisateur depuis son espace Stripe Customer Portal ou par email à contact@globegenius.app, au plus tard 24 heures avant la date de renouvellement.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 6 — Résiliation</h2>
            <p>
              L&apos;utilisateur peut résilier son abonnement Premium à tout moment depuis son espace client ou par email. La résiliation prend effet à la fin de la période en cours. Aucun remboursement au prorata n&apos;est effectué en dehors de la période de garantie de 30 jours.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 7 — Limitation de responsabilité</h2>
            <p>
              Globe Genius détecte et signale des anomalies de prix sur les vols à partir de données fournies par des tiers (Travelpayouts/Aviasales). Les prix affichés sont indicatifs et peuvent varier entre le moment de la détection et la réservation effective. Globe Genius ne se substitue pas à une agence de voyage et ne vend pas de billets d&apos;avion.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 8 — Droit applicable</h2>
            <p>
              Les présentes CGV sont soumises au droit français. En cas de litige, une solution amiable sera recherchée avant toute action judiciaire. À défaut, les tribunaux français seront compétents.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Article 9 — Contact</h2>
            <p>
              Pour toute question relative aux présentes CGV ou au service Globe Genius :<br />
              Email : <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a>
            </p>
          </section>

          <p className="text-sm text-[#0A1F3D]/40 pt-4">Dernière mise à jour : avril 2026</p>
        </div>
      </div>

      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-4xl mx-auto px-4 md:px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 · <Link href="/mentions-legales" className="hover:text-gray-500">Mentions légales</Link> · <Link href="/confidentialite" className="hover:text-gray-500">Confidentialité</Link>
        </div>
      </footer>
    </div>
  );
}
