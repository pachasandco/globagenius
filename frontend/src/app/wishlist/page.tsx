"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearSessionCookie } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface WishlistItem {
  id: string;
  origin: string;
  destination: string;
  created_at: string;
}

const AIRPORTS: Record<string, string> = {
  CDG: "Paris CDG", ORY: "Paris Orly", BVA: "Paris Beauvais",
  LYS: "Lyon", MRS: "Marseille", NCE: "Nice",
  BOD: "Bordeaux", NTE: "Nantes", TLS: "Toulouse",
};

const DESTINATIONS = [
  "AMS","ATH","BCN","BER","BKK","BRU","BUD","CMN","DBV","DXB",
  "FCO","GRU","HAV","HKG","IST","JFK","KUL","LAX","LIS","LHR",
  "MAD","MIA","MXP","NRT","OPO","PMI","PRG","RAK","RNS","SSA",
  "TFS","TUN","VIE","WAW","ZRH",
];

export default function WishlistPage() {
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [origin, setOrigin] = useState("ORY");
  const [destination, setDestination] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const userId = typeof window !== "undefined" ? localStorage.getItem("gg_user_id") : null;
  const token = typeof window !== "undefined" ? localStorage.getItem("gg_token") : null;

  useEffect(() => {
    if (!userId) { router.push("/login"); return; }
    fetchWishlists();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchWishlists() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/users/${userId}/wishlists`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setItems(data.wishlists || []);
    } catch {
      setError("Impossible de charger la wishlist.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!destination) return;
    setAdding(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/users/${userId}/wishlists`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ origin, destination }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Erreur lors de l'ajout.");
      } else {
        setDestination("");
        fetchWishlists();
      }
    } catch {
      setError("Erreur de connexion.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await fetch(`${API_URL}/api/users/${userId}/wishlists/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {
      setError("Erreur lors de la suppression.");
    }
  }

  function handleLogout() {
    localStorage.removeItem("gg_user_id");
    localStorage.removeItem("gg_email");
    localStorage.removeItem("gg_token");
    clearSessionCookie();
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-[#FFF8F0]">
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 md:px-5 h-[64px] flex items-center justify-between">
          <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-[19px] leading-none">
            Globe<span className="text-[#FF6B47]">Genius</span>
          </Link>
          <div className="hidden md:flex items-center gap-5 text-sm text-gray-500">
            <Link href="/home" className="hover:text-gray-900 transition-colors">Deals</Link>
            <Link href="/articles" className="hover:text-gray-900 transition-colors">Destinations</Link>
            <Link href="/wishlist" className="text-gray-900 font-medium">Ma wishlist</Link>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <Link href="/profile" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">Profil</Link>
            <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-red-500 transition-colors">
              Déconnexion
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 md:px-5 py-10">
        <div className="mb-8">
          <h1 className="font-[family-name:var(--font-dm-serif)] text-3xl text-[#0A1F3D] mb-1">
            Ma wishlist
          </h1>
          <p className="text-[#0A1F3D]/60 text-sm">
            Vous recevrez une alerte Telegram dès qu&apos;un deal correspond à une de vos routes.
          </p>
        </div>

        {/* Add form */}
        <div className="bg-white rounded-2xl border border-[#F0E6D8] p-5 mb-6">
          <h2 className="font-semibold text-[#0A1F3D] mb-4">Ajouter une route</h2>
          <div className="flex flex-col sm:flex-row gap-3 mb-3">
            <div className="flex-1">
              <label className="text-xs text-[#0A1F3D]/50 mb-1 block">Depuis</label>
              <select
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full text-sm bg-[#FFF8F0] border border-[#F0E6D8] rounded-xl px-3 py-2.5 outline-none focus:border-[#FF6B47]"
              >
                {Object.entries(AIRPORTS).map(([code, label]) => (
                  <option key={code} value={code}>{label} ({code})</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-[#0A1F3D]/50 mb-1 block">Vers</label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full text-sm bg-[#FFF8F0] border border-[#F0E6D8] rounded-xl px-3 py-2.5 outline-none focus:border-[#FF6B47]"
              >
                <option value="">Choisir une destination</option>
                {DESTINATIONS.map((code) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>
          </div>
          {error && <p className="text-xs text-red-500 mb-3">{error}</p>}
          <button
            onClick={handleAdd}
            disabled={adding || !destination}
            className="w-full bg-[#FF6B47] hover:bg-[#E55A38] disabled:opacity-40 text-white font-semibold text-sm py-3 rounded-full transition-all"
          >
            {adding ? "Ajout…" : "Surveiller cette route"}
          </button>
          {items.length >= 10 && (
            <p className="text-xs text-[#0A1F3D]/40 text-center mt-2">Maximum 10 routes atteint.</p>
          )}
        </div>

        {/* List */}
        {loading ? (
          <div className="text-center py-8 text-gray-400 text-sm">Chargement…</div>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-10 text-center">
            <div className="text-4xl mb-3">🗺️</div>
            <p className="text-sm text-gray-400">Aucune route surveillée pour l&apos;instant.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-2xl border border-[#F0E6D8] px-5 py-4 flex items-center justify-between"
              >
                <div>
                  <div className="font-[family-name:var(--font-dm-serif)] text-lg text-[#0A1F3D]">
                    {AIRPORTS[item.origin] || item.origin} → {item.destination}
                  </div>
                  <div className="text-xs text-[#0A1F3D]/40 mt-0.5">
                    {item.origin} → {item.destination}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-sm text-gray-300 hover:text-red-400 transition-colors px-2 py-1 rounded-lg hover:bg-red-50"
                  title="Supprimer"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="border-t border-gray-100 py-6 mt-8">
        <div className="max-w-6xl mx-auto px-5 text-center text-xs text-gray-300">
          Globe Genius © 2026 — Vols à prix cassés
        </div>
      </footer>
    </div>
  );
}
