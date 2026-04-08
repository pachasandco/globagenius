"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getPackages, getPipelineStatus, type Package, type PipelineStatus } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Article {
  slug: string;
  destination: string;
  country: string;
  title: string;
  subtitle: string;
  cover_photo: string;
  tags: string[];
}

function DealCard({ pkg }: { pkg: Package }) {
  const nights = Math.round(
    (new Date(pkg.return_date).getTime() - new Date(pkg.departure_date).getTime()) / 86400000
  );
  const dep = new Date(pkg.departure_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const ret = new Date(pkg.return_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  const isPremium = pkg.discount_pct >= 40;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className={`px-4 py-3 flex items-center justify-between ${isPremium ? "bg-gray-900" : "bg-gray-700"}`}>
        <div>
          <div className="text-white text-sm font-semibold">{pkg.origin} → {pkg.destination}</div>
          <div className="text-gray-400 text-xs">{dep} – {ret} · {nights} nuits</div>
        </div>
        <div className="flex items-center gap-2">
          {isPremium && <span className="bg-amber-400 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded-full">PREMIUM</span>}
          <div className={`text-white text-xs font-bold px-2.5 py-1 rounded-full ${isPremium ? "bg-red-500" : "bg-orange-500"}`}>
            -{Math.round(pkg.discount_pct)}%
          </div>
        </div>
      </div>
      <div className="p-4">
        {pkg.ai_description && <p className="text-sm text-gray-500 italic mb-3 leading-relaxed">{pkg.ai_description}</p>}
        <div className="flex items-end justify-between mb-2">
          <div>
            <div className="text-xs text-gray-400 mb-0.5">Vol + Hôtel</div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold">{Math.round(pkg.total_price)} €</span>
              <span className="text-sm text-gray-300 line-through">{Math.round(pkg.baseline_total)} €</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 bg-cyan-50 rounded-lg px-2.5 py-1">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
            <span className="text-xs font-semibold text-cyan-700">Score {pkg.score}</span>
          </div>
        </div>
        {pkg.ai_tip && (
          <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 text-xs text-amber-800">💡 {pkg.ai_tip}</div>
        )}
        {pkg.ai_tags && pkg.ai_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {pkg.ai_tags.map((tag: string) => (
              <span key={tag} className="text-[11px] text-cyan-600 bg-cyan-50 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [premiumDeals, setPremiumDeals] = useState<Package[]>([]);
  const [freeDeals, setFreeDeals] = useState<Package[]>([]);
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"premium" | "free">("premium");
  const router = useRouter();

  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const userEmail = localStorage.getItem("gg_email");
    if (!userId) {
      router.push("/login");
      return;
    }
    setEmail(userEmail || "");

    async function load() {
      try {
        const [premRes, freeRes, statusRes] = await Promise.allSettled([
          getPackages(0, 50, "premium"),
          getPackages(0, 50, "free"),
          getPipelineStatus(),
        ]);
        if (premRes.status === "fulfilled") {
          const d = premRes.value as { packages?: Package[]; items?: Package[] };
          setPremiumDeals(d?.packages || d?.items || []);
        }
        if (freeRes.status === "fulfilled") {
          const d = freeRes.value as { packages?: Package[]; items?: Package[] };
          setFreeDeals(d?.packages || d?.items || []);
        }
        if (statusRes.status === "fulfilled") {
          setStatus(statusRes.value as PipelineStatus);
        }
      } catch { /* ignore */ }

      // Load articles
      try {
        const res = await fetch(`${API_URL}/api/articles`);
        const data = await res.json();
        setArticles(data.articles || []);
      } catch { /* ignore */ }

      setLoading(false);
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("gg_user_id");
    localStorage.removeItem("gg_email");
    localStorage.removeItem("gg_token");
    router.push("/");
  }

  const deals = activeTab === "premium" ? premiumDeals : freeDeals;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-amber-400 flex items-center justify-center text-white font-bold text-sm">G</div>
            <span className="font-[family-name:var(--font-dm-serif)] text-[19px]">Globe Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="text-gray-900 font-medium">Deals</Link>
            <Link href="/articles" className="hover:text-gray-900 transition-colors">Articles</Link>
            <Link href="/planner" className="hover:text-gray-900 transition-colors">Planificateur</Link>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 hidden sm:block">{email}</span>
            <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-red-500 transition-colors">
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-5 py-8">
        {/* Status bar */}
        {status && (
          <div className="flex flex-wrap gap-6 mb-6 p-5 bg-white rounded-2xl border border-gray-100">
            <div>
              <div className="text-2xl font-bold">{premiumDeals.length + freeDeals.length}</div>
              <div className="text-xs text-gray-400">Deals actifs</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{status.active_baselines}</div>
              <div className="text-xs text-gray-400">Routes surveillées</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{(status.recent_scrapes || []).length}</div>
              <div className="text-xs text-gray-400">Scrapes récents</div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-gray-400">Pipeline actif · 6x/jour</span>
            </div>
          </div>
        )}

        {/* Deals section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Vos deals</h2>
            <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1">
              <button
                onClick={() => setActiveTab("premium")}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === "premium" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
              >
                ⭐ Premium -{">"}40%
                {premiumDeals.length > 0 && <span className="ml-1.5 bg-amber-100 text-amber-700 text-xs px-1.5 py-0.5 rounded-full">{premiumDeals.length}</span>}
              </button>
              <button
                onClick={() => setActiveTab("free")}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${activeTab === "free" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}
              >
                🆓 Gratuit -20 à -39%
                {freeDeals.length > 0 && <span className="ml-1.5 bg-gray-200 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">{freeDeals.length}</span>}
              </button>
            </div>
          </div>

          {loading && <div className="text-center py-12 text-gray-400">Chargement...</div>}

          {!loading && deals.length === 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
              <div className="text-4xl mb-3">🔍</div>
              <h3 className="font-semibold text-lg mb-2">Analyse en cours</h3>
              <p className="text-sm text-gray-400 max-w-md mx-auto mb-4">
                Notre pipeline scrape les prix 6 fois par jour depuis 8 aéroports français.
                Les deals apparaîtront dès qu'une anomalie de prix sera détectée.
              </p>
              <p className="text-xs text-gray-300">
                Vous serez alerté sur Telegram dès qu'un deal correspond à vos préférences.
              </p>
            </div>
          )}

          {!loading && deals.length > 0 && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {deals.map((pkg) => (
                <DealCard key={pkg.id} pkg={pkg} />
              ))}
            </div>
          )}
        </div>

        {/* Articles section */}
        {articles.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-[family-name:var(--font-dm-serif)] text-2xl">Guides de voyage</h2>
              <Link href="/articles" className="text-sm font-semibold text-cyan-600 hover:underline">
                Tout voir →
              </Link>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {articles.slice(0, 4).map((article) => (
                <Link key={article.slug} href={`/articles/${article.slug}`} className="group">
                  <div className="relative aspect-[4/3] rounded-xl overflow-hidden mb-2">
                    <img src={article.cover_photo} alt={article.destination} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <div className="absolute bottom-2 left-2">
                      <div className="text-white font-semibold text-sm drop-shadow">{article.destination}</div>
                      <div className="text-white/70 text-[11px]">{article.country}</div>
                    </div>
                  </div>
                  <h3 className="text-sm font-medium group-hover:text-cyan-600 transition-colors line-clamp-1">{article.title}</h3>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Quick links */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link href="/planner" className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow group">
            <div className="text-2xl mb-2">🗺️</div>
            <h3 className="font-semibold mb-1 group-hover:text-cyan-600 transition-colors">Planificateur de voyage</h3>
            <p className="text-sm text-gray-400">Notre IA vous prépare un programme jour par jour personnalisé.</p>
          </Link>
          <Link href="/articles" className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow group">
            <div className="text-2xl mb-2">✍️</div>
            <h3 className="font-semibold mb-1 group-hover:text-cyan-600 transition-colors">Guides de destinations</h3>
            <p className="text-sm text-gray-400">Des articles complets rédigés par IA pour préparer votre voyage.</p>
          </Link>
          <Link href="/onboarding" className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow group">
            <div className="text-2xl mb-2">⚙️</div>
            <h3 className="font-semibold mb-1 group-hover:text-cyan-600 transition-colors">Mes préférences</h3>
            <p className="text-sm text-gray-400">Modifiez vos aéroports, destinations et alertes Telegram.</p>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 — Packages voyage à prix cassés détectés par IA
        </div>
      </footer>
    </div>
  );
}
