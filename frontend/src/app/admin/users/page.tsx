"use client";

import { useEffect, useState } from "react";
import {
  listUsers,
  grantPremium,
  revokePremium,
  updateMinDiscount,
  resetPrefs,
  hasAdminKey,
  setAdminKey,
  type AdminUser,
} from "@/lib/admin";

export default function AdminUsersPage() {
  const [authed, setAuthed] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [grantExpiresAt, setGrantExpiresAt] = useState("");
  const [grantReason, setGrantReason] = useState("");

  useEffect(() => {
    if (hasAdminKey()) {
      setAuthed(true);
    }
  }, []);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const res = await listUsers();
      setUsers(res.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (authed) reload();

  }, [authed]);

  function handleLogin() {
    if (!keyInput.trim()) return;
    setAdminKey(keyInput.trim());
    setAuthed(true);
  }

  function normalizeExpiry(value: string): string | undefined {
    if (!value) return undefined;
    if (value.endsWith("Z")) return value;
    // datetime-local format: 2026-12-31T23:59
    return `${value}:00Z`;
  }

  async function handleGrant(user: AdminUser) {
    try {
      await grantPremium(
        user.id,
        normalizeExpiry(grantExpiresAt),
        grantReason || undefined
      );
      setSelected(null);
      setGrantExpiresAt("");
      setGrantReason("");
      await reload();
    } catch (e) {
      alert(`Failed: ${e instanceof Error ? e.message : "error"}`);
    }
  }

  async function handleRevoke(user: AdminUser) {
    if (!confirm(`Revoke premium for ${user.email}?`)) return;
    try {
      await revokePremium(user.id);
      await reload();
    } catch (e) {
      alert(`Failed: ${e instanceof Error ? e.message : "error"}`);
    }
  }

  async function handleMinDiscount(user: AdminUser, value: number) {
    try {
      await updateMinDiscount(user.id, value);
      await reload();
    } catch (e) {
      alert(`Failed: ${e instanceof Error ? e.message : "error"}`);
    }
  }

  async function handleReset(user: AdminUser) {
    if (!confirm(`Reset preferences for ${user.email}?`)) return;
    try {
      await resetPrefs(user.id);
      await reload();
    } catch (e) {
      alert(`Failed: ${e instanceof Error ? e.message : "error"}`);
    }
  }

  if (!authed) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow p-8 max-w-sm w-full">
          <h1 className="text-xl font-semibold mb-2">Admin console</h1>
          <p className="text-sm text-gray-500 mb-4">Enter your admin key</p>
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleLogin();
            }}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 mb-3"
            placeholder="X-Admin-Key"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-2 rounded-lg"
          >
            Se connecter
          </button>
          {error && (
            <p className="text-xs text-red-500 mt-3">{error}</p>
          )}
        </div>
      </div>
    );
  }

  const filtered = users.filter(
    (u) => !filter || u.email.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">
            Admin — Users ({users.length})
          </h1>
          <button
            onClick={() => {
              sessionStorage.removeItem("gg_admin_key");
              setAuthed(false);
              setUsers([]);
            }}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Logout
          </button>
        </div>

        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by email"
          className="w-full md:w-80 border border-gray-200 rounded-lg px-3 py-2 mb-4"
        />

        {loading && <div className="text-gray-400 mb-4">Loading…</div>}
        {error && !loading && (
          <div className="text-sm text-red-500 mb-4">{error}</div>
        )}

        <div className="bg-white rounded-2xl shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-100 text-left text-gray-500">
              <tr>
                <th className="p-3">Email</th>
                <th className="p-3">Tier</th>
                <th className="p-3">Min%</th>
                <th className="p-3">Stripe</th>
                <th className="p-3">TG</th>
                <th className="p-3">Grant</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-gray-50 hover:bg-gray-50"
                >
                  <td className="p-3">
                    {u.email}
                    {u.is_admin && (
                      <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full ml-2">
                        admin
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <span
                      className={
                        u.tier === "premium"
                          ? "text-cyan-600 font-semibold"
                          : "text-gray-400"
                      }
                    >
                      {u.tier}
                    </span>
                  </td>
                  <td className="p-3">
                    <select
                      value={u.min_discount}
                      onChange={(e) =>
                        handleMinDiscount(u, parseInt(e.target.value, 10))
                      }
                      className="border border-gray-200 rounded px-2 py-1 text-xs"
                    >
                      {[20, 30, 40, 50, 60].map((v) => (
                        <option key={v} value={v}>
                          {v}%
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="p-3">{u.stripe_customer_id ? "✓" : "—"}</td>
                  <td className="p-3">{u.telegram_connected ? "✓" : "—"}</td>
                  <td className="p-3">
                    {u.has_grant ? (
                      <span className="text-xs text-green-600">
                        ✓{" "}
                        {u.grant_expires_at
                          ? `until ${u.grant_expires_at.slice(0, 10)}`
                          : "∞"}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="p-3 flex gap-1">
                    {u.has_grant ? (
                      <button
                        onClick={() => handleRevoke(u)}
                        className="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-2 py-1 rounded"
                      >
                        Revoke
                      </button>
                    ) : (
                      <button
                        onClick={() => setSelected(u)}
                        className="text-xs bg-cyan-50 hover:bg-cyan-100 text-cyan-700 px-2 py-1 rounded"
                      >
                        Grant
                      </button>
                    )}
                    <button
                      onClick={() => handleReset(u)}
                      className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded"
                    >
                      Reset
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selected && (
          <div
            className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
            onClick={() => setSelected(null)}
          >
            <div
              className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-lg font-semibold mb-2">
                Grant premium to {selected.email}
              </h2>
              <label className="text-sm text-gray-500">
                Expires at (optional)
              </label>
              <input
                type="datetime-local"
                value={grantExpiresAt}
                onChange={(e) => setGrantExpiresAt(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 mb-3 mt-1"
              />
              <label className="text-sm text-gray-500">Reason (optional)</label>
              <textarea
                value={grantReason}
                onChange={(e) => setGrantReason(e.target.value)}
                rows={2}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 mb-4 mt-1"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleGrant(selected)}
                  className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-2 rounded-lg"
                >
                  Grant
                </button>
                <button
                  onClick={() => {
                    setSelected(null);
                    setGrantExpiresAt("");
                    setGrantReason("");
                  }}
                  className="flex-1 border border-gray-200 text-gray-700 py-2 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
