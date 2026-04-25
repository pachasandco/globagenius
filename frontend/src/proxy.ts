import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED = ["/home", "/profile", "/onboarding", "/dashboard"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED.some(
    (path) => pathname === path || pathname.startsWith(path + "/")
  );

  if (!isProtected) return NextResponse.next();

  // JWT is stored in localStorage — not readable server-side.
  // We use a lightweight session cookie set at login as the gate.
  const session = request.cookies.get("gg_session");
  if (!session) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/home/:path*", "/profile/:path*", "/onboarding/:path*", "/dashboard/:path*"],
};
