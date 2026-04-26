# GlobeGenius — Architecture technique & approche produit

## Vision produit

GlobeGenius est un outil de détection et d'alerte de bons plans vols en temps réel. L'utilisateur connecte son compte Telegram, renseigne ses aéroports de départ, et reçoit automatiquement des alertes quand un vol depuis son aéroport dépasse un seuil de réduction statistiquement significatif. L'approche repose sur une analyse de prix continue, pas sur un simple comparateur.

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Frontend | Next.js 16 (React 19, TypeScript, Tailwind CSS 4) |
| Backend | FastAPI (Python 3.12, Uvicorn) |
| Scheduler | APScheduler 3.10 (AsyncIO, cron triggers) |
| Base de données | Supabase PostgreSQL (supabase-py 2.13) |
| Auth | JWT HS256 (30 jours), cookie de session `gg_session` |
| Notifications | Telegram Bot (python-telegram-bot 21.10) |
| Paiements | Stripe (webhooks + portail client) |
| LLM | Claude (Anthropic SDK) — planner + génération d'articles |
| Scraping navigateur | Playwright 1.49 + Apify |
| Hébergement backend | Railway |
| Hébergement frontend | Vercel |

---

## Architecture globale

```
┌─────────────────────────────────────────────────────────┐
│                        FRONTEND                         │
│  Next.js — home, profile, onboarding, admin, articles   │
│  Auth: JWT localStorage + session cookie                │
└────────────────────────┬────────────────────────────────┘
                         │ REST JSON
┌────────────────────────▼────────────────────────────────┐
│                        BACKEND                          │
│  FastAPI — API REST + APScheduler + Bot Telegram        │
│                                                         │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │   Scrapers   │  │   Analyseurs  │  │  Alertes    │  │
│  │  Tier1 (LCC) │  │  Baselines    │  │  Telegram   │  │
│  │  Travelpayts │  │  Anomaly det. │  │  Digest     │  │
│  │  Vueling     │  │  Scorer       │  │  Dedup      │  │
│  └──────┬───────┘  └───────┬───────┘  └──────┬──────┘  │
└─────────┼──────────────────┼─────────────────┼─────────┘
          │                  │                 │
┌─────────▼──────────────────▼─────────────────▼─────────┐
│                    Supabase PostgreSQL                  │
│  raw_flights · price_baselines · qualified_items        │
│  sent_alerts · user_preferences · users                 │
│  scrape_logs · premium_grants · articles · packages     │
└─────────────────────────────────────────────────────────┘
```

---

## Pipeline de détection

### Vue d'ensemble

```
SCRAPING (toutes les 20 min / 2h)
    │
    ▼
raw_flights (upsert par hash)
    │
    ▼
_analyze_new_flights()
    │
    ├─ 1. Bucket durée (short/medium/long)
    ├─ 2. Règle stops (vol court → direct uniquement)
    ├─ 3. Lookup baseline (cascade 3 niveaux)
    ├─ 4. detect_anomaly() → z-score + discount
    │       └─ Fallback : discount ≥ 40% si z-score insuffisant
    ├─ 5. Filtre discount/score minimum
    ├─ 6. reverify_flight_price() — vérification temps réel
    └─ 7. qualified_items (insert) + dispatch groupé
                │
                ▼
    _dispatch_grouped_flight_alerts()
                │
                ├─ Dédup 7 jours (sent_alerts)
                ├─ Quota free tier (3/semaine)
                └─ Envoi Telegram groupé par destination
```

### Sources de scraping

| Source | Type | Couverture | Fréquence | Notes |
|--------|------|-----------|-----------|-------|
| Ryanair direct | LCC | CDG, ORY | Toutes les 20 min | Tier 1 — données quasi temps réel |
| Vueling direct | LCC | CDG, ORY | Toutes les 20 min | Demotion par route si API défaillante |
| Transavia direct | LCC | CDG, ORY | — | **Désactivé** (API retourne du HTML) |
| Travelpayouts | Agrégateur | 9 aéroports MVP | Toutes les 2h | Gratuit ; bootstrap des baselines |
| Google Flights (Apify) | Agrégateur | Toutes destinations | À la demande | Bootstrap baselines saisonnières |

**Aéroports MVP** : CDG, ORY, LYS, MRS, NCE, BOD, NTE, TLS, BVA

### Bucketing des durées

| Bucket | Durée séjour |
|--------|-------------|
| `short` | 1–3 jours |
| `medium` | 4–7 jours |
| `long` | 8–12 jours |

Les séjours hors plage sont rejetés. Les vols court-courrier (< 180 min) n'acceptent que 0 escale.

### Calcul des baselines

Clé de lookup en cascade (du plus précis au plus générique) :

```
1. {origin}-{destination}-bucket_{X}-m{MM}-lt{lead_time}   ← saisonnier
2. {origin}-{destination}-bucket_{X}                        ← legacy
3. *-{destination}-bucket_{X}                               ← cold-start
```

Lead-time buckets : `lt30` (0-29j), `lt60` (30-59j), `lt90` (60-89j), `lt90p` (90j+)

Pondération temporelle : les prix récents ont un poids plus élevé (`weight = 1 / age_days`).
Seuil minimum : **5 observations** par cellule.

### Détection d'anomalie

```python
z_score    = (avg_price - price) / std_dev
discount   = (avg_price - price) / avg_price * 100
```

| Niveau | z-score | Discount | Badge |
|--------|---------|----------|-------|
| `fare_mistake` | ≥ 3.5 | ≥ 60% | 🔴 ERREUR DE PRIX |
| `flash_promo` | ≥ 2.5 | ≥ 40% | 🟠 PROMO FLASH |
| `good_deal` | ≥ 2.0 | ≥ 20% | 🟡 BON DEAL |
| Fallback | — | ≥ 40% | `good_deal` (z-score non fiable) |

Le fallback s'active quand `detect_anomaly()` retourne `None` mais que le discount brut est ≥ 40% — cas typique d'une baseline avec forte variance ou trop peu d'observations.

### Scoring (0–100)

```
score = 0.50 × discount_score
      + 0.20 × popularité_destination
      + 0.15 × flexibilité_dates
      + 0.15 × note_hébergement
```

La popularité est une table statique par code IATA (BCN=95, LIS=90, DXB=90…). Pour les vols seuls, flexibilité et hébergement valent 0.

### Tier d'un deal

| Condition | Tier | Comportement |
|-----------|------|-------------|
| discount ≥ 50% | `premium` | Prix masqué pour les utilisateurs free |
| discount < 50% | `free` | Prix visible jusqu'au quota hebdomadaire |

---

## Système d'alertes Telegram

### Flux de connexion

```
User → POST /api/users/{id}/telegram/generate-link
     ← { link: "https://t.me/Globegenius_bot?start={token}" }

User clique → Telegram /start {token}
           → Webhook → match token → user_preferences mis à jour
              (telegram_connected=true, telegram_chat_id=...)
```

### Déduplication

- **Clé** : `SHA256("{user_id}|{destination}|{price_bucket}")[:32]`
- **Fenêtre** : 7 jours (168h)
- **Bucket prix** : tranches de 50€ — un passage de 85€ (bucket 50) à 45€ (bucket 0) déclenche une nouvelle alerte

### Quotas free tier

- **3 alertes complètes / 7 jours** (Telegram + homepage combinés)
- Au-delà : message teaser avec prix masqué + CTA Premium
- Les deals > 50% envoient un teaser masqué systématiquement

### Format d'un message groupé

```
🌍 Lisbonne (LIS)
🟠 PROMO FLASH — 3 offres

📅 Juin 2026
15 juin – 22 juin | 7j
💰 104€ · -34%  ✈️ Ryanair
[🔗 Voir le vol]  [🏨 Voir les hôtels]

📅 Août 2026
...
```

---

## API REST — endpoints principaux

### Auth & utilisateurs

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| POST | `/api/auth/signup` | — | Création de compte |
| POST | `/api/auth/login` | — | Connexion (retourne JWT) |
| GET/PUT | `/api/users/{id}/preferences` | JWT | Préférences (airports, budget, deal_tier) |
| PUT | `/api/users/{id}/email` | JWT | Changement d'email |
| PUT | `/api/users/{id}/password` | JWT | Changement de mot de passe |
| DELETE | `/api/users/{id}/account` | JWT | Suppression de compte |

### Deals & contenu

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET | `/api/packages` | Optionnelle | Deals (plan, min_score, min_discount, limit) |
| GET | `/api/status` | — | Statut pipeline (scrapes récents, baselines) |
| GET | `/api/articles` | — | Liste des guides destination |
| GET | `/api/articles/{slug}` | — | Guide destination complet |

### Telegram & Stripe

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| POST | `/api/users/{id}/telegram/generate-link` | JWT | Génère le lien de connexion bot |
| GET | `/api/users/{id}/telegram/status` | JWT | Statut de la connexion Telegram |
| POST | `/api/stripe/create-checkout` | JWT | Lance une session Stripe Checkout |
| GET | `/api/stripe/status` | JWT | Statut abonnement premium |
| POST | `/api/stripe/webhook` | — | Événements Stripe (subscription lifecycle) |

### Admin

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET | `/api/admin/users` | Admin key | Liste utilisateurs + tier |
| PUT | `/api/admin/users/{id}/premium` | Admin key | Grant premium manuel |
| GET | `/api/admin/routes` | Admin key | Routes monitorées + baselines |
| GET | `/api/admin/ctr` | Admin key | Taux de clic sur les alertes |
| POST | `/api/trigger/{job}` | Admin key | Déclenche un job manuellement |

---

## Jobs planifiés

| Job | Déclencheur | Description |
|-----|-------------|-------------|
| `scrape_tier1` | Toutes les 20 min | Ryanair + Vueling depuis CDG/ORY |
| `scrape_flights` | Toutes les 2h (heures paires) | Travelpayouts sur tous les MVP airports |
| `travelpayouts_enrichment` | 4h quotidien | Enrichissement métadonnées vols |
| `recalculate_baselines` | 3h quotidien | Recalcul des moyennes historiques |
| `expire_stale_data` | 5h quotidien | Purge des données périmées |
| `daily_digest` | 8h quotidien | Résumé des meilleurs deals du jour |
| `daily_admin_report` | 9h quotidien | Rapport stats vers canal admin |
| `sync_stripe_subscriptions` | 6h quotidien | Synchronisation `premium_expires_at` |
| `update_destinations` | Lundi 3h | Mise à jour destinations prioritaires |
| `check_scraper_health` | 7h quotidien | Probe Tier 1 ; réactivation si récupéré |

---

## Base de données — tables principales

| Table | Rôle |
|-------|------|
| `users` | Comptes utilisateurs (email, password_hash) |
| `user_preferences` | Airports, budget, Telegram, Stripe, premium_expires_at, deal_tier, alerts_paused_until |
| `raw_flights` | Tous les vols scrapés (hash unique pour dédup) |
| `price_baselines` | Moyennes historiques par (route, bucket, mois, lead-time) |
| `qualified_items` | Deals détectés (price, baseline, discount_pct, score, tier, status) |
| `sent_alerts` | Log de déduplication (user_id, alert_key, created_at) |
| `scrape_logs` | Audit des runs de scraping (source, items, erreurs, durée) |
| `premium_grants` | Grants premium manuels (admin, sans expiry possible) |
| `destination_wishlists` | Routes favorites par utilisateur (origin, destination, max_price, month) |
| `price_snapshots` | Snapshots pour détection de vélocité (chutes 40-60% en < 2h) |
| `articles` | Guides destination générés par LLM |
| `alert_redirect_tokens` | Tokens de tracking CTR (clic alerte → réservation) |
| `packages` | Bundles vol + hébergement (feature en cours) |

---

## Authentification & tiers premium

### JWT

- Algorithme : HS256
- Expiry : 30 jours
- Payload : `{ sub: user_id, email, exp, iat }`
- Stockage front : `localStorage["gg_token"]`

### Détermination du tier (`_get_user_tier`)

```
1. premium_grants (grant admin actif, non révoqué, non expiré) → "premium"
2. user_preferences.premium_expires_at (Stripe) > now            → "premium"
3. Fallback                                                        → "free"
```

---

## Paramètres de configuration clés

| Paramètre | Défaut | Rôle |
|-----------|--------|------|
| `MIN_DISCOUNT_PCT` | 40% | Seuil de qualification minimum |
| `MIN_SCORE_ALERT` | 40 | Score minimum pour déclencher une alerte |
| `MIN_SCORE_DIGEST` | 30 | Score minimum pour le digest quotidien |
| `FREE_TIER_WEEKLY_LIMIT` | 3 | Alertes complètes / 7 jours (free) |
| `ALERT_INHIBIT_HOURS` | 168 | Fenêtre de déduplication (7 jours) |
| `PRICE_BUCKET_SIZE` | 50€ | Granularité des buckets prix |
| `GLOBAL_MIN_DISCOUNT` (API) | 40% | Seuil d'affichage homepage |
| `BASELINE_RECALC_HOUR` | 3h | Heure UTC du recalcul baselines |
| `DIGEST_HOUR` | 8h | Heure UTC du digest quotidien |
| `DATA_FRESHNESS_HOURS` | 2h | Âge max pour données "fraîches" |
| `MVP_AIRPORTS` | 9 airports | CDG, ORY, LYS, MRS, NCE, BOD, NTE, TLS, BVA |

---

## Approche produit

### Positionnement

GlobeGenius cible les voyageurs français opportunistes — ceux qui partent quand une bonne affaire se présente plutôt que de planifier à l'avance. Le produit s'insère dans le flux Telegram de l'utilisateur et envoie une alerte uniquement quand un deal est statistiquement exceptionnel.

### Différenciation technique

- **Détection statistique** : z-score sur baseline historique vs simple comparaison de prix affichés
- **Données temps réel** : Tier 1 LCC toutes les 20 min vs agrégateurs qui cachent les données 2-6h
- **Vérification avant envoi** : `reverify_flight_price()` confirme que le prix est encore live
- **Déduplication intelligente** : une seule alerte par (destination, bucket prix) sur 7 jours
- **Groupement par destination** : plusieurs dates dans un seul message Telegram

### Modèle freemium

| | Free | Premium |
|-|------|---------|
| Deals affichés | ≥ 40% (3 unlocked/semaine) | Tous illimités |
| Deals > 50% | Teaser masqué | Prix complet |
| Alertes Telegram | 3/semaine | Illimitées |
| Wishlist | ✓ | ✓ |

### Roadmap technique identifiée

- Abaissement du seuil z-score good_deal de 2.0 → 1.5 après accumulation de 3 mois de baselines (prévu juillet 2026)
- Réactivation Transavia quand l'API directe est rétablie (scraper_health_agent)
- Baselines saisonnières plus robustes (actuellement ~18 obs/route, objectif ≥ 30)

---

## Dette technique

### 🔴 Critique — Orchestration des jobs (APScheduler in-process)

**État actuel** : APScheduler tourne dans le même processus Uvicorn que l'API FastAPI sur Railway. Un seul worker, un seul scheduler.

**Risques à mesure que le service scale :**
- **Doublons de jobs** : si Railway redémarre le service ou scale à plusieurs replicas, chaque instance lance son propre scheduler → double scraping, double dispatch d'alertes, doublons en DB.
- **Trous de scraping** : un redémarrage en cours de job (déploiement, crash) interrompt le run sans reprise.
- **Contention API** : les jobs lourds (scraping 900+ vols, reverify 50 deals) partagent le thread pool avec les requêtes HTTP entrantes → latence API dégradée pendant les runs.

**Seuil de criticité** : acceptable jusqu'à ~500 utilisateurs actifs avec un seul worker Railway. Devient dangereux au-delà ou dès qu'on active le scaling horizontal.

**Solution cible** : externaliser le scheduler dans un worker Railway dédié (service séparé dans le même projet) avec une variable d'environnement `SCHEDULER_ONLY=true`. Le service API reste stateless, le worker scheduler est unique par design. Alternativement : migrer vers un queue-based system (Redis + ARQ ou Celery) avec Railway Redis add-on.

**Action avant scale** : ajouter une guard `SCHEDULER_ENABLED=false` sur le service API dès qu'un second replica est activé.

---

### 🟡 Moyen — Robustesse statistique des baselines

**État actuel** : détection par z-score sur moyenne pondérée + écart-type. Fallback discount brut ≥ 40% si z-score insuffisant.

**Limites connues :**
- Baselines jeunes (< 30 obs) ont des écarts-types instables → faux positifs ou faux négatifs selon la route.
- Les routes à tarification très promotionnelle (ex. Ryanair BVA→LIS) ont une variance naturellement élevée qui rend le z-score peu discriminant.
- Pas de détection de "régime de prix" (une compagnie qui baisse structurellement ses tarifs fait monter le taux de faux positifs).

**Solution cible** : percentiles par route (p10/p25) comme estimateurs résistants aux outliers ; score de confiance de la baseline (fonction de `sample_count` et de l'âge des observations) affiché dans les logs de diagnostic.

**Action immédiate** : aucune — les baselines s'améliorent naturellement avec le temps. Réévaluer en juillet 2026 (seuil z-score + robustesse).

---

### 🟢 Mineur — Conformité RGPD : granularité opérationnelle

**État actuel** : politique de confidentialité correcte dans les grandes lignes (bcrypt, TLS 1.3, pas de cookies pub, collecte minimale).

**Points à compléter avant croissance utilisateurs :**
- Durée de rétention explicite des `scrape_logs` et `alert_redirect_tokens` (actuellement purge à 24h pour les snapshots, non documenté pour les autres tables).
- Traçabilité de la suppression en cascade lors d'un `DELETE /api/users/{id}/account` (FK cascade existante, à documenter dans la politique).
- Cycle de vie des sessions JWT (expiry 30j, pas de révocation active côté serveur — à mentionner).

**Action** : mettre à jour la politique de confidentialité avec les durées de rétention exactes par table lors de la prochaine révision légale.
