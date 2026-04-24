"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RedirectPage() {
  const params = useParams();
  const token = params?.token as string | undefined;

  useEffect(() => {
    if (token) {
      // Redirect to backend — it records the click and issues a 302 to the real URL.
      window.location.replace(`${API_URL}/r/${token}`);
    }
  }, [token]);

  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-center justify-center">
      <div className="text-center">
        <div className="text-2xl mb-2">✈️</div>
        <p className="text-sm text-gray-400">Redirection en cours...</p>
      </div>
    </div>
  );
}
