# Travel-Tech Glossary

Référence à charger quand le livrable nécessite une précision terminologique sur l'écosystème voyage.

## Distribution & sourcing

- **OTA (Online Travel Agency)** : agence de voyage en ligne (Booking, Expedia, Hotels.com). Revend l'inventaire de fournisseurs avec marge.
- **GDS (Global Distribution System)** : Amadeus, Sabre, Travelport. Plateforme historique d'agrégation d'inventaire airline + hotel + car. Toujours dominante en B2B.
- **NDC (New Distribution Capability)** : standard XML d'IATA pour la distribution directe airline → agences sans GDS. Permet aux compagnies de vendre des bundles enrichis (bagages, sièges, repas) au-delà du tarif sec.
- **Metasearch** : Skyscanner, Kayak, Google Flights, Trivago. N'a pas l'inventaire — redirige vers OTA/airline. Monétise via CPC/CPA.
- **Direct booking** : réservation directe sur le site de la compagnie ou de l'hôtel. Plus de marge pour le fournisseur, parfois meilleur prix.
- **Aggregator** : agrège des offres de multiples sources (terme générique englobant metasearch et OTA hybrides).

## Pricing & deals

- **Error fare / mistake fare** : tarif publié par erreur (mauvaise conversion devise, oubli de surcharge, bug de pricing engine). Souvent annulé sous 24-72h. Cœur du sourcing Globe Genius.
- **Fuel dump / hidden city / throwaway ticketing** : techniques de contournement tarifaire. **À éviter en produit grand public** (violent les CGV des compagnies, risque de blacklist).
- **Dynamic pricing** : ajustement en temps réel des prix selon demande, inventaire, comportement utilisateur. Standard dans l'aérien et l'hôtellerie.
- **Yield management / Revenue management** : discipline d'optimisation revenu par siège ou nuit disponible.
- **Fare class / booking class** : code lettre (Y, B, M, K, ...) qui détermine restrictions et prix. Importance pour les revendeurs.
- **Advance purchase (AP)** : nombre de jours minimum avant départ. Influence majeure sur le prix.
- **Stay-over Saturday rule** : ancienne règle qui imposait de dormir un samedi sur place pour bénéficier d'un tarif loisir. Largement obsolète mais encore présente sur certains tarifs corporate.
- **One-way pricing** : tarif aller-simple. Souvent plus cher proportionnellement qu'un AR (sauf low-cost).
- **Open-jaw** : départ d'une ville, retour vers une autre. Ex : Paris → Tokyo, Osaka → Paris.
- **Multi-city / stopover** : plusieurs segments avec arrêts volontaires.
- **Deal score** : métrique propriétaire (Globe Genius) — mix de % discount vs baseline, percentile historique, et freshness.

## Packaging

- **Dynamic packaging (DP)** : assemblage à la volée d'un vol + hôtel (+ extras) provenant de sources différentes, vendu comme un package unique. Permet contournement de la **rate parity** (l'hôtel ne peut pas vendre moins cher que sur Booking, mais peut accepter un prix plus bas si bundlé avec un vol).
- **Static package (forfait tour-opérateur)** : ancien modèle, lots pré-négociés.
- **Net rate** : prix HT négocié entre hôtel et revendeur, jamais affiché.
- **Rack rate** : prix public maximum affiché (rarement payé en réalité).
- **Bedbank** : grossiste hôtelier B2B (Hotelbeds, GIATA). Source d'inventaire pour les OTA.

## Inventaire aérien

- **Codeshare** : un vol opéré par compagnie A est aussi vendu sous le numéro de compagnie B (alliance). Impact UX : l'utilisateur voit "Air France AF1234 opéré par KLM".
- **Interline** : accord billet unique entre compagnies non-alliées. Bagages enregistrés bout-en-bout.
- **Self-transfer / virtual interlining** : Kiwi.com a popularisé. L'utilisateur achète 2 billets distincts présentés comme un seul. Risque de perte de bagage et de connexion ratée non couverte par la compagnie. Marketing UX = clé.
- **LCC (Low-Cost Carrier)** : Ryanair, easyJet, Wizz, Vueling. Tarifs sec très bas, ancillaries (bagages, sièges, priority) génèrent 30-40% du revenu.
- **HFC (Hybrid / Full-service Carrier)** : Air France, Lufthansa, BA — tarifs incluant souvent bagage cabine + repas.
- **Ultra-LCC** : Spirit, Frontier (US) — pousse encore plus loin la dégradation de l'inclus.

## Hébergement

- **OTA contract types** : merchant model (OTA paie l'hôtel après séjour), agency model (hôtel paie commission post-stay), opaque (Hotwire — nom révélé après achat).
- **Rate parity clauses** : clauses MFN ("Most Favored Nation") qui empêchent l'hôtel de vendre moins cher ailleurs. Sous pression réglementaire en Europe.
- **Revenue Per Available Room (RevPAR)** : KPI standard hôtellerie = ADR × occupancy.
- **ADR (Average Daily Rate)** : prix moyen vendu par nuit.

## Comportement & segmentation voyageur

- **Leisure / Bleisure / Business** : segmentation classique. Globe Genius cible majoritairement leisure.
- **Booking window / lead time** : délai entre la décision d'achat et le départ. Court courrier = 0-30j, long courrier = 30-90j, bargain hunters = jusqu'à 6+ mois.
- **Trip purpose** : weekend, vacances familiales, road trip, voyage de noces, city break — chaque purpose a un funnel et un pricing distincts.
- **Origin city / catchment area** : zone d'origine de l'utilisateur (CDG, ORY, BVA pour Paris). Crucial pour le sourcing Globe Genius — un user parisien acceptera Beauvais sur un LCC, un user lyonnais ne se déplacera pas à Paris.

## Conformité & réglementation (Europe)

- **EU 261/2004** : règlement européen sur les indemnisations en cas de retard, annulation, refus d'embarquement. Important à connaître pour le SAV et la trust.
- **Package Travel Directive (EU 2015/2302)** : transposée en France (Code du tourisme). Impose des obligations spécifiques aux vendeurs de "forfaits" — y compris des dynamic packages selon le seuil de bundle. **À surveiller pour Globe Genius si vente directe** (vs simple redirection affiliate).
- **Atout France immatriculation** : obligatoire en France pour vendre des forfaits voyage. Si Globe Genius reste pure player metasearch / affiliate, pas requis. Si bascule vers la vente, devient critique.
- **GDPR** : consentement marketing, droit d'oubli, transferts de données — applicable à toute la base user.
- **PSD2 / SCA** : authentification forte pour les paiements > 30€. Stripe gère, mais doit être bien intégré pour ne pas dégrader la conversion.

## Acronymes utiles

- **ADR** — Average Daily Rate (hôtellerie)
- **ANR** — Average Net Rate
- **ASK** — Available Seat Kilometers (capacité aérienne)
- **CPM** — Cost Per Mile (cargo et passager unit cost)
- **DMC** — Destination Management Company (réceptifs locaux)
- **GMV** — Gross Merchandise Value (volume vendu, pas revenu)
- **NPS** — Net Promoter Score
- **OAG** — Official Airline Guide (data provider)
- **PNR** — Passenger Name Record (dossier de réservation)
- **RBD** — Reservation Booking Designator (= fare class)
- **TAC** — Travel Agent Commission
- **TMC** — Travel Management Company (B2B corporate travel)
