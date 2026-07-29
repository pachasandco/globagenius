import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../_components/Wordmark";

export const metadata: Metadata = {
  title: "Conditions d’utilisation et de vente — GlobeGenius",
  description: "Conditions d’utilisation du service GlobeGenius et conditions prévues pour l’offre Premium à 49 € par an.",
  alternates: { canonical: "https://globegenius.app/conditions" },
  robots: { index: false, follow: false },
};

export default function Conditions() {
  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <nav className="border-b border-[#D9E2E3] bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-4xl items-center px-5">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl"><Wordmark /></Link>
        </div>
      </nav>

      <main className="mx-auto max-w-4xl px-5 py-12">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0E7490]">Cadre contractuel</p>
        <h1 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl">Conditions d’utilisation et de vente</h1>

        <div className="mt-8 rounded-2xl border border-[#2AB7A9]/30 bg-[#E9F5F7] p-5 text-sm leading-7 text-slate-600">
          <strong className="text-[#0B2A3F]">Information avant lancement du paiement :</strong> l’abonnement Premium est prévu à 49 € par an, mais Stripe n’est pas encore ouvert aux utilisateurs. La création d’un compte n’entraîne actuellement aucun paiement, aucun renouvellement et aucune demande de carte bancaire.
        </div>

        <div className="mt-10 space-y-9 text-[15px] leading-8 text-slate-600">
          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">1. Objet</h2>
            <p className="mt-3">Les présentes conditions encadrent l’utilisation de GlobeGenius, accessible sur globegenius.app, ainsi que la future souscription à l’offre Premium lorsqu’elle sera commercialement ouverte.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">2. Description du service</h2>
            <p className="mt-3">GlobeGenius détecte des tarifs aériens susceptibles d’être anormalement bas, les compare à un prix habituel observé, effectue des contrôles supplémentaires et envoie des alertes sur Telegram. GlobeGenius ne vend pas les billets et n’agit pas comme agence de voyage.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">3. Comptes gratuits</h2>
            <p className="mt-3">La création d’un compte permet de configurer des aéroports et des préférences d’alertes. La réception des alertes nécessite la connexion du compte au bot Telegram GlobeGenius. Les fonctionnalités gratuites, limites d’usage et seuils de sélection peuvent évoluer pour préserver la qualité du service.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">4. Offre Premium prévue</h2>
            <p className="mt-3">L’offre Premium sera proposée au tarif public de <strong className="text-[#0B2A3F]">49 € TTC par an</strong>, payable en une fois. Elle est destinée à inclure davantage d’alertes qualifiées, les deals exceptionnels, les allers simples, les combos malins et des options de personnalisation supplémentaires.</p>
            <p className="mt-3">Les comparaisons de rentabilité présentées sur le site sont des illustrations : une économie de 100 € sur un billet représente plus de deux années à 49 €, mais GlobeGenius ne garantit ni le montant d’une économie, ni la disponibilité d’un tarif, ni la réalisation d’une réservation.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">5. Paiement et renouvellement à l’ouverture</h2>
            <p className="mt-3">Lorsque le paiement sera activé, il sera traité par Stripe. Avant toute validation, l’utilisateur verra le prix, la durée, les conditions de renouvellement et le moyen d’annulation. Aucun prélèvement ne sera effectué avant une action explicite de souscription.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">6. Garantie commerciale prévue</h2>
            <p className="mt-3">À l’ouverture de Premium, GlobeGenius prévoit une garantie satisfait ou remboursé de 30 jours à compter de la souscription. Les modalités opérationnelles seront rappelées au moment du paiement et pourront être exercées par email à <a href="mailto:contact@globegenius.app" className="font-medium text-[#0E7490] hover:underline">contact@globegenius.app</a>.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">7. Prix et disponibilité des vols</h2>
            <p className="mt-3">Les prix proviennent de partenaires et de systèmes tiers. Ils peuvent évoluer ou disparaître entre la détection, l’alerte et la réservation. Les frais de bagages, options, conditions de modification et conditions d’annulation relèvent du vendeur du billet.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">8. Responsabilité</h2>
            <p className="mt-3">GlobeGenius fournit un service d’information et de mise en relation. L’utilisateur reste seul responsable de la vérification du trajet, des dates, des formalités, des visas, des correspondances et des conditions du vendeur avant de réserver.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">9. Données et suppression du compte</h2>
            <p className="mt-3">Les modalités relatives aux données personnelles sont décrites dans la <Link href="/confidentialite" className="font-medium text-[#0E7490] hover:underline">politique de confidentialité</Link>. La suppression du compte peut être demandée depuis l’espace utilisateur ou par email.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">10. Droit applicable et contact</h2>
            <p className="mt-3">Les présentes conditions sont soumises au droit français. Toute question peut être adressée à <a href="mailto:contact@globegenius.app" className="font-medium text-[#0E7490] hover:underline">contact@globegenius.app</a>.</p>
          </section>

          <p className="border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 29 juillet 2026.</p>
        </div>
      </main>
    </div>
  );
}
