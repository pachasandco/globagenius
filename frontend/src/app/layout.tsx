import type { Metadata } from "next";
import { DM_Serif_Display, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  weight: "400",
  variable: "--font-dm-serif",
  subsets: ["latin"],
  display: "swap",
});

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Globe Genius — Vols à Prix Cassés | Alertes Telegram temps réel",
  description:
    "Globe Genius détecte les vols aller-retour à prix anormalement bas sur 9 aéroports français. Chaque deal est statistiquement vérifié et reconfirmé en temps réel avant l'alerte Telegram.",
  verification: {
    google: "gf0vDAPS9U-Eb_qc6b9U7wDyKs04Ptlk8u3Z5WZmL2c",
  },
  keywords: [
    "vol pas cher alerte",
    "deal vol aller-retour",
    "erreur de prix vol",
    "alerte voyage telegram",
    "bons plans voyage",
    "vol prix cassé",
    "vol pas cher Paris",
    "détecter deal vol",
  ],
  metadataBase: new URL("https://globegenius.app"),
  openGraph: {
    title: "Globe Genius — Vols à Prix Cassés | Alertes Telegram temps réel",
    description:
      "Détection des vols aller-retour à prix anormalement bas sur 9 aéroports français. Alertes Telegram dès qu'un deal est confirmé.",
    url: "https://globegenius.app",
    siteName: "Globe Genius",
    images: [
      {
        url: "https://globegenius.app/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Globe Genius — Vols à Prix Cassés",
      },
    ],
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Globe Genius — Vols à Prix Cassés",
    description:
      "Détection de vols aller-retour à prix anormalement bas. Alertes Telegram temps réel. 9 aéroports français.",
    images: ["https://globegenius.app/opengraph-image"],
    creator: "@globegenius",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="fr"
      className={`${dmSerif.variable} ${plusJakarta.variable}`}
    >
      <body className="min-h-screen w-full">
        {/* JSON-LD Structured Data — server-rendered for SEO
            All values are static constants, no user input — safe for JSON-LD */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Organization",
              "@id": "https://globegenius.app/#organization",
              name: "Globe Genius",
              url: "https://globegenius.app",
              logo: {
                "@type": "ImageObject",
                url: "https://globegenius.app/globe1.png",
                width: 512,
                height: 512,
              },
              description:
                "Globe Genius détecte les vols aller-retour à prix anormalement bas sur les 9 aéroports français. Alertes Telegram dès qu\u2019une anomalie est confirmée.",
              sameAs: ["https://t.me/Globegenius_bot"],
              contactPoint: {
                "@type": "ContactPoint",
                contactType: "customer support",
                email: "contact@globegenius.app",
                availableLanguage: "French",
              },
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              "@id": "https://globegenius.app/#website",
              name: "Globe Genius",
              url: "https://globegenius.app",
              description:
                "Deals vols à prix cassés. Vols aller-retour avec anomalies de prix confirmées, alertes Telegram.",
              inLanguage: "fr-FR",
              publisher: { "@id": "https://globegenius.app/#organization" },
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Globe Genius",
              operatingSystem: "Web",
              applicationCategory: "TravelApplication",
              offers: {
                "@type": "AggregateOffer",
                lowPrice: "0",
                highPrice: "29",
                priceCurrency: "EUR",
                offerCount: 2,
              },
              url: "https://globegenius.app",
              description:
                "Détecteur de vols à prix cassés. Alertes Telegram en temps réel sur les meilleurs deals au départ de 9 aéroports français.",
            }),
          }}
        />
        {children}
      </body>
    </html>
  );
}
