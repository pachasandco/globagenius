# Migration du scraping vers Travelpayouts

**Date** : 2026-04-12
**Statut** : Validé pour implémentation
**Contexte** : Le scraping Google Flights via Playwright est cassé en production (Chromium ne se lance plus sur Railway), et le fallback Apify est épuisé (quota mensuel atteint). Aucun deal n'est inséré depuis le 11/04 ~16h.

## Objectif

Remplacer Google Flights (Playwright + Apify) par l'API Travelpayouts comme **source unique** de prix de vol. Travelpayouts est gratuit, stable, et déjà partiellement intégré dans le projet.

## Décisions clés

- **Suppression complète** de Playwright et Apify (code, dépendances, image Docker)
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

- `scrape_route_calendar(origin, destination, depart_month) -> list[dict]`
  Appelle `/v1/prices/calendar` pour récupérer un prix par jour de départ sur le mois. 1 appel = ~30 vols.

- `scrape_flights_for_route(origin, destination) -> list[dict]`
  Itère sur les mois cibles (M+1, M+2, M+3) et concatène les résultats. ~3 appels = ~90 vols par route.

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

Fichiers supprimés :
- `backend/app/scraper/apify_client.py`
- `backend/app/scraper/browser/google_flights.py`
- `backend/app/scraper/browser/google_hotels.py` (uniquement si non utilisé ailleurs — à vérifier)
- `backend/app/scraper/browser/stealth.py` (idem)
- `backend/app/scraper/browser/__init__.py` (si dossier vide après ménage)
- `backend/app/scraper/flights.py` (remplacé par le nouveau module `travelpayouts_flights.py`)

Fichiers modifiés :
- `backend/requirements.txt` : retirer `apify-client`, `playwright`
- `backend/Dockerfile` : retirer `RUN playwright install --with-deps chromium`
- `backend/app/scheduler/jobs.py` : `from app.scraper.travelpayouts_flights import scrape_all_flights` au lieu de `from app.scraper.flights import scrape_all_flights`
- `backend/app/api/routes.py` : si une route admin référence `flights.py` directement, mettre à jour
- `backend/tests/` : adapter les tests de scraping

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

- 8 airports × ~17 destinations × 3 mois = ~408 appels par cycle complet (1 cycle = 1 airport)
- En réalité avec `AIRPORTS_PER_CYCLE = 2` → ~816 appels par cron
- 6 crons/jour → **~4900 appels/jour**
- Rate limit Travelpayouts : ~1 req/sec, donc ~86k appels/jour théoriques
- **Marge : ×17, aucun risque de throttling**

Coût : **0 €/mois**.

## Gestion d'erreurs

- `httpx` timeout 15s déjà en place dans `travelpayouts.py`
- Si `_get` retourne `None` (erreur réseau, 5xx, JSON invalide) → la route est ignorée, l'erreur est loggée, `errors_count` incrémenté
- Si l'API retourne `data: {}` (pas de vols pour cette route ce mois-ci) → simplement ignoré, pas une erreur
- Le job termine avec `status: success` si `errors == 0`, `partial` sinon

## Tests

Tests à créer/adapter dans `backend/tests/test_travelpayouts_flights.py` :

1. `test_scrape_route_calendar_parses_response` — mock httpx, vérifie le mapping
2. `test_scrape_route_calendar_handles_empty_data` — réponse `{data: {}}` → liste vide
3. `test_scrape_route_calendar_handles_api_error` — httpx raise → liste vide, erreur loggée
4. `test_scrape_flights_for_route_iterates_months` — vérifie 3 appels (M+1, M+2, M+3)
5. `test_scrape_flights_for_airport_filters_long_haul` — depuis LYS, NRT/BKK/etc absents
6. `test_scrape_flights_for_airport_includes_long_haul_from_cdg` — depuis CDG, long-courriers présents
7. `test_normalize_calendar_entry_to_raw_flight` — mapping des champs
8. `test_scrape_all_flights_signature_compatible` — retourne `(list, int, list)` comme l'ancienne version

Tests existants à supprimer : tous ceux qui mockent Apify ou Playwright dans le pipeline vol.

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
