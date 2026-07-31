import type { Metadata } from "next";
import { DM_Serif_Display, Plus_Jakarta_Sans, Geist } from "next/font/google";
import "./globals.css";
import "./site-system.css";
import "./app-routes.css";
import { cn } from "@/lib/utils";
import { CampaignTracker } from "./_components/CampaignTracker";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
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
  title: "GlobeGenius — Alertes vols vérifiées sur Telegram",
  description:
    "GlobeGenius détecte les vols à prix anormalement bas depuis 10 aéroports français, vérifie les tarifs et envoie les alertes sur Telegram.",
  verification: {
    google: "gf0vDAPS9U-Eb_qc6b9U7wDyKs04Ptlk8u3Z5WZmL2c",
  },
  keywords: [
    "alerte vol pas cher",
    "alerte vol Telegram",
    "vol pas cher Paris",
    "vol pas cher Lyon",
    "vol pas cher Marseille",
    "deal vol aller-retour",
    "deal vol aller simple",
    "erreur de prix vol",
    "bons plans voyage",
  ],
  metadataBase: new URL("https://globegenius.app"),
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any", rel: "icon" },
      { url: "/icon.png", type: "image/png", sizes: "512x512" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    shortcut: "/favicon.ico",
  },
  openGraph: {
    title: "GlobeGenius — Les bons plans vols, avant qu’ils disparaissent",
    description:
      "Baisses de prix vérifiées, long-courriers depuis Paris et opportunités depuis les principaux aéroports français. Alertes Telegram.",
    url: "https://globegenius.app",
    siteName: "GlobeGenius",
    images: [{
      url: "https://globegenius.app/opengraph-image",
      width: 1200,
      height: 630,
      alt: "GlobeGenius — Alertes vols vérifiées",
    }],
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "GlobeGenius — Alertes vols vérifiées",
    description: "Les bons plans vols détectés et envoyés sur Telegram avant qu’ils disparaissent.",
    images: ["https://globegenius.app/opengraph-image"],
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

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const organization = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "@id": "https://globegenius.app/#organization",
    name: "GlobeGenius",
    url: "https://globegenius.app",
    logo: {
      "@type": "ImageObject",
      url: "https://globegenius.app/icon.png",
      width: 512,
      height: 512,
    },
    description:
      "Service français de détection et de vérification de baisses de prix sur les vols, avec alertes Telegram.",
    sameAs: ["https://t.me/Globegenius_bot"],
    contactPoint: {
      "@type": "ContactPoint",
      contactType: "customer support",
      email: "contact@globegenius.app",
      availableLanguage: "French",
    },
  };

  const software = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "GlobeGenius",
    operatingSystem: "Web",
    applicationCategory: "TravelApplication",
    url: "https://globegenius.app",
    description:
      "Détecteur de vols à prix anormalement bas avec alertes Telegram depuis 10 aéroports français.",
    offers: [
      {
        "@type": "Offer",
        name: "Compte gratuit",
        price: "0",
        priceCurrency: "EUR",
        availability: "https://schema.org/InStock",
      },
      {
        "@type": "Offer",
        name: "GlobeGenius Premium annuel",
        price: "39",
        priceCurrency: "EUR",
        availability: "https://schema.org/PreOrder",
        priceSpecification: {
          "@type": "UnitPriceSpecification",
          price: "39",
          priceCurrency: "EUR",
          billingDuration: "P1Y",
        },
      },
    ],
  };

  return (
    <html lang="fr" className={cn(dmSerif.variable, plusJakarta.variable, "font-sans", geist.variable)}>
      <body className="site-page min-h-screen w-full">
        <CampaignTracker />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(software) }} />
        {children}
      </body>
    </html>
  );
}
