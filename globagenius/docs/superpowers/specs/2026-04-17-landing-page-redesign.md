# Landing Page Redesign — GlobeGenius

**Date:** 2026-04-17
**Status:** Validated mockup, ready for implementation

## Problèmes identifiés

1. **Proposition de valeur floue** — les visiteurs ne comprennent pas ce que fait GlobeGenius
2. **Page trop longue** — trop de sections, les gens ne scrollent pas jusqu'au pricing/CTA
3. **Parcours Free → Premium pas clair** — les gens ne comprennent pas pourquoi payer

## Structure validée (7 sections)

Réduction de 11 sections à 7. Suppression de : aperçu Telegram (redondant), destinations (bruit), aéroports (info secondaire, en FAQ).

### 1. Navbar
- Logo GlobeGenius (globe1.png)
- 3 liens : Comment ça marche, Tarifs, FAQ (ancres internes)
- CTA bouton : "S'inscrire" (coral)
- Sticky, fond cream semi-transparent

### 2. Hero (avec image de voyage en fond)
- **Image de fond** : photo de destination (plage/ville) avec overlay sombre gradient (ink 88% → 30%)
- **Badge promo** : "🔥 Offre printemps — Premium à 29€/an au lieu de 59€" (fond coral semi-transparent, border coral)
- **Titre** : "Des vols à prix cassés, détectés _avant tout le monde_." (blanc, "avant tout le monde" en coral)
- **Sous-titre** : "On surveille tous les vols au départ de la France et on vous envoie les meilleures offres sur Telegram. Jusqu'à -70% sur vos billets."
- **CTA** : "Essayer gratuitement" (coral, gros bouton)
- **Micro-copy** : "Gratuit, sans carte bancaire"
- Le texte est aligné à gauche, occupe ~60% de la largeur. L'image se voit sur la droite à travers l'overlay plus léger.

### 3. Stats bar
Intégrée directement sous le hero, fond blanc, 4 stats en ligne :
- 2,340+ vols détectés
- -70% meilleur deal
- 47 deals en cours
- 8 aéroports de départ

### 4. Deals récents
- **Titre** : "Deals détectés récemment"
- **Sous-titre** : "Mis à jour en temps réel — les prix changent vite, ne tardez pas."
- **Grille** : 3 cartes (responsive : 1 colonne mobile, 3 colonnes desktop)
  - 2 deals Free : image destination, badge discount (coral), route, dates, prix actuel (coral) + prix barré
  - 1 deal Premium verrouillé : image assombrie, badge "🔒 Premium" (ink), route, dates, prix flouté (CSS blur), lien "🔓 Débloquer avec Premium →"
- **Source** : les deals sont fetchés dynamiquement depuis l'API (getFlightDeals). Fallback sur FALLBACK_DEALS_HERO si l'API ne répond pas.
- **CTA** : "Voir tous les deals en cours →" (lien coral, mène vers /signup ou /home selon état auth)

### 5. Comment ça marche
- **Titre** : "Comment ça marche ?"
- 3 étapes en colonnes, chacune avec numéro (cercle coral), titre bold, description :
  1. **"On surveille tous les vols au départ de la France"** — Depuis 8 aéroports français, vers le monde entier. En continu, 24h/24.
  2. **"Vous recevez les bons plans sur Telegram"** — Prix, dates, lien direct pour réserver. Rien à faire, tout arrive automatiquement.
  3. **"Vous réservez, vous économisez"** — Jusqu'à -70% sur vos vols, parfois plus avec les erreurs de prix des compagnies.
- Pas de mention d'IA — le client s'en fiche de la techno.

### 6. Pricing (côte à côte)
- **Titre** : "Choisissez votre formule"
- **Sous-titre** : "Un vol Premium rentabilise l'abonnement dès le premier voyage."
- Deux colonnes côte à côte :

**Gratuit (fond blanc, border sand) :**
- Prix : 0€
- ✓ Deals jusqu'à -29%
- ✓ 8 aéroports de départ
- ✓ Alertes Telegram
- ✗ Deals au-delà de -30% (grisé)
- ✗ Alertes prioritaires (grisé)
- ✗ Erreurs de prix (grisé)
- CTA : "S'inscrire gratuitement" (bouton outline ink)

**Premium (fond ink, badge "POPULAIRE" coral) :**
- Prix : ~~59€~~ 29€/an
- ✓ Tous les deals, jusqu'à -70%
- ✓ Erreurs de prix des compagnies
- ✓ 8 aéroports de départ
- ✓ Alertes Telegram prioritaires
- ✓ Garantie satisfait 14 jours
- = 2,42€/mois (vert forest)
- CTA : "Offre printemps -41%" (bouton coral plein)

### 7. FAQ (4 questions)
- **Titre** : "Questions fréquentes"
- Accordion (framer-motion, comme l'actuel mais réduit à 4) :
  1. Comment fonctionne Globe Genius ?
  2. Quelle est la différence entre Gratuit et Premium ?
  3. Comment fonctionne la garantie 14 jours ?
  4. Les prix incluent-ils les bagages ?
- Garder le JSON-LD FAQ schema (mettre à jour avec les 4 questions)

### 8. CTA final
- Fond ink (sombre)
- **Titre** : "Prêt à voyager moins cher ?"
- **Sous-titre** : "Rejoignez les voyageurs qui économisent sur chaque vol."
- **CTA** : "Commencer gratuitement" (bouton coral)

### 9. Footer
- Minimaliste : © 2026 Globe Genius + liens (Conditions, Confidentialité, Mentions légales, Contact)

## Design system (inchangé)

- Palette : Coral #FF6B47, Cream #FFF8F0, Ink #0A1F3D, Sand #F0E6D8, Cyan #06B6D4
- Pas de gradients (sauf overlay photo hero)
- Fonts : DM Serif Display (display) + Plus Jakarta Sans (body)
- Animations : framer-motion whileInView pour les entrées, stagger sur les grilles
- Coins arrondis : xl/2xl/3xl selon composant

## Contraintes techniques

- Le fichier actuel fait 960 lignes. Le nouveau devrait être significativement plus court (~500-600 lignes).
- Garder le client component ("use client") pour framer-motion et le fetch API dynamique.
- Garder les structured data (Organization, Website, FAQ — mettre à jour la FAQ à 4 items).
- Garder DESTINATION_IMAGES map (utilisée par les deal cards).
- Responsive : mobile-first, les grilles passent en 1 colonne sur mobile.
- Images hero : utiliser Unsplash via next/image (déjà configuré dans next.config.ts).

## Ce qui est supprimé

- Section aperçu Telegram (dark mockup) — redondant avec le hero
- Grille filtrable de deals — remplacée par 3 deals simples (2 free + 1 locked)
- Section destinations (6 cartes) — bruit, pas utile à la conversion
- Section aéroports (8) — info couverte par "8 aéroports de départ" dans les stats et étapes
- 3 FAQ supprimées (couvertes par d'autres sections)

## Mockup de référence

Mockup validé : `.superpowers/brainstorm/56462-1776419323/content/full-landing-v2.html`
