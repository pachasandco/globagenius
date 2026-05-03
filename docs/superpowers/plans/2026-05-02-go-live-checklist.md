# Go-live checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Boucler les derniers gardes-fous techniques de Globe Genius v9 pour ouvrir aux abonnés payants sans risque silencieux (paiement perdu, alerte cassée, bug runtime non détecté).

**Architecture:** Backend FastAPI sur Railway + Supabase Postgres + Stripe (abonnement annuel) + Brevo (welcome email) + Telegram bot (alertes). Le pipeline scrape ~13k routes/jour de manière indépendante du nombre d'users — donc la « scale » se résume à : sends Telegram, queries DB par dispatch, et trafic web. La capacité réelle est largement suffisante pour 200 abonnés. Les vrais blockers sont **observabilité** (Sentry absent), **trous Stripe** (test E2E manquant + dette migration) et **fonctionnalités RGPD/UX** (annulation self-service, confirmation refund).

**Tech Stack:** Python 3.12, FastAPI, supabase-py, stripe-python, sentry-sdk, pytest, Next.js 16 (frontend, hors scope sauf section 7).

**Branch:** Ce plan s'exécute sur `v9` (commit de départ `0cfb9c7` ou plus récent). Pas de worktree dédié — les tâches sont petites et indépendantes.

**Pré-requis avant de démarrer :**
- Migration `030_password_reset_tokens.sql` doit être appliquée sur Supabase prod (vérifier avec `psql $SUPABASE_URL -c "\d password_reset_tokens"`).
- Variables Railway prod déjà set : `BREVO_API_KEY`, `BREVO_WELCOME_TEMPLATE_ID=1`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` (à confirmer en Phase 0).

**Critère go/no-go pour ouvrir aux abonnés :**
- [ ] Phase 0, 1, 2, 3, 4 vertes
- [ ] Test paiement-refund-cancel manuel passé (Phase 5)
- [ ] 24h de soak en prod sans erreur Sentry > niveau warning
- [ ] Au moins 1 alerte Telegram réelle reçue après V9 deploy

---

## File structure

| Fichier | Statut | Responsabilité |
|---|---|---|
| `backend/requirements.txt` | modify | Ajouter `sentry-sdk[fastapi]==2.20.0` |
| `backend/app/main.py` | modify | Init Sentry au boot ; healthcheck enrichi |
| `backend/app/api/routes.py` | modify | Endpoint `/health/deep` ; endpoint `POST /api/users/me/cancel-subscription` |
| `backend/supabase/migrations/031_stripe_columns.sql` | create | Réintégrer `stripe_customer_id`, `stripe_subscription_id`, `is_premium` en migration (idempotent — colonnes déjà en prod) |
| `backend/tests/test_health_deep.py` | create | Tests TDD pour `/health/deep` |
| `backend/tests/test_user_cancel_subscription.py` | create | Tests TDD pour annulation self-service |
| `backend/tests/test_stripe_e2e.py` | create | Test E2E checkout → webhook → premium activé |
| `frontend/src/app/profile/page.tsx` | modify | Bouton « Annuler mon abonnement » (premium-only) |
| `frontend/src/lib/api.ts` | modify | Helper `cancelSubscription()` |
| `docs/runbooks/go-live.md` | create | Runbook : vars Railway à vérifier, commandes de smoke test, premier diagnostic en cas d'incident |

---

## Phase 0 — Pré-flight (no code, 15 min)

### Task 0.1: Vérifier que les vars Railway prod sont set

- [ ] **Step 1: Lister les vars Stripe / Brevo / Telegram en prod**

```bash
railway variables --service globagenius --environment production --kv 2>&1 | grep -iE "^(STRIPE|BREVO|SMTP|TELEGRAM|SENTRY|ADMIN_API_KEY)" | sed -E 's/=(.{15}).+/=\1***REDACTED***/'
```

Expected output (chaque ligne doit apparaître) :
```
ADMIN_API_KEY=fa97eda7769d5fa***REDACTED***
BREVO_API_KEY=xkeysib-079602c***REDACTED***
BREVO_WELCOME_TEMPLATE_ID=1
SMTP_HOST=smtp-relay.brevo.com
STRIPE_PRICE_ID=price_1TN6eFDBicGh3pGqHpuZO6Ym
STRIPE_SECRET_KEY=sk_live_...***REDACTED***
STRIPE_WEBHOOK_SECRET=whsec_...***REDACTED***
TELEGRAM_ADMIN_CHAT_ID=...
TELEGRAM_BOT_TOKEN=...***REDACTED***
```

- [ ] **Step 2: Si une variable manque, l'ajouter**

```bash
railway variables --service globagenius --environment production --set NOM=valeur
```

- [ ] **Step 3: Vérifier la migration 030 sur Supabase prod**

```bash
psql "$SUPABASE_URL" -c "\d password_reset_tokens"
```

Expected: tableau `password_reset_tokens` existe avec colonnes `token, user_id, expires_at, used_at, created_at`.

Si absent : appliquer maintenant
```bash
psql "$SUPABASE_URL" -f backend/supabase/migrations/030_password_reset_tokens.sql
```

- [ ] **Step 4: Confirmer que le tier1 scraper landing des rows en prod**

```bash
ADMIN_KEY=$(railway variables --service globagenius --environment production --kv 2>&1 | grep '^ADMIN_API_KEY=' | cut -d'=' -f2)
curl -s "https://globagenius-production-1380.up.railway.app/api/admin/scrapers/health" -H "X-Admin-Key: $ADMIN_KEY" | python3 -m json.tool | head -30
```

Expected: chaque scraper (`ryanair_direct`, `vueling_direct`, `travelpayouts`) affiche `rows_in_db_24h > 0` et `alert: false`.

Si un scraper a `alert: true` → STOP, fixer le scraper avant de continuer.

---

## Phase 1 — Sentry pour la visibilité runtime (45 min)

Sans Sentry tu ne sais pas qu'un user a une 500 au signup. Indispensable avant l'ouverture aux payants.

### Task 1.1: Ajouter sentry-sdk en dépendance

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Ajouter la dépendance**

Insérer cette ligne dans `backend/requirements.txt` juste après `slowapi==0.1.9` :
```
sentry-sdk[fastapi]==2.20.0
```

- [ ] **Step 2: Installer localement**

```bash
cd backend && .venv/bin/pip install -r requirements.txt
```

Expected: `Successfully installed sentry-sdk-2.20.0` ou similaire.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add sentry-sdk for runtime error monitoring"
```

### Task 1.2: Initialiser Sentry au boot avec gating sur DSN

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Ajouter le bloc d'init Sentry tout en haut du fichier**

Dans `backend/app/main.py`, juste après `import os` (ligne 16) et avant le premier `logger.info(...)`, insérer :

```python
# ── Sentry init ──
# Initialised before anything else so any boot-time exception (DB
# connection, Stripe key validation, Telegram token check) gets reported.
# DSN is read from SENTRY_DSN env var; if absent, sentry-sdk is a no-op
# so dev / CI runs stay quiet.
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=os.getenv("APP_ENV", "production"),
            release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev"),
            traces_sample_rate=0.05,  # 5% of requests get a trace
            profiles_sample_rate=0.0,  # profiling off, costs extra
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=40),  # WARNING+
            ],
            send_default_pii=False,  # never send Authorization headers / cookies
        )
        logger.info("Sentry initialised — environment=%s", os.getenv("APP_ENV", "production"))
    except Exception as e:
        # Never block startup on a Sentry import / init issue.
        logger.error("Sentry init failed (continuing without it): %s", e)
```

- [ ] **Step 2: Smoke-test que main.py importe sans crasher**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "from app.main import app; print('main import OK')"
```

Expected: `main import OK` (et probablement un log "Sentry initialised" ou rien si SENTRY_DSN absent en local).

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(monitoring): initialise Sentry at boot, gated on SENTRY_DSN env var"
```

### Task 1.3: Créer le projet Sentry et configurer Railway

⚠️ **Action manuelle hors-code** — l'engineer ne fait pas de commit ici.

- [ ] **Step 1: Créer un projet Sentry**

1. Aller sur https://sentry.io/ → nouveau projet
2. Platform : Python / FastAPI
3. Project name : `globe-genius-backend`
4. Copier le DSN proposé (forme : `https://abc123@o1234567.ingest.sentry.io/9876543`)

- [ ] **Step 2: Configurer Railway**

```bash
railway variables --service globagenius --environment production --set SENTRY_DSN=<le DSN copié>
```

Railway va automatiquement redéployer. Attendre ~2 min.

- [ ] **Step 3: Vérifier que Sentry reçoit bien**

Dans Sentry UI, project `globe-genius-backend`, onglet "Issues". Lancer un test d'erreur volontaire :

```bash
ADMIN_KEY=$(railway variables --service globagenius --environment production --kv 2>&1 | grep '^ADMIN_API_KEY=' | cut -d'=' -f2)
# Trigger a 500 by hitting a forbidden admin op without the key
curl -s -o /dev/null -w "%{http_code}\n" "https://globagenius-production-1380.up.railway.app/api/admin/scrapers/health" -H "X-Admin-Key: WRONG"
```

Expected: 403 — pas une erreur Sentry (auth refusal != bug).

Pour vraiment tester Sentry, créer un endpoint admin éphémère qui lève une exception, ou attendre la première erreur naturelle.

---

## Phase 2 — Healthcheck enrichi (30 min)

Le `/health` actuel ne prouve rien sauf que le process Python tourne. À l'ouverture aux abonnés, on veut savoir si la DB répond, si le bot Telegram a un token, si Stripe a sa clé. Sans ça, un load balancer continue de router vers une instance cassée.

### Task 2.1: TDD — endpoint /health/deep

**Files:**
- Create: `backend/tests/test_health_deep.py`

- [ ] **Step 1: Écrire le test (failing)**

Créer `backend/tests/test_health_deep.py` :

```python
"""Tests for the deep healthcheck endpoint.

The shallow /health endpoint just confirms the process is alive.
/health/deep additionally checks each external dependency and reports
status per component so a load balancer or monitoring system can
detect a degraded — but not crashed — instance.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_health_deep_returns_200_when_all_components_healthy():
    """Happy path: DB, Stripe key, Telegram token all present → 200 + ok."""
    from app.main import app
    client = TestClient(app)

    # Mock the DB ping query so we don't need a real Supabase
    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["components"]["db"] == "ok"
    assert body["components"]["stripe"] == "ok"
    assert body["components"]["telegram"] == "ok"
    assert body["components"]["brevo"] == "ok"


def test_health_deep_returns_503_when_db_is_down():
    """If the DB ping raises, /health/deep returns 503 with detail."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.side_effect = RuntimeError("connection refused")

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["components"]["db"] == "error"


def test_health_deep_returns_503_when_stripe_key_missing():
    """Misconfig: Stripe key empty → degraded."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", ""), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", "tok"), \
         patch("app.api.routes.settings.BREVO_API_KEY", "xkeysib-x"):
        r = client.get("/health/deep")
    assert r.status_code == 503
    assert r.json()["components"]["stripe"] == "missing"


def test_health_deep_lists_telegram_brevo_status_individually():
    """Each component is reported separately so we can spot a partial outage."""
    from app.main import app
    client = TestClient(app)

    db_mock = MagicMock()
    db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db", db_mock), \
         patch("app.api.routes.settings.STRIPE_SECRET_KEY", "sk_test_x"), \
         patch("app.api.routes.settings.TELEGRAM_BOT_TOKEN", ""), \
         patch("app.api.routes.settings.BREVO_API_KEY", ""):
        r = client.get("/health/deep")
    body = r.json()
    assert body["components"]["telegram"] == "missing"
    assert body["components"]["brevo"] == "missing"
```

- [ ] **Step 2: Run pour vérifier que ça FAIL**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_health_deep.py -v
```

Expected: 4 failures (l'endpoint n'existe pas encore → 404).

### Task 2.2: Implémenter /health/deep

**Files:**
- Modify: `backend/app/api/routes.py:256-258` (juste après `/health` existant)

- [ ] **Step 1: Ajouter l'endpoint**

Dans `backend/app/api/routes.py`, après la fonction `health()` actuelle (ligne ~258), insérer :

```python
@router.get("/health/deep")
def health_deep():
    """Deep healthcheck: ping DB + verify external service config.

    Used by uptime monitors and load balancers that need to know
    whether the instance is degraded (running but unable to do its
    job) versus simply alive.
    Returns HTTP 200 when every component is "ok", 503 otherwise.
    """
    components: dict[str, str] = {}

    # 1. DB ping — a 'select 1' equivalent via supabase-py
    try:
        if db is None:
            components["db"] = "missing"
        else:
            db.table("users").select("id").limit(1).execute()
            components["db"] = "ok"
    except Exception as e:
        components["db"] = "error"
        logger.warning(f"/health/deep: DB ping failed: {e}")

    # 2. Stripe — we don't make a network call (would slow each check),
    # we just confirm the secret key is configured.
    components["stripe"] = "ok" if settings.STRIPE_SECRET_KEY else "missing"

    # 3. Telegram bot token presence
    components["telegram"] = "ok" if settings.TELEGRAM_BOT_TOKEN else "missing"

    # 4. Brevo API key presence
    components["brevo"] = "ok" if settings.BREVO_API_KEY else "missing"

    overall_ok = all(v == "ok" for v in components.values())
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "components": components,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if overall_ok:
        return payload
    raise HTTPException(status_code=503, detail=payload)
```

- [ ] **Step 2: Run pour vérifier que ça PASS**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_health_deep.py -v
```

Expected: `4 passed`.

- [ ] **Step 3: Smoke en local**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "
from fastapi.testclient import TestClient
from app.main import app
r = TestClient(app).get('/health/deep')
print('status', r.status_code)
print('body', r.json())
"
```

Expected: les composants `db`, `stripe`, `telegram`, `brevo` apparaissent. En local certains peuvent être `missing` — c'est attendu.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes.py backend/tests/test_health_deep.py
git commit -m "feat(monitoring): /health/deep endpoint with per-component status"
```

---

## Phase 3 — Migration SQL pour les colonnes Stripe (15 min)

Les colonnes `stripe_customer_id`, `stripe_subscription_id`, `is_premium` existent en prod (vérifié) mais aucune migration ne les crée. Une nouvelle instance ne pourrait pas être reconstruite.

### Task 3.1: Créer la migration idempotente

**Files:**
- Create: `backend/supabase/migrations/031_stripe_columns.sql`

- [ ] **Step 1: Créer le fichier**

Créer `backend/supabase/migrations/031_stripe_columns.sql` avec :

```sql
-- 031_stripe_columns.sql
-- Reconcile schema with prod: stripe_customer_id, stripe_subscription_id
-- and is_premium were added directly through the Supabase UI when the
-- Stripe integration was wired up. This migration records that schema
-- in repo so a fresh environment (staging, local, dev) matches prod.
-- Idempotent: every column is `IF NOT EXISTS` so applying on prod is a no-op.

ALTER TABLE user_preferences
    ADD COLUMN IF NOT EXISTS stripe_customer_id text,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id text,
    ADD COLUMN IF NOT EXISTS is_premium boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_user_prefs_stripe_customer
    ON user_preferences(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_prefs_stripe_subscription
    ON user_preferences(stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;
```

- [ ] **Step 2: Tester le SQL en local (dry-run dans une DB jetable, optionnel)**

Si l'engineer a un Postgres local, valider :
```bash
psql "$LOCAL_PG" -f backend/supabase/migrations/031_stripe_columns.sql
psql "$LOCAL_PG" -c "\d user_preferences" | grep -E "stripe|is_premium"
```

Si pas de Postgres local, sauter ce step — la migration est triviale et l'idempotence des `IF NOT EXISTS` garantit qu'elle ne casse rien.

- [ ] **Step 3: Appliquer en prod**

```bash
psql "$SUPABASE_URL" -f backend/supabase/migrations/031_stripe_columns.sql
```

Expected output: `ALTER TABLE` `CREATE INDEX` `CREATE INDEX` (ou `NOTICE: relation already exists, skipping` si déjà là — c'est normal).

- [ ] **Step 4: Commit**

```bash
git add backend/supabase/migrations/031_stripe_columns.sql
git commit -m "db(migration): record Stripe columns in user_preferences (idempotent)"
```

---

## Phase 4 — Annulation self-service de l'abonnement (1h)

Aujourd'hui, un user qui veut annuler doit nous écrire ou supprimer son compte (qui annule via `_cancel_stripe_subscription_for_user` depuis `cc7d1ac`). Il faut un bouton « Annuler mon abonnement » dans `/profile` qui annule sans supprimer le compte.

### Task 4.1: TDD — backend POST /api/users/me/cancel-subscription

**Files:**
- Create: `backend/tests/test_user_cancel_subscription.py`

- [ ] **Step 1: Écrire les tests (failing)**

Créer `backend/tests/test_user_cancel_subscription.py` :

```python
"""Tests for the user-initiated subscription cancellation endpoint.

Reuses the helper _cancel_stripe_subscription_for_user(user_id) added
in cc7d1ac. Difference vs delete_account: the user keeps their account,
they just don't pay anymore. The underlying Stripe call is the same,
so we can rely on the helper's existing test coverage and only assert
the endpoint glue: auth, idempotency, response shape.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _client_with_auth(user_id: str = "u1"):
    """Spin up a TestClient and patch get_current_user to return user_id."""
    from app.main import app
    from app.api import routes

    async def fake_get_current_user(*args, **kwargs):
        return {"sub": user_id, "user_id": user_id}

    app.dependency_overrides[routes.get_current_user] = fake_get_current_user
    return TestClient(app)


def test_cancel_subscription_requires_auth():
    """Unauthenticated requests are 401, never reach the helper."""
    from app.main import app
    client = TestClient(app)
    r = client.post("/api/users/me/cancel-subscription")
    assert r.status_code in (401, 403)


def test_cancel_subscription_calls_helper_and_returns_ok():
    """Authenticated user with active subscription → helper called,
    response says cancelled=true."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": True,
        "cancelled": True,
        "subscription_id": "sub_x",
        "error": None,
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 200
        body = r.json()
        assert body["cancelled"] is True
        assert body["had_subscription"] is True
        helper_mock.assert_called_once_with("u1")
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_cancel_subscription_returns_200_when_user_has_no_subscription():
    """Free user (or already cancelled): no Stripe call, 200 with had_subscription=false.
    Idempotent — clicking the button twice doesn't 500."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": False,
        "cancelled": False,
        "subscription_id": None,
        "error": None,
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 200
        body = r.json()
        assert body["had_subscription"] is False
    finally:
        from app.main import app
        app.dependency_overrides.clear()


def test_cancel_subscription_returns_502_when_stripe_errors():
    """Stripe outage: surface a 502 so the frontend can show
    'réessayez dans quelques minutes' rather than a silent success."""
    from app.api import routes

    client = _client_with_auth("u1")
    helper_mock = MagicMock(return_value={
        "had_subscription": True,
        "cancelled": False,
        "subscription_id": "sub_x",
        "error": "stripe_unknown: connection error",
    })
    try:
        with patch.object(routes, "_cancel_stripe_subscription_for_user", helper_mock):
            r = client.post("/api/users/me/cancel-subscription")
        assert r.status_code == 502
        assert "stripe" in r.json().get("detail", "").lower()
    finally:
        from app.main import app
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run pour vérifier que ça FAIL**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_user_cancel_subscription.py -v
```

Expected: 3 tests fail (404 endpoint not found), 1 passe (auth refusal).

### Task 4.2: Implémenter l'endpoint

**Files:**
- Modify: `backend/app/api/routes.py` — ajouter à proximité de `delete_account` (~ligne 2000)

- [ ] **Step 1: Localiser l'endroit**

```bash
grep -n "@router.delete(\"/api/users/{user_id}/account\")" backend/app/api/routes.py
```

Note la ligne (autour de ~1996 après les commits Stripe récents).

- [ ] **Step 2: Insérer le nouvel endpoint juste avant `@router.delete("/api/users/{user_id}/account"`)**

```python
@router.post("/api/users/me/cancel-subscription", status_code=200)
def cancel_subscription_self(current_user: dict = Depends(get_current_user)):
    """User-initiated subscription cancellation.

    Reuses _cancel_stripe_subscription_for_user(). The user's account
    stays intact; only the Stripe subscription is cancelled. Stripe
    fires customer.subscription.deleted shortly after, which the
    webhook turns into is_premium=False — so the user keeps premium
    until the end of their paid period (Stripe behaviour) but no new
    invoice is generated.

    Idempotent: calling it on a free user returns 200 with
    had_subscription=False. A Stripe error returns 502 so the frontend
    can prompt a retry.
    """
    user_id = current_user.get("user_id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="auth missing")

    result = _cancel_stripe_subscription_for_user(user_id)

    if result["had_subscription"] and not result["cancelled"]:
        # Stripe is supposed to have cancelled the sub but didn't.
        # 502 because the Stripe upstream is the failing dependency.
        raise HTTPException(
            status_code=502,
            detail=f"stripe cancellation failed: {result.get('error') or 'unknown'}"
        )

    return {
        "ok": True,
        "had_subscription": result["had_subscription"],
        "cancelled": result["cancelled"],
    }
```

- [ ] **Step 3: Run les tests pour vérifier**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_user_cancel_subscription.py -v
```

Expected: `4 passed`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes.py backend/tests/test_user_cancel_subscription.py
git commit -m "feat(account): self-service subscription cancellation endpoint"
```

### Task 4.3: Frontend — bouton « Annuler mon abonnement »

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/profile/page.tsx`

- [ ] **Step 1: Ajouter le helper API**

Dans `frontend/src/lib/api.ts`, après le bloc `updatePreferences(...)`, insérer :

```typescript
export async function cancelSubscription(): Promise<{
  ok: boolean;
  had_subscription: boolean;
  cancelled: boolean;
}> {
  const token = typeof window !== "undefined" ? localStorage.getItem("gg_token") : "";
  const res = await fetch(`${API_BASE}/api/users/me/cancel-subscription`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
```

- [ ] **Step 2: Ajouter l'import + le state + le handler dans la page profile**

Dans `frontend/src/app/profile/page.tsx`:

A. Imports (en haut) — ajouter `cancelSubscription` à la liste existante :
```typescript
import {
  // ...existing imports...
  cancelSubscription,
} from "@/lib/api";
```

B. State (à proximité des autres `useState`) :
```typescript
const [cancellingSubscription, setCancellingSubscription] = useState(false);
const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
```

C. Handler (à proximité de `handleSave`) :
```typescript
async function handleCancelSubscription() {
  setCancellingSubscription(true);
  setError("");
  try {
    const r = await cancelSubscription();
    if (r.had_subscription) {
      setSuccess("Abonnement annulé. Vous gardez Premium jusqu'à la fin de la période en cours.");
    } else {
      setSuccess("Aucun abonnement actif à annuler.");
    }
    setCancelConfirmOpen(false);
    setTimeout(() => setSuccess(""), 6000);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Erreur d'annulation");
  } finally {
    setCancellingSubscription(false);
  }
}
```

D. Le bouton — placer dans la zone "Compte" du profile, gated sur `isPremium`. Chercher la section qui contient `showDeleteConfirm` (suppression de compte) et insérer juste avant :

```jsx
{isPremium && (
  <div className="mb-8 p-4 border border-[var(--color-sand)] rounded-xl bg-white">
    <h3 className="font-semibold text-[var(--color-ink)] mb-1">Abonnement Premium</h3>
    <p className="text-sm text-gray-500 mb-3">
      Vous pouvez annuler à tout moment. Vous gardez l'accès Premium jusqu'à la fin de la
      période payée. Aucun nouveau prélèvement.
    </p>
    {!cancelConfirmOpen ? (
      <button
        type="button"
        onClick={() => setCancelConfirmOpen(true)}
        className="text-sm text-[var(--color-coral)] hover:underline"
      >
        Annuler mon abonnement
      </button>
    ) : (
      <div className="flex gap-2 items-center">
        <button
          type="button"
          onClick={handleCancelSubscription}
          disabled={cancellingSubscription}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold"
        >
          {cancellingSubscription ? "Annulation…" : "Confirmer l'annulation"}
        </button>
        <button
          type="button"
          onClick={() => setCancelConfirmOpen(false)}
          className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
        >
          Garder l'abonnement
        </button>
      </div>
    )}
  </div>
)}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: aucune sortie (pas d'erreur TypeScript).

- [ ] **Step 4: Smoke en dev (optionnel mais recommandé)**

```bash
cd frontend && npm run dev
```

Aller sur `/profile` en tant qu'user premium, vérifier que le bouton apparaît, qu'il y a une étape de confirmation, qu'aucun bouton n'apparaît pour un user free.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/app/profile/page.tsx
git commit -m "feat(profile): self-service subscription cancellation button"
```

---

## Phase 5 — Test E2E paiement-refund (no code, 1h)

Pas de PR ici — c'est un test manuel obligatoire avant l'ouverture aux payants.

### Task 5.1: Tester checkout → premium activation

⚠️ **Action manuelle**.

- [ ] **Step 1: Préparer une carte test live**

Stripe test cards : https://stripe.com/docs/testing
- Carte qui réussit : `4242 4242 4242 4242`, n'importe quelle date future, n'importe quel CVC.
- Si tu utilises une vraie carte → le paiement sera réel. Refund après pour récupérer les 29€.

- [ ] **Step 2: S'abonner**

1. Aller sur https://globegenius.app/login
2. Login avec un compte test (ou créer un nouveau compte au préalable)
3. Aller dans `/profile` ou `/home`, cliquer sur l'option d'abonnement Premium
4. Compléter le checkout Stripe avec la carte test

- [ ] **Step 3: Vérifier l'activation premium**

Côté DB:
```bash
psql "$SUPABASE_URL" -c "SELECT user_id, is_premium, premium_expires_at, stripe_customer_id, stripe_subscription_id FROM user_preferences WHERE stripe_customer_id IS NOT NULL ORDER BY updated_at DESC LIMIT 5;"
```

Expected: la ligne du user qui vient d'être abonné doit avoir `is_premium=true` et `premium_expires_at` dans ~1 an.

Côté Telegram: dans les ~5 min, vérifier qu'il/elle reçoit une alerte si le pipeline détecte un deal sur ses aéroports.

### Task 5.2: Tester l'annulation self-service

- [ ] **Step 1: Cliquer sur « Annuler mon abonnement » dans /profile**

Attendre la confirmation visuelle "Abonnement annulé. Vous gardez Premium jusqu'à la fin de la période en cours."

- [ ] **Step 2: Vérifier côté Stripe**

Dans le dashboard Stripe → Customers → trouver le customer → la subscription doit être `cancelled` ou `cancel_at_period_end=true`.

- [ ] **Step 3: Vérifier côté DB**

```bash
psql "$SUPABASE_URL" -c "SELECT user_id, is_premium, stripe_subscription_id FROM user_preferences WHERE user_id='<le user_id>';"
```

Expected: `is_premium` peut encore être `true` (Stripe garde l'accès jusqu'à fin de période → c'est correct), `stripe_subscription_id` peut encore être présent (Stripe envoie `customer.subscription.deleted` plus tard).

### Task 5.3: Tester le refund

- [ ] **Step 1: Faire un refund depuis Stripe**

Dashboard Stripe → Payments → trouver le paiement → bouton "Refund".

- [ ] **Step 2: Attendre 30 secondes (le webhook arrive)**

Vérifier les logs Railway :
```bash
railway logs --service globagenius -d 2>&1 | grep -i "refund" | head -5
```

Expected: `Premium revoked (refund) for customer cus_...`

- [ ] **Step 3: Vérifier côté DB**

```bash
psql "$SUPABASE_URL" -c "SELECT user_id, is_premium, premium_expires_at FROM user_preferences WHERE stripe_customer_id='<le customer_id>';"
```

Expected: `is_premium=false`, `premium_expires_at` dans le passé.

### Task 5.4: Tester la suppression de compte avec abonnement actif

⚠️ **Refaire un signup + abonnement** (ou réutiliser le test card avec un compte différent).

- [ ] **Step 1: Cliquer "Supprimer mon compte" dans /profile**

- [ ] **Step 2: Vérifier que la subscription Stripe est cancelled**

Dashboard Stripe → la subscription doit être `cancelled` immédiatement (pas `cancel_at_period_end`).

- [ ] **Step 3: Vérifier que la DB est nettoyée**

```bash
psql "$SUPABASE_URL" -c "SELECT id, email FROM users WHERE email='<le email du compte test>';"
```

Expected: 0 rows.

---

## Phase 6 — Runbook go-live (15 min)

Documenter ce qu'il faut savoir en cas d'incident dans les premières 48h.

### Task 6.1: Créer le runbook

**Files:**
- Create: `docs/runbooks/go-live.md`

- [ ] **Step 1: Créer le fichier**

```bash
mkdir -p docs/runbooks
```

Créer `docs/runbooks/go-live.md` avec :

```markdown
# Go-live runbook

Premier diagnostic à dégainer en cas d'incident dans les 48h post-ouverture aux abonnés payants.

## Variables Railway prod indispensables

```bash
railway variables --service globagenius --environment production --kv 2>&1 | grep -iE "^(STRIPE|BREVO|SMTP|TELEGRAM|SENTRY|ADMIN_API_KEY|SUPABASE)"
```

Toutes ces variables doivent être set. Si l'une manque → l'app démarre mais une feature est cassée silencieusement.

## Smoke tests

### App vivante
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://globagenius-production-1380.up.railway.app/health
# Expected: 200
```

### Composants OK
```bash
curl -s https://globagenius-production-1380.up.railway.app/health/deep | jq
# Expected: status=ok, components.{db,stripe,telegram,brevo}=ok
```

### Scrapers landent des rows
```bash
ADMIN_KEY=$(railway variables --service globagenius --environment production --kv 2>&1 | grep '^ADMIN_API_KEY=' | cut -d'=' -f2)
curl -s "https://globagenius-production-1380.up.railway.app/api/admin/scrapers/health" -H "X-Admin-Key: $ADMIN_KEY" | jq '.scrapers[] | {source, rows_in_db_24h, alert}'
# Expected: chaque scraper alert=false et rows_in_db_24h > 0
```

### Brevo accessible depuis Railway
```bash
curl -s https://globagenius-production-1380.up.railway.app/api/admin/email/diagnose -H "X-Admin-Key: $ADMIN_KEY" | jq '.brevo_account_probe_status'
# Expected: 200
```

## Incidents possibles dans les 48h

### "Un user a payé, n'a pas reçu d'alerte"
1. Vérifier `is_premium=true` en DB pour ce user_id.
2. Vérifier `telegram_chat_id` non null (sinon il n'a pas connecté Telegram).
3. Vérifier `airport_codes` non vide.
4. Lancer une re-detection :
   ```bash
   curl -X POST "https://globagenius-production-1380.up.railway.app/api/trigger/scrape_flights" -H "X-Admin-Key: $ADMIN_KEY"
   ```
5. Si toujours rien dans 30 min → regarder Sentry pour exceptions sur `_dispatch_grouped_flight_alerts`.

### "Un user a annulé, c'est encore débité le mois suivant"
1. Vérifier la subscription dans Stripe dashboard. Doit être `cancelled` ou `cancel_at_period_end=true`.
2. Si `active` encore → le helper `_cancel_stripe_subscription_for_user` a échoué silencieusement. Logs : grep `Stripe cancellation failed` dans Railway logs.
3. Annuler manuellement depuis Stripe dashboard.

### "Brevo bloque les emails (IP changed)"
1. Récupérer la nouvelle IP Railway :
   ```bash
   curl -s https://globagenius-production-1380.up.railway.app/api/admin/email/diagnose -H "X-Admin-Key: $ADMIN_KEY" | jq '.outbound_ip'
   ```
2. Aller sur https://app.brevo.com/security/authorised_ips
3. Soit désactiver la whitelist, soit ajouter la nouvelle IP.

### "Sentry me ping sur une 500 récurrente"
1. Aller sur sentry.io, project `globe-genius-backend`, identifier l'issue.
2. Si endpoint = `/api/auth/signup` → probablement validation email DNS qui timeout. Vérifier la latence DNS depuis Railway.
3. Si endpoint = `/api/stripe/webhook` → probablement signature mismatch. Vérifier `STRIPE_WEBHOOK_SECRET` matche bien le webhook configuré dans Stripe dashboard.

## Rollback rapide

Si un commit récent casse la prod :

```bash
git checkout v9
git revert HEAD --no-edit
git push origin v9
# Railway redéploie automatiquement en ~2 min
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/runbooks/go-live.md
git commit -m "docs(runbooks): go-live first-incident playbook"
```

---

## Phase 7 — Post-déploiement : observation 24h (no code)

### Task 7.1: Soak en prod sans incident

⚠️ **Étape de validation**, pas un commit.

- [ ] **Step 1: Push toute la branche**

```bash
git push origin v9
```

Railway redéploie automatiquement.

- [ ] **Step 2: Attendre 5 min, vérifier le boot**

```bash
railway logs --service globagenius -d 2>&1 | head -20 | grep -iE "started|sentry"
```

Expected:
- `Sentry initialised — environment=production`
- `Scheduler started with N jobs`

- [ ] **Step 3: Lancer les smoke tests du runbook**

Voir `docs/runbooks/go-live.md` section "Smoke tests". Tout doit passer.

- [ ] **Step 4: Surveiller Sentry pendant 24h**

Surveiller https://sentry.io project `globe-genius-backend`. Critère go : aucun nouvel "issue" de niveau `error` ou `fatal` après le redéploiement.

Si une issue apparaît → fixer avant d'ouvrir aux payants.

### Task 7.2: Critère final go/no-go

- [ ] Tous les checkboxes ci-dessus cochés
- [ ] Phase 5 (test paiement-refund) passée intégralement
- [ ] 24h de soak Sentry sans issue niveau error/fatal
- [ ] Au moins 1 alerte Telegram réelle reçue par le compte test depuis V9 deploy
- [ ] Le watchdog scrapers (V8.3) n'a envoyé aucune alerte admin pendant ces 24h

Si tous les ✅ → **GO** pour ouverture aux abonnés payants. Sinon, identifier le bloquant et reprendre la phase concernée.

---

## Hors-scope (à traiter après le go-live)

Liste explicite de ce qui n'est PAS dans ce plan, par décision :

- **Test E2E Stripe automatisé** : Phase 5 le fait à la main. Un test E2E complet (TestClient + mock Stripe API + mock webhook) demande ~3h supplémentaires et ne dégage pas de valeur tant qu'on a pas testé manuellement une fois.
- **Cookies banner / DPA Brevo / page "exporter mes données" RGPD article 20** : à faire quand on dépasse 50 users payants.
- **Caching HTTP sur `/api/landing/deals`** : pertinent à >100 users actifs simultanés. Aujourd'hui le pipeline est largement sous-utilisé côté trafic web.
- **Connection pooling DB** : pertinent à >300 users payants. Supabase free tier (60 connexions) est largement suffisant pour les 200 premiers.
- **Watchdog étendu (Stripe / Brevo errors)** : à ajouter si Sentry ne suffit pas après 1 mois de prod.
- **Migration vers async Supabase client** : refactor lourd, pas de gain visible sous 500 users.
