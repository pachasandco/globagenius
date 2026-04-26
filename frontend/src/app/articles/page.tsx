import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Destinations — Globe Genius",
  description: "Guides de voyage pour toutes vos destinations préférées. Conseils pratiques, meilleures périodes, budgets estimés.",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ArticleSummary {
  slug: string;
  destination: string;
  country: string;
  title: string;
  subtitle: string;
  cover_photo: string;
  tags: string[];
  best_time: string;
}

async function fetchArticles(): Promise<ArticleSummary[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.articles || [];
  } catch {
    return [];
  }
}

export default async function ArticlesPage() {
  const articles = await fetchArticles();

  const countries = Array.from(new Set(articles.map((a) => a.country))).sort();

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="hover:text-gray-900 transition-colors">Deals</Link>
            <Link href="/articles" className="text-gray-900 font-medium">Destinations</Link>
          </div>
          <Link
            href="/home"
            className="text-sm bg-[#FF6B47] text-white font-semibold px-4 py-2 rounded-full hover:bg-[#E55A38] transition-colors"
          >
            Voir les deals →
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 md:px-5 py-10">
        <div className="mb-8">
          <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl text-[#0A1F3D] mb-2">
            Guides destination
          </h1>
          <p className="text-[#0A1F3D]/60 text-base">
            Conseils pratiques, meilleures périodes et budgets estimés pour planifier votre prochain voyage.
          </p>
        </div>

        {articles.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <div className="text-4xl mb-3">✍️</div>
            <p className="text-gray-400 text-sm">Les guides arrivent bientôt.</p>
          </div>
        ) : (
          <>
            {/* Country filter pills */}
            {countries.length > 1 && (
              <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
                {countries.map((country) => (
                  <a
                    key={country}
                    href={`#${country}`}
                    className="shrink-0 px-4 py-2 rounded-full text-sm font-medium border border-[#F0E6D8] bg-white text-[#0A1F3D]/70 hover:border-[#FF6B47] hover:text-[#FF6B47] transition-all"
                  >
                    {country}
                  </a>
                ))}
              </div>
            )}

            {/* Articles grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {articles.map((article) => (
                <Link
                  key={article.slug}
                  href={`/articles/${article.slug}`}
                  className="group bg-white rounded-2xl border border-[#F0E6D8] hover:border-[#FF6B47] hover:shadow-[0_12px_32px_rgba(255,107,71,0.10)] transition-all duration-300 overflow-hidden"
                >
                  {article.cover_photo && (
                    <div className="aspect-[16/9] overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={article.cover_photo}
                        alt={article.destination}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    </div>
                  )}
                  <div className="p-5">
                    <div className="text-xs text-[#FF6B47] font-semibold mb-1 uppercase tracking-wide">
                      {article.country}
                    </div>
                    <h2 className="font-[family-name:var(--font-dm-serif)] text-lg text-[#0A1F3D] mb-1 group-hover:text-[#FF6B47] transition-colors">
                      {article.destination}
                    </h2>
                    <p className="text-sm text-[#0A1F3D]/60 mb-3 line-clamp-2">
                      {article.subtitle}
                    </p>
                    {article.best_time && (
                      <div className="text-xs text-[#0A1F3D]/40">
                        🗓 Meilleure période : {article.best_time}
                      </div>
                    )}
                    {article.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {article.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="text-[11px] bg-[#FFF8F0] text-[#0A1F3D]/50 px-2 py-0.5 rounded-full border border-[#F0E6D8]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </>
        )}
      </div>

      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 — Vols à prix cassés
        </div>
      </footer>
    </div>
  );
}
