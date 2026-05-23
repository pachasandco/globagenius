"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { Wordmark } from "./Wordmark";
import { getRecentDeals, type RecentDeal } from "@/lib/api";

/**
 * Hero notification mockup — perspective stack.
 *
 * Three real-deal Telegram cards stacked in 3D. The frontmost is the
 * "incoming" alert; behind it sit the previous two, slightly tilted
 * and faded. Every ROTATION_MS, the front card recedes to the back
 * and the next one pops forward. The point: signal a rhythm of
 * alerts, not a single flashing card.
 *
 * The 3 cards are picked at random (≥1 province departure guaranteed)
 * from a live pool fetched at /api/stats/recent-deals, so a visitor
 * rarely sees the same deals twice. If the API is unreachable we fall
 * back to FALLBACK_NOTIFS so the hero is never empty.
 */

type DealTier = "exceptional" | "flash";

type NotifSample = {
  tier: DealTier;
  badge: string;
  route: string;
  price: number;
  baseline: number;
  discountPct: number;
  meta: string;
  ago: string;
};

// Shown only when /api/stats/recent-deals returns nothing (network
// error or empty pool). Real deals we have shipped in the last weeks.
const FALLBACK_NOTIFS: NotifSample[] = [
  { tier: "exceptional", badge: "Deal exceptionnel", route: "Paris → Barcelone", price: 40, baseline: 165, discountPct: 76, meta: "A/R · vérifié", ago: "récemment" },
  { tier: "flash", badge: "Promo flash", route: "Toulouse → Lisbonne", price: 64, baseline: 178, discountPct: 64, meta: "A/R · vérifié", ago: "récemment" },
  { tier: "flash", badge: "Promo flash", route: "Paris → Marrakech", price: 74, baseline: 155, discountPct: 52, meta: "A/R · vérifié", ago: "récemment" },
];

const ROTATION_MS = 5200;

// Map an API deal to the card view-model. Tier is derived from the
// discount: ≥70% reads as "exceptionnel", below as "promo flash".
function dealToNotif(d: RecentDeal): NotifSample {
  const exceptional = d.discount_pct >= 70;
  return {
    tier: exceptional ? "exceptional" : "flash",
    badge: exceptional ? "Deal exceptionnel" : "Promo flash",
    route: `${d.origin_city} → ${d.dest_city}`,
    price: d.price,
    baseline: d.baseline,
    discountPct: d.discount_pct,
    meta: "A/R · vérifié",
    ago: "récemment",
  };
}

// Pick 3 deals from the pool, guaranteeing at least one province
// departure when the pool contains one. Shuffles so each load differs.
function pickThree(pool: RecentDeal[]): RecentDeal[] {
  if (pool.length <= 3) return pool;
  const shuffled = [...pool].sort(() => Math.random() - 0.5);
  const province = shuffled.find((d) => d.is_province);
  const chosen: RecentDeal[] = [];
  if (province) chosen.push(province);
  for (const d of shuffled) {
    if (chosen.length >= 3) break;
    if (!chosen.includes(d)) chosen.push(d);
  }
  return chosen;
}

// Shared hook: fetch the pool once, pick 3 (random, ≥1 province), map
// to card view-models. Falls back to FALLBACK_NOTIFS on empty/error.
function useHeroNotifs(): NotifSample[] {
  const [pool, setPool] = useState<RecentDeal[] | null>(null);
  useEffect(() => {
    let alive = true;
    getRecentDeals().then((deals) => {
      if (alive) setPool(deals);
    });
    return () => {
      alive = false;
    };
  }, []);
  return useMemo(() => {
    if (!pool || pool.length === 0) return FALLBACK_NOTIFS;
    const picked = pickThree(pool).map(dealToNotif);
    return picked.length >= 1 ? picked : FALLBACK_NOTIFS;
  }, [pool]);
}

export function LandingNotificationHero() {
  const notifs = useHeroNotifs();
  const [front, setFront] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setFront((i) => (i + 1) % notifs.length);
    }, ROTATION_MS);
    return () => clearInterval(id);
  }, [notifs.length]);

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

      {/* Desktop stack — positioned right of HeroContent. Hidden on mobile
          to avoid overlapping the headline + CTA; mobile uses the
          in-flow <LandingNotificationStackMobile> placed below the hero. */}
      <div className="absolute inset-0 hidden md:flex items-center justify-end pointer-events-none">
        <div className="block w-[440px] max-w-[44%] mr-12 lg:mr-20">
          <NotifStack notifs={notifs} front={front} />
        </div>
      </div>
    </div>
  );
}

/**
 * Mobile-only in-flow version. Rendered BELOW <HeroContent> on small
 * screens so the stack never overlaps the headline or CTA. Wraps its
 * own dark backdrop so it visually reads as part of the hero.
 */
export function LandingNotificationStackMobile() {
  const notifs = useHeroNotifs();
  const [front, setFront] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setFront((i) => (i + 1) % notifs.length);
    }, ROTATION_MS);
    return () => clearInterval(id);
  }, [notifs.length]);

  return (
    <div className="md:hidden relative w-full bg-[#082B78] px-6 pt-10 pb-12">
      <div
        className="absolute inset-0 bg-cover bg-center opacity-40"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1200&q=60')",
          filter: "blur(14px) brightness(0.5) saturate(1.1)",
        }}
        aria-hidden="true"
      />
      <div className="relative max-w-sm mx-auto">
        <NotifStack notifs={notifs} front={front} compact />
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
function NotifStack({ notifs, front, compact = false }: { notifs: NotifSample[]; front: number; compact?: boolean }) {
  const slotOf = (i: number) => (i - front + notifs.length) % notifs.length;

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
      {notifs.map((notif, i) => {
        const slot = slotOf(i);
        const c = config[slot];
        return (
          <motion.div
            key={`${notif.route}-${i}`}
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
        {notifs.map((_, i) => {
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
          <span className="whitespace-nowrap">{notif.meta}</span>
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
