import type { MetadataRoute } from "next";

// Force dynamic generation: the sitemap depends on the live `articles`
// table, and the previous ISR (revalidate: 3600) caused new destinations
// to take up to an hour to appear after generation.
export const dynamic = "force-dynamic";

const BASE = "https://globegenius.app";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchArticleSlugs(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/articles`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.articles || []).map((a: { slug: string }) => a.slug);
  } catch {
    return [];
  }
}

async function fetchDestinationIatas(): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/api/destinations?limit=200`, { next: { revalidate: 3600 } });
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
    url: `${BASE}/destination/${iata.toLowerCase()}`,
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
    ...articleUrls,
    ...destinationUrls,
    {
      url: `${BASE}/conditions`,
      lastModified: new Date(),
      priority: 0.3,
      changeFrequency: "yearly",
    },
    {
      url: `${BASE}/confidentialite`,
      lastModified: new Date(),
      priority: 0.3,
      changeFrequency: "yearly",
    },
    {
      url: `${BASE}/mentions-legales`,
      lastModified: new Date(),
      priority: 0.3,
      changeFrequency: "yearly",
    },
  ];
}
