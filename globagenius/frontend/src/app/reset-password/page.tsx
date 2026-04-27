"use client";

import Link from "next/link";

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-[#FFF8F0] flex items-start sm:items-center justify-center px-4 py-8 sm:py-0">
      <div className="w-full max-w-sm text-center">
        <Link href="/" className="font-[family-name:var(--font-dm-serif)] text-xl leading-none block text-center mb-10">
          Globe<span className="text-[#FF6B47]">Genius</span>
        </Link>

        <div className="bg-white rounded-2xl border border-gray-100 p-8 shadow-sm">
          <div className="text-3xl mb-4">🔑</div>
          <h1 className="font-[family-name:var(--font-dm-serif)] text-2xl mb-3">
            Mot de passe oublié
          </h1>
          <p className="text-sm text-gray-500 mb-6 leading-relaxed">
            La réinitialisation par email n&apos;est pas encore disponible.
            Si vous connaissez votre mot de passe actuel, vous pouvez le changer depuis votre profil.
          </p>
          <div className="space-y-3">
            <Link
              href="/login"
              className="block w-full bg-[#FF6B47] hover:bg-[#E55A38] text-white font-semibold py-3 rounded-xl transition-all text-sm"
            >
              Retour à la connexion
            </Link>
            <Link
              href="/profile"
              className="block w-full py-3 rounded-xl border border-gray-200 text-gray-500 font-medium hover:bg-gray-50 transition-colors text-sm"
            >
              Modifier mon mot de passe →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
