# LifeOS AI

Assistant personnel de vie intelligent — coach, secrétaire, gestionnaire d'objectifs
et journal réunis dans une seule app.

## Statut

**Phase 1 (livrée) : backend prototype fonctionnel.**
Auth, tâches, habitudes, objectifs, mémoire IA long-terme, chat avec l'IA.
Testé de bout en bout (voir logs de test dans la conversation d'origine).

Ce qui n'est **pas encore construit** : l'app mobile, les intégrations
calendrier/santé/finances réelles, les notifications push (les rappels
contextuels existent côté serveur : voir « Mémoire automatique et
rappels » plus bas), le tableau de bord. Voir `ROADMAP.md`.

## Structure du projet

```
lifeos-ai/
├── backend/                  # API FastAPI (Python)
│   ├── app/
│   │   ├── main.py           # point d'entrée
│   │   ├── config.py         # variables d'environnement
│   │   ├── database.py       # connexion SQLAlchemy
│   │   ├── models.py         # tables (prototype, SQLite)
│   │   ├── schemas.py        # validation Pydantic
│   │   ├── auth.py           # JWT + hash mots de passe
│   │   ├── nudges.py         # règles des rappels intelligents (fonction pure)
│   │   ├── ai/
│   │   │   ├── memory.py     # mémoire vectorielle (RAG maison)
│   │   │   ├── memory_extraction.py  # mémoire automatique après chaque échange
│   │   │   └── engine.py     # prompt système + appel API Claude
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── tasks.py
│   │       ├── habits.py
│   │       ├── goals.py
│   │       ├── ai_chat.py
│   │       └── nudges.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── database/
│   └── schema.sql             # schéma PostgreSQL complet (production, pgvector)
├── mobile/                    # app React Native (Phase 2, à construire)
├── docker-compose.yml         # Postgres (pgvector) + Redis + backend
└── ROADMAP.md
```

## Lancer le prototype en local

```bash
cd backend
cp .env.example .env          # ajoute ta clé ANTHROPIC_API_KEY pour activer le vrai chat IA
pip install -r requirements.txt
uvicorn app.main:app --reload
```

L'API démarre sur `http://localhost:8000`. Documentation interactive
auto-générée : `http://localhost:8000/docs`.

Sans clé `ANTHROPIC_API_KEY`, l'endpoint `/ai/chat` répond en mode démo
(mais construit quand même le contexte personnalisé à partir de la
mémoire, des tâches et des objectifs — tu peux vérifier que la
récupération de mémoire fonctionne).

### Endpoints principaux

| Méthode | Route | Description |
|---|---|---|
| POST | `/auth/register` | Créer un compte |
| POST | `/auth/login` | Se connecter (retourne un JWT) |
| GET | `/auth/me` | Profil de l'utilisateur connecté |
| GET/POST | `/tasks` | Lister / créer une tâche |
| PATCH/DELETE | `/tasks/{id}` | Modifier / supprimer une tâche |
| GET/POST | `/habits` | Lister / créer une habitude |
| POST | `/habits/{id}/log` | Enregistrer une réalisation |
| GET/POST | `/goals` | Lister / créer un objectif |
| POST | `/ai/chat` | Discuter avec l'assistant IA (mémoire incluse) |
| POST | `/ai/memories` | Ajouter un souvenir manuellement |
| GET | `/ai/memories` | Tout ce que l'assistant retient (du plus récent au plus ancien) |
| DELETE | `/ai/memories/{id}` | Oublier un souvenir |
| DELETE | `/ai/memories` | Tout oublier |
| GET | `/nudges?tz=Europe/Paris&dismissed=late` | Rappels du moment (4 max) |

## Mémoire automatique et rappels

**Mémoire automatique.** Après chaque réponse de `/ai/chat`, une tâche de
fond demande à Claude s'il y a quelque chose de durable à retenir sur
l'utilisateur (préférence, proche, projet, contrainte), à corriger ou à
oublier (« oublie que… »). Le résultat est stocké dans la table `memories`
existante, avec son embedding, et retrouvé ensuite par la recherche de
`app/ai/memory.py`. L'utilisateur voit et supprime tout via
`GET/DELETE /ai/memories`.

- 3 nouveaux souvenirs au plus par échange ; doublons ignorés ; au-delà de
  40 souvenirs, une consolidation fusionne les doublons (son résultat est
  rejeté s'il est mal formé ou supprime plus de 60 % des souvenirs).
- Le modèle désigne les souvenirs à retirer par un numéro dans la liste de
  l'utilisateur concerné : il ne peut pas toucher à ceux d'un autre.
- Les messages de moins de 12 caractères ne déclenchent pas d'extraction
  (sauf s'ils contiennent « retiens » ou « oublie »).
- Sans `ANTHROPIC_API_KEY` (mode démo), l'extraction est désactivée.
- La réponse du chat n'attend pas l'extraction : le client voit les
  nouveaux souvenirs en rechargeant `GET /ai/memories`.
- **Confidentialité :** chaque extraction envoie à l'API Claude le message,
  la réponse de l'assistant et les souvenirs déjà enregistrés. Les journaux
  n'écrivent que des compteurs.

**Rappels.** `GET /nudges` applique les règles de `app/nudges.py` aux
tâches et habitudes de l'utilisateur : tâches en retard ou à terminer
aujourd'hui, série d'une habitude quotidienne en jeu (dès 17 h, série de 3
jours ou plus), habitudes quotidiennes restantes (dès 18 h). Le client passe
son fuseau (`tz`, nom IANA) ; à défaut, `DEFAULT_TIMEZONE`
(`Europe/Paris`). Pour masquer un rappel, le client le mémorise et renvoie
sa clé dans `dismissed` (le serveur ne garde pas d'état). Ce sont des
rappels à afficher dans l'app, pas des notifications push.

Limites connues : l'app mobile n'envoie pas encore d'échéance à la création
d'une tâche, donc les rappels « en retard » et « aujourd'hui » ne se
déclenchent que pour les tâches créées avec `due_date` ; les rappels
« sommeil », « journal » et « bilan du dimanche » du prototype web ne sont
pas repris tant que le backend n'a ni suivi du sommeil ni journal.

## Tests

```bash
cd backend
pytest      # test_nutrition_finance.py (script E2E) est ignoré par pytest
```

`test_nutrition_finance.py` se lance à part, serveur démarré :
`python test_nutrition_finance.py`.

## Passer en production (PostgreSQL)

1. `docker compose up -d postgres redis` (utilise `database/schema.sql` avec pgvector)
2. Dans `backend/.env`, remplacer `DATABASE_URL` par l'URL Postgres
3. Remplacer l'embedding "hashing" de `app/ai/memory.py` par un vrai modèle
   d'embeddings, et adapter la colonne `embedding` (JSON → `vector`)

## App mobile (Phase 2)

```bash
cd mobile
npm install
npx tsc --noEmit     # vérifie que tout compile (validé : 0 erreur)
npx expo start       # lance Metro — scanner le QR code avec Expo Go
```

Avant de lancer sur un téléphone physique ou un simulateur, changer
`API_BASE_URL` dans `mobile/src/api/client.ts` : `localhost` ne
fonctionne que si le backend et l'outil de dev tournent sur la même
machine avec un simulateur iOS. Pour un téléphone physique ou un
émulateur Android, utiliser l'IP locale de la machine qui fait tourner
le backend (ex: `http://192.168.1.20:8000`).

Écrans livrés : connexion, inscription, tableau de bord (avec le
"Daily Life Score" calculé à partir des tâches et objectifs), tâches,
habitudes, chat IA. Thème clair/sombre automatique selon les
préférences système.

Ajouts liés à la mémoire automatique et aux rappels (voir plus haut) :

- **Accueil** : carte de rappels (`GET /nudges`, fuseau de l'appareil). Un tap
  ouvre l'onglet concerné ; la croix masque le rappel pour la journée (retenu
  localement dans AsyncStorage, clé `lifeos_dismissed_nudges`).
- **Tâches** : choix d'échéance à la création (Sans date, Aujourd'hui, Demain,
  Dans 7 j) et affichage de l'échéance, « En retard » en rouge. L'échéance est
  envoyée comme minuit local sans fuseau (`2026-11-17T00:00:00`), car le backend
  ne retient que le jour.
- **Plus › Mémoire de l'assistant** : ce que l'assistant retient, avec ajout,
  suppression d'un souvenir et « Tout oublier » (confirmation). La liste se
  recharge à l'ouverture et par tirage vers le bas : l'extraction se fait en
  tâche de fond côté serveur, un souvenir peut apparaître quelques secondes
  après l'échange.

Vérifié : `npx tsc --noEmit` (0 erreur) et les fonctions de dates
(`src/utils/dates.ts`) par un script Node. Non vérifié : le rendu sur appareil.

**Non testé dans ce sandbox** (pas de simulateur iOS/Android
disponible ici) : le rendu visuel réel et le comportement sur
appareil. Seule la compilation TypeScript a pu être vérifiée
(0 erreur sur les 18 fichiers). À tester sur Expo Go avant d'aller
plus loin.

## Utiliser LifeOS sur l'iPhone sans ordinateur
L'app mobile s'exporte aussi en web (PWA) et le backend la sert à la même adresse : un seul service à héberger,
à installer depuis Safari (« Sur l'écran d'accueil »). Guide pas à pas (GitHub + Neon + Render) : **[DEPLOY.md](DEPLOY.md)**.
Variables utiles : `REGISTRATION_MODE` (`open` / `first_user` / `closed`), `CORS_ORIGINS`, `WEB_DIR`, `JWT_SECRET` (32 caractères
minimum dès que la base n'est pas SQLite).

## Google Calendar (Phase 3)

**Important, à lire avant de tester :** je n'ai aucun accès réseau vers
Google (accounts.google.com / googleapis.com) dans mon environnement
de développement. Le code suit fidèlement le protocole OAuth2 officiel
de Google, mais je n'ai pas pu faire un vrai test de bout en bout —
seule ta machine, avec de vrais identifiants, peut confirmer que ça
fonctionne. Ce que j'ai pu vérifier ici : le serveur démarre avec le
nouveau router, les endpoints répondent correctement (401 sans token,
503 avec message clair si les identifiants Google ne sont pas
configurés), et la détection de conflits d'agenda est validée par des
tests unitaires (`test_calendar_conflicts.py`, 6/6 passés).

### Créer tes identifiants Google Cloud

1. Va sur [console.cloud.google.com](https://console.cloud.google.com), crée un projet (ou utilise un existant)
2. Menu "API et services" → "Bibliothèque" → cherche "Google Calendar API" → Activer
3. "API et services" → "Écran de consentement OAuth" → type "Externe" → remplis le nom de l'app et ton email → en mode test, ajoute ton propre email comme utilisateur de test
4. "API et services" → "Identifiants" → "Créer des identifiants" → "ID client OAuth" → type "Application Web"
5. Dans "URI de redirection autorisés", ajoute exactement : `http://localhost:8000/calendar/google/callback`
6. Copie le "ID client" et le "Code secret du client" générés

### Configurer et tester

1. Dans `backend/.env`, renseigne `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET`
2. Redémarre le backend
3. Dans l'app mobile, onglet "Calendrier" → "Connecter" → ça ouvre le navigateur vers l'écran de consentement Google → autorise
4. Tu es redirigé vers une page de confirmation simple (pas encore de deep link vers l'app — à faire en Phase suivante) → reviens dans l'app et appuie sur "Synchroniser"

Si une étape échoue, colle-moi l'erreur exacte — je n'ai pas pu
anticiper tous les cas limites sans pouvoir tester le vrai flux.

## Strava (Phase 3)

Même avertissement que pour Google Calendar : je n'ai pas d'accès
réseau vers www.strava.com dans mon environnement de développement, le
vrai flux OAuth n'a donc pas pu être testé de bout en bout. Ce qui EST
vérifié : le serveur démarre avec le router intégré, tous les endpoints
répondent correctement sans connexion Strava, et surtout la fonction
qui convertit une activité Strava en entraînement local est validée
par 8 tests unitaires (`test_strava_mapping.py`) couvrant les cas
limites réels (calories absentes selon le capteur, type de sport non
répertorié).

### Créer tes identifiants Strava

1. Va sur [strava.com/settings/api](https://www.strava.com/settings/api) (connecté à ton compte Strava)
2. Crée une "Application Web" — le nom et la catégorie n'ont pas d'importance pour un usage perso
3. Dans "Authorization Callback Domain", mets juste : `localhost`
4. Note le "Client ID" et le "Client Secret" affichés

### Configurer et tester

1. Dans `backend/.env`, renseigne `STRAVA_CLIENT_ID` et `STRAVA_CLIENT_SECRET`
2. Redémarre le backend
3. Dans l'app, onglet "Sport" → "Connecter" → autorise dans le navigateur
4. Reviens dans l'app, appuie sur "Synchroniser"

Strava limite les appels API pour les apps non vérifiées (100
requêtes/15 min, 1000/jour) — largement suffisant pour un usage perso,
mais à savoir si tu synchronises très souvent en test.

## Nutrition & Finances (Phase 4)

Ces deux modules n'ont besoin d'aucune configuration externe — ils
sont testés de bout en bout dans ce sandbox (voir
`test_nutrition_finance.py`, 13/13 tests passés, y compris un scénario
réel de dépassement de budget détecté correctement).

**Nutrition** : saisie manuelle d'une description + calories/macros
optionnels, résumé quotidien automatique. L'estimation automatique
depuis une photo (prévue au cahier des charges) n'est pas encore
implémentée — l'app attend une saisie manuelle des calories pour
l'instant.

**Finances** : transactions manuelles par catégorie, budgets mensuels,
détection de dépassement en temps réel (`/finance/budgets/status`
recalcule les dépenses du mois en cours à chaque appel). Pas d'import
bancaire automatique — à ajouter via une intégration type Plaid/Bridge
si besoin.

Les deux ont leur onglet dans l'app mobile ("Nutrition", "Finances").

### Estimation nutritionnelle (calories/macros) automatique

Dans l'onglet Nutrition, le bouton "Estimer les calories" appelle
`POST /nutrition/estimate` avec la description tapée, et pré-remplit
les champs (calories, protéines, glucides, lipides) — modifiables
avant de valider.

Deux modes, choisis automatiquement :
- **Avec `ANTHROPIC_API_KEY` configurée** : l'estimation passe par
  Claude. Je n'ai pas pu tester ce chemin de bout en bout — pas de
  clé dans mon environnement de dev — mais le réseau vers
  `api.anthropic.com` est bien joignable ici (vérifié), et le code
  réutilise exactement le pattern déjà utilisé pour le chat IA
  (`app/ai/engine.py`). À confirmer avec ta propre clé.
- **Sans clé** (mode démo actuel) : une heuristique locale reconnaît
  une vingtaine d'aliments courants (`app/ai/nutrition_estimator.py`,
  `FOOD_DATABASE`) et additionne leurs valeurs typiques, avec gestion
  simple des quantités ("2 oeufs" → x2). **Testé réellement** :
  9/9 tests unitaires (`test_nutrition_estimator.py`), plus un test
  E2E via l'API (`2 oeufs et du pain` → 220 kcal, cohérent).
  Limite assumée : une vingtaine d'aliments seulement, pas de vraie
  compréhension du texte — un aliment absent de la liste renvoie
  `found: false` sans planter.

### Graphique de répartition des dépenses

Un donut (`GET /finance/spending-by-category`, composant mobile
`SpendingDonut`) affiche la répartition des dépenses du mois en cours
par catégorie, avec légende et montants. Contrairement à
`/budgets/status`, il inclut TOUTES les catégories, pas seulement
celles avec un budget défini — les transactions sans catégorie sont
regroupées sous "autre". Testé réellement : 11/11 tests unitaires sur
l'agrégation (`test_finance_utils.py`), plus vérification manuelle via
l'API (trois catégories avec des montants différents → tri décroissant
correct : restaurant 65.5€, transport 60€, autre 15€).

### Programmes sportifs générés

Dans l'onglet Sport, la section "Programme d'entraînement" génère un
plan multi-semaines à partir d'un objectif en texte libre (ex:
"courir un semi-marathon dans 3 mois"), sauvegardé et consultable
ensuite (`POST/GET /workouts/programs`).

Même architecture que l'estimation nutritionnelle :
- **Avec `ANTHROPIC_API_KEY`** : Claude génère le programme. Non testé
  de bout en bout ici faute de clé (même limite que pour la nutrition),
  mais réutilise le pattern déjà éprouvé.
- **Sans clé** (mode démo actuel) : heuristique locale
  (`app/ai/workout_planner.py`) qui détecte la catégorie d'objectif
  (course/musculation/cardio/générique) par mots-clés, déduit la durée
  ("6 mois" → 24 semaines) et génère un plan progressif avec semaines
  de récupération toutes les 4 semaines. **Testé réellement** :
  15/15 tests unitaires (`test_workout_planner.py`) + vérification
  E2E via l'API — un objectif "marathon dans 2 mois" génère bien
  8 semaines avec une sortie longue qui progresse dans le temps.
  Limite assumée : 4 catégories seulement, progression linéaire simple
  (pas d'adaptation à un niveau de forme initial).
