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
