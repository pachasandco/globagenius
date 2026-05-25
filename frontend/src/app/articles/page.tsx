import type { Metadata } from "next";
import Link from "next/link";
import { Wordmark } from "../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITE_URL = "https://globegenius.app";

interface ArticleSummary {
  slug: string;
  title: string;
  subtitle?: string;
  destination?: string;
  country?: string;
  cover_photo?: string;
  intro?: string;
  created_at?: string;
}

async function fetchArticles(): Promise<ArticleSummary[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.articles || [];
  } catch {
    return [];
  }
}

export const metadata: Metadata = {
  title: "Guides de voyage — Globe Genius",
  description:
    "Nos guides voyage longs en français : Rome, Marrakech, Barcelone, Lisbonne, et plus. Quartiers, budget, bonnes adresses et conseils pratiques pour partir mieux et moins cher.",
  alternates: {
    canonical: `${SITE_URL}/articles`,
  },
  openGraph: {
    title: "Guides de voyage — Globe Genius",
    description:
      "Guides voyage longs en français, écrits sans copier-coller. Préparez votre prochain départ avec Globe Genius.",
    url: `${SITE_URL}/articles`,
    siteName: "Globe Genius",
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Guides de voyage — Globe Genius",
    description:
      "Guides voyage longs en français : Rome, Marrakech, Barcelone, Lisbonne, et plus.",
  },
};

export default async function ArticlesIndexPage() {
  const articles = await fetchArticles();

  // JSON-LD — CollectionPage + BreadcrumbList
  const collectionSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Guides de voyage — Globe Genius",
    description:
      "Collection de guides voyage longs en français : Rome, Marrakech, Barcelone, Lisbonne, et plus.",
    url: `${SITE_URL}/articles`,
    inLanguage: "fr-FR",
    isPartOf: {
      "@type": "WebSite",
      name: "Globe Genius",
      url: SITE_URL,
    },
    hasPart: articles.map((a) => ({
      "@type": "Article",
      headline: a.title,
      url: `${SITE_URL}/articles/${a.slug}`,
      inLanguage: "fr-FR",
      ...(a.cover_photo ? { image: a.cover_photo } : {}),
    })),
  });

  const breadcrumbSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Accueil",
        item: SITE_URL,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Guides de voyage",
        item: `${SITE_URL}/articles`,
      },
    ],
  });

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* JSON-LD — sourced from our own API, not user input */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: collectionSchema }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: breadcrumbSchema }}
      />

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 md:px-5 h-[80px] flex items-center justify-between">
          <Link
            href="/"
            className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none"
          >
            <Wordmark />
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <Link
              href="/"
              className="text-sm text-gray-500 hover:text-gray-900"
            >
              ← Accueil
            </Link>
            <Link
              href="/home"
              className="text-sm text-gray-500 hover:text-gray-900 hidden sm:block"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </nav>

      {/* Header */}
      <header className="max-w-5xl mx-auto px-5 pt-16 pb-10 text-center">
        <p className="inline-block rounded-full bg-[var(--color-coral-50)] px-3 py-1 text-xs font-medium text-[var(--color-coral)] mb-4">
          Guides de voyage
        </p>
        <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl md:text-5xl text-[var(--color-ink)] mb-4">
          Nos guides de voyage
        </h1>
        <p className="max-w-2xl mx-auto text-gray-500 md:text-lg leading-relaxed">
          Des guides longs, écrits sans fard et sans copier-coller. Pour
          comprendre une ville avant d&apos;y poser le pied — et y partir bien
          moins cher grâce à nos alertes.
        </p>
      </header>

      {/* Articles grid */}
      <section
        aria-label="Liste des guides"
        className="max-w-5xl mx-auto px-5 pb-16"
      >
        {articles.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">
              Les guides sont en cours de chargement. Reviens dans quelques
              instants.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 lg:gap-8">
            {articles.map((article) => (
              <Link
                key={article.slug}
                href={`/articles/${article.slug}`}
                className="group block overflow-hidden rounded-2xl border border-[var(--color-sand)] bg-white hover:border-[var(--color-coral)] transition-colors"
              >
                <div className="relative aspect-[16/10] overflow-hidden bg-[var(--color-cream)]">
                  {article.cover_photo ? (
                    // <img> deliberately — these cards are below the fold and we
                    // already use <img> on the homepage guides section for the
                    // same reason (see app/page.tsx).
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={article.cover_photo}
                      alt={`${article.destination || article.title} — guide voyage`}
                      className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform duration-500"
                      loading="lazy"
                    />
                  ) : (
                    <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-coral-50)] to-[var(--color-cream)] flex items-center justify-center">
                      <span className="font-[family-name:var(--font-dm-serif)] text-4xl text-[var(--color-coral)]/40">
                        {article.title.charAt(0)}
                      </span>
                    </div>
                  )}
                </div>
                <div className="p-6">
                  {article.country && (
                    <div className="text-xs text-gray-400 mb-1">
                      {article.country}
                    </div>
                  )}
                  <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl text-[var(--color-ink)] group-hover:text-[var(--color-coral)] transition-colors mb-2">
                    {article.title}
                  </h2>
                  {article.subtitle && (
                    <p className="text-sm text-gray-500 leading-relaxed line-clamp-3">
                      {article.subtitle}
                    </p>
                  )}
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-coral)]">
                    Lire le guide →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* CTA produit */}
      <section className="bg-white border-t border-[var(--color-sand)] py-16 px-6 sm:px-12">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-4xl text-[var(--color-ink)] mb-3">
            Pars vraiment, pour 3× moins cher
          </h2>
          <p className="text-gray-500 leading-relaxed mb-6 max-w-xl mx-auto">
            Globe Genius scanne en continu plus de 200 compagnies aériennes
            pour trouver les erreurs de prix et les promos cachées. Reçois une
            alerte gratuite dès qu&apos;un deal est détecté.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-full bg-[var(--color-coral)] px-6 py-3 text-base font-semibold text-white shadow-sm transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-coral)] focus-visible:ring-offset-2"
          >
            Activer mes alertes gratuites
          </Link>
        </div>
      </section>
    </div>
  );
}
