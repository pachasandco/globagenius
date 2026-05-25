import { ImageResponse } from "next/og";

export const alt = "Membre fondateur Active Beta — GlobeGenius";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Dynamic Open Graph / shareable badge image for a contributor.
// Rendered server-side as a PNG via next/og. The name comes from the
// URL segment (already a display name the founder chose / approved),
// decoded and length-capped so a long value can't break the layout.
export default async function BadgeImage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const display = decodeURIComponent(name).slice(0, 24);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0A1F3D",
          fontFamily: "Georgia, serif",
          position: "relative",
        }}
      >
        {/* Coral accent bar at top */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "10px",
            background: "#FF6B47",
          }}
        />

        {/* Brand */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            marginBottom: "40px",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              background: "#FF6B47",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "30px",
            }}
          >
            🌍
          </div>
          <div style={{ fontSize: "38px", fontWeight: "bold", color: "#FFFFFF" }}>
            Globe Genius
          </div>
        </div>

        {/* Badge medal */}
        <div style={{ fontSize: "96px", marginBottom: "8px" }}>🏅</div>

        {/* Name */}
        <div
          style={{
            fontSize: "72px",
            fontWeight: "bold",
            color: "#FFFFFF",
            marginBottom: "8px",
            textAlign: "center",
            padding: "0 40px",
          }}
        >
          {display}
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: "30px",
            color: "#FF6B47",
            fontWeight: "bold",
            letterSpacing: "2px",
            textTransform: "uppercase",
          }}
        >
          Membre fondateur · Active Beta
        </div>

        {/* Subline */}
        <div
          style={{
            fontSize: "22px",
            color: "#9CB0CC",
            marginTop: "28px",
            fontFamily: "Helvetica, Arial, sans-serif",
          }}
        >
          A façonné GlobeGenius dès les premiers jours
        </div>
      </div>
    ),
    { ...size },
  );
}
