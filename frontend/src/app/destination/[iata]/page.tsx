import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { getDestinationGuide } from "@/lib/api";

type PageProps = { params: Promise<{ iata: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { iata } = await params;
  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) {
    return { title: "Destination non trouvée" };
  }
  return {
    title: guide.article.title,
    description: guide.article.meta_description,
    openGraph: {
      title: guide.article.title,
      description: guide.article.meta_description,
      images: guide.photo.url ? [{ url: guide.photo.url }] : undefined,
      type: "article",
    },
    alternates: {
      canonical: `https://globegenius.app/destination/${guide.article.iata.toLowerCase()}`,
    },
  };
}

export default async function DestinationPage({ params }: PageProps) {
  const { iata } = await params;
  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) notFound();

  const a = guide.article;
  const photo = guide.photo;
  const deals = guide.deals;

  // JSON-LD: TouristDestination + FAQPage for rich results
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TouristDestination",
        name: a.destination,
        description: a.meta_description,
        image: photo.url || undefined,
        url: `https://globegenius.app/destination/${a.iata.toLowerCase()}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: a.faq.map((q) => ({
          "@type": "Question",
          name: q.q,
          acceptedAnswer: { "@type": "Answer", text: q.a },
        })),
      },
    ],
  };

  return (
    <main className="min-h-screen bg-[var(--color-cream)]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      {/* Hero with cover photo */}
      <section className="relative h-[60vh] min-h-[400px] w-full overflow-hidden bg-[var(--color-ink)]">
        {photo.url && (
          <Image
            src={photo.url}
            alt={`${a.destination} — photo de couverture`}
            fill
            priority
            className="object-cover"
            sizes="100vw"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="relative z-10 flex h-full flex-col items-center justify-end p-8 text-center text-white">
          <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-6xl mb-4 max-w-4xl">
            {a.h1}
          </h1>
          <p className="max-w-2xl text-lg opacity-90">{a.meta_description}</p>
        </div>
        {photo.photographer_name && (
          <div className="absolute bottom-2 right-3 text-xs text-white/70">
            Photo :{" "}
            <a href={photo.photographer_url} target="_blank" rel="noopener noreferrer" className="underline">
              {photo.photographer_name}
            </a>{" "}
            sur{" "}
            <a href="https://unsplash.com" target="_blank" rel="noopener noreferrer" className="underline">
              Unsplash
            </a>
          </div>
        )}
      </section>

      {/* Article body */}
      <article className="mx-auto max-w-3xl px-6 py-12 prose prose-lg">
        <p className="text-xl font-medium text-[var(--color-ink)]">{a.lead}</p>
        <p className="text-[var(--color-ink)]/80">{a.nut_graf}</p>

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">À voir, à faire, à manger</h2>
        {a.top_picks.map((p, i) => (
          <div key={i} className="mb-8 border-l-4 border-[var(--color-coral)] pl-4">
            <h3 className="text-xl font-bold">
              {i + 1}. {p.name} — <span className="font-normal italic">{p.angle}</span>
            </h3>
            <p>{p.description}</p>
            <p className="text-sm text-gray-600">
              <strong>Pratique :</strong> {p.practical}
            </p>
          </div>
        ))}

        {a.neighborhoods && a.neighborhoods.length > 0 && (
          <>
            <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">Les quartiers</h2>
            {a.neighborhoods.map((nb, i) => (
              <div key={i} className="mb-8">
                <h3 className="text-xl font-bold">
                  {nb.name} — <span className="font-normal italic">{nb.character}</span>
                </h3>
                <p>{nb.description}</p>
                {nb.highlights && (
                  <p className="text-sm text-gray-600">
                    <strong>À voir :</strong> {nb.highlights}
                  </p>
                )}
              </div>
            ))}
          </>
        )}

        {/* Deals slot */}
        {deals.length > 0 && (
          <>
            <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">
              Vols pas chers vers {a.destination} en ce moment
            </h2>
            <div className="not-prose grid gap-4 sm:grid-cols-2">
              {deals.map((d, i) => (
                <div key={i} className="rounded-2xl border border-[var(--color-sand)] bg-white p-4">
                  <div className="text-sm font-bold">
                    {d.origin} → {d.destination} · {d.airline ?? ""}
                  </div>
                  <div className="text-2xl font-extrabold text-[var(--color-coral)]">{d.price}€ <span className="text-sm font-normal text-gray-400 line-through">{d.baseline_price}€</span></div>
                  <div className="text-xs text-gray-600">
                    {d.departure_date} {d.return_date ? `→ ${d.return_date}` : "(aller simple)"}
                  </div>
                  {d.source_url && (
                    <a href={d.source_url} target="_blank" rel="noopener noreferrer"
                       className="mt-2 inline-block text-sm text-[var(--color-coral)] hover:underline">
                      Voir le deal →
                    </a>
                  )}
                </div>
              ))}
            </div>
            <p className="mt-4 text-center">
              <Link href="/signup" className="inline-block rounded-xl bg-[var(--color-coral)] px-6 py-3 font-bold text-white hover:bg-[var(--color-coral-hover)]">
                Recevez les nouveaux deals sur Telegram (gratuit)
              </Link>
            </p>
          </>
        )}

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">Infos pratiques</h2>
        <ul>
          {Object.entries(a.infos_pratiques).map(([k, v]) => (
            <li key={k}>
              <strong>{k.replace(/_/g, " ")} :</strong> {v}
            </li>
          ))}
        </ul>

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">FAQ</h2>
        {a.faq.map((q, i) => (
          <details key={i} className="mb-3">
            <summary className="cursor-pointer font-bold">{q.q}</summary>
            <p className="mt-2 text-[var(--color-ink)]/80">{q.a}</p>
          </details>
        ))}

        {a.sources.length > 0 && (
          <>
            <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">Sources</h2>
            <ul className="text-sm text-gray-600">
              {a.sources.map((s) => (
                <li key={s}>
                  <a href={s} target="_blank" rel="noopener noreferrer" className="underline">{s}</a>
                </li>
              ))}
            </ul>
          </>
        )}
      </article>
    </main>
  );
}
