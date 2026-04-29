# Globegenius — Roadmap

Single source of truth for what's planned, what's deferred, and what's been
killed. **Append-only** for the "Done" section, **mutable** for the rest.

Last updated: 2026-04-29 (V5 / V5+ P1 shipped on branch `v5`).

---

## Conventions

- **P0** = hygiene / dette technique critique. Ship within the week.
- **P1** = user-facing value, ship in current sprint.
- **P2** = next 2-4 weeks, may need data first.
- **P3** = later quarter, only if volume justifies the cost.
- **🔒** = blocked on a dependency listed in the item.
- **📊** = needs data we don't have yet to decide.
- **❌** = explicitly killed; reasoning recorded.

When an item ships, **move it to "Done"** with the commit SHA. Never delete.

---

## ✅ Done

### V5 — One-way & 2x one-way (April 2026)

- `e1b20e3` — One-way preference + scraping + Telegram format + dispatch filter
- `327bee9` — Split-ticket combo detector (matcher pure + DB scan + dispatch)
- `ce77fab` — Fix `/home` premium banner flash for premium users
- `9474373` — Split-ticket combos as opt-in sub-option of "Aller-retour"
- `17fcd15` — Clean `/home` navbar + scope `/api/packages` to user's airports
- `cd4da7a` — Scorer cleanup (drop hotel rating, 60/25/15) + threshold
  centralisation in `app/thresholds.py` + migration 028
  (`qualification_method` column)
- `afc3856` — One-way qualifier + Telegram dispatch (option C, pre-baseline)
  + UTMs on one-way / split-ticket booking links

**Migrations to apply on Supabase prod (in order):**
025_flight_trip_types · 026_oneway_flights · 027_include_split_tickets · 028_qualification_method

---

## 🔥 Now (P0) — Open items

### UI/UX out of sync with V5/P0/P1 backend changes

The pipeline has evolved (one-way deals, split-ticket combos, scorer
60/25/15, navbar cleanup, airport-scoped homepage) but parts of the UI
still tell the pre-V5 story. Audit done 2026-04-29.

**External / marketing layer (highest leak):**
- `app/layout.tsx` lines 21, 27, 39, 57, 103, 124 — six occurrences
  of "vols aller-retour" in metadata, og:image alt, schema.org. Google
  + social shares advertise an outdated product promise.
- `app/page.tsx` FAQ doesn't mention one-way alerts or split-ticket
  combos. A user who receives a "Combo malin" Telegram alert and
  searches the FAQ finds nothing.
- `app/page.tsx` pricing grid doesn't position the new offer types as
  features (acceptable as they're not premium-gated, but the story
  isn't told).
- `app/_components/LandingAnimated.tsx:113` — every example deal card
  hard-codes "A/R" and never shows a one-way or combo card.

**Authenticated app layer (mid leak):**
- `app/profile/page.tsx:21` and `app/onboarding/page.tsx:23` — the
  legacy "Vols à prix cassés" offer-type card still describes itself as
  "Billets d'avion **aller-retour** en promo". It's also a ghost UI:
  it gates the whole flight pipeline but uncoking it has no real
  alternative since `package` and `accommodation` were dropped.
  Either reword + remove the alternatives, or remove the picker.
- `app/home/page.tsx:521` one-way migration banner — the
  `gg_oneway_banner_dismissed` flag in localStorage isn't cleared when
  the user actively unchecks `one_way` in their profile. They get
  re-prompted to enable an option they just opted out of. Subtle but
  user-hostile.
- `app/profile/page.tsx` `includeSplitTickets` state stays `true` in
  memory after the user unchecks "Aller-retour", so re-checking
  surfaces a sub-option they may not have intentionally re-validated.

**Dead code / zombie pages:**
- `app/dashboard/page.tsx` — orphaned. No navigation links to it. Has
  its own local `<FlightDealCard>` (different from the shared V5 one),
  free/premium tabs that no longer exist on `/home`, and a "Deals" nav
  link we just removed. Either delete the page or expose it. Today's
  state forces us to maintain it (we already had to fix
  `return_date: null` typing in it).
- `app/articles/[slug]/page.tsx:179` — same nav as `/home` but slightly
  different. Worth extracting a shared `<AppNav>` component.

**Compliance / transparency:**
- `app/mentions-legales/page.tsx` and `app/confidentialite/page.tsx`
  document the `/r/:token` redirect tokens but not the UTM tagging
  added in P1. Minor, but RGPD transparency benefits from being
  exhaustive.

**Recommended split:**

P0a — quick fixes that affect existing users (~2h total):
1. Reset `gg_oneway_banner_dismissed` when user unchecks `one_way`.
2. Reset `includeSplitTickets` to `false` when user unchecks
   `round_trip` in profile (state mirrors save behaviour).
3. Decide on `/dashboard`: delete OR un-orphan with a real entry point.

P0b — landing rewrite (~1.5 days):
1. Update metadata in `app/layout.tsx` to drop the "aller-retour" lock-in.
2. Add 2 example deal cards in `LandingAnimated` (one-way + combo) with
   the corresponding badges.
3. Add 2 FAQ entries: "Qu'est-ce qu'un combo malin ?" + "Recevez-vous
   aussi des aller simples ?"
4. Reword (or remove) the "Vols à prix cassés" picker in profile +
   onboarding so it doesn't say "aller-retour" anymore.
5. Update `og:image` if it still says "aller-retour".
6. Add UTM tagging to legal docs.

### Velocity drops bypass `qualified_items`

The Tier-1 velocity detector dispatches Telegram alerts directly without
inserting into `qualified_items`. Consequence: those deals don't show up
on the homepage, don't count in CTR analytics, don't surface in admin
debug. Identified during V5 P0 cleanup but deferred to keep the diff small.

**Action:** add a qualified_items insert in `_dispatch_velocity_alerts`
with `qualification_method='velocity_drop'`. Reuse existing tier logic
(velocity = always premium today). ~1 hour.

### Verify migration 028 in production

Supabase prod must have `qualification_method` before P1 (one-way
qualifier) can persist new rows successfully. Without it, every one-way
qualified insert raises and is silently dropped via `except`.

**Action:** confirm `\d qualified_items` shows the column. If not, apply
migration 028.

### Magic discount thresholds in `_deal_label()`

`jobs.py:440-443` still hard-codes `>= 60`, `>= 40`, `>= 20` for the
emoji badge mapping. Not in `app/thresholds.py`. Low-risk but inconsistent
with the rest of the cleanup.

**Action:** move to `app/thresholds.py` as `BADGE_FARE_MISTAKE_PCT`,
`BADGE_FLASH_PROMO_PCT`, `BADGE_GOOD_DEAL_PCT`. ~30 min.

---

## 🎯 Next (P1) — Active sprint

### Engagement instrumentation — round-trip alerts already covered, extend to one-way

Round-trip Telegram alerts use `_make_redirect_token()` for per-user click
tracking via `/r/:token`. One-way and split-ticket alerts only have UTMs
today (Travelpayouts-side only). Per-user attribution requires:

1. An `alert_key` for one-way (today's `compute_alert_key` is round-trip
   shaped — needs a one-way variant, probably keyed on
   `(user, dest, dep_date, direction, price_bucket)`).
2. A new dedup table or a `trip_type` column on `sent_alerts`.

**Why it matters:** without per-user clicks, we can't measure if a
specific user dismisses one-way alerts (signal to auto-disable). We're
flying blind on the value of the V5 promise.

**Effort:** ~1.5 days. Blocked on agreeing on the dedup key shape.

### CTR dashboard surface admin UI

`/api/admin/ctr` exists but no frontend page consumes it. Today only
queryable via curl + admin key. Building a `/admin/engagement` page that
shows CTR by route × period × tier × `qualification_method` would
unblock data-driven decisions on threshold tuning.

**Effort:** ~1 day frontend, ~2 hours backend (extend the endpoint with
breakdowns).

### Funnel metrics for `_analyze_new_flights`

The pipeline already tracks rejection counters
(`rejected_no_bucket`, `rejected_no_baseline`, etc.) and logs them
once per run. They're NOT persisted, so we can't see week-over-week
trends.

**Action:** insert into a new `analyze_funnel_logs` table on each run.
Migration 029. Surface on the admin page.

**Effort:** ~3 hours.

---

## 📊 Later (P2) — 2-4 weeks out

### One-way baseline pipeline (option A)

Replace the option C qualifier (raw discount vs 30-day median) with a
proper baseline-driven detection mirroring the round-trip cascade:
seasonal → legacy → dest-wide on `(origin, destination, direction, month, lead_time)`.

**Trigger:** at least 4 weeks of one-way scraping data accumulated.
Decision based on:
- Number of `(origin, dest, direction)` cells with ≥30 observations.
- Stability of the option C qualifier output (is it producing too many
  false positives? too few?).

**Effort:** ~3 days when triggered.

### Decommission option C fallback for one-way

Once option A is live and proven, drop the `oneway_discount`
qualification path. Keep it only as a transition fallback for cells
with <30 obs. Same pattern the round-trip pipeline already uses with
`fallback_discount`.

### Re-verify funnel metrics + circuit breaker

Today `reverify_flight_price()` is a synchronous gate. If the source
API is slow or rate-limited, qualified deals get rejected silently.
No tracking of `verify_succeeded / verify_timeout / verify_disappeared`.

**Action:**
1. Track outcomes per call.
2. Add a circuit breaker: if reverify fails >50% over 5 minutes,
   skip reverify entirely and trust the candidate (with a flag).
3. Surface metrics on the admin engagement page.

**Trigger:** when daily volume passes ~200 qualified candidates/day OR
the first incident where users complain about missed deals.

### Scorer enrichment — only if data warrants

External review suggested adding `scarcity`, `velocity`, `freshness`,
`seasonal_opportunity` to the score. Premature today: with 60/25/15
weights and hotel rating dropped, the score is already correlated with
discount but discriminates better than before.

**Decision rule:** before enriching, look at 2 weeks of CTR data
broken down by `score` band (40-49, 50-59, 60-69, 70-79, 80+). If
the click rate is flat across bands, the score under-discriminates and
we add features. If higher bands click significantly more, the score
already works — leave it alone.

**Effort:** 3-5 days when triggered.

### Migration: hardcoded URLs out of `composer/package_builder.py`

`package_builder.py` is legacy (vol+hôtel packages were dropped). Still
imported but no live caller in production. Either delete the module or
isolate it behind a feature flag.

**Effort:** ~1 hour audit, ~half day if removal.

---

## 🚀 Long-term (P3) — Quarter+

### DB-backed thresholds with A/B testing

Replace `app/thresholds.py` with a `pipeline_thresholds` table allowing
per-route, per-tier, and experiment-scoped overrides. Cache 5min in
memory. Audit log of changes.

**Trigger:** when we genuinely want to A/B test thresholds (not just
"it would be nice"). Today the constants in code are fine.

### ML-driven scoring on engagement history

Once we have ≥3 months of click + conversion data, replace the static
weighted scorer with a multiplier learned from historical engagement
per route. Stay weighted; don't go full ML.

**Trigger:** ≥10k tracked alerts AND active premium subscribers.

### Multi-channel alert distribution (email at parity with Telegram)

Today email is welcome-only. The deal alerts run Telegram-only, which
caps reach to opted-in Telegram users. Adding email parity opens the
funnel to anyone who signs up.

**Trigger:** product decision once Telegram engagement plateaus.

---

## ❌ Killed / Won't do

### Stopover (escales longues)

**Killed during V5 planning.** Out of scope: distinct positioning,
distinct partnerships (Finnair, TAP, Turkish stopover programs), distinct
storytelling. If revisited, would warrant its own product line.

### Skiplagging / hidden-city ticketing

**Killed during V5 planning.** Legal risk (American Airlines vs.
Skiplagged 2023, Lufthansa cases), affiliate program TOS conflicts
(Travelpayouts terms forbid promoting hidden-city), brand risk. Not
worth it for a flight alert product.

### Auto opt-in for existing users on `one_way` after V5

**Killed in V5 design.** Default `flight_trip_types=['round_trip']`
preserves the pre-V5 user experience. The dashboard banner on `/home`
is the migration path for those who want it.

### Two distinct toggles (outbound / inbound) in profile

**Killed in V5 design.** Single "Aller simple" toggle. The pipeline
handles both directions internally. Splitting in UI adds friction
without measurable value.

### Hotel rating in scorer

**Killed in V5 P0.** Always 0 for the flight-only product. Capped score
at 85. Removed in `cd4da7a`.

### Reading `accommodation_rating` from `package_builder.py`

**Soft-killed in V5 P0.** The arg is kept on `compute_score()` for API
compatibility but ignored. Once `package_builder` is decommissioned
(see P2), drop the parameter entirely.

---

## Decision log

When a roadmap item changes status (e.g. P2 → P1, or moves to "Done" /
"Killed"), log the rationale in one line below.

- **2026-04-29** — V5 P0 shipped (`cd4da7a`). Decision: scorer reweight
  60/25/15 instead of equal redistribution; user wanted discount-heavy.
- **2026-04-29** — V5 P1 shipped (`afc3856`). Decision: option C
  (median-based qualifier) now, option A (full baseline) deferred to P2
  pending 4 weeks of one-way data.
- **2026-04-29** — Roadmap created (this file).
- **2026-04-29** — UI/UX audit logged as P0 (split P0a quick-fix
  + P0b landing rewrite). Not started yet — owner to schedule.
