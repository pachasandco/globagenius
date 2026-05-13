import Image from "next/image";

type Props = {
  className?: string;
};

// Wordmark = the full GlobeGenius logo (icon + text baked into one PNG).
// Source ratio is 600x408 ≈ 1.47. We render at a fixed pixel height so the
// brand stays the same size everywhere it appears (nav, auth pages, footers)
// regardless of the surrounding font-size. Tweak h-* below to resize globally.
export function Wordmark({ className = "" }: Props) {
  return (
    <Image
      src="/logo2.png"
      alt="GlobeGenius"
      width={600}
      height={295}
      priority
      className={`inline-block align-middle h-16 w-auto ${className}`}
    />
  );
}
