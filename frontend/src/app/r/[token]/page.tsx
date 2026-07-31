"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { Wordmark } from "../../_components/Wordmark";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RedirectPage() {
  const params = useParams();
  const token = params?.token as string | undefined;

  useEffect(() => {
    if (token) window.location.replace(`${API_URL}/r/${token}`);
  }, [token]);

  return (
    <div className="site-hero-soft flex min-h-screen items-center justify-center px-5 text-white">
      <div className="text-center">
        <Wordmark variant="inverse" size="md" />
        <div className="mx-auto mt-9 h-10 w-10 animate-spin rounded-full border-2 border-white/25 border-t-white" aria-hidden="true" />
        <h1 className="mt-6 font-[family-name:var(--font-dm-serif)] text-3xl">Vérification du lien</h1>
        <p className="mt-3 text-sm text-white/60">Vous allez être redirigé vers le vendeur du billet.</p>
      </div>
    </div>
  );
}
