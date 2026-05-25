import { ImageResponse } from "next/og";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export const alt = "Membre fondateur OG — GlobeGenius";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Brand palette
const NAVY = "#0A1F3D";
const CORAL = "#FF6B47";

type Props = { params: Promise<{ number: string; name: string }> };

// The illustrated "baroudeur" emblem background (generated once, committed
// to /public). Satori can't resolve a public path, so we read the bytes at
// request time and inline them as a data URL. Read once at module load.
let BG_DATA_URL = "";
try {
  const bytes = readFileSync(join(process.cwd(), "public", "badge-bg.png"));
  BG_DATA_URL = `data:image/png;base64,${bytes.toString("base64")}`;
} catch {
  BG_DATA_URL = "";
}

// Dynamic Open Graph badge: an illustrated travel emblem (fixed background)
// with the OG number + first name overlaid in the central cream medallion.
export default async function BadgeImage({ params }: Props) {
  const { number, name } = await params;
  const display = decodeURIComponent(name).slice(0, 18);
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
          background: NAVY,
          position: "relative",
          fontFamily: "Georgia, serif",
        }}
      >
        {/* Illustrated emblem background, cover-cropped */}
        {BG_DATA_URL ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={BG_DATA_URL}
            alt=""
            width={1200}
            height={670}
            style={{
              position: "absolute",
              top: "-20px",
              left: 0,
              width: "1200px",
              height: "670px",
              objectFit: "cover",
            }}
          />
        ) : null}

        {/* Center overlay: OG number + name, sitting in the cream medallion.
            The emblem's clear circle is centered, so we center the column. */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            marginTop: "-16px",
          }}
        >
          <div
            style={{
              display: "flex",
              fontSize: "30px",
              fontWeight: "bold",
              color: NAVY,
              lineHeight: 1,
              letterSpacing: "1px",
            }}
          >
            {`OG #${n}`}
          </div>
          <div
            style={{
              width: "56px",
              height: "2px",
              background: CORAL,
              borderRadius: "2px",
              margin: "7px 0",
              display: "flex",
            }}
          />
          <div
            style={{
              display: "flex",
              fontSize: "24px",
              fontWeight: "bold",
              color: NAVY,
              maxWidth: "180px",
              textAlign: "center",
              lineHeight: 1,
            }}
          >
            {display}
          </div>
        </div>

        {/* Wordmark bottom-right */}
        <div
          style={{
            position: "absolute",
            bottom: "34px",
            right: "48px",
            display: "flex",
            fontSize: "24px",
            color: "rgba(255,248,240,0.9)",
            fontWeight: "bold",
          }}
        >
          Globe Genius
        </div>

        {/* Active Beta tag bottom-left */}
        <div
          style={{
            position: "absolute",
            bottom: "34px",
            left: "48px",
            display: "flex",
            fontSize: "20px",
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
