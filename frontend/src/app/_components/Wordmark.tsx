import Image from "next/image";
import type { CSSProperties } from "react";

type WordmarkVariant = "default" | "inverse" | "monochrome";
type WordmarkSize = "sm" | "md" | "lg";

type Props = {
  className?: string;
  variant?: WordmarkVariant;
  size?: WordmarkSize;
  priority?: boolean;
};

const SIZE_CLASSES: Record<WordmarkSize, string> = {
  sm: "h-8",
  md: "h-12",
  lg: "h-16",
};

const MASK_STYLE: CSSProperties = {
  aspectRatio: "600 / 295",
  WebkitMaskImage: "url('/logo2.png')",
  maskImage: "url('/logo2.png')",
  WebkitMaskPosition: "center",
  maskPosition: "center",
  WebkitMaskRepeat: "no-repeat",
  maskRepeat: "no-repeat",
  WebkitMaskSize: "contain",
  maskSize: "contain",
};

/**
 * GlobeGenius wordmark variants:
 * - default: original coloured logo, for light backgrounds;
 * - inverse: white monochrome silhouette, for dark backgrounds;
 * - monochrome: night-blue silhouette, for neutral/print contexts.
 */
export function Wordmark({
  className = "",
  variant = "default",
  size = "lg",
  priority = false,
}: Props) {
  const sizing = SIZE_CLASSES[size];

  if (variant !== "default") {
    return (
      <span
        role="img"
        aria-label="GlobeGenius"
        data-wordmark-variant={variant}
        className={`inline-block shrink-0 align-middle ${sizing} ${className}`}
        style={{
          ...MASK_STYLE,
          backgroundColor: variant === "inverse" ? "#FFFFFF" : "#0B2A3F",
        }}
      />
    );
  }

  return (
    <Image
      src="/logo2.png"
      alt="GlobeGenius"
      width={600}
      height={295}
      priority={priority}
      draggable={false}
      data-wordmark-variant="default"
      className={`inline-block w-auto shrink-0 align-middle ${sizing} ${className}`}
    />
  );
}
