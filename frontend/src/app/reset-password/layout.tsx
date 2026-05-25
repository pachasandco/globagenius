import type { Metadata } from "next";

// Private flow — keep Google from indexing reset-password URLs (token in URL).
// Deliberately not blocked in robots.txt so Googlebot can see this noindex tag.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function ResetPasswordLayout({ children }: { children: React.ReactNode }) {
  return children;
}
