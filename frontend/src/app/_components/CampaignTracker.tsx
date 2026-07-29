"use client";

import { useEffect } from "react";

const ATTRIBUTION_KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
] as const;

export function CampaignTracker() {
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const attribution: Record<string, string> = {};

      for (const key of ATTRIBUTION_KEYS) {
        const value = params.get(key);
        if (value) attribution[key] = value.slice(0, 200);
      }

      if (Object.keys(attribution).length > 0) {
        localStorage.setItem(
          "gg_attribution",
          JSON.stringify({
            ...attribution,
            landing_path: window.location.pathname,
            captured_at: new Date().toISOString(),
          }),
        );
      }
    } catch {
      // Attribution must never block navigation or signup.
    }
  }, []);

  return null;
}
