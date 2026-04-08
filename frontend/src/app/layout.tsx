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
  title: "Globe Genius — Packages Voyage à Prix Cassés | -40% minimum",
  description:
    "Globe Genius détecte les anomalies de prix pour vous trouver des packages voyage (vol + hôtel) à -40% minimum sur le prix du marché. Alertes Telegram, 8 aéroports français couverts.",
  keywords: [
    "packages voyage pas cher",
    "vol hôtel prix cassé",
    "deal voyage IA",
    "alerte voyage telegram",
    "bons plans voyage",
    "package vol hotel",
    "voyage prix cassé france",
    "offre voyage dernière minute",
  ],
  metadataBase: new URL("https://www.globegenius.app"),
  alternates: {
    canonical: "https://www.globegenius.app",
  },
  openGraph: {
    title: "Globe Genius — Packages Voyage à Prix Cassés | -40% minimum",
    description:
      "Notre IA détecte les anomalies de prix pour vous trouver des packages voyage (vol + hôtel) à -40% minimum sur le prix du marché. Recevez les alertes sur Telegram.",
    url: "https://www.globegenius.app",
    siteName: "Globe Genius",
    images: [
      {
        url: "https://www.globegenius.app/og-image.png",
        width: 1200,
        height: 630,
        alt: "Globe Genius — Packages Voyage à Prix Cassés",
      },
    ],
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Globe Genius — Packages Voyage à Prix Cassés | -40% minimum",
    description:
      "Notre IA détecte les anomalies de prix pour des packages voyage (vol + hôtel) à -40% minimum. Alertes sur Telegram.",
    images: ["https://www.globegenius.app/og-image.png"],
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
