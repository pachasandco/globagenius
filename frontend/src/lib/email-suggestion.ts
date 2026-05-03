/**
 * Detect common typos in an email address and suggest a correction.
 *
 * Two checks:
 * - Common-domain typos: "gmial.com" → "gmail.com", "yhaoo.fr" → "yahoo.fr"
 * - Common-TLD typos: "gmail.cim" → "gmail.com", "yahoo.con" → "yahoo.com"
 *
 * Returns the suggested correction if anything looked off, or null if the
 * address looks fine. Pure string logic — no network call. The backend
 * does the authoritative DNS check at signup time.
 */

const COMMON_DOMAINS = [
  "gmail.com",
  "yahoo.com", "yahoo.fr",
  "hotmail.com", "hotmail.fr",
  "outlook.com", "outlook.fr",
  "live.fr", "live.com",
  "orange.fr", "wanadoo.fr",
  "free.fr",
  "sfr.fr",
  "laposte.net",
  "icloud.com", "me.com",
  "protonmail.com", "proton.me",
];

// TLD typos → canonical TLD. Keys are bare TLDs (no leading dot).
const TLD_FIXES: Record<string, string> = {
  cim: "com", con: "com", cmo: "com", cpm: "com", coom: "com", comm: "com", om: "com",
  nett: "net", ne: "net", ent: "net",
  ogr: "org", rg: "org", orgg: "org",
  fra: "fr", frr: "fr",
};

/** Tiny Levenshtein for short strings. Good enough for domains < 30 chars. */
function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  const dp = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) dp[i][0] = i;
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost,
      );
    }
  }
  return dp[a.length][b.length];
}

export function suggestEmailCorrection(email: string): string | null {
  const trimmed = email.trim().toLowerCase();
  const at = trimmed.lastIndexOf("@");
  if (at < 1 || at === trimmed.length - 1) return null;

  const local = trimmed.slice(0, at);
  const domain = trimmed.slice(at + 1);

  // Already a known-good domain → no suggestion.
  if (COMMON_DOMAINS.includes(domain)) return null;

  // Pass 1 — TLD typo on a known domain stem.
  const lastDot = domain.lastIndexOf(".");
  if (lastDot > 0) {
    const stem = domain.slice(0, lastDot);
    const tld = domain.slice(lastDot + 1);
    const fixedTld = TLD_FIXES[tld];
    if (fixedTld) {
      return `${local}@${stem}.${fixedTld}`;
    }
  }

  // Pass 2 — fuzzy match against common domains (Levenshtein ≤ 2).
  let bestDomain: string | null = null;
  let bestDistance = 3;
  for (const candidate of COMMON_DOMAINS) {
    const d = levenshtein(domain, candidate);
    if (d > 0 && d < bestDistance) {
      bestDistance = d;
      bestDomain = candidate;
    }
  }
  if (bestDomain) {
    return `${local}@${bestDomain}`;
  }

  return null;
}
