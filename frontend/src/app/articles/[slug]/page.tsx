import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SimpleHeader, SiteFooter } from "../../_components/SiteChrome";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Section { title: string; content: string; photo_url: string; }
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
    const res = await fetch(`${API_URL}/api/articles/${slug}`, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    const data = await res.json();
    if (typeof data.sections === "string") data.sections = JSON.parse(data.sections);
    return data;
  } catch { return null; }
}

async function fetchAllSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.articles || []).map((a: { slug: string }) => a.slug);
  } catch { return []; }
}

export async function generateStaticParams() {
  const slugs = await fetchAllSlugs();
  return slugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) return { title: "Article non trouvé — GlobeGenius" };
  const title = `${article.title} — Guide ${article.destination} | GlobeGenius`;
  const description = article.subtitle || article.intro?.slice(0, 155) || `Guide de voyage ${article.destination} par GlobeGenius`;
  return {
    title,
    description,
    alternates: { canonical: `https://globegenius.app/articles/${slug}` },
    openGraph: {
      title,
      description,
      url: `https://globegenius.app/articles/${slug}`,
      siteName: "GlobeGenius",
      images: article.cover_photo ? [{ url: article.cover_photo, width: 1200, height: 630, alt: article.title }] : [],
      locale: "fr_FR",
      type: "article",
    },
    twitter: { card: "summary_large_image", title, description, images: article.cover_photo ? [article.cover_photo] : [] },
  };
}

export default async function ArticlePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const article = await fetchArticle(slug);
  if (!article) notFound();

  const articleSchema = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Article",
    headline: article.title,
    description: article.subtitle,
    image: article.cover_photo,
    url: `https://globegenius.app/articles/${slug}`,
    datePublished: article.created_at ? article.created_at.slice(0, 10) : undefined,
    dateModified: article.updated_at ? article.updated_at.slice(0, 10) : undefined,
    author: { "@type": "Organization", name: "GlobeGenius", url: "https://globegenius.app" },
    publisher: { "@type": "Organization", name: "GlobeGenius", logo: { "@type": "ImageObject", url: "https://globegenius.app/icon.png" } },
    inLanguage: "fr-FR",
    about: { "@type": "Place", name: article.destination },
  });

  return (
    <div className="min-h-screen bg-[#F7F3EA] text-[#0B2A3F]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: articleSchema }} />
      <SimpleHeader backHref="/articles" backLabel="Tous les guides" />

      <main>
        <section className="relative min-h-[390px] overflow-hidden sm:min-h-[520px]">
          <Image src={article.cover_photo} alt={`${article.destination} — guide voyage GlobeGenius`} fill priority className="object-cover" sizes="100vw" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#061824] via-[#0B2A3F]/55 to-[#0B2A3F]/10" />
          <div className="absolute inset-x-0 bottom-0 px-5 pb-10 sm:px-8 sm:pb-14">
            <div className="mx-auto max-w-4xl text-white">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7DE0D6]">{article.country}</p>
              <h1 className="mt-3 max-w-3xl font-[family-name:var(--font-dm-serif)] text-4xl leading-tight sm:text-6xl">{article.title}</h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-white/75 sm:text-lg">{article.subtitle}</p>
            </div>
          </div>
        </section>

        <article className="mx-auto max-w-4xl px-5 py-12 sm:px-8 sm:py-16">
          <div className="site-editorial-card rounded-[32px] border border-[#D9E2E3] bg-white p-6 sm:p-10">
            <p className="text-lg leading-8 text-slate-600">{article.intro}</p>

            {article.tags?.length > 0 && (
              <div className="mt-7 flex flex-wrap gap-2">
                {article.tags.map((tag) => <span key={tag} className="rounded-full bg-[#E9F5F7] px-3 py-1 text-xs font-semibold text-[#0E7490]">{tag}</span>)}
              </div>
            )}

            {article.sections?.map((section, i) => (
              <section key={i} className="mt-10">
                <h2>{section.title}</h2>
                {section.photo_url && (
                  <div className="relative mt-5 aspect-[16/9] overflow-hidden rounded-2xl">
                    <Image src={section.photo_url} alt={section.title} fill className="object-cover" sizes="(max-width: 768px) 100vw, 896px" />
                  </div>
                )}
                <div className="mt-5 whitespace-pre-line text-slate-600 leading-8">{section.content}</div>
              </section>
            ))}

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              {article.best_time && <div className="rounded-2xl border border-[#8FC9D2] bg-[#E9F5F7] p-5"><div className="text-sm font-bold text-[#0B2A3F]">Meilleure période</div><p className="mt-2 text-sm leading-6 text-slate-600">{article.best_time}</p></div>}
              {article.budget_tip && <div className="rounded-2xl border border-[#FF7A59]/25 bg-[#FFF0EA] p-5"><div className="text-sm font-bold text-[#0B2A3F]">Conseil budget</div><p className="mt-2 text-sm leading-6 text-slate-600">{article.budget_tip}</p></div>}
            </div>

            <div className="site-hero-soft mt-10 rounded-[28px] p-7 text-center text-white sm:p-9">
              <h3 className="font-[family-name:var(--font-dm-serif)] text-3xl">Envie de partir à {article.destination} ?</h3>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-white/70">Activez votre aéroport et laissez GlobeGenius surveiller les baisses de prix réellement intéressantes.</p>
              <Link href="/signup" className="mt-6 inline-flex rounded-xl bg-white px-6 py-3.5 text-sm font-bold text-[#0B2A3F] hover:bg-[#E9F5F7]">Activer mon radar</Link>
            </div>
          </div>
        </article>
      </main>
      <SiteFooter />
    </div>
  );
}
