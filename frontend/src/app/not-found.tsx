import Link from "next/link";
import { Wordmark } from "./_components/Wordmark";

export default function NotFound() {
  return (
    <main className="site-hero-soft flex min-h-screen items-center justify-center px-5 text-white">
      <div className="max-w-xl text-center">
        <Wordmark variant="inverse" size="md" />
        <p className="mt-10 text-xs font-bold uppercase tracking-[0.2em] text-[#7DE0D6]">Erreur 404</p>
        <h1 className="mt-4 font-[family-name:var(--font-dm-serif)] text-5xl leading-tight sm:text-6xl">Cette destination n’est pas sur la carte.</h1>
        <p className="mx-auto mt-5 max-w-md text-sm leading-7 text-white/65">La page a été déplacée, supprimée ou l’adresse est incorrecte.</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/" className="rounded-xl bg-white px-6 py-3.5 text-sm font-bold text-[#0B2A3F] hover:bg-[#E9F5F7]">Retour à l’accueil</Link>
          <Link href="/signup" className="rounded-xl border border-white/20 bg-white/10 px-6 py-3.5 text-sm font-bold text-white hover:bg-white/15">Activer mon radar</Link>
        </div>
      </div>
    </main>
  );
}
