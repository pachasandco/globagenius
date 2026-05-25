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
