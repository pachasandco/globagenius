"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * Editorial-style world map for the landing hero.
 *
 * Not a real geographic projection — three stylised continent blobs on an
 * equirectangular-ish canvas, Paris pinned at the centre. The point is
 * "look, real deals from your home airport", not a Google-Maps lookalike.
 *
 * Pin positions are coarse approximations sufficient for the editorial vibe.
 * If we ever need true geography, swap in a topojson world-110m via d3-geo.
 *
 * Fetches live deals client-side from /api/landing/deals after hydration.
 * Seeds with the parent's initialDeals so the map never appears empty.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type LandingDeal = {
  origin: string;
  destination: string;
  discount_pct: number;
};

// IATA → (x, y) in 0-100 viewBox space. Paris (CDG) anchored at (50, 38).
// Latitudes mapped logarithmically because a flat lat→y crowds Northern Europe.
const CITY_COORDS: Record<string, { x: number; y: number; label: string }> = {
  // Europe
  CDG: { x: 50, y: 38, label: "Paris" },
  ORY: { x: 50, y: 38, label: "Paris" },
  BVA: { x: 50, y: 37, label: "Paris" },
  LYS: { x: 51, y: 41, label: "Lyon" },
  MRS: { x: 51, y: 44, label: "Marseille" },
  NCE: { x: 53, y: 44, label: "Nice" },
  BOD: { x: 48, y: 43, label: "Bordeaux" },
  NTE: { x: 47, y: 41, label: "Nantes" },
  TLS: { x: 49, y: 44, label: "Toulouse" },
  LIS: { x: 43, y: 47, label: "Lisbonne" },
  OPO: { x: 43, y: 45, label: "Porto" },
  MAD: { x: 45, y: 46, label: "Madrid" },
  BCN: { x: 49, y: 45, label: "Barcelone" },
  FCO: { x: 55, y: 46, label: "Rome" },
  ATH: { x: 60, y: 47, label: "Athènes" },
  IST: { x: 63, y: 44, label: "Istanbul" },
  AMS: { x: 51, y: 34, label: "Amsterdam" },
  BER: { x: 55, y: 34, label: "Berlin" },
  LHR: { x: 47, y: 33, label: "Londres" },
  DUB: { x: 44, y: 32, label: "Dublin" },
  PRG: { x: 56, y: 36, label: "Prague" },
  VIE: { x: 57, y: 38, label: "Vienne" },
  CPH: { x: 54, y: 30, label: "Copenhague" },
  HEL: { x: 60, y: 26, label: "Helsinki" },
  ARN: { x: 56, y: 28, label: "Stockholm" },
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

const PARIS = { x: 50, y: 38 };

function lookupCoords(iata: string): { x: number; y: number; label: string } | null {
  return CITY_COORDS[iata] ?? null;
}

export function LandingDealsMap({ initialDeals }: { initialDeals: LandingDeal[] }) {
  // Start with the seed deals provided by the parent (always renders something
  // even if the API is slow/down). After hydration, replace with live data.
  const [deals, setDeals] = useState<LandingDeal[]>(initialDeals);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/api/landing/deals?limit=6`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const items = (data as { items?: LandingDeal[] }).items;
        if (items && items.length >= 3) setDeals(items);
      })
      .catch(() => {
        // Stay on seed deals — map is decorative, no need to surface a failure.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Filter out unmapped destinations + dedup by destination so we never pin
  // the same city twice if the API returns duplicates.
  const seen = new Set<string>();
  const visiblePins = deals
    .filter((d) => {
      if (seen.has(d.destination)) return false;
      seen.add(d.destination);
      return lookupCoords(d.destination) !== null;
    })
    .slice(0, 6)
    .map((d) => ({ ...d, coords: lookupCoords(d.destination)! }));

  return (
    <div className="absolute inset-0 w-full h-full">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0A1F3D] via-[#10284D] to-[#0A1F3D]" />

      {/* Subtle grain dots — hint of latitude/longitude grid without being a real graticule */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="absolute inset-0 w-full h-full opacity-[0.07]"
        aria-hidden="true"
      >
        <defs>
          <pattern id="grid-dots" x="0" y="0" width="5" height="5" patternUnits="userSpaceOnUse">
            <circle cx="0.3" cy="0.3" r="0.15" fill="#FFFEF9" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#grid-dots)" />
      </svg>

      {/* Stylised continent blobs — coarse silhouettes, not real shapes */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 w-full h-full"
        aria-hidden="true"
      >
        <g fill="#FFFEF9" fillOpacity="0.06" stroke="#FFFEF9" strokeOpacity="0.12" strokeWidth="0.15">
          {/* North America */}
          <path d="M 5 28 Q 12 24 18 28 L 24 32 Q 27 38 24 44 L 20 48 Q 15 50 12 53 L 8 50 Q 4 42 5 28 Z" />
          {/* Central America */}
          <path d="M 12 53 Q 16 56 18 60 L 21 60 L 18 62 Q 14 60 12 56 Z" />
          {/* South America */}
          <path d="M 24 60 Q 30 62 32 70 L 30 80 Q 27 86 24 84 L 22 76 Q 22 66 24 60 Z" />
          {/* Europe */}
          <path d="M 44 28 Q 50 25 56 28 L 60 32 Q 60 40 56 44 L 50 46 Q 44 44 42 38 Q 42 32 44 28 Z" />
          {/* Africa */}
          <path d="M 46 48 Q 54 48 60 52 L 64 60 Q 64 70 60 78 L 54 82 Q 48 78 46 72 L 44 60 Q 44 52 46 48 Z" />
          {/* Middle East */}
          <path d="M 60 44 Q 68 44 70 50 L 68 56 Q 64 56 60 52 Z" />
          {/* Asia (huge blob) */}
          <path d="M 60 28 Q 70 24 82 26 L 90 30 Q 92 38 90 44 L 86 48 Q 78 52 72 50 L 66 46 Q 60 38 60 28 Z" />
          {/* SE Asia / India */}
          <path d="M 70 50 Q 76 52 82 56 L 84 62 Q 80 66 76 64 L 72 58 Z" />
          {/* Oceania */}
          <path d="M 86 72 Q 94 72 96 78 L 94 82 Q 88 84 84 80 Q 84 74 86 72 Z" />
        </g>

        {/* Dotted route lines from Paris to each pin */}
        {visiblePins.map((p) => (
          <line
            key={`route-${p.destination}`}
            x1={PARIS.x}
            y1={PARIS.y}
            x2={p.coords.x}
            y2={p.coords.y}
            stroke="#FF6B47"
            strokeOpacity="0.35"
            strokeWidth="0.2"
            strokeDasharray="0.6 0.8"
          />
        ))}

        {/* Paris anchor (subtle, not a deal pin) */}
        <circle cx={PARIS.x} cy={PARIS.y} r="0.7" fill="#FFFEF9" fillOpacity="0.7" />
        <text
          x={PARIS.x}
          y={PARIS.y - 1.5}
          textAnchor="middle"
          fill="#FFFEF9"
          fontSize="1.3"
          fontFamily="var(--font-dm-serif), serif"
          fillOpacity="0.6"
        >
          Paris
        </text>
      </svg>

      {/* Pins (HTML overlay so we can use real Tailwind typography + DOM events) */}
      <div className="absolute inset-0 pointer-events-none">
        {visiblePins.map((p, i) => (
          <DealPin key={p.destination} pin={p} delay={i * 0.4} />
        ))}
      </div>
    </div>
  );
}

function DealPin({
  pin,
  delay,
}: {
  pin: LandingDeal & { coords: { x: number; y: number; label: string } };
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.5 }}
      className="absolute -translate-x-1/2 -translate-y-full"
      style={{ left: `${pin.coords.x}%`, top: `${pin.coords.y}%` }}
    >
      <div className="relative">
        {/* Pulse halo */}
        <motion.span
          className="absolute left-1/2 -bottom-1 h-2 w-2 -translate-x-1/2 rounded-full bg-[#FF6B47]"
          animate={{ scale: [1, 2.6, 1], opacity: [0.55, 0, 0.55] }}
          transition={{ duration: 2.4, repeat: Infinity, delay, ease: "easeOut" }}
        />
        {/* Solid pin dot */}
        <span className="absolute left-1/2 -bottom-1 h-2 w-2 -translate-x-1/2 rounded-full bg-[#FF6B47] ring-2 ring-[#0A1F3D]" />

        {/* Card */}
        <div className="mb-2 rounded-lg bg-[#FFFEF9] px-2.5 py-1.5 shadow-[0_4px_12px_rgba(0,0,0,0.25)] whitespace-nowrap">
          <div
            className="text-[11px] sm:text-xs font-semibold leading-tight text-[#0A1F3D]"
            style={{ fontFamily: "var(--font-dm-serif), serif" }}
          >
            {pin.coords.label}
          </div>
          <div className="text-[10px] sm:text-[11px] font-bold text-[#FF6B47] leading-tight">
            -{pin.discount_pct}%
          </div>
        </div>
      </div>
    </motion.div>
  );
}
