import { ImageResponse } from "next/og";

export const alt = "Membre fondateur OG — GlobeGenius";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Brand palette
const NAVY = "#0A1F3D";
const NAVY_DEEP = "#06152B";
const CORAL = "#FF6B47";
const GOLD = "#E8C37E";
const CREAM = "#FFF8F0";

type Props = { params: Promise<{ number: string; name: string }> };

// Dynamic Open Graph badge: a circular "founder seal" rendered server-side
// as PNG via next/og (Satori). The name + OG number come from the URL
// segments. Satori supports a flexbox subset, borderRadius and layered
// boxes — the seal is built from concentric circles, not SVG textPath.
export default async function BadgeImage({ params }: Props) {
  const { number } = await params;
  const n = (decodeURIComponent(number).replace(/[^0-9]/g, "") || "1").slice(0, 4);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY_DEEP} 100%)`,
          fontFamily: "Georgia, serif",
          position: "relative",
        }}
      >
        {/* Soft coral glow behind the seal */}
        <div
          style={{
            position: "absolute",
            width: "560px",
            height: "560px",
            borderRadius: "50%",
            background: CORAL,
            opacity: 0.16,
            display: "flex",
          }}
        />

        {/* ── The seal ── */}
        <div
          style={{
            width: "470px",
            height: "470px",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: NAVY,
            border: `3px solid ${GOLD}`,
            boxShadow: `0 0 0 16px rgba(232,195,126,0.18)`,
            position: "relative",
          }}
        >
          {/* Inner ring (the medallion core) */}
          <div
            style={{
              width: "330px",
              height: "330px",
              borderRadius: "50%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              border: `2px solid rgba(232,195,126,0.45)`,
              background:
                "radial-gradient(circle at 50% 35%, rgba(255,107,71,0.18) 0%, rgba(10,31,61,0) 60%)",
            }}
          >
            {/* Globe mark */}
            <div
              style={{
                width: "86px",
                height: "86px",
                borderRadius: "50%",
                background: CORAL,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "48px",
                marginBottom: "6px",
                boxShadow: "0 8px 24px rgba(255,107,71,0.4)",
              }}
            >
              🌍
            </div>

            {/* OG monogram */}
            <div
              style={{
                fontSize: "76px",
                fontWeight: "bold",
                color: CREAM,
                lineHeight: 1,
                letterSpacing: "4px",
              }}
            >
              OG
            </div>

            {/* The number */}
            <div
              style={{
                display: "flex",
                fontSize: "48px",
                fontWeight: "bold",
                color: GOLD,
                marginTop: "4px",
              }}
            >
              #{n}
            </div>
          </div>
        </div>

        {/* Wordmark bottom-right */}
        <div
          style={{
            position: "absolute",
            bottom: "40px",
            right: "56px",
            display: "flex",
            alignItems: "center",
            fontSize: "26px",
            color: "rgba(255,255,255,0.85)",
            fontWeight: "bold",
          }}
        >
          Globe Genius
        </div>

        {/* Active Beta tag bottom-left */}
        <div
          style={{
            position: "absolute",
            bottom: "40px",
            left: "56px",
            display: "flex",
            fontSize: "22px",
            color: CORAL,
            fontWeight: "bold",
            letterSpacing: "2px",
            textTransform: "uppercase",
          }}
        >
          Active Beta
        </div>
      </div>
    ),
    { ...size },
  );
}
