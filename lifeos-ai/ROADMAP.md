# Roadmap LifeOS AI

## Phase 1 — Fondations (livrée)
- [x] Architecture backend FastAPI + SQLAlchemy
- [x] Auth (JWT, hash bcrypt)
- [x] Tâches, habitudes, objectifs (CRUD complet)
- [x] Mémoire IA long-terme (embeddings + recherche par similarité)
- [x] Chat IA avec contexte personnalisé (mémoire + tâches + objectifs actifs)
- [x] Mémoire automatique : extraction après chaque échange, consultation et suppression par l'utilisateur (`/ai/memories`) — testée (unitaire + API + parcours complet avec faux modèle) ; l'appel réel à Claude reste à valider avec une vraie clé
- [x] Mémoire : écran « Mémoire de l'assistant » dans l'app mobile (Plus › Mémoire) — liste, ajout, suppression, tout oublier ; compilation TypeScript validée, rendu à tester sur Expo Go
- [ ] Chat : envoyer l'historique récent à Claude (aujourd'hui chaque message est traité seul)
- [x] Schéma PostgreSQL de production (toutes les tables du cahier des charges)
- [x] Docker Compose (Postgres+pgvector, Redis, backend)

## Phase 2 — App mobile (React Native)
- [x] Setup projet React Native (Expo) + navigation
- [x] Écrans : onboarding (login/register), tableau de bord, tâches, habitudes, chat IA
- [x] Design system (mode clair/sombre, composants réutilisables, thème "croissance personnelle")
- [x] Connexion à l'API backend (auth token, requêtes)
- [x] Testée en conditions réelles sur iPhone physique via Expo Go (SDK 54) — parcours complet validé : auth, tâches, habitudes, chat
- [x] Navigation regroupée en 5 onglets (Accueil, Tâches, Habitudes, Assistant, Plus) — Calendrier/Sport/Nutrition/Finances déplacés dans un hub "Plus" avec pile de navigation et retour natif
- [x] Version web installable (PWA) servie par le backend + guide de déploiement gratuit (Render + Neon) — voir DEPLOY.md ; testée en navigateur iPhone émulé (inscription → tâches → mémoire → chat) et sur un vrai PostgreSQL ; pas encore testée sur un vrai iPhone ni déployée
- [ ] Notifications push (Firebase Cloud Messaging)

## Phase 3 — Intégrations externes
- [x] Google Calendar (lecture + écriture d'événements) — OAuth2 codé et testé partiellement (endpoints, logique), vrai flux à valider avec de vrais identifiants (voir README)
- [ ] Apple Calendar / Outlook
- [x] Détection de conflits d'agenda (testée, 6/6 tests unitaires)
- [x] Strava (import entraînements) — même statut que Google Calendar : codé et testé partiellement, vrai flux à valider avec de vrais identifiants
- [ ] Apple Health / Google Fit / Garmin — nécessite un "development build" natif (HealthKit inaccessible via Expo Go), à traiter séparément
- [ ] Optimisation de planning par l'IA

## Phase 4 — Modules santé, nutrition, finances
- [x] Suivi sport : programmes générés par l'IA (mode IA + heuristique locale de secours, testée 15/15 tests unitaires + vérification E2E), progression dans le temps du volume d'entraînement
- [x] Nutrition : saisie manuelle (description + calories/macros), résumé quotidien (testé, endpoints validés)
- [x] Nutrition : estimation automatique calories/macros à partir d'une description texte — mode IA (Claude, non testé de bout en bout faute de clé) + heuristique locale de secours (testée, 9/9 tests unitaires). L'estimation depuis une photo reste à faire.
- [x] Finances : transactions manuelles, budgets par catégorie, détection de dépassement (testée, 7 tests unitaires + scénario E2E avec dépassement réel détecté)
- [x] Finances : graphique de répartition des dépenses par catégorie (donut, testé 11/11 tests unitaires sur l'agrégation)
- [ ] Finances : import automatique depuis un compte bancaire (nécessiterait une intégration type Plaid/Bridge, non commencée)

## Phase 5 — Intelligence proactive
- [x] Moteur de notifications contextuelles — partie « règles » : `GET /nudges` (tâches en retard/du jour, séries d'habitudes), testée
- [x] Notifications : carte de rappels sur l'accueil mobile (masquables pour la journée) — compilation validée, rendu à tester sur Expo Go
- [ ] Notifications : envoi en push, règles sommeil/journal/budget, partie « IA »
- [x] Mobile : choix d'échéance à la création d'une tâche (Sans date / Aujourd'hui / Demain / Dans 7 j) et affichage « En retard » — sans échéance, les rappels de tâches ne se déclenchent pas
- [ ] Automatisations conditionnelles (météo, agenda, habitudes)
- [ ] "Daily Life Score" calculé à partir de sommeil/sport/productivité/habitudes
- [ ] Journal intelligent avec résumé hebdomadaire et détection de tendances d'humeur

## Phase 6 — Robustesse & lancement
- [ ] Tests automatisés (backend + mobile)
- [ ] Chiffrement des données sensibles, export/suppression de compte (RGPD)
- [ ] Observabilité (logs, métriques, alerting)
- [ ] Bêta fermée puis lancement public
