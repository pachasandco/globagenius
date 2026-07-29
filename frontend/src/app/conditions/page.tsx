import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../_components/Wordmark";

export const metadata: Metadata = {
  title: "Conditions d’utilisation et de vente — GlobeGenius",
  description: "Conditions du Freemium GlobeGenius, de Premium Découverte et de la future offre Premium à 49 € par an.",
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
          <strong className="text-[#0B2A3F]">Information avant lancement du paiement :</strong> Premium est prévu à 49 € TTC par an, mais Stripe n’est pas encore ouvert. La création d’un compte, les 7 jours de Premium Découverte et le passage au Freemium n’entraînent aucun paiement, aucun renouvellement et aucune demande de carte bancaire.
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
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">3. Premium Découverte — 7 jours</h2>
            <p className="mt-3">Un nouveau compte public peut bénéficier une seule fois de <strong className="text-[#0B2A3F]">7 jours de Premium Découverte</strong>. La période commence lors de la première connexion du compte au bot Telegram GlobeGenius, afin que l’utilisateur puisse réellement recevoir et évaluer les alertes.</p>
            <p className="mt-3">Pendant cette période, les fonctions Premium sont accessibles sans carte bancaire et sans engagement. À son terme, le compte passe automatiquement au Freemium, sauf si l’utilisateur détient un badge OG ou bénéficie d’un autre droit Premium valide.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">4. Formule Freemium</h2>
            <p className="mt-3">Après la période de découverte, la formule Freemium permet actuellement :</p>
            <ul className="mt-3 list-disc space-y-2 pl-6">
              <li>la surveillance d’un aéroport de départ principal ;</li>
              <li>jusqu’à deux alertes aller-retour complètes et instantanées par période glissante de sept jours ;</li>
              <li>une alerte aller-retour exceptionnelle complète par période glissante de trente jours ;</li>
              <li>un joker par période glissante de trente jours pour révéler le prix, les dates et le lien d’un deal Premium présenté dans l’espace utilisateur ;</li>
              <li>l’accès aux teasers des autres opportunités, aux préférences essentielles et aux guides destination.</li>
            </ul>
            <p className="mt-3">Les allers simples, les combinaisons de billets, les alertes sans quota, les réglages avancés et l’utilisation de plusieurs aéroports restent réservés aux comptes Premium. Les alertes gratuites ne sont pas retardées artificiellement : GlobeGenius limite leur nombre plutôt que d’envoyer un tarif potentiellement périmé.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">5. Badge OG</h2>
            <p className="mt-3">Le maintien du Premium fondateur est réservé aux comptes auxquels GlobeGenius a effectivement attribué un <strong className="text-[#0B2A3F]">badge OG</strong>. Ce badge matérialise une contribution reconnue à la phase fondatrice du produit.</p>
            <p className="mt-3">Les anciens comptes de beta qui ne disposent pas de ce badge utilisent la formule Freemium. Les droits liés à un abonnement payant, à un essai en cours ou à une attribution administrative distincte ne sont pas concernés par cette règle.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">6. Offre Premium prévue</h2>
            <p className="mt-3">L’offre Premium sera proposée au tarif public de <strong className="text-[#0B2A3F]">49 € TTC par an</strong>, payable en une fois. Elle est destinée à inclure toutes les alertes qualifiées sans quota Freemium, plusieurs aéroports, les deals exceptionnels, les allers simples, les combos malins et des options de personnalisation supplémentaires.</p>
            <p className="mt-3">Les comparaisons de rentabilité présentées sur le site sont des illustrations. Une économie de 100 € sur un billet représente plus de deux années à 49 €, et une économie de 150 € plus de trois, mais GlobeGenius ne garantit ni le montant d’une économie, ni la disponibilité d’un tarif, ni la réalisation d’une réservation.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">7. Paiement et renouvellement à l’ouverture</h2>
            <p className="mt-3">Lorsque le paiement sera activé, il sera traité par Stripe. Avant toute validation, l’utilisateur verra le prix, la durée, les conditions de renouvellement et le moyen d’annulation. Aucun prélèvement ne sera effectué avant une action explicite de souscription.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">8. Garantie commerciale prévue</h2>
            <p className="mt-3">À l’ouverture de Premium, GlobeGenius prévoit une garantie satisfait ou remboursé de 30 jours à compter de la souscription. Les modalités opérationnelles seront rappelées au moment du paiement et pourront être exercées par email à <a href="mailto:contact@globegenius.app" className="font-medium text-[#0E7490] hover:underline">contact@globegenius.app</a>.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">9. Prix et disponibilité des vols</h2>
            <p className="mt-3">Les prix proviennent de partenaires et de systèmes tiers. Ils peuvent évoluer ou disparaître entre la détection, l’alerte et la réservation. Les frais de bagages, options, conditions de modification et conditions d’annulation relèvent du vendeur du billet.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">10. Responsabilité</h2>
            <p className="mt-3">GlobeGenius fournit un service d’information et de mise en relation. L’utilisateur reste seul responsable de la vérification du trajet, des dates, des formalités, des visas, des correspondances et des conditions du vendeur avant de réserver.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">11. Données, évolution du service et suppression du compte</h2>
            <p className="mt-3">Les modalités relatives aux données personnelles sont décrites dans la <Link href="/confidentialite" className="font-medium text-[#0E7490] hover:underline">politique de confidentialité</Link>. La suppression du compte peut être demandée depuis l’espace utilisateur ou par email. Les limites du Freemium peuvent évoluer pour préserver la qualité, les coûts et l’équilibre du service ; toute modification substantielle sera présentée clairement aux utilisateurs.</p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[#0B2A3F]">12. Droit applicable et contact</h2>
            <p className="mt-3">Les présentes conditions sont soumises au droit français. Toute question peut être adressée à <a href="mailto:contact@globegenius.app" className="font-medium text-[#0E7490] hover:underline">contact@globegenius.app</a>.</p>
          </section>

          <p className="border-t border-[#D9E2E3] pt-6 text-sm text-slate-400">Dernière mise à jour : 29 juillet 2026.</p>
        </div>
      </main>
    </div>
  );
}
