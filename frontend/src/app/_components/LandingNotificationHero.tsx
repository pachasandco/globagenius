"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Wordmark } from "./Wordmark";

/**
 * Hero notification mockup.
 *
 * A floating card styled like a Telegram alert pulses through the three
 * V5 deal flavours (round-trip, one-way, split-ticket combo) on a 5s loop.
 * No fake iPhone frame: showing a Telegram alert as an iOS native notif
 * would be lying about the product. The card lives in its own visual
 * world — slight shadow, frosted glass, drop-cap typography.
 *
 * Background photo is single + heavily blurred so it never competes with
 * the headline or the notification card.
 */

type NotifSample = {
  variant: "round_trip" | "one_way" | "split_ticket";
  badge: string;
  origin: string;
  destination: string;
  headline: string;
  body: string;
  meta: string;
};

const NOTIFS: NotifSample[] = [
  {
    variant: "round_trip",
    badge: "🟠 Promo flash",
    origin: "Paris",
    destination: "Tokyo",
    headline: "Paris → Tokyo · 480 € A/R",
    body: "Prix habituel ~840 € · -43%",
    meta: "12 mars – 26 mars · 14 jours · Air France",
  },
  {
    variant: "one_way",
    badge: "🔴 Erreur de prix",
    origin: "Paris",
    destination: "New York",
    headline: "Paris → New York · 220 € aller seul",
    body: "Prix habituel ~520 € · -58%",
    meta: "Départ 8 avril · French Bee · ↩ retour estimé ~280 €",
  },
  {
    variant: "split_ticket",
    badge: "💡 Combo malin",
    origin: "Paris",
    destination: "Bangkok",
    headline: "Paris ⇄ Bangkok · 540 € total",
    body: "A/R habituel ~780 € · économie 240 € (-31%)",
    meta: "2 billets : French Bee + Norse · 4-22 avril",
  },
];

const ROTATION_MS = 5500;

export function LandingNotificationHero() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % NOTIFS.length);
    }, ROTATION_MS);
    return () => clearInterval(id);
  }, []);

  const current = NOTIFS[index];

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden">
      {/* Background photo — heavily blurred so it never fights the notif */}
      <div
        className="absolute inset-0 bg-cover bg-center scale-110"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1600&q=70')",
          filter: "blur(8px) saturate(1.1) brightness(0.55)",
        }}
        aria-hidden="true"
      />
      {/* Editorial scrim */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#082B78]/85 via-[#082B78]/55 to-[#082B78]/30" />

      {/* Notification card — positioned right of HeroContent on desktop */}
      <div className="absolute inset-0 flex items-center justify-end pointer-events-none">
        <div className="hidden md:block w-[420px] max-w-[42%] mr-12 lg:mr-20">
          <NotificationCard notif={current} />
          <NotifDots count={NOTIFS.length} active={index} />
        </div>
      </div>

      {/* Mobile-only: card sits at the bottom so it doesn't fight the headline */}
      <div className="md:hidden absolute inset-x-0 bottom-6 px-4 flex flex-col items-center pointer-events-none">
        <div className="w-full max-w-sm">
          <NotificationCard notif={current} />
          <NotifDots count={NOTIFS.length} active={index} />
        </div>
      </div>
    </div>
  );
}

function NotificationCard({ notif }: { notif: NotifSample }) {
  return (
    <div className="relative">
      {/* Coral accent bar — sits just to the left of the card */}
      <motion.div
        key={`accent-${notif.variant}`}
        initial={{ opacity: 0, scaleY: 0.4 }}
        animate={{ opacity: 1, scaleY: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
        className="absolute -left-1 top-3 bottom-3 w-1 bg-[#FF6B47] rounded-full"
      />

      <AnimatePresence mode="wait">
        <motion.div
          key={notif.variant}
          initial={{ opacity: 0, y: 14, scale: 0.985 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -14, scale: 0.985 }}
          transition={{ duration: 0.55, ease: [0.32, 0.72, 0, 1] }}
          className="relative bg-white/95 backdrop-blur-xl rounded-2xl shadow-[0_24px_60px_rgba(0,0,0,0.35)] border border-white/40 px-5 py-4"
        >
          {/* Header row: app id + time */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-[#082B78] flex items-center justify-center text-white text-[11px] font-bold">
                ✈
              </div>
              <span className="text-[12px] font-semibold text-[#082B78] tracking-tight">
                <Wordmark />
              </span>
              <NotifLiveDot />
            </div>
            <span className="text-[11px] text-gray-400 font-medium tabular-nums">
              maintenant
            </span>
          </div>

          {/* Tier badge */}
          <div className="text-[11px] font-bold text-[#FF6B47] mb-1.5 tracking-wide">
            {notif.badge}
          </div>

          {/* Headline */}
          <div
            className="text-[15px] font-bold text-[#082B78] leading-snug mb-1"
            style={{ fontFamily: "var(--font-dm-serif), serif" }}
          >
            {notif.headline}
          </div>

          {/* Body line */}
          <div className="text-[12.5px] text-[#082B78]/80 leading-snug mb-2">
            {notif.body}
          </div>

          {/* Meta line */}
          <div className="text-[11px] text-gray-500 leading-snug">
            {notif.meta}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function NotifLiveDot() {
  return (
    <div className="relative h-1.5 w-1.5">
      <motion.span
        className="absolute inset-0 rounded-full bg-[#16A34A]"
        animate={{ scale: [1, 1.5, 1], opacity: [1, 0.4, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

function NotifDots({ count, active }: { count: number; active: number }) {
  return (
    <div className="flex justify-center gap-1.5 mt-4">
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          className="h-1 rounded-full transition-all duration-300"
          style={{
            width: i === active ? 18 : 6,
            background: i === active ? "#FF6B47" : "rgba(255,254,249,0.4)",
          }}
        />
      ))}
    </div>
  );
}
