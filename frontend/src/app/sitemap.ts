import type { MetadataRoute } from "next";
import { slugFor } from "@/lib/destinations";

export const dynamic = "force-dynamic";

const BASE = "https://globegenius.app";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AIRPORT_SLUGS = [
  "paris",
  "lyon",
  "marseille",
  "toulouse",
  "bordeaux",
  "nantes",
  "nice",
  "bale-mulhouse",
];

async function fetchArticleSlugs(): Promise<string[]> {
  try {
    const response = await fetch(`${API_URL}/api/articles`, { cache: "no-store" });
    if (!response.ok) return [];
    const data = await response.json();
    return (data.articles || []).map((article: { slug: string }) => article.slug);
  } catch {
    return [];
  }
}

async function fetchDestinationIatas(): Promise<string[]> {
  try {
    const response = await fetch(`${API_URL}/api/destinations?limit=200`, { cache: "no-store" });
    if (!response.ok) return [];
    const data = await response.json();
    return (data.items || []).map((destination: { iata: string }) => destination.iata);
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [articleSlugs, destinationIatas] = await Promise.all([
    fetchArticleSlugs(),
    fetchDestinationIatas(),
  ]);

  const articleUrls: MetadataRoute.Sitemap = articleSlugs.map((slug) => ({
    url: `${BASE}/articles/${slug}`,
    lastModified: new Date(),
    priority: 0.7,
    changeFrequency: "monthly",
  }));

  const destinationUrls: MetadataRoute.Sitemap = destinationIatas.map((iata) => ({
    url: `${BASE}/destination/${slugFor(iata)}`,
    lastModified: new Date(),
    priority: 0.7,
    changeFrequency: "weekly",
  }));

  const airportUrls: MetadataRoute.Sitemap = AIRPORT_SLUGS.map((slug) => ({
    url: `${BASE}/depart/${slug}`,
    lastModified: new Date(),
    priority: 0.85,
    changeFrequency: "weekly",
  }));

  return [
    {
      url: BASE,
      lastModified: new Date(),
      priority: 1,
      changeFrequency: "daily",
    },
    {
      url: `${BASE}/methodologie`,
      lastModified: new Date(),
      priority: 0.8,
      changeFrequency: "monthly",
    },
    {
      url: `${BASE}/articles`,
      lastModified: new Date(),
      priority: 0.8,
      changeFrequency: "weekly",
    },
    ...airportUrls,
    ...articleUrls,
    ...destinationUrls,
  ];
}
