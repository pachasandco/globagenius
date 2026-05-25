import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { getDestinationGuide } from "@/lib/api";
import { iataFor, slugFor } from "@/lib/destinations";

// URL param renamed from [iata] to [slug] in 2026-05 as part of the
// migration from IATA-code URLs (/destination/dub) to SEO-friendly
// slug URLs (/destination/dublin). Old IATA URLs are 301-redirected
// to the slug version via next.config.ts.
type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const iata = iataFor(slug);
  if (!iata) {
    return { title: "Destination non trouvée — Globe Genius" };
  }

  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) {
    return { title: "Destination non trouvée — Globe Genius" };
  }

  const destination = guide.article.destination;
  // Canonical always points to the slug form. If a visitor lands on a
  // legacy /destination/<iata> URL, next.config.ts 301s them here, so
  // the canonical never contains the IATA.
  const canonicalSlug = slugFor(guide.article.iata);
  const canonical = `https://globegenius.app/destination/${canonicalSlug}`;

  // Pull the cheapest live deal price (if any) to inject in the title/description.
  // This gives us transactional, click-worthy SERP snippets that rank for
  // "vol [ville] pas cher" rather than competing with Lonely Planet on
  // "[ville] guide voyage" (which we'll never win).
  const minPrice = guide.deals.length > 0
    ? Math.min(...guide.deals.map((d) => d.price))
    : null;

  const title = minPrice !== null
    ? `Vol ${destination} dès ${minPrice}€ — Bons plans & guide | Globe Genius`
    : `Vol pas cher ${destination} — Bons plans & guide | Globe Genius`;

  const description = minPrice !== null
    ? `Vol pour ${destination} détecté dès ${minPrice}€. Globe Genius scanne plus de 200 compagnies en continu et t'envoie une alerte gratuite dès qu'un deal arrive. Guide voyage ${destination} inclus.`
    : `Trouve le meilleur vol pour ${destination} grâce à Globe Genius. Alertes gratuites dès qu'un deal est détecté, plus de 200 compagnies scannées en continu. Guide voyage ${destination} inclus.`;

  return {
    title,
    description,
    alternates: { canonical },
    openGraph: {
      title,
      description,
      url: canonical,
      siteName: "Globe Genius",
      locale: "fr_FR",
      type: "article",
      images: guide.photo.url
        ? [{ url: guide.photo.url, width: 1200, height: 630, alt: destination }]
        : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: guide.photo.url ? [guide.photo.url] : undefined,
    },
  };
}

export default async function DestinationPage({ params }: PageProps) {
  const { slug } = await params;
  const iata = iataFor(slug);
  if (!iata) notFound();

  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) notFound();

  const a = guide.article;
  const photo = guide.photo;
  const deals = guide.deals;

  // Pick the cheapest live deal for the hero banner. Falls back to a
  // "monitoring" empty state when no live deal is available.
  const bestDeal = deals.length > 0
    ? deals.reduce((min, d) => (d.price < min.price ? d : min), deals[0])
    : null;

  // JSON-LD: TouristDestination + FAQPage + BreadcrumbList for rich results.
  // Canonical URL uses the slug, never the IATA, so the schema stays
  // consistent with what Google sees in the search results.
  const canonicalSlug = slugFor(a.iata);
  const canonicalUrl = `https://globegenius.app/destination/${canonicalSlug}`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TouristDestination",
        name: a.destination,
        description: a.meta_description,
        image: photo.url || undefined,
        url: canonicalUrl,
      },
      {
        "@type": "FAQPage",
        mainEntity: a.faq.map((q) => ({
          "@type": "Question",
          name: q.q,
          acceptedAnswer: { "@type": "Answer", text: q.a },
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Accueil",
            item: "https://globegenius.app",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Destinations",
            item: "https://globegenius.app/articles",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: a.destination,
            item: canonicalUrl,
          },
        ],
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

      {/* ── Deal hero block ──────────────────────────────────────────
        Sits between the cover photo and the long-form guide.
        Pulls the cheapest live deal to make the product value visible
        immediately. SEO visitors landing on this page see the deal
        before having to scroll through 4000 words of guide. */}
      <section className="bg-white border-b border-[var(--color-sand)]">
        <div className="mx-auto max-w-3xl px-6 py-6 sm:py-8">
          {bestDeal ? (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex-1">
                <div className="inline-flex items-center gap-2 rounded-full bg-[var(--color-coral-50)] px-3 py-1 text-xs font-semibold text-[var(--color-coral)] mb-2">
                  <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-coral)]" />
                  Deal détecté
                </div>
                <div className="font-[family-name:var(--font-dm-serif)] text-2xl sm:text-3xl text-[var(--color-ink)] leading-tight">
                  Vol {bestDeal.origin} → {a.destination} dès{" "}
                  <span className="text-[var(--color-coral)]">
                    {bestDeal.price}€
                  </span>
                  {bestDeal.baseline_price > bestDeal.price && (
                    <span className="ml-2 text-base font-normal text-gray-400 line-through align-middle">
                      {bestDeal.baseline_price}€
                    </span>
                  )}
                </div>
                <div className="mt-1 text-sm text-gray-500">
                  {[
                    bestDeal.airline,
                    bestDeal.departure_date
                      ? bestDeal.return_date
                        ? `${bestDeal.departure_date} → ${bestDeal.return_date}`
                        : `${bestDeal.departure_date} (aller simple)`
                      : null,
                    bestDeal.discount_pct > 0
                      ? `-${Math.round(bestDeal.discount_pct)}% vs prix médian`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
                {deals.length > 1 && (
                  <a
                    href="#deals"
                    className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-coral)] hover:underline"
                  >
                    Voir les {deals.length} deals détectés ↓
                  </a>
                )}
              </div>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center rounded-full bg-[var(--color-coral)] px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-coral)] focus-visible:ring-offset-2 whitespace-nowrap"
              >
                Recevoir les alertes (gratuit)
              </Link>
            </div>
          ) : (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex-1">
                <div className="inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600 mb-2">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-gray-400" />
                  Surveillance active
                </div>
                <div className="font-[family-name:var(--font-dm-serif)] text-xl sm:text-2xl text-[var(--color-ink)] leading-tight">
                  Pas de deal sur {a.destination} en ce moment
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  On scanne 200+ compagnies en continu. Reçois une alerte
                  gratuite dès qu&apos;un vol pas cher est détecté pour{" "}
                  {a.destination}.
                </p>
              </div>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center rounded-full bg-[var(--color-coral)] px-6 py-3 text-sm font-bold text-white shadow-sm transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-coral)] focus-visible:ring-offset-2 whitespace-nowrap"
              >
                M&apos;alerter quand un deal arrive
              </Link>
            </div>
          )}
        </div>
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
            <h2
              id="deals"
              className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl scroll-mt-20"
            >
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
