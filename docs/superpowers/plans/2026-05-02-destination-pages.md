# Destination pages SEO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pour chaque destination qui déclenche au moins une alerte Telegram, générer un guide voyage SEO de 2000 mots (style journaliste, voix `travel-journalist-writer`) + photo Unsplash, l'afficher sur une page publique `/destination/[iata]`, et la lier depuis la landing, la home logged-in, et chaque alerte Telegram.

**Architecture:** Génération **synchrone** juste avant l'envoi de la 1ʳᵉ alerte vers une destination donnée — l'alerte attend que l'article soit prêt (~30-60s), puis le lien Telegram pointe vers la page complète. Pas de batch initial : seules les destinations qui ont une alerte génèrent du contenu (zéro coût Anthropic gaspillé). Article stocké en DB Supabase, key sur IATA. Page Next.js publique pour le SEO. Si Anthropic plante, l'alerte part quand même et la page affiche juste les deals + photo (pas de loader, pas de "en cours").

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK (Claude Sonnet pour qualité), Unsplash API (gratuit, 50 req/h), Supabase Postgres, Next.js 16, React 19.

**Branch:** Ce plan s'exécute sur `v9`.

**Skill source de vérité pour l'écriture :** `/tmp/travel-skill/travel-journalist-writer/` (décompressé depuis `travel-journalist-writer.skill` à la racine du repo). Format **guide destination** uniquement, sous-format **Top X + Itinéraire J1-J3** mixé. Voir `references/format-guide.md` et `references/seo-blog.md`.

**Variables d'env requises sur Railway prod (à confirmer Phase 0) :**
- `ANTHROPIC_API_KEY` (déjà en place, vérifié)
- `UNSPLASH_ACCESS_KEY` (à créer/ajouter)

---

## File structure

| Fichier | Statut | Responsabilité |
|---|---|---|
| `backend/supabase/migrations/032_articles_iata_destination.sql` | create | Migration : ajouter colonnes `iata` (text unique nullable), `word_count` (int), et les nouveaux champs guide journaliste (`h1`, `meta_description`, `lead`, `nut_graf`, `top_picks jsonb`, `itinerary jsonb`, `infos_pratiques jsonb`, `faq jsonb`, `sources jsonb`) plus l'attribution Unsplash (`photographer_name`, `photographer_url`, `photo_id`). Index unique partiel sur `iata`. Garde la colonne `destination` (nom FR) et tout le legacy schema (intro/sections/subtitle/best_time/budget_tip) pour les 4 vieux articles. |
| `backend/app/agents/destination_writer.py` | create | Génère un article 2000 mots format guide via Claude Sonnet, suivant le skill `travel-journalist-writer`. Fonction principale `generate_destination_guide(iata: str) -> dict | None`. Appel synchrone (block ~30-60s). Retourne le dict prêt à insérer en DB ou None si échec. |
| `backend/app/notifications/unsplash.py` | create | Fetch une photo de couverture pour une destination via Unsplash API. `fetch_destination_photo(iata: str, query_hint: str) -> dict | None` retourne `{url, photo_id, photographer_name, photographer_url}`. Cache mémoire 24h pour éviter les appels redondants. |
| `backend/app/notifications/destination_articles.py` | create | Helper qui orchestre : check si l'article existe pour `iata`, sinon génère + stocke. `ensure_article_for_destination(iata: str) -> bool`. Pas async (sera appelé depuis le dispatch sync). |
| `backend/app/scheduler/jobs.py` | modify | Au moment du dispatch des alertes (round-trip grouped, oneway, combo), juste avant `bot.send_message`, appeler `ensure_article_for_destination(grp_dest)`. Best-effort : si génération échoue, l'alerte part quand même. |
| `backend/app/notifications/telegram.py` | modify | Dans `format_grouped_flight_alerts`, `format_oneway_deal_alert`, `format_split_ticket_alert` : ajouter une dernière ligne `📖 [Le guide de {dest_label}](https://globegenius.app/destination/{iata})` avant le bouton existant `Toutes les offres`. |
| `backend/app/api/routes.py` | modify | Nouveau endpoint public `GET /api/destinations/{iata}` qui renvoie l'article + photo + 5 deals actifs vers cette destination. Utilisé par la page Next.js publique. |
| `backend/tests/test_destination_writer.py` | create | TDD : génération mockée Claude, validation structure JSON retournée, gestion truncation, gestion API down. |
| `backend/tests/test_destination_article_helper.py` | create | TDD : `ensure_article_for_destination` skip si article existe déjà, écrit en DB si nouveau, retourne False si Anthropic plante. |
| `backend/tests/test_unsplash.py` | create | TDD : URL bien formée, photographer attribution, fallback si Unsplash plante. |
| `frontend/src/app/destination/[iata]/page.tsx` | create | Page Next.js publique qui rend l'article (markdown), la photo de couverture avec attribution, les deals actifs, les CTA signup (non-loggué) ou réservation (loggué). Server-side rendered (SSR). Sitemap-friendly. |
| `frontend/src/app/destination/[iata]/layout.tsx` | create | OG tags, Twitter cards, JSON-LD schema TouristDestination + FAQPage. Title et meta description issus de l'article. |
| `frontend/src/app/sitemap.ts` | modify (or create) | Ajoute toutes les destinations qui ont un article au sitemap.xml. Permet à Google de découvrir les pages. |
| `frontend/src/lib/api.ts` | modify | Helper `getDestinationGuide(iata: string)` qui fetch `/api/destinations/{iata}`. |
| `frontend/src/app/page.tsx` | modify | Sur la landing, ajoute une section "Nos guides destination" entre la stats bar et la 3-types section. Affiche 6 cards (les 6 dernières destinations alertées avec article). |
| `frontend/src/app/home/page.tsx` | modify | Chaque deal card devient cliquable → ouvre `/destination/{iata}` dans un nouvel onglet (ne casse pas le flow user logged-in). |
| `docs/runbooks/go-live.md` | modify | Ajouter section "Une page destination ne s'affiche pas" à la liste des incidents. |

---

## Phase 0 — Pré-flight (5 min)

### Task 0.1: Créer un compte Unsplash développeur + récupérer la clé

Action manuelle hors-code.

- [ ] **Step 1: S'inscrire sur Unsplash Developers**

Aller sur https://unsplash.com/developers → sign up → "New Application" → cocher les conditions → nommer l'app "Globe Genius" → URL `https://globegenius.app`.

- [ ] **Step 2: Copier l'Access Key**

Dans la page de l'app créée, section "Keys", copier la valeur "Access Key" (forme : `Abc123...XyZ`, ~43 caractères).

- [ ] **Step 3: Ajouter la clé sur Railway prod**

```bash
railway variables --service globagenius --environment production --set "UNSPLASH_ACCESS_KEY=<la clé copiée>"
```

Railway va redéployer automatiquement. Aucun code n'utilise encore cette clé, donc le redeploy est silencieux.

- [ ] **Step 4: Confirmer**

```bash
railway variables --service globagenius --environment production --kv 2>&1 | grep "^UNSPLASH_ACCESS_KEY=" | sed -E 's/=(.{15}).+/=\1***REDACTED***/'
```

Expected: une ligne `UNSPLASH_ACCESS_KEY=Abc123...***REDACTED***`.

### Task 0.2: Vérifier qu'Anthropic Sonnet est bien disponible

- [ ] **Step 1: Tester le client Anthropic en local**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -c "
from app.agents.llm_client import get_client
c = get_client()
if c is None:
    print('FAIL: ANTHROPIC_API_KEY missing')
else:
    r = c.messages.create(model='claude-sonnet-4-6', max_tokens=20, messages=[{'role':'user','content':'Dis bonjour en 5 mots.'}])
    print('OK:', r.content[0].text)
"
```

Expected: `OK: <réponse en 5 mots français>`.

Si l'erreur indique "model not found", utiliser `claude-haiku-4-5` à la place dans toutes les tâches qui réfèrent à Sonnet (Haiku reste suffisant pour 2000 mots de guide, juste moins de finesse littéraire).

---

## Phase 1 — Migration DB pour adapter `articles` (15 min)

### Task 1.1: Créer la migration 032

**Files:**
- Create: `backend/supabase/migrations/032_articles_iata_destination.sql`

- [ ] **Step 1: Créer le fichier**

Créer `backend/supabase/migrations/032_articles_iata_destination.sql` avec :

```sql
-- 032_articles_iata_destination.sql
-- V9 destination pages: index articles by IATA code (BCN, BKK, ...)
-- to match sent_alerts.destination, raw_flights.destination, etc.
-- The legacy `destination` column (FR name like "Marrakech") stays for
-- the 4 pre-existing articles. New articles MUST set both `iata` and
-- `destination`.
--
-- Also extends the schema with the journalist-style guide fields
-- (h1, meta_description, lead, nut_graf, top_picks, itinerary,
-- infos_pratiques, faq, sources, word_count) and Unsplash attribution
-- columns (photographer_name, photographer_url, photo_id). The legacy
-- columns (intro, sections, subtitle, best_time, budget_tip) are kept
-- so the 4 existing articles still render via /api/articles.

ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS iata text,
    ADD COLUMN IF NOT EXISTS word_count int,
    ADD COLUMN IF NOT EXISTS h1 text,
    ADD COLUMN IF NOT EXISTS meta_description text,
    ADD COLUMN IF NOT EXISTS lead text,
    ADD COLUMN IF NOT EXISTS nut_graf text,
    ADD COLUMN IF NOT EXISTS top_picks jsonb,
    ADD COLUMN IF NOT EXISTS itinerary jsonb,
    ADD COLUMN IF NOT EXISTS infos_pratiques jsonb,
    ADD COLUMN IF NOT EXISTS faq jsonb,
    ADD COLUMN IF NOT EXISTS sources jsonb,
    ADD COLUMN IF NOT EXISTS photographer_name text,
    ADD COLUMN IF NOT EXISTS photographer_url text,
    ADD COLUMN IF NOT EXISTS photo_id text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_iata_unique
    ON articles(iata)
    WHERE iata IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_articles_iata
    ON articles(iata)
    WHERE iata IS NOT NULL;
```

**Note for the implementer:** the legacy `articles` table (migration 003) had only `slug`, `destination`, `country`, `title`, `subtitle`, `intro`, `sections jsonb`, `best_time`, `budget_tip`, `tags`, `cover_photo`, `photo_query`, `generated_at`, `created_at`. We add the new columns *additively* — we do NOT drop the legacy ones, because the 4 existing articles (Marrakech, Lisbonne, Rome, Barcelone) still depend on `subtitle`, `intro`, `sections`, `best_time`, `budget_tip`. New articles populate the new columns and leave the legacy ones NULL. The legacy `/api/articles/generate` route keeps working.

- [ ] **Step 2: Appliquer en prod**

```bash
psql "$SUPABASE_URL" -f backend/supabase/migrations/032_articles_iata_destination.sql
```

Expected: `ALTER TABLE` `CREATE INDEX` `CREATE INDEX` (ou skip si déjà appliquée).

- [ ] **Step 3: Vérifier**

```bash
psql "$SUPABASE_URL" -c "\d articles" | grep -E "iata|word_count|h1|meta_description|lead|nut_graf|top_picks|itinerary|infos_pratiques|faq|sources|photographer"
```

Expected: 14 lignes pour les 14 colonnes ajoutées (`iata`, `word_count`, `h1`, `meta_description`, `lead`, `nut_graf`, `top_picks`, `itinerary`, `infos_pratiques`, `faq`, `sources`, `photographer_name`, `photographer_url`, `photo_id`).

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/032_articles_iata_destination.sql
git commit -m "db(migration): add iata + word_count columns to articles"
```

---

## Phase 2 — Helper Unsplash (30 min)

### Task 2.1: TDD — tests pour `unsplash.fetch_destination_photo`

**Files:**
- Create: `backend/tests/test_unsplash.py`

- [ ] **Step 1: Écrire les tests (failing)**

Créer `backend/tests/test_unsplash.py` :

```python
"""Tests for unsplash.fetch_destination_photo.

The helper hits the Unsplash search API to find a representative photo
for a destination. Returns a dict with the URL we'll embed and the
photographer attribution (legally required by Unsplash terms).
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _ok_response(items: list[dict]):
    """Build a fake httpx response with the Unsplash search payload."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"results": items}
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def test_returns_first_landscape_photo_when_results_present():
    """Happy path: API returns 3 photos, helper picks the first one and
    extracts URL + photographer name + profile URL."""
    from app.notifications.unsplash import fetch_destination_photo

    fake_payload = [
        {
            "id": "abc123",
            "urls": {"regular": "https://images.unsplash.com/photo-abc?w=1200"},
            "user": {
                "name": "Jane Doe",
                "links": {"html": "https://unsplash.com/@janedoe"},
            },
        },
        {
            "id": "def456",
            "urls": {"regular": "https://images.unsplash.com/photo-def?w=1200"},
            "user": {"name": "John Smith", "links": {"html": "https://unsplash.com/@john"}},
        },
    ]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _ok_response(fake_payload)

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("BCN", query_hint="Barcelona Spain")

    assert result is not None
    assert result["url"] == "https://images.unsplash.com/photo-abc?w=1200"
    assert result["photo_id"] == "abc123"
    assert result["photographer_name"] == "Jane Doe"
    assert result["photographer_url"] == "https://unsplash.com/@janedoe"


def test_returns_none_when_unsplash_returns_no_results():
    """Empty result set → None (no fallback to a default photo, the
    article page handles the missing-photo case in the UI)."""
    from app.notifications.unsplash import fetch_destination_photo

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = _ok_response([])

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("XXX", query_hint="Nonexistent")

    assert result is None


def test_returns_none_when_unsplash_api_raises():
    """A network/API error must not crash the caller — return None."""
    from app.notifications.unsplash import fetch_destination_photo

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = httpx.HTTPError("boom")

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        result = fetch_destination_photo("BCN", query_hint="Barcelona")

    assert result is None


def test_returns_none_when_access_key_missing():
    """No API key configured → no call, return None silently."""
    from app.notifications.unsplash import fetch_destination_photo

    with patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", ""):
        result = fetch_destination_photo("BCN", query_hint="Barcelona")

    assert result is None


def test_passes_query_hint_to_unsplash_search():
    """Verify the query string we send to Unsplash includes the hint
    (city name) — this is what makes results relevant."""
    from app.notifications.unsplash import fetch_destination_photo

    captured = {}
    def _capture_get(url, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params or {}
        captured["headers"] = headers or {}
        return _ok_response([{
            "id": "x",
            "urls": {"regular": "https://example.com/x"},
            "user": {"name": "A", "links": {"html": "https://unsplash.com/@a"}},
        }])

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = _capture_get

    with patch("app.notifications.unsplash.httpx.Client", return_value=mock_client), \
         patch("app.notifications.unsplash.settings.UNSPLASH_ACCESS_KEY", "test_key"):
        fetch_destination_photo("BCN", query_hint="Barcelona Spain travel")

    assert "Barcelona Spain travel" in captured["params"].get("query", "")
    # Authorization header carries the access key, prefixed with Client-ID
    auth = captured["headers"].get("Authorization", "")
    assert "Client-ID" in auth and "test_key" in auth
    # Filter on landscape orientation for cover photos
    assert captured["params"].get("orientation") == "landscape"
```

- [ ] **Step 2: Run pour vérifier que ça FAIL**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_unsplash.py -v
```

Expected: 5 fails (module n'existe pas).

### Task 2.2: Implémenter `unsplash.py`

**Files:**
- Create: `backend/app/notifications/unsplash.py`
- Modify: `backend/app/config.py` — ajouter `UNSPLASH_ACCESS_KEY`

- [ ] **Step 1: Ajouter la var d'env dans Settings**

Modifier `backend/app/config.py`. Trouver la section où sont déclarées les vars (autour de `BREVO_*`), insérer :

```python
    UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")
```

- [ ] **Step 2: Créer le module**

Créer `backend/app/notifications/unsplash.py` :

```python
"""Unsplash search helper for destination cover photos.

Hits the Unsplash search API and returns the first landscape result
along with photographer attribution (mandatory per Unsplash API terms:
https://help.unsplash.com/en/articles/2511315-guideline-attribution).

We don't use a CDN cache here — Unsplash URLs are themselves served
from a fast CDN, and we store the URL once in DB per destination so
each user-facing page makes zero Unsplash calls.
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"


def fetch_destination_photo(
    iata: str,
    query_hint: str,
    timeout: float = 8.0,
) -> Optional[dict]:
    """Return a dict with `url`, `photo_id`, `photographer_name`,
    `photographer_url` for the first landscape match, or None on any
    failure (no key, no result, network error).

    `query_hint` should be a search-friendly string like "Barcelona Spain"
    — Unsplash search ranks by relevance, so the more context the better.
    """
    if not settings.UNSPLASH_ACCESS_KEY:
        logger.info("UNSPLASH_ACCESS_KEY not set, skipping photo fetch for %s", iata)
        return None

    headers = {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}
    params = {
        "query": query_hint,
        "per_page": 5,
        "orientation": "landscape",
        "content_filter": "high",  # safe-search
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(UNSPLASH_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Unsplash search failed for %s: %s", iata, e)
        return None

    results = data.get("results") or []
    if not results:
        logger.info("Unsplash returned no results for %s (query=%s)", iata, query_hint)
        return None

    first = results[0]
    return {
        "url": first.get("urls", {}).get("regular", ""),
        "photo_id": first.get("id", ""),
        "photographer_name": first.get("user", {}).get("name", ""),
        "photographer_url": first.get("user", {}).get("links", {}).get("html", ""),
    }
```

- [ ] **Step 3: Run, verify PASS**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_unsplash.py -v
```

Expected: 5 passed.

- [ ] **Step 4: Smoke test contre l'API réelle (optionnel)**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && set -a && source .env && set +a && PYTHONPATH=. .venv/bin/python -c "
from app.notifications.unsplash import fetch_destination_photo
r = fetch_destination_photo('BCN', 'Barcelona Spain')
print(r)
"
```

Expected: dict avec `url` qui commence par `https://images.unsplash.com/`. Si UNSPLASH_ACCESS_KEY n'est pas dans `.env` local, retourne `None` (normal).

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/notifications/unsplash.py backend/tests/test_unsplash.py
git commit -m "feat(content): Unsplash photo fetcher with attribution"
```

---

## Phase 3 — Générateur d'article (1h)

### Task 3.1: TDD — tests pour `destination_writer.generate_destination_guide`

**Files:**
- Create: `backend/tests/test_destination_writer.py`

- [ ] **Step 1: Écrire les tests**

Créer `backend/tests/test_destination_writer.py` :

```python
"""Tests for destination_writer.generate_destination_guide.

The function calls Claude Sonnet (or Haiku as fallback) with a prompt
that follows the travel-journalist-writer skill's "guide destination"
format. Returns a dict with the structured article ready to be inserted
into the `articles` table.

Tests mock Anthropic so we never burn tokens in CI. The integration
with the real API is verified in Task 3.3 manual smoke.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _fake_anthropic_response(text: str, stop_reason: str = "end_turn"):
    """Build a fake Anthropic Message response carrying `text` as
    the assistant's content. We mimic the SDK's content[0].text shape."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    msg.stop_reason = stop_reason
    return msg


def _valid_guide_json() -> dict:
    """A minimal but valid guide JSON shape the prompt asks for."""
    return {
        "title": "Barcelone : guide complet pour un week-end réussi",
        "h1": "Barcelone en 3 jours : itinéraire d'un voyageur exigeant",
        "slug": "barcelone-3-jours-guide",
        "meta_description": "Itinéraire de 3 jours à Barcelone par quartier, adresses testées, budget réel et conseils pour éviter les pièges à touristes.",
        "lead": "Barcelone à 7h du matin, place de Catalunya...",
        "nut_graf": "Ce guide propose un itinéraire de 3 jours organisé par quartier...",
        "top_picks": [
            {"name": "MACBA", "angle": "le seul musée d'art contemporain de la ville",
             "description": "Fondé en 1995, le MACBA expose...",
             "practical": "Plaça dels Àngels 1 · 11h-19h, fermé mardi · 12 €"},
            {"name": "Cervecería Catalana", "angle": "tapas haut de gamme sans réservation",
             "description": "Comptoir et terrasse...",
             "practical": "Mallorca 236 · 9h-1h · plats 4-18 €"},
        ] * 4,  # 8 entries
        "itinerary": [
            {"day": 1, "title": "Gothic Quarter à pied",
             "morning": "9h-12h: Cathédrale et Plaça del Rei",
             "lunch": "Bar del Pla, plats 8-14 €",
             "afternoon": "14h-18h: Born et Picasso",
             "evening": "Tapas dans El Xampanyet",
             "lodging": "Hôtel mid-range à Born, 130 €",
             "rain_plan": "Musée Picasso", "budget_option": "Auberge Equity Point",
             "premium_option": "Hotel Neri 5*"},
            {"day": 2, "title": "Eixample moderniste", "morning": "Casa Batlló",
             "lunch": "Cervecería Catalana", "afternoon": "Sagrada Família",
             "evening": "Cava bar Cinc Sentits", "lodging": "Same",
             "rain_plan": "Casa Vicens", "budget_option": "Sandwich Conesa",
             "premium_option": "Restaurant Cinc Sentits"},
            {"day": 3, "title": "Park Güell + plage", "morning": "Park Güell",
             "lunch": "Pla dels Àngels", "afternoon": "Plage Barceloneta",
             "evening": "Vermouth à Sant Antoni", "lodging": "Same",
             "rain_plan": "Aquarium", "budget_option": "Pic-nic au parc",
             "premium_option": "Beach club W Hotel"},
        ],
        "infos_pratiques": {
            "best_season": "Mai-juin et septembre-octobre, 18-25°C",
            "how_to_get_there": "Vols Paris-BCN dès 35 € sur Vueling",
            "visa": "Aucun pour les ressortissants UE",
            "daily_budget_eco": "60 €", "daily_budget_comfort": "130 €", "daily_budget_premium": "300 €",
            "where_to_sleep": "Born (charme), Eixample (calme), Gràcia (local)",
            "to_avoid": "Las Ramblas en haute saison, restos sur la plage",
            "local_tips": "Tapas servies au comptoir = moins cher qu'en salle",
        },
        "faq": [
            {"q": "Combien de jours pour visiter Barcelone ?", "a": "3 à 4 jours suffisent pour les principaux quartiers."},
            {"q": "Quelle est la meilleure période ?", "a": "Mai-juin et septembre-octobre."},
            {"q": "Faut-il réserver la Sagrada Família à l'avance ?", "a": "Oui, billets coupe-file en ligne 1-2 semaines avant."},
        ],
        "sources": [
            "https://www.barcelonaturisme.com",
            "https://www.barcelona.cat",
        ],
        "tags": ["barcelone", "espagne", "weekend", "city-trip", "catalogne"],
        "photo_query": "Barcelona Spain travel",
    }


def test_generate_returns_structured_dict_on_happy_path():
    """When Claude returns valid JSON, we parse it and add the IATA + dates."""
    from app.agents import destination_writer

    raw_json = json.dumps(_valid_guide_json())
    fake_resp = _fake_anthropic_response(raw_json)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_resp

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is not None
    assert result["iata"] == "BCN"
    assert result["slug"] == "barcelone-3-jours-guide"
    assert result["title"] == "Barcelone : guide complet pour un week-end réussi"
    assert "lead" in result
    assert "itinerary" in result
    assert "faq" in result
    assert "generated_at" in result
    assert result["word_count"] > 0


def test_generate_strips_markdown_code_fences_around_json():
    """Claude often wraps JSON in ```json ... ```; we must unwrap."""
    from app.agents import destination_writer

    payload = json.dumps(_valid_guide_json())
    raw_text = f"```json\n{payload}\n```"
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response(raw_text)

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is not None
    assert result["slug"] == "barcelone-3-jours-guide"


def test_generate_returns_none_when_anthropic_client_missing():
    """No API key → get_client() returns None → generator must not crash."""
    from app.agents import destination_writer

    with patch.object(destination_writer, "get_client", return_value=None):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_generate_returns_none_when_json_invalid():
    """Claude returns garbage → JSON parse fails → return None, log error."""
    from app.agents import destination_writer

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response("not json at all")

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_generate_returns_none_when_anthropic_raises():
    """A network / API error must be caught."""
    from app.agents import destination_writer

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = RuntimeError("API down")

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    assert result is None


def test_word_count_tracks_actual_text_length():
    """word_count is derived from the lead+nut_graf+top_picks+itinerary+faq
    so we can audit whether articles are reaching the 2000-word goal."""
    from app.agents import destination_writer

    raw_json = json.dumps(_valid_guide_json())
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_anthropic_response(raw_json)

    with patch.object(destination_writer, "get_client", return_value=fake_client):
        result = destination_writer.generate_destination_guide("BCN")

    # The fixture contains short text, so word_count is small. We just
    # assert it's > 0 and is an int — the smoke test in Task 3.3 checks
    # the real count against a real Claude generation.
    assert isinstance(result["word_count"], int)
    assert result["word_count"] > 0
```

- [ ] **Step 2: Run pour vérifier que ça FAIL**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_writer.py -v
```

Expected: 6 fails (module n'existe pas).

### Task 3.2: Implémenter `destination_writer.py`

**Files:**
- Create: `backend/app/agents/destination_writer.py`

- [ ] **Step 1: Créer le module**

Créer `backend/app/agents/destination_writer.py` avec :

```python
"""Generate a 2000-word destination guide following the
travel-journalist-writer skill (format: guide destination).

Architecture decision: this module is intentionally separate from the
legacy article_writer.py (which produces a different 4-section shape
and is kept for the existing /api/articles/generate admin endpoint).
We don't extend article_writer to avoid breaking those 4 existing
articles' contract.

The output dict matches what we'll insert into the `articles` table:
title, h1, slug, meta_description, lead, nut_graf, top_picks,
itinerary, infos_pratiques, faq, sources, tags, photo_query, plus
the technical fields iata, generated_at, word_count.

References (from /tmp/travel-skill/travel-journalist-writer/):
- references/format-guide.md (structure)
- references/seo-blog.md (slug, meta, FAQ)
- references/voix-journaliste.md (style rules)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.agents.llm_client import get_client
from app.config import IATA_TO_CITY

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
FALLBACK_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 8000  # large enough for a 2000-word guide structured as JSON

SYSTEM_PROMPT = """Tu es un journaliste voyage français professionnel. Style: Le Monde Voyage, Géo, National Geographic Traveler. Tu écris pour Globe Genius (alertes vols pas chers depuis la France) un GUIDE DESTINATION de 2000 mots minimum.

PRINCIPES NON-NÉGOCIABLES:
1. ANGLE avant la destination. Pas de "X est une ville magnifique".
2. Montrer, pas affirmer. Pas de "magnifique", "incroyable", "à couper le souffle". Remplace par scènes, chiffres, citations, détails sensoriels.
3. Premier paragraphe = scène ou tension, jamais de définition Wikipedia.
4. Sources fact-checkables (office du tourisme, INSEE, étude). Pas d'invention.
5. Pas de clichés ("perle de…", "pays des sourires", "Venise du Nord").
6. Le lecteur n'est pas un client. L'article informe et raconte, il ne vend pas.

FORMAT GUIDE DESTINATION mixé Top X + Itinéraire J1-J3 + Infos pratiques. Toujours en français, toujours rigoureux.

Réponds UNIQUEMENT avec un JSON valide qui suit EXACTEMENT cette structure:

{
  "title": "Title tag SEO ≤60 caractères, mot-clé en début, promesse claire",
  "h1": "H1 article (peut différer du title, plus accrocheur)",
  "slug": "slug-court-kebab-mots-cles (3-6 mots, pas de mots vides)",
  "meta_description": "140-155 caractères, verbe action, mot-clé, promesse",
  "lead": "Paragraphe d'ouverture (80-150 mots): scène concrète qui pose l'angle. Pas de définition.",
  "nut_graf": "Paragraphe-clé (150-200 mots): de quoi parle vraiment l'article et pourquoi le lecteur doit lire.",
  "top_picks": [
    {
      "name": "Nom du lieu/expérience",
      "angle": "phrase d'angle 6-12 mots qui dit pourquoi celui-ci",
      "description": "2-4 phrases journalistiques sur le lieu, son histoire, son intérêt",
      "practical": "Adresse · Horaires · Prix · Comment y aller depuis le centre"
    }
    // EXACTEMENT 8 entrées
  ],
  "itinerary": [
    {
      "day": 1,
      "title": "Titre thématique de la journée",
      "morning": "9h-12h: description avec adresses + temps + prix",
      "lunch": "Restau précis avec adresse et budget",
      "afternoon": "14h-18h: description + transports",
      "evening": "Bar/dîner/spectacle",
      "lodging": "Suggestion gamme + quartier",
      "rain_plan": "Plan B 1-2 phrases si pluie",
      "budget_option": "Variante éco",
      "premium_option": "Variante haut de gamme"
    }
    // EXACTEMENT 3 jours
  ],
  "infos_pratiques": {
    "best_season": "Mois précis et pourquoi (3-4 phrases)",
    "how_to_get_there": "Depuis Paris (vol/train/voiture) + ordres de prix",
    "visa": "Formalités pour ressortissants UE",
    "daily_budget_eco": "Montant € pour 1 jour éco",
    "daily_budget_comfort": "Montant € confort",
    "daily_budget_premium": "Montant € premium",
    "where_to_sleep": "3 quartiers avec angle (charme/calme/local)",
    "to_avoid": "Pièges à touristes, arnaques, périodes",
    "local_tips": "Pratiques locales utiles, pourboire, tabous"
  },
  "faq": [
    {"q": "Question issue de Google People Also Ask", "a": "Réponse 40-80 mots autonome"}
    // 3 à 6 questions
  ],
  "sources": [
    "https://lien.officiel.fr/source-1",
    "https://lien.officiel.fr/source-2"
    // 2 à 4 sources d'autorité
  ],
  "tags": ["mot-cle-1", "mot-cle-2", "mot-cle-3", "mot-cle-4", "mot-cle-5"],
  "photo_query": "search query in English for Unsplash, e.g. 'Barcelona Spain travel'"
}

Densité totale visée: 2000 mots minimum (lead + nut_graf + 8x top_picks + 3x itinerary + infos_pratiques + faq). Sans bourrage. Si l'angle ne porte pas 2000 mots de qualité, descends à 1500 mais ne brode pas.

Aucun texte en dehors du JSON. Aucun ```. JSON brut."""


def _strip_code_fence(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers Claude often adds
    even when explicitly told not to."""
    text = text.strip()
    if text.startswith("```"):
        # remove first line (```json or ```)
        first_newline = text.find("\n")
        if first_newline > 0:
            text = text[first_newline + 1 :]
        # remove trailing ```
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


def _count_words(article: dict) -> int:
    """Rough word count over the user-visible text fields. Used for
    audit (are articles really hitting 2000 words?)."""
    parts: list[str] = []
    parts.append(article.get("lead", ""))
    parts.append(article.get("nut_graf", ""))
    for pick in article.get("top_picks", []) or []:
        parts.append(pick.get("description", ""))
        parts.append(pick.get("practical", ""))
    for day in article.get("itinerary", []) or []:
        for k in ("morning", "lunch", "afternoon", "evening", "lodging", "rain_plan", "budget_option", "premium_option"):
            parts.append(day.get(k, ""))
    infos = article.get("infos_pratiques") or {}
    for v in infos.values():
        if isinstance(v, str):
            parts.append(v)
    for q in article.get("faq", []) or []:
        parts.append(q.get("a", ""))
    return sum(len(p.split()) for p in parts if p)


def generate_destination_guide(iata: str) -> Optional[dict]:
    """Generate a 2000-word guide for a destination identified by its
    IATA code (BCN, BKK, MLE...). Synchronous, blocks ~30-60s.

    Returns a dict ready to insert into the `articles` table, or None
    on any failure (no API key, JSON parse error, network error).
    """
    client = get_client()
    if client is None:
        logger.warning("Anthropic client unavailable, cannot generate guide for %s", iata)
        return None

    # Build a friendly user message: city name + country if we know it
    city_label = IATA_TO_CITY.get(iata, iata)
    user_message = (
        f"Rédige le guide destination pour {city_label} (code aéroport: {iata}). "
        f"Public: voyageurs français qui partent en court ou moyen séjour. "
        f"Mot-clé SEO principal: \"{city_label.lower()} guide voyage\". "
        f"Mots-clés secondaires: \"que faire à {city_label.lower()}\", \"itinéraire {city_label.lower()}\", "
        f"\"voyage {city_label.lower()} pas cher\". Format de réponse: JSON brut conforme au schéma."
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        logger.warning("Sonnet call failed for %s, retrying with Haiku: %s", iata, e)
        try:
            response = client.messages.create(
                model=FALLBACK_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e2:
            logger.error("Haiku fallback also failed for %s: %s", iata, e2)
            return None

    if not response.content:
        logger.error("Empty Anthropic response for %s", iata)
        return None
    raw_text = response.content[0].text or ""
    if response.stop_reason == "max_tokens":
        logger.warning("Guide generation hit max_tokens for %s — JSON may be truncated", iata)

    cleaned = _strip_code_fence(raw_text)
    try:
        article = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Guide JSON parse failed for %s: %s. Last 200 chars: %s",
                     iata, e.msg, cleaned[-200:])
        return None

    article["iata"] = iata
    article["destination"] = city_label  # keep human-readable name in DB too
    article["generated_at"] = datetime.now(timezone.utc).isoformat()
    article["word_count"] = _count_words(article)

    return article
```

- [ ] **Step 2: Run, verify PASS**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_writer.py -v
```

Expected: 6 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/agents/destination_writer.py backend/tests/test_destination_writer.py
git commit -m "feat(content): destination guide generator (Sonnet, 2000 words, journalist style)"
```

### Task 3.3: Smoke test contre Claude réel (manuel)

⚠️ Action manuelle, brûle ~$0.05 de tokens.

- [ ] **Step 1: Générer un vrai article BCN en local**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && set -a && source .env && set +a && PYTHONPATH=. .venv/bin/python -c "
from app.agents.destination_writer import generate_destination_guide
import json
r = generate_destination_guide('BCN')
if r is None:
    print('FAIL')
else:
    print('OK title:', r['title'])
    print('OK slug:', r['slug'])
    print('OK word_count:', r['word_count'])
    print('OK top_picks:', len(r.get('top_picks', [])))
    print('OK itinerary days:', len(r.get('itinerary', [])))
    print('OK faq:', len(r.get('faq', [])))
"
```

Expected:
- `title` ≤ 60 caractères, slug court, word_count entre 1500 et 3500
- 8 top_picks, 3 itinerary days, 3-6 faq
- Pas d'erreur

Si le word_count est < 1200 → le prompt ne tient pas la longueur. Ouvrir le système prompt et resserrer la consigne ou passer à `claude-opus-4-7` (plus cher mais plus verbeux).

---

## Phase 4 — Helper d'orchestration "ensure article" (45 min)

### Task 4.1: TDD — tests pour `ensure_article_for_destination`

**Files:**
- Create: `backend/tests/test_destination_article_helper.py`

- [ ] **Step 1: Écrire les tests**

Créer `backend/tests/test_destination_article_helper.py` :

```python
"""Tests for ensure_article_for_destination orchestration helper.

The function is called synchronously from the dispatch loop just before
sending a Telegram alert. It checks if an article exists for the IATA;
if not, it generates one (Claude) + fetches a photo (Unsplash) + inserts
into the articles table.

Returns True if an article exists in DB after the call, False otherwise
— so the caller can decide whether to include the "📖 Le guide" link
in the Telegram alert.
"""
from unittest.mock import MagicMock, patch

import pytest


def _build_db_mock(*, existing_article: bool = False, insert_succeeds: bool = True):
    """A db.table() router that responds to the queries
    ensure_article_for_destination makes."""
    db = MagicMock()

    def _table(name):
        t = MagicMock()
        if name == "articles":
            # check-existence query
            select_chain = (
                t.select.return_value
                .eq.return_value
                .limit.return_value
            )
            select_chain.execute.return_value = MagicMock(
                data=[{"id": "x"}] if existing_article else []
            )
            # insert
            ins_chain = t.insert.return_value
            ins_chain.execute.return_value = MagicMock(
                data=[{"id": "newid"}] if insert_succeeds else None
            )
        return t

    db.table.side_effect = _table
    return db


def test_returns_true_immediately_when_article_already_exists():
    """No generation if the IATA is already in DB. Saves Anthropic budget."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=True)
    gen_mock = MagicMock()
    photo_mock = MagicMock()

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is True
    gen_mock.assert_not_called()
    photo_mock.assert_not_called()


def test_generates_and_inserts_when_no_existing_article():
    """Happy path: generate guide + fetch photo + insert row."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False, insert_succeeds=True)
    fake_article = {
        "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T",
        "h1": "H1", "meta_description": "M", "lead": "L",
        "nut_graf": "N", "top_picks": [], "itinerary": [],
        "infos_pratiques": {}, "faq": [], "sources": [],
        "tags": [], "photo_query": "Barcelona Spain",
        "generated_at": "2026-05-02T12:00:00+00:00",
        "word_count": 2000,
    }
    fake_photo = {
        "url": "https://images.unsplash.com/photo-x",
        "photo_id": "x",
        "photographer_name": "Jane",
        "photographer_url": "https://unsplash.com/@jane",
    }
    gen_mock = MagicMock(return_value=fake_article)
    photo_mock = MagicMock(return_value=fake_photo)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is True
    gen_mock.assert_called_once_with("BCN")
    photo_mock.assert_called_once_with("BCN", query_hint="Barcelona Spain")
    # The insert payload must include the photo URL merged in
    insert_payload = db_mock.table("articles").insert.call_args.args[0]
    assert insert_payload["iata"] == "BCN"
    assert insert_payload["cover_photo"] == "https://images.unsplash.com/photo-x"
    assert insert_payload["photographer_name"] == "Jane"


def test_returns_false_when_generation_fails():
    """Anthropic returns None → no DB insert, return False so caller
    falls back to alert-without-guide-link behaviour."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False)
    gen_mock = MagicMock(return_value=None)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is False
    db_mock.table("articles").insert.assert_not_called()


def test_inserts_article_even_if_unsplash_fails():
    """A missing cover photo isn't a blocker — the article is the value."""
    from app.notifications import destination_articles

    db_mock = _build_db_mock(existing_article=False, insert_succeeds=True)
    fake_article = {
        "iata": "XXX", "destination": "Nowhere (XXX)",
        "slug": "nowhere-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [], "photo_query": "Nowhere",
        "generated_at": "2026-05-02T12:00:00+00:00", "word_count": 1500,
    }
    gen_mock = MagicMock(return_value=fake_article)
    photo_mock = MagicMock(return_value=None)

    with patch.object(destination_articles, "db", db_mock), \
         patch.object(destination_articles, "generate_destination_guide", gen_mock), \
         patch.object(destination_articles, "fetch_destination_photo", photo_mock):
        result = destination_articles.ensure_article_for_destination("XXX")

    assert result is True
    insert_payload = db_mock.table("articles").insert.call_args.args[0]
    assert insert_payload.get("cover_photo") in (None, "")


def test_returns_false_when_db_unavailable():
    """db is None (e.g. Supabase not configured in dev) → no-op, False."""
    from app.notifications import destination_articles

    with patch.object(destination_articles, "db", None):
        result = destination_articles.ensure_article_for_destination("BCN")

    assert result is False
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_article_helper.py -v
```

Expected: 5 fails (module n'existe pas).

### Task 4.2: Implémenter `destination_articles.py`

**Files:**
- Create: `backend/app/notifications/destination_articles.py`

- [ ] **Step 1: Créer le module**

Créer `backend/app/notifications/destination_articles.py` :

```python
"""Synchronous helper called from the alert dispatcher to lazily generate
a destination guide before the very first Telegram alert ever sent for
that destination.

Behaviour:
- If an article exists in DB for `iata` → no-op, returns True.
- Else → call destination_writer.generate_destination_guide(iata),
  fetch a cover photo via Unsplash, insert the row.
- Returns True iff an article exists in DB after the call.

Cost discipline: an article is generated AT MOST ONCE per destination,
ever. Subsequent alerts to the same destination don't pay any Anthropic
tokens.

Failure modes don't crash the caller — they return False so the alert
dispatcher can decide to send the alert without the guide link.
"""
import logging
from typing import Optional

from app.agents.destination_writer import generate_destination_guide
from app.db import db
from app.notifications.unsplash import fetch_destination_photo

logger = logging.getLogger(__name__)


def _article_exists(iata: str) -> bool:
    """Return True iff the articles table has a row with this iata."""
    if not db:
        return False
    try:
        r = (
            db.table("articles")
            .select("id")
            .eq("iata", iata)
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception as e:
        logger.warning("Article existence check failed for %s: %s", iata, e)
        return False


def ensure_article_for_destination(iata: str) -> bool:
    """Make sure an article row exists for the destination. Generates one
    synchronously if needed (~30-60s blocking call). Safe to call before
    every Telegram dispatch — it returns immediately when the article is
    already in DB.

    Returns:
        True  — an article exists in DB after the call (already there or
                successfully generated).
        False — generation failed or DB unavailable. Caller should still
                send the alert, just without the "📖 guide" link.
    """
    if not db:
        logger.info("DB unavailable, cannot ensure article for %s", iata)
        return False

    if _article_exists(iata):
        return True

    logger.info("No article for %s yet, generating now (synchronous)", iata)
    article = generate_destination_guide(iata)
    if not article:
        logger.warning("Article generation returned None for %s", iata)
        return False

    # Fetch cover photo. Best-effort — a missing photo doesn't block insertion.
    photo_query = article.get("photo_query") or article.get("destination") or iata
    photo = fetch_destination_photo(iata, query_hint=photo_query)
    if photo:
        article["cover_photo"] = photo["url"]
        article["photo_id"] = photo["photo_id"]
        article["photographer_name"] = photo["photographer_name"]
        article["photographer_url"] = photo["photographer_url"]
    else:
        # Explicit empty values so the column exists and frontend can
        # branch cleanly on falsy checks.
        article["cover_photo"] = ""
        article["photo_id"] = ""
        article["photographer_name"] = ""
        article["photographer_url"] = ""

    # Convert nested lists/dicts to JSON-friendly form. Supabase python
    # client serialises dict / list automatically into jsonb columns,
    # so no manual json.dumps needed.
    try:
        db.table("articles").insert(article).execute()
        logger.info("Article inserted for %s (slug=%s, words=%s)",
                    iata, article.get("slug"), article.get("word_count"))
        return True
    except Exception as e:
        logger.error("Article insert failed for %s: %s", iata, e)
        return False
```

- [ ] **Step 2: Run, verify PASS**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_article_helper.py -v
```

Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/notifications/destination_articles.py backend/tests/test_destination_article_helper.py
git commit -m "feat(content): ensure_article_for_destination orchestrator (lazy generation)"
```

---

## Phase 5 — Hook dans le dispatch + lien dans alertes (45 min)

### Task 5.1: Brancher l'orchestrator dans `_dispatch_grouped_flight_alerts`

**Files:**
- Modify: `backend/app/scheduler/jobs.py`

- [ ] **Step 1: Localiser le bon endroit**

Le bloc V8.2 qui flush les alertes round-trip groupées par (user, dest) appelle `send_grouped_flight_alerts(...)`. Il faut appeler `ensure_article_for_destination(grp_dest)` JUSTE AVANT chaque send. Localiser :

```bash
grep -n "send_grouped_flight_alerts(" backend/app/scheduler/jobs.py
```

Note la ligne du `await send_grouped_flight_alerts(...)` (autour de la ligne 980).

- [ ] **Step 2: Insérer l'appel**

Dans `backend/app/scheduler/jobs.py`, juste avant le bloc `try: success = await send_grouped_flight_alerts(...)`, ajouter :

```python
        # V9: lazily generate the destination guide before the very
        # first alert to this dest. Synchronous (blocks ~30-60s on
        # the first hit). Subsequent alerts to the same dest = no-op.
        # If generation fails, the alert still goes out — the formatter
        # will simply skip the "📖 Le guide" line.
        try:
            from app.notifications.destination_articles import ensure_article_for_destination
            has_guide = ensure_article_for_destination(grp_dest)
        except Exception as e:
            logger.warning(f"ensure_article_for_destination crashed for {grp_dest}: {e}")
            has_guide = False
```

Puis modifier l'appel `send_grouped_flight_alerts(...)` pour passer `has_guide` (à condition que la signature le supporte — voir Task 5.2). Pour l'instant, juste mémoriser `has_guide` ; on le branchera dans le formatter dans la prochaine tâche.

Ajouter aussi le même appel `ensure_article_for_destination(destination)` dans `_detect_and_dispatch_oneway_alerts` (juste avant `send_oneway_deal_alert`) et dans `_detect_and_dispatch_split_ticket_combos` (juste avant `send_split_ticket_alert`). Cherche les deux call-sites :

```bash
grep -n "send_oneway_deal_alert(\|send_split_ticket_alert(" backend/app/scheduler/jobs.py
```

Pour chacun, ajouter au-dessus du `try` qui appelle le send :
```python
            try:
                from app.notifications.destination_articles import ensure_article_for_destination
                has_guide = ensure_article_for_destination(destination)  # or `dest` for combos
            except Exception as e:
                logger.warning(f"ensure_article_for_destination crashed: {e}")
                has_guide = False
```

(Variable `destination` dans oneway, `dest` dans combo — voir contexte.)

- [ ] **Step 3: Smoke import**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -c "from app.scheduler.jobs import _dispatch_grouped_flight_alerts; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/scheduler/jobs.py
git commit -m "feat(dispatch): generate destination guide before first alert"
```

### Task 5.2: Ajouter le lien "📖 Le guide" dans les 3 formatters Telegram

**Files:**
- Modify: `backend/app/notifications/telegram.py`

- [ ] **Step 1: Modifier `format_grouped_flight_alerts`**

Trouver la signature `def format_grouped_flight_alerts(...)`. Vérifier si la fonction reçoit déjà l'IATA destination (paramètre `destination` ou similaire). Si non, l'ajouter (`destination_iata: str`). Ajouter aussi un paramètre `has_guide: bool = False` à la fin. Dans le corps, juste avant la dernière ligne `👉 [Toutes les offres ...]`, insérer :

```python
    if has_guide:
        msg_parts.append(
            f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{destination_iata.lower()})"
        )
```

(Remplacer `destination_iata` par le nom du paramètre IATA effectivement utilisé dans la signature.)

Modifier le call-site dans `send_grouped_flight_alerts` pour passer `has_guide` (paramètre lui-aussi à ajouter à `send_grouped_flight_alerts` ; vois la signature, propage simplement le bool).

- [ ] **Step 2: Pareil pour `format_oneway_deal_alert`**

Ajouter `has_guide: bool = False` au paramètre. Juste avant la dernière ligne, insérer :

```python
    if has_guide:
        guide_iata = dest if direction == "outbound" else origin
        lines += ["", f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{guide_iata.lower()})"]
```

Et propager dans `send_oneway_deal_alert`.

- [ ] **Step 3: Pareil pour `format_split_ticket_alert`**

Ajouter `has_guide: bool = False` au paramètre. Juste avant la dernière ligne, insérer :

```python
    if has_guide:
        lines += ["", f"📖 [Le guide complet de {dest_label}]({settings.FRONTEND_URL}/destination/{dest.lower()})"]
```

Et propager dans `send_split_ticket_alert`.

- [ ] **Step 4: Modifier les 3 sites d'appel dans jobs.py**

Maintenant, les `await send_*` du dispatch peuvent passer le `has_guide` calculé en Task 5.1. Modifier chaque site d'appel pour ajouter `has_guide=has_guide` aux kwargs.

- [ ] **Step 5: Tests existants**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_telegram.py tests/test_oneway_telegram.py -v 2>&1 | tail -20
```

Expected: tous les tests existants passent toujours (le nouveau paramètre a un default `False`, donc compatible).

- [ ] **Step 6: Test inline du lien**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -c "
from app.notifications.telegram import format_grouped_flight_alerts
offers = [{'departure_date':'2026-09-01','return_date':'2026-09-08','price':89,'discount_pct':55,'origin':'CDG','baseline_price':130,'booking_url':'https://x','airline':'AF'}]
msg = format_grouped_flight_alerts('Paris','Barcelone','BCN',offers,tier='premium',origin_iata='CDG',has_guide=True)
print('contains guide link:', 'destination/bcn' in msg)
print(msg)
"
```

Expected: la dernière ligne du message contient `📖 [Le guide complet de Barcelone (BCN)](https://globegenius.app/destination/bcn)`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/notifications/telegram.py
git commit -m "feat(alerts): link Telegram alerts to the destination guide page"
```

---

## Phase 6 — API publique pour la page destination (30 min)

### Task 6.1: TDD — endpoint `GET /api/destinations/{iata}`

**Files:**
- Create: `backend/tests/test_destination_endpoint.py`

- [ ] **Step 1: Écrire les tests**

Créer `backend/tests/test_destination_endpoint.py` :

```python
"""Tests for the public GET /api/destinations/{iata} endpoint.

Returns the article + photo + active deals for a destination. Used by
the Next.js page /destination/[iata]. Public — no auth.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_returns_404_when_no_article_exists():
    """No article in DB → 404, the Next.js page renders the
    not-found state."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/XXX")
    assert r.status_code == 404


def test_returns_article_payload_when_present():
    """Article exists → 200 with the article fields + photo + deals."""
    from app.main import app
    client = TestClient(app)

    article_row = {
        "id": "a1", "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [],
        "cover_photo": "https://images.unsplash.com/x",
        "photographer_name": "Jane",
        "photographer_url": "https://unsplash.com/@jane",
        "word_count": 2000,
    }

    def _table(name):
        t = MagicMock()
        if name == "articles":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[article_row])
        elif name == "qualified_items":
            # Return 0 active deals (deals are optional in the response)
            t.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        return t

    db_mock = MagicMock()
    db_mock.table.side_effect = _table

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/BCN")
    assert r.status_code == 200
    body = r.json()
    assert body["article"]["iata"] == "BCN"
    assert body["article"]["slug"] == "barcelone-3-jours-guide"
    assert body["photo"]["url"] == "https://images.unsplash.com/x"
    assert body["photo"]["photographer_name"] == "Jane"
    assert "deals" in body  # may be empty


def test_iata_is_uppercased_for_lookup():
    """A request to /api/destinations/bcn (lowercase) must find the BCN article."""
    from app.main import app
    client = TestClient(app)

    article_row = {
        "id": "a1", "iata": "BCN", "destination": "Barcelone (BCN)",
        "slug": "barcelone-3-jours-guide", "title": "T", "h1": "H1",
        "meta_description": "M", "lead": "L", "nut_graf": "N",
        "top_picks": [], "itinerary": [], "infos_pratiques": {},
        "faq": [], "sources": [], "tags": [],
        "cover_photo": "", "photographer_name": "", "photographer_url": "",
        "word_count": 2000,
    }

    captured = {}
    def _table(name):
        t = MagicMock()
        if name == "articles":
            def _eq(col, val):
                captured["iata_query"] = val
                m = MagicMock()
                m.limit.return_value.execute.return_value = MagicMock(data=[article_row])
                return m
            t.select.return_value.eq.side_effect = _eq
        elif name == "qualified_items":
            t.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        return t

    db_mock = MagicMock()
    db_mock.table.side_effect = _table

    with patch("app.api.routes.db", db_mock):
        r = client.get("/api/destinations/bcn")
    assert r.status_code == 200
    assert captured["iata_query"] == "BCN"
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_endpoint.py -v
```

Expected: 3 fails (404 instead of mocked behaviour).

### Task 6.2: Implémenter l'endpoint

**Files:**
- Modify: `backend/app/api/routes.py`

- [ ] **Step 1: Ajouter l'endpoint**

Trouver une zone publique (ex. après `/health/deep`) et ajouter :

```python
@router.get("/api/destinations/{iata}")
def get_destination(iata: str):
    """Public endpoint backing the /destination/[iata] page.

    Returns the article + cover photo + up to 5 active deals towards
    this destination. 404 if no article generated yet.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Database not configured")

    iata_upper = (iata or "").upper().strip()
    if not iata_upper or len(iata_upper) > 4:
        raise HTTPException(status_code=400, detail="Invalid IATA code")

    art_resp = (
        db.table("articles")
        .select("*")
        .eq("iata", iata_upper)
        .limit(1)
        .execute()
    )
    if not art_resp.data:
        raise HTTPException(status_code=404, detail="No guide for this destination yet")
    article = art_resp.data[0]

    photo = {
        "url": article.get("cover_photo", ""),
        "photographer_name": article.get("photographer_name", ""),
        "photographer_url": article.get("photographer_url", ""),
    }

    # Active deals towards this destination, freshest first.
    # We use raw_flights linked from qualified_items so we have the
    # origin / dates / source_url to propose.
    deals: list[dict] = []
    try:
        # Step 1: get freshest qualified_items for this dest
        qi_resp = (
            db.table("qualified_items")
            .select("item_id,discount_pct,price,baseline_price,trip_type")
            .eq("status", "active")
            .eq("type", "flight")
            .gte("discount_pct", 30)
            .order("discount_pct", desc=True)
            .limit(20)
            .execute()
        )
        qi_rows = qi_resp.data or []
        if qi_rows:
            item_ids = [q["item_id"] for q in qi_rows if q.get("item_id")]
            rf_resp = (
                db.table("raw_flights")
                .select("id,origin,destination,departure_date,return_date,airline,source_url,trip_type")
                .in_("id", item_ids[:50])
                .eq("destination", iata_upper)
                .execute()
            )
            rf_by_id = {r["id"]: r for r in (rf_resp.data or [])}
            for q in qi_rows:
                rf = rf_by_id.get(q.get("item_id"))
                if not rf:
                    continue
                deals.append({
                    "origin": rf.get("origin"),
                    "destination": rf.get("destination"),
                    "departure_date": rf.get("departure_date"),
                    "return_date": rf.get("return_date"),
                    "price": q.get("price"),
                    "baseline_price": q.get("baseline_price"),
                    "discount_pct": q.get("discount_pct"),
                    "airline": rf.get("airline"),
                    "source_url": rf.get("source_url"),
                    "trip_type": rf.get("trip_type"),
                })
                if len(deals) >= 5:
                    break
    except Exception as e:
        logger.warning(f"Deal lookup for destination {iata_upper} failed: {e}")

    return {"article": article, "photo": photo, "deals": deals}
```

- [ ] **Step 2: Run, verify PASS**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_destination_endpoint.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes.py backend/tests/test_destination_endpoint.py
git commit -m "feat(api): public GET /api/destinations/{iata} endpoint"
```

---

## Phase 7 — Frontend page destination (1h30)

### Task 7.1: Helper API + types

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Ajouter types et fetcher**

À la fin de `frontend/src/lib/api.ts`, ajouter :

```typescript
// ─── Destination guides ───

export interface DestinationGuide {
  article: {
    id: string;
    iata: string;
    destination: string;
    slug: string;
    title: string;
    h1: string;
    meta_description: string;
    lead: string;
    nut_graf: string;
    top_picks: Array<{
      name: string;
      angle: string;
      description: string;
      practical: string;
    }>;
    itinerary: Array<{
      day: number;
      title: string;
      morning: string;
      lunch: string;
      afternoon: string;
      evening: string;
      lodging: string;
      rain_plan: string;
      budget_option: string;
      premium_option: string;
    }>;
    infos_pratiques: Record<string, string>;
    faq: Array<{ q: string; a: string }>;
    sources: string[];
    tags: string[];
    word_count: number;
    generated_at: string;
  };
  photo: {
    url: string;
    photographer_name: string;
    photographer_url: string;
  };
  deals: Array<{
    origin: string;
    destination: string;
    departure_date: string;
    return_date: string | null;
    price: number;
    baseline_price: number;
    discount_pct: number;
    airline: string | null;
    source_url: string | null;
    trip_type: string;
  }>;
}

export async function getDestinationGuide(iata: string): Promise<DestinationGuide | null> {
  const res = await fetch(`${API_URL}/api/destinations/${iata.toUpperCase()}`, {
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

- [ ] **Step 2: Type-check**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend && npx tsc --noEmit 2>&1 | tail -3
```

Expected: aucune sortie.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): API helper getDestinationGuide + types"
```

### Task 7.2: Page Next.js `/destination/[iata]`

**Files:**
- Create: `frontend/src/app/destination/[iata]/page.tsx`
- Create: `frontend/src/app/destination/[iata]/layout.tsx`

- [ ] **Step 1: Créer la page (server component, SSR)**

Créer le dossier puis `frontend/src/app/destination/[iata]/page.tsx` :

```tsx
import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { getDestinationGuide } from "@/lib/api";

type PageProps = { params: Promise<{ iata: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { iata } = await params;
  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) {
    return { title: "Destination non trouvée" };
  }
  return {
    title: guide.article.title,
    description: guide.article.meta_description,
    openGraph: {
      title: guide.article.title,
      description: guide.article.meta_description,
      images: guide.photo.url ? [{ url: guide.photo.url }] : undefined,
      type: "article",
    },
    alternates: {
      canonical: `https://globegenius.app/destination/${guide.article.iata.toLowerCase()}`,
    },
  };
}

export default async function DestinationPage({ params }: PageProps) {
  const { iata } = await params;
  const guide = await getDestinationGuide(iata).catch(() => null);
  if (!guide) notFound();

  const a = guide.article;
  const photo = guide.photo;
  const deals = guide.deals;

  // JSON-LD: TouristDestination + FAQPage for rich results
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TouristDestination",
        name: a.destination,
        description: a.meta_description,
        image: photo.url || undefined,
        url: `https://globegenius.app/destination/${a.iata.toLowerCase()}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: a.faq.map((q) => ({
          "@type": "Question",
          name: q.q,
          acceptedAnswer: { "@type": "Answer", text: q.a },
        })),
      },
    ],
  };

  return (
    <main className="min-h-screen bg-[var(--color-cream)]">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      {/* Hero with cover photo */}
      <section className="relative h-[60vh] min-h-[400px] w-full overflow-hidden bg-[var(--color-ink)]">
        {photo.url && (
          <Image
            src={photo.url}
            alt={`${a.destination} — photo de couverture`}
            fill
            priority
            className="object-cover"
            sizes="100vw"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent" />
        <div className="relative z-10 flex h-full flex-col items-center justify-end p-8 text-center text-white">
          <h1 className="font-[family-name:var(--font-dm-serif)] text-4xl sm:text-6xl mb-4 max-w-4xl">
            {a.h1}
          </h1>
          <p className="max-w-2xl text-lg opacity-90">{a.meta_description}</p>
        </div>
        {photo.photographer_name && (
          <div className="absolute bottom-2 right-3 text-xs text-white/70">
            Photo :{" "}
            <a href={photo.photographer_url} target="_blank" rel="noopener noreferrer" className="underline">
              {photo.photographer_name}
            </a>{" "}
            sur{" "}
            <a href="https://unsplash.com" target="_blank" rel="noopener noreferrer" className="underline">
              Unsplash
            </a>
          </div>
        )}
      </section>

      {/* Article body */}
      <article className="mx-auto max-w-3xl px-6 py-12 prose prose-lg">
        <p className="text-xl font-medium text-[var(--color-ink)]">{a.lead}</p>
        <p className="text-[var(--color-ink)]/80">{a.nut_graf}</p>

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">À voir, à faire, à manger</h2>
        {a.top_picks.map((p, i) => (
          <div key={i} className="mb-8 border-l-4 border-[var(--color-coral)] pl-4">
            <h3 className="text-xl font-bold">
              {i + 1}. {p.name} — <span className="font-normal italic">{p.angle}</span>
            </h3>
            <p>{p.description}</p>
            <p className="text-sm text-gray-600">
              <strong>Pratique :</strong> {p.practical}
            </p>
          </div>
        ))}

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">L&apos;itinéraire suggéré</h2>
        {a.itinerary.map((day) => (
          <div key={day.day} className="mb-8">
            <h3 className="text-xl font-bold">
              Jour {day.day} — {day.title}
            </h3>
            <p><strong>Matin (9h-12h) :</strong> {day.morning}</p>
            <p><strong>Déjeuner :</strong> {day.lunch}</p>
            <p><strong>Après-midi (14h-18h) :</strong> {day.afternoon}</p>
            <p><strong>Soir :</strong> {day.evening}</p>
            <p><strong>Logement :</strong> {day.lodging}</p>
            <p className="text-sm text-gray-600">
              <strong>Si pluie :</strong> {day.rain_plan}<br />
              <strong>Option budget :</strong> {day.budget_option}<br />
              <strong>Option premium :</strong> {day.premium_option}
            </p>
          </div>
        ))}

        {/* Deals slot */}
        {deals.length > 0 && (
          <>
            <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">
              Vols pas chers vers {a.destination} en ce moment
            </h2>
            <div className="not-prose grid gap-4 sm:grid-cols-2">
              {deals.map((d, i) => (
                <div key={i} className="rounded-2xl border border-[var(--color-sand)] bg-white p-4">
                  <div className="text-sm font-bold">
                    {d.origin} → {d.destination} · {d.airline ?? ""}
                  </div>
                  <div className="text-2xl font-extrabold text-[var(--color-coral)]">{d.price}€ <span className="text-sm font-normal text-gray-400 line-through">{d.baseline_price}€</span></div>
                  <div className="text-xs text-gray-600">
                    {d.departure_date} {d.return_date ? `→ ${d.return_date}` : "(aller simple)"}
                  </div>
                  {d.source_url && (
                    <a href={d.source_url} target="_blank" rel="noopener noreferrer"
                       className="mt-2 inline-block text-sm text-[var(--color-coral)] hover:underline">
                      Voir le deal →
                    </a>
                  )}
                </div>
              ))}
            </div>
            <p className="mt-4 text-center">
              <Link href="/signup" className="inline-block rounded-xl bg-[var(--color-coral)] px-6 py-3 font-bold text-white hover:bg-[var(--color-coral-hover)]">
                Recevez les nouveaux deals sur Telegram (gratuit)
              </Link>
            </p>
          </>
        )}

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">Infos pratiques</h2>
        <ul>
          {Object.entries(a.infos_pratiques).map(([k, v]) => (
            <li key={k}>
              <strong>{k.replace(/_/g, " ")} :</strong> {v}
            </li>
          ))}
        </ul>

        <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">FAQ</h2>
        {a.faq.map((q, i) => (
          <details key={i} className="mb-3">
            <summary className="cursor-pointer font-bold">{q.q}</summary>
            <p className="mt-2 text-[var(--color-ink)]/80">{q.a}</p>
          </details>
        ))}

        {a.sources.length > 0 && (
          <>
            <h2 className="mt-12 font-[family-name:var(--font-dm-serif)] text-3xl">Sources</h2>
            <ul className="text-sm text-gray-600">
              {a.sources.map((s) => (
                <li key={s}>
                  <a href={s} target="_blank" rel="noopener noreferrer" className="underline">{s}</a>
                </li>
              ))}
            </ul>
          </>
        )}
      </article>
    </main>
  );
}
```

- [ ] **Step 2: Type-check + smoke**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend && npx tsc --noEmit 2>&1 | tail -3
```

Expected: aucune sortie.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/destination/
git commit -m "feat(frontend): /destination/[iata] SSR page with article + deals + JSON-LD"
```

### Task 7.3: Sitemap.xml

**Files:**
- Create or modify: `frontend/src/app/sitemap.ts`

- [ ] **Step 1: Vérifier si un sitemap existe déjà**

```bash
ls frontend/src/app/sitemap.ts 2>/dev/null
```

S'il existe, ajouter les destinations en plus des routes existantes. S'il n'existe pas, le créer :

```typescript
import type { MetadataRoute } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchDestinationsWithArticle(): Promise<string[]> {
  // We piggy-back on /api/admin/scrapers/health to learn known destinations
  // is overkill — instead, hit a tiny public endpoint that lists slugs.
  // For now, return an empty list and let articles be discovered via internal links.
  // (When traffic justifies, add a /api/destinations endpoint that lists all slugs.)
  return [];
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = "https://globegenius.app";
  const dests = await fetchDestinationsWithArticle();

  return [
    { url: `${base}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/login`, changeFrequency: "monthly", priority: 0.3 },
    { url: `${base}/signup`, changeFrequency: "monthly", priority: 0.3 },
    ...dests.map((iata) => ({
      url: `${base}/destination/${iata.toLowerCase()}`,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
```

NOTE : pour que `fetchDestinationsWithArticle` ramène vraiment les IATA présents en DB, on a besoin d'un endpoint backend. Vu qu'on est lazy et que Google va découvrir les pages via les liens internes (landing → guide), on **commit ce sitemap minimal** pour l'instant. Améliorations futures (Phase 9 hors-scope).

- [ ] **Step 2: Type-check**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend && npx tsc --noEmit 2>&1 | tail -3
```

Expected: aucune sortie.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/sitemap.ts
git commit -m "seo: sitemap.xml scaffold (destinations to be discovered via internal links for now)"
```

---

## Phase 8 — Liens entrants depuis landing + home (45 min)

### Task 8.1: Section "Nos guides destination" sur la landing

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Identifier l'emplacement**

Dans `frontend/src/app/page.tsx`, trouver la section "3 types de deals" (`On cherche partout pour vous`). On va insérer la nouvelle section **avant** elle, pour qu'elle apparaisse haut dans la page.

```bash
grep -n "On cherche partout pour vous\|3 types de deals" frontend/src/app/page.tsx
```

- [ ] **Step 2: Ajouter un fetcher serveur en haut de la page**

En haut du fichier, juste sous les imports, ajouter :

```typescript
async function fetchRecentDestinationGuides(): Promise<Array<{ iata: string; destination: string; cover_photo: string; title: string }>> {
  // Hits a public endpoint that returns the 6 most recently generated articles.
  // Falls back to empty array on any error so the section just doesn't render.
  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${API_URL}/api/destinations`, { next: { revalidate: 600 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items?.slice(0, 6) ?? [];
  } catch {
    return [];
  }
}
```

- [ ] **Step 3: Rendre la section conditionnellement**

Convertir le composant `Landing` en `async` (`export default async function Landing()`), fetcher les guides, et insérer la section avant "On cherche partout pour vous" :

```tsx
const recentGuides = await fetchRecentDestinationGuides();

// ...

{recentGuides.length > 0 && (
  <section className="py-16 px-6 sm:px-12 bg-white border-t border-[var(--color-sand)]">
    <h2 className="font-[family-name:var(--font-dm-serif)] text-3xl font-bold text-[var(--color-ink)] text-center mb-2">
      Nos guides destination
    </h2>
    <p className="text-center text-gray-500 text-sm mb-10">
      Des guides écrits par nos rédacteurs voyage pour préparer chaque destination.
    </p>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
      {recentGuides.map((g) => (
        <Link key={g.iata} href={`/destination/${g.iata.toLowerCase()}`}
              className="group block overflow-hidden rounded-2xl border border-[var(--color-sand)] bg-white hover:border-[var(--color-coral)] transition-colors">
          {g.cover_photo && (
            <div className="relative aspect-video overflow-hidden">
              <img src={g.cover_photo} alt={g.destination}
                   className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform" />
            </div>
          )}
          <div className="p-4">
            <div className="text-xs text-gray-400">{g.destination}</div>
            <div className="font-bold text-[var(--color-ink)]">{g.title}</div>
          </div>
        </Link>
      ))}
    </div>
  </section>
)}
```

- [ ] **Step 4: Backend — endpoint `GET /api/destinations` (liste)**

L'endpoint n'existe pas encore. Ajouter dans `backend/app/api/routes.py`, juste avant `GET /api/destinations/{iata}` :

```python
@router.get("/api/destinations")
def list_destinations(limit: int = 6):
    """Public list of destinations with an article. Used by the landing
    page to surface the latest 6 guides."""
    if not db:
        return {"items": []}
    try:
        r = (
            db.table("articles")
            .select("iata,destination,title,cover_photo,generated_at")
            .not_.is_("iata", "null")
            .order("generated_at", desc=True)
            .limit(min(max(limit, 1), 50))
            .execute()
        )
        return {"items": r.data or []}
    except Exception as e:
        logger.warning(f"List destinations failed: {e}")
        return {"items": []}
```

- [ ] **Step 5: Test l'endpoint**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/backend && PYTHONPATH=. .venv/bin/python -c "
from app.api.routes import router
routes = [r.path for r in router.routes if hasattr(r, 'path')]
print('list endpoint:', '/api/destinations' in routes)
"
```

Expected: `True`.

- [ ] **Step 6: Type-check frontend**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend && npx tsc --noEmit 2>&1 | tail -3
```

Expected: aucune sortie.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes.py frontend/src/app/page.tsx
git commit -m "feat(landing): show 6 most recent destination guides + GET /api/destinations"
```

### Task 8.2: Cards cliquables sur `/home`

**Files:**
- Modify: `frontend/src/app/home/page.tsx`

- [ ] **Step 1: Localiser les cards**

Chercher les éléments de rendu des deals dans `home/page.tsx` (probablement un `.map()` sur les deals). Identifier la structure de la card de deal.

- [ ] **Step 2: Wrapper la card dans un Link**

Pour chaque card de deal, wrapper le contenu dans :
```tsx
<Link href={`/destination/${deal.destination.toLowerCase()}`} target="_blank" rel="noopener noreferrer" className="block hover:opacity-90 transition-opacity">
  {/* card content */}
</Link>
```

`target="_blank"` ouvre la page dans un nouvel onglet → ne casse pas la navigation du user logged-in dans `/home`.

- [ ] **Step 3: Type-check + smoke**

```bash
cd /Users/moussa/Documents/PROJETS/globegenius/frontend && npx tsc --noEmit 2>&1 | tail -3
```

Expected: aucune sortie.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/home/page.tsx
git commit -m "feat(home): make deal cards link to destination guide page"
```

---

## Phase 9 — Validation post-deploy (manuelle, no code)

### Task 9.1: Push + attendre Railway

- [ ] **Step 1: Push et attendre 2 min**

```bash
git push origin v9
```

Railway redéploie automatiquement. Attendre ~2 min.

- [ ] **Step 2: Smoke /api/destinations**

```bash
curl -s https://globagenius-production-1380.up.railway.app/api/destinations | python3 -m json.tool
```

Expected: `{"items": []}` au début (aucun article IATA en DB encore).

### Task 9.2: Déclencher la première génération via une vraie alerte

- [ ] **Step 1: Trigger un scrape manuel** (si tu veux forcer une nouvelle alerte rapidement)

```bash
ADMIN_KEY=$(railway variables --service globagenius --environment production --kv 2>&1 | grep '^ADMIN_API_KEY=' | cut -d'=' -f2)
curl -X POST "https://globagenius-production-1380.up.railway.app/api/trigger/scrape_flights" -H "X-Admin-Key: $ADMIN_KEY"
```

- [ ] **Step 2: Surveiller les logs Railway**

```bash
railway logs --service globagenius -d 2>&1 | grep -iE "ensure_article|article inserted" | head -20
```

Expected dans les ~5 min : `No article for BCN yet, generating now (synchronous)` puis `Article inserted for BCN (slug=..., words=...)`.

- [ ] **Step 3: Vérifier l'article en DB**

```bash
psql "$SUPABASE_URL" -c "SELECT iata, slug, word_count, generated_at FROM articles WHERE iata IS NOT NULL ORDER BY generated_at DESC LIMIT 5;"
```

Expected: au moins une ligne avec `iata` non null et `word_count` ≥ 1500.

- [ ] **Step 4: Visiter la page**

```bash
open https://globegenius.app/destination/<iata généré>
```

Expected:
- Hero avec photo Unsplash + crédit photographe
- Article structuré (top picks, itinéraire 3 jours, infos pratiques, FAQ)
- Deals actifs si présents
- View source : `<script type="application/ld+json">` contient TouristDestination + FAQPage

- [ ] **Step 5: Vérifier le lien Telegram**

Sur l'alerte Telegram réelle reçue, dernière ligne doit être `📖 Le guide complet de <ville>` cliquable.

### Task 9.3: Validation SEO

- [ ] **Step 1: Test indexabilité**

Aller sur Google Search Console (ou rich results test : https://search.google.com/test/rich-results) → tester l'URL `https://globegenius.app/destination/<iata>`.

Expected : pas d'erreur de crawl, schémas TouristDestination + FAQPage détectés.

- [ ] **Step 2: Check meta**

```bash
curl -s https://globegenius.app/destination/<iata> | grep -iE "<title>|description"
```

Expected : title ≤ 60 char, meta description 140-155 char.

---

## Hors-scope (à traiter plus tard si valeur prouvée)

- **Régénération automatique des articles vieux** (>6 mois) — la donnée est stable, ce sera utile dans 1 an seulement.
- **Variantes par origine** : "Vol pas cher Bangkok depuis Marseille" — multiplier par 9 origins = 9× la charge SEO + génération. Attendre les premiers signaux Search Console pour décider.
- **Sitemap dynamique** avec les 70 IATAs : pour l'instant Google découvre via les liens internes (landing → guides + alertes pages publiques). Si on ranke pas sous 4 semaines, ajouter un sitemap.xml généré par crawl.
- **Image alt SEO optimisée** : on met "X — photo de couverture", on pourrait passer 4 mots-clés saisonniers ("Barcelone été plage Catalogne"). À tester.
- **Articles long-form 5000 mots** sur les top 10 destinations à plus fort trafic une fois le trafic mesurable.
- **Localisation EN/ES/IT** — multiplier les pages pour les marchés voisins. Phase 2 produit.
- **Régénération à la demande via UI admin** — pour corriger un article erroné. Pour l'instant, intervention DB directe.
