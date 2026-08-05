import type { Metadata } from "next";
import Link from "next/link";
import { PublicHeader, SiteFooter } from "../_components/SiteChrome";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITE_URL = "https://globegenius.app";

interface ArticleSummary {
  slug: string;
  title: string;
  subtitle?: string;
  destination?: string;
  country?: string;
  cover_photo?: string;
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

export const metadata: Metadata = {
  title: "Guides de voyage — GlobeGenius",
  description: "Guides voyage en français : quartiers, budget, conseils pratiques et préparation du séjour.",
  alternates: { canonical: `${SITE_URL}/articles` },
  openGraph: {
    title: "Guides de voyage — GlobeGenius",
    description: "Préparez votre prochain départ avec les guides GlobeGenius.",
    url: `${SITE_URL}/articles`,
    siteName: "GlobeGenius",
    locale: "fr_FR",
    type: "website",
  },
};

export default async function ArticlesIndexPage() {
  const articles = await fetchArticles();
  const collectionSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Guides de voyage — GlobeGenius",
    url: `${SITE_URL}/articles`,
    inLanguage: "fr-FR",
    hasPart: articles.map((a) => ({ "@type": "Article", headline: a.title, url: `${SITE_URL}/articles/${a.slug}`, ...(a.cover_photo ? { image: a.cover_photo } : {}) })),
  });

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: collectionSchema }} />
      <PublicHeader />

      <main>
        <section className="site-hero-soft px-5 py-16 text-white sm:px-8 sm:py-24">
          <div className="mx-auto max-w-5xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#7DE0D6]">Inspiration et préparation</p>
            <h1 className="mt-4 font-[family-name:var(--font-dm-serif)] text-5xl leading-tight sm:text-6xl">Guides destination</h1>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-white/70 sm:text-lg">Comprendre une destination, préparer son budget et éviter les erreurs courantes avant de réserver.</p>
          </div>
        </section>

        <section aria-label="Liste des guides" className="mx-auto max-w-6xl px-5 py-14 sm:px-8 sm:py-20">
          {articles.length === 0 ? (
            <div className="site-card rounded-[30px] border border-[#D9E2E3] p-12 text-center">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl">Les guides arrivent</h2>
              <p className="mx-auto mt-3 max-w-md text-sm leading-7 text-slate-500">La collection est enrichie progressivement pour les destinations surveillées.</p>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {articles.map((article) => (
                <Link key={article.slug} href={`/articles/${article.slug}`} className="group overflow-hidden rounded-[28px] border border-[#D9E2E3] bg-white shadow-[0_14px_38px_rgba(11,42,63,.05)] transition-all hover:-translate-y-1 hover:border-[#8FC9D2] hover:shadow-[0_22px_48px_rgba(11,42,63,.09)]">
                  <div className="relative aspect-[16/10] overflow-hidden bg-[#E9F5F7]">
                    {article.cover_photo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={article.cover_photo} alt={`${article.destination || article.title} — guide voyage`} className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" loading="lazy" />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[#E9F5F7] to-[#FFF0EA]"><span className="font-[family-name:var(--font-dm-serif)] text-5xl text-[#0E7490]/35">{article.title.charAt(0)}</span></div>
                    )}
                  </div>
                  <div className="p-6">
                    <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#FF7A59]">{article.country || article.destination || "Guide"}</p>
                    <h2 className="mt-2 font-[family-name:var(--font-dm-serif)] text-2xl leading-tight text-[#0B2A3F]">{article.title}</h2>
                    {article.subtitle && <p className="mt-3 line-clamp-3 text-sm leading-7 text-slate-500">{article.subtitle}</p>}
                    <span className="mt-5 inline-flex text-sm font-bold text-[#0E7490]">Lire le guide →</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white px-5 py-16 sm:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#FF7A59]">Le guide ne trouve pas le billet</p>
            <h2 className="mt-3 font-[family-name:var(--font-dm-serif)] text-4xl">Laissez GlobeGenius surveiller le prix.</h2>
            <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-500">Choisissez votre aéroport et recevez sur Telegram les baisses de prix réellement intéressantes lorsqu’elles apparaissent.</p>
            <Link href="/signup" className="site-cta-primary mt-7 inline-flex rounded-xl px-6 py-3.5 text-sm font-bold">Activer mon radar gratuitement</Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
