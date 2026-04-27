# Landing Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the GlobeGenius landing page from 11 sections to 7, with clearer value proposition, travel hero image, deal cards with premium lock teaser, and streamlined pricing.

**Architecture:** Single-file rewrite of `src/app/page.tsx`. Keep DESTINATION_IMAGES map, FAQItem component, LandingDealCard component (modified), helper functions. Remove TelegramHeroMockup, destinations grid, airports section, Telegram preview section. Restructure the Landing component JSX.

**Tech Stack:** Next.js 16 (App Router, client component), React 19, Tailwind v4, framer-motion, Unsplash images via `<img>` tags (already configured in next.config.ts).

**Spec:** `docs/superpowers/specs/2026-04-17-landing-page-redesign.md`

**IMPORTANT:** This is a Next.js 16 project. Before writing any code, check `node_modules/next/dist/docs/` for API changes if using Next.js-specific features (Image, Link, metadata, etc.).

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/app/page.tsx` | Rewrite | Landing page — all 7 sections |
| `src/app/globals.css` | No change | Design tokens already correct |
| `src/app/layout.tsx` | No change | Fonts, metadata already correct |

This is a single-file rewrite. The page is a client component with inline sub-components — we keep that pattern.

---

### Task 1: Backup and strip unused sections

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Create a backup branch**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius
git checkout -b landing-redesign
```

- [ ] **Step 2: Remove TelegramHeroMockup component**

Delete the `TelegramHeroMockup` function (lines ~278-357) and its associated constants `FALLBACK_DEALS_HERO`, `formatShortDateFr`, `computeHeroDays`. These are no longer used in the redesign.

Delete these functions/constants from page.tsx:
- `formatShortDateFr` (L270-272)
- `computeHeroDays` (L274-276)
- `TelegramHeroMockup` (L278-357)
- `FALLBACK_DEALS_HERO` array (find it in constants section ~L359-404)

- [ ] **Step 3: Remove unused constants**

Delete from page.tsx:
- `destinations` array (6 featured destinations with images/deal counts)
- `airports` array (8 French airports)

Keep:
- `DESTINATION_IMAGES` map (used by deal cards)
- `faqs` array (will be trimmed in Task 4)

- [ ] **Step 4: Remove unused imports if any**

Check that `useRouter` from `next/navigation` is still needed (used for auth redirect). Keep `useEffect`, `useState`, `motion`, `Link`, `getFlightDeals`, `FlightDeal`.

- [ ] **Step 5: Verify build compiles**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

Expected: Build passes (possibly with warnings about unused vars — fix those).

- [ ] **Step 6: Commit**

```bash
git add src/app/page.tsx
git commit -m "refactor: strip unused landing page sections (Telegram mockup, destinations, airports)"
```

---

### Task 2: Rewrite Hero section with travel background image

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Replace the current hero JSX**

Find the hero section in the Landing component (the first major section after the navbar). Replace it with:

```tsx
{/* HERO */}
<section className="relative min-h-[480px] flex items-center overflow-hidden">
  {/* Background image */}
  <img
    src="https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=80"
    alt=""
    aria-hidden="true"
    className="absolute inset-0 w-full h-full object-cover"
  />
  <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-ink)]/90 via-[var(--color-ink)]/70 to-[var(--color-ink)]/30" />

  <div className="relative z-10 px-6 sm:px-12 py-16 max-w-2xl">
    {/* Promo badge */}
    <span className="inline-block bg-[var(--color-coral)]/20 border border-[var(--color-coral)]/40 text-[#FF9B82] px-4 py-1.5 rounded-full text-sm font-bold mb-6 backdrop-blur-sm">
      🔥 Offre printemps — Premium à 29€/an au lieu de 59€
    </span>

    <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-5xl font-bold text-white leading-tight mb-4">
      Des vols à prix cassés,{" "}
      <br />
      détectés{" "}
      <em className="not-italic text-[var(--color-coral)]">avant tout le monde</em>.
    </h1>

    <p className="text-white/75 text-lg leading-relaxed mb-8 max-w-lg">
      On surveille tous les vols au départ de la France et on vous envoie les meilleures offres sur Telegram. Jusqu&apos;à -70% sur vos billets.
    </p>

    <Link
      href="/signup"
      className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors"
    >
      Essayer gratuitement
    </Link>
    <p className="text-white/50 text-sm mt-3">Gratuit, sans carte bancaire</p>
  </div>
</section>
```

- [ ] **Step 2: Replace stats bar**

Replace the current social proof stats section with:

```tsx
{/* STATS BAR */}
<section className="flex flex-wrap justify-center gap-8 sm:gap-12 py-6 px-6 bg-white border-t border-[var(--color-sand)]">
  {[
    { value: "2 340+", label: "vols détectés" },
    { value: "-70%", label: "meilleur deal" },
    { value: "47", label: "deals en cours" },
    { value: "8", label: "aéroports de départ" },
  ].map((s) => (
    <div key={s.label} className="text-center">
      <div className="text-2xl font-extrabold text-[var(--color-ink)]">{s.value}</div>
      <div className="text-xs text-gray-400 mt-1">{s.label}</div>
    </div>
  ))}
</section>
```

- [ ] **Step 3: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: hero section with travel background image and stats bar"
```

---

### Task 3: Add deals récents section

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Add deals section after stats bar**

Insert this JSX after the stats bar section. This reuses the existing `deals` state variable and `LandingDealCard`-style rendering, but simplified:

```tsx
{/* DEALS RECENTS */}
<section className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
  <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
    Deals détectés récemment
  </h2>
  <p className="text-center text-gray-400 text-sm mb-10">
    Mis à jour en temps réel — les prix changent vite, ne tardez pas.
  </p>

  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
    {(deals.length > 0 ? deals.slice(0, 2) : []).map((deal, i) => (
      <motion.div
        key={deal.id ?? i}
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: i * 0.1, duration: 0.4 }}
        className="bg-white rounded-2xl overflow-hidden border border-[var(--color-sand)]"
      >
        <div className="h-36 bg-cover bg-center relative" style={{
          backgroundImage: `url(${destinationMeta(deal.destination_code)?.image ?? "https://images.unsplash.com/photo-1488085061387-422e29b40080?w=400&q=80"})`
        }}>
          <span className="absolute top-3 right-3 bg-[var(--color-coral)] text-white text-xs font-bold px-2.5 py-1 rounded-lg">
            -{deal.discount_pct}%
          </span>
        </div>
        <div className="p-4">
          <div className="font-bold text-[var(--color-ink)] text-sm mb-1">
            {deal.origin} → {destinationMeta(deal.destination_code)?.name ?? deal.destination_code} {destinationMeta(deal.destination_code)?.flag ?? ""}
          </div>
          <div className="text-xs text-gray-400 mb-3">A/R</div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-extrabold text-[var(--color-coral)]">{deal.price}€</span>
            {deal.usual_price && (
              <span className="text-sm text-gray-300 line-through">{deal.usual_price}€</span>
            )}
          </div>
        </div>
      </motion.div>
    ))}

    {/* Locked premium deal teaser */}
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: 0.2, duration: 0.4 }}
      className="bg-white rounded-2xl overflow-hidden border border-[var(--color-sand)]"
    >
      <div
        className="h-36 bg-cover bg-center relative brightness-75"
        style={{
          backgroundImage: `url(${deals.length > 2 ? (destinationMeta(deals[2].destination_code)?.image ?? "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=400&q=80") : "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=400&q=80"})`
        }}
      >
        <span className="absolute top-3 right-3 bg-[var(--color-ink)] text-white text-xs font-bold px-2.5 py-1 rounded-lg">
          🔒 Premium
        </span>
      </div>
      <div className="p-4">
        <div className="font-bold text-[var(--color-ink)] text-sm mb-1">
          {deals.length > 2
            ? `${deals[2].origin} → ${destinationMeta(deals[2].destination_code)?.name ?? deals[2].destination_code} ${destinationMeta(deals[2].destination_code)?.flag ?? ""}`
            : "LYS → Barcelone 🇪🇸"
          }
        </div>
        <div className="text-xs text-gray-400 mb-3">A/R</div>
        <div className="text-center">
          <div className="text-xl font-extrabold text-gray-200 blur-sm select-none mb-1">
            {deals.length > 2 ? `${deals[2].price}€` : "72€"}
          </div>
          <Link href="/signup" className="text-[var(--color-coral)] text-sm font-semibold hover:underline">
            🔓 Débloquer avec Premium →
          </Link>
        </div>
      </div>
    </motion.div>
  </div>

  <div className="text-center mt-8">
    <Link href="/signup" className="text-[var(--color-coral)] font-bold text-sm hover:underline">
      Voir tous les deals en cours →
    </Link>
  </div>
</section>
```

- [ ] **Step 2: Verify the `deals` state is still fetched**

The existing `load()` function should still call `getFlightDeals("free", 6)`. Verify it populates `deals` state. If the existing code fetches more than needed, keep it — we just `slice(0, 2)` for the free deals.

- [ ] **Step 3: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: deals récents section with 2 free deals + 1 locked premium teaser"
```

---

### Task 4: Rewrite "Comment ça marche" section

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Replace the "How it works" section**

Find the current "Comment ça marche" section and replace it with:

```tsx
{/* COMMENT CA MARCHE */}
<section className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
  <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-12">
    Comment ça marche ?
  </h2>
  <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto">
    {[
      {
        num: "1",
        title: "On surveille tous les vols au départ de la France",
        desc: "Depuis 8 aéroports français, vers le monde entier. En continu, 24h/24.",
      },
      {
        num: "2",
        title: "Vous recevez les bons plans sur Telegram",
        desc: "Prix, dates, lien direct pour réserver. Rien à faire, tout arrive automatiquement.",
      },
      {
        num: "3",
        title: "Vous réservez, vous économisez",
        desc: "Jusqu\u2019à -70% sur vos vols, parfois plus avec les erreurs de prix des compagnies.",
      },
    ].map((step, i) => (
      <motion.div
        key={step.num}
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: i * 0.1, duration: 0.4 }}
        className="text-center"
      >
        <div className="w-12 h-12 bg-[#FFF1EC] text-[var(--color-coral)] rounded-full flex items-center justify-center font-extrabold text-lg mx-auto mb-4">
          {step.num}
        </div>
        <h3 className="font-bold text-[var(--color-ink)] text-base mb-2">{step.title}</h3>
        <p className="text-sm text-gray-400 leading-relaxed">{step.desc}</p>
      </motion.div>
    ))}
  </div>
</section>
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: rewrite 'comment ça marche' with validated copy"
```

---

### Task 5: Rewrite Pricing section (côte à côte)

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Replace the pricing section**

Find the current pricing section and replace with:

```tsx
{/* PRICING */}
<section id="tarifs" className="py-16 px-6 sm:px-12 bg-[var(--color-cream)] border-t border-[var(--color-sand)]">
  <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
    Choisissez votre formule
  </h2>
  <p className="text-center text-gray-400 text-sm mb-10">
    Un vol Premium rentabilise l&apos;abonnement dès le premier voyage.
  </p>

  <div className="flex flex-col sm:flex-row gap-6 max-w-2xl mx-auto">
    {/* Free */}
    <div className="flex-1 bg-white border border-[var(--color-sand)] rounded-2xl p-6">
      <div className="font-bold text-[var(--color-ink)] text-sm mb-1">Gratuit</div>
      <div className="text-3xl font-extrabold text-[var(--color-ink)] mb-5">0€</div>
      <div className="text-sm text-gray-500 leading-loose mb-6">
        ✓ Deals jusqu&apos;à -29%<br />
        ✓ 8 aéroports de départ<br />
        ✓ Alertes Telegram<br />
        <span className="text-gray-300">✗ Deals au-delà de -30%</span><br />
        <span className="text-gray-300">✗ Alertes prioritaires</span><br />
        <span className="text-gray-300">✗ Erreurs de prix</span>
      </div>
      <Link
        href="/signup"
        className="block text-center py-3 rounded-xl font-bold text-sm border-2 border-[var(--color-ink)] text-[var(--color-ink)] hover:bg-[var(--color-ink)] hover:text-white transition-colors"
      >
        S&apos;inscrire gratuitement
      </Link>
    </div>

    {/* Premium */}
    <div className="flex-1 bg-[var(--color-ink)] rounded-2xl p-6 relative">
      <span className="absolute -top-3 right-4 bg-[var(--color-coral)] text-white text-xs font-bold px-3 py-1 rounded-full">
        POPULAIRE
      </span>
      <div className="font-bold text-[var(--color-coral)] text-sm mb-1">Premium</div>
      <div className="mb-5">
        <span className="line-through text-gray-500 text-base">59€</span>{" "}
        <span className="text-3xl font-extrabold text-white">29€</span>
        <span className="text-gray-500 text-sm">/an</span>
      </div>
      <div className="text-sm text-gray-400 leading-loose mb-6">
        ✓ <span className="text-white">Tous les deals, jusqu&apos;à -70%</span><br />
        ✓ <span className="text-white">Erreurs de prix des compagnies</span><br />
        ✓ <span className="text-white">8 aéroports de départ</span><br />
        ✓ <span className="text-white">Alertes Telegram prioritaires</span><br />
        ✓ <span className="text-white">Garantie satisfait 14 jours</span><br />
        <span className="text-[var(--color-forest)]">= 2,42€/mois</span>
      </div>
      <Link
        href="/signup"
        className="block text-center py-3 rounded-xl font-bold text-sm bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white transition-colors"
      >
        Offre printemps -41%
      </Link>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: pricing section side-by-side with premium highlight"
```

---

### Task 6: Trim FAQ to 4 questions and update JSON-LD

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Replace the `faqs` constant**

Find the `faqs` array and replace with exactly 4 items:

```tsx
const faqs = [
  {
    q: "Comment fonctionne Globe Genius ?",
    a: "On surveille en permanence les prix des vols au départ de 8 aéroports français. Dès qu'on détecte une baisse de prix significative, on vous envoie une alerte sur Telegram avec tous les détails pour réserver.",
  },
  {
    q: "Quelle est la différence entre Gratuit et Premium ?",
    a: "En Gratuit, vous recevez les deals avec des réductions jusqu'à -29%. En Premium, vous accédez à tous les deals (jusqu'à -70%+), y compris les erreurs de prix des compagnies, avec des alertes prioritaires.",
  },
  {
    q: "Comment fonctionne la garantie 14 jours ?",
    a: "Si Premium ne vous convient pas, contactez-nous dans les 14 jours suivant votre achat et on vous rembourse intégralement, sans question.",
  },
  {
    q: "Les prix incluent-ils les bagages ?",
    a: "Les prix affichés sont ceux des compagnies aériennes. Les bagages en soute sont parfois inclus selon la compagnie et le tarif. On le précise dans chaque alerte quand l'information est disponible.",
  },
];
```

- [ ] **Step 2: Rewrite FAQ section JSX**

Replace the FAQ section with:

```tsx
{/* FAQ */}
<section id="faq" className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
  <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-10">
    Questions fréquentes
  </h2>
  <div className="max-w-2xl mx-auto">
    {faqs.map((faq, i) => (
      <FAQItem key={i} q={faq.q} a={faq.a} i={i} />
    ))}
  </div>
</section>
```

- [ ] **Step 3: Update FAQ JSON-LD schema**

Find the FAQPage JSON-LD `<script>` tag and ensure it maps over the trimmed `faqs` array (should already be dynamic if it references the `faqs` const). Verify the structured data only contains 4 questions.

- [ ] **Step 4: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: trim FAQ to 4 conversion-focused questions, update JSON-LD"
```

---

### Task 7: Rewrite CTA final + Footer and clean up navbar

**Files:**
- Modify: `src/app/page.tsx`

- [ ] **Step 1: Rewrite the navbar**

Replace the current navbar with anchor links matching the new section IDs:

```tsx
{/* NAVBAR */}
<nav className="sticky top-0 z-50 flex items-center justify-between px-6 sm:px-12 py-4 bg-[var(--color-cream)]/95 backdrop-blur-sm border-b border-[var(--color-sand)]">
  <Link href="/" className="font-extrabold text-lg text-[var(--color-ink)]">
    Globe<span className="text-[var(--color-coral)]">Genius</span>
  </Link>
  <div className="flex items-center gap-6 text-sm">
    <a href="#comment-ca-marche" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">Comment ça marche</a>
    <a href="#tarifs" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">Tarifs</a>
    <a href="#faq" className="hidden sm:inline text-[var(--color-ink)] hover:text-[var(--color-coral)] transition-colors">FAQ</a>
    <Link href="/signup" className="bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-4 py-2 rounded-lg font-semibold text-sm transition-colors">
      S&apos;inscrire
    </Link>
  </div>
</nav>
```

Also add `id="comment-ca-marche"` to the "Comment ça marche" section's `<section>` tag.

- [ ] **Step 2: Rewrite CTA final**

Replace the current CTA final section:

```tsx
{/* CTA FINAL */}
<section className="py-16 px-6 sm:px-12 bg-[var(--color-ink)] text-center">
  <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-white mb-4">
    Prêt à voyager moins cher ?
  </h2>
  <p className="text-gray-400 mb-8">
    Rejoignez les voyageurs qui économisent sur chaque vol.
  </p>
  <Link
    href="/signup"
    className="inline-block bg-[var(--color-coral)] hover:bg-[var(--color-coral-hover)] text-white px-8 py-4 rounded-xl font-bold text-lg transition-colors"
  >
    Commencer gratuitement
  </Link>
</section>
```

- [ ] **Step 3: Rewrite Footer**

Replace the footer:

```tsx
{/* FOOTER */}
<footer className="py-6 px-6 sm:px-12 bg-[#050e1a] flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-gray-500">
  <span>© 2026 Globe Genius</span>
  <div className="flex gap-4">
    <Link href="/conditions" className="hover:text-gray-300 transition-colors">Conditions</Link>
    <Link href="/confidentialite" className="hover:text-gray-300 transition-colors">Confidentialité</Link>
    <Link href="/mentions-legales" className="hover:text-gray-300 transition-colors">Mentions légales</Link>
    <a href="mailto:contact@globegenius.app" className="hover:text-gray-300 transition-colors">Contact</a>
  </div>
</footer>
```

- [ ] **Step 4: Remove any remaining old sections**

Delete any JSX that's still in the Landing component that doesn't belong to the 7 sections: navbar, hero, stats, deals, how-it-works, pricing, FAQ, CTA, footer. This includes:
- Old Telegram preview section
- Old destinations grid
- Old airports grid
- Any old CTA or duplicate sections

- [ ] **Step 5: Verify build**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

- [ ] **Step 6: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: navbar with anchor links, CTA final, and footer — landing redesign complete"
```

---

### Task 8: Visual QA and final cleanup

**Files:**
- Modify: `src/app/page.tsx` (if needed)

- [ ] **Step 1: Start dev server**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run dev
```

- [ ] **Step 2: Visual QA in browser**

Open `http://localhost:3000` and verify:
- [ ] Navbar is sticky with working anchor links
- [ ] Hero shows travel image with overlay, text is readable
- [ ] Stats bar shows 4 stats in a row (wraps on mobile)
- [ ] Deals section shows 2 free deals + 1 locked premium deal
- [ ] "Comment ça marche" shows 3 steps in columns
- [ ] Pricing shows Free vs Premium side by side
- [ ] FAQ accordion works (4 questions)
- [ ] CTA final has dark background with coral button
- [ ] Footer links work
- [ ] Mobile responsive (check at 375px width)
- [ ] Auth redirect works (if gg_user_id in localStorage, redirects to /home)

- [ ] **Step 3: Fix any visual issues found**

Adjust spacing, font sizes, colors as needed based on QA.

- [ ] **Step 4: Remove LandingDealCard if no longer used**

If the old `LandingDealCard` component (L159-243) is no longer referenced anywhere in the JSX (we inlined deal cards in Task 3), delete it.

- [ ] **Step 5: Final build check**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend
npm run build
```

Expected: Clean build, no errors, no warnings.

- [ ] **Step 6: Commit and merge**

```bash
git add src/app/page.tsx
git commit -m "chore: visual QA fixes and cleanup"
git checkout main
git merge landing-redesign
```
