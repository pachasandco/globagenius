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

// The illustrated "baroudeur" emblem (same asset as the OG image) with the
// OG number + name overlaid in the central cream medallion, so the landing
// page matches what gets shared on social.
function Seal({ display, n }: { display: string; n: string }) {
  return (
    <div
      className="relative"
      style={{ width: 380, height: 380 }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/badge-bg.png"
        alt=""
        className="absolute inset-0 w-full h-full object-cover rounded-2xl"
      />
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="font-bold leading-none"
          style={{ color: "#0A1F3D", fontSize: 34, letterSpacing: 1 }}
        >
          OG #{n}
        </div>
        <div
          style={{
            width: 64,
            height: 3,
            background: "#FF6B47",
            borderRadius: 2,
            margin: "9px 0",
          }}
        />
        <div
          className="font-bold text-center leading-none px-2"
          style={{ color: "#0A1F3D", fontSize: 27, maxWidth: 200 }}
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
