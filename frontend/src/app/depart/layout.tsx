import { PublicHeader, SiteFooter } from "../_components/SiteChrome";

export default function AirportLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="depart-route-shell min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <PublicHeader compact />
      {children}
      <SiteFooter />
    </div>
  );
}
