import type { NextConfig } from "next";
import { IATA_TO_SLUG } from "./src/lib/destinations";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async redirects() {
    // 301 redirects from legacy IATA URLs (/destination/dub) to the
    // new SEO-friendly slug URLs (/destination/dublin). Generated from
    // the IATA_TO_SLUG mapping so we have a single source of truth.
    const iataRedirects = Object.entries(IATA_TO_SLUG).map(([iata, slug]) => ({
      source: `/destination/${iata}`,
      destination: `/destination/${slug}`,
      permanent: true,
    }));

    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.globegenius.app" }],
        destination: "https://globegenius.app/:path*",
        permanent: true,
      },
      {
        source: "/premium",
        destination: "/signup",
        permanent: true,
      },
      {
        // Beta reframing 2026-05-17: the public pricing block became
        // the founder programme. Old "/tarifs" links (anchor or
        // historical indexed URLs) land on /beta instead.
        source: "/tarifs",
        destination: "/beta",
        permanent: true,
      },
      ...iataRedirects,
    ];
  },
  async rewrites() {
    // 2026-07-06: the Telegram alert click-tracking links point at
    // https://globegenius.app/r/{token}. That path is a BACKEND route
    // (@router.get("/r/{token}") — records the click, then 302s to the
    // Aviasales deal). The frontend has no /r/ route, so before this
    // rewrite every click landed on a blank Next.js 200 page: the click
    // was never recorded (CTR read a false 0%) AND the user never
    // reached the deal. Proxy /r/* straight through to the backend.
    // (This regressed silently when the domain was re-pointed at
    // Cloudflare → frontend after the 2026-07 domain recovery.)
    const apiUrl = (
      process.env.NEXT_PUBLIC_API_URL ||
      "https://globagenius-production-1380.up.railway.app"
    ).replace(/\/$/, "");
    return [
      {
        source: "/r/:token",
        destination: `${apiUrl}/r/:token`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
