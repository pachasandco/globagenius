# Globegenius — Roadmap

Single source of truth for what's planned, what's deferred, and what's been
killed. **Append-only** for the "Done" section, **mutable** for the rest.

Last updated: 2026-05-04 (V9 / V10 shipped on branch `v9`).

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
- `51531b0` — Per-user click tracking on one-way + split-ticket alerts
  (migration 029, dedup keys, /api/admin/ctr breakdowns by trip_type
  and qualification_method)
- `8c47991` — Drop the 'Se désabonner' button from Telegram alerts +
  webhook URL re-pinned (out-of-band fix for stale Railway domain)
- `e3f5134` — Telegram alert headers redesigned: 🛫/🛬 split lines,
  fix double-IATA bug, one-way uses 'Départ de' / 'Retour de' phrasing
- `b5d7f8a` — Admin endpoint `POST /api/admin/users/{id}/telegram/generate-link`
  for manual recovery of users who never finished onboarding
- `f8b0b5a` — Self-service Telegram reconnect card in /profile (poll
  loop confirms when /start <token> lands on the webhook, no manual
  refresh needed)

### V7 — Simpler free-tier alert policy (April 2026)

- `a9837cb` — Free users: full alerts only in [40%, 50%); deals in
  [50%, 60%) silently skipped (dead band); deals ≥60% trigger a
  teaser, max 1 per rolling 7-day window. Removes the noisy
  'limit reached' teaser. Premium unchanged.

**Migrations to apply on Supabase prod (in order):**
025_flight_trip_types · 026_oneway_flights · 027_include_split_tickets ·
028_qualification_method · 029_redirect_tokens_trip_type
(V7 introduces no new migration — uses existing `sent_alerts` table with a
new `alert_type='teaser_premium'` value.)

### V9 / V10 — Telegram-first product, perf hardening, churn signal (May 2026)

**Branch:** `v9` (V10 squashed in via PR #5).

**Performance & infra**
- `38a88db` — login `async` + bcrypt/DB in `run_in_executor` so /api
  routes stop blocking on auth. Signup welcome email now via
  BackgroundTasks (was up to 10 s sync). Email validator: 1 h LRU
  cache + 1 s timeout (was 3 s, no cache).
- `48d2f21` — Railway split into 2 services. `globagenius` (web,
  RUN_SCHEDULER=0, WEB_CONCURRENCY=2) serves API only. `globagenius-
  worker` (RUN_SCHEDULER=1) runs APScheduler + scrapers. /health
  dropped from 5–15 s to 80 ms after the split.
- `2e54c67` — `BACKEND_URL` no longer hardcoded to a stale Railway
  domain in `config.py`; both Railway services have it set as env var
  so `setup-webhook` can't silently re-publish a dead URL again.
- `f1a1e12` — `WEB_CONCURRENCY` and `RUN_SCHEDULER` env vars wired up
  with safe defaults.

**Telegram bot — full in-chat control**
- `c230918` — Per-alert `🚫 Masquer <destination>` button (one-tap
  blocking). Pause now opens a sub-menu (7 d / 30 d / indefinite).
  `/destinations` command lists blocked destinations + free-text
  search by city name (accent-insensitive). `/pause` slash-command
  mirrors the inline button. `setMyCommands` published so the
  hamburger menu surfaces /destinations, /pause, /status, /help.
  IATA ↔ name mapping pulled from `articles` table (single source of
  truth, cached 15 min).

**Front rebuild**
- `5dffcf0` / `12fabc3` — Brand wordmark moved to image
  (logo2.png 67 KB, transparent). `--color-globe-blue: #1E90FF` and
  navy text colour `#082B78`. Nav h-[80px] with h-16 logo. Favicon
  swapped from default Vercel to GG logo.
- `09909ca` — Landing copy fully Telegram-centric: hero subline +
  CTA "Activer mes alertes Telegram", stats bar shows "<5 s alerte
  sur Telegram", new "Pourquoi Telegram, et pas un email ?" section
  before pricing (3 cards), final CTA fused with the orphan Telegram
  banner into a 2-card "Tu as déjà Telegram / Pas encore Telegram ?"
  block.
- `2ebf000` — `/home` rewrite: deals feed dropped (real-time alerts
  live in Telegram only). New Telegram-status banner (deep-link to
  the bot, mentions /destinations and /pause), planificateur
  promoted to a hero card, every published destination guide shown
  in a dense mosaic. -236 net lines.
- `22dc769` — Planificateur refactor with shadcn/ui (Radix Nova): bot
  avatars in chat, day-by-day Card grid with Sunrise/Sun/Moon icons,
  tone-tinted onboarding pills.
- `f857a0e` / `f38a314` — Favicon swap and home deals filter (now
  obsolete: deals feed removed entirely).

**Stripe / pricing**
- `6c82e29` — `stripe_subscription_period_end` helper reads
  `subscription.items.data[0].current_period_end` (Stripe API change
  2025-03-31), used in webhook + sync job. Without this, every paid
  signup since the API rev got a null `premium_expires_at` and the
  daily sync job marked them expired overnight.

**Churn signal**
- `ca5a6e7` — Cancellation survey on /profile (mandatory radio with
  8 reasons + 500-char free-text feedback). Inserted into new
  `cancellation_reasons` table (migration 035). Best-effort insert:
  if the table write fails, the cancellation still goes through.

**Min-discount filter — finally honoured**
- `a71eaa7` — Widened `sent_alerts.alert_type` CHECK to allow
  `one_way` and `split_ticket` so dispatchers stop crashing on insert.
- `bda4409` — `_user_passes_discount_floor` helper applied to
  one-way and split-ticket dispatchers (previously: only round-trip
  was filtered, premium 60 %-floor users still got 40 % one-way
  alerts).
- `2357a8b` — Removed admin override of `min_discount` (the table on
  `/admin/users` had a select that wrote 20-60 %; user-set 60 %
  could be silently overwritten to 30 % from there). `reset_prefs`
  also no longer touches `min_discount`.
- `fdf745f` — The actual smoking gun: round-trip dispatcher's SELECT
  on `user_preferences` didn't include `min_discount`, so every
  premium user was being treated as if their floor was 40 %. One
  added column to the SELECT.

**Vueling Tier 1 fake-deal catastrophe**
- `40d91df` — Vueling calendar endpoint exposes ONE-WAY leadprices.
  Scraper used to ship them as round-trip rows verbatim (30 € ORY-
  IBZ), discount vs A/R baseline → -78 %, "Erreur de prix" alert,
  user clicks → 100 € real A/R. Fix: multiply by 2.0× on persist,
  Travelpayouts cross-check in reverify, and `_deal_badge` no longer
  stamps "Erreur de prix" when sources are leadprice-only. 178 stale
  qualified items invalidated in DB.
- `ac12788` — Bumped multiplier to 2.2× (return leg from southern
  destinations is asymmetrically more expensive). `_reverify_via_
  travelpayouts` now returns `(verdict, cheapest_match)`; when TP
  confirms a higher real A/R within 50 % tolerance, we adopt the TP
  price so the user sees in Telegram exactly what Aviasales will
  show on click. Anomaly recomputed after reverify; deals dropping
  below 15 % / z=1.5 after price adjustment are dropped instead of
  dispatched with a fake big discount.

**Destination universe expansion**
- `3985447` — Long-haul coverage roughly doubled to align with
  French traveller habits (school holidays, DOM-TOM, Cuba, Vietnam,
  Madagascar, Tahiti, Vancouver, etc.). 28 → 59 long-haul guaranteed
  destinations. `LONG_HAUL_DESTINATIONS`, `LONG_HAUL_GUARANTEED`,
  `SEASONAL_DESTINATIONS`, `HIGH_FARE_MISTAKE_ROUTES` re-aligned.
  Removed PMI duplicate.

**Guides — never ship without a cover photo**
- `a6df3a2` — Writer skips insert when no Unsplash photo found
  (was creating empty-cover guides). Added a fallback chain
  (city-only / city + country / "city skyline") so destinations
  with airport-name labels like "Londres Stansted" or "Milan
  Bergame" no longer get rejected silently. 7 existing guides
  back-filled in DB via one-shot script.

**Telegram alert UX**
- `e975160` — Removed the per-offer "🏨 Voir les hôtels" CTA from
  grouped flight alerts. Cluttered the message; the Booking
  affiliation revenue was negligible.

**Migrations applied to Supabase prod since V7:**
030_password_reset_tokens · 031_stripe_columns · 032_articles_iata_
destination · 033_articles_country_nullable · 034_sent_alerts_
subtypes · 035_cancellation_reasons.

---

## 🔥 Now (P0) — Open items

Most of the V5 / V5+ / V7 P0 backlog landed in V8 / V9 / V10 (see Done).
Remaining real items, ordered by risk:

### `/dashboard` orphan page (low risk, low effort)

`app/dashboard/page.tsx` exists but no navigation links to it (verified
2026-05-04: `grep -rn 'href="/dashboard"' frontend/src` returns 0).
Carries its own legacy `<FlightDealCard>` rendering and free/premium
tabs that no longer exist on `/home` after the V10 home rewrite.

**Action:** either delete the route entirely, or wire it back into
the nav with a clear purpose. Today's state silently doubles
maintenance cost without delivering value. ~15 min.

### Velocity drops bypass `qualified_items`

The Tier-1 velocity detector dispatches Telegram alerts directly via
the synthetic `QualifiedItem` it builds in `_dispatch_velocity_alerts`,
but doesn't insert a row into `qualified_items`. Consequence: those
deals don't show up on the homepage, don't count in CTR analytics,
don't surface in admin debug. Confirmed 2026-05-04 still the case.

**Action:** add a qualified_items insert in `_dispatch_velocity_alerts`
with `qualification_method='velocity_drop'`. Reuse existing tier logic
(velocity = always premium today). ~1 hour.

### Magic discount thresholds in `_deal_label()`

`jobs.py:458-465` still hard-codes `>= 60`, `>= 40` for the legacy
`_deal_label` helper. The function is currently unused (the live badge
logic is in `telegram._deal_badge`, source-aware after V10), but the
constants are duplicated, which is exactly the inconsistency we cleaned
up elsewhere.

**Action:** either delete `_deal_label` (looks unused) or move the
constants to `app/thresholds.py`. ~15 min.

### Profile / onboarding "Vols à prix cassés" picker

`app/profile/page.tsx` and `app/onboarding/page.tsx` still expose a
single-item offer-type picker labelled "Vols à prix cassés / Billets
d'avion aller-retour en promo". It's a ghost UI: there's only one
choice, the description is partly stale (one-way + combos shipped),
and the user can't actually choose anything else since `package` and
`accommodation` were dropped.

**Action:** remove the picker entirely (cleaner) or reword and keep
it as info-only. ~30 min.

---

## 🎯 Next (P1) — Active sprint

### Configure SMTP for transactional outreach from contact@globegenius.app

Welcome emails ship today via `app/notifications/welcome_email.py` but
SMTP is not configured on Railway prod (HOST/PORT/USER/PASS all unset),
so the welcome flow runs no-op. Once a provider is wired:

- Welcome emails actually go out.
- Ops can email premium users who never completed Telegram onboarding
  with their personal connect link (the admin endpoint added in `b5d7f8a`
  produces the link; SMTP is what's missing to automate the send).
- Future use cases: digest opt-out, premium expiry reminders, etc.

**Suggested provider:** Resend or Brevo. Both accept a single API key
and "From: contact@globegenius.app" once the domain DNS is verified
(SPF + DKIM TXT records). ~1 hour including DNS.

**Action:**
1. Pick provider, verify the domain.
2. Set `SMTP_HOST/PORT/USER/PASS` (or swap `welcome_email.py` for the
   provider's HTTP API).
3. Add a thin `send_telegram_invite_email(user_id)` helper that pulls
   the personal link via `admin_generate_telegram_link` and emails it.
4. Schedule a weekly job that picks up premium users with
   `telegram_connected=false` and emails them the link.

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

## 🛠 Runbook / Ops gotchas

Lessons paid for in production. Each item is a procedure to remember,
not work to schedule. Append when something bites us.

### Telegram webhook URL drifts when Railway changes the public domain

**Symptom:** inline-keyboard buttons (Pause, future buttons) silently do
nothing. No error in our backend logs because Telegram never reaches us.

**Root cause:** Railway can change a service's `*.up.railway.app` URL
between deploys (rare but happens, especially after re-creating a
service). Telegram's `setWebhook` was set once and stays pinned to the
old URL. Every callback returns 404 on Telegram's side.

**Detection:** run
```
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```
and check `last_error_date` / `last_error_message`. A persistent 404
means the URL is stale.

**Fix:** re-register the webhook against the current backend domain:
```
curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=https://<current-backend-domain>/api/telegram/webhook" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}" \
  --data-urlencode "allowed_updates=[\"message\",\"callback_query\"]"
```
Effect is immediate. No redeploy needed.

**Prevention:** when migrating or recreating a Railway service, run
`setWebhook` as part of the migration checklist, OR move to a stable
custom domain (e.g. `api.globegenius.app`) so the webhook URL never
drifts again. The custom-domain route is the durable fix; the manual
re-register is the band-aid.

### Frontend NEXT_PUBLIC_API_URL on Railway

**Same drift risk** as the Telegram webhook. The frontend's
`NEXT_PUBLIC_API_URL` env var on Railway points to the backend's
`*.up.railway.app` URL. If the backend domain rotates, the frontend
keeps fetching the old URL and silently fails (`/api/landing/deals`
returns 404, the map falls back to seeds, etc.).

**Fix:** set `NEXT_PUBLIC_API_URL` to a stable custom domain on the
backend, OR re-set the variable + rebuild the frontend each time the
backend domain changes.

### Cache busting after a frontend deploy

Railway's Fastly CDN caches `/` for `s-maxage=31536000` (1 year). When
you push a fix, the new HTML lives behind a stale CDN entry. Hard
refresh (Cmd+Shift+R) bypasses it; private browsing too. If a user
reports "I don't see the new feature" right after a deploy, this is
the first suspect.

**Diagnostic:** `curl -sI <url>` and look at `x-nextjs-cache: HIT` and
`age:`. If `age` is high, the CDN is serving stale.

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
- **2026-04-29** — Per-user engagement instrumentation shipped
  (`51531b0`). Decision: 1 click on either leg of a split-ticket combo
  counts as 1 engagement (simpler signal, captures real interest).
  CTR dashboard frontend deferred — `/api/admin/ctr` curl-only stays
  acceptable until we have real volume to look at.
- **2026-04-29** — Telegram webhook drift incident: Pause button silently
  broken for days because the webhook URL pointed to a defunct Railway
  domain. Fixed by re-running setWebhook (`8c47991`); 'Se désabonner'
  button removed at the same time (too aggressive for an accidental tap).
  Logged as a runbook gotcha in the new "Runbook / Ops gotchas" section.
- **2026-04-29** — Discovered 8 of 9 users have never connected Telegram,
  3 of them are paying premium. Root cause split: (a) onboarding never
  forced the Telegram step, (b) the broken-webhook incident swallowed
  /start <token> attempts for days. Fix landed in two parts:
  `b5d7f8a` admin endpoint to generate links by hand for ops, and
  `f8b0b5a` self-service reconnect card on /profile so users can recover
  without us. Email automation deferred (SMTP not configured) — logged
  as P1 'Configure SMTP for transactional outreach'.
- **2026-04-30** — V6 (Foursquare-augmented planner) explored on a
  separate branch. Spec + plan + 7 of 11 tasks shipped before the user
  paused and decided to set the work aside. Branch `v6` kept locally
  with 9 commits, not pushed to origin. To resume: `git checkout v6`.
  To discard: `git branch -D v6`.
- **2026-04-30** — V7 simpler free-tier policy shipped (`a9837cb`).
  Decisions: dead band [50, 60) is silent; teaser ≥60% strict 1/week;
  removed 'limit reached' teaser. Reasoning: the 'noisy upsell' loop
  with several teasers per week was hurting the free-user experience
  more than driving conversions.
