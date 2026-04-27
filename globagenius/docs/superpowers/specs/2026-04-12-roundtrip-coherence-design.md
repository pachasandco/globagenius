
# Cohérence aller-retour des deals Travelpayouts

**Date** : 2026-04-12
**Statut** : En attente de validation
**Contexte** : La migration Travelpayouts (mergée ce matin) utilise l'endpoint `/v1/prices/calendar`, qui retourne « le prix le moins cher pour chaque jour de départ » sans contrainte sur la durée du séjour. En pratique, on récupère un mélange de séjours allant de 0 à 56 jours, ce qui rend les comparaisons aux baselines incohérentes et risque d'afficher aux utilisateurs des « promos » qui n'en sont pas vraiment.

## Objectif

Garantir que **chaque deal affiché est une vraie réduction sur un vrai aller-retour**, en :

1. Récupérant uniquement de **vrais aller-retours** depuis l'API Travelpayouts
2. Comparant les prix à des **baselines pertinentes** (groupées par durée de séjour, statistiquement fiables, robustes aux outliers)
3. **Revérifiant le prix en temps réel** au moment d'envoyer une alerte
4. Filtrant les vols **à plus d'une escale** (ou plus de zéro pour le court-courrier)

Le produit ne demande JAMAIS à l'utilisateur de spécifier une durée de séjour : on lui propose les meilleures opportunités de prix qu'on trouve, et on cherche un hôtel qui colle aux dates exactes du vol au moment de la composition d'un package.

## Décisions clés

- **Endpoint API** : `/aviasales/v3/prices_for_dates` (un seul aller-retour par entrée, garanti `one_way=false`)
- **Bucketing par durée** : 3 buckets fixes — `short` (1-3j), `medium` (4-9j), `long` (10-21j). Tout vol hors `[1, 21]` jours est rejeté
- **Statistique** : médiane (pas moyenne) pour le prix de référence, robuste aux outliers
- **Seuil minimum** : 30 observations par baseline pour qu'elle soit publiée
- **Tiering business** :
  - Réduction **20% à 39%** → tier `free` (visible et alerté pour tous, mais pas de bouton de réservation)
  - Réduction **40%+** → tier `premium` (paywall Stripe pour réserver)
- **Garde-fou statistique** : z-score >= 2.0 en plus du seuil de discount
- **Règle escales** : court-courrier (< 3h vol direct) max 0 escale, long-courrier max 1 escale
- **Revérification temps réel** : juste avant d'insérer un `qualified_item`, on rappelle l'API et on confirme que le prix existe toujours et n'a pas augmenté de plus de 5% (ex: vol détecté à 100€ → accepté si l'API renvoie ≤ 105€, rejeté si ≥ 106€)
- **Pas de feature flag** : swap atomique au merge, rollback git simple
- **Hôtels et `accommodations.py` hors scope** (chantier séparé)

## Architecture

### Flux de données

```
[cron 6×/jour]
  → scrape_all_flights (prices_for_dates API)
  → 1 appel par route, ~30 vrais aller-retours retournés
  → upsert raw_flights (avec trip_duration_days, stops, duration_minutes)
  → _analyze_new_flights (réécrit) :
       1. déterminer le bucket selon trip_duration_days
       2. déterminer si court/long courrier selon duration_minutes
       3. lookup baseline {origin}-{dest}-bucket_{name}
       4. si pas de baseline OU sample_count < 30 → skip
       5. detect_anomaly → discount_pct, z_score
       6. si discount >= 20% ET z >= 2.0 ET stops respectent règle :
            → reverify_flight_price (appel temps réel)
            → si OK : qualified_item avec tier free/premium
            → composition package + alerte Telegram

[cron 1×/jour à 4h, élargi]
  → job_travelpayouts_enrichment (modifié)
  → construit baselines bucket via month-matrix
  → upsert price_baselines avec route_key {origin}-{dest}-bucket_{name}
```

### Modèle de données

#### Modifications de `raw_flights`

```sql
ALTER TABLE raw_flights
  ADD COLUMN IF NOT EXISTS trip_duration_days INTEGER,
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;

CREATE INDEX IF NOT EXISTS idx_raw_flights_route_duration
  ON raw_flights (origin, destination, trip_duration_days);
```

`stops` existe déjà dans `raw_flights` (utilisé par le legacy). À vérifier au moment du plan, à ajouter via `IF NOT EXISTS` si absent.

#### Modifications de `qualified_items`

```sql
ALTER TABLE qualified_items
  ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';
```

Cette colonne facilite le filtrage frontend pour afficher free vs premium. Elle est calculée par `_analyze_new_flights` au moment de l'insertion : `tier = "premium" if discount_pct >= 40 else "free"`.

#### Format des `route_key` dans `price_baselines`

- **Legacy (à laisser pourrir)** : `CDG-LIS-1m`, `CDG-LIS-3m`, `CDG-LIS-6m`
- **Nouveau** : `CDG-LIS-bucket_short`, `CDG-LIS-bucket_medium`, `CDG-LIS-bucket_long`

Le préfixe `bucket_` évite toute collision et permet aux deux formats de cohabiter pendant la transition.

### Définition des buckets

```python
DURATION_BUCKETS: dict[str, tuple[int, int]] = {
    "short":  (1, 3),    # weekend, city break
    "medium": (4, 9),    # semaine type
    "long":   (10, 21),  # vacances longues
}

SHORT_HAUL_MAX_MINUTES = 180  # < 3h vol direct = court-courrier
```

Les bornes sont **inclusives**. Un vol de 3 jours (départ J0, retour J3) est `short`. Un vol de 4 jours est `medium`.

Les vols hors `[1, 21]` jours sont rejetés au moment de la normalisation. Les vols à 0 jour (`return_date == departure_date`) sont également rejetés (cas pathologique d'API).

### Composants logiciels

#### Composant 1 : `app/scraper/travelpayouts.py` — nouveau helper

```python
def get_prices_for_dates(
    origin: str,
    destination: str,
    departure_month: str = "",
    return_month: str = "",
    limit: int = 1000,
) -> list[dict]:
    """Get round-trip flight prices via /aviasales/v3/prices_for_dates."""
```

Retourne une liste de dicts contenant : `origin_airport`, `destination_airport`, `departure_at`, `return_at`, `price`, `transfers`, `return_transfers`, `duration_to`, `duration_back`, `link`.

Le param `one_way=false` est forcé en interne. La fonction respecte le pattern existant (`_get` pour HTTP, `REST_URL` pour la base URL, retourne `[]` en cas d'erreur).

#### Composant 2 : `app/scraper/travelpayouts_flights.py` — modifié

- **`scrape_flights_for_route`** appelle `get_prices_for_dates` au lieu de `get_calendar_prices`
- **`_normalize_calendar_entry`** est renommé en **`_normalize_priced_entry`** et adapté :
  - Mappe `transfers` → `stops`
  - Calcule `trip_duration_days = (return_date - departure_date).days`
  - Calcule `duration_minutes = (duration_to + duration_back) // 2`
  - Utilise `origin_airport` (pas `origin` qui est la ville `PAR`)
  - Utilise le `link` retourné par l'API si présent, sinon fallback sur `_build_aviasales_url`
  - Rejette tout vol où `trip_duration_days` est hors `[1, 21]`
  - Rejette tout vol où `price <= 0` ou `departure_at` manquant

#### Composant 3 : `app/analysis/buckets.py` — nouveau module pur

```python
DURATION_BUCKETS: dict[str, tuple[int, int]] = {
    "short":  (1, 3),
    "medium": (4, 9),
    "long":   (10, 21),
}

SHORT_HAUL_MAX_MINUTES = 180

def bucket_for_duration(days: int) -> str | None: ...
def is_short_haul(duration_minutes: int) -> bool: ...
def stops_allowed(duration_minutes: int) -> int:
    """Max stops allowed for this haul type. 0 short-haul, 1 long-haul."""
```

Module pur sans I/O, trivialement testable.

#### Composant 4 : `app/analysis/baselines.py` — étendu

```python
MIN_SAMPLE_COUNT = 30

def compute_baselines_by_bucket(
    route_key_prefix: str,  # e.g. "CDG-LIS"
    observations: list[dict],  # each: {price, trip_duration_days, stops, duration_minutes}
) -> list[dict]:
    """Group observations by bucket, apply stops filter, return one baseline per bucket
    that meets MIN_SAMPLE_COUNT. Uses MEDIAN for avg_price (robust to outliers)."""
```

- Groupe les observations par bucket via `bucket_for_duration`
- Pour chaque bucket, applique la règle stops via `is_short_haul` + `stops_allowed`
- Si le bucket a au moins 30 observations valides, calcule médiane et std_dev
- Retourne 0 à 3 baselines par appel (selon ce qui passe les filtres)
- Le nom de colonne `avg_price` est conservé (rétro-compatibilité avec `detect_anomaly` et le frontend)

La fonction `compute_baseline` originale est conservée pour ne pas casser le code legacy qui pourrait encore l'utiliser pendant la transition.

#### Composant 5 : `app/scraper/reverify.py` — nouveau module

```python
async def reverify_flight_price(flight: dict) -> bool:
    """Re-fetch the same route from Travelpayouts and verify:
    - The flight is still in the API response
    - The price is still <= flight['price'] * 1.05 (5% tolerance)

    Returns True if the deal is still valid, False otherwise.
    Returns False on any API error (better safe than sorry)."""
```

Logique :
1. Appelle `get_prices_for_dates(origin, destination)` pour la route du flight
2. Cherche un match sur `(departure_date, return_date, airline)` dans les résultats
3. Si trouvé et `result.price <= flight.price * 1.05` → True
4. Sinon → False
5. Toute exception → False
6. Logge le résultat avec contexte (route, prix initial, prix re-vérifié, décision)

#### Composant 6 : `app/scheduler/jobs.py` — `_analyze_new_flights` réécrit

Pseudo-code :

```python
async def _analyze_new_flights(flights: list[dict]):
    if not db:
        return
    for flight in flights:
        bucket = bucket_for_duration(flight.get("trip_duration_days") or 0)
        if not bucket:
            continue

        # If duration_minutes is missing, treat as short-haul (strictest rule, 0 stops max)
        # to avoid false positives on legacy rows without this field.
        duration_minutes = flight.get("duration_minutes") or 0
        max_stops = stops_allowed(duration_minutes)
        if (flight.get("stops") or 0) > max_stops:
            continue

        route_key = f"{flight['origin']}-{flight['destination']}-bucket_{bucket}"
        baseline_resp = db.table("price_baselines").select("*").eq("route_key", route_key).eq("type", "flight").execute()
        if not baseline_resp.data:
            continue

        baseline = baseline_resp.data[0]
        if (baseline.get("sample_count") or 0) < 30:
            continue

        anomaly = detect_anomaly(price=flight["price"], baseline=baseline)
        if not anomaly or anomaly.discount_pct < 20 or anomaly.z_score < 2.0:
            continue

        if not await reverify_flight_price(flight):
            logger.info(f"Reverify rejected {flight['origin']}->{flight['destination']} @{flight['price']}€")
            continue

        tier = "premium" if anomaly.discount_pct >= 40 else "free"
        score = compute_score(
            discount_pct=anomaly.discount_pct,
            destination_code=flight["destination"],
            date_flexibility=0,
            accommodation_rating=None,
        )

        db.table("qualified_items").insert({
            "type": "flight",
            "item_id": flight.get("id", ""),
            "price": anomaly.price,
            "baseline_price": anomaly.baseline_price,
            "discount_pct": anomaly.discount_pct,
            "score": score,
            "tier": tier,
            "status": "active",
        }).execute()

        await _compose_packages_for_flight(flight, baseline)
```

#### Composant 7 : `app/scheduler/jobs.py` — `job_travelpayouts_enrichment` étendu

Le job actuel calcule des baselines au format legacy via `month-matrix`. On l'étend pour qu'il calcule aussi (ou principalement) les baselines `bucket_*` :

```python
async def job_travelpayouts_enrichment():
    # Pour chaque (origin, destination) pertinent :
    #   1. Appeler get_prices_for_dates pour récupérer ~30 observations historiques
    #   2. Construire les 3 baselines bucket via compute_baselines_by_bucket
    #   3. Upsert dans price_baselines
```

Le job continue à tourner 1×/jour à 4h UTC. Il est aussi ajouté à la whitelist de `/api/trigger` (cf composant 8) pour pouvoir le déclencher manuellement post-deploy.

#### Composant 8 : `app/api/routes.py` — whitelist trigger

Ajouter `travelpayouts_enrichment` à la liste des jobs triggerables manuellement :

```python
jobs = {
    "scrape_flights": job_scrape_flights,
    "scrape_accommodations": job_scrape_accommodations,
    "recalculate_baselines": job_recalculate_baselines,
    "expire_stale_data": job_expire_stale_data,
    "travelpayouts_enrichment": job_travelpayouts_enrichment,
}
```

#### Composant 9 : `app/notifications/telegram.py` — alertes free tier

`send_deal_alert` reçoit un nouveau paramètre `tier` (free/premium) :

- **Premium** : message actuel avec lien direct de réservation
- **Free** : message avec mention « Deal -X% détecté — créez un compte premium pour réserver » + lien vers la page de pricing

Le branchement se fait dans `_compose_packages_for_flight` qui passe `tier` à l'appel `send_deal_alert`.

## Gestion d'erreurs

| Couche | Cas d'erreur | Comportement |
|---|---|---|
| API | Timeout / 5xx / JSON invalide | log warning, retourne `[]`, no exception |
| API | `success: false` | log warning, retourne `[]` |
| Scraping route | Exception inattendue | catch dans `scrape_flights_for_airport`, errors++ |
| Normalisation | Durée hors [1, 21] | return None (skip silencieux) |
| Normalisation | Prix <= 0 ou departure_at manquant | return None |
| Analyse | Pas de baseline pour le bucket | skip silencieux |
| Analyse | sample_count < 30 | skip silencieux |
| Analyse | discount_pct < 20 ou z < 2 | skip silencieux |
| Revérification | Erreur API | return False, deal rejeté |
| Revérification | Vol disparu de l'API | return False, deal rejeté |
| Revérification | Prix > 105% du prix initial | return False, deal rejeté |
| Compute baselines | Bucket avec < 30 obs | bucket pas publié, autres buckets de la route peuvent réussir |

**Principe directeur** : en cas de doute, on rejette le deal silencieusement plutôt que d'envoyer une fausse alerte.

## Volume et performance

- **API calls flights/cron** : ~17 destinations × 2 airports × 1 appel = ~34 appels
- **API calls flights/jour** : ~200 (6 crons × 34)
- **API calls revérification/jour** : estimés 10-50 (un appel par deal qualifié, qui sont rares)
- **API calls enrichment/jour** : ~140 (1 par route MVP)
- **Total** : ~400 appels/jour
- **Rate limit Travelpayouts** : ~1 req/sec, soit ~86k/jour théorique
- **Marge** : ×200, aucun risque de throttling
- **Coût** : 0 €/mois

## Tests

### Tests purs (sans I/O)

`backend/tests/test_buckets.py` (nouveau, ~7 tests) :
- `test_bucket_for_duration_short` (1, 2, 3 → "short")
- `test_bucket_for_duration_medium` (4, 7, 9 → "medium")
- `test_bucket_for_duration_long` (10, 15, 21 → "long")
- `test_bucket_for_duration_outside_range` (0, 22, 56 → None)
- `test_is_short_haul_threshold` (179 → True, 180 → False)
- `test_stops_allowed_short_haul` (→ 0)
- `test_stops_allowed_long_haul` (→ 1)

`backend/tests/test_baselines.py` (étendu, ~6 tests) :
- `test_groups_observations_by_bucket`
- `test_uses_median_not_mean`
- `test_excludes_short_haul_with_stops`
- `test_excludes_long_haul_with_2_plus_stops`
- `test_minimum_sample_count_not_met` (29 obs → pas publié)
- `test_minimum_sample_count_met` (30 obs → publié)

`backend/tests/test_travelpayouts_flights.py` (étendu, ~8 nouveaux tests pour `_normalize_priced_entry`) :
- `test_rejects_duration_outside_range`
- `test_rejects_zero_duration`
- `test_extracts_trip_duration_days`
- `test_extracts_stops_from_transfers`
- `test_extracts_duration_minutes_average`
- `test_uses_origin_airport_not_city`
- `test_uses_api_link_when_present`
- `test_falls_back_to_built_url_when_link_missing`

### Tests avec mocks httpx

`backend/tests/test_travelpayouts.py` (étendu, ~4 nouveaux tests) :
- `test_get_prices_for_dates_parses_response`
- `test_get_prices_for_dates_handles_empty_data`
- `test_get_prices_for_dates_handles_unsuccessful_response`
- `test_get_prices_for_dates_includes_one_way_false_param`

`backend/tests/test_reverify.py` (nouveau, ~7 tests) :
- `test_returns_true_when_price_unchanged`
- `test_returns_true_when_price_decreased`
- `test_returns_true_within_5pct_tolerance` (100 → 104 → True)
- `test_returns_false_above_5pct_tolerance` (100 → 106 → False)
- `test_returns_false_when_flight_disappeared`
- `test_returns_false_on_api_error`
- `test_logs_decision_for_observability`

### Tests d'intégration light

`backend/tests/test_jobs.py` (étendu, ~8 nouveaux tests pour `_analyze_new_flights`) :
- `test_skips_flights_outside_duration_buckets`
- `test_skips_flights_violating_stops_rule`
- `test_uses_correct_bucket_baseline`
- `test_skips_when_no_baseline_for_bucket`
- `test_skips_when_baseline_sample_count_too_low`
- `test_assigns_free_tier_for_20_to_39_pct`
- `test_assigns_premium_tier_for_40_plus_pct`
- `test_skips_when_reverify_returns_false`

### Smoke test live (manuel)

Après le déploiement, lancer :

```bash
python -c "
from app.scraper.travelpayouts_flights import scrape_flights_for_route
flights = scrape_flights_for_route('CDG', 'BCN')
print(f'{len(flights)} flights')
durations = sorted(set(f['trip_duration_days'] for f in flights))
print(f'Durations: {durations}')
stops = sorted(set(f['stops'] for f in flights))
print(f'Stops: {stops}')
"
```

Critères :
- Toutes les durées dans `[1, 21]`
- Toutes les stops dans `{0, 1}` (les 2+ rejetés)
- Au moins ~10 vols par route
- `source_url` est cliquable

## Migration en production

1. Migration SQL idempotente appliquée via `backend/supabase/migrations/`
2. Merge de la PR → Railway redéploie automatiquement
3. Trigger manuel `POST /api/trigger/travelpayouts_enrichment` (X-Admin-Key) pour construire immédiatement les baselines bucket
4. Attendre le prochain cron `scrape_flights` (max 4h) ou trigger manuel
5. Vérifier les métriques de succès (cf section suivante)

## Métriques de succès post-deploy

À surveiller dans les 24h :

1. `/api/status` → `recent_scrapes[0].items_count > 0` et `errors_count == 0`
2. `SELECT MIN(trip_duration_days), MAX(trip_duration_days) FROM raw_flights WHERE scraped_at > NOW() - INTERVAL '1 hour'` → entre 1 et 21
3. `/api/status` → `active_baselines` > 246 (croissance significative grâce aux nouvelles baselines bucket)
4. `/api/qualified-items?type_filter=flight` → au moins 1 item après le prochain cron complet
5. Logs Railway : ratio `reverify` accept/reject raisonnable (ni 100% ni 0%)
6. Pas de spam Telegram : si des alertes free tier partent, elles correspondent à de vraies bonnes affaires

## Plan de rollback

Si problème post-deploy :
1. `git revert <merge-sha>` sur main
2. `git push` → Railway redéploie l'ancienne version
3. Le pipeline revient à l'état actuel (scrape OK, 0 deals qualifiés)

Aucune intervention DBA nécessaire — la migration SQL est purement additive (colonnes nullable, defaults). Les anciennes baselines `-1m/-3m/-6m` n'ont jamais été touchées et continuent d'exister.

## Hors scope (chantiers séparés)

- **Hôtels** : `accommodations.py` continue à utiliser Apify + Playwright. Migration vers Hotellook/Travelpayouts dans une PR ultérieure.
- **Affiliation** : pas de marker affilié dans cette PR. À ajouter dans `_normalize_priced_entry` (1 ligne) quand le compte affilié sera créé.
- **Cleanup baselines legacy** : les `-1m/-3m/-6m` sont laissées en base (dead data, sans impact).
- **Suppression du code calendar** : `get_calendar_prices` est conservé temporairement (pas appelé) pour faciliter le rollback. Suppression dans une PR de cleanup ultérieure.
- **Augmentation du volume scraping** (plus d'airports, crons plus fréquents) : à traiter séparément.
- **Bucketing dynamique** ou **prix au jour** : décisions futures basées sur les retours utilisateurs.
