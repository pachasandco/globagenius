import { ImageResponse } from "next/og";

export const alt = "Globe Genius — Vols à Prix Cassés";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
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
          background: "#FFF8F0",
          fontFamily: "Georgia, serif",
        }}
      >
        {/* Logo area */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div
            style={{
              width: "80px",
              height: "80px",
              borderRadius: "50%",
              background: "#FF6B47",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "40px",
            }}
          >
            🌍
          </div>
          <div
            style={{
              fontSize: "56px",
              fontWeight: "bold",
              color: "#0A1F3D",
            }}
          >
            Globe Genius
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: "36px",
            color: "#0A1F3D",
            marginBottom: "24px",
          }}
        >
          Vols à prix cassés
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: "22px",
            color: "#0A1F3D",
            opacity: 0.5,
            marginBottom: "40px",
          }}
        >
          Alertes Telegram temps réel · 8 aéroports français
        </div>

        {/* Price examples */}
        <div style={{ display: "flex", gap: "24px" }}>
          {[
            { city: "Lisbonne", price: "89€" },
            { city: "Marrakech", price: "98€" },
            { city: "Athènes", price: "156€" },
          ].map((deal) => (
            <div
              key={deal.city}
              style={{
                background: "#FFFEF9",
                border: "2px solid #F0E6D8",
                borderRadius: "16px",
                padding: "16px 28px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
              }}
            >
              <div
                style={{ fontSize: "18px", color: "#0A1F3D", opacity: 0.6 }}
              >
                {deal.city}
              </div>
              <div
                style={{
                  fontSize: "32px",
                  fontWeight: "bold",
                  color: "#FF6B47",
                }}
              >
                {deal.price}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: "absolute",
            bottom: "0",
            width: "100%",
            height: "6px",
            background: "#FF6B47",
          }}
        />
      </div>
    ),
    { ...size }
  );
}
