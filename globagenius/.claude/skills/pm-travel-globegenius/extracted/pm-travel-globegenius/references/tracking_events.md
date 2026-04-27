# Tracking Events — Globe Genius

Référence canonique des événements analytics pour Globe Genius. À utiliser comme source de truth quand un livrable inclut un tracking plan, ou quand un master prompt doit instrumenter une feature.

## Convention de nommage

- Format : `object_action` en snake_case (ex : `deal_clicked`, pas `clickedDeal` ou `DealClicked`).
- Verbes au passé pour les actions complétées (`signup_completed`, pas `signup`).
- Préfixes par domaine quand utile : `subscription_*`, `alert_*`, `deal_*`, `notification_*`.
- Toujours en anglais (standard analytics multi-pays).

## Propriétés communes (envoyées sur tous les événements)

```json
{
  "user_id": "uuid",
  "anonymous_id": "uuid",
  "session_id": "uuid",
  "platform": "web | telegram | ios | android",
  "locale": "fr-FR | en-US | ...",
  "user_tier": "anonymous | free | premium | elite",
  "origin_airport": "CDG | ORY | LYS | ...",
  "timestamp": "ISO 8601"
}
```

## Catalogue d'événements

### Acquisition & onboarding

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `landing_viewed` | Affichage page d'accueil | `referrer`, `utm_source`, `utm_medium`, `utm_campaign` |
| `signup_started` | User clique CTA inscription | `entry_point` (homepage / pricing / blog / deal_page) |
| `signup_completed` | Compte créé avec succès | `signup_method` (email / google / apple) |
| `email_verified` | Lien email cliqué | `delay_minutes` |
| `onboarding_step_completed` | Chaque étape onboarding | `step_number`, `step_name` |
| `onboarding_finished` | Tunnel onboarding complété | `total_duration_seconds`, `steps_skipped` |

### Alertes & préférences

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `alert_created` | Création d'une alerte | `alert_id`, `origin_airports[]`, `destination_type` (anywhere / region / specific), `budget_max`, `duration_min`, `duration_max`, `flexibility_days` |
| `alert_updated` | Modification d'une alerte | `alert_id`, `changed_fields[]` |
| `alert_paused` | Alerte mise en pause | `alert_id`, `pause_reason` (user_request / quota_reached) |
| `alert_deleted` | Alerte supprimée | `alert_id`, `lifetime_days` |
| `preferences_updated` | Modif paramètres globaux | `field_changed`, `old_value`, `new_value` |

### Deals & notifications

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `deal_generated` | Pipeline interne — deal créé par Package Composer | `deal_id`, `score`, `discount_percent`, `baseline_price`, `deal_price`, `route`, `dates` |
| `deal_qualified` | Price Analyst valide le deal | `deal_id`, `freshness_seconds` |
| `notification_sent` | Notifier envoie au user | `deal_id`, `channel` (telegram / push / email), `user_segment` |
| `notification_delivered` | Confirmation de delivery (Telegram callback) | `notification_id`, `latency_ms` |
| `deal_viewed` | User affiche le deal en détail | `deal_id`, `view_source` (telegram / web / email_link) |
| `deal_clicked` | User clique CTA (vers affiliate ou détail) | `deal_id`, `cta_position`, `time_since_notification_seconds` |
| `deal_shared` | User partage le deal | `deal_id`, `share_channel` (whatsapp / link_copy / native) |
| `deal_saved` | User sauvegarde / favorite | `deal_id` |
| `deal_dismissed` | User ferme / mute le deal | `deal_id`, `dismiss_reason` (not_interested / wrong_dates / etc.) |

### Conversion & affiliate

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `affiliate_redirect` | User envoyé vers OTA | `deal_id`, `partner` (booking / expedia / kayak / direct_airline), `affiliate_id` |
| `booking_initiated` | Postback partner — début checkout | `deal_id`, `partner`, `booking_id_partner`, `value_estimated` |
| `booking_confirmed` | Postback partner — booking confirmé (peut arriver J+1 à J+7) | `deal_id`, `partner`, `booking_id_partner`, `value_actual`, `commission_estimated` |
| `booking_cancelled` | Postback partner — annulation | `deal_id`, `partner`, `cancellation_reason`, `delay_days` |

### Subscription / monétisation

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `paywall_viewed` | Affichage page upgrade | `paywall_trigger` (locked_feature / quota_reached / banner_click), `current_tier`, `target_tier` |
| `checkout_started` | User entre dans le tunnel Stripe | `target_tier`, `billing_period` (monthly / annual), `price` |
| `checkout_completed` | Paiement validé | `subscription_id`, `tier`, `billing_period`, `price`, `discount_applied` |
| `subscription_started` | Création subscription Stripe | `subscription_id`, `tier`, `billing_period`, `mrr_value` |
| `subscription_renewed` | Renouvellement automatique | `subscription_id`, `tier`, `cycle_number` |
| `subscription_upgraded` | Free → Premium ou Premium → Elite | `from_tier`, `to_tier`, `mrr_delta` |
| `subscription_downgraded` | Inverse | `from_tier`, `to_tier`, `mrr_delta` |
| `subscription_cancelled` | User annule (effective fin de période) | `subscription_id`, `tier`, `lifetime_days`, `total_paid`, `cancellation_reason` |
| `subscription_churned` | Subscription terminée (post-période) | `subscription_id`, `tier`, `lifetime_days` |
| `subscription_reactivated` | Reprise après annulation | `subscription_id`, `gap_days` |
| `payment_failed` | Échec prélèvement Stripe | `subscription_id`, `failure_reason`, `attempt_number` |
| `dunning_email_sent` | Relance paiement | `subscription_id`, `dunning_step` |

### Telegram bot specific

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `telegram_bot_started` | User envoie /start | `referral_code`, `entry_source` |
| `telegram_command_used` | Commande slash utilisée | `command` (/deals, /alerts, /pause, /upgrade) |
| `telegram_inline_clicked` | Bouton inline cliqué | `button_action`, `deal_id` |
| `telegram_bot_blocked` | User bloque le bot | `lifetime_days`, `messages_received` |

### Engagement & quality

| Event | Trigger | Propriétés spécifiques |
|---|---|---|
| `nps_survey_sent` | Envoi survey NPS | `survey_trigger` (D30 / post_booking) |
| `nps_response` | User répond au NPS | `score` (0-10), `comment`, `tier` |
| `support_ticket_opened` | User contacte support | `category`, `tier` |
| `feedback_submitted` | Feedback in-app | `feature_area`, `sentiment` (positive / neutral / negative) |
| `feature_flag_exposed` | A/B test exposure | `flag_name`, `variant` |

## Règles d'implémentation

- **Émetteur** : tous les événements user-facing partent du client (web/mobile/Telegram), sauf les événements pipeline interne (`deal_generated`, `deal_qualified`, `notification_sent` côté serveur) et les postbacks affiliate (côté serveur).
- **Stockage** : Amplitude (analytics produit) + Postgres event log (pour requêtes ad-hoc et machine learning futur).
- **PII** : ne jamais logger email/téléphone dans les properties. Toujours via `user_id` (uuid).
- **GDPR** : flag `tracking_consent_given` à respecter ; les events restent émis pour les essentiels business (paiement, fraude) mais pas pour analytics quand consentement refusé.
- **Validation** : tous les événements doivent matcher un schéma JSON validé en CI (proto à terme).

## Schéma JSON exemple — `deal_clicked`

```json
{
  "event": "deal_clicked",
  "user_id": "u_a8b3...",
  "anonymous_id": "anon_xyz",
  "session_id": "sess_123",
  "platform": "telegram",
  "locale": "fr-FR",
  "user_tier": "free",
  "origin_airport": "CDG",
  "timestamp": "2026-04-25T14:32:11.291Z",
  "properties": {
    "deal_id": "deal_2026_PAR_BCN_5n",
    "score": 87,
    "discount_percent": 42,
    "baseline_price_eur": 720,
    "deal_price_eur": 418,
    "route": "CDG-BCN",
    "destination_country": "ES",
    "departure_date": "2026-06-12",
    "return_date": "2026-06-17",
    "duration_nights": 5,
    "cta_position": "telegram_inline_button_1",
    "time_since_notification_seconds": 142,
    "view_source": "telegram"
  }
}
```

## Antipatterns à proscrire

- ❌ Événements génériques (`button_clicked` avec un `button_name` — préférer un event dédié pour les CTAs critiques).
- ❌ Propriétés en camelCase mélangées au snake_case.
- ❌ Logger des objets imbriqués profonds (max 1 niveau de nesting dans `properties`).
- ❌ Modifier la structure d'un event existant sans versioning ni migration.
- ❌ Logger côté client des événements financiers (toujours côté serveur, source de truth Stripe).
