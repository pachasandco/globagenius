# Globe Genius — Pipeline de Donnees (MVP)

**Date :** 2026-04-07
**Statut :** Valide
**Perimetre :** Backend Python — scraping, analyse de prix, composition de packages, notifications Telegram

---

## 1. Contexte

Globe Genius est une web app SaaS qui detecte des packages voyage (vols + hebergements) a prix casses (-40% minimum vs marche). Le pipeline de donnees est le premier sous-systeme a implementer : sans donnees, ni les agents IA ni le dashboard n'ont de contenu.

## 2. Architecture

### 2.1 Vue d'ensemble

Worker Python unique (FastAPI + APScheduler) qui orchestre :
1. **Scraping** — Apify SDK Python execute des actors pour vols et hebergements
2. **Normalisation** — Nettoyage, deduplication, insertion Supabase
3. **Analyse** — Baselines de prix 30j, detection d'anomalies par z-score
4. **Composition** — Association vols + hebergements en packages qualifies
5. **Notification** — Alertes Telegram (utilisateurs + admin)

### 2.2 Stack technique

| Composant | Technologie |
|-----------|-------------|
| Framework API | FastAPI + Uvicorn |
| Scheduler | APScheduler |
| Scraping | apify-client (Python SDK) |
| Base de donnees | Supabase (PostgreSQL) |
| Notifications | python-telegram-bot |
| Calculs statistiques | numpy |
| HTTP client | httpx |
| Deploiement | Railway ou Render |

### 2.3 Diagramme de flux

```
Scheduler (APScheduler)
    │
    ├──[toutes les 2h]──▶ Scraper Vols ──▶ Normalizer ──▶ Supabase (raw_flights)
    │                                                           │
    ├──[toutes les 4h]──▶ Scraper Hebergements ──▶ Normalizer ──▶ Supabase (raw_accommodations)
    │                                                           │
    ├──[toutes les 24h]──▶ Baseline Calculator ◀────────────────┘
    │                           │
    │                           ▼
    │                     price_baselines
    │                           │
    └──[post-scrape]──▶ Anomaly Detector ──▶ Package Composer ──▶ Telegram Notifier
                              │                     │
                              ▼                     ▼
                        qualified_items          packages
```

## 3. Schema de base de donnees

### 3.1 `raw_flights`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | Identifiant unique |
| hash | varchar UNIQUE | SHA256 deduplication |
| origin | varchar(3) | Code IATA depart |
| destination | varchar(3) | Code IATA arrivee |
| departure_date | date | Date de depart |
| return_date | date | Date de retour |
| price | decimal | Prix en EUR |
| airline | varchar | Compagnie aerienne |
| stops | int | Nombre d'escales |
| source_url | text | Deep link reservation |
| source | varchar | skyscanner, google_flights, kayak |
| scraped_at | timestamptz | Moment du scraping |
| expires_at | timestamptz | scraped_at + 2h |

### 3.2 `raw_accommodations`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | Identifiant unique |
| hash | varchar UNIQUE | SHA256 deduplication |
| city | varchar | Ville destination |
| name | varchar | Nom hotel/logement |
| price_per_night | decimal | Prix par nuit EUR |
| total_price | decimal | Prix total sejour |
| rating | decimal | Note sur 5 |
| check_in | date | Date d'arrivee |
| check_out | date | Date de depart |
| source_url | text | Deep link reservation |
| source | varchar | booking, airbnb, hotels_com |
| scraped_at | timestamptz | Moment du scraping |
| expires_at | timestamptz | scraped_at + 2h |

### 3.3 `price_baselines`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | |
| route_key | varchar UNIQUE | "CDG-LIS" ou "lisbon-booking" |
| type | varchar | flight / accommodation |
| avg_price | decimal | Moyenne ponderee 30j |
| std_dev | decimal | Ecart-type |
| sample_count | int | Nombre d'observations |
| calculated_at | timestamptz | Dernier recalcul |

### 3.4 `packages`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | |
| flight_id | uuid FK | → raw_flights |
| origin | varchar(3) | Aeroport depart |
| destination | varchar(3) | Aeroport arrivee |
| departure_date | date | |
| return_date | date | |
| flight_price | decimal | Prix vol |
| accommodation_id | uuid FK | → raw_accommodations |
| accommodation_price | decimal | Prix hebergement total |
| total_price | decimal | Prix total package |
| baseline_total | decimal | Prix reference marche |
| discount_pct | decimal | Remise en % |
| score | int | Score 0-100 |
| status | varchar | active / expired |
| created_at | timestamptz | |
| expires_at | timestamptz | |

### 3.5 `qualified_items`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | |
| type | varchar | flight / accommodation |
| item_id | uuid | FK vers raw_flights ou raw_accommodations |
| price | decimal | Prix actuel |
| baseline_price | decimal | Prix baseline |
| discount_pct | decimal | Remise en % |
| score | int | Score 0-100 |
| status | varchar | active / expired |
| created_at | timestamptz | |

### 3.6 `scrape_logs`

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | |
| actor_id | varchar | ID actor Apify |
| source | varchar | Nom de la source |
| type | varchar | flights / accommodations |
| items_count | int | Nombre de resultats |
| errors_count | int | Nombre d'erreurs |
| duration_ms | int | Duree d'execution |
| status | varchar | success / partial / failed |
| started_at | timestamptz | |
| completed_at | timestamptz | |

### 3.7 `telegram_subscribers` (MVP simplifie)

| Colonne | Type | Description |
|---------|------|-------------|
| id | uuid PK | |
| chat_id | bigint UNIQUE | ID chat Telegram |
| airport_code | varchar(3) | Aeroport de depart |
| min_score | int DEFAULT 50 | Score minimum pour alertes |
| created_at | timestamptz | |

## 4. Logique metier

### 4.1 Scraping

**Aeroports MVP :** CDG, ORY, LYS, MRS, NCE, BOD, NTE, TLS

**Flow par job :**
1. Pour chaque aeroport, lancer l'actor Apify (origin, dates J+15 → J+90, destinations ouvertes)
2. Polling SDK avec timeout 10 min
3. Recuperer le dataset JSON
4. Normaliser : conversion EUR, nettoyage champs, generation hash SHA256 (`origin|destination|departure_date|return_date|price|source`)
5. Upsert Supabase (skip doublons via hash)
6. Logger dans `scrape_logs`
7. Declencher analyse d'anomalies sur les nouvelles donnees

### 4.2 Baselines (recalcul 24h)

Pour chaque route et chaque hebergement :
- Requete sur les 30 derniers jours de donnees
- Moyenne ponderee : poids = `1 / age_en_jours` (donnees recentes pesent plus)
- Ecart-type sur les memes observations
- Minimum 10 observations pour qu'une baseline soit valide

### 4.3 Detection d'anomalies

Pour chaque nouvelle donnee post-scrape :
```
z_score = (baseline_price - current_price) / std_dev
discount_pct = (baseline_price - current_price) / baseline_price * 100
```
- **z_score > 2.0** ET **discount_pct >= 40%** → item qualifie
- Pas de baseline valide → skip

### 4.4 Scoring (0-100)

| Critere | Poids | Calcul |
|---------|-------|--------|
| Remise % | 50% | `min(discount_pct / 60 * 100, 100)` |
| Popularite destination | 20% | Volume historique normalise 0-100 |
| Flexibilite dates retour | 15% | Nombre d'alternatives prix similaire |
| Note hebergement | 15% | `(rating / 5) * 100` |

### 4.5 Composition des packages

Pour chaque vol qualifie :
1. Chercher hebergements : meme ville destination, check_in = jour d'arrivee, check_out = jour de retour
2. Filtrer : note >= 4.0, donnees fraiches (< 2h)
3. Calculer total = flight_price + accommodation_total_price
4. Comparer au baseline total (flight_baseline + accommodation_baseline)
5. Remise totale >= 40% → creer package, calculer score
6. Garder les 2-3 meilleurs hebergements par vol (meilleur score)

### 4.6 Expiration

Job toutes les 30 min : passer `status = 'expired'` pour tout package/item dont `expires_at < now()`.

## 5. Notifications Telegram

### 5.1 Alertes utilisateur

**Immediates (score >= 70) :**
```
✈️ GLOBE GENIUS DEAL ALERT

🌍 Paris CDG → Lisbonne LIS
📅 Depart : 25/04 | Retour : 02/05
🏨 Hotel Lisboa Plaza ⭐ 4.3/5
💰 Total : 509€  |  🔥 -48% vs marche
🎯 Score : 84/100

👉 Vol : [lien]
👉 Hotel : [lien]
```

**Digest quotidien (8h00, score >= 50) :** Top 5 deals du jour par score.

### 5.2 Canal admin

**Rapport quotidien (9h00) :**
```
📊 GLOBE GENIUS — Rapport [date]

Scrapes : X vols ✅ | Y hebergements ✅
Donnees : N vols | M hebergements
Erreurs : E
Packages qualifies : P (taux : T%)
Alertes envoyees : A
Baselines actives : B routes

⚠️ [alertes si seuils depasses]
```

**Alertes temps reel :**
- Source sans donnees > 3h
- Taux erreur > 10% sur 1h glissante
- Taux qualification < 5%

## 6. API Endpoints

| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/health` | Health check |
| GET | `/api/status` | Metriques pipeline (dernier scrape, stats, erreurs) |
| POST | `/api/trigger/{job}` | Lancement manuel d'un job (debug) |
| GET | `/api/packages` | Liste packages actifs (pour futur frontend) |
| GET | `/api/packages/{id}` | Detail d'un package |
| GET | `/api/qualified-items` | Items seuls qualifies |

## 7. Variables d'environnement

```
APIFY_API_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
APP_ENV=development
SCRAPE_FLIGHTS_INTERVAL_HOURS=2
SCRAPE_ACCOMMODATIONS_INTERVAL_HOURS=4
BASELINE_RECALC_HOUR=3
DIGEST_HOUR=8
MIN_DISCOUNT_PCT=40
MIN_SCORE_ALERT=70
MIN_SCORE_DIGEST=50
DATA_FRESHNESS_HOURS=2
MVP_AIRPORTS=CDG,ORY,LYS,MRS,NCE,BOD,NTE,TLS
```

## 8. Structure du projet

```
globegenius/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── scraper/
│   │   │   ├── __init__.py
│   │   │   ├── apify_client.py
│   │   │   ├── flights.py
│   │   │   ├── accommodations.py
│   │   │   └── normalizer.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── baselines.py
│   │   │   ├── anomaly_detector.py
│   │   │   └── scorer.py
│   │   ├── composer/
│   │   │   ├── __init__.py
│   │   │   └── package_builder.py
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   └── telegram.py
│   │   ├── scheduler/
│   │   │   ├── __init__.py
│   │   │   └── jobs.py
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
├── docs/
└── .gitignore
```

## 9. Deploiement

| Service | Plateforme | Notes |
|---------|------------|-------|
| Backend Python | Railway ou Render | Service web always-on (scheduler) |
| PostgreSQL | Supabase | Plan gratuit MVP |
| Frontend Next.js | Vercel | Phase 2 |
| Telegram Bot | Dans le process FastAPI | Meme service |

## 10. Mapping IATA → Ville

Le schema `raw_flights` stocke un code IATA destination, tandis que `raw_accommodations` stocke un nom de ville. Pour associer les deux lors de la composition des packages, un dictionnaire statique `IATA_TO_CITY` est maintenu dans `config.py` :

```python
IATA_TO_CITY = {
    "LIS": "Lisbon", "BCN": "Barcelona", "FCO": "Rome",
    "ATH": "Athens", "NAP": "Naples", "OPO": "Porto",
    # ... complete au fur et a mesure des destinations detectees
}
```

Le normalizer des hebergements normalise aussi le champ `city` pour matcher ces valeurs.

## 11. Limites et decisions explicites

- **Pas d'OpenClaw au MVP** — monitoring via scrape_logs + alertes Telegram admin. OpenClaw en phase 2.
- **Pas d'agents IA au MVP pipeline** — le pipeline est algorithmique. Les agents Claude (orchestrateur, compositeur) viendront en phase 2 pour enrichir l'analyse.
- **Popularite destination** — au MVP, table statique de popularite par destination (basee sur des donnees publiques). Sera remplacee par des donnees reelles en phase 2.
- **Flexibilite dates** — comptee comme le nombre de dates retour alternatives dans les donnees scrapees pour la meme route avec un prix dans +/- 10%.
- **Telegram subscribers** — table simplifiee sans lien users. L'association user ↔ chat_id viendra avec le frontend.
