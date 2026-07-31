import type { Metadata } from "next";
import { AppRouteShell } from "../_components/SiteChrome";

export const metadata: Metadata = {
  title: "Mes deals — GlobeGenius",
  description: "Espace privé des opportunités GlobeGenius.",
  robots: { index: false, follow: false },
};

export default function DealsLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AppRouteShell route="deals">{children}</AppRouteShell>;
}
