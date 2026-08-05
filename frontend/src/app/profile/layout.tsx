import type { Metadata } from "next";
import { AppRouteShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Mon profil — GlobeGenius",
  description: "Préférences et paramètres du compte GlobeGenius.",
  robots: { index: false, follow: false },
};

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return <AppRouteShell route="profile">{children}</AppRouteShell>;
}
