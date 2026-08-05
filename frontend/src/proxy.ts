import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED = ["/home", "/profile", "/onboarding", "/deals"];

// Fallback corrigé (audit 2026-07-31) : b887 est un ancien domaine Railway
// mort (404) — un build sans NEXT_PUBLIC_API_URL cassait silencieusement
// le proxy. Le domaine backend actif est -1380.
const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://globagenius-production-1380.up.railway.app").trim();

function buildCsp(): string {
  return [
    "default-src 'self'",
    `connect-src 'self' ${API_URL} https://api.stripe.com`,
    "script-src 'self' 'unsafe-inline' https://js.stripe.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https://images.unsplash.com",
    "frame-src https://js.stripe.com https://hooks.stripe.com",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED.some(
    (path) => pathname === path || pathname.startsWith(path + "/")
  );

  if (isProtected) {
    const session = request.cookies.get("gg_session");
    if (!session) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  const response = NextResponse.next();
  response.headers.set("Content-Security-Policy", buildCsp());
  return response;
}

export const config = {
  matcher: ["/home/:path*", "/profile/:path*", "/onboarding/:path*", "/deals/:path*"],
};
