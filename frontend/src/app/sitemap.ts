import type { MetadataRoute } from "next";
import { slugFor } from "@/lib/destinations";

// Force dynamic generation: the sitemap depends on the live `articles`
// table, and the previous ISR (revalidate: 3600) caused new destinations
// to take up to an hour to appear after generation.
export const dynamic = "force-dynamic";

const BASE = "https://globegenius.app";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchArticleSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.articles || []).map((a: { slug: string }) => a.slug);
  } catch {
    return [];
  }
}

async function fetchDestinationIatas(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/destinations?limit=200`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []).map((d: { iata: string }) => d.iata);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [slugs, iatas] = await Promise.all([
    fetchArticleSlugs(),
    fetchDestinationIatas(),
  ]);

  const articleUrls: MetadataRoute.Sitemap = slugs.map((slug) => ({
    url: `${BASE}/articles/${slug}`,
    lastModified: new Date(),
    priority: 0.8,
    changeFrequency: "monthly",
  }));

  const destinationUrls: MetadataRoute.Sitemap = iatas.map((iata) => ({
    // SEO-friendly slug (e.g. /destination/dublin) — old IATA URLs
    // (/destination/dub) are 301-redirected via next.config.ts.
    url: `${BASE}/destination/${slugFor(iata)}`,
    lastModified: new Date(),
    priority: 0.7,
    changeFrequency: "weekly",
  }));

  return [
    {
      url: BASE,
      lastModified: new Date(),
      priority: 1.0,
      changeFrequency: "daily",
    },
    // Page index des articles (résout le 404 historique sur /articles)
    {
      url: `${BASE}/articles`,
      lastModified: new Date(),
      priority: 0.9,
      changeFrequency: "weekly",
    },
    // Planificateur IA — page produit importante, manquait dans l'ancien sitemap
    {
      url: `${BASE}/planificateur`,
      lastModified: new Date(),
      priority: 0.9,
      changeFrequency: "weekly",
    },
    ...articleUrls,
    ...destinationUrls,
    // ⚠️ Pages légales (/conditions, /confidentialite, /mentions-legales)
    // volontairement EXCLUES du sitemap car elles sont en noindex côté HTML.
    // Les laisser dans le sitemap créait un signal contradictoire pour Google
    // (sitemap = "indexe-moi", noindex HTML = "n'indexe pas"). Standard de
    // l'industrie pour les pages légales : ni dans le sitemap, ni indexées.
  ];
}
