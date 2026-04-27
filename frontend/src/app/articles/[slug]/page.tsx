import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Section {
  title: string;
  content: string;
  photo_url: string;
}

interface Article {
  slug: string;
  destination: string;
  country: string;
  title: string;
  subtitle: string;
  intro: string;
  cover_photo: string;
  tags: string[];
  best_time: string;
  sections: Section[];
  budget_tip: string;
  created_at?: string;
  updated_at?: string;
}

async function fetchArticle(slug: string): Promise<Article | null> {
  try {
    const res = await fetch(`${API_URL}/api/articles/${slug}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (typeof data.sections === "string") {
      data.sections = JSON.parse(data.sections);
    }
    return data;
  } catch {
    return null;
  }
}

async function fetchAllSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.articles || []).map((a: { slug: string }) => a.slug);
  } catch {
    return [];
  }
}

export async function generateStaticParams() {
  const slugs = await fetchAllSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticle(slug);

  if (!article) {
    return { title: "Article non trouvé — Globe Genius" };
  }

  const title = `${article.title} — Guide ${article.destination} | Globe Genius`;
  const description =
    article.subtitle ||
    article.intro?.slice(0, 155) ||
    `Guide de voyage ${article.destination} par Globe Genius`;

  return {
    title,
    description,
    alternates: {
      canonical: `https://globegenius.app/articles/${slug}`,
    },
    openGraph: {
      title,
      description,
      url: `https://globegenius.app/articles/${slug}`,
      siteName: "Globe Genius",
      images: article.cover_photo
        ? [{ url: article.cover_photo, width: 1200, height: 630, alt: article.title }]
        : [],
      locale: "fr_FR",
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: article.cover_photo ? [article.cover_photo] : [],
    },
  };
}

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = await fetchArticle(slug);

  if (!article) {
    notFound();
  }

  // JSON-LD schemas — data comes from our own API (not user input), XSS-safe
  const articleSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.subtitle,
    image: article.cover_photo,
    url: `https://globegenius.app/articles/${slug}`,
    datePublished: article.created_at ? article.created_at.slice(0, 10) : "2026-04-10",
    dateModified: article.updated_at ? article.updated_at.slice(0, 10) : undefined,
    author: {
      "@type": "Organization",
      name: "Globe Genius",
      url: "https://globegenius.app",
    },
    publisher: {
      "@type": "Organization",
      name: "Globe Genius",
      logo: {
        "@type": "ImageObject",
        url: "https://globegenius.app/globe1.png",
      },
    },
    inLanguage: "fr-FR",
    about: { "@type": "Place", name: article.destination },
  });

  const breadcrumbSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Accueil",
        item: "https://globegenius.app",
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "Articles",
        item: "https://globegenius.app/articles",
      },
      {
        "@type": "ListItem",
        position: 3,
        name: article.title,
        item: `https://globegenius.app/articles/${slug}`,
      },
    ],
  });

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      {/* JSON-LD — sourced from our own API, not user input */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: articleSchema }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: breadcrumbSchema }} />

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <Link
              href="/home#guides"
              className="text-sm text-gray-500 hover:text-gray-900"
            >
              ← Articles
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

      {/* Hero */}
      <div className="relative h-[30vh] md:h-[50vh]">
        <Image
          src={article.cover_photo}
          alt={`${article.destination} — guide voyage Globe Genius`}
          fill
          priority
          className="object-cover"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="absolute bottom-8 left-0 right-0">
          <div className="max-w-4xl mx-auto px-5">
            <div className="text-white/70 text-sm mb-2">{article.country}</div>
            <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl md:text-5xl text-white mb-1.5 md:mb-2">
              {article.title}
            </h1>
            <p className="text-white/80 text-sm md:text-lg line-clamp-2 md:line-clamp-none">
              {article.subtitle}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 md:px-5 py-8 md:py-10">
        <p className="text-base md:text-lg text-gray-600 leading-relaxed mb-8 md:mb-10">
          {article.intro}
        </p>

        {article.tags && article.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-10">
            {article.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs text-cyan-600 bg-cyan-50 px-3 py-1 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {article.sections &&
          article.sections.map((section, i) => (
            <div key={i} className="mb-12">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-4">
                {section.title}
              </h2>
              {section.photo_url && (
                <div className="rounded-2xl overflow-hidden mb-4 aspect-[16/9] relative">
                  <Image
                    src={section.photo_url}
                    alt={section.title}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 100vw, 896px"
                  />
                </div>
              )}
              <div className="text-gray-600 leading-relaxed whitespace-pre-line">
                {section.content}
              </div>
            </div>
          ))}

        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          {article.best_time && (
            <div className="bg-cyan-50 border border-cyan-100 rounded-2xl p-5">
              <div className="font-semibold text-sm text-cyan-900 mb-1">
                📅 Meilleure période
              </div>
              <p className="text-sm text-cyan-800">{article.best_time}</p>
            </div>
          )}
          {article.budget_tip && (
            <div className="bg-amber-50 border border-amber-100 rounded-2xl p-5">
              <div className="font-semibold text-sm text-amber-900 mb-1">
                💰 Conseil budget
              </div>
              <p className="text-sm text-amber-800">{article.budget_tip}</p>
            </div>
          )}
        </div>

        <div className="bg-[#FFFEF9] border border-[#F0E6D8] rounded-2xl p-8 text-center">
          <h3 className="font-[family-name:var(--font-dm-serif)] text-xl mb-2">
            Envie de partir à {article.destination} ?
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Nos alertes vous préviennent dès qu&apos;un deal est détecté pour
            cette destination.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold px-6 py-3 rounded-full transition-all text-sm"
          >
            Recevoir les deals →
          </Link>
        </div>
      </div>

      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-4xl mx-auto px-4 md:px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026
        </div>
      </footer>
    </div>
  );
}
