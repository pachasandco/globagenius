import Link from "next/link";
import type { Metadata } from "next";
import { Wordmark } from "../../_components/Wordmark";

type PageProps = { params: Promise<{ name: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { name } = await params;
  const display = decodeURIComponent(name).slice(0, 24);
  const url = `https://globegenius.app/badge/${name}`;
  return {
    title: `${display} · Membre fondateur Active Beta — GlobeGenius`,
    description: `${display} fait partie des membres fondateurs Active Beta de GlobeGenius.`,
    alternates: { canonical: url },
    openGraph: {
      title: `${display} · Membre fondateur Active Beta`,
      description: "A façonné GlobeGenius dès les premiers jours.",
      url,
      type: "profile",
    },
    twitter: { card: "summary_large_image" },
  };
}

export default async function BadgePage({ params }: PageProps) {
  const { name } = await params;
  const display = decodeURIComponent(name).slice(0, 24);

  return (
    <div className="min-h-screen bg-[#0A1F3D] flex flex-col items-center justify-center px-6 py-12 text-center">
      <Link
        href="/"
        className="font-[family-name:var(--font-dm-serif)] text-lg text-white mb-10"
      >
        <Wordmark />
      </Link>

      <div className="text-7xl mb-4">🏅</div>
      <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-white mb-2">
        {display}
      </h1>
      <p className="text-[var(--color-coral)] font-bold uppercase tracking-widest text-sm mb-6">
        Membre fondateur · Active Beta
      </p>
      <p className="text-gray-400 max-w-md leading-relaxed mb-10">
        {display} fait partie des tout premiers à avoir fait vivre la beta de
        GlobeGenius — usage, feedbacks, et partages qui ont façonné le produit
        dès ses débuts. 🙏
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
