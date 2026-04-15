"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  sections: Array<{ title: string; content: string; photo_url: string }>;
  budget_tip: string;
}

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/articles`)
      .then(r => r.json())
      .then(data => setArticles(data.articles || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <img src="/globe1.png" alt="Globe Genius" className="w-8 h-8 shrink-0 object-contain" />
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">Globe Genius</span>
          </Link>
          <div className="flex items-center gap-2 md:gap-3">
            <Link href="/home" className="text-sm text-gray-500 hover:text-gray-900 hidden sm:block">Dashboard</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 md:px-5 py-10 md:py-16">
        <div className="text-center mb-12">
          <div className="text-xs font-bold text-cyan-600 tracking-widest uppercase mb-2">Guides de voyage</div>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-[26px] md:text-[42px] mb-3">
            Nos destinations
          </h1>
          <p className="text-gray-400 max-w-lg mx-auto">
            Des guides complets pour vous inspirer et préparer votre prochain voyage.
          </p>
        </div>

        {loading && <div className="text-center py-20 text-gray-400">Chargement...</div>}

        {!loading && articles.length === 0 && (
          <div className="text-center py-20">
            <div className="text-4xl mb-4">✍️</div>
            <h3 className="text-lg font-semibold mb-2">Articles en cours de rédaction</h3>
            <p className="text-gray-400 text-sm max-w-sm mx-auto">
              Nos guides de destinations sont en cours de rédaction. Revenez bientôt !
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
          {articles.map((article) => (
            <Link
              key={article.slug}
              href={`/articles/${article.slug}`}
              className="group"
            >
              <div className="relative aspect-[4/3] rounded-2xl overflow-hidden mb-3">
                <img
                  src={article.cover_photo}
                  alt={article.destination}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="absolute bottom-3 left-3 right-3">
                  <div className="text-white font-semibold text-lg drop-shadow-lg">{article.destination}</div>
                  <div className="text-white/70 text-xs">{article.country}</div>
                </div>
              </div>
              <h3 className="font-semibold text-[15px] mb-1 group-hover:text-cyan-600 transition-colors">{article.title}</h3>
              <p className="text-sm text-gray-400 line-clamp-2">{article.subtitle}</p>
              {article.tags && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {article.tags.slice(0, 3).map((tag: string) => (
                    <span key={tag} className="text-[10px] text-cyan-600 bg-cyan-50 px-2 py-0.5 rounded-full">{tag}</span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
