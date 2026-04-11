/**
 * Session auto-logout after 15 minutes of inactivity.
 * Call initSession() once in a top-level component.
 */

const TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes
let timer: ReturnType<typeof setTimeout> | null = null;

function resetTimer() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(logout, TIMEOUT_MS);
}

function logout() {
  localStorage.removeItem("gg_user_id");
  localStorage.removeItem("gg_email");
  localStorage.removeItem("gg_token");
  window.location.href = "/";
}

export function initSession() {
  if (typeof window === "undefined") return;

  const token = localStorage.getItem("gg_token");
  if (!token) return;

  // Reset timer on any user activity
  const events = ["mousedown", "keydown", "touchstart", "scroll"];
  events.forEach(e => window.addEventListener(e, resetTimer, { passive: true }));

  // Start the timer
  resetTimer();

  // Cleanup function
  return () => {
    if (timer) clearTimeout(timer);
    events.forEach(e => window.removeEventListener(e, resetTimer));
  };
}
