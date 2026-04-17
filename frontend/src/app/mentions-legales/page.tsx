import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mentions légales — Globe Genius",
  description: "Mentions légales et conditions générales d'utilisation du service Globe Genius.",
  alternates: { canonical: "https://globegenius.app/mentions-legales" },
};

export default function MentionsLegales() {
  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 md:px-5 h-[64px] flex items-center">
          <Link href="/" className="flex items-end gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-10 h-10 shrink-0 object-contain" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">Globe Genius</span>
          </Link>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 md:px-5 py-12">
        <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl mb-8 text-[#0A1F3D]">Mentions légales</h1>

        <div className="prose prose-gray max-w-none text-[#0A1F3D]/80 space-y-8">
          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Éditeur du site</h2>
            <p>
              Le site <strong>globegenius.app</strong> est édité par Globe Genius.<br />
              Email de contact : <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a>
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Hébergement</h2>
            <p>
              Le site est hébergé par Railway Corporation, 548 Market St, San Francisco, CA 94104, États-Unis.<br />
              Site : <a href="https://railway.app" className="text-[#FF6B47] hover:underline" target="_blank" rel="noopener noreferrer">railway.app</a>
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Propriété intellectuelle</h2>
            <p>
              L&apos;ensemble du contenu du site (textes, images, logos, design) est la propriété exclusive de Globe Genius, sauf mention contraire. Toute reproduction, représentation, modification ou adaptation de tout ou partie du site est interdite sans autorisation écrite préalable.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Données personnelles</h2>
            <p>
              Globe Genius collecte les données suivantes lors de l&apos;inscription : adresse email, préférences de voyage (aéroports de départ, destinations). Ces données sont utilisées uniquement pour le fonctionnement du service (alertes Telegram, personnalisation des deals).
            </p>
            <p>
              Les données sont stockées sur des serveurs sécurisés (Supabase, Railway). Elles ne sont jamais vendues ni partagées avec des tiers à des fins commerciales.
            </p>
            <p>
              Conformément au RGPD, vous disposez d&apos;un droit d&apos;accès, de rectification et de suppression de vos données. Pour exercer ces droits, contactez <a href="mailto:contact@globegenius.app" className="text-[#FF6B47] hover:underline">contact@globegenius.app</a>.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Cookies</h2>
            <p>
              Le site utilise des cookies techniques nécessaires au fonctionnement du service (authentification, session). Aucun cookie publicitaire ou de tracking tiers n&apos;est utilisé.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Liens affiliés</h2>
            <p>
              Globe Genius participe au programme d&apos;affiliation Travelpayouts. Les liens de réservation vers Aviasales et Booking.com contiennent un identifiant affilié. Globe Genius perçoit une commission sur les réservations effectuées via ces liens, sans surcoût pour l&apos;utilisateur.
            </p>
          </section>

          <section>
            <h2 className="font-[family-name:var(--font-dm-serif)] text-xl text-[#0A1F3D]">Limitation de responsabilité</h2>
            <p>
              Globe Genius s&apos;efforce de fournir des informations exactes et à jour sur les prix des vols. Cependant, les prix affichés sont issus de sources tierces (Travelpayouts/Aviasales) et peuvent varier entre le moment de la détection et la réservation effective. Globe Genius ne garantit pas la disponibilité des tarifs affichés.
            </p>
          </section>
        </div>
      </div>

      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-4xl mx-auto px-4 md:px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 · <Link href="/conditions" className="hover:text-gray-500">CGV</Link> · <Link href="/confidentialite" className="hover:text-gray-500">Confidentialité</Link>
        </div>
      </footer>
    </div>
  );
}
