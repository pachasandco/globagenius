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
  title: "Globe Genius — Packages Voyage a Prix Casses",
  description:
    "Notre IA detecte les anomalies de prix pour vous trouver des packages voyage (vol + hotel) a -40% minimum sur le prix marche.",
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
