# Utiliser LifeOS sur ton iPhone, sans ordinateur ni Claude

Principe : LifeOS tourne sur Internet (un seul service qui sert l'API **et** l'app), et tu l'installes
sur l'écran d'accueil de ton iPhone comme une vraie application (PWA). Une fois en place, plus besoin
de ton ordinateur ni de Claude : tu ouvres l'icône LifeOS, c'est tout.

| Brique | Rôle | Coût |
|---|---|---|
| GitHub | héberge le code (dépôt **privé**) | gratuit |
| Neon | base de données PostgreSQL (tes données restent même si le serveur dort) | offre gratuite |
| Render | fait tourner le backend + l'app web, en HTTPS | offre gratuite |
| Anthropic API | l'IA de l'assistant (chat, mémoire automatique) | **payant à l'usage**, facturé à part de ton abonnement Claude |

Compte ~30 minutes la première fois. Les écrans des sites changent parfois : si un libellé diffère
légèrement, cherche l'équivalent.

## 1. Mettre le code sur GitHub
1. Crée un compte sur github.com, puis un **nouveau dépôt privé** (ex. `lifeos`).
2. Envoie-y le contenu du dossier `lifeos-ai` (le `.gitignore` fourni exclut déjà `.env`, `node_modules`, etc.).
   Sans Git en ligne de commande : sur la page du dépôt, « Add file › Upload files », glisse le contenu du dossier
   (pas le zip lui-même) puis « Commit changes ».

## 2. Créer la base de données (Neon)
1. Compte sur neon.tech, **Create project** (région Europe, ex. Francfort).
2. Sur le tableau de bord, copie la **connection string** (elle ressemble à
   `postgresql://utilisateur:motdepasse@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`).
   Garde-la : c'est ton `DATABASE_URL`. Traite-la comme un mot de passe.

## 3. Déployer sur Render
1. Compte sur render.com, connecte ton GitHub.
2. **New › Blueprint**, choisis ton dépôt : Render lit `render.yaml` et prépare le service `lifeos`.
3. Renseigne les variables demandées :
   - `DATABASE_URL` : la chaîne Neon de l'étape 2 ;
   - `ANTHROPIC_API_KEY` : voir l'étape 4 (tu peux la laisser vide et l'ajouter plus tard : l'assistant répond alors en « mode démo ») ;
   - `JWT_SECRET` est généré automatiquement ; `REGISTRATION_MODE=first_user` est déjà réglé.
4. Lance le déploiement (première construction : plusieurs minutes). Quand c'est « Live », Render te donne
   une adresse du type `https://lifeos-xxxx.onrender.com`.

## 4. Activer l'IA (clé Anthropic)
1. Sur console.anthropic.com, crée un compte, ajoute un moyen de paiement, **fixe une limite de dépense mensuelle**,
   puis crée une clé API. (C'est un compte distinct de ton abonnement Claude : l'abonnement ne couvre pas l'API.)
2. Dans Render › ton service › **Environment**, ajoute `ANTHROPIC_API_KEY` = ta clé, puis sauvegarde (le service redémarre).

## 5. Créer ton compte — tout de suite
Ouvre l'adresse Render **dans Safari sur ton iPhone**, puis « Créer un compte ».
`REGISTRATION_MODE=first_user` ferme les inscriptions dès que ton compte existe : personne d'autre ne pourra
en créer un (et donc utiliser ta clé API). Fais-le avant de partager l'adresse à qui que ce soit.

## 6. Installer l'icône sur l'iPhone
Dans **Safari** (pas Chrome) : bouton Partager › **Sur l'écran d'accueil** › Ajouter.
L'app s'ouvre ensuite en plein écran, sans barre Safari, et ta session est conservée.

## À savoir
- **Premier lancement lent** : sur l'offre gratuite de Render, le serveur s'endort après ~15 min sans visite et met
  environ une minute à se réveiller. Tes données, elles, sont dans Neon et ne bougent pas. Pour supprimer l'attente :
  passer le service sur une offre payante de Render, ou un service de « ping » gratuit qui appelle `/health` toutes les 10 min.
- **Mises à jour** : modifie le code sur GitHub, Render redéploie tout seul. L'app installée se met à jour à la
  réouverture (fermer complètement puis rouvrir l'icône).
- **Pas de notifications push** : les rappels s'affichent dans l'app à l'ouverture (carte « rappels »).
- **Google Calendar / Strava** : les URLs de redirection (`GOOGLE_REDIRECT_URI`, `STRAVA_REDIRECT_URI`) doivent devenir
  `https://ton-adresse.onrender.com/...` — dans les variables Render **et** dans les consoles Google/Strava. Non testé en ligne.
- **Sauvegardes** : la base est chez Neon ; vérifie ce que leur offre gratuite conserve avant d'y mettre des données précieuses.
- **Mot de passe oublié** : pas de procédure de réinitialisation pour l'instant.

## Alternative : vraie app native (TestFlight)
Une app installée comme une application App Store (notifications push possibles) passe par EAS Build + TestFlight et
demande un compte **Apple Developer payant**. Non nécessaire pour l'usage décrit ici ; à envisager plus tard.

## Essayer en local avant de déployer (facultatif)
```bash
cd mobile && npm ci && npx expo export --platform web      # produit mobile/dist
cd ../backend && pip install -r requirements.txt
WEB_DIR=../mobile/dist uvicorn app.main:app --port 8000     # puis ouvrir http://localhost:8000
```
Ou, avec Docker : `docker build -t lifeos . && docker run -p 8000:8000 -e PORT=8000 lifeos`.
