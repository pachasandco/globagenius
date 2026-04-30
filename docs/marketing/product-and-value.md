# Globe Genius — Produit & Valeur

> Document de référence interne, descriptif et factuel.
> Source unique pour : email marketing, scripts UGC TikTok, fiches commerciales,
> briefs créatifs, communication externe.
>
> **Aucun élément n'est inventé** — toutes les informations proviennent du code
> en production (commits sur `v7`). Si une information manque ici, elle ne doit
> pas être inventée pour de la communication externe.

---

## 1. Résumé en une phrase

Globe Genius est un service d'alertes de prix pour vols pas chers au départ
de la France. Il surveille en continu les prix sur 9 aéroports français,
détecte automatiquement les baisses anormales, et envoie une notification
Telegram dès qu'un deal est confirmé.

---

## 2. Le produit en clair

### 2.1 Ce que fait le service, concrètement

1. **Collecte des prix** sur les vols au départ de 9 aéroports français vers
   le monde entier, plusieurs fois par jour.
2. **Compare chaque prix** au prix habituel de la même route à la même
   période (saisonnalité prise en compte).
3. **Identifie les anomalies** : un prix significativement inférieur à la
   moyenne des dernières semaines.
4. **Vérifie le prix en temps réel** auprès de la source juste avant
   d'alerter, pour s'assurer qu'il est encore disponible.
5. **Envoie une alerte Telegram** à l'utilisateur dans les minutes qui
   suivent la détection.

L'utilisateur n'a rien à chercher. Il configure une fois ses aéroports de
départ et reçoit les bonnes affaires automatiquement.

### 2.2 Aéroports couverts (9)

CDG, ORY, BVA, LYS, MRS, NCE, BOD, NTE, TLS.

### 2.3 Cadence de mise à jour

- **Routes prioritaires au départ de Paris (CDG/ORY)** : les prix sont mis
  à jour toutes les 20 minutes.
- **Autres aéroports français** : toutes les 2 heures.
- **Une fois un deal détecté**, l'alerte Telegram part dans la foulée
  (typiquement moins de 5 minutes).

### 2.4 Canaux de communication

- **Telegram** : canal principal pour les alertes de deals.
- **Email** : email de bienvenue à l'inscription, email de réinitialisation
  de mot de passe. Pas d'alertes de deals par email.

### 2.5 Ce que le service NE fait PAS

- Il n'est pas une agence de voyage. Il ne vend pas de billets.
- Il ne réserve rien à la place de l'utilisateur. Il fournit le lien de
  réservation, l'utilisateur réserve directement.
- Il ne propose ni hôtels seuls, ni packages vol+hôtel, ni trains, ni bus.
- Il ne propose ni stopovers programmés (escales prolongées type
  Icelandair Stopover), ni hidden-city ticketing.
- Il ne garantit pas la disponibilité du tarif au moment de la réservation
  (les prix peuvent changer entre la détection et la réservation —
  c'est pour cela que la rapidité de l'alerte est importante).

---

## 3. Les types de deals détectés

Le service distingue trois formes de bons plans, chacune notifiée
différemment.

### 3.1 Aller-retour

Le deal classique : un vol A/R sur la même route, dates fixes, prix
total inférieur au prix habituel.

### 3.2 Aller simple

Un seul sens en promotion : soit le départ depuis la France, soit le
retour vers la France. Utile pour les voyages ouverts (tour du monde,
expatriations, séjours longs).

L'utilisateur active ce type d'alerte depuis son profil (par défaut, seuls
les aller-retour sont activés).

### 3.3 Combo malin (split-ticket)

Quand acheter deux billets aller simple séparés (potentiellement chez
deux compagnies différentes) revient moins cher qu'un seul aller-retour.
Le service détecte automatiquement ces opportunités.

L'alerte mentionne explicitement que les bagages et l'annulation sont
gérés séparément pour chaque billet.

C'est une option avancée que l'utilisateur active depuis son profil
(décochée par défaut).

### 3.4 Niveaux de deal (badges visuels dans les alertes)

- **🔴 Erreur de prix** : baisse exceptionnelle (souvent une erreur de
  configuration de la compagnie). Tarif corrigé en quelques heures
  généralement.
- **🟠 Promo flash** : forte promotion temporaire.
- **🟡 Bon deal** : tarif sous la moyenne sans être exceptionnel.

---

## 4. Les offres

### 4.1 Plan Gratuit

- 3 alertes complètes par semaine.
- Deals avec une réduction comprise entre 40% et 50% du prix habituel.
- Au-delà de 60% de réduction, l'utilisateur reçoit un message d'aperçu
  (sans le détail du deal) au maximum 1 fois par semaine.
- Accès à tous les aéroports de départ et tous les types de vols.
- Accès au planificateur de voyage IA en mode démonstration uniquement.

### 4.2 Plan Premium

- Alertes illimitées.
- Tous les deals visibles, y compris les erreurs de prix exceptionnelles.
- Détails complets : prix, dates, lien de réservation directe.
- Accès complet au planificateur de voyage IA.
- Garantie satisfait ou remboursé pendant 30 jours après l'achat.
- 29 €/an au moment de la rédaction (prix de lancement, prix barré
  affiché : 59 €).

### 4.3 Différence en une ligne

Le plan Gratuit est conçu pour découvrir le service et capter quelques
bons deals par mois. Le plan Premium s'adresse à ceux qui veulent ne
manquer aucune opportunité, y compris les meilleures.

---

## 5. Configuration utilisateur

L'utilisateur peut configurer depuis son profil :

- **Aéroports de départ** parmi les 9 disponibles (au moins 1 obligatoire).
- **Types de vols** : aller-retour et/ou aller simple (au moins 1
  obligatoire).
- **Combos malins** : sous-option du type aller-retour.
- **Destinations masquées** : liste de destinations qu'il ne souhaite pas
  voir dans ses alertes (~60 destinations sélectionnables).
- **Compte Telegram** : connexion via un lien personnel généré dans le
  profil. Sans Telegram connecté, aucune alerte de deals n'est envoyée.
- **Email et mot de passe** : modifiables.

L'utilisateur peut aussi mettre ses alertes en pause directement depuis
n'importe quelle alerte Telegram (bouton « ⏸ Pause »), sans passer par le
site.

---

## 6. La valeur

### 6.1 Le problème que résout le produit

- **Chercher un vol pas cher prend du temps**. Comparer 5 sites, sur
  plusieurs dates, pour plusieurs destinations, c'est plusieurs heures
  par mois pour quelqu'un qui voyage régulièrement.
- **Les bons deals durent peu** : une erreur de prix se corrige en
  quelques heures, une promo flash en une journée. Le voyageur qui ne
  surveille pas en continu les rate.
- **Les alertes existantes sont souvent du bruit** : trop d'alertes peu
  qualifiées, ou alertes sur des destinations qui ne nous intéressent
  pas.

### 6.2 Les bénéfices apportés

- **Aucune recherche manuelle**. Le service surveille à la place de
  l'utilisateur, 24h/24.
- **Détection rapide**. La cadence de 20 minutes sur les routes
  prioritaires permet d'attraper les erreurs de prix avant qu'elles
  soient corrigées.
- **Vérification systématique avant alerte**. Un prix qui n'existe plus
  n'est pas alerté.
- **Anti-spam** : un utilisateur Gratuit reçoit au maximum 3 à 4
  notifications par semaine. Pas plus. La déduplication garantit qu'un
  même deal n'est pas envoyé deux fois (sauf si son prix baisse
  significativement).
- **Personnalisation** : l'utilisateur ne reçoit que des alertes pour ses
  aéroports et types de vols choisis.

### 6.3 Pourquoi Telegram et pas l'email

- **Latence** : une notification Telegram arrive en quelques secondes.
  Un email peut traîner plusieurs minutes.
- **Visibilité** : Telegram pousse une notification mobile immédiate,
  difficile à ignorer. L'email finit souvent dans une pile non lue.
- **Format** : les alertes contiennent des boutons d'action (Pause,
  ouvrir le deal) directement utilisables sans changer d'application.

---

## 7. Différenciateurs techniques

Pour un audience averti (presse spécialisée, partenariats, recrutement) :

- **Détection statistique**, pas comparaison de prix simple. Chaque prix
  est comparé à une distribution historique de prix sur la même route à
  la même période, avec calcul d'un z-score.
- **Cascade de baselines à 3 niveaux** : saisonnier (route + bucket de
  durée + mois + délai d'achat) en priorité, puis baselines plus
  génériques en cas de données insuffisantes.
- **Re-vérification temps réel** avant chaque alerte : le prix est
  reconfirmé auprès de la source avant que la notification ne parte.
- **Déduplication par bucket de prix** (50 € de granularité) : un même
  itinéraire ne re-alerte que si son prix baisse significativement.
- **Détection de chutes brutales** : un prix qui chute de plus de 60% en
  moins de 2 heures est traité comme une erreur de prix probable et
  alerte plus rapidement, en bypassant certains filtres statistiques.

---

## 8. Engagements et garanties

- **Garantie satisfait ou remboursé** pendant 30 jours sur le plan
  Premium.
- **Pas de tracking tiers**. Cookies techniques uniquement.
- **Données hébergées en Europe** (Supabase + Railway).
- **Pas de stockage de données bancaires**. Le paiement passe directement
  par Stripe.
- **Conformité RGPD** : droit d'accès, de rectification et de suppression
  pour chaque utilisateur.

---

## 9. Vocabulaire produit

Termes utilisés dans l'interface et les alertes. À reprendre tels quels
dans toute communication pour cohérence.

| Terme | Définition |
|---|---|
| Deal | Bon plan détecté (toute catégorie). |
| Erreur de prix | Tarif anormalement bas, souvent corrigé en quelques heures. |
| Promo flash | Promotion temporaire sur un tarif normal. |
| Bon deal | Tarif sous la moyenne, sans caractère exceptionnel. |
| Aller-retour | Vol A/R sur les mêmes dates. |
| Aller simple | Vol un seul sens (départ ou retour). |
| Combo malin | Deux billets aller simple séparés moins chers qu'un A/R. |
| Routes prioritaires | Routes Paris (CDG/ORY) avec mise à jour 20 minutes. |
| Plan Gratuit / Plan Premium | Les deux niveaux d'abonnement. |
| Aérport de départ | L'aéroport configuré par l'utilisateur. |

---

## 10. Termes à NE PAS utiliser dans la communication externe

- « Skiplagging », « hidden city ticketing » — refus de positionnement
  pour raisons légales.
- « Stopover » au sens d'escale prolongée programmée — pas une
  fonctionnalité du produit.
- « API », « scraping », « web scraping » — jargon technique inutile et
  parfois mal perçu. Préférer « les prix sont mis à jour toutes les
  X minutes ».
- « Algorithme propriétaire » — formule creuse, utiliser à la place
  « détection statistique » ou « surveillance automatisée ».
- Noms spécifiques de compagnies aériennes dans la description du
  fonctionnement du pipeline (Ryanair, Vueling, Transavia, etc.). Ces
  noms peuvent en revanche apparaître dans les exemples de deals
  individuels.
- « Garantie de prix », « garantie de disponibilité » — le service ne
  garantit pas que le prix sera encore disponible au moment de la
  réservation.

---

## 11. Chiffres de référence

Pour les fiches commerciales et les communications chiffrées.

| Information | Valeur |
|---|---|
| Aéroports français couverts | 9 |
| Mise à jour prix routes prioritaires | toutes les 20 minutes |
| Mise à jour prix autres routes | toutes les 2 heures |
| Délai entre détection et alerte | typiquement < 5 minutes |
| Réduction minimum pour qu'un deal soit alerté | 40% |
| Plan Gratuit — alertes complètes par semaine | 3 |
| Plan Gratuit — aperçus de deals exceptionnels par semaine | 1 maximum |
| Plan Premium — prix annuel | 29 € (prix de lancement) |
| Garantie satisfait ou remboursé | 30 jours |
| Période de validité d'un lien de réinitialisation de mot de passe | 1 heure |

---

## 12. Pour aller plus loin

- **Spécifications produit complètes** : voir `ROADMAP.md` à la racine du
  repo (sections « Done », « Killed / Won't do », « Decision log »).
- **Architecture technique** : `ARCHITECTURE.md` à la racine.
- **Évolution récente** : `git log --oneline -30` sur la branche `v7`.
