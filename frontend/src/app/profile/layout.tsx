import type { Metadata } from "next";

// Private page — keep Google from indexing it. We deliberately do NOT
// block it in robots.txt: blocking prevents Googlebot from seeing this
// noindex tag, which causes the "Indexed though blocked by robots.txt"
// anti-pattern in Search Console.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function ProfileLayout({ children }: { children: React.ReactNode }) {
  return children;
}
