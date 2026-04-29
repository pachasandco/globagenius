"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * Editorial-style world map for the landing hero.
 *
 * Style brief: deep-navy datavis, à la Bloomberg / The Guardian / FT.
 * - Continents drawn as a *stipple* of small dots (denser inside land,
 *   nothing outside) rather than solid blobs. Reads as datavis, not as
 *   a cartoon map.
 * - Route arcs run from Paris (anchor) to each pinned deal, dashed coral.
 * - Each pin shows: city / striked usual price → deal price / -X%.
 *   Usual prices are baseline reference fares per IATA — not the real
 *   booking price (the API never exposes that to anonymous visitors).
 * - "EN DIRECT" status pill top-left to signal live data.
 *
 * Pin positions are coarse approximations on a 0-100 viewBox (Paris ≈
 * (50, 38)). Good enough for an editorial vibe; not a real projection.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LandingDeal = {
  origin: string;
  destination: string;
  discount_pct: number;
};

// IATA → (x, y) on a 0-100 viewBox, label for the pin card.
const CITY_COORDS: Record<string, { x: number; y: number; label: string }> = {
  // France
  CDG: { x: 50, y: 38, label: "Paris" },
  ORY: { x: 50, y: 38, label: "Paris" },
  BVA: { x: 50, y: 37, label: "Paris" },
  LYS: { x: 51, y: 41, label: "Lyon" },
  MRS: { x: 51, y: 44, label: "Marseille" },
  NCE: { x: 53, y: 44, label: "Nice" },
  BOD: { x: 48, y: 43, label: "Bordeaux" },
  NTE: { x: 47, y: 41, label: "Nantes" },
  TLS: { x: 49, y: 44, label: "Toulouse" },
  // Iberia
  LIS: { x: 43, y: 47, label: "Lisbonne" },
  OPO: { x: 43, y: 45, label: "Porto" },
  FAO: { x: 43, y: 48, label: "Faro" },
  MAD: { x: 45, y: 46, label: "Madrid" },
  BCN: { x: 49, y: 45, label: "Barcelone" },
  AGP: { x: 45, y: 48, label: "Malaga" },
  PMI: { x: 49, y: 47, label: "Palma" },
  ALC: { x: 47, y: 47, label: "Alicante" },
  IBZ: { x: 48, y: 47, label: "Ibiza" },
  SVQ: { x: 44, y: 48, label: "Séville" },
  VLC: { x: 47, y: 46, label: "Valence" },
  TFS: { x: 38, y: 53, label: "Ténérife" },
  ACE: { x: 39, y: 53, label: "Lanzarote" },
  LPA: { x: 38, y: 54, label: "Las Palmas" },
  FUE: { x: 39, y: 54, label: "Fuerteventura" },
  FNC: { x: 38, y: 51, label: "Madère" },
  PDL: { x: 35, y: 47, label: "Açores" },
  // Italy
  FCO: { x: 55, y: 46, label: "Rome" },
  MXP: { x: 53, y: 42, label: "Milan" },
  LIN: { x: 53, y: 42, label: "Milan" },
  BGY: { x: 54, y: 42, label: "Bergame" },
  VCE: { x: 55, y: 41, label: "Venise" },
  TSF: { x: 55, y: 41, label: "Trévise" },
  NAP: { x: 56, y: 47, label: "Naples" },
  BLQ: { x: 54, y: 43, label: "Bologne" },
  BRI: { x: 57, y: 47, label: "Bari" },
  CTA: { x: 56, y: 49, label: "Catane" },
  CAG: { x: 54, y: 47, label: "Cagliari" },
  OLB: { x: 54, y: 45, label: "Olbia" },
  // Greece / Balkans / Eastern Europe
  ATH: { x: 60, y: 47, label: "Athènes" },
  HER: { x: 61, y: 49, label: "Héraklion" },
  JMK: { x: 61, y: 47, label: "Mykonos" },
  JTR: { x: 61, y: 48, label: "Santorin" },
  RHO: { x: 62, y: 48, label: "Rhodes" },
  CFU: { x: 59, y: 46, label: "Corfou" },
  SKG: { x: 59, y: 45, label: "Thessalonique" },
  SPU: { x: 57, y: 44, label: "Split" },
  DBV: { x: 58, y: 44, label: "Dubrovnik" },
  TIV: { x: 58, y: 44, label: "Tivat" },
  ZAG: { x: 56, y: 42, label: "Zagreb" },
  TIA: { x: 58, y: 45, label: "Tirana" },
  BEG: { x: 58, y: 43, label: "Belgrade" },
  SOF: { x: 59, y: 44, label: "Sofia" },
  OTP: { x: 60, y: 42, label: "Bucarest" },
  SKP: { x: 59, y: 44, label: "Skopje" },
  IST: { x: 63, y: 44, label: "Istanbul" },
  SAW: { x: 63, y: 44, label: "Istanbul" },
  // Northern Europe
  AMS: { x: 51, y: 34, label: "Amsterdam" },
  BER: { x: 55, y: 34, label: "Berlin" },
  BRU: { x: 51, y: 35, label: "Bruxelles" },
  LHR: { x: 47, y: 33, label: "Londres" },
  LGW: { x: 47, y: 33, label: "Londres" },
  STN: { x: 47, y: 32, label: "Londres" },
  LTN: { x: 47, y: 33, label: "Londres" },
  MAN: { x: 46, y: 31, label: "Manchester" },
  BHX: { x: 46, y: 32, label: "Birmingham" },
  GLA: { x: 45, y: 29, label: "Glasgow" },
  EDI: { x: 46, y: 29, label: "Édimbourg" },
  DUB: { x: 44, y: 32, label: "Dublin" },
  PRG: { x: 56, y: 36, label: "Prague" },
  VIE: { x: 57, y: 38, label: "Vienne" },
  BUD: { x: 58, y: 39, label: "Budapest" },
  WAW: { x: 58, y: 34, label: "Varsovie" },
  KRK: { x: 58, y: 36, label: "Cracovie" },
  CPH: { x: 54, y: 30, label: "Copenhague" },
  HEL: { x: 60, y: 26, label: "Helsinki" },
  ARN: { x: 56, y: 28, label: "Stockholm" },
  OSL: { x: 54, y: 27, label: "Oslo" },
  RIX: { x: 60, y: 30, label: "Riga" },
  TLL: { x: 60, y: 28, label: "Tallinn" },
  VNO: { x: 60, y: 31, label: "Vilnius" },
  ZRH: { x: 53, y: 39, label: "Zurich" },
  GVA: { x: 52, y: 40, label: "Genève" },
  BSL: { x: 53, y: 39, label: "Bâle" },
  LUX: { x: 52, y: 36, label: "Luxembourg" },
  // Americas
  JFK: { x: 22, y: 42, label: "New York" },
  EWR: { x: 21, y: 42, label: "Newark" },
  YUL: { x: 19, y: 36, label: "Montréal" },
  MIA: { x: 19, y: 53, label: "Miami" },
  LAX: { x: 8, y: 47, label: "Los Angeles" },
  SFO: { x: 6, y: 44, label: "San Francisco" },
  CUN: { x: 14, y: 56, label: "Cancún" },
  PUJ: { x: 22, y: 58, label: "Punta Cana" },
  GIG: { x: 30, y: 75, label: "Rio" },
  EZE: { x: 27, y: 82, label: "Buenos Aires" },
  // Asia / Oceania
  BKK: { x: 79, y: 56, label: "Bangkok" },
  SIN: { x: 81, y: 64, label: "Singapour" },
  KUL: { x: 80, y: 63, label: "Kuala Lumpur" },
  HKG: { x: 84, y: 50, label: "Hong Kong" },
  NRT: { x: 89, y: 42, label: "Tokyo" },
  HND: { x: 89, y: 42, label: "Tokyo" },
  ICN: { x: 87, y: 41, label: "Séoul" },
  BOM: { x: 71, y: 53, label: "Mumbai" },
  DEL: { x: 73, y: 47, label: "Delhi" },
  DXB: { x: 67, y: 50, label: "Dubaï" },
  DOH: { x: 66, y: 51, label: "Doha" },
  TLV: { x: 62, y: 49, label: "Tel Aviv" },
  CAI: { x: 60, y: 51, label: "Le Caire" },
  SYD: { x: 93, y: 80, label: "Sydney" },
  // Africa
  RAK: { x: 44, y: 51, label: "Marrakech" },
  CMN: { x: 44, y: 50, label: "Casablanca" },
  TUN: { x: 53, y: 49, label: "Tunis" },
  ALG: { x: 50, y: 49, label: "Alger" },
  CPT: { x: 56, y: 82, label: "Le Cap" },
  JNB: { x: 60, y: 78, label: "Johannesburg" },
  ZNZ: { x: 64, y: 70, label: "Zanzibar" },
};

// Reference round-trip fare per destination (€). Used to render the
// striked-out "usual price" on each pin. These are illustrative anchors,
// not the live booking price — we never expose the true booking fare on
// the anonymous landing.
const USUAL_PRICE_EUR: Record<string, number> = {
  // Long-haul
  NRT: 850, HND: 850, ICN: 800, HKG: 780, BKK: 780, SIN: 850, KUL: 750,
  JFK: 580, EWR: 580, LAX: 720, SFO: 720, MIA: 620, YUL: 560,
  GIG: 850, EZE: 950, SYD: 1300,
  BOM: 700, DEL: 720, DXB: 480, DOH: 520, TLV: 380, CAI: 380,
  // Africa
  RAK: 220, CMN: 200, TUN: 240, ALG: 220, ZNZ: 700, JNB: 850, CPT: 900,
  // Caribbean
  CUN: 720, PUJ: 750,
  // Iberia / Mediterranean (low-cost)
  LIS: 180, OPO: 170, FAO: 190, MAD: 160, BCN: 150, AGP: 180, PMI: 160,
  ALC: 160, IBZ: 180, SVQ: 180, VLC: 150,
  TFS: 280, ACE: 280, LPA: 290, FUE: 280, FNC: 280, PDL: 320,
  // Italy
  FCO: 180, MXP: 150, LIN: 150, BGY: 140, VCE: 170, TSF: 170, NAP: 200,
  BLQ: 170, BRI: 220, CTA: 220, CAG: 200, OLB: 200,
  // Greece / Balkans / Turkey
  ATH: 220, HER: 280, JMK: 320, JTR: 320, RHO: 280, CFU: 240, SKG: 240,
  SPU: 220, DBV: 240, TIV: 250, ZAG: 200, TIA: 200, BEG: 200, SOF: 220,
  OTP: 180, SKP: 220, IST: 240, SAW: 240,
  // Northern / Eastern Europe
  AMS: 150, BER: 160, BRU: 150, LHR: 150, LGW: 150, STN: 130, LTN: 140,
  MAN: 180, BHX: 180, GLA: 200, EDI: 200, DUB: 180,
  PRG: 180, VIE: 180, BUD: 180, WAW: 180, KRK: 180,
  CPH: 200, HEL: 280, ARN: 240, OSL: 220, RIX: 220, TLL: 220, VNO: 220,
  ZRH: 180, GVA: 160, BSL: 160, LUX: 200,
};

const PARIS = { x: 50, y: 38 };

// Stylised continent silhouettes on the 0-100 viewBox. More vertices than
// blob shapes (so they actually read as continents) but still abstract — a
// real Mercator dump would crush the editorial vibe. Drawn three times
// (fill / stipple / outline) in render.
const CONTINENT_PATHS: string[] = [
  // North America
  "M 4 24 L 9 22 L 14 22 L 17 24 L 20 23 L 23 25 L 24 28 L 25 32 L 24 36 L 22 40 L 20 42 L 19 45 L 17 48 L 15 52 L 13 55 L 11 53 L 9 50 L 7 46 L 5 40 L 4 33 Z",
  // Greenland
  "M 28 18 L 33 17 L 35 21 L 33 24 L 29 23 Z",
  // Central America
  "M 13 55 L 16 57 L 18 60 L 20 60 L 17 62 L 14 60 L 12 57 Z",
  // South America
  "M 22 58 L 26 58 L 30 62 L 32 68 L 32 74 L 30 80 L 27 84 L 24 84 L 22 78 L 21 70 L 22 64 Z",
  // Iberian peninsula
  "M 41 44 L 44 42 L 47 41 L 48 43 L 47 47 L 44 49 L 42 48 Z",
  // Continental Europe
  "M 44 28 L 48 26 L 52 27 L 55 28 L 58 30 L 60 33 L 60 37 L 58 40 L 55 42 L 52 42 L 48 41 L 46 38 L 44 34 Z",
  // British Isles
  "M 43 30 L 46 28 L 47 31 L 46 34 L 44 33 Z",
  // Scandinavia
  "M 53 22 L 57 21 L 60 24 L 60 30 L 57 32 L 54 30 L 53 26 Z",
  // Eastern Europe / W. Russia
  "M 58 27 L 64 26 L 68 28 L 68 33 L 65 36 L 60 36 L 58 33 Z",
  // Africa
  "M 46 48 L 50 47 L 54 48 L 58 50 L 61 53 L 63 58 L 64 64 L 62 70 L 59 76 L 55 80 L 52 80 L 49 76 L 46 70 L 44 62 L 44 54 Z",
  // Arabia / Middle East
  "M 60 46 L 65 46 L 68 48 L 70 52 L 68 55 L 64 55 L 61 53 L 60 50 Z",
  // Asia mainland
  "M 60 27 L 66 25 L 73 25 L 80 26 L 86 28 L 90 32 L 91 38 L 89 42 L 86 44 L 82 45 L 78 44 L 73 42 L 68 40 L 64 38 L 61 35 Z",
  // India
  "M 70 46 L 74 46 L 76 50 L 75 55 L 72 56 L 70 52 Z",
  // SE Asia / Indochina
  "M 76 50 L 80 50 L 82 53 L 82 58 L 79 60 L 77 56 Z",
  // Indonesia
  "M 78 62 L 84 62 L 86 64 L 84 66 L 80 66 L 78 64 Z",
  // Japan
  "M 87 38 L 90 37 L 91 40 L 89 43 L 87 41 Z",
  // Australia
  "M 84 72 L 90 71 L 95 73 L 96 77 L 94 81 L 89 82 L 85 80 L 83 76 Z",
];

function lookupCoords(iata: string): { x: number; y: number; label: string } | null {
  return CITY_COORDS[iata] ?? null;
}

// Round to a "nice" price near the value (10€ for cheap, 5€ for very cheap, 50€ for expensive).
function niceRound(eur: number): number {
  if (eur < 60) return Math.max(9, Math.round(eur / 5) * 5);
  if (eur < 250) return Math.round(eur / 10) * 10;
  return Math.round(eur / 10) * 10;
}

function pricesFor(deal: LandingDeal): { usual: number; deal: number } | null {
  const usual = USUAL_PRICE_EUR[deal.destination];
  if (!usual) return null;
  const dealPrice = niceRound(usual * (1 - deal.discount_pct / 100));
  return { usual, deal: dealPrice };
}

// Greedy spread selector: walk the candidate list in order, skip any pick
// whose destination is too close (in viewBox units) to one we've already
// taken, or whose card would land outside the visible area.
//
// Why: when the live API returns 5+ European destinations they all collapse
// into a single overlapping mess in the Europe area. We'd rather show 4
// visually distinct pins covering the world than 6 stacked rectangles.
const MIN_PIN_DIST = 14;

function withSpread(deals: LandingDeal[], maxCount: number): LandingDeal[] {
  const picked: LandingDeal[] = [];
  const taken: Array<{ x: number; y: number; dest: string }> = [];
  for (const d of deals) {
    if (taken.some((p) => p.dest === d.destination)) continue;
    const c = lookupCoords(d.destination);
    if (!c) continue;
    if (pricesFor(d) === null) continue;
    // Card needs ~10 units of margin on the right and 8 on the top to render
    // its label without clipping. Anything past x=92 or y<7 is rejected.
    if (c.x > 92 || c.y < 7) continue;
    if (taken.some((p) => Math.hypot(p.x - c.x, p.y - c.y) < MIN_PIN_DIST)) continue;
    picked.push(d);
    taken.push({ x: c.x, y: c.y, dest: d.destination });
    if (picked.length >= maxCount) break;
  }
  return picked;
}

export function LandingDealsMap({ initialDeals }: { initialDeals: LandingDeal[] }) {
  // Apply spread to the initial seeds too — the seed list itself is already
  // diverse, but this guarantees the invariant in one place.
  const [deals, setDeals] = useState<LandingDeal[]>(() =>
    withSpread(initialDeals, 6)
  );

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/api/landing/deals?limit=12`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const items = (data as { items?: LandingDeal[] }).items ?? [];
        // Merge: API picks first (live data wins), then seeds fill any
        // geographic gaps the spread filter leaves open. Because seeds are
        // appended, we always end up with >=4 well-distributed pins even
        // when the API returns deals all clustered in one region.
        const merged = withSpread([...items, ...initialDeals], 6);
        if (merged.length > 0) setDeals(merged);
      })
      .catch(() => {
        // Stay on seed deals — map is decorative.
      });
    return () => {
      cancelled = true;
    };
  }, [initialDeals]);

  // Final spread pass — guarantees no overlap regardless of upstream state.
  const visiblePins = withSpread(deals, 6).map((d) => ({
    ...d,
    coords: lookupCoords(d.destination)!,
    prices: pricesFor(d)!,
  }));

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0A1F3D] via-[#10284D] to-[#081830]" />

      {/* Faint latitude grid — three dashed lines for a subtle datavis hint */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      >
        {[25, 50, 75].map((y) => (
          <line
            key={y}
            x1="0"
            y1={y}
            x2="100"
            y2={y}
            stroke="#FFFEF9"
            strokeOpacity="0.05"
            strokeWidth="0.1"
            strokeDasharray="0.6 0.8"
          />
        ))}
      </svg>

      {/* Stippled continents — denser dot pattern clipped to land paths */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      >
        <defs>
          <pattern
            id="land-stipple"
            x="0"
            y="0"
            width="0.7"
            height="0.7"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="0.14" cy="0.14" r="0.18" fill="#C8DDF5" fillOpacity="0.95" />
          </pattern>
          <pattern
            id="ocean-dust"
            x="0"
            y="0"
            width="3"
            height="3"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="0.2" cy="0.2" r="0.07" fill="#FFFEF9" fillOpacity="0.12" />
          </pattern>
        </defs>

        {/* Faint ocean dust across the whole frame */}
        <rect width="100" height="100" fill="url(#ocean-dust)" />

        {/* Continent silhouettes — three stacked passes so the land reads
            clearly even on dark navy: (1) soft body fill, (2) stipple dots
            on top for the editorial datavis texture, (3) outline stroke. */}
        <g>
          {CONTINENT_PATHS.map((d, i) => (
            <path key={`fill-${i}`} d={d} fill="#5B7FA8" fillOpacity="0.32" />
          ))}
          {CONTINENT_PATHS.map((d, i) => (
            <path key={`stipple-${i}`} d={d} fill="url(#land-stipple)" />
          ))}
          {CONTINENT_PATHS.map((d, i) => (
            <path
              key={`stroke-${i}`}
              d={d}
              fill="none"
              stroke="#A8C7E8"
              strokeOpacity="0.55"
              strokeWidth="0.22"
              strokeLinejoin="round"
            />
          ))}
        </g>
      </svg>

      {/* Route arcs from Paris — drawn as quadratic curves so they feel like
          flight paths rather than rulers. Stroke length animates in. */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      >
        {visiblePins.map((p, i) => {
          const dx = p.coords.x - PARIS.x;
          const dy = p.coords.y - PARIS.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          // Arc bulges perpendicular to the line, more for longer routes.
          const bulge = Math.min(dist * 0.28, 14);
          const mx = (PARIS.x + p.coords.x) / 2;
          const my = (PARIS.y + p.coords.y) / 2 - bulge;
          const d = `M ${PARIS.x} ${PARIS.y} Q ${mx} ${my} ${p.coords.x} ${p.coords.y}`;
          return (
            <motion.path
              key={`route-${p.destination}`}
              d={d}
              fill="none"
              stroke="#FF6B47"
              strokeOpacity="0.45"
              strokeWidth="0.18"
              strokeDasharray="0.8 0.9"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ delay: 0.2 + i * 0.18, duration: 0.9, ease: "easeOut" }}
            />
          );
        })}

        {/* Paris anchor */}
        <circle cx={PARIS.x} cy={PARIS.y} r="0.85" fill="#FFFEF9" fillOpacity="0.85" />
        <circle cx={PARIS.x} cy={PARIS.y} r="1.6" fill="none" stroke="#FFFEF9" strokeOpacity="0.35" strokeWidth="0.15" />
        <text
          x={PARIS.x}
          y={PARIS.y - 1.8}
          textAnchor="middle"
          fill="#FFFEF9"
          fontSize="1.4"
          fontFamily="var(--font-dm-serif), serif"
          fillOpacity="0.7"
          letterSpacing="0.08"
        >
          PARIS
        </text>
      </svg>

      {/* "EN DIRECT" status pill, top-right of the map (out of the hero
          headline area on the left). */}
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6 z-10 flex items-center gap-2 rounded-full bg-[#FFFEF9]/8 backdrop-blur-sm border border-[#FFFEF9]/15 px-3 py-1.5">
        <span className="relative flex h-2 w-2">
          <motion.span
            className="absolute inset-0 rounded-full bg-emerald-400"
            animate={{ scale: [1, 2.5, 1], opacity: [0.7, 0, 0.7] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
          />
          <span className="relative h-2 w-2 rounded-full bg-emerald-400" />
        </span>
        <span className="text-[10px] sm:text-xs font-semibold tracking-[0.15em] text-white/85 uppercase">
          En direct
        </span>
      </div>

      {/* Pin overlay (HTML, so we can use Tailwind typography + tabular nums). */}
      <div className="absolute inset-0 pointer-events-none">
        {visiblePins.map((p, i) => (
          <DealPin key={p.destination} pin={p} delay={0.3 + i * 0.18} />
        ))}
      </div>
    </div>
  );
}

function DealPin({
  pin,
  delay,
}: {
  pin: LandingDeal & {
    coords: { x: number; y: number; label: string };
    prices: { usual: number; deal: number };
  };
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6, scale: 0.92 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay, duration: 0.5, ease: "easeOut" }}
      className="absolute -translate-x-1/2 -translate-y-full"
      style={{ left: `${pin.coords.x}%`, top: `${pin.coords.y}%` }}
    >
      <div className="relative">
        {/* Pulse halo + solid dot at the bottom of the card (the "pin tip") */}
        <motion.span
          className="absolute left-1/2 -bottom-1.5 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[#FF6B47]"
          animate={{ scale: [1, 2.6, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 2.4, repeat: Infinity, delay, ease: "easeOut" }}
        />
        <span className="absolute left-1/2 -bottom-1.5 h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[#FF6B47] ring-2 ring-[#0A1F3D]" />

        {/* Card */}
        <div className="mb-2.5 rounded-lg bg-[#FFFEF9] pl-3 pr-2.5 py-2 shadow-[0_6px_18px_rgba(0,0,0,0.35)] whitespace-nowrap border border-[#0A1F3D]/5">
          <div className="flex items-center gap-2.5">
            <div>
              <div
                className="text-[12px] sm:text-[13px] font-semibold leading-none text-[#0A1F3D]"
                style={{ fontFamily: "var(--font-dm-serif), serif" }}
              >
                {pin.coords.label}
              </div>
              <div className="mt-1 flex items-baseline gap-1.5 tabular-nums">
                <span className="text-[10px] sm:text-[11px] text-[#0A1F3D]/40 line-through leading-none">
                  {pin.prices.usual}€
                </span>
                <span className="text-[10px] sm:text-[11px] text-[#0A1F3D]/40 leading-none">→</span>
                <span className="text-[13px] sm:text-[14px] font-extrabold text-[#0A1F3D] leading-none">
                  {pin.prices.deal}€
                </span>
              </div>
            </div>
            <span className="ml-1 inline-flex items-center rounded-md bg-[#FF6B47] text-white text-[10px] sm:text-[11px] font-bold leading-none px-1.5 py-1 tabular-nums">
              −{pin.discount_pct}%
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
