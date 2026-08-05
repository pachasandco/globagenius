import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Créer un compte — GlobeGenius",
  description: "Activez gratuitement le radar GlobeGenius de votre aéroport.",
  robots: { index: false, follow: true },
};

export default function BetaPage() {
  redirect("/signup?utm_source=legacy_beta&utm_medium=redirect&utm_campaign=freemium_activation");
}
