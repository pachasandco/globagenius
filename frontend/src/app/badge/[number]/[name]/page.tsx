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
function Seal({ n }: { n: string }) {
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
          className="mb-2 flex items-center justify-center rounded-full"
          style={{
            width: 72,
            height: 72,
            background: "#FF6B47",
            fontSize: 40,
            boxShadow: "0 8px 24px rgba(255,107,71,0.4)",
          }}
        >
          🌍
        </div>
        <div
          className="font-bold leading-none text-[#FFF8F0]"
          style={{ fontSize: 64, letterSpacing: 3 }}
        >
          OG
        </div>
        <div className="mt-1 font-bold text-[#E8C37E]" style={{ fontSize: 34 }}>
          #{n}
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0A1F3D] px-6 py-12 text-center">
      <Link href="/" className="mb-10 inline-flex" aria-label="Retour à l’accueil GlobeGenius">
        <Wordmark variant="inverse" size="md" className="opacity-95" />
      </Link>

      <Seal n={n} />

      <p className="mb-3 mt-8 text-sm font-bold uppercase tracking-widest text-[var(--color-coral)]">
        OG #{n} · Membre fondateur
      </p>
      <p className="mb-10 max-w-md leading-relaxed text-gray-400">
        {display} fait partie des tout premiers à avoir fait vivre la beta de
        GlobeGenius — usage, retours honnêtes et partages qui ont façonné le
        produit dès ses débuts. 🙏
      </p>

      <Link
        href="/beta"
        className="inline-block rounded-xl bg-[var(--color-coral)] px-8 py-3 font-bold text-white transition-colors hover:bg-[var(--color-coral-hover)]"
      >
        Rejoindre la beta
      </Link>

      <p className="mt-8 text-xs text-gray-600">globegenius.app</p>
    </div>
  );
}
