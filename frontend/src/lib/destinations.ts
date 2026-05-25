/**
 * IATA ↔ semantic-slug mapping for destination pages.
 *
 * Why this exists:
 *  - Old URLs were `/destination/dub`, `/destination/fco`, etc.
 *    Nobody types "dub" into Google. Ranking on city-code-only URLs
 *    is effectively impossible.
 *  - New URLs are `/destination/dublin`, `/destination/rome`, etc.
 *    They match real search intent and inherit keywords from the slug.
 *
 * Old IATA URLs are 301-redirected to the slug version via
 * `next.config.js` (see `redirects()`). Search Console will replace
 * the old URLs in the index within 2-4 weeks of deploy.
 *
 * If you add a new destination to the backend, add the mapping here
 * too. Until you do, `slugFor()` falls back to the lowercase IATA,
 * which keeps the page working (just without the SEO win).
 */

export const IATA_TO_SLUG: Record<string, string> = {
  // Spain
  bcn: "barcelone",
  mad: "madrid",
  svq: "seville",
  agp: "malaga",
  alc: "alicante",
  vlc: "valence",
  pmi: "palma-de-majorque",
  ibz: "ibiza",
  lpa: "las-palmas",
  tfs: "tenerife",

  // Portugal
  lis: "lisbonne",
  opo: "porto",
  fao: "faro",

  // Italy
  fco: "rome",
  vce: "venise",
  nap: "naples",
  bgy: "bergame",

  // Greece
  ath: "athenes",
  her: "heraklion",
  skg: "thessalonique",

  // Croatia / Montenegro
  spu: "split",
  dbv: "dubrovnik",
  tiv: "tivat",

  // Northern / Central Europe
  ber: "berlin",
  prg: "prague",
  bud: "budapest",
  waw: "varsovie",
  wmi: "varsovie-modlin",
  cph: "copenhague",

  // UK / Ireland
  dub: "dublin",
  edi: "edimbourg",
  stn: "londres",

  // Turkey
  saw: "istanbul",

  // Maghreb
  cmn: "casablanca",
  rak: "marrakech",
  fez: "fes",
  tng: "tanger",
  aga: "agadir",
  alg: "alger",
  tun: "tunis",

  // Long-haul
  jfk: "new-york",
  yvr: "vancouver",
  ptp: "pointe-a-pitre",
  puj: "punta-cana",
};

// Reverse map, computed once at module load.
export const SLUG_TO_IATA: Record<string, string> = Object.fromEntries(
  Object.entries(IATA_TO_SLUG).map(([iata, slug]) => [slug, iata]),
);

/**
 * IATA code (any case) → SEO slug. Falls back to lowercase IATA when
 * no mapping is registered (keeps the page reachable, just without
 * the keyword boost).
 */
export function slugFor(iata: string): string {
  const lower = iata.trim().toLowerCase();
  return IATA_TO_SLUG[lower] ?? lower;
}

/**
 * Slug → IATA code (uppercase, as expected by `/api/destinations/{iata}`).
 * Returns `null` when the slug is unknown so the page can render a 404.
 *
 * Also tolerates a raw IATA in the slot (e.g. someone hits
 * `/destination/dub` before the redirect kicks in or the asset cache
 * is invalidated). The Next.js 301 still does the heavy lifting.
 */
export function iataFor(slug: string): string | null {
  const lower = slug.trim().toLowerCase();
  if (SLUG_TO_IATA[lower]) {
    return SLUG_TO_IATA[lower].toUpperCase();
  }
  // Tolerate a 3-letter IATA code as a fallback so the page still
  // renders if the redirect didn't fire (e.g. internal links not yet
  // migrated). The 301 will catch the next visit.
  if (/^[a-z]{3,4}$/i.test(lower)) {
    return lower.toUpperCase();
  }
  return null;
}
