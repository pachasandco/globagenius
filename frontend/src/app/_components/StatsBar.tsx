"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";

const STATS = [
  { value: 2400, label: "voyageurs inscrits", prefix: "+", suffix: "" },
  { value: 70, label: "meilleur deal détecté", prefix: "-", suffix: "%" },
  { value: 30, label: "garantie satisfait ou remboursé", prefix: "", suffix: "j" },
  { value: 9, label: "aéroports surveillés", prefix: "", suffix: "" },
];

function StatItem({
  value,
  label,
  prefix = "",
  suffix = "",
  delay = 0,
}: {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  delay?: number;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  useEffect(() => {
    if (!isInView) return;
    const duration = 1800;
    const steps = 60;
    const stepDuration = duration / steps;
    const increment = value / steps;
    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep++;
      setCount(Math.min(Math.floor(increment * currentStep), value));
      if (currentStep >= steps) clearInterval(interval);
    }, stepDuration);
    return () => clearInterval(interval);
  }, [isInView, value]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay }}
      className="text-center"
    >
      <div className="text-2xl sm:text-3xl font-extrabold" style={{ color: "var(--color-coral)" }}>
        {prefix}{count.toLocaleString("fr-FR")}{suffix}
      </div>
      <div className="text-xs text-gray-400 mt-1 leading-tight max-w-[120px] mx-auto">{label}</div>
    </motion.div>
  );
}

export default function StatsBar() {
  return (
    <section className="flex flex-wrap justify-center gap-8 sm:gap-16 py-6 px-6 bg-white border-t border-[var(--color-sand)]">
      {STATS.map((s, i) => (
        <StatItem key={s.label} {...s} delay={i * 0.1} />
      ))}
    </section>
  );
}
