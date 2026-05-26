"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  listFeedback,
  hasAdminKey,
  setAdminKey,
  type FeedbackResponse,
  type FeedbackItem,
} from "@/lib/admin";

const FEEDBACK_META: Record<string, { emoji: string; label: string; cls: string }> = {
  good:     { emoji: "👍", label: "Bon",       cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  bad:      { emoji: "👎", label: "Faux",      cls: "bg-rose-50 text-rose-700 border-rose-200" },
  too_late: { emoji: "⏱️", label: "Trop tard", cls: "bg-amber-50 text-amber-700 border-amber-200" },
};

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("fr-FR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function AdminFeedbackPage() {
  const [authed, setAuthed] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [data, setData] = useState<FeedbackResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [filterType, setFilterType] = useState<string>("");
  const [filterUser, setFilterUser] = useState("");

  useEffect(() => {
    if (hasAdminKey()) setAuthed(true);
  }, []);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const res = await listFeedback(days, 200);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authed) reload();
  }, [authed, days]);

  function handleLogin() {
    if (!keyInput.trim()) return;
    setAdminKey(keyInput.trim());
    setAuthed(true);
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#FFF8F0] flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow p-8 max-w-sm w-full">
          <h1 className="text-xl font-semibold mb-2">Admin · Feedback</h1>
          <p className="text-sm text-gray-500 mb-4">Enter your admin key</p>
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleLogin(); }}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 mb-3"
            placeholder="X-Admin-Key"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-2 rounded-lg transition-all"
          >
            Se connecter
          </button>
          {error && <p className="text-xs text-red-500 mt-3">{error}</p>}
        </div>
      </div>
    );
  }

  const items: FeedbackItem[] = (data?.items || []).filter((r) => {
    if (filterType && r.feedback !== filterType) return false;
    if (filterUser && !(r.user_email || "").toLowerCase().includes(filterUser.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#FFF8F0] p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-[#0A1F3D]">Feedback Telegram</h1>
            <p className="text-sm text-gray-500">
              Clics utilisateur sur les boutons 👍 / 👎 / ⏱️ des alertes.
              1 ligne = 1 clic réel (dédupliqué par message Telegram).
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Link
              href="/admin"
              className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-white transition-colors"
            >
              ← Admin
            </Link>
            <Link
              href="/admin/users"
              className="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-white transition-colors"
            >
              Users
            </Link>
            <button
              onClick={reload}
              className="text-xs text-cyan-600 hover:text-cyan-700 px-3 py-1.5 rounded-lg border border-cyan-200 hover:bg-cyan-50 transition-colors"
            >
              ↻ Rafraîchir
            </button>
          </div>
        </header>

        {/* Stats */}
        {data && (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
            <Stat label="Clics total" value={String(data.total_clicks)} />
            <Stat label="Utilisateurs" value={String(data.distinct_users)} />
            <Stat label="👍 Bon" value={String(data.by_type.good ?? 0)} cls="text-emerald-600" />
            <Stat label="👎 Faux" value={String(data.by_type.bad ?? 0)} cls="text-rose-600" />
            <Stat label="⏱️ Trop tard" value={String(data.by_type.too_late ?? 0)} cls="text-amber-600" />
            <Stat
              label="⚠️ Sans ouverture"
              value={String(data.feedback_without_open ?? 0)}
              cls="text-orange-600"
            />
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 mb-4 flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-600">Fenêtre :</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
          >
            <option value={1}>24h</option>
            <option value={7}>7 jours</option>
            <option value={30}>30 jours</option>
            <option value={90}>90 jours</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
          >
            <option value="">Tous types</option>
            <option value="good">👍 Bon</option>
            <option value="bad">👎 Faux</option>
            <option value="too_late">⏱️ Trop tard</option>
          </select>
          <input
            type="text"
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
            placeholder="Filtrer par email"
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 flex-1 min-w-[200px]"
          />
          {loading && <span className="text-xs text-gray-400">Chargement…</span>}
        </div>

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-3 mb-4">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="bg-white rounded-2xl shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 text-left text-gray-500">
              <tr>
                <th className="p-3">Quand</th>
                <th className="p-3">Feedback</th>
                <th className="p-3">User</th>
                <th className="p-3">Alerte</th>
                <th className="p-3">Type</th>
                <th className="p-3 text-right">Prix</th>
                <th className="p-3 text-right">Discount</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-gray-400 text-sm">
                    Aucun feedback dans cette fenêtre.
                  </td>
                </tr>
              )}
              {items.map((r) => {
                const meta = FEEDBACK_META[r.feedback] || { emoji: "?", label: r.feedback, cls: "bg-gray-50 text-gray-700 border-gray-200" };
                return (
                  <tr key={r.message_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="p-3 text-xs text-gray-500 tabular-nums whitespace-nowrap">
                      {fmt(r.feedback_at)}
                    </td>
                    <td className="p-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${meta.cls}`}>
                        {meta.emoji} {meta.label}
                      </span>
                      {!r.opened_link && (
                        <span
                          className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full border bg-orange-50 text-orange-700 border-orange-200 whitespace-nowrap"
                          title="Feedback envoyé sans avoir ouvert le lien de l'alerte"
                        >
                          ⚠️ sans ouverture
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-xs">{r.user_email}</td>
                    <td className="p-3 font-medium">{r.destination ?? "—"}</td>
                    <td className="p-3 text-xs text-gray-500">{r.alert_type ?? "—"}</td>
                    <td className="p-3 text-right tabular-nums">
                      {r.price != null ? `${Math.round(r.price)}€` : "—"}
                    </td>
                    <td className="p-3 text-right tabular-nums text-gray-500">
                      {r.discount_pct != null ? `-${Math.round(r.discount_pct)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums ${cls || "text-[#0A1F3D]"}`}>
        {value}
      </div>
    </div>
  );
}
