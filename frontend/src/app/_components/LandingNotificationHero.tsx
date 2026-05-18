"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Wordmark } from "./Wordmark";

/**
 * Hero notification mockup — perspective stack.
 *
 * Three real-deal Telegram cards stacked in 3D. The frontmost is the
 * "incoming" alert; behind it sit the previous two, slightly tilted
 * and faded. Every ROTATION_MS, the front card recedes to the back
 * and the next one pops forward. The point: signal a rhythm of
 * alerts, not a single flashing card.
 */

type DealTier = "exceptional" | "flash";

type NotifSample = {
  tier: DealTier;
  badge: string;
  route: string;
  price: number;
  baseline: number;
  discountPct: number;
  dates: string;
  duration: string;
  airline: string;
  ago: string;
};

// Real deals we have shipped in the last 14 days.
const NOTIFS: NotifSample[] = [
  {
    tier: "exceptional",
    badge: "Deal exceptionnel",
    route: "Paris → Barcelone",
    price: 40,
    baseline: 165,
    discountPct: 76,
    dates: "8 → 12 juin",
    duration: "4 jours",
    airline: "Vueling",
    ago: "maintenant",
  },
  {
    tier: "flash",
    badge: "Promo flash",
    route: "Paris → Marrakech",
    price: 74,
    baseline: 155,
    discountPct: 52,
    dates: "22 → 26 mai",
    duration: "4 jours",
    airline: "Transavia",
    ago: "il y a 12 min",
  },
  {
    tier: "flash",
    badge: "Promo flash",
    route: "Paris → Lisbonne",
    price: 89,
    baseline: 210,
    discountPct: 58,
    dates: "15 → 22 juin",
    duration: "7 jours",
    airline: "TAP Portugal",
    ago: "il y a 28 min",
  },
];

const ROTATION_MS = 5200;

export function LandingNotificationHero() {
  const [front, setFront] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setFront((i) => (i + 1) % NOTIFS.length);
    }, ROTATION_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden">
      {/* Background photo — heavily blurred so it never fights the notif */}
      <div
        className="absolute inset-0 bg-cover bg-center scale-110"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1600&q=70')",
          filter: "blur(10px) saturate(1.15) brightness(0.5)",
        }}
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[#082B78]/85 via-[#082B78]/55 to-[#082B78]/30" />

      {/* Stack — positioned right of HeroContent on desktop */}
      <div className="absolute inset-0 flex items-center justify-end pointer-events-none">
        <div className="hidden md:block w-[440px] max-w-[44%] mr-12 lg:mr-20">
          <NotifStack front={front} />
        </div>
      </div>

      {/* Mobile-only: stack sits at the bottom */}
      <div className="md:hidden absolute inset-x-0 bottom-6 px-4 flex flex-col items-center pointer-events-none">
        <div className="w-full max-w-sm">
          <NotifStack front={front} compact />
        </div>
      </div>
    </div>
  );
}

/**
 * The depth math: each card has a slot — 0 = front, 1 = mid, 2 = back.
 * When `front` advances, every card recomputes its slot via modular
 * distance. We animate translate/scale/opacity/tilt off the slot so
 * the swap looks like a deck of cards being dealt.
 */
function NotifStack({ front, compact = false }: { front: number; compact?: boolean }) {
  const slotOf = (i: number) => (i - front + NOTIFS.length) % NOTIFS.length;

  // Slot 0 = front, slot 1 = mid, slot 2 = back
  const config: Record<number, { y: number; scale: number; opacity: number; rotate: number; blur: number; zIndex: number; shadow: string }> = {
    0: { y: 0, scale: 1, opacity: 1, rotate: 0, blur: 0, zIndex: 30, shadow: "0 28px 64px -12px rgba(0,0,0,0.5), 0 8px 24px -8px rgba(0,0,0,0.35)" },
    1: { y: -28, scale: 0.94, opacity: 0.78, rotate: -1.4, blur: 1.2, zIndex: 20, shadow: "0 14px 32px -10px rgba(0,0,0,0.35)" },
    2: { y: -54, scale: 0.88, opacity: 0.45, rotate: 1.8, blur: 2.5, zIndex: 10, shadow: "0 8px 18px -6px rgba(0,0,0,0.25)" },
  };

  return (
    <div
      className="relative"
      style={{
        // Reserve enough vertical room so the receded cards aren't clipped.
        // Back card translates up by 54px above the front card's top edge,
        // so the container is sized for: card height + back-card offset.
        height: compact ? 256 : 272,
        perspective: 1400,
      }}
    >
      {NOTIFS.map((notif, i) => {
        const slot = slotOf(i);
        const c = config[slot];
        return (
          <motion.div
            key={notif.route}
            initial={false}
            animate={{
              y: c.y,
              scale: c.scale,
              opacity: c.opacity,
              rotate: c.rotate,
              filter: `blur(${c.blur}px)`,
            }}
            transition={{
              duration: 0.7,
              ease: [0.32, 0.72, 0, 1],
            }}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 0,
              height: compact ? 196 : 212,
              zIndex: c.zIndex,
              boxShadow: c.shadow,
              transformOrigin: "50% 100%",
              borderRadius: 18,
            }}
          >
            <NotificationCard notif={notif} isFront={slot === 0} compact={compact} />
          </motion.div>
        );
      })}

      {/* Stack indicator — quiet dots beneath, slot-aware */}
      <div
        className="absolute left-0 right-0 flex justify-center gap-1.5"
        style={{ bottom: -22 }}
      >
        {NOTIFS.map((_, i) => {
          const slot = slotOf(i);
          return (
            <span
              key={i}
              className="h-1 rounded-full transition-all duration-500"
              style={{
                width: slot === 0 ? 22 : 6,
                background: slot === 0 ? "#FF6B47" : "rgba(255,254,249,0.35)",
              }}
            />
          );
        })}
      </div>
    </div>
  );
}

function NotificationCard({
  notif,
  isFront,
  compact,
}: {
  notif: NotifSample;
  isFront: boolean;
  compact: boolean;
}) {
  const tierColor = notif.tier === "exceptional" ? "#16A34A" : "#F59E0B";

  return (
    <div
      className="relative w-full h-full bg-white rounded-[18px] border border-white/60 overflow-hidden"
      style={{
        // Subtle paper grain — faint, only adds texture, never noise
        backgroundImage:
          "radial-gradient(rgba(8,43,120,0.025) 1px, transparent 1px)",
        backgroundSize: "3px 3px",
      }}
    >
      {/* Left coral spine — denotes Globe Genius brand alert */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-[#FF6B47]" />

      <div className={compact ? "pl-4 pr-4 py-3.5" : "pl-5 pr-5 py-4"}>
        {/* Header row */}
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-semibold tracking-tight">
              <Wordmark />
            </span>
            {isFront && <LiveDot color={tierColor} />}
          </div>
          <span className="text-[10.5px] text-gray-400 font-medium tabular-nums">
            {notif.ago}
          </span>
        </div>

        {/* Tier badge */}
        <div
          className="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-[0.06em] mb-2.5"
          style={{ color: tierColor }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: tierColor }}
          />
          {notif.badge}
        </div>

        {/* Route */}
        <div
          className="text-[15.5px] font-bold text-[#082B78] leading-snug mb-2"
          style={{ fontFamily: "var(--font-dm-serif), serif" }}
        >
          {notif.route}
        </div>

        {/* Price + discount row */}
        <div className="flex items-baseline gap-3 mb-2">
          <div
            className="text-[28px] font-bold text-[#082B78] leading-none tabular-nums"
            style={{ fontFamily: "var(--font-dm-serif), serif" }}
          >
            {notif.price}€
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[11px] text-gray-400 line-through tabular-nums">
              {notif.baseline}€
            </span>
            <span
              className="text-[11px] font-bold tabular-nums"
              style={{ color: tierColor }}
            >
              −{notif.discountPct}%
            </span>
          </div>
        </div>

        {/* Meta line */}
        <div className="flex items-center gap-1.5 text-[11px] text-gray-500 leading-snug flex-wrap">
          <span className="whitespace-nowrap">{notif.dates}</span>
          <span className="text-gray-300">·</span>
          <span className="whitespace-nowrap">{notif.duration}</span>
          <span className="text-gray-300">·</span>
          <span className="font-medium whitespace-nowrap">{notif.airline}</span>
        </div>
      </div>
    </div>
  );
}

function LiveDot({ color }: { color: string }) {
  return (
    <span className="relative inline-flex h-1.5 w-1.5">
      <motion.span
        className="absolute inset-0 rounded-full"
        style={{ backgroundColor: color }}
        animate={{ scale: [1, 1.8, 1], opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <span
        className="absolute inset-0 rounded-full"
        style={{ backgroundColor: color }}
      />
    </span>
  );
}
