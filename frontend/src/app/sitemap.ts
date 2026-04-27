import type { MetadataRoute } from "next";

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

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const slugs = await fetchArticleSlugs();

  const articleUrls: MetadataRoute.Sitemap = slugs.map((slug) => ({
    url: `${BASE}/articles/${slug}`,
    lastModified: new Date(),
    priority: 0.8,
    changeFrequency: "monthly",
  }));

  return [
    {
      url: BASE,
      lastModified: new Date(),
      priority: 1.0,
      changeFrequency: "daily",
    },
    ...articleUrls,
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
