import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../../../_components/Wordmark";

type PageProps = { params: Promise<{ number: string; name: string }> };

function clean(name: string): string {
  return decodeURIComponent(name).slice(0, 24);
}

function ogNumber(number: string): string {
  return (decodeURIComponent(number).replace(/[^0-9]/g, "") || "1").slice(0, 4);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { number, name } = await params;
  const display = clean(name);
  const n = ogNumber(number);
  const url = `https://globegenius.app/badge/${number}/${name}`;
  return {
    title: `${display} · OG #${n} — Membre fondateur GlobeGenius`,
    description: `${display} est OG #${n}, membre fondateur de l'Active Beta GlobeGenius.`,
    alternates: { canonical: url },
    openGraph: {
      title: `${display} · OG #${n} — Membre fondateur`,
      description: "A façonné GlobeGenius dès les premiers jours.",
      url,
      type: "profile",
    },
    twitter: { card: "summary_large_image" },
  };
}

// HTML/CSS twin of the OG seal so the landing page itself looks like the
// shared image (concentric gold rings, globe, OG #n, name).
function Seal({ display, n }: { display: string; n: string }) {
  return (
    <div
      className="relative flex items-center justify-center rounded-full"
      style={{
        width: 360,
        height: 360,
        background: "#0A1F3D",
        border: "3px solid #E8C37E",
        boxShadow:
          "0 0 0 11px #0A1F3D, 0 0 0 13px rgba(232,195,126,0.35), 0 30px 80px rgba(0,0,0,0.45)",
      }}
    >
      <div
        className="absolute top-5 text-[#E8C37E] font-bold uppercase"
        style={{ fontSize: 17, letterSpacing: 6 }}
      >
— Membre fondateur —
      </div>

      <div
        className="flex flex-col items-center justify-center rounded-full"
        style={{
          width: 252,
          height: 252,
          border: "2px solid rgba(232,195,126,0.45)",
          background:
            "radial-gradient(circle at 50% 35%, rgba(255,107,71,0.18) 0%, rgba(10,31,61,0) 60%)",
        }}
      >
        <div
          className="flex items-center justify-center rounded-full mb-1"
          style={{
            width: 66,
            height: 66,
            background: "#FF6B47",
            fontSize: 36,
            boxShadow: "0 8px 24px rgba(255,107,71,0.4)",
          }}
        >
          🌍
        </div>
        <div
          className="text-[#FFF8F0] font-bold leading-none"
          style={{ fontSize: 58, letterSpacing: 3 }}
        >
          OG
        </div>
        <div className="text-[#E8C37E] font-bold" style={{ fontSize: 30 }}>
          #{n}
        </div>
        <div
          className="my-3"
          style={{ width: 96, height: 2, background: "rgba(232,195,126,0.5)" }}
        />
        <div
          className="text-[#FFF8F0] font-bold text-center px-4"
          style={{ fontSize: 24, maxWidth: 230 }}
        >
          {display}
        </div>
      </div>
    </div>
  );
}

export default async function BadgePage({ params }: PageProps) {
  const { number, name } = await params;
  const display = clean(name);
  const n = ogNumber(number);

  return (
    <div className="min-h-screen bg-[#0A1F3D] flex flex-col items-center justify-center px-6 py-12 text-center">
      <Link
        href="/"
        className="font-[family-name:var(--font-dm-serif)] text-lg text-white mb-10"
      >
        <Wordmark />
      </Link>

      <Seal display={display} n={n} />

      <p className="text-[var(--color-coral)] font-bold uppercase tracking-widest text-sm mt-8 mb-3">
        OG #{n} · Membre fondateur
      </p>
      <p className="text-gray-400 max-w-md leading-relaxed mb-10">
        {display} fait partie des tout premiers à avoir fait vivre la beta de
        GlobeGenius — usage, retours honnêtes et partages qui ont façonné le
        produit dès ses débuts. 🙏
      </p>

      <Link
        href="/beta"
        className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-3 rounded-xl font-bold transition-colors"
      >
        Rejoindre la beta
      </Link>

      <p className="text-gray-600 text-xs mt-8">globegenius.app</p>
    </div>
  );
}
