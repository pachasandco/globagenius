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
    "Globe Genius détecte les vols aller-retour à prix anormalement bas sur 8 aéroports français. Chaque deal est statistiquement vérifié et reconfirmé en temps réel avant l'alerte Telegram.",
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
  alternates: {},
  openGraph: {
    title: "Globe Genius — Vols à Prix Cassés | Alertes Telegram temps réel",
    description:
      "Détection des vols aller-retour à prix anormalement bas sur 8 aéroports français. Alertes Telegram dès qu'un deal est confirmé.",
    url: "https://globegenius.app",
    siteName: "Globe Genius",
    images: [
      {
        url: "https://globegenius.app/og-image.png",
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
      "Détection de vols aller-retour à prix anormalement bas. Alertes Telegram temps réel. 8 aéroports français.",
    images: ["https://globegenius.app/og-image.png"],
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
        {children}
      </body>
    </html>
  );
}
