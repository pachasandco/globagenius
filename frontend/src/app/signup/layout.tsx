import type { Metadata } from "next";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
  alternates: { canonical: "https://globegenius.app/signup" },
};

export default function SignupLayout({ children }: { children: React.ReactNode }) {
  return children;
}
