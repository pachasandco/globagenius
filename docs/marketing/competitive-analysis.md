# Analyse concurrentielle — GlobeGenius

*Première rédaction : 2026-05-22. Snapshot du paysage à cette date — à
rafraîchir quand les concurrents évoluent (nouveau pricing, lancement
français, etc.).*

## Définition du marché

GlobeGenius opère sur le segment **"flight deal alerts"** : services
qui détectent en continu les baisses de prix et notifient les abonnés
de manière push, par opposition aux agrégateurs de recherche
(Skyscanner, Google Flights, Kayak) où l'utilisateur cherche
activement.

## Mapping concurrentiel

### Tier 1 — concurrents directs

| Concurrent          | Modèle                              | Couverture                  | Pricing            | Audience       |
| ------------------- | ----------------------------------- | --------------------------- | ------------------ | -------------- |
| Going (ex-Scott's Cheap Flights) | Newsletter + app, alertes par origine | Hubs US d'abord, EU couvert mais peu prio FR | Free / 49 $ / 199 $ an | Anglophone, 2 M+ subs |
| Jack's Flight Club  | Newsletter, 2-3 deals/sem           | UK – FR – DE – IE           | Free / 49 £ an     | Premium UK     |
| Holiday Pirates     | Newsletter + app, deals packagés    | EU large, FR existe mais light | 100 % gratuit (affiliation) | Mainstream EU |
| Secret Flying       | Site web + email, mistake fares     | Mondial, FR mentionné       | Free, ad-supported | Hardcore deal hunters |
| Travelzoo           | Newsletter "Top 20", deals + hotels | EU + US                     | Free, commission affiliate | Mainstream older |

### Tier 2 — concurrents indirects

- **Skyscanner / Google Flights** : recherche active, pas d'alertes push
- **Hopper** : prédiction de prix + booking direct
- **Telegram channels gratuits FR** (@deals_voyage, @flightfares_fr) :
  volume gratuit, qualité variable, zéro personnalisation

## Forces différenciantes (uniques sur le segment)

1. **Couverture 9 aéroports français de départ** vs hub-centric anglais.
   Going / Jack's c'est Heathrow / JFK first ; GlobeGenius prend
   Lyon, Marseille, Nantes, Toulouse, Bordeaux et Beauvais
   sérieusement. **Probablement le meilleur moat actuel.**

2. **Re-vérification 2-tier** (Tier 1 LCC direct API + Tier 2
   Travelpayouts). La plupart des concurrents se contentent d'une
   source. Ghost fares Vueling / Ryanair éliminés. **Argument de
   fond crédibilisé par /methodologie.**

3. **Transparence méthodologique publique**. Personne ne publie sa
   baseline statistique, ses exclusions compagnie, ses cooldowns. La
   page /methodologie est unique. **Très puissant en PR + auprès des
   sceptiques.**

4. **Push Telegram** (vs newsletter). Latence ~5 min vs heures pour
   les newsletters. **Avantage significatif sur les mistake fares qui
   durent <2 h.**

5. **Boutons feedback inline** (👍 / 👎 / ⏱️) pour calibration
   continue. Aucun concurrent ne fait ça aujourd'hui. **Différenciation
   technique invisible mais structurante long terme.**

## Faiblesses honnêtes

1. **Pas de long-courrier mature** (Asie, Amériques) — c'est exactement
   ce que Going vend le mieux. Maturité baseline attendue : 6-9 mois.

2. **Pas de gestion famille / multi-pax**. Holiday Pirates et Travelzoo
   poussent des deals "couple/famille" packagés. GlobeGenius est
   flight-only solo aujourd'hui.

3. **Pas de hotel package** — supprimé volontairement pour rester
   focused. Avantage exploité par les concurrents.

4. **Volume bas** : 5 alertes / jour max par user. Going envoie 20-40
   deals / semaine en mode Elite. Pour un deal hunter intensif,
   GlobeGenius est insuffisant.

5. **Pas de notoriété / SEO** : ~50 fondateurs vs Going 2 M, Holiday
   Pirates 4 M abonnés. **N'existe pas dans Google search aujourd'hui.**

6. **Brand "GlobeGenius" inconnu** — confusion possible avec d'autres
   apps voyage. Travelzoo et Going ont 10+ ans de capital de marque.

7. **Web app limitée**. Going a app iOS / Android natives, push
   notifications, expérience produit aboutie. GlobeGenius est
   Telegram-only.

## Positionnement

```
                       PROFONDEUR / RIGUEUR
                                  ▲
     Jack's Flight Club  ●        │
                                  │ ● GlobeGenius
     Going             ●          │
                                  │
       ───────────────────────────┼──────────────► VOLUME / SCALE
                                  │
                                  │  ● Holiday Pirates
                                  │  ● Travelzoo
                                  │  ● Secret Flying
                                  ▼
                       LARGEUR / GRAND PUBLIC
```

Quadrant **haut-gauche : qualité + rigueur > scale**. Cohérent pour une
beta solo founder. Tient si la rigueur est communiquée activement
(d'où l'importance de la page méthodologie + rapports trimestriels
promis publiquement).

## Marché-cible réel

Pas "tous les voyageurs français" — trop large vs le volume actuel.
Le segment où GlobeGenius **gagne vs Going / Jack's** :

> **Voyageur français hors-Paris, 25-45 ans, qui voyage 2-4 fois / an
> depuis sa ville régionale, valeur "qualité > quantité".**

Environ 3-5 M de personnes en France. Going et Jack's ne les couvrent
pas bien (hub-centric anglo-saxon). C'est l'océan bleu.

## Risques compétitifs à 12 mois

1. **Going lance une vraie offre française** (peu probable mais
   possible) → l'avantage hors-Paris disparaît.
2. **Un concurrent FR existant copie la méthodologie publique** —
   Travelinks / Skyscanner-FR sortent leur propre tier-1+2 verification.
3. **Telegram bot officiel d'une OTA majeure** — Aviasales /
   Travelpayouts pourraient pousser leur propre bot.

**Défense principale** : l'engagement public dans la durée
(méthodologie + rapports trimestriels). Un concurrent qui annonce
"nous aussi on calcule médiane" devra prouver 18 mois pour avoir la
même crédibilité.

## Synthèse en une phrase

GlobeGenius est aujourd'hui **le seul service d'alertes flight-deals
qui couvre sérieusement la France hors-Paris avec une méthodologie
publique**. Pas un concurrent direct de Going / Jack's côté volume,
mais peut capter 3-5 M de voyageurs français régionaux qu'ils ignorent.
Le vrai risque n'est pas un concurrent qui copie — c'est de ne pas
tenir les promesses publiques (rapports trimestriels, méthodologie,
transparence) qui forment le moat.
