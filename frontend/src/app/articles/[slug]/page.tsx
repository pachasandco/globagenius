"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Section {
  title: string;
  content: string;
  photo_url?: string;
  photo_query?: string;
}

interface Article {
  slug: string;
  destination: string;
  country: string;
  title: string;
  subtitle: string;
  intro: string;
  sections: Section[];
  best_time: string;
  budget_tip: string;
  tags: string[];
  cover_photo: string;
}

export default function ArticlePage() {
  const params = useParams();
  const slug = params?.slug as string;
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) return;
    fetch(`${API_URL}/api/articles/${slug}`)
      .then(r => {
        if (!r.ok) throw new Error("Article non trouve");
        return r.json();
      })
      .then(data => {
        // sections might be a JSON string
        if (typeof data.sections === "string") {
          data.sections = JSON.parse(data.sections);
        }
        setArticle(data);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement...</div>;
  if (error || !article) return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <div className="text-4xl mb-4">😔</div>
      <h1 className="text-xl font-semibold mb-2">Article non trouve</h1>
      <Link href="/articles" className="text-cyan-600 text-sm hover:underline">← Retour aux articles</Link>
    </div>
  );

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white font-bold text-sm">G</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/articles" className="text-sm text-gray-500 hover:text-gray-900">← Articles</Link>
            <Link href="/home" className="text-sm text-gray-500 hover:text-gray-900">Dashboard</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div className="relative h-[40vh] md:h-[50vh]">
        <img src={article.cover_photo} alt={article.destination} className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="absolute bottom-8 left-0 right-0">
          <div className="max-w-4xl mx-auto px-5">
            <div className="text-white/70 text-sm mb-2">{article.country}</div>
            <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl md:text-5xl text-white mb-2">{article.title}</h1>
            <p className="text-white/80 text-lg">{article.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-5 py-10">
        {/* Intro */}
        <p className="text-lg text-gray-600 leading-relaxed mb-10">{article.intro}</p>

        {/* Tags */}
        {article.tags && article.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-10">
            {article.tags.map(tag => (
              <span key={tag} className="text-xs text-cyan-600 bg-cyan-50 px-3 py-1 rounded-full">{tag}</span>
            ))}
          </div>
        )}

        {/* Sections */}
        {article.sections && article.sections.map((section, i) => (
          <div key={i} className="mb-12">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-4">{section.title}</h2>
            {section.photo_url && (
              <div className="rounded-2xl overflow-hidden mb-4 aspect-[16/9]">
                <img src={section.photo_url} alt={section.title} className="w-full h-full object-cover" />
              </div>
            )}
            <div className="text-gray-600 leading-relaxed whitespace-pre-line">{section.content}</div>
          </div>
        ))}

        {/* Tips */}
        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          {article.best_time && (
            <div className="bg-cyan-50 border border-cyan-100 rounded-2xl p-5">
              <div className="font-semibold text-sm text-cyan-900 mb-1">📅 Meilleure periode</div>
              <p className="text-sm text-cyan-800">{article.best_time}</p>
            </div>
          )}
          {article.budget_tip && (
            <div className="bg-amber-50 border border-amber-100 rounded-2xl p-5">
              <div className="font-semibold text-sm text-amber-900 mb-1">💰 Conseil budget</div>
              <p className="text-sm text-amber-800">{article.budget_tip}</p>
            </div>
          )}
        </div>

        {/* CTA */}
        <div className="bg-gray-50 rounded-2xl p-8 text-center">
          <h3 className="font-[family-name:var(--font-dm-serif)] text-xl mb-2">
            Envie de partir a {article.destination} ?
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Nos alertes vous previennent des qu'un deal est detecte pour cette destination.
          </p>
          <Link href="/signup" className="inline-flex items-center gap-2 bg-gray-900 text-white font-semibold px-6 py-3 rounded-full hover:bg-black text-sm">
            Recevoir les deals →
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-6">
        <div className="max-w-4xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026
        </div>
      </footer>
    </div>
  );
}
