# Migration du scraping vers Travelpayouts

**Date** : 2026-04-12
**Statut** : Validé pour implémentation
**Contexte** : Le scraping Google Flights via Playwright est cassé en production (Chromium ne se lance plus sur Railway), et le fallback Apify est épuisé (quota mensuel atteint). Aucun deal n'est inséré depuis le 11/04 ~16h.

## Objectif

Remplacer Google Flights (Playwright + Apify) par l'API Travelpayouts comme **source unique** de prix de vol. Travelpayouts est gratuit, stable, et déjà partiellement intégré dans le projet.

## Décisions clés

- **Suppression de Playwright et Apify pour le scrape vol uniquement** (le scrape hôtel `accommodations.py` continue à utiliser ces deux dépendances tant qu'on n'aura pas migré les hôtels — autre projet)
- **Travelpayouts = source unique** des prix vol (pas de fallback navigateur)
- **Long-courrier uniquement depuis CDG**, court/moyen courrier depuis les 8 airports MVP
- **Pas de marker affilié** dans cette première itération (ajout possible plus tard)
- **Saisonnalité conservée** : `route_selector` filtre les destinations selon la saison courante

## Périmètre des routes

### Court/moyen courrier (8 airports × destinations Europe + Maghreb)
Airports : `CDG, ORY, LYS, MRS, NCE, BOD, NTE, TLS`
Destinations Europe : `LIS, ATH, PRG, BCN, BUD, OPO, NAP, DBV, AMS, FCO, BER, MAD, VCE, SPU, EDI, IST`
Destinations Maghreb : `RAK, CMN, TUN`
→ ~136 routes max, filtrées par `route_selector` selon saison.

### Long-courrier (CDG uniquement)
Union de toutes les saisons : `NRT, JFK, BKK, YUL, DXB, MIA, SYD, CUN, PUJ, MLE, MRU, RUN, GIG, LAX`
→ 14 destinations max, filtrées par `route_selector` (~5-7 actives par saison).

**Total : ~150 routes max, ~140 actives par saison.**

## Architecture

### Nouveau module `app/scraper/travelpayouts_flights.py`

Responsabilité unique : récupérer les prix vol depuis Travelpayouts et les normaliser au format `raw_flights`.

Fonctions :

- `get_calendar_prices(origin, destination, depart_month="")` (dans `app/scraper/travelpayouts.py`)
  Appelle `/v1/prices/calendar`. Le paramètre `depart_month` est optionnel : sans lui, l'API renvoie sa fenêtre cachée complète (typiquement 6 à 9 mois) en un seul appel, avec ~30 à 50 dates uniques.

- `scrape_flights_for_route(origin, destination) -> list[dict]`
  **Un seul appel** à `get_calendar_prices` (sans `depart_month`) suffit pour récupérer toutes les dates cachées par l'API. Les premiers tests prévoyaient 3 appels mensuels (M+1, M+2, M+3) mais le smoke test en local a révélé que l'endpoint ignore le filtre `depart_date` : les 3 appels renvoyaient le même catalogue. Un appel unique → ~30-50 vols par route, 3x moins de quota et 3x plus rapide.

- `scrape_flights_for_airport(origin) -> list[dict]`
  Itère sur les destinations retournées par `route_selector` (en filtrant les long-courriers si origin ≠ CDG).

- `scrape_all_flights() -> tuple[list[dict], int, list[dict]]`
  Conserve la signature actuelle (`flights, errors, baselines`) pour rester drop-in compatible avec `job_scrape_flights`.
  Itère sur les airports MVP, applique la rotation existante (`AIRPORTS_PER_CYCLE`).

### Mapping des données Travelpayouts → `raw_flights`

L'API renvoie pour chaque jour :
```json
{
  "origin": "PAR",        // ville, pas airport
  "destination": "NYC",   // ville, pas airport
  "airline": "SV",
  "departure_at": "2026-05-05T08:25:00+02:00",
  "return_at": "2026-05-12T15:25:00+07:00",
  "expires_at": "2026-04-12T10:04:44Z",
  "price": 578,
  "flight_number": 130,
  "transfers": 1
}
```

Mapping :
- `origin` (raw_flights) ← l'airport demandé (CDG, LYS...) — **on garde le code airport, pas la ville**, car l'utilisateur s'abonne par airport
- `destination` ← le code IATA airport demandé
- `price` ← `value` (calendar) ou `price` (cheap)
- `departure_date` ← `departure_at`[:10]
- `return_date` ← `return_at`[:10] si présent, sinon `departure_date + 7j` (durée par défaut)
- `airline` ← `airline`
- `stops` ← `transfers` (calendar) ou `number_of_changes` (month-matrix)
- `source` ← `"travelpayouts"`
- `source_url` ← lien Aviasales construit (sans marker pour l'instant)
- `expires_at` ← `expires_at` de l'API si présent, sinon now + 24h

### Suppression du code obsolète

Fichiers supprimés (vol-only, hôtels hors scope) :
- `backend/app/scraper/browser/google_flights.py`
- `backend/app/scraper/flights.py` (remplacé par `travelpayouts_flights.py`)

Fichiers **conservés** car utilisés par le scrape hôtels (hors scope) :
- `backend/app/scraper/apify_client.py` — encore utilisé par `accommodations.py:_scrape_city_apify`
- `backend/app/scraper/browser/google_hotels.py` — utilisé par `accommodations.py:_scrape_city_playwright`
- `backend/app/scraper/browser/stealth.py` — dépendance de `google_hotels.py`
- `playwright` dans requirements.txt et Dockerfile — encore utilisé par `google_hotels.py`
- `apify-client` dans requirements.txt — encore utilisé par `accommodations.py`

Fichiers modifiés :
- `backend/app/scheduler/jobs.py` :
  - L1.5 : `from app.scraper.travelpayouts_flights import scrape_all_flights` (était `from app.scraper.flights import scrape_all_flights`)
  - L132, L282, L496 : `from app.scraper.travelpayouts_flights import _window_label` (était `from app.scraper.flights import _window_label`) — la fonction `_window_label` est dupliquée à l'identique dans le nouveau module
- `backend/tests/` : adapter les tests de scraping vol

### Conservation

`job_travelpayouts_enrichment` (déjà existant dans `jobs.py:489`) **reste actif** : il enrichit les baselines via `month-matrix` une fois par jour. C'est complémentaire au scraping live et apporte la profondeur historique nécessaire à la détection d'anomalies.

## Flux de données

```
[cron 6×/jour]
  → job_scrape_flights (jobs.py)
  → travelpayouts_flights.scrape_all_flights()
  → pour chaque (airport, destination) :
       → calendar API (3 mois × 1 appel = 3 appels)
       → ~90 raw_flights par route
  → upsert raw_flights (Supabase)
  → _analyze_new_flights (existant, inchangé)
       → lookup baseline → detect_anomaly → score → qualified_items → packages
```

```
[cron 1×/jour à 4h]
  → job_travelpayouts_enrichment (existant, inchangé)
  → month-matrix → calcul baselines → upsert price_baselines
```

## Volume et rate limit

Mesuré localement après le fix single-call :

- 1 airport × 17 destinations × 1 appel = ~17 appels par airport
- `AIRPORTS_PER_CYCLE = 2` → ~34 appels par cron
- 6 crons/jour → **~200 appels/jour pour les vols**
- À cela s'ajoute `job_travelpayouts_enrichment` (1×/jour) qui appelle `month-matrix` pour ~140 routes
- **Total : ~340 appels/jour**
- Rate limit Travelpayouts : ~1 req/sec, donc ~86k appels/jour théoriques
- **Marge : ×250, aucun risque de throttling**

Smoke test mesuré le 12/04 : `scrape_all_flights()` complet (2 airports, ~17 destinations chacun) → 278 vols uniques, 0 erreur, 6 secondes.

Coût : **0 €/mois**.

## Gestion d'erreurs

- `httpx` timeout 15s déjà en place dans `travelpayouts.py`
- Si `_get` retourne `None` (erreur réseau, 5xx, JSON invalide) → la route est ignorée, l'erreur est loggée, `errors_count` incrémenté
- Si l'API retourne `data: {}` (pas de vols pour cette route ce mois-ci) → simplement ignoré, pas une erreur
- Le job termine avec `status: success` si `errors == 0`, `partial` sinon

## Tests

Tests créés (état final après implémentation) :

`backend/tests/test_travelpayouts.py` (7 tests pour `get_calendar_prices`) :
- parsing happy path, fallback sur la clé `day` quand `departure_at` absent
- réponses null/unsuccessful/empty → liste vide
- omission/inclusion de `depart_date` dans les params selon que `depart_month` est fourni

`backend/tests/test_travelpayouts_flights.py` (19 tests pour le scraper) :
- `_window_label` : 5 tests aux bornes (1m/2m/3m/4m/6m)
- `_normalize_calendar_entry` : mapping complet, fallback `return_at`, rejet de prix=0 et `departure_at` vide
- `_build_aviasales_url` : happy path + fallbacks
- `scrape_flights_for_route` : agrégation et skip des entries inutilisables
- `scrape_flights_for_airport` : filtrage long-courrier non-CDG, conservation depuis CDG, skip self
- `scrape_all_flights` : signature `(list, int, list)`, comptage des erreurs par airport

`backend/tests/test_route_selector.py` (4 tests pour `is_long_haul` / `LONG_HAUL_DESTINATIONS`).

**Total : 71 tests passent** (45 baseline conservés + 26 nouveaux).

## Migration en production

1. Merger le PR
2. Railway redéploie automatiquement
3. **Vérifier dans les logs** : prochaine exécution cron → cherche `travelpayouts_flights` au lieu de `BrowserType.launch`
4. **Vérifier `/api/status`** : `recent_scrapes[0].items_count > 0`
5. **Vérifier qu'on ne paie plus Apify** : désactiver le compte ou révoquer le token

## Hors scope (pour plus tard)

- **Marker affilié** : à ajouter quand le compte Travelpayouts/Aviasales est activé pour l'affiliation. Modification triviale dans `_build_source_url`.
- **Vérification ponctuelle via Playwright** : option C de la discussion initiale, abandonnée pour rester simple.
- **Endpoint `/v2/prices/special-offers`** : retourne du non-JSON, probablement déprécié. On retire son usage de `job_travelpayouts_enrichment`.
- **Hôtels** : le scraping hôtel via `accommodations.py` est inchangé, c'est une autre décision.
